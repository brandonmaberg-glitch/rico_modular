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
    if not message:
        return ""

    parts = []
    output = getattr(message, "output", None) or []
    for entry in output:
        content = entry.get("content", []) if isinstance(entry, dict) else getattr(entry, "content", [])
        if not content:
            continue
        for block in content:
            if isinstance(block, dict):
                text = block.get("text") or block.get("output_text")
                if text:
                    parts.append(text)
            elif getattr(block, "text", None):
                parts.append(block.text)

    if not parts:
        for fallback_attr in ("output_text", "output_string"):
            fallback_text = getattr(message, fallback_attr, None)
            if fallback_text:
                parts.append(fallback_text)
                break

    return "\n".join(parts).strip()


def _run_search(client: OpenAI, query: str) -> str:
    """Execute the web search tool and collapse to 1-3 sentences."""

    instruction = (
        f"{_SYSTEM_PROMPT}\npersona:{_PERSONA_ID}\n{_PERSONA_TEXT}\n"
        "As a courteous British butler, search the web for the user's request and"
        " reply in 1 to 3 concise sentences, no more than 350 characters."
    )

    response = client.responses.create(
        model="gpt-4.1",
        input=f"{instruction}\nQuery: {query}",
        web_search={"bing_query": [{"q": query}], "n_tokens": 2048},
    )

    text = _extract_text(response)
    if not text:
        return "Sir, the web was oddly silent."

    short = text.replace("\n", " ").strip()
    sentences = [part.strip() for part in short.split(". ") if part.strip()]
    limited_sentences = sentences[:3]

    while len(". ".join(limited_sentences)) > 350 and len(limited_sentences) > 1:
        limited_sentences.pop()

    limited = ". ".join(limited_sentences).strip()
    if not limited:
        return "Sir, the web was oddly silent."
    if limited and not limited.endswith(('.', '!', '?')):
        limited += "."

    if len(limited) > 350:
        limited = limited[:350].rstrip()
    return limited


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
