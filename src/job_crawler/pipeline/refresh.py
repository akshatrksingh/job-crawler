"""Small safe refresh pipeline slices."""

from __future__ import annotations

import time
from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from job_crawler.crawlers.ashby import fetch_ashby_jobs
from job_crawler.crawlers.base import JobPosting
from job_crawler.crawlers.github_boards import fetch_default_github_board_jobs
from job_crawler.crawlers.greenhouse import fetch_greenhouse_jobs
from job_crawler.crawlers.hn import fetch_hn_who_is_hiring_jobs
from job_crawler.crawlers.lever import fetch_lever_jobs
from job_crawler.crawlers.yc import fetch_yc_jobs
from job_crawler.dashboard import write_dashboard
from job_crawler.discovery import discover_sources_from_web_search, extract_sources_from_urls
from job_crawler.storage import JobRepository, open_database

JobFetcher = Callable[..., list[JobPosting]]
SourceFetcher = Callable[..., list[JobPosting]]
GitHubBoardsFetcher = Callable[..., list[JobPosting]]
HnFetcher = Callable[..., list[JobPosting]]
WebDiscoveryFetcher = Callable[..., list]
ProgressCallback = Callable[[dict[str, object]], None]


@dataclass(frozen=True)
class SourceRefreshResult:
    """Refresh stats for one source."""

    source: str
    seen: int
    inserted: int
    error: str | None = None
    skipped: bool = False


@dataclass(frozen=True)
class RefreshResult:
    """Aggregate refresh stats."""

    sources: tuple[SourceRefreshResult, ...]
    candidates: int
    refreshed: bool = True
    last_refresh_at: str | None = None

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
WEB_DISCOVERY_QUERY_BUDGET_KEY = "web_discovery_query_budget"
WEB_DISCOVERY_MIN_QUERY_BUDGET = 10
WEB_DISCOVERY_BACKOFF_STEP = 10
DEFAULT_ATS_WORKERS = 8
DEFAULT_SOURCE_TIMEOUT_SECONDS = 35.0
STALE_RUN_MINUTES = 90


@dataclass(frozen=True)
class StoredSourcePlan:
    """One stored ATS source selected for this refresh."""

    source_type: str
    source_id: int
    slug: str
    crawl_run_id: int


@dataclass(frozen=True)
class StoredSourceFetchResult:
    """Network result for one stored source."""

    plan: StoredSourcePlan
    jobs: list[JobPosting]
    error: str | None = None


def refresh_yc(
    *,
    db_path: Path,
    output_path: Path,
    days: int = 14,
    candidate_limit: int = 10_000,
    yc_limit: int = 80,
    yc_fetcher: JobFetcher = fetch_yc_jobs,
) -> RefreshResult:
    """Fetch YC, store/dedupe jobs, and regenerate the dashboard."""
    source_results = []
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        source_results.append(
            _refresh_source(repo, source="yc", fetcher=yc_fetcher, limit=yc_limit)
        )
        refreshed_at = datetime.now(UTC)
        repo.set_app_state(REFRESH_STATE_KEY, refreshed_at.isoformat())
        jobs = repo.list_recent_jobs(limit=candidate_limit)
        refresh_runs = repo.list_recent_crawl_runs()

    write_dashboard(jobs, output_path=output_path, days=days, refresh_runs=refresh_runs)
    return RefreshResult(
        sources=tuple(source_results),
        candidates=len(jobs),
        last_refresh_at=refreshed_at.isoformat(),
    )


