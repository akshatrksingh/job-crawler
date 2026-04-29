"""Local-only dashboard server."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from job_crawler.dashboard import render_dashboard
from job_crawler.pipeline import refresh_jobs
from job_crawler.storage import JobRepository, open_database


class DashboardServerConfig:
    """Configuration for the local dashboard server."""

    def __init__(
        self,
        *,
        db_path: Path,
        output_path: Path,
        days: int,
        candidate_limit: int,
        ashby_limit: int,
        google_jobs_limit: int,
        github_jobs_limit: int,
        linkedin_posts_limit: int,
        yc_limit: int,
        max_google_queries: int,
        cooldown_hours: int,
    ) -> None:
        self.db_path = db_path
        self.output_path = output_path
        self.days = days
        self.candidate_limit = candidate_limit
        self.ashby_limit = ashby_limit
        self.google_jobs_limit = google_jobs_limit
        self.github_jobs_limit = github_jobs_limit
        self.linkedin_posts_limit = linkedin_posts_limit
        self.yc_limit = yc_limit
        self.max_google_queries = max_google_queries
        self.cooldown_hours = cooldown_hours


def run_dashboard_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: Path = Path("data/job_crawler.sqlite"),
    output_path: Path = Path("site/index.html"),
    days: int = 14,
    candidate_limit: int = 10_000,
    ashby_limit: int = 100,
    google_jobs_limit: int = 10,
    github_jobs_limit: int = 250,
    linkedin_posts_limit: int = 40,
    yc_limit: int = 80,
    max_google_queries: int = 20,
    cooldown_hours: int = 6,
) -> None:
    """Serve the local dashboard until interrupted."""
    config = DashboardServerConfig(
        db_path=db_path,
        output_path=output_path,
        days=days,
        candidate_limit=candidate_limit,
        ashby_limit=ashby_limit,
        google_jobs_limit=google_jobs_limit,
        github_jobs_limit=github_jobs_limit,
        linkedin_posts_limit=linkedin_posts_limit,
        yc_limit=yc_limit,
        max_google_queries=max_google_queries,
        cooldown_hours=cooldown_hours,
    )
    handler = _build_handler(config)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving job dashboard at http://{host}:{port}/")
    print("Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


def _build_handler(config: DashboardServerConfig) -> type[BaseHTTPRequestHandler]:
    class DashboardRequestHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path not in {"/", "/index.html"}:
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            html = _render_current_dashboard(config)
            self._send_bytes(html.encode("utf-8"), content_type="text/html; charset=utf-8")

        def do_POST(self) -> None:
            if self.path == "/api/refresh":
                self._handle_refresh()
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def _handle_refresh(self) -> None:
            result = refresh_jobs(
                db_path=config.db_path,
                output_path=config.output_path,
                days=config.days,
                candidate_limit=config.candidate_limit,
                ashby_limit=config.ashby_limit,
                google_jobs_limit=config.google_jobs_limit,
                github_jobs_limit=config.github_jobs_limit,
                linkedin_posts_limit=config.linkedin_posts_limit,
                yc_limit=config.yc_limit,
                max_google_queries=config.max_google_queries,
                cooldown_hours=config.cooldown_hours,
                force=True,
            )
            payload = {
                "ok": not result.errors,
                "message": (
                    "Fetched stored ATS sources and refreshed dashboard."
                    if result.refreshed
                    else "Refresh cooldown active."
                ),
                "refreshed": result.refreshed,
                "seen": result.seen,
                "inserted": result.inserted,
                "candidates": result.candidates,
                "last_refresh_at": result.last_refresh_at,
                "next_refresh_at": result.next_refresh_at,
                "cooldown_seconds_remaining": result.cooldown_seconds_remaining,
                "sources": [source.__dict__ for source in result.sources],
                "errors": result.errors,
            }
            self._send_json(payload)

        def _read_json(self) -> dict[str, object]:
            length = int(self.headers.get("Content-Length", "0") or "0")
            if length <= 0:
                return {}
            body = self.rfile.read(length).decode("utf-8")
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                return {}
            return payload if isinstance(payload, dict) else {}

        def _send_json(
            self,
            payload: dict[str, object],
            *,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self._send_bytes(
                json.dumps(payload).encode("utf-8"),
                content_type="application/json; charset=utf-8",
                status=status,
            )

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_bytes(
            self,
            body: bytes,
            *,
            content_type: str,
            status: HTTPStatus = HTTPStatus.OK,
        ) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

    return DashboardRequestHandler

def _render_current_dashboard(config: DashboardServerConfig) -> str:
    with open_database(config.db_path) as connection:
        repo = JobRepository(connection)
        return render_dashboard(
            repo.list_jobs_for_digest(limit=config.candidate_limit),
            days=config.days,
            last_refresh_at=repo.get_app_state("last_refresh_at"),
            cooldown_hours=config.cooldown_hours,
        )
