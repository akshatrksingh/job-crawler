"""Public search-result leads for LinkedIn hiring posts.

This module only reads search result pages. It does not open LinkedIn, log in,
or automate LinkedIn itself.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from urllib.parse import parse_qs, quote_plus, unquote, urlsplit

import httpx
from bs4 import BeautifulSoup

from job_crawler.crawlers.base import JobPosting

LINKEDIN_POST_SOURCE = "linkedin_post_leads"

DEFAULT_LINKEDIN_POST_QUERIES = (
    'site:linkedin.com/posts "hiring" "founding ai engineer"',
    'site:linkedin.com/posts "hiring" "applied ai engineer"',
    'site:linkedin.com/posts "hiring" "machine learning engineer"',
    'site:linkedin.com/posts "hiring" "llm engineer"',
    'site:linkedin.com/posts "hiring" "generative ai engineer"',
    'site:linkedin.com/posts "hiring" "ai engineer" "startup"',
    'site:linkedin.com/posts "hiring" "software engineer" "ai"',
    'site:linkedin.com/posts "hiring" "backend engineer" "ai"',
    'site:linkedin.com/posts "hiring" "full stack engineer" "ai"',
    'site:linkedin.com/posts "hiring" "data scientist" "startup"',
    'site:linkedin.com/posts "0-3 YOE" "founding engineer"',
    'site:linkedin.com/posts "new grad" "software engineer" "startup"',
)

ROLE_HINTS = (
    "ai engineer",
    "applied ai",
    "machine learning",
    "ml engineer",
    "llm",
    "generative ai",
    "agent",
    "software engineer",
    "backend engineer",
    "full stack",
    "founding engineer",
    "data scientist",
    "applied scientist",
    "research engineer",
)

HIRING_HINTS = (
    "hiring",
    "we're hiring",
    "we are hiring",
    "is hiring",
    "looking for",
    "join",
    "role",
    "opening",
)

LOCATION_HINTS = (
    ("New York, NY", ("new york", "nyc")),
    ("San Francisco, CA", ("san francisco", "sf", "bay area")),
    ("Seattle, WA", ("seattle",)),
    ("Boston, MA", ("boston", "cambridge")),
    ("Austin, TX", ("austin",)),
    ("Los Angeles, CA", ("los angeles", " la ")),
    ("Chicago, IL", ("chicago",)),
    ("Denver, CO", ("denver",)),
    ("Washington, DC", ("washington dc", "washington, dc")),
    ("United States", ("united states", " usa ", " u.s.")),
    ("Remote", ("remote",)),
)


@dataclass(frozen=True)
class SearchResult:
    """A compact public search result."""

    url: str
    title: str
    snippet: str


SearchResultFetcher = Callable[..., list[SearchResult]]


def fetch_linkedin_post_leads(
    *,
    limit: int = 40,
    queries: Iterable[str] = DEFAULT_LINKEDIN_POST_QUERIES,
    results_per_query: int = 5,
    fetcher: SearchResultFetcher | None = None,
) -> list[JobPosting]:
    """Fetch public LinkedIn hiring-post leads from search results."""
    search = fetcher or fetch_linkedin_search_results
    leads: dict[str, JobPosting] = {}
    for query in queries:
        if len(leads) >= limit:
            break
        try:
            results = search(query=query, limit=results_per_query)
        except httpx.HTTPError:
            continue
        for result in results:
            if len(leads) >= limit:
                break
            if not _is_linkedin_post_url(result.url):
                continue
            if not _is_relevant_hiring_result(result):
                continue
            url = _canonicalize_url(result.url)
            leads.setdefault(url, _posting_from_result(result, url=url))
    return list(leads.values())


def fetch_linkedin_search_results(*, query: str, limit: int = 5) -> list[SearchResult]:
    """Fetch LinkedIn post search results through public search engines."""
    try:
        results = _fetch_google_results(query=query, limit=limit)
    except httpx.HTTPError:
        results = []
    if results:
        return results[:limit]
    try:
        return _fetch_duckduckgo_results(query=query, limit=limit)
    except httpx.HTTPError:
        return []


def parse_google_results(html: str, *, limit: int) -> list[SearchResult]:
    """Parse Google result HTML into compact search results."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []
    for anchor in soup.find_all("a", href=True):
        url = _unwrap_google_url(str(anchor["href"]))
        if not url or not _is_linkedin_post_url(url):
            continue
        title = anchor.get_text(" ", strip=True)
        if not title:
            title = "LinkedIn hiring post"
        snippet = _nearby_text(anchor)
        _append_unique_result(results, SearchResult(url=url, title=title, snippet=snippet), limit)
        if len(results) >= limit:
            break
    return results


