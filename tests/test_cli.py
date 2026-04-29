from job_crawler.cli import build_parser


def test_serve_parser_defaults_to_localhost() -> None:
    args = build_parser().parse_args(["serve"])

    assert args.command == "serve"
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.days == 14
    assert args.ashby_limit == 100
    assert args.google_jobs_limit == 10
    assert args.github_jobs_limit == 250
    assert args.linkedin_posts_limit == 40
    assert args.yc_limit == 80
    assert args.max_google_queries == 20
    assert args.cooldown_hours == 6


def test_discovery_query_parser() -> None:
    args = build_parser().parse_args(["discovery-queries", "--limit", "7"])

    assert args.command == "discovery-queries"
    assert args.limit == 7


def test_ingest_urls_parser_accepts_file_and_query() -> None:
    args = build_parser().parse_args(
        [
            "ingest-urls",
            "https://jobs.ashbyhq.com/example",
            "--file",
            "urls.txt",
            "--query",
            "site:jobs.ashbyhq.com ai engineer",
        ]
    )

    assert args.command == "ingest-urls"
    assert args.urls == ["https://jobs.ashbyhq.com/example"]
    assert str(args.file) == "urls.txt"
    assert args.query == "site:jobs.ashbyhq.com ai engineer"


def test_discover_pages_parser_accepts_limit() -> None:
    args = build_parser().parse_args(
        ["discover-pages", "https://example.com/careers", "--limit", "3"]
    )

    assert args.command == "discover-pages"
    assert args.urls == ["https://example.com/careers"]
    assert args.limit == 3
