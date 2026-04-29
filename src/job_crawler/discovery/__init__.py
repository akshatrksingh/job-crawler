"""Dynamic company and source discovery."""

from job_crawler.discovery.queries import (
    DEFAULT_LOCATION_QUERIES,
    DEFAULT_ROLE_QUERIES,
    SOURCE_SITE_QUERIES,
    build_discovery_queries,
)
from job_crawler.discovery.sources import (
    DiscoveredSource,
    extract_source_from_url,
    extract_sources_from_urls,
)

__all__ = [
    "DEFAULT_LOCATION_QUERIES",
    "DEFAULT_ROLE_QUERIES",
    "SOURCE_SITE_QUERIES",
    "DiscoveredSource",
    "build_discovery_queries",
    "extract_source_from_url",
    "extract_sources_from_urls",
]
