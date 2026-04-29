"""Greenhouse public Job Board API crawler."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

import httpx

from job_crawler.crawlers.base import JobPosting, clean_html

GREENHOUSE_JOBS_URL = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
DEFAULT_TIMEOUT_SECONDS = 20


def build_greenhouse_url(board_token: str, *, include_content: bool = True) -> str:
    """Build the public Greenhouse jobs API URL for a board token."""
    value = "true" if include_content else "false"
    return f"{GREENHOUSE_JOBS_URL.format(board_token=board_token)}?content={value}"


def fetch_greenhouse_jobs(
    board_token: str,
    *,
    company: str | None = None,
    limit: int = 100,
    client: httpx.Client | None = None,
) -> list[JobPosting]:
    """Fetch and normalize jobs from one Greenhouse board."""
    close_client = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        response = http.get(build_greenhouse_url(board_token))
        response.raise_for_status()
        return parse_greenhouse_jobs(
            response.json(),
            board_token=board_token,
            company=company,
            limit=limit,
        )
    finally:
        if close_client:
            http.close()


def parse_greenhouse_jobs(
    payload: dict[str, Any],
    *,
    board_token: str,
    company: str | None = None,
    limit: int = 100,
) -> list[JobPosting]:
    """Normalize Greenhouse API payloads into shared job postings."""
    postings: list[JobPosting] = []
    for job in _limited(payload.get("jobs", []), limit):
        title = str(job.get("title") or "").strip()
        url = str(job.get("absolute_url") or "").strip()
        if not title or not url:
            continue
        postings.append(
            JobPosting(
                source="greenhouse",
                source_id=str(job.get("id")),
                company=company or board_token,
                title=title,
                location=_greenhouse_location(job),
                url=url,
                description=clean_html(job.get("content")),
                posted_at=None,
            )
        )
    return postings


def _greenhouse_location(job: dict[str, Any]) -> str | None:
    location = job.get("location") or {}
    name = location.get("name")
    return str(name).strip() if name else None


def _limited(items: Iterable[dict[str, Any]], limit: int) -> Iterable[dict[str, Any]]:
    count = 0
    for item in items:
        if count >= limit:
            break
        yield item
        count += 1
