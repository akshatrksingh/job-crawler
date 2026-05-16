"""Web search discovery for ATS source URLs."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlsplit

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from job_crawler.discovery.queries import DEFAULT_WEB_DISCOVERY_QUERIES
from job_crawler.discovery.sources import DiscoveredSource, extract_sources_from_urls

SearchFetcher = Callable[..., list[str]]
TAVILY_SEARCH_URL = "https://api.tavily.com/search"
SEARCH_TIMEOUT = httpx.Timeout(8.0, connect=3.0, read=8.0, write=5.0, pool=3.0)


def discover_sources_from_web_search(
    *,
    queries: Iterable[str] = DEFAULT_WEB_DISCOVERY_QUERIES,
    max_queries: int = 20,
    results_per_query: int = 8,
    max_seconds: int = 120,
    use_tavily: bool = False,
    fetcher: SearchFetcher | None = None,
) -> list[DiscoveredSource]:
    """Run bounded web searches and extract supported ATS sources."""
    search = fetcher or fetch_search_result_urls
    discovered: dict[tuple[str, str], DiscoveredSource] = {}
    started = time.monotonic()
    for query in list(queries)[:max_queries]:
        if time.monotonic() - started >= max_seconds:
            break
        try:
            urls = search(query=query, limit=results_per_query, use_tavily=use_tavily)
        except httpx.HTTPError as exc:
            if _is_blocking_tavily_error(exc):
                raise
            continue
        for source in extract_sources_from_urls(urls, discovered_from=f"web search: {query}"):
            discovered.setdefault((source.source_type, source.slug), source)
    return list(discovered.values())


def fetch_search_result_urls(
    *,
    query: str,
    limit: int = 8,
    use_tavily: bool = False,
) -> list[str]:
    """Fetch result URLs using Tavily only when explicitly enabled."""
    load_dotenv(Path.cwd() / ".env")
    tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if use_tavily and tavily_api_key:
        urls = _fetch_tavily_result_urls(
            query=query,
            limit=limit,
            api_key=tavily_api_key,
        )
        if urls:
            return urls[:limit]
    return _fetch_duckduckgo_result_urls(query=query, limit=limit)


def _fetch_tavily_result_urls(*, query: str, limit: int, api_key: str) -> list[str]:
    response = httpx.post(
        TAVILY_SEARCH_URL,
        json={
            "query": query,
            "search_depth": "basic",
            "max_results": min(limit, 20),
            "include_answer": False,
            "include_raw_content": False,
            "include_images": False,
            "country": "united states",
        },
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        timeout=SEARCH_TIMEOUT,
    )
    response.raise_for_status()
    return _parse_tavily_result_urls(response.json(), limit=limit)


def _fetch_duckduckgo_result_urls(*, query: str, limit: int) -> list[str]:
    response = httpx.get(
        f"https://duckduckgo.com/html/?q={quote_plus(query)}",
        headers={"User-Agent": "Mozilla/5.0 job-crawler/0.1"},
        follow_redirects=True,
        timeout=SEARCH_TIMEOUT,
    )
    response.raise_for_status()
    return _parse_duckduckgo_result_urls(response.text, limit=limit)


def _parse_google_result_urls(html: str, *, limit: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        url = _unwrap_google_url(href)
        if url and _is_supported_result_url(url) and url not in urls:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


def _parse_tavily_result_urls(payload: dict, *, limit: int) -> list[str]:
    urls: list[str] = []
    for item in payload.get("results", []):
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or "")
        if url and _is_supported_result_url(url) and url not in urls:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


def _parse_duckduckgo_result_urls(html: str, *, limit: int) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        url = _unwrap_duckduckgo_url(href)
        if url and _is_supported_result_url(url) and url not in urls:
            urls.append(url)
        if len(urls) >= limit:
            break
    return urls


def _unwrap_google_url(href: str) -> str | None:
    if href.startswith("/url?"):
        values = parse_qs(urlsplit(href).query).get("q")
        return values[0] if values else None
    return href if href.startswith("http") else None


def _unwrap_duckduckgo_url(href: str) -> str | None:
    values = parse_qs(urlsplit(href).query).get("uddg")
    if values:
        return unquote(values[0])
    return href if href.startswith("http") else None


def _is_supported_result_url(url: str) -> bool:
    hostname = urlsplit(url).hostname or ""
    return hostname in {
        "jobs.ashbyhq.com",
        "boards.greenhouse.io",
        "job-boards.greenhouse.io",
        "jobs.lever.co",
    }


def _is_blocking_tavily_error(exc: httpx.HTTPError) -> bool:
    request = getattr(exc, "request", None)
    if request is None:
        return False
    if request.url.host != "api.tavily.com":
        return False
    if not isinstance(exc, httpx.HTTPStatusError):
        return False
    return exc.response.status_code in {401, 403, 429}
