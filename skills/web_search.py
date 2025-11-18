"""Live web search skill backed by OpenAI tool-calling."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from duckduckgo_search import DDGS
from openai import OpenAI

logger = logging.getLogger("RICO")

_api_key = os.getenv("OPENAI_API_KEY")
_client: Optional[OpenAI] = OpenAI(api_key=_api_key) if _api_key else None

_WEB_SEARCH_TOOL = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Look up recent, factual information from the live web.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search phrase including relevant entities and time scope",
                }
            },
            "required": ["query"],
        },
    },
}

_STYLE_PROMPT = (
    "You are RICO, a precise and unflappable British butler. Cite newsworthiness,"
    " keep conclusions cautious, and stick to verified web findings."
)


def _collect_search_results(query: str, limit: int = 6) -> str:
    """Fetch and format DuckDuckGo search snippets for the tool result."""
    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=limit))

    if not results:
        return "No documents located."

    snippets: List[str] = []
    for item in results:
        title = item.get("title") or item.get("heading") or "Result"
        body = item.get("body") or item.get("snippet") or ""
        href = item.get("href") or item.get("url") or ""
        snippets.append(f"{title}\nURL: {href}\nSummary: {body}")

    return "\n\n".join(snippets)


def _call_model(messages: List[Dict[str, Any]]):
    return _client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages,
        tools=[_WEB_SEARCH_TOOL],
        temperature=0.4,
    )


def run_web_search(query: str) -> str:
    """Use OpenAI tool-calling plus DuckDuckGo to answer live web queries."""
    if not _client:
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
        first_completion = _call_model(base_messages)
        choice = first_completion.choices[0].message

        if getattr(choice, "tool_calls", None):
            tool_call = choice.tool_calls[0]
            args = json.loads(tool_call.function.arguments or "{}")
            search_query = args.get("query") or query
            logger.info("Running DuckDuckGo search for: %s", search_query)
            search_payload = _collect_search_results(search_query)

            follow_up_messages = base_messages + [
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": search_payload,
                },
            ]

            final_completion = _call_model(follow_up_messages)
            final_message = final_completion.choices[0].message.content
        else:
            final_message = choice.content

        if not final_message:
            raise ValueError("OpenAI returned no content for web search.")

        return final_message.strip()

    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Web search failed: %s", exc)
        return "Sorry Sir, I could not retrieve the requested web intelligence."


__all__ = ["run_web_search"]
