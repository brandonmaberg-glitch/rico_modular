"""Runtime entry point for the RICO assistant."""
from __future__ import annotations

import json
import logging
import os
import re

import conversation
import core.skill_loader as SkillLoader
from config.settings import AppConfig
from core.intent_router import select_skill
from core.skill_registry import SkillRegistry
from logs.logger import setup_logger
from memory.memory_manager import (
    append_conversation_turn,
    clear_conversation_history,
    get_context,
    get_conversation_history,
    get_relevant_memories,
    periodic_memory_maintenance,
    process_memory_suggestion,
    set_context,
)
from rico.app import RicoApp
from rico.app_context import AppContext, get_app_context
from rico.commands import _handle_voice_command, _normalise_command, _should_exit
from rico.processing import handle_text_interaction
from router.command_router import CommandRouter
from skills import car_info, system_status, web_search
from stt.base import SpeechToTextEngine, TranscriptionResult
from tts.speaker import Speaker
from ui_bridge import (
    launch_ui,
    send_listening,
    send_reply,
    send_thinking,
    send_transcription,
    start_ui_server,
)
from wakeword.engine import WakeWordEngine


logger = logging.getLogger("RICO")


def _parse_response_output(completion: object) -> dict | None:
    """
    Extract a structured memory_response payload from the Responses API output.

    Supports:
    - Responses-style tool calls inside message.content[] with type == "tool_call"
    - Legacy Responses-style items with type == "function_call"
    - Chat Completions-style message.tool_calls
    - Plain assistant message text as a last resort

    Returns:
        dict with keys:
            "reply": str
            "memory_to_write": str | None
            "should_write_memory": str | None
        or None if nothing usable could be found.
    """

    try:
        response_dict = completion.model_dump()
    except Exception as exc:  # pragma: no cover - defensive
        conversation.logger.error("Failed to dump completion: %s", exc)
        return None

    outputs = response_dict.get("output") or []
    if not outputs:
        conversation.logger.error("No 'output' items present in response: %r", response_dict)
        return None

    # 1) New Responses API pattern:
    #    - output items with type == "message"
    #    - message["content"] is a list of blocks
    #    - each block may have type == "tool_call" with name & arguments
    message_items = [item for item in outputs if item.get("type") == "message" or item.get("role") == "assistant"]
    for message in message_items:
        for block in message.get("content", []) or []:
            block_type = block.get("type")
            if block_type not in ("tool_call", "function_call"):
                continue

            # New Responses output usually has these at the block level
            name = block.get("name") or block.get("function", {}).get("name")
            if name and name != "memory_response":
                continue

            args = block.get("arguments") or block.get("function", {}).get("arguments") or "{}"

            try:
                if isinstance(args, str):
                    parsed_args = json.loads(args)
                elif isinstance(args, dict):
                    parsed_args = args
                else:
                    conversation.logger.error(
                        "Unexpected arguments type in tool_call block: %r", type(args)
                    )
                    return None

                # Normalise expected keys
                if "reply" not in parsed_args:
                    conversation.logger.warning(
                        "memory_response tool_call missing 'reply': %r", parsed_args
                    )
                    continue

                parsed_args.setdefault("memory_to_write", None)
                parsed_args.setdefault("should_write_memory", None)
                return parsed_args
            except Exception as exc:  # pragma: no cover - defensive
                conversation.logger.error("Failed to parse tool_call arguments: %s", exc)
                return None

    # 2) Legacy Responses-style items with top-level type == "function_call"
    for item in outputs:
        if item.get("type") == "function_call":
            tool_name = item.get("name")
            if tool_name and tool_name != "memory_response":
                continue

            try:
                args = item.get("arguments") or "{}"
                if isinstance(args, str):
                    parsed_args = json.loads(args)
                elif isinstance(args, dict):
                    parsed_args = args
                else:
                    conversation.logger.error(
                        "Unexpected arguments type in legacy function_call item: %r", type(args)
                    )
                    return None

                if "reply" not in parsed_args:
                    conversation.logger.warning(
                        "memory_response function_call missing 'reply': %r", parsed_args
                    )
                    continue

                parsed_args.setdefault("memory_to_write", None)
                parsed_args.setdefault("should_write_memory", None)
                return parsed_args
            except Exception as exc:  # pragma: no cover - defensive
                conversation.logger.error("Failed to parse legacy function_call arguments: %s", exc)
                return None

    # 3) Chat Completions-style tool_calls on the message itself (very old path)
    if message_items:
        last_msg = message_items[-1]
        tool_calls = last_msg.get("tool_calls") or []
        if not tool_calls:
            for block in last_msg.get("content", []) or []:
                if block.get("tool_calls"):
                    tool_calls = block["tool_calls"]
                    break

        if tool_calls:
            try:
                args = tool_calls[0]["function"]["arguments"]
                if isinstance(args, str):
                    parsed_args = json.loads(args)
                elif isinstance(args, dict):
                    parsed_args = args
                else:
                    conversation.logger.error(
                        "Unexpected arguments type in legacy tool call: %r", type(args)
                    )
                    return None

                if "reply" not in parsed_args:
                    parsed_args["reply"] = ""
                parsed_args.setdefault("memory_to_write", None)
                parsed_args.setdefault("should_write_memory", None)
                return parsed_args
            except Exception as exc:  # pragma: no cover - defensive
                conversation.logger.error("Failed to parse legacy tool call: %s", exc)
                return None

    # 4) Plain text fallback – just use any assistant text we can find
    if message_items:
        last_msg = message_items[-1]
        for block in last_msg.get("content", []) or []:
            text = block.get("text")
            if text:
                return {
                    "reply": text,
                    "memory_to_write": None,
                    "should_write_memory": None,
                }

    # Final debug log so we can see future unexpected shapes
    conversation.logger.error("Unable to interpret model output structure: %r", outputs)
    return None


