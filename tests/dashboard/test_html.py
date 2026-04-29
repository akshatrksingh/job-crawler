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


def test_select_dashboard_jobs_uses_first_seen_when_posted_date_is_missing() -> None:
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
    assert "<td>N/A</td>" in html
    assert "<td>2026-04-28</td>" in html


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

    assert html.count("<tr>") == 31
    assert "<th>Posted</th>" in html
    assert "<th>Seen</th>" in html
    assert 'id="prev"' in html
    assert 'id="next"' in html
    assert 'id="search"' not in html
    assert 'id="location"' not in html
    assert 'id="role"' not in html
    assert 'id="source"' not in html
    assert "Seattle, WA" in html


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


def test_render_dashboard_excludes_hn_jobs() -> None:
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

    assert "HN Co" not in html
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


def test_render_dashboard_shows_refresh_cooldown_state() -> None:
    html = render_dashboard(
        [],
        last_refresh_at=datetime.now(UTC).isoformat(),
        cooldown_hours=6,
    )

    assert "Last refresh" in html
    assert "next after" in html
    assert 'id="refresh" type="button" disabled' in html


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
