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