def _conversation_with_memory(text: str) -> dict:
    """
    Memory-aware conversation using the NEW OpenAI Responses API
    with function-calling (tools) for structured JSON output.
    """

    # 1. Retrieve relevant memories
    relevant_memories = get_relevant_memories(text, top_k=5)

    if relevant_memories:
        bullet_list = "\n".join(
            f"- {m['text']} (category: {m['category']}, importance: {m['importance']:.2f})"
            for m in relevant_memories
        )
        memory_context = (
            "You have stored user memories. Use them when answering.\n"
            f"Memories:\n{bullet_list}\n\n"
        )
    else:
        memory_context = "No stored memories are available.\n\n"

    # 2. Safety check
    if not conversation._client:
        return {"reply": "Terribly sorry Sir, my conversational faculties are offline."}

    # 3. Build personality + persona
    system_personality_prompt = (
        f"{conversation._SYSTEM_PROMPT}\npersona:{conversation._PERSONA_ID}"
    )
    persona_content = conversation._PERSONA_TEXT

    # 4. Detect subject to build contextual memory
    subject, subject_type = conversation.detect_subject(text)
    if subject:
        conversation.set_context_topic(subject, subject_type)
    context_message = (
        conversation._build_context_message()
        if conversation._needs_context(text)
        else None
    )

    # 1b. Retrieve recent short-term conversation history
    recent_turns = get_conversation_history(max_turns=8)
    if recent_turns:
        history_lines = []
        for turn in recent_turns:
            u = turn.get("user") or ""
            a = turn.get("assistant") or ""
            if u:
                history_lines.append(f"User: {u}")
            if a:
                history_lines.append(f"RICO: {a}")
        history_text = "Recent conversation (most recent last):\n" + "\n".join(history_lines) + "\n\n"
    else:
        history_text = ""

    # 5. Build Inputs (NEW API FORMAT)
    system_content_blocks = [
        {"type": "input_text", "text": system_personality_prompt},
        {"type": "input_text", "text": persona_content},
        {"type": "input_text", "text": memory_context},
    ]

    if history_text:
        system_content_blocks.append(
            {"type": "input_text", "text": history_text}
        )

    if context_message:
        system_content_blocks.append(
            {"type": "input_text", "text": context_message["content"]}
        )

    system_content_blocks.append(
        {
            "type": "input_text",
            "text": (
                "Always call the `memory_response` tool to return your reply and "
                "memory suggestions as structured JSON. Never return plain text "
                "or JSON outside of the tool."
            ),
        }
    )

    input_blocks = [
        {
            "role": "system",
            "content": system_content_blocks,
        },
        {
            "role": "user",
            "content": [
                {"type": "input_text", "text": text},
            ],
        },
    ]

    # 6. Define the function tool (the correct replacement for response_format)
    tools = [
        {
            "type": "function",
            "name": "memory_response",
            "description": "Structured memory-aware reply from RICO.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reply": {"type": "string"},
                    "memory_to_write": {"type": ["string", "null"]},
                    "should_write_memory": {"type": ["string", "null"]},
                },
                "required": ["reply", "memory_to_write", "should_write_memory"],
                "additionalProperties": False,
            },
            "strict": True,
        }
    ]

    # 7. Call the NEW Responses API
    try:
        completion = conversation._client.responses.create(
            model=conversation._select_model(text),
            input=input_blocks,
            tools=tools,
            tool_choice={
                "type": "function",
                "name": "memory_response",
            },
            temperature=0.4,
        )

        parsed = _parse_response_output(completion)
        if parsed:
            return parsed

        # Final failsafe
        return {
            "reply": "My apologies Sir, I was unable to interpret the model's response.",
            "memory_to_write": None,
            "should_write_memory": None
        }

    except Exception as exc:
        conversation.logger.error("Conversation failed: %s", exc)
        return {
            "reply": "My apologies Sir, something went wrong.",
            "memory_to_write": None,
            "should_write_memory": None,
        }
