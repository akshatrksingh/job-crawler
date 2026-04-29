"""Run one tiny Google Jobs search through python-jobspy."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from job_crawler.crawlers.google_jobs import fetch_google_jobs
from job_crawler.storage import JobRepository, open_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--search-term", default="software engineer new grad")
    parser.add_argument("--location", default="Remote")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--db", default="data/job_crawler.sqlite")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db_path = Path(args.db)
    jobs = fetch_google_jobs(
        search_term=args.search_term,
        location=args.location,
        results_wanted=args.limit,
    )
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        inserted = sum(int(repo.insert_job(job).inserted) for job in jobs)

    print(f"database={db_path}")
    print(f"search_term={args.search_term}")
    print(f"location={args.location}")
    print(f"jobs_seen={len(jobs)}")
    print(f"jobs_inserted={inserted}")


if __name__ == "__main__":
    main()