def parse_duckduckgo_results(html: str, *, limit: int) -> list[SearchResult]:
    """Parse DuckDuckGo HTML results into compact search results."""
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []
    for result in soup.select(".result"):
        anchor = result.select_one("a.result__a[href]")
        if anchor is None:
            continue
        url = _unwrap_duckduckgo_url(str(anchor["href"]))
        if not url or not _is_linkedin_post_url(url):
            continue
        title = anchor.get_text(" ", strip=True) or "LinkedIn hiring post"
        snippet_node = result.select_one(".result__snippet")
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else ""
        _append_unique_result(results, SearchResult(url=url, title=title, snippet=snippet), limit)
        if len(results) >= limit:
            break
    return results


def _fetch_google_results(*, query: str, limit: int) -> list[SearchResult]:
    response = httpx.get(
        "https://www.google.com/search",
        params={"q": query, "num": str(limit), "hl": "en"},
        headers={"User-Agent": "Mozilla/5.0 job-crawler/0.1"},
        follow_redirects=True,
        timeout=15,
    )
    response.raise_for_status()
    return parse_google_results(response.text, limit=limit)


def _fetch_duckduckgo_results(*, query: str, limit: int) -> list[SearchResult]:
    response = httpx.get(
        f"https://duckduckgo.com/html/?q={quote_plus(query)}",
        headers={"User-Agent": "Mozilla/5.0 job-crawler/0.1"},
        follow_redirects=True,
        timeout=15,
    )
    response.raise_for_status()
    return parse_duckduckgo_results(response.text, limit=limit)


def _posting_from_result(result: SearchResult, *, url: str) -> JobPosting:
    title = _clean_title(result.title)
    return JobPosting(
        source=LINKEDIN_POST_SOURCE,
        source_id=hashlib.sha256(url.encode("utf-8")).hexdigest()[:16],
        company=_extract_company(title),
        title=title,
        location=_extract_location(f"{title} {result.snippet}"),
        url=url,
        description=result.snippet or title,
    )


def _is_relevant_hiring_result(result: SearchResult) -> bool:
    text = f"{result.title} {result.snippet}".lower()
    return any(hint in text for hint in HIRING_HINTS) and any(
        hint in text for hint in ROLE_HINTS
    )


def _is_linkedin_post_url(url: str) -> bool:
    parsed = urlsplit(url)
    hostname = parsed.hostname or ""
    is_linkedin = hostname == "linkedin.com" or hostname.endswith(".linkedin.com")
    return is_linkedin and (
        parsed.path.startswith("/posts/") or parsed.path.startswith("/feed/update/")
    )


def _canonicalize_url(url: str) -> str:
    parsed = urlsplit(url)
    return parsed._replace(query="", fragment="").geturl()


def _clean_title(title: str) -> str:
    cleaned = " ".join(title.split())
    for suffix in (" | LinkedIn", " posted on LinkedIn"):
        cleaned = cleaned.removesuffix(suffix)
    return cleaned or "LinkedIn hiring post"


def _extract_company(title: str) -> str:
    for delimiter in (" hiring ", " Hiring ", " | "):
        if delimiter in title:
            left = title.split(delimiter, 1)[0].strip()
            if left:
                return left[:80]
    return "LinkedIn post"


def _extract_location(text: str) -> str:
    padded = f" {text.lower()} "
    for location, hints in LOCATION_HINTS:
        if any(hint in padded for hint in hints):
            return location
    return "Unknown"


def _nearby_text(anchor) -> str:
    parent = anchor.find_parent()
    if parent is None:
        return ""
    return " ".join(parent.get_text(" ", strip=True).split())


def _append_unique_result(
    results: list[SearchResult],
    result: SearchResult,
    limit: int,
) -> None:
    url = _canonicalize_url(result.url)
    if any(_canonicalize_url(existing.url) == url for existing in results):
        return
    results.append(result)
    del results[limit:]


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
