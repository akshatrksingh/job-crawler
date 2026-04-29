"""Command-line entrypoint for the job crawler."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

from job_crawler.discovery import (
    build_discovery_queries,
    extract_sources_from_urls,
    fetch_sources_from_pages,
)
from job_crawler.server import run_dashboard_server
from job_crawler.storage import JobRepository, open_database


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    load_dotenv(Path.cwd() / ".env")
    parser = argparse.ArgumentParser(prog="job-crawler")
    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Serve the local private dashboard")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.add_argument("--db", type=Path, default=Path("data/job_crawler.sqlite"))
    serve.add_argument("--output", type=Path, default=Path("site/index.html"))
    serve.add_argument("--days", type=int, default=14)
    serve.add_argument("--candidate-limit", type=int, default=10_000)
    serve.add_argument(
        "--ashby-limit",
        "--ats-limit",
        dest="ashby_limit",
        type=int,
        default=10,
        help="Maximum jobs to fetch per Ashby, Greenhouse, or Lever company board",
    )
    serve.add_argument("--github-jobs-limit", type=int, default=250)
    serve.add_argument("--hn-limit", type=int, default=80)
    serve.add_argument("--yc-limit", type=int, default=80)
    serve.add_argument("--cooldown-hours", type=int, default=6)
    serve.add_argument("--auth-username", default=_env_value("JOB_CRAWLER_AUTH_USERNAME"))
    serve.add_argument("--auth-password", default=_env_value("JOB_CRAWLER_AUTH_PASSWORD"))

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
            github_jobs_limit=args.github_jobs_limit,
            hn_limit=args.hn_limit,
            yc_limit=args.yc_limit,
            cooldown_hours=args.cooldown_hours,
            auth_username=args.auth_username,
            auth_password=args.auth_password,
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


def _env_value(name: str) -> str | None:
    return os.getenv(name) or None


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
