"""Zero-cost web search discovery for ATS source URLs."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from urllib.parse import parse_qs, quote_plus, unquote, urlsplit

import httpx
from bs4 import BeautifulSoup

from job_crawler.discovery.queries import DEFAULT_WEB_DISCOVERY_QUERIES
from job_crawler.discovery.sources import DiscoveredSource, extract_sources_from_urls

SearchFetcher = Callable[..., list[str]]


def discover_sources_from_web_search(
    *,
    queries: Iterable[str] = DEFAULT_WEB_DISCOVERY_QUERIES,
    max_queries: int = 20,
    results_per_query: int = 8,
    fetcher: SearchFetcher | None = None,
) -> list[DiscoveredSource]:
    """Run bounded web searches and extract supported ATS sources."""
    search = fetcher or fetch_search_result_urls
    discovered: dict[tuple[str, str], DiscoveredSource] = {}
    for query in list(queries)[:max_queries]:
        urls = search(query=query, limit=results_per_query)
        for source in extract_sources_from_urls(urls, discovered_from=f"web search: {query}"):
            discovered.setdefault((source.source_type, source.slug), source)
    return list(discovered.values())


def fetch_search_result_urls(*, query: str, limit: int = 8) -> list[str]:
    """Fetch result URLs from Google, falling back to DuckDuckGo HTML."""
    urls = _fetch_google_result_urls(query=query, limit=limit)
    if urls:
        return urls[:limit]
    return _fetch_duckduckgo_result_urls(query=query, limit=limit)


def _fetch_google_result_urls(*, query: str, limit: int) -> list[str]:
    response = httpx.get(
        "https://www.google.com/search",
        params={"q": query, "num": str(limit), "hl": "en"},
        headers={"User-Agent": "Mozilla/5.0 job-crawler/0.1"},
        follow_redirects=True,
        timeout=15,
    )
    response.raise_for_status()
    return _parse_google_result_urls(response.text, limit=limit)


def _fetch_duckduckgo_result_urls(*, query: str, limit: int) -> list[str]:
    response = httpx.get(
        f"https://duckduckgo.com/html/?q={quote_plus(query)}",
        headers={"User-Agent": "Mozilla/5.0 job-crawler/0.1"},
        follow_redirects=True,
        timeout=15,
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