def build_skill_registry(config: AppConfig):
    """Create the mapping of skill names to callable handlers."""
    registry = SkillRegistry()
    skills = SkillLoader.load_skills()

    for skill in skills:
        registry.register(skill)

    from skills.conversation import ConversationSkill

    conversation_skill = ConversationSkill(
        name="ConversationSkill",
        description="Handles general conversation",
        handler=_conversation_with_memory,
    )

    registry.register(conversation_skill)

    skills.append(conversation_skill)

    loaded_skill_names = [skill.__class__.__name__ for skill in skills]
    logger.info("Loaded skills: %s", ", ".join(loaded_skill_names) or "none")

    return (
        registry,
        {
            "system_status": system_status.activate,
            "conversation": _conversation_with_memory,
            "car_info": car_info.activate,
            "web_search": web_search.run_web_search,
        },
    )


def main() -> None:
    """Start the assistant with the shared application context."""

    global logger
    context = get_app_context()
    logger = context.logger
    logger.info("Initialising RICO...")

    start_ui_server()
    launch_ui()

    rico_app = RicoApp(context)
    wake_engine = WakeWordEngine()

    logger.info("RICO is online. Awaiting your command, Sir.")

    while True:
        try:
            if not wake_engine.wait_for_wakeword():
                logger.info("Wakeword listener stopped. Shutting down.")
                break

            logger.info("Wakeword detected. Entering conversation mode...")
            clear_conversation_history()
            _run_conversation_loop(
                rico_app=rico_app,
                context=context,
                silence_timeout=20.0,
            )
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Exiting gracefully.")
            break
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Unexpected error: %s", exc)
            context.tts_engine.speak(
                "Apologies Sir, an error occurred but I remain attentive."
            )

    logger.info("RICO has powered down.")


def _run_conversation_loop(
    rico_app: RicoApp,
    context: AppContext,
    silence_timeout: float,
) -> None:
    """Maintain an active conversation until an exit condition is met."""

    while True:
        send_listening(True)
        transcription = context.stt_engine.transcribe(timeout=silence_timeout)
        if isinstance(transcription, TranscriptionResult):
            result = transcription
        else:  # pragma: no cover - defensive for legacy return
            result = TranscriptionResult(text=str(transcription), timed_out=False)

        if result.timed_out:
            logger.info(
                "Silence timeout reached after %.0f seconds; exiting conversation mode.",
                silence_timeout,
            )
            context.tts_engine.speak("Very well, Sir.")
            send_listening(False)
            break

        text = result.text.strip()
        logger.info("Transcription: %s", text)
        send_transcription(text)

        if not text:
            logger.warning("No speech detected.")
            context.tts_engine.speak("I am terribly sorry Sir, I did not catch that.")
            continue

        send_thinking(0.85)
        interaction_result = rico_app.handle_text(text, source="cli")
        if interaction_result.metadata.get("exit"):
            logger.info("Exit phrase detected; ending conversation mode.")
            context.tts_engine.speak("Very well, Sir.")
            send_listening(False)
            break

        metadata = interaction_result.metadata or {}
        styled_reply = interaction_result.reply or ""
        response = metadata.get("raw_response")
        memory_result = metadata.get("memory_result")
        suggested_memory = metadata.get("suggested_memory")
        should_write_memory = metadata.get("should_write_memory")

        logger.info("Skill response: %s", response)
        send_thinking(0.0)
        send_reply(styled_reply)
        context.tts_engine.speak(styled_reply)

        if memory_result is True:
            logger.info("Memory saved.")
        elif memory_result == "ask" and suggested_memory:
            context.tts_engine.speak("Shall I remember that, Sir?")
            send_listening(True)
            confirmation = context.stt_engine.transcribe(timeout=silence_timeout)
            send_listening(False)
            if isinstance(confirmation, TranscriptionResult):
                confirmation_text = confirmation.text
            else:  # pragma: no cover - legacy behaviour
                confirmation_text = str(confirmation)
            if confirmation_text:
                lowered_confirmation = confirmation_text.strip().lower()
                if lowered_confirmation.startswith("y"):
                    final_result = process_memory_suggestion(
                        {
                            "should_write_memory": "yes",
                            "memory_to_write": suggested_memory,
                        }
                    )
                    if final_result:
                        logger.info("Memory saved.")

    try:
        clear_conversation_history()
    except Exception as exc:
        logger.error("Failed to clear conversation history: %s", exc)
        

if __name__ == "__main__":
    main()
