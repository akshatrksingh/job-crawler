from datetime import UTC, date, datetime, timedelta

from job_crawler.crawlers.base import JobPosting
from job_crawler.dashboard import render_dashboard, write_dashboard
from job_crawler.dashboard.html import select_dashboard_jobs


def make_job(
    title: str,
    company: str,
    location: str,
    posted_at: datetime,
    source: str = "fixture",
    first_seen_at: datetime | None = None,
) -> JobPosting:
    return JobPosting(
        source=source,
        source_id=f"{company}-{title}",
        company=company,
        title=title,
        location=location,
        url=f"https://example.com/{company}/{title}".replace(" ", "-"),
        description="Entry level AI engineering role.",
        posted_at=posted_at,
        first_seen_at=first_seen_at,
    )


def test_select_dashboard_jobs_uses_first_seen_for_rolling_window() -> None:
    today = date(2026, 4, 29)
    fresh = make_job(
        "AI Engineer",
        "Fresh Co",
        "New York, NY",
        datetime(2026, 1, 20, tzinfo=UTC),
        first_seen_at=datetime(2026, 4, 20, tzinfo=UTC),
    )
    old = make_job(
        "AI Engineer",
        "Old Co",
        "New York, NY",
        datetime(2026, 4, 28, tzinfo=UTC),
        first_seen_at=datetime(2026, 4, 1, tzinfo=UTC),
    )

    selected = select_dashboard_jobs([fresh, old], today=today, days=14)

    assert [job.company for job in selected] == ["Fresh Co"]


def test_select_dashboard_jobs_uses_first_seen_window_when_posted_date_is_missing() -> None:
    today = date(2026, 4, 29)
    fresh = JobPosting(
        source="ashby",
        source_id="fresh",
        company="Fresh Seen Co",
        title="AI Engineer",
        location="Boston, US",
        url="https://example.com/fresh",
        description="Entry level AI role.",
        posted_at=None,
        first_seen_at=datetime(2026, 4, 28, tzinfo=UTC),
    )
    old = JobPosting(
        source="ashby",
        source_id="old",
        company="Old Seen Co",
        title="AI Engineer",
        location="Boston, US",
        url="https://example.com/old",
        description="Entry level AI role.",
        posted_at=None,
        first_seen_at=datetime(2026, 4, 1, tzinfo=UTC),
    )

    html = render_dashboard([fresh, old], today=today, days=14)

    assert "Fresh Seen Co" in html
    assert "Old Seen Co" not in html
    assert "<th>Posted</th>" not in html


def test_render_dashboard_has_pagination_and_no_filters_or_hard_limit() -> None:
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

    assert html.count("<tr>") == 33
    assert 'id="prev"' in html
    assert 'id="next"' in html
    assert 'id="search"' not in html
    assert 'id="location"' not in html
    assert 'id="role"' not in html
    assert 'id="source"' not in html
    assert "Seattle, WA" in html
    assert "Refresh Status" in html


def test_render_dashboard_shows_refresh_errors() -> None:
    html = render_dashboard(
        [],
        refresh_runs=[
            {
                "source_type": "greenhouse",
                "source_slug": "example",
                "status": "failed",
                "jobs_seen": 0,
                "jobs_inserted": 0,
                "finished_at": "2026-04-29 12:00:00",
                "error": "network issue",
            }
        ],
    )

    assert "greenhouse:example" in html
    assert "failed" in html
    assert "network issue" in html


def test_render_dashboard_warns_when_web_discovery_fails() -> None:
    html = render_dashboard(
        [],
        refresh_runs=[
            {
                "source_type": "web_search_discovery",
                "source_slug": None,
                "status": "failed",
                "jobs_seen": 0,
                "jobs_inserted": 0,
                "finished_at": "2026-04-29 12:00:00",
                "error": "429 too many requests",
            },
            {
                "source_type": "github_jobs",
                "source_slug": None,
                "status": "succeeded",
                "jobs_seen": 250,
                "jobs_inserted": 10,
                "finished_at": "2026-04-29 12:01:00",
                "error": None,
            },
        ],
    )

    assert "Tavily/web discovery failed" in html
    assert "Other sources still refreshed" in html
    assert "Next refresh will try discovery again" in html
    assert "429 too many requests" in html


def test_render_dashboard_does_not_warn_when_web_discovery_succeeds() -> None:
    html = render_dashboard(
        [],
        refresh_runs=[
            {
                "source_type": "web_search_discovery",
                "source_slug": None,
                "status": "succeeded",
                "jobs_seen": 10,
                "jobs_inserted": 5,
                "finished_at": "2026-04-29 12:00:00",
                "error": None,
            }
        ],
    )

    assert "Tavily/web discovery failed" not in html


