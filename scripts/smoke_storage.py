"""Create a local SQLite DB and exercise dedupe once."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from job_crawler.crawlers.base import JobPosting
from job_crawler.storage import JobRepository, open_database


def main() -> None:
    db_path = Path("data/job_crawler.sqlite")
    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        source_id = repo.upsert_source(
            source_type="ashby",
            slug="example-company",
            base_url="https://jobs.ashbyhq.com/example-company",
            discovered_from="smoke_storage",
        )
        job = JobPosting(
            source="ashby",
            source_id="job_123",
            company="Example Company",
            title="AI Engineer",
            location="New York, NY",
            url="https://jobs.ashbyhq.com/example-company/job_123?utm_source=test",
            description="Build AI products.",
        )
        first = repo.insert_job(job)
        second = repo.insert_job(job)
        repo.mark_source_crawled(source_id=source_id)

        print(f"database={db_path}")
        print(f"source_id={source_id}")
        print(f"first_inserted={first.inserted}")
        print(f"second_inserted={second.inserted}")
        print(f"jobs={repo.count_rows('jobs')}")
        print(f"sources={repo.count_rows('sources')}")


if __name__ == "__main__":
    main()
