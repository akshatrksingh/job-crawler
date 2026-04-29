from __future__ import annotations

from job_crawler.crawlers.ashby import build_ashby_url, parse_ashby_jobs
from job_crawler.crawlers.greenhouse import build_greenhouse_url, parse_greenhouse_jobs
from job_crawler.crawlers.lever import build_lever_url, parse_lever_jobs


def test_parse_ashby_jobs_normalizes_listed_jobs() -> None:
    payload = {
        "apiVersion": "1",
        "jobs": [
            {
                "id": "abc123",
                "title": "AI Engineer, New Grad",
                "location": "San Francisco",
                "secondaryLocations": [{"location": "New York"}],
                "isRemote": True,
                "isListed": True,
                "jobUrl": "https://jobs.ashbyhq.com/example/abc123",
                "descriptionHtml": "<p>Build agent workflows.</p>",
                "publishedDate": "2026-04-20T10:00:00.000Z",
            },
            {
                "id": "hidden",
                "title": "Hidden Role",
                "isListed": False,
            },
        ],
    }

    jobs = parse_ashby_jobs(payload, slug="example", company="Example Co")

    assert len(jobs) == 1
    assert jobs[0].source == "ashby"
    assert jobs[0].source_id == "abc123"
    assert jobs[0].company == "Example Co"
    assert jobs[0].title == "AI Engineer, New Grad"
    assert jobs[0].location == "San Francisco, New York, Remote"
    assert jobs[0].description == "Build agent workflows."
    assert jobs[0].posted_at is not None


def test_parse_greenhouse_jobs_normalizes_jobs_with_content() -> None:
    payload = {
        "jobs": [
            {
                "id": 127817,
                "title": "Software Engineer I",
                "location": {"name": "New York, NY"},
                "absolute_url": "https://boards.greenhouse.io/example/jobs/127817",
                "content": "Work on ML systems. &lt;p&gt;Python&lt;/p&gt;",
            }
        ]
    }

    jobs = parse_greenhouse_jobs(payload, board_token="example", company="Example Co")

    assert len(jobs) == 1
    assert jobs[0].source == "greenhouse"
    assert jobs[0].source_id == "127817"
    assert jobs[0].company == "Example Co"
    assert jobs[0].title == "Software Engineer I"
    assert jobs[0].location == "New York, NY"
    assert jobs[0].url == "https://boards.greenhouse.io/example/jobs/127817"
    assert "Python" in jobs[0].description


def test_parse_lever_jobs_normalizes_all_locations() -> None:
    payload = [
        {
            "id": "posting-1",
            "text": "Machine Learning Engineer",
            "hostedUrl": "https://jobs.lever.co/example/posting-1",
            "categories": {
                "location": "San Francisco, CA",
                "allLocations": ["San Francisco, CA", "Remote"],
            },
            "descriptionPlain": "Train and ship applied AI models.",
            "createdAt": 1_777_000_000_000,
        }
    ]

    jobs = parse_lever_jobs(payload, site="example", company="Example Co")

    assert len(jobs) == 1
    assert jobs[0].source == "lever"
    assert jobs[0].source_id == "posting-1"
    assert jobs[0].company == "Example Co"
    assert jobs[0].title == "Machine Learning Engineer"
    assert jobs[0].location == "San Francisco, CA, Remote"
    assert jobs[0].posted_at is not None


def test_ats_url_builders_use_public_api_endpoints() -> None:
    assert (
        build_ashby_url("example")
        == "https://api.ashbyhq.com/posting-api/job-board/example?includeCompensation=false"
    )
    assert (
        build_greenhouse_url("example")
        == "https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true"
    )
    assert (
        build_lever_url("example", limit=25)
        == "https://api.lever.co/v0/postings/example?mode=json&limit=25&skip=0"
    )
