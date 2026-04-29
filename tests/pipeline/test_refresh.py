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
        assert slug in {"board-co", "discovered-ai", "example-company"}
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
        assert site in {"example-lever", "hn-ai"}
        assert company == site
        assert limit == 3
        return [make_job("lever", "1", "Machine Learning Engineer")]

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

    def fake_hn_fetcher(limit: int):
        assert limit == 6
        return [
            JobPosting(
                source="hn",
                source_id="1",
                company="HN Co",
                title="Applied AI Engineer",
                location="New York, NY",
                url="https://jobs.lever.co/hn-ai/job-1",
                description="Entry level AI role.",
            )
        ]

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
        github_jobs_limit=4,
        hn_limit=6,
        yc_limit=5,
        web_discovery_queries=2,
        web_discovery_results_per_query=3,
        ashby_fetcher=fake_ashby_fetcher,
        greenhouse_fetcher=fake_greenhouse_fetcher,
        lever_fetcher=fake_lever_fetcher,
        github_boards_fetcher=fake_github_boards_fetcher,
        hn_fetcher=fake_hn_fetcher,
        yc_fetcher=fake_yc_fetcher,
        web_discovery_fetcher=fake_web_discovery_fetcher,
    )

    assert result.seen == 10
    assert result.inserted == 9
    assert [source.source for source in result.sources] == [
        "web_search_discovery",
        "github_jobs:default_boards",
        "hn",
        "yc",
        "ashby:board-co",
        "ashby:discovered-ai",
        "ashby:example-company",
        "greenhouse:example-gh",
        "lever:example-lever",
        "lever:hn-ai",
    ]
    assert output_path.exists()
    assert "AI Engineer" in output_path.read_text(encoding="utf-8")
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        ashby_slugs = [row["slug"] for row in repo.list_sources(source_type="ashby")]
        lever_slugs = [row["slug"] for row in repo.list_sources(source_type="lever")]
        query_budget = repo.get_app_state("web_discovery_query_budget")
    assert "board-co" in ashby_slugs
    assert "discovered-ai" in ashby_slugs
    assert "hn-ai" in lever_slugs
    assert query_budget == "2"


def test_refresh_jobs_backs_off_web_discovery_query_budget_on_error(tmp_path) -> None:
    db_path = tmp_path / "jobs.sqlite"
    output_path = tmp_path / "site" / "index.html"
    with open_database(db_path) as connection:
        JobRepository(connection).set_app_state("web_discovery_query_budget", "40")

    def failing_web_discovery_fetcher(max_queries: int, results_per_query: int):
        assert max_queries == 40
        assert results_per_query == 3
        raise RuntimeError("tavily unavailable")

    result = refresh_jobs(
        db_path=db_path,
        output_path=output_path,
        github_jobs_limit=1,
        hn_limit=1,
        yc_limit=1,
        web_discovery_queries=99,
        web_discovery_results_per_query=3,
        max_sources=0,
        github_boards_fetcher=lambda limit: [],
        hn_fetcher=lambda limit: [],
        yc_fetcher=lambda limit: [],
        web_discovery_fetcher=failing_web_discovery_fetcher,
    )

    assert result.errors == ["tavily unavailable"]
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        assert repo.get_app_state("web_discovery_query_budget") == "30"


def test_refresh_jobs_never_backs_off_web_discovery_below_ten(tmp_path) -> None:
    db_path = tmp_path / "jobs.sqlite"
    output_path = tmp_path / "site" / "index.html"
    with open_database(db_path) as connection:
        JobRepository(connection).set_app_state("web_discovery_query_budget", "10")

    result = refresh_jobs(
        db_path=db_path,
        output_path=output_path,
        github_jobs_limit=1,
        hn_limit=1,
        yc_limit=1,
        web_discovery_queries=99,
        max_sources=0,
        github_boards_fetcher=lambda limit: [],
        hn_fetcher=lambda limit: [],
        yc_fetcher=lambda limit: [],
        web_discovery_fetcher=lambda max_queries, results_per_query: [],
    )

    assert result.errors == []
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        assert repo.get_app_state("web_discovery_query_budget") == "10"
