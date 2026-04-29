"""Zero-cost heuristics for prioritizing jobs."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import IntEnum

from job_crawler.crawlers.base import JobPosting


class LocationTier(IntEnum):
    """Location priority, lower is better."""

    PRIMARY = 0
    MAJOR_US_CITY = 1
    OTHER_US = 2
    REMOTE_US = 3
    GENERIC_REMOTE = 4
    NON_US_OR_UNKNOWN = 5


PRIMARY_LOCATION_KEYWORDS = (
    "new york",
    "nyc",
    "san francisco",
    "sf",
    "bay area",
)

MAJOR_US_CITY_KEYWORDS = (
    "seattle",
    "seatle",
    "boston",
    "austin",
    "los angeles",
    "la",
    "chicago",
    "denver",
    "washington",
    "dc",
    "atlanta",
    "miami",
    "dallas",
    "houston",
    "phoenix",
    "portland",
    "minneapolis",
    "nashville",
    "charlotte",
    "salt lake city",
    "provo",
    "raleigh",
    "durham",
    "pittsburgh",
    "philadelphia",
    "san diego",
    "san jose",
    "palo alto",
    "mountain view",
    "sunnyvale",
    "foster city",
)

ROLE_KEYWORDS = (
    "machine learning",
    "machine learning engineer",
    "ml",
    "ml engineer",
    "ml ops",
    "ai engineer",
    "artificial intelligence",
    "applied machine learning",
    "generative ai",
    "genai",
    "llm",
    "large language model",
    "model engineer",
    "deep learning",
    "nlp",
    "agent",
    "agentic",
    "agents",
    "applied ai",
    "software engineer",
    "software engineering",
    "swe",
    "sde",
    "software development engineer",
    "full stack",
    "full-stack",
    "fullstack",
    "founding engineer",
    "founding ai engineer",
    "founding machine learning engineer",
    "platform engineer",
    "backend",
    "back end",
    "backend engineer",
    "infrastructure",
    "infra",
    "data engineer",
    "research engineer",
    "research scientist",
    "data scientist",
    "data science",
    "data science engineer",
    "applied scientist",
    "forward deployed engineer",
    "forward deployed software engineer",
)

TARGET_TITLE_KEYWORDS = (
    "machine learning",
    "ml engineer",
    "ai engineer",
    "applied ai",
    "artificial intelligence",
    "applied machine learning",
    "generative ai",
    "genai",
    "llm",
    "large language model",
    "model engineer",
    "deep learning",
    "nlp",
    "software engineer",
    "software development engineer",
    "founding engineer",
    "founding ai engineer",
    "founding machine learning engineer",
    "swe",
    "sde",
    "fullstack",
    "full stack",
    "full-stack",
    "frontend engineer",
    "front end engineer",
    "backend engineer",
    "back end engineer",
    "platform engineer",
    "infrastructure engineer",
    "cloud platform engineer",
    "data scientist",
    "data science",
    "data science engineer",
    "applied scientist",
    "research scientist",
    "research engineer",
    "forward deployed software engineer",
    "fdse",
    "autonomy engineer",
    "computer vision",
    "cuda",
    "kernel engineer",
    "embedded software",
)

CONTEXT_TITLE_KEYWORDS = (
    "engineer",
    "developer",
    "scientist",
    "researcher",
    "research",
    "founding",
    "member of technical staff",
    "mts",
)

AI_CONTEXT_KEYWORDS = (
    "machine learning",
    "artificial intelligence",
    "applied ai",
    "applied machine learning",
    "generative ai",
    "genai",
    "llm",
    "large language model",
    "deep learning",
    "nlp",
    "computer vision",
    "agentic",
    "ai agent",
)

NON_TARGET_TITLE_KEYWORDS = (
    "account executive",
    "associate buyer",
    "business development",
    "community",
    "customer",
    "cyber",
    "designer",
    "design",
    "electrical engineer",
    "field engineer",
    "field marketer",
    "finance",
    "growth",
    "gtm",
    "instructor",
    "legal",
    "marketer",
    "marketing",
    "mechanical engineer",
    "operations",
    "product manager",
    "production technician",
    "proposal",
    "recruiter",
    "recruiting",
    "sales",
    "security",
    "social media",
    "solutions engineer",
    "support",
    "technician",
    "workplace",
)

ROLE_FILTER_OPTIONS = (
    "AI",
    "ML",
    "SWE/SDE",
    "Backend",
    "Data",
    "Infrastructure",
    "Product",
    "Design",
    "Other",
)

SOURCE_FILTER_OPTIONS = (
    "ashby",
    "greenhouse",
    "lever",
    "yc",
    "github_jobs",
    "jobright_swe_new_grad_2026",
    "jobright_data_analysis_new_grad_2026",
    "simplify_new_grad_positions",
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

TOO_MUCH_EXPERIENCE_PATTERNS = (
    re.compile(r"\b(?:[4-9]|1[0-9])\+?\s*(?:years?|yrs?)\b"),
    re.compile(
        r"\b(?:at least|minimum(?: of)?|requires?)\s+"
        r"(?:[4-9]|1[0-9])\+?\s*(?:years?|yrs?)\b"
    ),
    re.compile(
        r"\b(?:[4-9]|1[0-9])\+?\s*(?:years?|yrs?)\s+of\s+"
        r"(?:professional\s+)?experience\b"
    ),
)

US_LOCATION_KEYWORDS = (
    "united states",
    "usa",
    "u.s.",
    " us ",
    ", us",
    "remote (us",
    "remote (united states",
    "us remote",
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "district of columbia",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington state",
    "west virginia",
    "wisconsin",
    "wyoming",
    "pennsylvania",
)

US_STATE_ABBREVIATIONS = (
    "AL",
    "AK",
    "AZ",
    "AR",
    "CA",
    "CO",
    "CT",
    "DC",
    "DE",
    "FL",
    "GA",
    "HI",
    "IA",
    "ID",
    "IL",
    "IN",
    "KS",
    "KY",
    "LA",
    "MA",
    "MD",
    "ME",
    "MI",
    "MN",
    "MO",
    "MS",
    "MT",
    "NC",
    "ND",
    "NE",
    "NH",
    "NJ",
    "NM",
    "NV",
    "NY",
    "OH",
    "OK",
    "OR",
    "PA",
    "RI",
    "SC",
    "SD",
    "TN",
    "TX",
    "UT",
    "VA",
    "VT",
    "WA",
    "WI",
    "WV",
    "WY",
)

NON_US_LOCATION_KEYWORDS = (
    "abu dhabi",
    "amsterdam",
    "australia",
    "canada",
    "canberra",
    "doha",
    "dubai",
    "france",
    "toronto",
    "montreal",
    "vancouver",
    "united kingdom",
    "uk",
    "london",
    "england",
    "europe",
    "israel",
    "japan",
    "lithuania",
    "netherlands",
    "singapore",
    "south korea",
    "seoul",
    "stockholm",
    "sweden",
    "sydney",
    "india",
    "mexico",
    "monterrey",
    "mexico city",
    "poland",
    "gdańsk",
    "gdansk",
    "beijing",
    "shanghai",
    "shenzhen",
    "china",
    "buenos aires",
    "argentina",
    "portugal",
    "qatar",
    "tokyo",
    "united arab emirates",
    "vilnius",
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

    excluded = is_senior_role(job) or requires_too_much_experience(job)
    score = 0
    if any(keyword in combined for keyword in ROLE_KEYWORDS):
        score += 40
    if any(keyword in combined for keyword in EARLY_CAREER_KEYWORDS):
        score += 25
    if tier == LocationTier.PRIMARY:
        score += 13
    elif tier == LocationTier.MAJOR_US_CITY:
        score += 12
    elif tier == LocationTier.OTHER_US:
        score += 10
    elif tier == LocationTier.REMOTE_US:
        score += 4
    elif tier == LocationTier.GENERIC_REMOTE:
        score += 1
    if excluded:
        score -= 100

    if is_senior_role(job):
        reason = "excluded senior/staff role"
    elif requires_too_much_experience(job):
        reason = "excluded experience requirement above 3 years"
    else:
        reason = f"location tier {tier.name.lower()}"
    return RankedJob(job=job, score=score, location_tier=tier, excluded=excluded, reason=reason)


def is_senior_role(job: JobPosting) -> bool:
    """Return true for seniority levels the user wants to avoid."""
    title = job.title.lower()
    return any(keyword in title for keyword in SENIOR_KEYWORDS)


def requires_too_much_experience(job: JobPosting) -> bool:
    """Return true when text explicitly asks for more than 3 years."""
    combined = f"{job.title} {job.description or ''}".lower()
    return any(pattern.search(combined) for pattern in TOO_MUCH_EXPERIENCE_PATTERNS)


def is_target_role(job: JobPosting) -> bool:
    """Return true for roles aligned to the user's target search."""
    title = job.title.lower()
    if any(keyword in title for keyword in NON_TARGET_TITLE_KEYWORDS):
        return False
    if any(keyword in title for keyword in TARGET_TITLE_KEYWORDS):
        return True
    description = (job.description or "").lower()
    has_technical_title = any(keyword in title for keyword in CONTEXT_TITLE_KEYWORDS)
    has_ai_context = any(keyword in description for keyword in AI_CONTEXT_KEYWORDS)
    return has_technical_title and has_ai_context


