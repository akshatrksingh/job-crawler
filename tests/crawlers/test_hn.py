from job_crawler.crawlers.hn import (
    build_hn_thread_comments_params,
    build_hn_who_is_hiring_thread_params,
    parse_hn_who_is_hiring_comments,
    parse_hn_who_is_hiring_threads,
)


def test_build_hn_algolia_params_are_bounded() -> None:
    assert build_hn_who_is_hiring_thread_params(hits_per_page=2) == {
        "tags": "story",
        "query": "Ask HN: Who is hiring?",
        "hitsPerPage": 2,
    }
    assert build_hn_thread_comments_params("123", hits_per_page=25) == {
        "tags": "comment,story_123",
        "hitsPerPage": 25,
    }


def test_parse_hn_who_is_hiring_threads_filters_titles() -> None:
    payload = {
        "hits": [
            {"objectID": "1", "title": "Ask HN: Who is hiring? (April 2026)"},
            {"objectID": "2", "title": "Ask HN: Who wants to be hired?"},
        ]
    }

    assert parse_hn_who_is_hiring_threads(payload) == [
        {"objectID": "1", "title": "Ask HN: Who is hiring? (April 2026)"}
    ]


def test_parse_hn_comments_normalizes_job_like_comments() -> None:
    payload = {
        "hits": [
            {
                "objectID": "456",
                "comment_text": (
                    "Example AI | AI Engineer | NYC / Remote | Full-time<br>"
                    "We build agent tools with Python."
                ),
                "created_at": "2026-04-01T12:00:00Z",
            }
        ]
    }

    jobs = parse_hn_who_is_hiring_comments(
        payload,
        thread_title="Ask HN: Who is hiring? (April 2026)",
    )

    assert len(jobs) == 1
    assert jobs[0].source == "hn"
    assert jobs[0].source_id == "456"
    assert jobs[0].company == "Example AI"
    assert jobs[0].title == "AI Engineer"
    assert jobs[0].location == "NYC / Remote"
    assert jobs[0].url == "https://news.ycombinator.com/item?id=456"
    assert "agent tools" in jobs[0].description
