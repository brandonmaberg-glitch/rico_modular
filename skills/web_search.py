"""Web search skill using DuckDuckGo search API."""
from __future__ import annotations

from typing import List

try:
    from duckduckgo_search import DDGS
except Exception:  # pragma: no cover - optional dependency
    DDGS = None  # type: ignore


def _perform_search(query: str) -> List[str]:
    if not DDGS:
        return ["Web search module unavailable in this environment."]

    with DDGS() as ddgs:  # type: ignore[call-arg]
        results = ddgs.text(query, max_results=3)
    summaries = [f"{item['title']}: {item['href']}" for item in results]
    return summaries or ["No results at present, Sir."]


def activate(text: str) -> str:
    """Search the web and summarize top findings."""

    query = text or "current automotive technology"
    summaries = _perform_search(query)
    joined = '; '.join(summaries)
    return f"Sir, here is what the web whispers: {joined}"
