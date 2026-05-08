"""Curated fallback ATS sources for high-value startup discovery."""

from __future__ import annotations

from job_crawler.discovery.sources import DiscoveredSource

SEED_DISCOVERY_LABEL = "curated sf/bay area ai startup seed"


def _ashby(slug: str) -> DiscoveredSource:
    base_url = f"https://jobs.ashbyhq.com/{slug}"
    return DiscoveredSource(
        source_type="ashby",
        slug=slug,
        base_url=base_url,
        discovered_from=SEED_DISCOVERY_LABEL,
        result_url=base_url,
    )


SF_AI_STARTUP_SEED_SOURCES = (
    _ashby("8vc"),
    _ashby("automat"),
    _ashby("baseten"),
    _ashby("browserbase"),
    _ashby("cartesia"),
    _ashby("casap"),
    _ashby("cursor"),
    _ashby("decagon"),
    _ashby("effective-ai"),
    _ashby("eloquentai"),
    _ashby("factory"),
    _ashby("fal"),
    _ashby("fractional-ai"),
    _ashby("gumloop"),
    _ashby("harvey"),
    _ashby("iambic-therapeutics"),
    _ashby("julius"),
    _ashby("kindred"),
    _ashby("langchain"),
    _ashby("litellm"),
    _ashby("lotushealth"),
    _ashby("mechanize"),
    _ashby("mercator"),
    _ashby("mercor"),
    _ashby("modal"),
    _ashby("nen"),
    _ashby("norm-ai"),
    _ashby("perplexity"),
    _ashby("pingo-ai"),
    _ashby("poesis"),
    _ashby("pytho-ai"),
    _ashby("quintess-ai"),
    _ashby("relace"),
    _ashby("sierra"),
    _ashby("togetherai"),
    _ashby("vapi"),
)
