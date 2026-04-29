"""Run a bounded Hacker News Who is Hiring smoke crawl."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from job_crawler.crawlers.hn import fetch_latest_who_is_hiring_jobs
from job_crawler.storage import JobRepository, open_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--db", default="data/job_crawler.sqlite")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    jobs = fetch_latest_who_is_hiring_jobs(limit=args.limit)
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        inserted = sum(int(repo.insert_job(job).inserted) for job in jobs)

    print(f"database={db_path}")
    print(f"jobs_seen={len(jobs)}")
    print(f"jobs_inserted={inserted}")


if __name__ == "__main__":
    main()
