"""Curated fallback ATS sources for high-value startup discovery."""

from __future__ import annotations

from job_crawler.discovery.sources import DiscoveredSource

SEED_DISCOVERY_LABEL = "curated ai startup ats seed"


def _ashby(slug: str) -> DiscoveredSource:
    base_url = f"https://jobs.ashbyhq.com/{slug}"
    return DiscoveredSource(
        source_type="ashby",
        slug=slug,
        base_url=base_url,
        discovered_from=SEED_DISCOVERY_LABEL,
        result_url=base_url,
    )


def _greenhouse(slug: str) -> DiscoveredSource:
    base_url = f"https://job-boards.greenhouse.io/{slug}"
    return DiscoveredSource(
        source_type="greenhouse",
        slug=slug,
        base_url=base_url,
        discovered_from=SEED_DISCOVERY_LABEL,
        result_url=base_url,
    )


SF_AI_STARTUP_SEED_SOURCES = (
    _ashby("additiveai"),
    _ashby("appliedlabs"),
    _ashby("asari.ai"),
    _ashby("8vc"),
    _ashby("atlas"),
    _ashby("automat"),
    _ashby("avallon"),
    _ashby("baseten"),
    _ashby("browserbase"),
    _ashby("cartesia"),
    _ashby("casap"),
    _ashby("chroma"),
    _ashby("coframe"),
    _ashby("cursor"),
    _ashby("decagon"),
    _ashby("Edison%20Scientific"),
    _ashby("effective-ai"),
    _ashby("eloquentai"),
    _ashby("factory"),
    _ashby("fal"),
    _ashby("fractional-ai"),
    _ashby("fulcrum-inc"),
    _ashby("gimlet"),
    _ashby("gumloop"),
    _ashby("harvey"),
    _ashby("iambic-therapeutics"),
    _ashby("jampack-ai"),
    _ashby("julius"),
    _ashby("kindred"),
    _ashby("langchain"),
    _ashby("legionhealth"),
    _ashby("litellm"),
    _ashby("lotushealth"),
    _ashby("maven-agi"),
    _ashby("mechanize"),
    _ashby("mercator"),
    _ashby("mercor"),
    _ashby("modal"),
    _ashby("nen"),
    _ashby("norm-ai"),
    _ashby("omnea"),
    _ashby("perplexity"),
    _ashby("phylo"),
    _ashby("pingo-ai"),
    _ashby("pluto"),
    _ashby("poesis"),
    _ashby("pytho-ai"),
    _ashby("quintess-ai"),
    _ashby("relace"),
    _ashby("rye"),
    _ashby("sierra"),
    _ashby("simile"),
    _ashby("stably.ai"),
    _ashby("suno"),
    _ashby("togetherai"),
    _ashby("trychroma"),
    _ashby("vapi"),
    _greenhouse("amplitude"),
    _greenhouse("anthropic"),
    _greenhouse("applytobreadboard"),
    _greenhouse("applytopario"),
    _greenhouse("cookunity"),
    _greenhouse("join3yhealth"),
    _greenhouse("mindsdb"),
    _greenhouse("perplexityai"),
    _greenhouse("roivantsciences"),
    _greenhouse("snyk"),
    _greenhouse("starburst"),
    _greenhouse("weave"),
)
