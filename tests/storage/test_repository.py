from __future__ import annotations

from datetime import UTC, datetime

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


def test_insert_job_dedupes_same_role_across_sources() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)

        ats = repo.insert_job(
            make_job(
                source="ashby",
                source_id="ats-1",
                url="https://jobs.ashbyhq.com/example-company/ats-1",
            )
        )
        board = repo.insert_job(
            make_job(
                source="github_jobs",
                source_id="board-1",
                url="https://jobright.ai/jobs/info/board-1",
            )
        )

        assert ats.inserted is True
        assert board.inserted is False
        assert ats.job_id == board.job_id
        assert repo.count_rows("jobs") == 1


def test_insert_job_replaces_github_board_url_when_direct_source_arrives() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)

        board = repo.insert_job(
            make_job(
                source="github_jobs",
                source_id="board-1",
                url="https://jobright.ai/jobs/info/board-1",
            )
        )
        direct = repo.insert_job(
            make_job(
                source="ashby",
                source_id="ats-1",
                url="https://jobs.ashbyhq.com/example-company/ats-1?utm_source=board",
            )
        )
        row = connection.execute("SELECT url FROM jobs WHERE id = ?", (board.job_id,)).fetchone()

        assert direct.inserted is False
        assert row["url"] == "https://jobs.ashbyhq.com/example-company/ats-1"


def test_list_recent_jobs_includes_ids_and_delete_jobs_removes_selected_rows() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        first = repo.insert_job(make_job(source_id="job-1", title="AI Engineer"))
        second = repo.insert_job(make_job(source_id="job-2", title="Software Engineer"))

        jobs = repo.list_recent_jobs()
        deleted = repo.delete_jobs([first.job_id, 999])

        assert {job.id for job in jobs} == {first.job_id, second.job_id}
        assert deleted == 1
        assert [job.id for job in repo.list_recent_jobs()] == [second.job_id]


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


def test_source_crawl_outcome_prioritizes_useful_sources() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        useful_id = repo.upsert_source(source_type="ashby", slug="useful")
        quiet_id = repo.upsert_source(source_type="ashby", slug="quiet")

        repo.record_source_crawl_outcome(
            source_id=useful_id,
            jobs_seen=10,
            jobs_inserted=3,
            now=datetime(2026, 5, 4, tzinfo=UTC),
        )
        repo.record_source_crawl_outcome(
            source_id=quiet_id,
            jobs_seen=10,
            jobs_inserted=0,
            now=datetime(2026, 5, 4, tzinfo=UTC),
        )

        rows = connection.execute(
            """
            SELECT slug, usefulness_score, consecutive_empty_runs, next_crawl_after
            FROM sources
            ORDER BY usefulness_score DESC
            """
        ).fetchall()

        assert [row["slug"] for row in rows] == ["useful", "quiet"]
        assert rows[0]["consecutive_empty_runs"] == 0
        assert rows[1]["consecutive_empty_runs"] == 1
        assert rows[0]["next_crawl_after"] == "2026-05-05 00:00:00"
        assert rows[1]["next_crawl_after"] == "2026-05-07 00:00:00"


def test_list_due_sources_skips_sources_until_next_crawl_time() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        due_id = repo.upsert_source(source_type="lever", slug="due")
        later_id = repo.upsert_source(source_type="lever", slug="later")
        repo.record_source_crawl_outcome(
            source_id=due_id,
            jobs_seen=0,
            jobs_inserted=0,
            now=datetime(2026, 4, 1, tzinfo=UTC),
        )
        repo.record_source_crawl_outcome(
            source_id=later_id,
            jobs_seen=0,
            jobs_inserted=0,
            now=datetime(2026, 5, 4, tzinfo=UTC),
        )

        due_sources = repo.list_due_sources(
            source_type="lever",
            limit=10,
            now=datetime(2026, 5, 4, tzinfo=UTC),
        )

        assert [row["slug"] for row in due_sources] == ["due"]


def test_cleanup_stale_crawl_runs_marks_abandoned_rows_failed() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        run_id = repo.start_crawl_run(source_type="ashby")
        connection.execute(
            "UPDATE crawl_runs SET started_at = '2026-05-04 00:00:00' WHERE id = ?",
            (run_id,),
        )
        connection.commit()

        cleaned = repo.cleanup_stale_crawl_runs(stale_after_minutes=30)

        row = connection.execute(
            "SELECT status, error FROM crawl_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        assert cleaned == 1
        assert row["status"] == "failed"
        assert "stale running crawl" in row["error"]


def test_list_recent_crawl_runs_includes_source_slug() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        source_id = repo.upsert_source(
            source_type="ashby",
            slug="example-company",
            base_url="https://jobs.ashbyhq.com/example-company",
        )
        run_id = repo.start_crawl_run(source_type="ashby", source_id=source_id)
        repo.finish_crawl_run(
            crawl_run_id=run_id,
            status="failed",
            jobs_seen=3,
            jobs_inserted=1,
            error="network issue",
        )

        runs = repo.list_recent_crawl_runs()

        assert len(runs) == 1
        assert runs[0]["source_type"] == "ashby"
        assert runs[0]["source_slug"] == "example-company"
        assert runs[0]["error"] == "network issue"


def test_list_recent_crawl_runs_hides_removed_google_jobs_by_default() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        google_run = repo.start_crawl_run(source_type="google_jobs")
        repo.finish_crawl_run(
            crawl_run_id=google_run,
            status="failed",
            jobs_seen=0,
            jobs_inserted=0,
            error="rate limited",
        )
        hn_run = repo.start_crawl_run(source_type="hn")
        repo.finish_crawl_run(
            crawl_run_id=hn_run,
            status="succeeded",
            jobs_seen=3,
            jobs_inserted=2,
        )

        runs = repo.list_recent_crawl_runs()

        assert [run["source_type"] for run in runs] == ["hn"]
