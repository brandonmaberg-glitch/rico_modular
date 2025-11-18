"""Live web search skill backed by OpenAI's native web-search tool."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger("RICO")

_client: Optional[OpenAI] = None

_STYLE_PROMPT = (
    "You are RICO, an impeccably polite British butler. Provide concise, cited "
    "intelligence from the live web and avoid speculation."
)


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


def _format_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert chat-style messages into the Responses API format."""

    formatted: List[Dict[str, Any]] = []
    for message in messages:
        content = message.get("content")
        if not content:
            continue
        formatted.append(
            {
                "role": message["role"],
                "content": [{"type": "input_text", "text": str(content)}],
            }
        )
    return formatted


def _extract_text(response: Any) -> str:
    """Return the concatenated text chunks from a Responses API result."""

    chunks: List[str] = []
    for item in getattr(response, "output", []) or []:
        if getattr(item, "type", None) != "message":
            continue
        for part in getattr(item, "content", []) or []:
            if getattr(part, "type", None) == "output_text":
                text = getattr(part, "text", "")
                if text:
                    chunks.append(text)
    return "\n".join(chunks).strip()


def run_web_search(query: str) -> str:
    """Use OpenAI's native web search to answer live queries."""

    client = _get_client()
    if not client:
        return "My apologies Sir, but the web search apparatus lacks its credentials."

    base_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": _STYLE_PROMPT},
        {
            "role": "user",
            "content": (
                "Search the live web and deliver a brief butler-style reply to this request: "
                f"{query}"
            ),
        },
    ]

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=_format_messages(base_messages),
            tools=[{"type": "web_search"}],
            tool_choice="auto",
        )
        final_message = _extract_text(response)

        if not final_message:
            raise ValueError("OpenAI returned no content for web search.")

        return final_message
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Web search failed: %s", exc)
        return "Sorry Sir, I could not retrieve the requested web intelligence."


__all__ = ["run_web_search"]
