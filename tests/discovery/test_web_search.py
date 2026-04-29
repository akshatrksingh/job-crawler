from job_crawler.discovery.web_search import (
    _parse_duckduckgo_result_urls,
    _parse_google_result_urls,
    discover_sources_from_web_search,
)


def test_parse_google_result_urls_extracts_supported_ats_links() -> None:
    html = """
<a href="/url?q=https://jobs.ashbyhq.com/example-ai/role&sa=U">Ashby</a>
<a href="/url?q=https://example.com/careers&sa=U">Other</a>
<a href="https://jobs.lever.co/example-labs/123">Lever</a>
"""

    assert _parse_google_result_urls(html, limit=5) == [
        "https://jobs.ashbyhq.com/example-ai/role",
        "https://jobs.lever.co/example-labs/123",
    ]


def test_parse_duckduckgo_result_urls_extracts_supported_ats_links() -> None:
    html = (
        '<a class="result__a" href="//duckduckgo.com/l/?uddg='
        'https%3A%2F%2Fboards.greenhouse.io%2Fexample%2Fjobs%2F123">Greenhouse</a>'
    )

    assert _parse_duckduckgo_result_urls(html, limit=5) == [
        "https://boards.greenhouse.io/example/jobs/123"
    ]


def test_discover_sources_from_web_search_dedupes_sources() -> None:
    def fake_fetcher(query: str, limit: int):
        assert limit == 2
        return [
            "https://jobs.ashbyhq.com/example-ai/one",
            "https://jobs.ashbyhq.com/example-ai/two",
            "https://jobs.lever.co/example-labs/123",
        ]

    sources = discover_sources_from_web_search(
        queries=("q1", "q2"),
        max_queries=2,
        results_per_query=2,
        fetcher=fake_fetcher,
    )

    assert [(source.source_type, source.slug) for source in sources] == [
        ("ashby", "example-ai"),
        ("lever", "example-labs"),
    ]
