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


def style_reply_with_rico(user_text: str, raw_reply: str) -> str:
    """
    Take a raw skill reply and lightly rewrite it in RICO's butler persona,
    using recent conversation as context. Uses a small model to keep costs low.
    """

    if not raw_reply or not conversation._client:
        return raw_reply

    # Pull in recent conversation history for extra context, but keep it short.
    recent_turns = get_conversation_history(max_turns=6)
    history_snippets = []
    for turn in recent_turns:
        u = turn.get("user")
        a = turn.get("assistant")
        if u:
            history_snippets.append(f"User: {u}")
        if a:
            history_snippets.append(f"RICO: {a}")
    history_text = "\n".join(history_snippets) if history_snippets else ""

    system_text = (
        f"{conversation._SYSTEM_PROMPT}\npersona:{conversation._PERSONA_ID}\n\n"
        "You are RICO, a polite, concise British butler-style assistant. "
        "Rewrite the given TOOL RESPONSE into a natural spoken reply that you would say to the user. "
        "Keep it short, conversational, and in first person. DO NOT add new facts – just rephrase.\n"
    )

    if history_text:
        system_text += (
            "\nRelevant recent conversation:\n"
            f"{history_text}\n"
        )

    # Use a small model for styling to save tokens
    try:
        resp = conversation._client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {
                    "role": "system",
                    "content": [
                        {"type": "input_text", "text": system_text},
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "User just said:\n"
                                f"{user_text}\n\n"
                                "TOOL RESPONSE (what the skill returned):\n"
                                f"{raw_reply}\n\n"
                                "Now rewrite that TOOL RESPONSE as your spoken reply."
                            ),
                        }
                    ],
                },
            ],
            temperature=0.3,
        )

        # Simple text extraction from Responses API output
        response_dict = resp.model_dump()
        outputs = response_dict.get("output") or []
        for item in outputs:
            if item.get("type") == "message":
                for block in item.get("content", []) or []:
                    text = block.get("text")
                    if text:
                        return text

        # Fallback
        return raw_reply
    except Exception as exc:
        conversation.logger.error("Failed to style reply with RICO persona: %s", exc)
        return raw_reply


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
    """Start the assistant."""
    global logger
    config = AppConfig.load()
    logger = setup_logger()
    logger.info("Initialising RICO...")

    start_ui_server()
    launch_ui()

    wake_engine = WakeWordEngine()
    stt_engine = SpeechToTextEngine(config.openai_api_key)
    tts_engine = Speaker(
        openai_api_key=config.openai_api_key,
        elevenlabs_api_key=config.elevenlabs_api_key,
        voice_id=config.elevenlabs_voice_id,
    )
    skill_registry, skills = build_skill_registry(config)
    router = CommandRouter(skills)

    logger.info("RICO is online. Awaiting your command, Sir.")

    while True:
        try:
            if not wake_engine.wait_for_wakeword():
                logger.info("Wakeword listener stopped. Shutting down.")
                break

            logger.info("Wakeword detected. Entering conversation mode...")
            clear_conversation_history()
            _run_conversation_loop(
                stt_engine=stt_engine,
                tts_engine=tts_engine,
                router=router,
                silence_timeout=20.0,
                skill_registry=skill_registry,
            )
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Exiting gracefully.")
            break
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Unexpected error: %s", exc)
            tts_engine.speak(
                "Apologies Sir, an error occurred but I remain attentive."
            )

    logger.info("RICO has powered down.")


_EXIT_PHRASES = ["rico, stop listening", "that's all, rico", "that’s all, rico"]


def _should_exit(text: str) -> bool:
    lowered = text.strip().lower()
    return any(phrase in lowered for phrase in _EXIT_PHRASES)


def _normalise_command(text: str) -> str:
    """Lowercase and strip trailing punctuation for command matching."""

    return text.strip().lower().rstrip(".,?!")


def is_vague(text: str) -> bool:
    """Return True for short acknowledgements or ambiguous replies."""

    lowered = text.strip().lower()
    if not lowered:
        return True

    acknowledgement_phrases = {
        "yes",
        "no",
        "yeah",
        "nope",
        "ok",
        "okay",
        "sure",
        "probably",
        "maybe",
        "alright",
        "alright perfect",
        "that's good",
        "that is good",
        "what about now",
        "i guess that means no",
    }
    if lowered in acknowledgement_phrases:
        return True

    if len(lowered) <= 50:
        follow_up_starts = (
            "and ",
            "what about",
            "how about",
            "what if",
            "and tomorrow",
            "and today",
        )
        if any(lowered.startswith(prefix) for prefix in follow_up_starts):
            return True

        follow_up_keywords = (
            "tomorrow",
            "later",
            "tonight",
            "today",
            "again",
            "umbrella",
            "coat",
            "jacket",
        )
        if any(keyword in lowered for keyword in follow_up_keywords):
            return True

    if len(lowered) < 10:
        return True

    short_tokens = {"yup", "yep", "uh-huh", "k", "cool", "fine"}
    return lowered.rstrip(".?!") in short_tokens


def _handle_voice_command(command: str, tts_engine: Speaker) -> bool:
    """Switch TTS provider based on the voice command provided."""

    if "eleven" in command:
        if tts_engine.switch_to_elevenlabs():
            tts_engine.speak("Switching to your ElevenLabs voice, Sir.")
        else:
            tts_engine.speak("ElevenLabs voice is unavailable, Sir.")
        return True

    if "openai" in command:
        if tts_engine.switch_to_openai():
            tts_engine.speak("Reverting to the OpenAI voice, Sir.")
        else:
            tts_engine.speak("OpenAI voice is unavailable, Sir.")
        return True

    if command == "voice":
        if tts_engine.provider == "elevenlabs":
            return _handle_voice_command("voice openai", tts_engine)
        return _handle_voice_command("voice elevenlabs", tts_engine)

    return False


