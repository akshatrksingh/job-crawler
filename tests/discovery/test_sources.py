from job_crawler.discovery import extract_source_from_url, extract_sources_from_urls
from job_crawler.storage import JobRepository, open_database


def test_extract_ashby_source_from_job_url() -> None:
    source = extract_source_from_url(
        "https://jobs.ashbyhq.com/example-company/abc123?utm_source=google",
        discovered_from="site:jobs.ashbyhq.com ai engineer remote",
    )

    assert source is not None
    assert source.source_type == "ashby"
    assert source.slug == "example-company"
    assert source.base_url == "https://jobs.ashbyhq.com/example-company"


def test_extract_greenhouse_source_from_board_url() -> None:
    source = extract_source_from_url(
        "https://boards.greenhouse.io/examplecompany/jobs/123",
        discovered_from="site:boards.greenhouse.io software engineer New York",
    )

    assert source is not None
    assert source.source_type == "greenhouse"
    assert source.slug == "examplecompany"
    assert source.base_url == "https://boards.greenhouse.io/examplecompany"


def test_extract_greenhouse_source_from_embed_url() -> None:
    source = extract_source_from_url(
        "https://job-boards.greenhouse.io/embed/job_board?for=examplecompany",
        discovered_from="site:boards.greenhouse.io ai engineer",
    )

    assert source is not None
    assert source.source_type == "greenhouse"
    assert source.slug == "examplecompany"


def test_extract_lever_source_from_posting_url() -> None:
    source = extract_source_from_url(
        "https://jobs.lever.co/example-company/posting-1",
        discovered_from="site:jobs.lever.co machine learning engineer",
    )

    assert source is not None
    assert source.source_type == "lever"
    assert source.slug == "example-company"
    assert source.base_url == "https://jobs.lever.co/example-company"


def test_extract_sources_dedupes_by_source_type_and_slug() -> None:
    discovered = extract_sources_from_urls(
        [
            "https://jobs.ashbyhq.com/example/one",
            "https://jobs.ashbyhq.com/example/two",
            "https://jobs.lever.co/example/three",
            "https://www.example.com/careers",
        ],
        discovered_from="unit-test",
    )

    assert [(source.source_type, source.slug) for source in discovered] == [
        ("ashby", "example"),
        ("lever", "example"),
    ]


def test_store_discovered_sources_in_sqlite() -> None:
    discovered = extract_sources_from_urls(
        [
            "https://jobs.ashbyhq.com/example/one",
            "https://boards.greenhouse.io/acme/jobs/123",
        ],
        discovered_from="unit-test-query",
    )

    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        for source in discovered:
            repo.upsert_discovered_source(source)
            repo.upsert_discovered_source(source)

        rows = repo.list_sources()

        assert repo.count_rows("sources") == 2
        assert [(row["source_type"], row["slug"]) for row in rows] == [
            ("ashby", "example"),
            ("greenhouse", "acme"),
        ]
        assert rows[0]["discovered_from"] == "unit-test-query"