def refresh_jobs(
    *,
    db_path: Path,
    output_path: Path,
    days: int = 14,
    candidate_limit: int = 10_000,
    ashby_limit: int = 10,
    github_jobs_limit: int = 250,
    hn_limit: int = 80,
    yc_limit: int = 80,
    web_discovery_queries: int = 100,
    web_discovery_results_per_query: int = 8,
    max_sources: int = 500,
    ashby_fetcher: SourceFetcher = fetch_ashby_jobs,
    greenhouse_fetcher: SourceFetcher = fetch_greenhouse_jobs,
    lever_fetcher: SourceFetcher = fetch_lever_jobs,
    github_boards_fetcher: GitHubBoardsFetcher = fetch_default_github_board_jobs,
    hn_fetcher: HnFetcher = fetch_hn_who_is_hiring_jobs,
    yc_fetcher: JobFetcher = fetch_yc_jobs,
    web_discovery_fetcher: WebDiscoveryFetcher = discover_sources_from_web_search,
    ats_workers: int = DEFAULT_ATS_WORKERS,
    source_timeout_seconds: float = DEFAULT_SOURCE_TIMEOUT_SECONDS,
    progress_callback: ProgressCallback | None = None,
) -> RefreshResult:
    """Fetch stored job sources, store/dedupe jobs, and regenerate the dashboard."""
    source_results = []
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        stale_runs = repo.cleanup_stale_crawl_runs(stale_after_minutes=STALE_RUN_MINUTES)
        if stale_runs:
            _emit_progress(
                progress_callback,
                phase="cleanup",
                message=f"Cleaned up {stale_runs} stale crawl run(s).",
            )
        web_discovery_query_budget = _web_discovery_query_budget(
            repo,
            ceiling=web_discovery_queries,
        )
        web_discovery_result = _refresh_web_discovery(
            repo,
            max_queries=web_discovery_query_budget,
            results_per_query=web_discovery_results_per_query,
            fetcher=web_discovery_fetcher,
        )
        source_results.append(web_discovery_result)
        _update_web_discovery_query_budget(
            repo,
            current=web_discovery_query_budget,
            ceiling=web_discovery_queries,
            result=web_discovery_result,
        )
        source_results.append(
            _refresh_github_boards(
                repo,
                limit=github_jobs_limit,
                fetcher=github_boards_fetcher,
            )
        )
        source_results.append(
            _refresh_source(
                repo,
                source="hn",
                fetcher=hn_fetcher,
                limit=hn_limit,
            )
        )
        source_results.append(
            _refresh_source(
                repo,
                source="yc",
                fetcher=yc_fetcher,
                limit=yc_limit,
            )
        )
        fetchers = {
            "ashby": ashby_fetcher,
            "greenhouse": greenhouse_fetcher,
            "lever": lever_fetcher,
        }
        source_results.extend(
            _refresh_stored_sources_parallel(
                repo,
                fetchers=fetchers,
                limit=ashby_limit,
                max_sources=max_sources,
                workers=ats_workers,
                source_timeout_seconds=source_timeout_seconds,
                progress_callback=progress_callback,
            )
        )
        refreshed_at = datetime.now(UTC)
        repo.set_app_state(REFRESH_STATE_KEY, refreshed_at.isoformat())
        jobs = repo.list_recent_jobs(limit=candidate_limit)
        refresh_runs = repo.list_recent_crawl_runs()

    write_dashboard(jobs, output_path=output_path, days=days, refresh_runs=refresh_runs)
    return RefreshResult(
        sources=tuple(source_results),
        candidates=len(jobs),
        last_refresh_at=refreshed_at.isoformat(),
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
        _upsert_sources_from_jobs(repo, jobs, discovered_from=f"{source} job links")
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


def _refresh_stored_source(
    repo: JobRepository,
    *,
    source_type: str,
    source_id: int,
    slug: str,
    limit: int,
    fetcher: SourceFetcher,
) -> SourceRefreshResult:
    crawl_run_id = repo.start_crawl_run(source_type=source_type, source_id=source_id)
    jobs_seen = 0
    jobs_inserted = 0
    try:
        jobs = _fetch_source_jobs(source_type, fetcher=fetcher, slug=slug, limit=limit)
        jobs_seen = len(jobs)
        for job in jobs:
            jobs_inserted += int(repo.insert_job(job).inserted)
        repo.finish_crawl_run(
            crawl_run_id=crawl_run_id,
            status="succeeded",
            jobs_seen=jobs_seen,
            jobs_inserted=jobs_inserted,
        )
        repo.mark_source_crawled(source_id=source_id)
        return SourceRefreshResult(
            source=f"{source_type}:{slug}",
            seen=jobs_seen,
            inserted=jobs_inserted,
        )
    except Exception as exc:
        repo.finish_crawl_run(
            crawl_run_id=crawl_run_id,
            status="failed",
            jobs_seen=jobs_seen,
            jobs_inserted=jobs_inserted,
            error=str(exc),
        )
        repo.mark_source_crawled(source_id=source_id)
        return SourceRefreshResult(
            source=f"{source_type}:{slug}",
            seen=jobs_seen,
            inserted=jobs_inserted,
            error=str(exc),
        )


def _refresh_stored_sources_parallel(
    repo: JobRepository,
    *,
    fetchers: dict[str, SourceFetcher],
    limit: int,
    max_sources: int,
    workers: int,
    source_timeout_seconds: float,
    progress_callback: ProgressCallback | None,
) -> list[SourceRefreshResult]:
    plans: list[StoredSourcePlan] = []
    per_type_limit = max(1, max_sources)
    for source_type in fetchers:
        for source in repo.list_due_sources(source_type=source_type, limit=per_type_limit):
            if len(plans) >= max_sources:
                break
            plans.append(
                StoredSourcePlan(
                    source_type=source_type,
                    source_id=int(source["id"]),
                    slug=str(source["slug"]),
                    crawl_run_id=repo.start_crawl_run(
                        source_type=source_type,
                        source_id=int(source["id"]),
                    ),
                )
            )
        if len(plans) >= max_sources:
            break

    if not plans:
        _emit_progress(
            progress_callback,
            phase="ats",
            message="No stored ATS sources due for this refresh.",
            total=0,
            completed=0,
            eta_seconds=0,
        )
        return [
            SourceRefreshResult(
                source="ats:scheduled_sources",
                seen=0,
                inserted=0,
                skipped=True,
            )
        ]

    total = len(plans)
    completed = 0
    started_at = time.monotonic()
    _emit_progress(
        progress_callback,
        phase="ats",
        message=f"Fetching {total} due ATS company boards...",
        total=total,
        completed=completed,
        eta_seconds=None,
    )

    executor = ThreadPoolExecutor(max_workers=max(1, workers))
    futures: dict[Future[StoredSourceFetchResult], tuple[StoredSourcePlan, float]] = {
        executor.submit(
            _fetch_stored_source_jobs,
            plan,
            fetcher=fetchers[plan.source_type],
            limit=limit,
        ): (plan, time.monotonic())
        for plan in plans
    }
    results: list[SourceRefreshResult] = []
    try:
        while futures:
            done, _ = wait(futures, timeout=0.5, return_when=FIRST_COMPLETED)
            now = time.monotonic()
            timed_out = [
                future
                for future, (_, start) in futures.items()
                if now - start > source_timeout_seconds
            ]
            for future in timed_out:
                plan, _ = futures.pop(future)
                future.cancel()
                result = StoredSourceFetchResult(
                    plan=plan,
                    jobs=[],
                    error=f"timed out after {source_timeout_seconds:.0f}s",
                )
                results.append(_store_stored_source_result(repo, result))
                completed += 1
                _emit_ats_progress(
                    progress_callback,
                    started_at=started_at,
                    completed=completed,
                    total=total,
                    source=f"{plan.source_type}:{plan.slug}",
                )
            for future in done:
                if future not in futures:
                    continue
                plan, _ = futures.pop(future)
                try:
                    result = future.result()
                except Exception as exc:
                    result = StoredSourceFetchResult(plan=plan, jobs=[], error=str(exc))
                results.append(_store_stored_source_result(repo, result))
                completed += 1
                _emit_ats_progress(
                    progress_callback,
                    started_at=started_at,
                    completed=completed,
                    total=total,
                    source=f"{plan.source_type}:{plan.slug}",
                )
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return results


def _fetch_stored_source_jobs(
    plan: StoredSourcePlan,
    *,
    fetcher: SourceFetcher,
    limit: int,
) -> StoredSourceFetchResult:
    try:
        jobs = _fetch_source_jobs(plan.source_type, fetcher=fetcher, slug=plan.slug, limit=limit)
        return StoredSourceFetchResult(plan=plan, jobs=jobs)
    except Exception as exc:
        return StoredSourceFetchResult(plan=plan, jobs=[], error=str(exc))


def _store_stored_source_result(
    repo: JobRepository,
    result: StoredSourceFetchResult,
) -> SourceRefreshResult:
    jobs_seen = len(result.jobs)
    jobs_inserted = 0
    if result.error is None:
        for job in result.jobs:
            jobs_inserted += int(repo.insert_job(job).inserted)
        repo.finish_crawl_run(
            crawl_run_id=result.plan.crawl_run_id,
            status="succeeded",
            jobs_seen=jobs_seen,
            jobs_inserted=jobs_inserted,
        )
    else:
        repo.finish_crawl_run(
            crawl_run_id=result.plan.crawl_run_id,
            status="failed",
            jobs_seen=jobs_seen,
            jobs_inserted=jobs_inserted,
            error=result.error,
        )
    repo.record_source_crawl_outcome(
        source_id=result.plan.source_id,
        jobs_seen=jobs_seen,
        jobs_inserted=jobs_inserted,
        error=result.error,
    )
    return SourceRefreshResult(
        source=f"{result.plan.source_type}:{result.plan.slug}",
        seen=jobs_seen,
        inserted=jobs_inserted,
        error=result.error,
    )


def _refresh_web_discovery(
    repo: JobRepository,
    *,
    max_queries: int,
    results_per_query: int,
    fetcher: WebDiscoveryFetcher,
) -> SourceRefreshResult:
    crawl_run_id = repo.start_crawl_run(source_type="web_search_discovery")
    sources_seen = 0
    sources_inserted = 0
    try:
        sources = fetcher(max_queries=max_queries, results_per_query=results_per_query)
        sources_seen = len(sources)
        before = _source_keys(repo)
        for source in sources:
            repo.upsert_discovered_source(source)
        after = _source_keys(repo)
        sources_inserted = len(after - before)
        repo.finish_crawl_run(
            crawl_run_id=crawl_run_id,
            status="succeeded",
            jobs_seen=sources_seen,
            jobs_inserted=sources_inserted,
        )
        return SourceRefreshResult(
            source="web_search_discovery",
            seen=sources_seen,
            inserted=sources_inserted,
        )
    except Exception as exc:
        repo.finish_crawl_run(
            crawl_run_id=crawl_run_id,
            status="failed",
            jobs_seen=sources_seen,
            jobs_inserted=sources_inserted,
            error=str(exc),
        )
        return SourceRefreshResult(
            source="web_search_discovery",
            seen=sources_seen,
            inserted=sources_inserted,
            error=str(exc),
        )


def _source_keys(repo: JobRepository) -> set[tuple[str, str]]:
    return {(str(row["source_type"]), str(row["slug"])) for row in repo.list_sources()}


def _web_discovery_query_budget(repo: JobRepository, *, ceiling: int) -> int:
    if ceiling <= 0:
        return 0
    floor = min(WEB_DISCOVERY_MIN_QUERY_BUDGET, ceiling)
    raw_value = repo.get_app_state(WEB_DISCOVERY_QUERY_BUDGET_KEY)
    if raw_value is None:
        return ceiling
    try:
        parsed = int(raw_value)
    except ValueError:
        return ceiling
    return min(max(parsed, floor), ceiling)


def _update_web_discovery_query_budget(
    repo: JobRepository,
    *,
    current: int,
    ceiling: int,
    result: SourceRefreshResult,
) -> None:
    if ceiling <= 0:
        repo.set_app_state(WEB_DISCOVERY_QUERY_BUDGET_KEY, "0")
        return
    floor = min(WEB_DISCOVERY_MIN_QUERY_BUDGET, ceiling)
    if result.error or result.seen == 0:
        next_budget = max(floor, current - WEB_DISCOVERY_BACKOFF_STEP)
    else:
        next_budget = min(ceiling, current + WEB_DISCOVERY_BACKOFF_STEP)
    repo.set_app_state(WEB_DISCOVERY_QUERY_BUDGET_KEY, str(next_budget))


def _upsert_sources_from_jobs(
    repo: JobRepository,
    jobs: list[JobPosting],
    *,
    discovered_from: str,
) -> None:
    sources = extract_sources_from_urls(
        [job.url for job in jobs],
        discovered_from=discovered_from,
    )
    for source in sources:
        repo.upsert_discovered_source(source)


def _fetch_source_jobs(
    source_type: str,
    *,
    fetcher: SourceFetcher,
    slug: str,
    limit: int,
) -> list[JobPosting]:
    if source_type == "greenhouse":
        return fetcher(board_token=slug, company=slug, limit=limit)
    if source_type == "lever":
        return fetcher(site=slug, company=slug, limit=limit)
    return fetcher(slug=slug, company=slug, limit=limit)


def _refresh_github_boards(
    repo: JobRepository,
    *,
    limit: int,
    fetcher: GitHubBoardsFetcher,
) -> SourceRefreshResult:
    crawl_run_id = repo.start_crawl_run(source_type="github_jobs")
    jobs_seen = 0
    jobs_inserted = 0
    try:
        jobs = fetcher(limit=limit)
        jobs_seen = len(jobs)
        for job in jobs:
            jobs_inserted += int(repo.insert_job(job).inserted)
        for source in extract_sources_from_urls(
            [job.url for job in jobs],
            discovered_from="github job board apply links",
        ):
            repo.upsert_discovered_source(source)
        repo.finish_crawl_run(
            crawl_run_id=crawl_run_id,
            status="succeeded",
            jobs_seen=jobs_seen,
            jobs_inserted=jobs_inserted,
        )
        return SourceRefreshResult(
            source="github_jobs:default_boards",
            seen=jobs_seen,
            inserted=jobs_inserted,
        )
    except Exception as exc:
        repo.finish_crawl_run(
            crawl_run_id=crawl_run_id,
            status="failed",
            jobs_seen=jobs_seen,
            jobs_inserted=jobs_inserted,
            error=str(exc),
        )
        return SourceRefreshResult(
            source="github_jobs:default_boards",
            seen=jobs_seen,
            inserted=jobs_inserted,
            error=str(exc),
        )


def _emit_ats_progress(
    callback: ProgressCallback | None,
    *,
    started_at: float,
    completed: int,
    total: int,
    source: str,
) -> None:
    elapsed = max(0.0, time.monotonic() - started_at)
    average = elapsed / completed if completed else 0.0
    remaining = max(0, total - completed)
    _emit_progress(
        callback,
        phase="ats",
        message=f"Fetched {completed}/{total} ATS boards. Latest: {source}.",
        total=total,
        completed=completed,
        eta_seconds=round(average * remaining),
    )


def _emit_progress(callback: ProgressCallback | None, **payload: object) -> None:
    if callback is not None:
        callback(payload)
