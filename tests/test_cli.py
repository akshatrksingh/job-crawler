from job_crawler.cli import build_parser


def test_serve_parser_defaults_to_localhost() -> None:
    args = build_parser().parse_args(["serve"])

    assert args.command == "serve"
    assert args.host == "127.0.0.1"
    assert args.port == 8765
    assert args.days == 14
    assert args.ashby_limit == 100
    assert args.google_jobs_limit == 10
    assert args.max_google_queries == 9
    assert args.cooldown_hours == 6
