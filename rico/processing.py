"""Core text interaction pipeline shared by CLI and web entrypoints."""

from __future__ import annotations

import logging

import conversation
from core.intent_router import select_skill
from core.skill_registry import SkillRegistry
from memory.memory_manager import (
    append_conversation_turn,
    get_conversation_history,
    get_context,
    periodic_memory_maintenance,
    process_memory_suggestion,
    set_context,
)
from router.command_router import CommandRouter

logger = logging.getLogger("RICO")


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
    except Exception as exc:  # pragma: no cover - defensive
        conversation.logger.error("Failed to style reply with RICO persona: %s", exc)
        return raw_reply


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


def handle_text_interaction(
    user_text: str,
    router: CommandRouter,
    skill_registry: SkillRegistry | None = None,
    interaction_count: int = 1,
) -> dict:
    """Route a single text input through the existing skill pipeline."""

    response = None
    selected_skill = None

    if skill_registry:
        try:
            if is_vague(user_text):
                last_skill = get_context("last_skill")
                if last_skill:
                    selected_skill = skill_registry.get(last_skill)
                    if selected_skill:
                        query_text = user_text
                        if last_skill == "weather":
                            location_hint = get_context("last_location")
                            if location_hint:
                                query_text = location_hint
                                set_context("last_location", location_hint, ttl_seconds=60)
                            extractor = getattr(selected_skill, "_extract_location", None)
                            if callable(extractor):
                                location_for_context = extractor(query_text)
                                if location_for_context:
                                    set_context("last_location", location_for_context, ttl_seconds=60)
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
                    skill_name = select_skill(user_text, available_skills)
                    selected_skill = skill_registry.get(skill_name)
                    if selected_skill:
                        set_context("last_skill", skill_name, ttl_seconds=60)
                        if skill_name == "weather":
                            extractor = getattr(selected_skill, "_extract_location", None)
                            if callable(extractor):
                                location_for_context = extractor(user_text)
                                if location_for_context:
                                    set_context(
                                        "last_location", location_for_context, ttl_seconds=60
                                    )
                        response = selected_skill.run(user_text)
                    else:
                        logger.info(
                            "No matching skill found for '%s'; falling back to conversation.",
                            skill_name,
                        )
                        response = router.skills.get("conversation", router.route)(
                            user_text
                        )
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("Skill selection or execution failed: %s", exc)

    if response is None:
        response = router.route(user_text)

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

    try:
        append_conversation_turn(user_text=user_text, assistant_text=styled_reply)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Failed to append conversation history: %s", exc)

    selected_skill_name = None
    if selected_skill:
        selected_skill_name = getattr(selected_skill, "name", None) or getattr(
            selected_skill, "__name__", None
        )

    metadata = {
        "raw_response": response,
        "selected_skill": selected_skill_name,
        "memory_result": memory_result,
        "suggested_memory": suggested_memory,
        "should_write_memory": should_write_memory,
    }

    return {"reply": styled_reply, "metadata": metadata}


__all__ = ["handle_text_interaction", "is_vague", "style_reply_with_rico"]
