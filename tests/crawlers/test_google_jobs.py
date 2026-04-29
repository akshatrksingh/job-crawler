from job_crawler.crawlers.google_jobs import (
    build_default_google_job_queries,
    parse_jobspy_records,
)


def test_parse_jobspy_records_normalizes_google_jobs() -> None:
    records = [
        {
            "id": "google-123",
            "title": "AI Engineer",
            "company": "Example AI",
            "location": "New York, NY",
            "job_url": "https://example.com/jobs/ai-engineer?utm_source=google",
            "description": "<p>Build AI agents.</p>",
            "date_posted": "2026-04-20",
        },
        {
            "title": "Missing URL",
            "company": "Nope",
        },
    ]

    jobs = parse_jobspy_records(records, query="ai engineer", location="Remote")

    assert len(jobs) == 1
    assert jobs[0].source == "google_jobs"
    assert jobs[0].source_id == "google-123"
    assert jobs[0].company == "Example AI"
    assert jobs[0].title == "AI Engineer"
    assert jobs[0].location == "New York, NY"
    assert jobs[0].url == "https://example.com/jobs/ai-engineer?utm_source=google"
    assert jobs[0].description == "Build AI agents."


def test_parse_jobspy_records_uses_fallback_location_and_source_id() -> None:
    jobs = parse_jobspy_records(
        [
            {
                "title": "Software Engineer I",
                "company_name": "Example Co",
                "url": "https://example.com/jobs/swe",
            }
        ],
        query="software engineer new grad",
        location="Remote",
    )

    assert len(jobs) == 1
    assert jobs[0].source_id == "Example Co:Software Engineer I:https://example.com/jobs/swe"
    assert jobs[0].location == "Remote"


def test_build_default_google_job_queries_is_bounded() -> None:
    pairs = build_default_google_job_queries(
        search_terms=("ai engineer", "software engineer"),
        locations=("Remote", "New York"),
        limit=3,
    )

    assert pairs == [
        ("ai engineer", "Remote"),
        ("ai engineer", "New York"),
        ("software engineer", "Remote"),
    ]
