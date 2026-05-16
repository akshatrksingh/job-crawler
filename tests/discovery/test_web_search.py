import httpx
import pytest

import job_crawler.discovery.web_search as web_search
from job_crawler.discovery.web_search import (
    _parse_duckduckgo_result_urls,
    _parse_google_result_urls,
    _parse_tavily_result_urls,
    discover_sources_from_web_search,
    fetch_search_result_urls,
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


def test_parse_tavily_result_urls_extracts_supported_ats_links() -> None:
    payload = {
        "results": [
            {"url": "https://jobs.ashbyhq.com/example-ai/role"},
            {"url": "https://example.com/careers"},
            {"url": "https://jobs.lever.co/example-labs/123"},
        ]
    }

    assert _parse_tavily_result_urls(payload, limit=5) == [
        "https://jobs.ashbyhq.com/example-ai/role",
        "https://jobs.lever.co/example-labs/123",
    ]


def test_discover_sources_from_web_search_dedupes_sources() -> None:
    def fake_fetcher(query: str, limit: int, use_tavily: bool):
        assert limit == 2
        assert use_tavily is False
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


def test_discover_sources_from_web_search_skips_query_http_errors() -> None:
    def fake_fetcher(query: str, limit: int, use_tavily: bool):
        if query == "bad":
            request = httpx.Request("GET", "https://example.com")
            response = httpx.Response(429)
            raise httpx.HTTPStatusError("rate limited", request=request, response=response)
        return ["https://jobs.ashbyhq.com/example-ai/one"]

    sources = discover_sources_from_web_search(
        queries=("bad", "good"),
        max_queries=2,
        results_per_query=2,
        fetcher=fake_fetcher,
    )

    assert [(source.source_type, source.slug) for source in sources] == [
        ("ashby", "example-ai")
    ]


def test_discover_sources_from_web_search_surfaces_tavily_http_errors() -> None:
    def fake_fetcher(query: str, limit: int, use_tavily: bool):
        request = httpx.Request("POST", "https://api.tavily.com/search")
        response = httpx.Response(401)
        raise httpx.HTTPStatusError("bad key", request=request, response=response)

    with pytest.raises(httpx.HTTPStatusError):
        discover_sources_from_web_search(
            queries=("ai engineer",),
            max_queries=1,
            results_per_query=2,
            fetcher=fake_fetcher,
        )


def test_discover_sources_from_web_search_skips_tavily_timeouts() -> None:
    def fake_fetcher(query: str, limit: int, use_tavily: bool):
        request = httpx.Request("POST", "https://api.tavily.com/search")
        raise httpx.ConnectTimeout("connect timed out", request=request)

    sources = discover_sources_from_web_search(
        queries=("ai engineer",),
        max_queries=1,
        results_per_query=2,
        fetcher=fake_fetcher,
    )

    assert sources == []


def test_discover_sources_from_web_search_honors_total_time_budget() -> None:
    calls = []

    def fake_fetcher(query: str, limit: int, use_tavily: bool):
        calls.append(query)
        return ["https://jobs.ashbyhq.com/example-ai/one"]

    sources = discover_sources_from_web_search(
        queries=("q1", "q2"),
        max_queries=2,
        results_per_query=2,
        max_seconds=0,
        fetcher=fake_fetcher,
    )

    assert sources == []
    assert calls == []


def test_fetch_search_result_urls_uses_tavily_when_enabled_and_key_is_set(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    calls = []

    def fake_tavily(query: str, limit: int, api_key: str) -> list[str]:
        calls.append(("tavily", query, limit, api_key))
        return ["https://jobs.ashbyhq.com/example-ai/role"]

    def fake_duckduckgo(query: str, limit: int) -> list[str]:
        calls.append(("duckduckgo", query, limit))
        return []

    monkeypatch.setattr(web_search, "_fetch_tavily_result_urls", fake_tavily)
    monkeypatch.setattr(web_search, "_fetch_duckduckgo_result_urls", fake_duckduckgo)

    assert fetch_search_result_urls(query="ai engineer", limit=4, use_tavily=True) == [
        "https://jobs.ashbyhq.com/example-ai/role"
    ]
    assert calls == [("tavily", "ai engineer", 4, "tvly-test")]


def test_fetch_search_result_urls_uses_duckduckgo_when_tavily_is_not_enabled(
    monkeypatch,
) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test")
    calls = []

    def fake_tavily(query: str, limit: int, api_key: str) -> list[str]:
        calls.append(("tavily", query, limit, api_key))
        return []

    def fake_duckduckgo(query: str, limit: int) -> list[str]:
        calls.append(("duckduckgo", query, limit))
        return ["https://jobs.ashbyhq.com/example-ai/role"]

    monkeypatch.setattr(web_search, "_fetch_tavily_result_urls", fake_tavily)
    monkeypatch.setattr(web_search, "_fetch_duckduckgo_result_urls", fake_duckduckgo)

    assert fetch_search_result_urls(query="ai engineer", limit=4) == [
        "https://jobs.ashbyhq.com/example-ai/role"
    ]
    assert calls == [("duckduckgo", "ai engineer", 4)]


def test_fetch_search_result_urls_uses_duckduckgo_without_tavily_key(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    calls = []

    def fake_tavily(query: str, limit: int, api_key: str) -> list[str]:
        calls.append(("tavily", query, limit, api_key))
        return []

    def fake_duckduckgo(query: str, limit: int) -> list[str]:
        calls.append(("duckduckgo", query, limit))
        return ["https://jobs.lever.co/example-labs/123"]

    monkeypatch.setattr(web_search, "_fetch_tavily_result_urls", fake_tavily)
    monkeypatch.setattr(web_search, "_fetch_duckduckgo_result_urls", fake_duckduckgo)

    assert fetch_search_result_urls(query="ai engineer", limit=4) == [
        "https://jobs.lever.co/example-labs/123"
    ]
    assert calls == [("duckduckgo", "ai engineer", 4)]


def test_fetch_search_result_urls_loads_tavily_key_from_local_env(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    (tmp_path / ".env").write_text("TAVILY_API_KEY=tvly-file\n", encoding="utf-8")
    calls = []

    def fake_tavily(query: str, limit: int, api_key: str) -> list[str]:
        calls.append(("tavily", query, limit, api_key))
        return ["https://jobs.ashbyhq.com/example-ai/role"]

    monkeypatch.setattr(web_search, "_fetch_tavily_result_urls", fake_tavily)
    monkeypatch.setattr(web_search, "_fetch_duckduckgo_result_urls", lambda **kwargs: [])

    assert fetch_search_result_urls(query="ai engineer", limit=4, use_tavily=True) == [
        "https://jobs.ashbyhq.com/example-ai/role"
    ]
    assert calls == [("tavily", "ai engineer", 4, "tvly-file")]
