"""Shared crawler contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
