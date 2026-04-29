"""Command-line entrypoint for the job crawler."""

from __future__ import annotations

import argparse
from pathlib import Path

from job_crawler.server import run_dashboard_server


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
        )
