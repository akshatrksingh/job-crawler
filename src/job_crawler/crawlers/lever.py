"""Lever public Postings API crawler."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from job_crawler.crawlers.base import JobPosting, clean_html, coerce_datetime

LEVER_POSTINGS_URL = "https://api.lever.co/v0/postings/{site}"
DEFAULT_TIMEOUT_SECONDS = 20


def build_lever_url(site: str, *, limit: int = 100, skip: int = 0) -> str:
    """Build the public Lever postings API URL for a site slug."""
    return f"{LEVER_POSTINGS_URL.format(site=site)}?mode=json&limit={limit}&skip={skip}"


def fetch_lever_jobs(
    site: str,
    *,
    company: str | None = None,
    limit: int = 100,
    client: httpx.Client | None = None,
) -> list[JobPosting]:
    """Fetch and normalize jobs from one Lever site."""
    close_client = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        response = http.get(build_lever_url(site, limit=limit))
        response.raise_for_status()
        return parse_lever_jobs(response.json(), site=site, company=company, limit=limit)
    finally:
        if close_client:
            http.close()


def parse_lever_jobs(
    payload: list[dict[str, Any]],
    *,
    site: str,
    company: str | None = None,
    limit: int = 100,
) -> list[JobPosting]:
    """Normalize Lever API payloads into shared job postings."""
    postings: list[JobPosting] = []
    for job in _limited(payload, limit):
        title = str(job.get("text") or "").strip()
        url = str(job.get("hostedUrl") or "").strip()
        if not title or not url:
            continue
        postings.append(
            JobPosting(
                source="lever",
                source_id=str(job.get("id")),
                company=company or site,
                title=title,
                location=_lever_location(job),
                url=url,
                description=job.get("descriptionPlain") or clean_html(job.get("description")),
                posted_at=coerce_datetime(job.get("createdAt")),
            )
        )
    return postings


def _lever_location(job: dict[str, Any]) -> str | None:
    categories = job.get("categories") or {}
    all_locations = categories.get("allLocations") or []
    if all_locations:
        return ", ".join(str(location) for location in all_locations if location)
    location = categories.get("location")
    return str(location).strip() if location else None


def _limited(items: Iterable[dict[str, Any]], limit: int) -> Iterable[dict[str, Any]]:
    count = 0
    for item in items:
        if count >= limit:
            break
        yield item
        count += 1
