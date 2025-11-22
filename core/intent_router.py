"""LLM-based intent routing for choosing the best skill."""
from __future__ import annotations

import json
import logging
import os
from typing import Mapping, Sequence

from openai import OpenAI

logger = logging.getLogger("RICO")

_CLIENT: OpenAI | None = None
_DEFAULT_MODEL = "gpt-4.1-mini"
_SYSTEM_PROMPT = (
    "You are an intent router that selects the best skill for the user's request."
    " Choose only from the provided skills, and respond with JSON containing"
    " a single key 'skill' whose value is one of the given skill names."
)


def _get_client() -> OpenAI | None:
    """Return a cached OpenAI client when an API key is available."""

    global _CLIENT  # pylint: disable=global-statement

    if _CLIENT is not None:
        return _CLIENT

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    _CLIENT = OpenAI(api_key=api_key)
    return _CLIENT


def select_skill(
    user_text: str, skills: Sequence[Mapping[str, str]], model: str = _DEFAULT_MODEL
) -> str:
    """Return the name of the most appropriate skill for the given input.

    Args:
        user_text: The user's request.
        skills: A sequence of mappings containing ``name`` and ``description`` keys.
        model: The OpenAI model to use for selection. Defaults to ``gpt-4.1-mini``.

    Returns:
        The ``name`` of the chosen skill. If no OpenAI API key is configured or the
        model call fails, the function falls back to the first provided skill.

    Raises:
        ValueError: If ``skills`` is empty.
    """

    if not skills:
        raise ValueError("At least one skill must be provided for routing.")

    fallback_skill = skills[0]["name"]
    allowed_names = {skill["name"] for skill in skills}
    formatted_skills = "\n".join(
        f"- {skill['name']}: {skill.get('description', '').strip()}" for skill in skills
    )

    client = _get_client()
    if not client:
        logger.warning("Skill routing unavailable; defaulting to the first skill.")
        return fallback_skill

    try:
        completion = client.chat.completions.create(
            model=model,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "User request:\n"
                        f"{user_text}\n\n"
                        "Available skills:\n"
                        f"{formatted_skills}\n\n"
                        "Respond with JSON like {\"skill\": \"<name>\"}."
                    ),
                },
            ],
            temperature=0,
        )
        content = completion.choices[0].message.content if completion.choices else None
        if not content:
            raise ValueError("No content returned from skill router.")

        parsed = json.loads(content)
        chosen_skill = str(parsed.get("skill", "")).strip()

        if chosen_skill in allowed_names:
            return chosen_skill

        logger.warning(
            "Skill router returned unknown skill '%s'; defaulting to the first skill.",
            chosen_skill,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.error("Skill routing failed: %s", exc)

    return fallback_skill


__all__ = ["select_skill"]
