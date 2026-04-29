"""Hacker News Who is Hiring crawler using the public Algolia API."""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup

from job_crawler.crawlers.base import JobPosting, clean_html, coerce_datetime

ALGOLIA_BASE_URL = "https://hn.algolia.com/api/v1"
HN_ITEM_BASE_URL = "https://news.ycombinator.com/item"

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
    "swe",
    "sde",
)

HIRING_HINTS = (
    "hiring",
    "we're hiring",
    "we are hiring",
    "is hiring",
    "join us",
    "open roles",
    "positions",
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
    ("Atlanta, GA", ("atlanta",)),
    ("United States", ("united states", " usa ", " u.s.", "remote us", "remote (us)")),
    ("Remote", ("remote",)),
)


def fetch_hn_who_is_hiring_jobs(
    *,
    limit: int = 80,
    thread_id: str | None = None,
) -> list[JobPosting]:
    """Fetch current HN Who is Hiring top-level company posts."""
    with httpx.Client(timeout=20, follow_redirects=True) as client:
        resolved_thread_id = thread_id or find_latest_hiring_thread_id(client=client)
        if resolved_thread_id is None:
            return []
        response = client.get(f"{ALGOLIA_BASE_URL}/items/{resolved_thread_id}")
        response.raise_for_status()
    return parse_hn_thread(response.json(), limit=limit)


def find_latest_hiring_thread_id(*, client: httpx.Client | None = None) -> str | None:
    """Find the newest official monthly Who is Hiring thread."""
    close_client = client is None
    active_client = client or httpx.Client(timeout=20, follow_redirects=True)
    try:
        response = active_client.get(
            f"{ALGOLIA_BASE_URL}/search_by_date",
            params={
                "tags": "story,author_whoishiring",
                "hitsPerPage": "10",
            },
        )
        response.raise_for_status()
        for hit in response.json().get("hits", []):
            title = str(hit.get("title") or "").lower()
            if "who is hiring?" in title and "wants to be hired" not in title:
                object_id = hit.get("objectID") or hit.get("story_id")
                return str(object_id) if object_id is not None else None
        return None
    finally:
        if close_client:
            active_client.close()


def parse_hn_thread(payload: dict[str, Any], *, limit: int = 80) -> list[JobPosting]:
    """Parse an Algolia item tree into rough job postings."""
    postings: list[JobPosting] = []
    for comment in payload.get("children", []):
        if len(postings) >= limit:
            break
        posting = parse_hn_comment(comment)
        if posting is not None:
            postings.append(posting)
    return postings


def parse_hn_comment(comment: dict[str, Any]) -> JobPosting | None:
    """Parse one top-level Who is Hiring comment."""
    comment_id = comment.get("id") or comment.get("objectID")
    html = str(comment.get("text") or "")
    text = _clean_comment_text(html)
    if comment_id is None or not _looks_like_hiring_post(text):
        return None
    company = _extract_company(text)
    title = _extract_title(text)
    location = _extract_location(text)
    external_url = _extract_first_external_url(html)
    url = external_url or f"{HN_ITEM_BASE_URL}?id={comment_id}"
    return JobPosting(
        source="hn",
        source_id=str(comment_id),
        company=company,
        title=title,
        location=location,
        url=url,
        description=text,
        posted_at=coerce_datetime(comment.get("created_at")),
    )


def _clean_comment_text(html: str) -> str:
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n", strip=True)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def _looks_like_hiring_post(text: str) -> bool:
    value = f" {text.lower()} "
    if len(value) < 40:
        return False
    if any(reply in value for reply in (" just applied", " interested", " i can work")):
        return False
    return any(hint in value for hint in HIRING_HINTS) or any(
        hint in value for hint in ROLE_HINTS
    )


def _extract_company(text: str) -> str:
    first_line = _first_content_line(text)
    for delimiter in (" | ", " - ", " – ", " — "):
        if delimiter in first_line:
            value = first_line.split(delimiter, 1)[0].strip()
            return value[:80] if value else "HN company"
    words = first_line.split()
    return " ".join(words[:4])[:80] or "HN company"


def _extract_title(text: str) -> str:
    first_lines = "\n".join(text.splitlines()[:4])
    parts = re.split(r"\s+\|\s+|\s+[–—-]\s+", first_lines)
    for part in parts[1:] + parts[:1]:
        if any(hint in part.lower() for hint in ROLE_HINTS):
            return _clean_title(part)
    for hint in ROLE_HINTS:
        if hint in text.lower():
            return _clean_title(hint)
    return "HN Who is Hiring post"


def _extract_location(text: str) -> str:
    value = f" {text.lower()} "
    for location, hints in LOCATION_HINTS:
        if any(hint in value for hint in hints):
            return location
    return "Unknown"


def _extract_first_external_url(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        href = str(anchor["href"]).strip()
        if _is_external_url(href):
            return href
    return None


def _is_external_url(url: str) -> bool:
    hostname = urlsplit(url).hostname or ""
    return bool(hostname) and not hostname.endswith("ycombinator.com")


def _first_content_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return text.strip()


def _clean_title(value: str) -> str:
    cleaned = clean_html(value) or value
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" :-–—|")
    return cleaned[:120] or "HN Who is Hiring post"


def flatten_comment_ids(comments: Iterable[dict[str, Any]]) -> list[str]:
    """Return comment ids from a nested Algolia tree, useful for diagnostics."""
    ids: list[str] = []
    for comment in comments:
        comment_id = comment.get("id") or comment.get("objectID")
        if comment_id is not None:
            ids.append(str(comment_id))
        ids.extend(flatten_comment_ids(comment.get("children", [])))
    return ids
