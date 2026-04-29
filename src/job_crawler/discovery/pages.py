"""Discover ATS sources from generic company career pages."""

from __future__ import annotations

from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from job_crawler.discovery.sources import DiscoveredSource, extract_sources_from_urls


def extract_sources_from_html(
    html: str,
    *,
    page_url: str,
    discovered_from: str,
) -> list[DiscoveredSource]:
    """Extract ATS sources from links on a generic careers page."""
    soup = BeautifulSoup(html, "html.parser")
    urls = [urljoin(page_url, str(anchor["href"])) for anchor in soup.find_all("a", href=True)]
    return extract_sources_from_urls(urls, discovered_from=discovered_from)


def fetch_sources_from_pages(
    urls: list[str],
    *,
    discovered_from: str,
    limit: int = 50,
) -> list[DiscoveredSource]:
    """Fetch company pages and extract supported ATS links."""
    discovered: dict[tuple[str, str], DiscoveredSource] = {}
    for url in urls[:limit]:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=20,
            headers={"User-Agent": "job-crawler/0.1"},
        )
        response.raise_for_status()
        for source in extract_sources_from_html(
            response.text,
            page_url=url,
            discovered_from=discovered_from,
        ):
            discovered.setdefault((source.source_type, source.slug), source)
    return list(discovered.values())
