"""Google Jobs adapter through python-jobspy.

The live dependency is imported lazily so normal tests do not import pandas or
trigger any scraping setup.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from job_crawler.crawlers.base import JobPosting, clean_html, coerce_datetime

DEFAULT_GOOGLE_SEARCH_TERMS = (
    "ai engineer",
    "applied ai engineer",
    "machine learning engineer",
    "ml engineer",
    "llm engineer",
    "generative ai engineer",
    "research engineer",
    "applied scientist",
    "data scientist",
    "data science engineer",
    "software engineer ai",
    "software engineer machine learning",
    "software engineer",
    "software development engineer",
    "founding engineer",
    "product engineer ai",
    "backend engineer",
    "full stack engineer",
    "junior software engineer",
    "entry level software engineer",
)

DEFAULT_GOOGLE_LOCATIONS = (
    "United States",
    "Seattle, WA",
    "Boston, MA",
    "Austin, TX",
    "Chicago, IL",
    "Denver, CO",
    "Atlanta, GA",
    "Dallas, TX",
    "Los Angeles, CA",
    "Washington, DC",
    "Raleigh, NC",
    "Remote",
)

DEFAULT_GOOGLE_JOB_QUERIES = (
    ("ai engineer", "United States"),
    ("applied ai engineer", "United States"),
    ("machine learning engineer", "United States"),
    ("ml engineer", "United States"),
    ("llm engineer", "United States"),
    ("generative ai engineer", "United States"),
    ("research engineer", "United States"),
    ("applied scientist", "United States"),
    ("data scientist", "United States"),
    ("data science engineer", "United States"),
    ("software engineer ai", "United States"),
    ("software engineer machine learning", "United States"),
    ("software engineer", "United States"),
    ("software development engineer", "United States"),
    ("founding engineer", "United States"),
    ("backend engineer", "United States"),
    ("full stack engineer", "United States"),
    ("ai engineer", "Seattle, WA"),
    ("machine learning engineer", "Boston, MA"),
    ("applied ai engineer", "Austin, TX"),
)


def fetch_google_jobs(
    *,
    search_term: str,
    location: str,
    results_wanted: int = 10,
) -> list[JobPosting]:
    """Run one bounded Google Jobs search through python-jobspy."""
    from jobspy import scrape_jobs

    dataframe = scrape_jobs(
        site_name=["google"],
        search_term=search_term,
        location=location,
        results_wanted=results_wanted,
        hours_old=24 * 30,
    )
    records = dataframe.to_dict("records")
    return parse_jobspy_records(records, query=search_term, location=location, limit=results_wanted)


def parse_jobspy_records(
    records: Iterable[dict[str, Any]],
    *,
    query: str,
    location: str,
    limit: int = 10,
) -> list[JobPosting]:
    """Normalize python-jobspy records into shared job postings."""
    postings: list[JobPosting] = []
    for record in records:
        if len(postings) >= limit:
            break
        title = _first_text(record, "title", "job_title")
        company = _first_text(record, "company", "company_name")
        url = _first_text(record, "job_url", "url", "job_url_direct")
        if not title or not company or not url:
            continue
        source_id = _first_text(record, "id", "job_id") or f"{company}:{title}:{url}"
        posting_location = _first_text(record, "location", "job_location") or location
        description = _first_text(record, "description", "job_description")
        postings.append(
            JobPosting(
                source="google_jobs",
                source_id=str(source_id),
                company=company,
                title=title,
                location=posting_location,
                url=url,
                description=clean_html(description),
                posted_at=coerce_datetime(_first_value(record, "date_posted", "posted_at")),
            )
        )
    return postings


def build_default_google_job_queries(
    *,
    queries: tuple[tuple[str, str], ...] = DEFAULT_GOOGLE_JOB_QUERIES,
    search_terms: tuple[str, ...] = DEFAULT_GOOGLE_SEARCH_TERMS,
    locations: tuple[str, ...] = DEFAULT_GOOGLE_LOCATIONS,
    limit: int = 20,
) -> list[tuple[str, str]]:
    """Build bounded search-term/location pairs for Google Jobs."""
    if limit <= 0:
        return []
    if queries:
        return list(queries[:limit])
    pairs: list[tuple[str, str]] = []
    for search_term in search_terms:
        for location in locations:
            pairs.append((search_term, location))
            if len(pairs) >= limit:
                return pairs
    return pairs


def _first_text(record: dict[str, Any], *keys: str) -> str | None:
    value = _first_value(record, *keys)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _first_value(record: dict[str, Any], *keys: str) -> Any | None:
    for key in keys:
        value = record.get(key)
        if value is not None and value == value:
            return value
    return None
