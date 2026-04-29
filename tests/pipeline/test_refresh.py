from datetime import UTC, datetime, timedelta

from job_crawler.crawlers.base import JobPosting
from job_crawler.discovery import DiscoveredSource
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
        assert slug in {"example-company", "discovered-ai"}
        assert company == slug
        assert limit == 3
        return [
            JobPosting(
                source="ashby",
                source_id=slug,
                company=slug,
                title="AI Engineer",
                location="New York, NY",
                url=f"https://jobs.ashbyhq.com/{slug}/job",
                description="Entry level AI role.",
            )
        ]

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
        assert search_term == "ai engineer"
        assert location == "United States"
        assert results_wanted == 2
        return [make_job("google_jobs", "1", "AI Engineer")]

    def fake_github_boards_fetcher(limit: int):
        assert limit == 4
        return [
            JobPosting(
                source="simplify_new_grad_positions",
                source_id="1",
                company="Board Co",
                title="Software Engineer I",
                location="New York, NY",
                url="https://jobs.ashbyhq.com/board-co/job-1/application",
                description="Entry level AI role.",
            )
        ]

    def fake_yc_fetcher(limit: int):
        assert limit == 5
        return [make_job("yc", "1", "Founding Engineer")]

    def fake_web_discovery_fetcher(max_queries: int, results_per_query: int):
        assert max_queries == 2
        assert results_per_query == 3
        return [
            DiscoveredSource(
                source_type="ashby",
                slug="discovered-ai",
                base_url="https://jobs.ashbyhq.com/discovered-ai",
                discovered_from="unit-test",
                result_url="https://jobs.ashbyhq.com/discovered-ai/job",
            )
        ]

    result = refresh_jobs(
        db_path=db_path,
        output_path=output_path,
        ashby_limit=3,
        google_jobs_limit=2,
        github_jobs_limit=4,
        yc_limit=5,
        max_google_queries=1,
        web_discovery_queries=2,
        web_discovery_results_per_query=3,
        ashby_fetcher=fake_ashby_fetcher,
        greenhouse_fetcher=fake_greenhouse_fetcher,
        lever_fetcher=fake_lever_fetcher,
        google_fetcher=fake_google_fetcher,
        github_boards_fetcher=fake_github_boards_fetcher,
        yc_fetcher=fake_yc_fetcher,
        web_discovery_fetcher=fake_web_discovery_fetcher,
    )

    assert result.seen == 8
    assert result.inserted == 8
    assert [source.source for source in result.sources] == [
        "web_search_discovery",
        "ashby:discovered-ai",
        "ashby:example-company",
        "greenhouse:example-gh",
        "lever:example-lever",
        "google_jobs:ai engineer:United States",
        "github_jobs:default_boards",
        "yc",
    ]
    assert output_path.exists()
    assert "AI Engineer" in output_path.read_text(encoding="utf-8")
    with open_database(db_path) as connection:
        slugs = [row["slug"] for row in JobRepository(connection).list_sources(source_type="ashby")]
    assert "board-co" in slugs
    assert "discovered-ai" in slugs
