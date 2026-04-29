"""Search query generation for ATS source discovery."""

from __future__ import annotations

DEFAULT_ROLE_QUERIES = (
    "ai engineer",
    "applied ai engineer",
    "machine learning engineer",
    "ml engineer",
    "llm engineer",
    "generative ai engineer",
    "agent engineer",
    "ai agents engineer",
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
    "forward deployed software engineer",
    "platform engineer machine learning",
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
    "Dallas",
    "Houston",
    "Miami",
    "Raleigh",
    "Durham",
    "Philadelphia",
    "Pittsburgh",
    "San Diego",
    "San Jose",
    "Palo Alto",
    "Mountain View",
    "Foster City",
    "Portland",
    "Minneapolis",
    "Nashville",
    "Charlotte",
    "Salt Lake City",
)

SOURCE_SITE_QUERIES = {
    "ashby": "site:jobs.ashbyhq.com",
    "greenhouse": "site:boards.greenhouse.io",
    "lever": "site:jobs.lever.co",
}

DEFAULT_WEB_DISCOVERY_ROLES = (
    "ai engineer",
    "applied ai engineer",
    "machine learning engineer",
    "ml engineer",
    "llm engineer",
    "generative ai engineer",
    "research engineer",
    "applied scientist",
    "data scientist",
    "software engineer ai",
)

DEFAULT_WEB_DISCOVERY_QUERIES = tuple(
    query
    for role in DEFAULT_WEB_DISCOVERY_ROLES
    for query in (
        f'site:jobs.ashbyhq.com "{role}" "United States"',
        f'site:boards.greenhouse.io "{role}" "United States"',
        f'site:jobs.lever.co "{role}" "United States"',
    )
)


def build_discovery_queries(
    *,
    roles: tuple[str, ...] = DEFAULT_ROLE_QUERIES,
    locations: tuple[str, ...] = DEFAULT_LOCATION_QUERIES,
    source_types: tuple[str, ...] = ("ashby", "greenhouse", "lever"),
    limit: int = 30,
) -> list[str]:
    """Build bounded Google-style search queries for ATS discovery."""
    queries: list[str] = []
    for role in roles:
        for source_type in source_types:
            site_query = SOURCE_SITE_QUERIES[source_type]
            for location in locations:
                queries.append(f"{site_query} {role} {location}")
                if len(queries) >= limit:
                    return queries
    return queries
