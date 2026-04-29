"""Shared crawler contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from html import unescape

from bs4 import BeautifulSoup


@dataclass(frozen=True)
class JobPosting:
    """Normalized job posting collected from any source."""

    source: str
    source_id: str
    company: str
    title: str
    location: str | None
    url: str
    description: str | None = None
    posted_at: datetime | None = None
    first_seen_at: datetime | None = None


def clean_html(value: str | None) -> str | None:
    """Convert optional HTML content into compact plain text."""
    if not value:
        return None
    text = BeautifulSoup(unescape(value), "html.parser").get_text(" ", strip=True)
    return " ".join(text.split()) or None


def coerce_datetime(value: object) -> datetime | None:
    """Parse common API datetime values without raising on missing data."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value / 1000 if value > 10_000_000_000 else value)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
    return None
