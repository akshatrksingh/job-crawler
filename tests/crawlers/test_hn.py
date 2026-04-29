from job_crawler.crawlers.hn import parse_hn_comment, parse_hn_thread


def test_parse_hn_comment_extracts_company_role_location_and_url() -> None:
    comment = {
        "id": 123,
        "created_at": "2026-04-01T15:30:00Z",
        "text": """
        Example AI | Applied AI Engineer, Backend Engineer | New York, NY | ONSITE
        <p>We're hiring engineers to build LLM agents for finance workflows.</p>
        <p>Apply: <a href="https://example.ai/careers/ai-engineer">careers</a></p>
        """,
    }

    job = parse_hn_comment(comment)

    assert job is not None
    assert job.source == "hn"
    assert job.source_id == "123"
    assert job.company == "Example AI"
    assert job.title == "Applied AI Engineer, Backend Engineer"
    assert job.location == "New York, NY"
    assert job.url == "https://example.ai/careers/ai-engineer"
    assert job.posted_at is not None


def test_parse_hn_comment_uses_hn_link_when_no_external_url() -> None:
    comment = {
        "id": 456,
        "text": """
        Tiny Labs | Machine Learning Engineer | Remote (US)
        <p>We are hiring for ML infrastructure and agent workflows.</p>
        """,
    }

    job = parse_hn_comment(comment)

    assert job is not None
    assert job.url == "https://news.ycombinator.com/item?id=456"
    assert job.location == "United States"


def test_parse_hn_comment_skips_reply_noise() -> None:
    assert parse_hn_comment({"id": 789, "text": "Interested, just applied."}) is None


def test_parse_hn_thread_limits_to_top_level_matching_comments() -> None:
    payload = {
        "children": [
            {
                "id": 1,
                "text": "Company One | AI Engineer | Boston<p>We are hiring AI engineers.</p>",
            },
            {"id": 2, "text": "thanks!"},
            {
                "id": 3,
                "text": "Company Two | Software Engineer | Seattle<p>Open roles for SWE.</p>",
            },
        ]
    }

    jobs = parse_hn_thread(payload, limit=1)

    assert len(jobs) == 1
    assert jobs[0].company == "Company One"
