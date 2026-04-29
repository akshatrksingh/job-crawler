"""Run one bounded ATS crawl and store results in SQLite."""

from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path

from job_crawler.crawlers.ashby import fetch_ashby_jobs
from job_crawler.crawlers.base import JobPosting
from job_crawler.crawlers.greenhouse import fetch_greenhouse_jobs
from job_crawler.crawlers.lever import fetch_lever_jobs
from job_crawler.storage import JobRepository, open_database

Fetcher = Callable[..., list[JobPosting]]

FETCHERS: dict[str, Fetcher] = {
    "ashby": fetch_ashby_jobs,
    "greenhouse": fetch_greenhouse_jobs,
    "lever": fetch_lever_jobs,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=sorted(FETCHERS), required=True)
    parser.add_argument("--slug", required=True, help="ATS company slug or board token")
    parser.add_argument("--company", help="Display company name")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--db", default="data/job_crawler.sqlite")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    fetcher = FETCHERS[args.source]

    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        source_id = repo.upsert_source(
            source_type=args.source,
            slug=args.slug,
            discovered_from="smoke_ats",
        )
        crawl_run_id = repo.start_crawl_run(source_type=args.source, source_id=source_id)
        jobs_seen = 0
        jobs_inserted = 0
        try:
            jobs = fetcher(args.slug, company=args.company, limit=args.limit)
            jobs_seen = len(jobs)
            for job in jobs:
                result = repo.insert_job(job)
                jobs_inserted += int(result.inserted)
            repo.finish_crawl_run(
                crawl_run_id=crawl_run_id,
                status="succeeded",
                jobs_seen=jobs_seen,
                jobs_inserted=jobs_inserted,
            )
            repo.mark_source_crawled(source_id=source_id)
        except Exception as exc:
            repo.finish_crawl_run(
                crawl_run_id=crawl_run_id,
                status="failed",
                jobs_seen=jobs_seen,
                jobs_inserted=jobs_inserted,
                error=str(exc),
            )
            raise

    print(f"database={db_path}")
    print(f"source={args.source}")
    print(f"slug={args.slug}")
    print(f"jobs_seen={jobs_seen}")
    print(f"jobs_inserted={jobs_inserted}")


if __name__ == "__main__":
    main()
