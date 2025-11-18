"""Web search skill using DuckDuckGo."""
from __future__ import annotations

from typing import List

try:
    from duckduckgo_search import DDGS  # type: ignore
except Exception:  # pragma: no cover
    DDGS = None  # type: ignore


def activate(query: str, *, safe_search: bool = True) -> str:
    """Search the web for the given query."""
    if not DDGS:
        return "Apologies Sir, web search is temporarily unavailable."

    results: List[str] = []
    with DDGS() as ddgs:
        for result in ddgs.text(query, safesearch="on" if safe_search else "off", max_results=3):
            title = result.get("title", "result")
            href = result.get("href", "")
            snippet = result.get("body", "")
            results.append(f"{title}: {snippet} ({href})")

    if not results:
        return "Sir, no relevant articles were located."

    return "Sir, here is what the web yielded:\n- " + "\n- ".join(results)


__all__ = ["activate"]
