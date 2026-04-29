"""Zero-cost heuristics for prioritizing jobs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from job_crawler.crawlers.base import JobPosting


class LocationTier(IntEnum):
    """Location priority, lower is better."""

    PRIMARY = 0
    MAJOR_US_CITY = 1
    REMOTE_US = 2
    OTHER_US = 3
    UNKNOWN_OR_OTHER = 4


PRIMARY_LOCATION_KEYWORDS = (
    "new york",
    "nyc",
    "san francisco",
    "sf",
    "bay area",
)

MAJOR_US_CITY_KEYWORDS = (
    "seattle",
    "boston",
    "austin",
    "los angeles",
    "chicago",
    "denver",
    "washington",
    "dc",
    "atlanta",
    "miami",
    "raleigh",
    "durham",
    "pittsburgh",
    "philadelphia",
    "san diego",
)

ROLE_KEYWORDS = (
    "machine learning",
    "ml engineer",
    "ai engineer",
    "agent",
    "applied ai",
    "software engineer",
    "swe",
    "sde",
    "backend",
    "infrastructure",
)

EARLY_CAREER_KEYWORDS = (
    "new grad",
    "university grad",
    "entry level",
    "entry-level",
    "junior",
    "software engineer i",
    "engineer i",
    "0-2",
    "0 - 2",
    "1-3",
    "1 - 3",
    "2-3",
    "2 - 3",
)

SENIOR_KEYWORDS = (
    "senior",
    "sr.",
    "staff",
    "principal",
    "lead",
    "manager",
    "director",
    "architect",
    "head of",
)


@dataclass(frozen=True)
class RankedJob:
    """A job plus its deterministic rank metadata."""

    job: JobPosting
    score: int
    location_tier: LocationTier
    excluded: bool
    reason: str


def rank_job(job: JobPosting) -> RankedJob:
    """Rank a job without paid APIs or LLM calls."""
    title = job.title.lower()
    description = (job.description or "").lower()
    combined = f"{title} {description}"
    tier = location_tier(job.location)

    excluded = is_senior_role(job)
    score = 0
    if any(keyword in combined for keyword in ROLE_KEYWORDS):
        score += 40
    if any(keyword in combined for keyword in EARLY_CAREER_KEYWORDS):
        score += 25
    if tier == LocationTier.PRIMARY:
        score += 20
    elif tier == LocationTier.MAJOR_US_CITY:
        score += 14
    elif tier == LocationTier.REMOTE_US:
        score += 12
    elif tier == LocationTier.OTHER_US:
        score += 6
    if excluded:
        score -= 100

    reason = "excluded senior/staff role" if excluded else f"location tier {tier.name.lower()}"
    return RankedJob(job=job, score=score, location_tier=tier, excluded=excluded, reason=reason)


def is_senior_role(job: JobPosting) -> bool:
    """Return true for seniority levels the user wants to avoid."""
    title = job.title.lower()
    return any(keyword in title for keyword in SENIOR_KEYWORDS)


def location_tier(location: str | None) -> LocationTier:
    """Classify a location with NYC/SF first, then major US cities."""
    if not location:
        return LocationTier.UNKNOWN_OR_OTHER
    value = location.lower()
    if any(keyword in value for keyword in PRIMARY_LOCATION_KEYWORDS):
        return LocationTier.PRIMARY
    if any(keyword in value for keyword in MAJOR_US_CITY_KEYWORDS):
        return LocationTier.MAJOR_US_CITY
    if "remote" in value and ("us" in value or "usa" in value or "united states" in value):
        return LocationTier.REMOTE_US
    if "remote" == value.strip():
        return LocationTier.REMOTE_US
    if any(token in value for token in ("united states", "usa", " us", ", us")):
        return LocationTier.OTHER_US
    return LocationTier.UNKNOWN_OR_OTHER
