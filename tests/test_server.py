from pathlib import Path

from job_crawler.server import DashboardServerConfig, _build_handler, _is_authorized


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
            hn_limit=10,
            yc_limit=10,
            max_google_queries=2,
            cooldown_hours=6,
            auth_username=None,
            auth_password=None,
        )
    )

    assert handler.__name__ == "DashboardRequestHandler"


def test_basic_auth_helper_is_opt_in_and_checks_credentials() -> None:
    open_config = DashboardServerConfig(
        db_path=Path("data/job_crawler.sqlite"),
        output_path=Path("site/index.html"),
        days=14,
        candidate_limit=100,
        ashby_limit=10,
        google_jobs_limit=5,
        github_jobs_limit=25,
        hn_limit=10,
        yc_limit=10,
        max_google_queries=2,
        cooldown_hours=6,
    )
    locked_config = DashboardServerConfig(
        db_path=Path("data/job_crawler.sqlite"),
        output_path=Path("site/index.html"),
        days=14,
        candidate_limit=100,
        ashby_limit=10,
        google_jobs_limit=5,
        github_jobs_limit=25,
        hn_limit=10,
        yc_limit=10,
        max_google_queries=2,
        cooldown_hours=6,
        auth_username="akshat",
        auth_password="secret",
    )

    assert _is_authorized(None, open_config)
    assert not _is_authorized(None, locked_config)
    assert _is_authorized("Basic YWtzaGF0OnNlY3JldA==", locked_config)
    assert not _is_authorized("Basic YWtzaGF0Ondyb25n", locked_config)


def test_dashboard_handler_allows_health_without_auth() -> None:
    handler = _build_handler(
        DashboardServerConfig(
            db_path=Path("data/job_crawler.sqlite"),
            output_path=Path("site/index.html"),
            days=14,
            candidate_limit=100,
            ashby_limit=10,
            google_jobs_limit=5,
            github_jobs_limit=25,
            hn_limit=10,
            yc_limit=10,
            max_google_queries=2,
            cooldown_hours=6,
            auth_username="akshat",
            auth_password="secret",
        )
    )

    assert handler.__name__ == "DashboardRequestHandler"
