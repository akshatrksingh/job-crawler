"""Hacker News Who is Hiring crawler using the public Algolia API."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any

import httpx

from job_crawler.crawlers.base import JobPosting, clean_html, coerce_datetime

ALGOLIA_SEARCH_BY_DATE_URL = "https://hn.algolia.com/api/v1/search_by_date"
HN_ITEM_URL = "https://news.ycombinator.com/item?id={item_id}"
DEFAULT_TIMEOUT_SECONDS = 20


def build_hn_who_is_hiring_thread_params(*, hits_per_page: int = 3) -> dict[str, str | int]:
    """Build Algolia params for recent monthly Who is Hiring threads."""
    return {
        "tags": "story",
        "query": "Ask HN: Who is hiring?",
        "hitsPerPage": hits_per_page,
    }


def build_hn_thread_comments_params(
    thread_id: str,
    *,
    hits_per_page: int = 100,
) -> dict[str, str | int]:
    """Build Algolia params for comments under a specific HN thread."""
    return {
        "tags": f"comment,story_{thread_id}",
        "hitsPerPage": hits_per_page,
    }


def fetch_latest_who_is_hiring_jobs(
    *,
    limit: int = 100,
    client: httpx.Client | None = None,
) -> list[JobPosting]:
    """Fetch comments from the latest discovered Who is Hiring thread."""
    close_client = client is None
    http = client or httpx.Client(timeout=DEFAULT_TIMEOUT_SECONDS)
    try:
        thread_response = http.get(
            ALGOLIA_SEARCH_BY_DATE_URL,
            params=build_hn_who_is_hiring_thread_params(),
        )
        thread_response.raise_for_status()
        threads = parse_hn_who_is_hiring_threads(thread_response.json())
        if not threads:
            return []
        latest = threads[0]
        comments_response = http.get(
            ALGOLIA_SEARCH_BY_DATE_URL,
            params=build_hn_thread_comments_params(latest["objectID"], hits_per_page=limit),
        )
        comments_response.raise_for_status()
        return parse_hn_who_is_hiring_comments(
            comments_response.json(),
            thread_title=latest["title"],
            limit=limit,
        )
    finally:
        if close_client:
            http.close()


def parse_hn_who_is_hiring_threads(payload: dict[str, Any]) -> list[dict[str, str]]:
    """Return likely Who is Hiring monthly thread hits."""
    threads: list[dict[str, str]] = []
    for hit in payload.get("hits", []):
        title = str(hit.get("title") or "")
        if "who is hiring" not in title.lower():
            continue
        object_id = str(hit.get("objectID") or "")
        if not object_id:
            continue
        threads.append({"objectID": object_id, "title": title})
    return threads


def parse_hn_who_is_hiring_comments(
    payload: dict[str, Any],
    *,
    thread_title: str,
    limit: int = 100,
) -> list[JobPosting]:
    """Normalize HN Who is Hiring comments into coarse job postings."""
    postings: list[JobPosting] = []
    for hit in _limited(payload.get("hits", []), limit):
        comment_text = clean_html(hit.get("comment_text"))
        if not comment_text:
            continue
        object_id = str(hit.get("objectID") or "")
        company, title, location = _parse_hn_comment_heading(comment_text)
        postings.append(
            JobPosting(
                source="hn",
                source_id=object_id,
                company=company,
                title=title,
                location=location,
                url=HN_ITEM_URL.format(item_id=object_id),
                description=f"{thread_title}\n\n{comment_text}",
                posted_at=coerce_datetime(hit.get("created_at")),
            )
        )
    return postings


def _parse_hn_comment_heading(comment_text: str) -> tuple[str, str, str | None]:
    first_line = comment_text.splitlines()[0]
    pieces = [piece.strip() for piece in first_line.split("|") if piece.strip()]
    company = pieces[0] if pieces else "HN Company"
    location = _find_location_piece(pieces[1:])
    title = "Who is Hiring post"
    for piece in pieces[1:]:
        lower = piece.lower()
        if any(token in lower for token in ("engineer", "developer", "scientist", "swe", "sde")):
            title = piece
            break
    return company, title, location


def _find_location_piece(pieces: Iterable[str]) -> str | None:
    for piece in pieces:
        lower = piece.lower()
        if any(
            token in lower
            for token in (
                "remote",
                "san francisco",
                "new york",
                "nyc",
                "us",
                "usa",
                "ca",
                "wa",
                "ma",
                "tx",
            )
        ):
            return piece
    return None


def _limited(items: Iterable[dict[str, Any]], limit: int) -> Iterable[dict[str, Any]]:
    count = 0
    for item in items:
        if count >= limit:
            break
        yield item
        count += 1


def utc_now_iso() -> str:
    """Expose UTC now for future live-crawl provenance without sprinkling datetime calls."""
    return datetime.now(UTC).isoformat()
