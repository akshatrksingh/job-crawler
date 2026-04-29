"""YC Work at a Startup public page parser."""

from __future__ import annotations

from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from job_crawler.crawlers.base import JobPosting

YC_JOBS_URL = "https://www.ycombinator.com/jobs"
DEFAULT_TIMEOUT_SECONDS = 20


def fetch_yc_jobs(
    *,
    limit: int = 50,
    client: httpx.Client | None = None,
) -> list[JobPosting]:
    """Fetch and parse the public YC jobs page."""
    close_client = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        response = http.get(YC_JOBS_URL)
        response.raise_for_status()
        return parse_yc_jobs_html(response.text, limit=limit)
    finally:
        if close_client:
            http.close()


def parse_yc_jobs_html(html: str, *, limit: int = 50) -> list[JobPosting]:
    """Normalize visible YC job links from public HTML."""
    soup = BeautifulSoup(html, "html.parser")
    postings: list[JobPosting] = []
    seen_urls: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"])
        if "/jobs/" not in href:
            continue
        if href.startswith("/jobs/role/") or href == "/jobs":
            continue
        title = anchor.get_text(" ", strip=True)
        if not title or "job" in title.lower() and len(title.split()) <= 3:
            continue
        url = urljoin(YC_JOBS_URL, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)
        container = anchor.find_parent(["li", "article", "div"])
        context = container.get_text(" ", strip=True) if container else title
        company = _guess_company(context, title)
        location = _guess_location(context)
        postings.append(
            JobPosting(
                source="yc",
                source_id=url.rstrip("/").split("/")[-1],
                company=company,
                title=title,
                location=location,
                url=url,
                description=context,
            )
        )
        if len(postings) >= limit:
            break
    return postings


def _guess_company(context: str, title: str) -> str:
    if title in context:
        prefix = context.split(title, 1)[0].strip()
        if prefix:
            return prefix.split("  ")[0].strip() or "YC Company"
    return "YC Company"


def _guess_location(context: str) -> str | None:
    markers = (
        "Remote",
        "New York",
        "San Francisco",
        "Seattle",
        "Boston",
        "Austin",
        "Los Angeles",
        "Chicago",
        "Denver",
        "Washington",
        "Atlanta",
    )
    found = [marker for marker in markers if marker.lower() in context.lower()]
    return " / ".join(found) if found else None
