"""Search query generation for ATS source discovery."""

from __future__ import annotations

DEFAULT_ROLE_QUERIES = (
    "machine learning engineer",
    "ai engineer",
    "agentic ai engineer",
    "software engineer new grad",
    "software development engineer entry level",
)

DEFAULT_LOCATION_QUERIES = (
    "New York",
    "San Francisco",
    "Seattle",
    "Boston",
    "Austin",
    "remote",
    "Los Angeles",
    "Chicago",
    "Denver",
    "Washington DC",
    "Atlanta",
)

SOURCE_SITE_QUERIES = {
    "ashby": "site:jobs.ashbyhq.com",
    "greenhouse": "site:boards.greenhouse.io",
    "lever": "site:jobs.lever.co",
}


def build_discovery_queries(
    *,
    roles: tuple[str, ...] = DEFAULT_ROLE_QUERIES,
    locations: tuple[str, ...] = DEFAULT_LOCATION_QUERIES,
    source_types: tuple[str, ...] = ("ashby", "greenhouse", "lever"),
    limit: int = 30,
) -> list[str]:
    """Build bounded Google-style search queries for ATS discovery."""
    queries: list[str] = []
    for source_type in source_types:
        site_query = SOURCE_SITE_QUERIES[source_type]
        for role in roles:
            for location in locations:
                queries.append(f"{site_query} {role} {location}")
                if len(queries) >= limit:
                    return queries
    return queries
