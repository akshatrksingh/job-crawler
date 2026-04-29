"""Small safe refresh pipeline slices."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from job_crawler.crawlers.base import JobPosting
from job_crawler.crawlers.yc import fetch_yc_jobs
from job_crawler.dashboard import write_dashboard
from job_crawler.storage import JobRepository, open_database

JobFetcher = Callable[..., list[JobPosting]]


@dataclass(frozen=True)
class SourceRefreshResult:
    """Refresh stats for one source."""

    source: str
    seen: int
    inserted: int
    error: str | None = None


@dataclass(frozen=True)
class RefreshResult:
    """Aggregate refresh stats."""

    sources: tuple[SourceRefreshResult, ...]
    candidates: int
    refreshed: bool = True
    last_refresh_at: str | None = None
    next_refresh_at: str | None = None
    cooldown_seconds_remaining: int = 0

    @property
    def seen(self) -> int:
        return sum(source.seen for source in self.sources)

    @property
    def inserted(self) -> int:
        return sum(source.inserted for source in self.sources)

    @property
    def errors(self) -> list[str]:
        return [source.error for source in self.sources if source.error]


REFRESH_STATE_KEY = "last_refresh_at"


def refresh_yc(
    *,
    db_path: Path,
    output_path: Path,
    days: int = 14,
    candidate_limit: int = 10_000,
    yc_limit: int = 80,
    yc_fetcher: JobFetcher = fetch_yc_jobs,
    cooldown_hours: int = 6,
    force: bool = False,
) -> RefreshResult:
    """Fetch YC, store/dedupe jobs, and regenerate the dashboard."""
    source_results = []
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        now = datetime.now(UTC)
        last_refresh_at = _parse_datetime(repo.get_app_state(REFRESH_STATE_KEY))
        if last_refresh_at is not None:
            next_refresh_at = last_refresh_at + timedelta(hours=cooldown_hours)
            if not force and now < next_refresh_at:
                jobs = repo.list_jobs_for_digest(limit=candidate_limit)
                write_dashboard(jobs, output_path=output_path, days=days)
                return RefreshResult(
                    sources=(),
                    candidates=len(jobs),
                    refreshed=False,
                    last_refresh_at=last_refresh_at.isoformat(),
                    next_refresh_at=next_refresh_at.isoformat(),
                    cooldown_seconds_remaining=int((next_refresh_at - now).total_seconds()),
                )

        source_results.append(
            _refresh_source(repo, source="yc", fetcher=yc_fetcher, limit=yc_limit)
        )
        refreshed_at = datetime.now(UTC)
        next_refresh_at = refreshed_at + timedelta(hours=cooldown_hours)
        repo.set_app_state(REFRESH_STATE_KEY, refreshed_at.isoformat())
        jobs = repo.list_jobs_for_digest(limit=candidate_limit)

    write_dashboard(jobs, output_path=output_path, days=days)
    return RefreshResult(
        sources=tuple(source_results),
        candidates=len(jobs),
        last_refresh_at=refreshed_at.isoformat(),
        next_refresh_at=next_refresh_at.isoformat(),
    )


def _refresh_source(
    repo: JobRepository,
    *,
    source: str,
    fetcher: JobFetcher,
    limit: int,
) -> SourceRefreshResult:
    crawl_run_id = repo.start_crawl_run(source_type=source)
    jobs_seen = 0
    jobs_inserted = 0
    try:
        jobs = fetcher(limit=limit)
        jobs_seen = len(jobs)
        for job in jobs:
            jobs_inserted += int(repo.insert_job(job).inserted)
        repo.finish_crawl_run(
            crawl_run_id=crawl_run_id,
            status="succeeded",
            jobs_seen=jobs_seen,
            jobs_inserted=jobs_inserted,
        )
        return SourceRefreshResult(source=source, seen=jobs_seen, inserted=jobs_inserted)
    except Exception as exc:
        repo.finish_crawl_run(
            crawl_run_id=crawl_run_id,
            status="failed",
            jobs_seen=jobs_seen,
            jobs_inserted=jobs_inserted,
            error=str(exc),
        )
        return SourceRefreshResult(
            source=source,
            seen=jobs_seen,
            inserted=jobs_inserted,
            error=str(exc),
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
