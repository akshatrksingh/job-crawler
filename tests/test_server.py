from pathlib import Path

from job_crawler.server import DashboardServerConfig, _build_handler


def test_dashboard_handler_can_be_constructed() -> None:
    handler = _build_handler(
        DashboardServerConfig(
            db_path=Path("data/job_crawler.sqlite"),
            output_path=Path("site/index.html"),
            days=14,
            candidate_limit=100,
            ashby_limit=10,
            google_jobs_limit=5,
            github_jobs_limit=25,
            max_google_queries=2,
            cooldown_hours=6,
        )
    )

    assert handler.__name__ == "DashboardRequestHandler"
