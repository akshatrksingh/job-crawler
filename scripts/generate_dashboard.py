"""Generate the local private jobs dashboard."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from job_crawler.dashboard import write_dashboard
from job_crawler.storage import JobRepository, open_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="data/job_crawler.sqlite")
    parser.add_argument("--output", default="site/index.html")
    parser.add_argument("--days", type=int, default=14)
    parser.add_argument("--candidate-limit", type=int, default=10_000)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with open_database(args.db) as connection:
        repo = JobRepository(connection)
        jobs = repo.list_jobs_for_digest(limit=args.candidate_limit)
        last_refresh_at = repo.get_app_state("last_refresh_at")
    path = write_dashboard(
        jobs,
        output_path=Path(args.output),
        days=args.days,
        last_refresh_at=last_refresh_at,
    )
    print(f"dashboard={path}")
    print(f"candidates={len(jobs)}")


if __name__ == "__main__":
    main()
