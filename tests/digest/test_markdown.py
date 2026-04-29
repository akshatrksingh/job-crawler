from datetime import date

from job_crawler.crawlers.base import JobPosting
from job_crawler.digest import render_digest, select_digest_jobs, write_digest


def make_job(title: str, location: str, company: str = "Example Co") -> JobPosting:
    return JobPosting(
        source="fixture",
        source_id=f"{company}-{title}",
        company=company,
        title=title,
        location=location,
        url=f"https://example.com/{company}/{title}".replace(" ", "-"),
        description="Entry level AI engineering role.",
    )


def test_select_digest_jobs_orders_primary_locations_then_major_cities() -> None:
    jobs = [
        make_job("AI Engineer", "London", "Other Co"),
        make_job("AI Engineer", "Seattle, WA", "Seattle Co"),
        make_job("AI Engineer", "New York, NY", "NYC Co"),
    ]

    selected = select_digest_jobs(jobs, limit=3)

    assert [item.job.company for item in selected] == ["NYC Co", "Seattle Co", "Other Co"]


def test_select_digest_jobs_excludes_senior_roles() -> None:
    jobs = [
        make_job("Senior AI Engineer", "New York, NY", "Senior Co"),
        make_job("Software Engineer I", "Boston, MA", "Junior Co"),
    ]

    selected = select_digest_jobs(jobs)

    assert [item.job.company for item in selected] == ["Junior Co"]


def test_render_digest_outputs_simple_table_only() -> None:
    markdown = render_digest(
        [make_job("Software Engineer I", "Austin, TX", "Austin AI")],
        digest_date=date(2026, 4, 29),
    )

    assert "# Job Digest - 2026-04-29" in markdown
    assert "| Company | Job | Location | Link |" in markdown
    assert "| Austin AI | Software Engineer I | Austin, TX | [Open](" in markdown
    assert "score" not in markdown.lower()
    assert "why it matches" not in markdown.lower()


def test_write_digest_creates_dated_markdown_file(tmp_path) -> None:
    path = write_digest(
        [make_job("AI Engineer", "San Francisco, CA", "SF AI")],
        output_dir=tmp_path,
        digest_date=date(2026, 4, 29),
    )

    assert path == tmp_path / "2026-04-29.md"
    assert "SF AI" in path.read_text(encoding="utf-8")
