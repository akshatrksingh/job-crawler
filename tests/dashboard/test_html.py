from datetime import UTC, date, datetime, timedelta

from job_crawler.crawlers.base import JobPosting
from job_crawler.dashboard import render_dashboard, write_dashboard
from job_crawler.dashboard.html import select_dashboard_jobs


def make_job(
    title: str,
    company: str,
    location: str,
    posted_at: datetime,
) -> JobPosting:
    return JobPosting(
        source="fixture",
        source_id=f"{company}-{title}",
        company=company,
        title=title,
        location=location,
        url=f"https://example.com/{company}/{title}".replace(" ", "-"),
        description="Entry level AI engineering role.",
        posted_at=posted_at,
    )


def test_select_dashboard_jobs_keeps_only_last_14_days() -> None:
    today = date(2026, 4, 29)
    fresh = make_job(
        "AI Engineer",
        "Fresh Co",
        "New York, NY",
        datetime(2026, 4, 20, tzinfo=UTC),
    )
    old = make_job(
        "AI Engineer",
        "Old Co",
        "New York, NY",
        datetime(2026, 4, 1, tzinfo=UTC),
    )

    selected = select_dashboard_jobs([fresh, old], today=today, days=14)

    assert [job.company for job in selected] == ["Fresh Co"]


def test_render_dashboard_includes_filters_and_no_hard_limit() -> None:
    today = date(2026, 4, 29)
    jobs = [
        make_job(
            f"Software Engineer I {index}",
            f"Company {index}",
            "Seattle, WA",
            datetime.combine(today - timedelta(days=1), datetime.min.time(), tzinfo=UTC),
        )
        for index in range(30)
    ]

    html = render_dashboard(jobs, today=today, days=14)

    assert html.count("<tr data-search=") == 30
    assert 'id="search"' in html
    assert 'id="city"' in html
    assert 'id="source"' in html
    assert "Seattle, WA" in html


def test_render_dashboard_excludes_senior_roles() -> None:
    today = date(2026, 4, 29)
    jobs = [
        make_job(
            "Senior AI Engineer",
            "Senior Co",
            "New York, NY",
            datetime(2026, 4, 28, tzinfo=UTC),
        ),
        make_job(
            "Software Engineer I",
            "Junior Co",
            "Boston, MA",
            datetime(2026, 4, 28, tzinfo=UTC),
        ),
    ]

    html = render_dashboard(jobs, today=today)

    assert "Senior Co" not in html
    assert "Junior Co" in html


def test_write_dashboard_creates_index_html(tmp_path) -> None:
    path = write_dashboard(
        [
            make_job(
                "AI Engineer",
                "Example Co",
                "Austin, TX",
                datetime(2026, 4, 28, tzinfo=UTC),
            )
        ],
        output_path=tmp_path / "index.html",
        today=date(2026, 4, 29),
    )

    assert path == tmp_path / "index.html"
    assert "Example Co" in path.read_text(encoding="utf-8")
