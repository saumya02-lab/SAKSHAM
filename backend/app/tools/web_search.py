import asyncio
import logging

logger = logging.getLogger(__name__)

SEARCH_TIMEOUT_SECONDS = 15


def _search_sync(query: str, num_results: int) -> list[dict]:
    """Blocking DuckDuckGo search. Must be run in a worker thread."""
    from duckduckgo_search import DDGS

    with DDGS() as ddgs:
        results = list(ddgs.text(query, max_results=num_results))

    return [
        {
            "title": r.get("title", ""),
            "url": r.get("href", r.get("link", "")),
            "snippet": r.get("body", r.get("snippet", "")),
        }
        for r in results
    ]


async def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo and return results.

    Runs the blocking client on a worker thread so it cannot stall the
    event loop and starve other in-flight SSE streams.
    """
    try:
        return await asyncio.wait_for(
            asyncio.to_thread(_search_sync, query, num_results),
            timeout=SEARCH_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning(f"Web search timed out after {SEARCH_TIMEOUT_SECONDS}s: {query}")
        return []
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return []
