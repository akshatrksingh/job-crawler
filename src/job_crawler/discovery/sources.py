"""Extract ATS source slugs from search result URLs."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlsplit


@dataclass(frozen=True)
class DiscoveredSource:
    """A source discovered from a search result URL."""

    source_type: str
    slug: str
    base_url: str
    discovered_from: str
    result_url: str


def extract_source_from_url(url: str, *, discovered_from: str) -> DiscoveredSource | None:
    """Extract one supported ATS source from a URL, if possible."""
    parsed = urlsplit(url.strip())
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    path_parts = [part for part in parsed.path.split("/") if part]

    if hostname == "jobs.ashbyhq.com" and path_parts:
        slug = path_parts[0]
        return DiscoveredSource(
            source_type="ashby",
            slug=slug,
            base_url=f"https://jobs.ashbyhq.com/{slug}",
            discovered_from=discovered_from,
            result_url=url,
        )

    if hostname == "jobs.lever.co" and path_parts:
        slug = path_parts[0]
        return DiscoveredSource(
            source_type="lever",
            slug=slug,
            base_url=f"https://jobs.lever.co/{slug}",
            discovered_from=discovered_from,
            result_url=url,
        )

    if hostname == "boards.greenhouse.io" and path_parts:
        query = parse_qs(parsed.query)
        slug = _first_query_value(query, "for") or path_parts[0]
        return DiscoveredSource(
            source_type="greenhouse",
            slug=slug,
            base_url=f"https://boards.greenhouse.io/{slug}",
            discovered_from=discovered_from,
            result_url=url,
        )

    if hostname == "job-boards.greenhouse.io":
        query = parse_qs(parsed.query)
        slug = _first_query_value(query, "for")
        if slug:
            return DiscoveredSource(
                source_type="greenhouse",
                slug=slug,
                base_url=f"https://boards.greenhouse.io/{slug}",
                discovered_from=discovered_from,
                result_url=url,
            )

    return None


def extract_sources_from_urls(
    urls: list[str],
    *,
    discovered_from: str,
) -> list[DiscoveredSource]:
    """Extract and dedupe supported ATS sources from URLs."""
    discovered: dict[tuple[str, str], DiscoveredSource] = {}
    for url in urls:
        source = extract_source_from_url(url, discovered_from=discovered_from)
        if source is None:
            continue
        discovered.setdefault((source.source_type, source.slug), source)
    return list(discovered.values())


def _first_query_value(query: dict[str, list[str]], key: str) -> str | None:
    values = query.get(key)
    if not values:
        return None
    return values[0] or None
