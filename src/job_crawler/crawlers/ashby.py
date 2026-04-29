"""Ashby public job board crawler."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from job_crawler.crawlers.base import JobPosting, clean_html, coerce_datetime

ASHBY_BOARD_URL = "https://api.ashbyhq.com/posting-api/job-board/{slug}"
DEFAULT_TIMEOUT_SECONDS = 20


def build_ashby_url(slug: str, *, include_compensation: bool = False) -> str:
    """Build the public Ashby job board API URL for a company slug."""
    value = "true" if include_compensation else "false"
    return f"{ASHBY_BOARD_URL.format(slug=slug)}?includeCompensation={value}"


def fetch_ashby_jobs(
    slug: str,
    *,
    company: str | None = None,
    limit: int = 100,
    client: httpx.Client | None = None,
) -> list[JobPosting]:
    """Fetch and normalize jobs from one Ashby job board."""
    close_client = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        response = http.get(build_ashby_url(slug))
        response.raise_for_status()
        return parse_ashby_jobs(response.json(), slug=slug, company=company, limit=limit)
    finally:
        if close_client:
            http.close()


def parse_ashby_jobs(
    payload: dict[str, Any],
    *,
    slug: str,
    company: str | None = None,
    limit: int = 100,
) -> list[JobPosting]:
    """Normalize Ashby API payloads into shared job postings."""
    jobs = payload.get("jobs", [])
    postings: list[JobPosting] = []
    for job in _limited(jobs, limit):
        if job.get("isListed") is False:
            continue
        source_id = str(job.get("id") or job.get("jobId") or job.get("title"))
        title = str(job.get("title") or "").strip()
        if not title:
            continue
        description = job.get("descriptionPlain") or clean_html(job.get("descriptionHtml"))
        postings.append(
            JobPosting(
                source="ashby",
                source_id=source_id,
                company=company or slug,
                title=title,
                location=_format_ashby_location(job),
                url=str(job.get("jobUrl") or f"https://jobs.ashbyhq.com/{slug}/{source_id}"),
                description=description,
                posted_at=coerce_datetime(job.get("publishedDate") or job.get("createdAt")),
            )
        )
    return postings


def _format_ashby_location(job: dict[str, Any]) -> str | None:
    locations = []
    primary = job.get("location")
    if primary:
        locations.append(str(primary))
    for secondary in job.get("secondaryLocations") or []:
        location = secondary.get("location")
        if location:
            locations.append(str(location))
    if job.get("isRemote"):
        locations.append("Remote")
    unique_locations = list(dict.fromkeys(locations))
    return ", ".join(unique_locations) if unique_locations else None


def _limited(items: Iterable[dict[str, Any]], limit: int) -> Iterable[dict[str, Any]]:
    count = 0
    for item in items:
        if count >= limit:
            break
        yield item
        count += 1
