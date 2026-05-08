"""Dynamic company and source discovery."""

from job_crawler.discovery.pages import extract_sources_from_html, fetch_sources_from_pages
from job_crawler.discovery.queries import (
    DEFAULT_LOCATION_QUERIES,
    DEFAULT_ROLE_QUERIES,
    DEFAULT_WEB_DISCOVERY_LOCATIONS,
    DEFAULT_WEB_DISCOVERY_QUERIES,
    DEFAULT_WEB_DISCOVERY_QUERY_LIMIT,
    DEFAULT_WEB_DISCOVERY_ROLES,
    DEFAULT_WEB_DISCOVERY_SITES,
    SF_AI_STARTUP_WEB_DISCOVERY_QUERIES,
    SOURCE_SITE_QUERIES,
    build_discovery_queries,
)
from job_crawler.discovery.seeds import SF_AI_STARTUP_SEED_SOURCES
from job_crawler.discovery.sources import (
    DiscoveredSource,
    extract_source_from_url,
    extract_sources_from_urls,
)
from job_crawler.discovery.web_search import (
    discover_sources_from_web_search,
    fetch_search_result_urls,
)

__all__ = [
    "DEFAULT_LOCATION_QUERIES",
    "DEFAULT_ROLE_QUERIES",
    "DEFAULT_WEB_DISCOVERY_LOCATIONS",
    "DEFAULT_WEB_DISCOVERY_QUERIES",
    "DEFAULT_WEB_DISCOVERY_QUERY_LIMIT",
    "DEFAULT_WEB_DISCOVERY_ROLES",
    "DEFAULT_WEB_DISCOVERY_SITES",
    "SOURCE_SITE_QUERIES",
    "SF_AI_STARTUP_SEED_SOURCES",
    "SF_AI_STARTUP_WEB_DISCOVERY_QUERIES",
    "DiscoveredSource",
    "build_discovery_queries",
    "extract_sources_from_html",
    "fetch_sources_from_pages",
    "discover_sources_from_web_search",
    "fetch_search_result_urls",
    "extract_source_from_url",
    "extract_sources_from_urls",
]
