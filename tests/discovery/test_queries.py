from job_crawler.discovery import build_discovery_queries


def test_build_discovery_queries_is_bounded_and_google_style() -> None:
    queries = build_discovery_queries(
        roles=("machine learning engineer",),
        locations=("San Francisco", "remote"),
        source_types=("ashby", "lever"),
        limit=3,
    )

    assert queries == [
        "site:jobs.ashbyhq.com machine learning engineer San Francisco",
        "site:jobs.ashbyhq.com machine learning engineer remote",
        "site:jobs.lever.co machine learning engineer San Francisco",
    ]


def test_build_discovery_queries_interleaves_sources_before_next_role() -> None:
    queries = build_discovery_queries(
        roles=("ai engineer", "data scientist"),
        locations=("United States",),
        source_types=("ashby", "greenhouse", "lever"),
        limit=4,
    )

    assert queries == [
        "site:jobs.ashbyhq.com ai engineer United States",
        "site:boards.greenhouse.io ai engineer United States",
        "site:jobs.lever.co ai engineer United States",
        "site:jobs.ashbyhq.com data scientist United States",
    ]
