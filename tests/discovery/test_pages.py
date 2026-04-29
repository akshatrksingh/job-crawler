from job_crawler.discovery.pages import extract_sources_from_html


def test_extract_sources_from_html_finds_linked_ats_pages() -> None:
    html = """
<a href="https://jobs.ashbyhq.com/example-ai">Jobs</a>
<a href="/about">About</a>
<a href="https://jobs.lever.co/example-labs/abc">Backend Engineer</a>
<a href="https://job-boards.greenhouse.io/example/jobs/123">ML Engineer</a>
"""

    sources = extract_sources_from_html(
        html,
        page_url="https://example.com/careers",
        discovered_from="career page",
    )

    assert [(source.source_type, source.slug) for source in sources] == [
        ("ashby", "example-ai"),
        ("lever", "example-labs"),
        ("greenhouse", "example"),
    ]
