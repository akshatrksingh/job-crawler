from datetime import UTC, datetime, timedelta

from job_crawler.crawlers.base import JobPosting
from job_crawler.pipeline import refresh_jobs, refresh_yc
from job_crawler.storage import JobRepository, open_database


def make_job(source: str, source_id: str, title: str) -> JobPosting:
    return JobPosting(
        source=source,
        source_id=source_id,
        company=f"{source.upper()} Co",
        title=title,
        location="New York, NY",
        url=f"https://example.com/{source}/{source_id}",
        description="Entry level AI role.",
    )


def test_refresh_yc_fetches_dedupes_and_writes_dashboard(tmp_path) -> None:
    db_path = tmp_path / "jobs.sqlite"
    output_path = tmp_path / "site" / "index.html"

    result = refresh_yc(
        db_path=db_path,
        output_path=output_path,
        yc_limit=2,
        yc_fetcher=lambda limit: [make_job("yc", "1", "Software Engineer I")],
    )
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        old_refresh = datetime.now(UTC) - timedelta(hours=7)
        repo.set_app_state("last_refresh_at", old_refresh.isoformat())
    second = refresh_yc(
        db_path=db_path,
        output_path=output_path,
        yc_limit=2,
        yc_fetcher=lambda limit: [make_job("yc", "1", "Software Engineer I")],
    )

    assert result.seen == 1
    assert result.inserted == 1
    assert second.seen == 1
    assert second.inserted == 0
    assert output_path.exists()
    assert "Software Engineer I" in output_path.read_text(encoding="utf-8")
    with open_database(db_path) as connection:
        assert JobRepository(connection).count_rows("jobs") == 1


def test_refresh_yc_uses_six_hour_cooldown(tmp_path) -> None:
    db_path = tmp_path / "jobs.sqlite"
    output_path = tmp_path / "site" / "index.html"
    refresh_yc(
        db_path=db_path,
        output_path=output_path,
        yc_fetcher=lambda limit: [make_job("yc", "1", "Software Engineer I")],
    )

    second = refresh_yc(
        db_path=db_path,
        output_path=output_path,
        yc_fetcher=lambda limit: [make_job("yc", "2", "AI Engineer")],
    )

    assert second.refreshed is False
    assert second.seen == 0
    assert second.inserted == 0
    assert second.cooldown_seconds_remaining > 0


def test_refresh_yc_records_source_errors(tmp_path) -> None:
    db_path = tmp_path / "jobs.sqlite"
    output_path = tmp_path / "site" / "index.html"

    def failing_fetcher(limit: int):
        raise RuntimeError("network issue")

    result = refresh_yc(
        db_path=db_path,
        output_path=output_path,
        yc_fetcher=failing_fetcher,
    )

    assert result.inserted == 0
    assert result.errors == ["network issue"]
    assert output_path.exists()


def test_refresh_jobs_fetches_stored_ats_sources(tmp_path) -> None:
    db_path = tmp_path / "jobs.sqlite"
    output_path = tmp_path / "site" / "index.html"
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        repo.upsert_source(
            source_type="ashby",
            slug="example-company",
            base_url="https://jobs.ashbyhq.com/example-company",
            discovered_from="unit-test",
        )
        repo.upsert_source(
            source_type="greenhouse",
            slug="example-gh",
            base_url="https://boards.greenhouse.io/example-gh",
            discovered_from="unit-test",
        )
        repo.upsert_source(
            source_type="lever",
            slug="example-lever",
            base_url="https://jobs.lever.co/example-lever",
            discovered_from="unit-test",
        )

    def fake_ashby_fetcher(slug: str, company: str, limit: int):
        assert slug == "example-company"
        assert company == "example-company"
        assert limit == 3
        return [make_job("ashby", "1", "AI Engineer")]

    def fake_greenhouse_fetcher(board_token: str, company: str, limit: int):
        assert board_token == "example-gh"
        assert company == "example-gh"
        assert limit == 3
        return [make_job("greenhouse", "1", "Software Engineer")]

    def fake_lever_fetcher(site: str, company: str, limit: int):
        assert site == "example-lever"
        assert company == "example-lever"
        assert limit == 3
        return [make_job("lever", "1", "Machine Learning Engineer")]

    def fake_google_fetcher(search_term: str, location: str, results_wanted: int):
        assert search_term == "software engineer"
        assert location == "United States"
        assert results_wanted == 2
        return [make_job("google_jobs", "1", "AI Engineer")]

    def fake_github_boards_fetcher(limit: int):
        assert limit == 4
        return [make_job("github_jobs", "1", "Software Engineer I")]

    result = refresh_jobs(
        db_path=db_path,
        output_path=output_path,
        ashby_limit=3,
        google_jobs_limit=2,
        github_jobs_limit=4,
        max_google_queries=1,
        ashby_fetcher=fake_ashby_fetcher,
        greenhouse_fetcher=fake_greenhouse_fetcher,
        lever_fetcher=fake_lever_fetcher,
        google_fetcher=fake_google_fetcher,
        github_boards_fetcher=fake_github_boards_fetcher,
    )

    assert result.seen == 5
    assert result.inserted == 5
    assert [source.source for source in result.sources] == [
        "ashby:example-company",
        "greenhouse:example-gh",
        "lever:example-lever",
        "google_jobs:software engineer:United States",
        "github_jobs:default_boards",
    ]
    assert output_path.exists()
    assert "AI Engineer" in output_path.read_text(encoding="utf-8")