def _run_conversation_loop(
    stt_engine: SpeechToTextEngine,
    tts_engine: Speaker,
    router: CommandRouter,
    silence_timeout: float,
    skill_registry: SkillRegistry | None = None,
) -> None:
    """Maintain an active conversation until an exit condition is met."""

    interaction_count = 0
    while True:
        send_listening(True)
        transcription = stt_engine.transcribe(timeout=silence_timeout)
        if isinstance(transcription, TranscriptionResult):
            result = transcription
        else:  # pragma: no cover - defensive for legacy return
            result = TranscriptionResult(text=str(transcription), timed_out=False)

        interaction_count += 1
        if result.timed_out:
            logger.info(
                "Silence timeout reached after %.0f seconds; exiting conversation mode.",
                silence_timeout,
            )
            tts_engine.speak("Very well, Sir.")
            send_listening(False)
            break

        text = result.text.strip()
        logger.info("Transcription: %s", text)
        send_transcription(text)

        if not text:
            logger.warning("No speech detected.")
            tts_engine.speak("I am terribly sorry Sir, I did not catch that.")
            continue

        normalised = _normalise_command(text)

        if normalised.startswith("voice"):
            if _handle_voice_command(normalised, tts_engine):
                continue

        if _should_exit(text):
            logger.info("Exit phrase detected; ending conversation mode.")
            tts_engine.speak("Very well, Sir.")
            send_listening(False)
            break

        user_text = text

        send_thinking(0.85)

        response = None
        selected_skill = None
        if skill_registry:
            try:
                if is_vague(text):
                    last_skill = get_context("last_skill")
                    if last_skill:
                        selected_skill = skill_registry.get(last_skill)
                        if selected_skill:
                            query_text = text
                            if last_skill == "weather":
                                location_hint = get_context("last_location")
                                if location_hint:
                                    query_text = location_hint
                                    set_context("last_location", location_hint, ttl_seconds=60)
                                extractor = getattr(selected_skill, "_extract_location", None)
                                if callable(extractor):
                                    location_for_context = extractor(query_text)
                                    if location_for_context:
                                        set_context(
                                            "last_location", location_for_context, ttl_seconds=60
                                        )
                            response = selected_skill.run(query_text)
                            set_context("last_skill", last_skill, ttl_seconds=60)
                if response is None:
                    available_skills = [
                        {
                            "name": skill.name or skill.__name__,
                            "description": getattr(skill, "description", ""),
                        }
                        for skill in skill_registry.all()
                    ]
                    if available_skills:
                        skill_name = select_skill(text, available_skills)
                        selected_skill = skill_registry.get(skill_name)
                        if selected_skill:
                            set_context("last_skill", skill_name, ttl_seconds=60)
                            if skill_name == "weather":
                                extractor = getattr(selected_skill, "_extract_location", None)
                                if callable(extractor):
                                    location_for_context = extractor(text)
                                    if location_for_context:
                                        set_context(
                                            "last_location", location_for_context, ttl_seconds=60
                                        )
                            response = selected_skill.run(text)
                        else:
                            logger.info(
                                "No matching skill found for '%s'; falling back to conversation.",
                                skill_name,
                            )
                            response = router.skills.get("conversation", router.route)(text)
            except Exception as exc:  # pragma: no cover - defensive fallback
                logger.exception("Skill selection or execution failed: %s", exc)

        if response is None:
            response = router.route(text)

        if interaction_count % 10 == 0:
            periodic_memory_maintenance()
            logger.info("Memory maintenance executed.")
        suggested_memory = None
        should_write_memory = None
        memory_result = None
        if isinstance(response, dict):
            suggested_memory = response.get("memory_to_write")
            should_write_memory = response.get("should_write_memory")
            # Normalise boolean-like values for memory decisions
            if should_write_memory in ("true", True, "True", "YES", "Yes"):
                should_write_memory = "yes"
            if should_write_memory in ("false", False, "False", "NO", "No"):
                should_write_memory = "no"
            memory_result = process_memory_suggestion(
                {
                    "should_write_memory": should_write_memory,
                    "memory_to_write": suggested_memory,
                }
            )
        if isinstance(response, dict):
            response_text = response.get("response") or response.get("reply") or str(response)
        else:
            response_text = str(response)

        from skills.conversation import ConversationSkill

        is_conversation_skill = isinstance(selected_skill, ConversationSkill)
        if not is_conversation_skill and isinstance(response, dict):
            if {"memory_to_write", "should_write_memory"}.intersection(response.keys()):
                is_conversation_skill = True

        if is_conversation_skill:
            styled_reply = response_text
        else:
            styled_reply = style_reply_with_rico(user_text, response_text)

        logger.info("Skill response: %s", response)
        send_thinking(0.0)
        send_reply(styled_reply)
        tts_engine.speak(styled_reply)
        try:
            append_conversation_turn(user_text=user_text, assistant_text=styled_reply)
        except Exception as exc:
            logger.warning("Failed to append conversation history: %s", exc)
        if memory_result is True:
            logger.info("Memory saved.")
        elif memory_result == "ask" and suggested_memory:
            tts_engine.speak("Shall I remember that, Sir?")
            send_listening(True)
            confirmation = stt_engine.transcribe(timeout=silence_timeout)
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
