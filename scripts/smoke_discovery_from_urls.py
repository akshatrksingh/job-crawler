"""Extract and store ATS sources from pasted search result URLs."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from job_crawler.discovery import extract_sources_from_urls
from job_crawler.storage import JobRepository, open_database


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("urls", nargs="+", help="Search result URLs to inspect")
    parser.add_argument("--query", default="manual", help="Search query/provenance label")
    parser.add_argument("--db", default="data/job_crawler.sqlite")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    discovered = extract_sources_from_urls(args.urls, discovered_from=args.query)
    db_path = Path(args.db)

    with open_database(db_path) as connection:
        repo = JobRepository(connection)
        for source in discovered:
            repo.upsert_discovered_source(source)

    print(f"database={db_path}")
    print(f"discovered={len(discovered)}")
    for source in discovered:
        print(f"{source.source_type}\t{source.slug}\t{source.base_url}")


if __name__ == "__main__":
    main()
