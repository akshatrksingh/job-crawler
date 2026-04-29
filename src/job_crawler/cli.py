"""Command-line entrypoint for the job crawler."""

from __future__ import annotations

import argparse
from pathlib import Path

from job_crawler.discovery import (
    build_discovery_queries,
    extract_sources_from_urls,
    fetch_sources_from_pages,
)
from job_crawler.server import run_dashboard_server
from job_crawler.storage import JobRepository, open_database


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(prog="job-crawler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Serve the local private dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--db", type=Path, default=Path("data/job_crawler.sqlite"))
    serve.add_argument("--output", type=Path, default=Path("site/index.html"))
    serve.add_argument("--days", type=int, default=14)
    serve.add_argument("--candidate-limit", type=int, default=10_000)
    serve.add_argument("--ashby-limit", type=int, default=100)
    serve.add_argument("--google-jobs-limit", type=int, default=10)
    serve.add_argument("--github-jobs-limit", type=int, default=250)
    serve.add_argument("--linkedin-posts-limit", type=int, default=40)
    serve.add_argument("--yc-limit", type=int, default=80)
    serve.add_argument("--max-google-queries", type=int, default=20)
    serve.add_argument("--cooldown-hours", type=int, default=6)

    queries = subparsers.add_parser(
        "discovery-queries",
        help="Print Google search queries for finding ATS company sources",
    )
    queries.add_argument("--limit", type=int, default=60)

    ingest = subparsers.add_parser(
        "ingest-urls",
        help="Store ATS sources extracted from pasted search-result URLs",
    )
    ingest.add_argument("urls", nargs="*")
    ingest.add_argument("--file", type=Path, help="Text file with one URL per line")
    ingest.add_argument("--query", default="manual", help="Search query/provenance label")
    ingest.add_argument("--db", type=Path, default=Path("data/job_crawler.sqlite"))

    pages = subparsers.add_parser(
        "discover-pages",
        help="Fetch company career pages and store linked ATS sources",
    )
    pages.add_argument("urls", nargs="*")
    pages.add_argument("--file", type=Path, help="Text file with one URL per line")
    pages.add_argument("--query", default="company career page")
    pages.add_argument("--db", type=Path, default=Path("data/job_crawler.sqlite"))
    pages.add_argument("--limit", type=int, default=50)

    return parser


def main(argv: list[str] | None = None) -> None:
    """Run the job crawler CLI."""
    args = build_parser().parse_args(argv)
    if args.command == "serve":
        run_dashboard_server(
            host=args.host,
            port=args.port,
            db_path=args.db,
            output_path=args.output,
            days=args.days,
            candidate_limit=args.candidate_limit,
            ashby_limit=args.ashby_limit,
            google_jobs_limit=args.google_jobs_limit,
            github_jobs_limit=args.github_jobs_limit,
            linkedin_posts_limit=args.linkedin_posts_limit,
            yc_limit=args.yc_limit,
            max_google_queries=args.max_google_queries,
            cooldown_hours=args.cooldown_hours,
        )
    elif args.command == "discovery-queries":
        for query in build_discovery_queries(limit=args.limit):
            print(query)
    elif args.command == "ingest-urls":
        urls = _collect_urls(args.urls, args.file)
        discovered = extract_sources_from_urls(urls, discovered_from=args.query)
        _store_discovered_sources(db_path=args.db, discovered=discovered)
    elif args.command == "discover-pages":
        urls = _collect_urls(args.urls, args.file)
        discovered = fetch_sources_from_pages(
            urls,
            discovered_from=args.query,
            limit=args.limit,
        )
        _store_discovered_sources(db_path=args.db, discovered=discovered)


def _collect_urls(urls: list[str], file: Path | None) -> list[str]:
    collected = list(urls)
    if file is not None:
        collected.extend(
            line.strip()
            for line in file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )
    return collected


def _store_discovered_sources(
    *,
    db_path: Path,
    discovered,
) -> None:
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
