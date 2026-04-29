from job_crawler.cli import build_parser


def test_serve_parser_defaults_to_localhost(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("JOB_CRAWLER_AUTH_USERNAME", raising=False)
    monkeypatch.delenv("JOB_CRAWLER_AUTH_PASSWORD", raising=False)
    args = build_parser().parse_args(["serve"])

    assert args.command == "serve"
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.days == 14
    assert args.ashby_limit == 10
    assert args.github_jobs_limit == 250
    assert args.hn_limit == 80
    assert args.yc_limit == 80
    assert args.cooldown_hours == 6
    assert args.auth_username is None
    assert args.auth_password is None


def test_serve_parser_accepts_basic_auth() -> None:
    args = build_parser().parse_args(
        ["serve", "--auth-username", "akshat", "--auth-password", "secret"]
    )

    assert args.auth_username == "akshat"
    assert args.auth_password == "secret"


def test_serve_parser_accepts_ats_limit_alias() -> None:
    args = build_parser().parse_args(["serve", "--ats-limit", "25"])

    assert args.ashby_limit == 25


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
