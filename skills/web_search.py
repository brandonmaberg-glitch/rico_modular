"""Live web search skill backed by OpenAI's native web-search tool."""
from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger("RICO")

_client: Optional[OpenAI] = None

_STYLE_PROMPT = (
    "You are RICO, an impeccably polite British butler. Provide concise, cited "
    "intelligence from the live web and avoid speculation."
)

_REFINE_PROMPT = (
    "You are RICO, a succinct British butler. Rewrite the provided tool output "
    "into 2-3 sentences no longer than 350 characters. Avoid raw URLs, "
    "debug-style output, or trailing half-sentences. Maintain citations if "
    "supplied and keep the tone poised yet warm."
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


def _clean_urls(text: str) -> str:
    """Remove bare URLs from the response text."""

    return re.sub(r"https?://\S+", "", text)


def _trim_sentences(text: str, limit: int = 350) -> str:
    """Limit text to whole sentences within the character budget."""

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    kept: List[str] = []
    total = 0

    for sentence in sentences:
        if not sentence:
            continue
        potential = total + len(sentence)
        if kept:
            potential += 1  # space
        if potential > limit:
            break
        kept.append(sentence)
        total = potential
        if len(kept) == 3:
            break

    return " ".join(kept).strip()


def _detail_requested(query: str) -> bool:
    """Return True if the user explicitly wants extended detail."""

    query_lower = query.lower()
    keywords = (
        "detailed",
        "in-depth",
        "comprehensive",
        "elaborate",
        "full report",
        "long form",
        "thorough",
    )
    return any(keyword in query_lower for keyword in keywords)


def _refine_response(
    *, client: OpenAI, raw_text: str, query: str, allow_expanded: bool
) -> str:
    """Polish the raw model output into a brief butler-style reply."""

    if not raw_text:
        return ""

    constraints = (
        "Summarise in exactly 2-3 complete sentences and no more than 350 "
        "characters."
        if not allow_expanded
        else "Summarise in 2-3 polished sentences (max 350 characters) while "
        "respecting any explicit request for detail."
    )

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": _REFINE_PROMPT},
        {
            "role": "user",
            "content": (
                f"{constraints}\nPrompt: {query}\n\nResult to refine:\n{raw_text}"
            ),
        },
    ]

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=_format_messages(messages),
        )
        refined = _extract_text(response)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Response refinement failed: %s", exc)
        refined = raw_text

    refined = _clean_urls(refined).strip()
    if not refined:
        refined = _clean_urls(raw_text).strip()

    refined = _trim_sentences(refined, limit=350)
    if not refined:
        refined = _trim_sentences(_clean_urls(raw_text), limit=350)

    return refined


def run_web_search(query: str) -> str:
    """Use OpenAI's native web search to answer live queries."""

    client = _get_client()
    if not client:
        return "My apologies Sir, but the web search apparatus lacks its credentials."

    detailed = _detail_requested(query)

    base_messages: List[Dict[str, Any]] = [
        {"role": "system", "content": _STYLE_PROMPT},
        {
            "role": "user",
            "content": (
                "Consult the live web and respond as RICO the butler. "
                "Keep the answer concise, elegant, and cite sources. "
                "Never dump raw search snippets. "
                f"Query: {query}"
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
            return (
                "Sir, I regret the search yielded nothing useful. Perhaps try asking "
                "in another manner?"
            )

        return _refine_response(
            client=client, raw_text=final_message, query=query, allow_expanded=detailed
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Web search failed: %s", exc)
        return "Sorry Sir, I could not retrieve the requested web intelligence."


__all__ = ["run_web_search"]