def role_category(title: str) -> str:
    """Classify a title into a stable dashboard role bucket."""
    value = title.lower()
    if "machine learning" in value or "ml" in value:
        return "ML"
    if "founding" in value:
        return "Founding"
    if (
        "ai" in value
        or "artificial intelligence" in value
        or "agent" in value
        or "llm" in value
        or "generative" in value
        or "genai" in value
    ):
        return "AI"
    if "data scientist" in value or "data science" in value:
        return "Data Science"
    if "data" in value:
        return "Data"
    if "infra" in value or "platform" in value or "cloud" in value:
        return "Infrastructure"
    if "backend" in value or "back end" in value:
        return "Backend"
    if (
        "swe" in value
        or "software" in value
        or "sde" in value
        or "fullstack" in value
        or "full stack" in value
        or "frontend" in value
        or "front end" in value
    ):
        return "SWE/SDE"
    if (
        "autonomy" in value
        or "computer vision" in value
        or "embedded" in value
        or "cuda" in value
        or "kernel" in value
    ):
        return "Engineering"
    if "product" in value:
        return "Product"
    if "design" in value:
        return "Design"
    return "Other"


def location_tier(location: str | None) -> LocationTier:
    """Classify a location with concrete US cities ahead of remote roles."""
    if not location:
        return LocationTier.NON_US_OR_UNKNOWN
    value = f" {location.lower()} "
    if any(keyword in value for keyword in PRIMARY_LOCATION_KEYWORDS):
        return LocationTier.PRIMARY
    if any(keyword in value for keyword in MAJOR_US_CITY_KEYWORDS):
        return LocationTier.MAJOR_US_CITY
    if "remote" in value and ("us" in value or "usa" in value or "united states" in value):
        return LocationTier.REMOTE_US
    if value.strip() == "remote":
        return LocationTier.GENERIC_REMOTE
    if any(token in value for token in ("united states", "usa", " us", ", us")):
        return LocationTier.OTHER_US
    return LocationTier.NON_US_OR_UNKNOWN


def is_us_role(job: JobPosting) -> bool:
    """Return true unless the location is explicitly non-US-only."""
    location = (job.location or "").strip()
    if not location:
        return False
    value = f" {location.lower()} "
    has_us_signal = any(keyword in value for keyword in US_LOCATION_KEYWORDS) or _has_us_state(
        location
    )
    if has_us_signal:
        return True
    if location.lower() == "remote":
        return True
    has_non_us_signal = any(keyword in value for keyword in NON_US_LOCATION_KEYWORDS)
    return not has_non_us_signal


def _has_us_state(location: str) -> bool:
    return any(
        re.search(rf"(?<![A-Za-z]){state}(?![A-Za-z])", location, flags=re.IGNORECASE)
        for state in US_STATE_ABBREVIATIONS
    )
