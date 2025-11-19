"""Live web search skill backed by OpenAI's native web-search tool."""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from openai import OpenAI

from memory.manager import load_persona, load_system_prompt

logger = logging.getLogger("RICO")

_client: Optional[OpenAI] = None
_PERSONA_ID = "rico_butler_v3"
_SYSTEM_PROMPT = load_system_prompt()
_PERSONA_TEXT = load_persona(_PERSONA_ID)


def _get_client() -> Optional[OpenAI]:
    """Return a cached OpenAI client if credentials are available."""

    global _client  # pylint: disable=global-statement

    if _client is not None:
        return _client

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    _client = OpenAI(api_key=api_key)
    return _client


def _extract_text(message: Any) -> str:
    if not message or not getattr(message, "content", None):
        return ""
    parts = []
    for item in message.content:
        if item.get("type") == "text" and item.get("text"):
            parts.append(item["text"])
    return "\n".join(parts).strip()


def _run_search(client: OpenAI, query: str) -> str:
    """Execute the web search tool and collapse to 1-3 sentences."""

    system = f"{_SYSTEM_PROMPT}\npersona:{_PERSONA_ID}"
    search_instruction = (
        "Fetch current information via the web_search function. Answer as a British"
        " butler in no more than 3 short sentences. Keep it crisp and avoid fluff."
    )
    chat = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "system", "content": _PERSONA_TEXT},
            {"role": "user", "content": f"{search_instruction}\nQuery: {query}"},
        ],
        tools=[{"type": "web_search"}],
        tool_choice="auto",
        temperature=0,
    )

    message = chat.choices[0].message if chat.choices else None
    if not message:
        return "Sir, I regret the search yielded nothing useful."

    # If the model returns tool calls, let it finish the call and summarise.
    if getattr(message, "tool_calls", None):
        follow_up = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "system", "content": _PERSONA_TEXT},
                {"role": "assistant", "tool_calls": message.tool_calls},
            ],
            tools=[{"type": "web_search"}],
            tool_choice="none",
            temperature=0,
        )
        message = follow_up.choices[0].message if follow_up.choices else message

    text = _extract_text(message)
    if not text:
        return "Sir, the web was oddly silent."

    short = text.replace("\n", " ").strip()
    sentences = short.split(". ")
    limited = ". ".join(sentences[:3]).strip()
    if not limited.endswith(('.', '!', '?')):
        limited += "."
    return limited[:400].strip()


def run_web_search(query: str) -> str:
    """Use OpenAI's native web search to answer live queries."""

    client = _get_client()
    if not client:
        return "My apologies Sir, but the web search apparatus lacks its credentials."

    try:
        return _run_search(client, query)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Web search failed: %s", exc)
        return "Sorry Sir, I could not retrieve the requested web intelligence."


__all__ = ["run_web_search"]
