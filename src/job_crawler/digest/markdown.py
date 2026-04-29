"""Markdown digest generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from job_crawler.crawlers.base import JobPosting
from job_crawler.ranking import RankedJob, rank_job


@dataclass(frozen=True)
class DigestItem:
    """A job selected for the daily digest."""

    company: str
    title: str
    url: str
    location: str


def select_digest_jobs(jobs: list[JobPosting], *, limit: int = 25) -> list[RankedJob]:
    """Rank, filter, and choose jobs for the digest."""
    ranked = [rank_job(job) for job in jobs]
    visible = [item for item in ranked if not item.excluded]
    return sorted(
        visible,
        key=lambda item: (
            -item.score,
            item.location_tier,
            item.job.company.lower(),
            item.job.title.lower(),
        ),
    )[:limit]


def render_digest(
    jobs: list[JobPosting],
    *,
    digest_date: date,
    limit: int = 25,
) -> str:
    """Render a simple Markdown digest."""
    selected = select_digest_jobs(jobs, limit=limit)
    lines = [f"# Job Digest - {digest_date.isoformat()}", ""]
    if not selected:
        lines.append("No matching jobs found.")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Company | Job | Location | Link |")
    lines.append("|---|---|---|---|")
    for ranked in selected:
        item = _to_digest_item(ranked.job)
        lines.append(
            f"| {_escape_table(item.company)} "
            f"| {_escape_table(item.title)} "
            f"| {_escape_table(item.location)} "
            f"| [Open]({item.url}) |"
        )
    lines.append("")
    return "\n".join(lines)


def write_digest(
    jobs: list[JobPosting],
    *,
    output_dir: Path,
    digest_date: date,
    limit: int = 25,
) -> Path:
    """Write a daily Markdown digest and return its path."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{digest_date.isoformat()}.md"
    path.write_text(render_digest(jobs, digest_date=digest_date, limit=limit), encoding="utf-8")
    return path


def _to_digest_item(job: JobPosting) -> DigestItem:
    return DigestItem(
        company=job.company,
        title=job.title,
        url=job.url,
        location=job.location or "Unknown",
    )


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()
