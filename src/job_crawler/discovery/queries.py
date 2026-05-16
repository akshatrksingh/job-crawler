"""Search query generation for ATS source discovery."""

from __future__ import annotations

DEFAULT_ROLE_QUERIES = (
    "ai engineer",
    "applied ai engineer",
    "applied ai ml engineer",
    "applied machine learning engineer",
    "founding ai engineer",
    "founding applied ai engineer",
    "machine learning engineer",
    "ml engineer",
    "ai ml engineer",
    "llm engineer",
    "generative ai engineer",
    "agent engineer",
    "ai agents engineer",
    "agentic ai engineer",
    "member of technical staff",
    "mts ai engineer",
    "research engineer",
    "applied scientist",
    "data scientist",
    "data science engineer",
    "software engineer ai",
    "software engineer machine learning",
    "ai product engineer",
    "model engineer",
    "ml systems engineer",
    "ml infrastructure engineer",
    "machine learning infrastructure engineer",
    "ai platform engineer",
    "software engineer",
    "software development engineer",
    "founding engineer",
    "founding software engineer",
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
    "applied machine learning engineer",
    "founding applied ai engineer",
    "machine learning engineer",
    "ml engineer",
    "ai ml engineer",
    "llm engineer",
    "agentic ai engineer",
    "member of technical staff",
    "ml systems engineer",
    "ml infrastructure engineer",
    "ai platform engineer",
    "software engineer",
    "software development engineer",
    "backend engineer",
    "full stack engineer",
    "founding engineer",
    "founding software engineer",
    "data scientist",
)

DEFAULT_WEB_DISCOVERY_LOCATIONS = (
    "United States",
    "New York",
    "San Francisco",
    "Seattle",
    "Austin",
    "Chicago",
    "Boston",
    "Los Angeles",
    "Denver",
    "Atlanta",
)

DEFAULT_WEB_DISCOVERY_SITES = (
    "site:jobs.ashbyhq.com",
    "site:jobs.ashbyhq.com",
    "site:jobs.ashbyhq.com",
    "site:boards.greenhouse.io",
    "site:jobs.lever.co",
)

DEFAULT_WEB_DISCOVERY_QUERY_LIMIT = 150

SF_AI_STARTUP_WEB_DISCOVERY_QUERIES = (
    'site:jobs.ashbyhq.com "ai engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "applied ai engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "applied machine learning engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "founding applied ai engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "machine learning engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "ml engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "ai ml engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "llm engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "agentic ai engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "founding engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "founding software engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "member of technical staff" "San Francisco"',
    'site:jobs.ashbyhq.com "ml systems engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "ml infrastructure engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "ai platform engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "research engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "computer vision" "San Francisco"',
    'site:jobs.ashbyhq.com "robotics engineer" "San Francisco"',
    'site:jobs.ashbyhq.com "defense tech" "San Francisco"',
    'site:jobs.ashbyhq.com "deep tech" "San Francisco"',
    'site:jobs.ashbyhq.com "ai engineer" "Bay Area"',
    'site:jobs.ashbyhq.com "applied ai engineer" "Bay Area"',
    'site:jobs.ashbyhq.com "machine learning engineer" "Bay Area"',
    'site:jobs.ashbyhq.com "ml engineer" "Bay Area"',
    'site:jobs.ashbyhq.com "founding engineer" "Bay Area"',
    'site:jobs.ashbyhq.com "founding applied ai engineer" "Bay Area"',
    'site:jobs.ashbyhq.com "member of technical staff" "Bay Area"',
    'site:jobs.ashbyhq.com "ai engineer" "New York"',
    'site:jobs.ashbyhq.com "applied ai engineer" "New York"',
    'site:jobs.ashbyhq.com "machine learning engineer" "New York"',
    'site:jobs.ashbyhq.com "founding engineer" "New York"',
    'site:jobs.ashbyhq.com "software engineer" "New York"',
    'site:jobs.ashbyhq.com "member of technical staff" "New York"',
    'site:jobs.ashbyhq.com "ai engineer" "Boston"',
    'site:jobs.ashbyhq.com "applied ai engineer" "Boston"',
    'site:jobs.ashbyhq.com "machine learning engineer" "Boston"',
    'site:jobs.ashbyhq.com "software engineer" "Boston"',
    'site:jobs.ashbyhq.com "ai engineer" "Seattle"',
    'site:jobs.ashbyhq.com "applied ai engineer" "Seattle"',
    'site:jobs.ashbyhq.com "machine learning engineer" "Seattle"',
    'site:boards.greenhouse.io "ai engineer" "San Francisco"',
    'site:boards.greenhouse.io "applied ai engineer" "San Francisco"',
    'site:boards.greenhouse.io "machine learning engineer" "San Francisco"',
    'site:boards.greenhouse.io "founding engineer" "New York"',
    'site:boards.greenhouse.io "applied ai engineer" "New York"',
    'site:boards.greenhouse.io "software engineer" "Boston"',
    'site:job-boards.greenhouse.io "ai engineer" "San Francisco"',
    'site:job-boards.greenhouse.io "applied ai engineer" "San Francisco"',
    'site:job-boards.greenhouse.io "machine learning engineer" "San Francisco"',
    'site:job-boards.greenhouse.io "founding engineer" "New York"',
    'site:job-boards.greenhouse.io "applied ai engineer" "New York"',
    'site:job-boards.greenhouse.io "software engineer" "Boston"',
    'site:jobs.ashbyhq.com "software engineer" "Denver"',
)


def _build_default_web_discovery_queries(
    limit: int = DEFAULT_WEB_DISCOVERY_QUERY_LIMIT,
) -> tuple[str, ...]:
    queries = list(SF_AI_STARTUP_WEB_DISCOVERY_QUERIES[:limit])
    index = 0
    while len(queries) < limit:
        role = DEFAULT_WEB_DISCOVERY_ROLES[index % len(DEFAULT_WEB_DISCOVERY_ROLES)]
        location = DEFAULT_WEB_DISCOVERY_LOCATIONS[
            (index // len(DEFAULT_WEB_DISCOVERY_ROLES)) % len(DEFAULT_WEB_DISCOVERY_LOCATIONS)
        ]
        site_query = DEFAULT_WEB_DISCOVERY_SITES[index % len(DEFAULT_WEB_DISCOVERY_SITES)]
        query = f'{site_query} "{role}" "{location}"'
        if query not in queries:
            queries.append(query)
        index += 1
    return tuple(queries)


DEFAULT_WEB_DISCOVERY_QUERIES = _build_default_web_discovery_queries()


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
