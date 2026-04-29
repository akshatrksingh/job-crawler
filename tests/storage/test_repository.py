from __future__ import annotations

from job_crawler.crawlers.base import JobPosting
from job_crawler.storage import JobRepository, canonicalize_url, open_database


def make_job(**overrides: str) -> JobPosting:
    values = {
        "source": "ashby",
        "source_id": "job_123",
        "company": "Example Company",
        "title": "AI Engineer",
        "location": "San Francisco, CA",
        "url": "https://jobs.ashbyhq.com/example-company/job_123?utm_source=test",
        "description": "Build AI products.",
    }
    values.update(overrides)
    return JobPosting(**values)


def test_canonicalize_url_removes_query_and_trailing_slash() -> None:
    assert (
        canonicalize_url("HTTPS://Jobs.AshbyHQ.com/example-company/job_123/?utm_source=test")
        == "https://jobs.ashbyhq.com/example-company/job_123"
    )


def test_insert_job_is_idempotent_by_fingerprint() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)

        first = repo.insert_job(make_job(source_id="first-source-id"))
        second = repo.insert_job(make_job(source_id="different-source-id"))

        assert first.inserted is True
        assert second.inserted is False
        assert first.job_id == second.job_id
        assert repo.count_rows("jobs") == 1


def test_insert_job_allows_distinct_titles_for_same_company() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)

        first = repo.insert_job(make_job(title="AI Engineer"))
        second = repo.insert_job(make_job(source_id="job_456", title="Software Engineer"))

        assert first.inserted is True
        assert second.inserted is True
        assert repo.count_rows("jobs") == 2


def test_unscored_jobs_excludes_existing_model_prompt_scores() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        first = repo.insert_job(make_job(source_id="job_1", title="AI Engineer"))
        repo.insert_job(make_job(source_id="job_2", title="Software Engineer"))

        repo.insert_score(
            job_id=first.job_id,
            model="gpt-4o-mini",
            score=8.0,
            reason="Strong match",
        )

        unscored = repo.list_unscored_jobs(model="gpt-4o-mini")

        assert [row["title"] for row in unscored] == ["Software Engineer"]


def test_source_crawl_state_supports_rate_limit_friendly_reruns() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        source_id = repo.upsert_source(
            source_type="lever",
            slug="example-company",
            base_url="https://jobs.lever.co/example-company",
            discovered_from="unit-test",
            crawl_interval_seconds=43_200,
        )

        repo.mark_source_crawled(source_id=source_id, next_crawl_after="2026-04-30T12:00:00")

        row = connection.execute(
            """
            SELECT last_crawled_at, next_crawl_after, crawl_interval_seconds
            FROM sources
            WHERE id = ?
            """,
            (source_id,),
        ).fetchone()

        assert row["last_crawled_at"] is not None
        assert row["next_crawl_after"] == "2026-04-30T12:00:00"
        assert row["crawl_interval_seconds"] == 43_200
