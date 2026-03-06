"""
Search Service — Python version, tương thích SearXNG API.

GET /search?q=query&format=json — trả về JSON với mảng results (url, title, content).
Dùng DuckDuckGo (duckduckgo-search) — free, không cần API key.
"""

import os
from typing import Any

from ddgs import DDGS
from fastapi import FastAPI, Query

app = FastAPI(
    title="Search Service (SearXNG-compatible)",
    version="2.0.0",
    description="Web search API — tương thích endpoint /search của SearXNG. Dùng DuckDuckGo.",
)

_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "10"))
_QUERY_TIMEOUT = float(os.getenv("SEARCH_TIMEOUT_SECONDS", "15"))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search")
def search(
    q: str = Query(..., min_length=1, description="Search query"),
    format: str = Query(default="json", description="Output format (json only)"),
) -> dict[str, Any]:
    """
    Tìm kiếm web — tương thích SearXNG API.
    Chatbot web_search gọi: GET /search?q=query&format=json
    """
    if format != "json":
        return {"query": q, "results": []}

    try:
        with DDGS() as ddgs:
            items = list(
                ddgs.text(q, max_results=_MAX_RESULTS, safesearch="moderate")
            )
    except Exception:
        return {"query": q, "results": []}

    results = []
    seen_urls: set[str] = set()
    for item in items:
        # duckduckgo_search trả về href, title, body
        url = (item.get("href") or item.get("url") or "").strip()
        if not url or not url.startswith("http"):
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = (item.get("title") or "").strip()
        content = (item.get("body") or item.get("content") or "").strip()
        results.append({
            "url": url,
            "title": title,
            "content": content,
        })

    return {"query": q, "results": results}