def test_render_dashboard_has_no_manual_discovery_controls() -> None:
    html = render_dashboard(
        [
            make_job(
                "AI Engineer",
                "Example Co",
                "New York, NY",
                datetime(2026, 4, 28, tzinfo=UTC),
            )
        ],
        today=date(2026, 4, 29),
    )

    assert 'id="discovery-urls"' not in html
    assert 'id="discover-ats"' not in html
    assert 'id="discover-pages"' not in html
    assert "/api/discover-urls" not in html
    assert "/api/discover-pages" not in html


def test_select_dashboard_jobs_interleaves_location_buckets() -> None:
    today = date(2026, 4, 29)
    jobs = [
        make_job(
            f"Software Engineer SF {index}",
            f"SF Co {index}",
            "San Francisco",
            datetime(2026, 4, 28, tzinfo=UTC),
        )
        for index in range(8)
    ] + [
        make_job(
            "Software Engineer Seattle",
            "Seattle Co",
            "Seattle, WA",
            datetime(2026, 4, 28, tzinfo=UTC),
        ),
        make_job(
            "Software Engineer Boston",
            "Boston Co",
            "Boston, US",
            datetime(2026, 4, 28, tzinfo=UTC),
        ),
    ]

    selected = select_dashboard_jobs(jobs, today=today)

    assert [job.company for job in selected[:3]] == ["SF Co 0", "Boston Co", "Seattle Co"]
    assert [job.company for job in selected[:4]].count("SF Co 0") == 1


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


def test_render_dashboard_excludes_non_us_only_locations() -> None:
    today = date(2026, 4, 29)
    html = render_dashboard(
        [
            make_job(
                "AI Engineer",
                "US Co",
                "Seattle, WA",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
            make_job(
                "AI Engineer",
                "Remote Co",
                "Remote",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
            make_job(
                "AI Engineer",
                "UK Co",
                "Remote - United Kingdom",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
            make_job(
                "AI Engineer",
                "China Co",
                "Shanghai, Remote",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
        ],
        today=today,
    )

    assert "US Co" in html
    assert "Remote Co" in html
    assert "UK Co" not in html
    assert "China Co" not in html


def test_render_dashboard_excludes_non_target_roles() -> None:
    today = date(2026, 4, 29)
    html = render_dashboard(
        [
            make_job(
                "Machine Learning Engineer",
                "ML Co",
                "Boston, US",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
            make_job(
                "Recruiter",
                "Recruiting Co",
                "Seattle, WA",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
            make_job(
                "Growth Operations Associate",
                "Growth Co",
                "San Francisco, CA",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
            make_job(
                "Cloud Security Engineer",
                "Security Co",
                "Seattle, WA",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
            make_job(
                "Support Engineer",
                "Support Co",
                "Remote",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
            make_job(
                "Social Media Manager",
                "Social Co",
                "New York, NY",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
        ],
        today=today,
    )

    assert "ML Co" in html
    assert "Recruiting Co" not in html
    assert "Growth Co" not in html
    assert "Security Co" not in html
    assert "Support Co" not in html
    assert "Social Co" not in html


def test_render_dashboard_includes_hn_jobs() -> None:
    today = date(2026, 4, 29)
    html = render_dashboard(
        [
            make_job(
                "AI Engineer",
                "HN Co",
                "New York, NY",
                datetime(2026, 4, 28, tzinfo=UTC),
                source="hn",
            ),
            make_job(
                "AI Engineer",
                "YC Co",
                "New York, NY",
                datetime(2026, 4, 28, tzinfo=UTC),
                source="yc",
            ),
        ],
        today=today,
    )

    assert "HN Co" in html
    assert "YC Co" in html


def test_render_dashboard_excludes_yc_role_category_links() -> None:
    today = date(2026, 4, 29)
    html = render_dashboard(
        [
            JobPosting(
                source="yc",
                source_id="designer",
                company="YC Company",
                title="Design & UI/UX",
                location="Unknown",
                url="https://www.ycombinator.com/jobs/role/designer",
                description=None,
                posted_at=datetime(2026, 4, 28, tzinfo=UTC),
            ),
            make_job(
                "AI Engineer",
                "Example Co",
                "New York, NY",
                datetime(2026, 4, 28, tzinfo=UTC),
            ),
        ],
        today=today,
    )

    assert "Design &amp; UI/UX" not in html
    assert "Example Co" in html


def test_render_dashboard_shows_last_refresh_without_disabling_refresh() -> None:
    html = render_dashboard(
        [],
        last_refresh_at=datetime.now(UTC).isoformat(),
    )

    assert "Last refresh" in html
    assert "next after" not in html
    assert 'id="refresh" type="button" disabled' not in html


def test_render_dashboard_polls_refresh_progress() -> None:
    html = render_dashboard([])

    assert "/api/refresh-progress" in html
    assert "ETA ~" in html
    assert "pollRefresh" in html


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
