"""Google Jobs adapter through python-jobspy.

The live dependency is imported lazily so normal tests do not import pandas or
trigger any scraping setup.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from job_crawler.crawlers.base import JobPosting, clean_html, coerce_datetime

DEFAULT_GOOGLE_SEARCH_TERMS = (
    "software engineer new grad",
    "software engineer entry level",
    "software engineer 0-2 years",
    "machine learning engineer",
    "ai engineer",
    "applied ai engineer",
    "data scientist entry level",
)

DEFAULT_GOOGLE_LOCATIONS = (
    "New York, NY",
    "San Francisco, CA",
    "Seattle, WA",
    "Boston, MA",
    "Austin, TX",
    "Remote",
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
    search_terms: tuple[str, ...] = DEFAULT_GOOGLE_SEARCH_TERMS,
    locations: tuple[str, ...] = DEFAULT_GOOGLE_LOCATIONS,
    limit: int = 9,
) -> list[tuple[str, str]]:
    """Build bounded search-term/location pairs for Google Jobs."""
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
