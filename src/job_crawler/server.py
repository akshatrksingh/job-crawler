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
        cooldown_hours: int,
    ) -> None:
        self.db_path = db_path
        self.output_path = output_path
        self.days = days
        self.candidate_limit = candidate_limit
        self.ashby_limit = ashby_limit
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
    cooldown_hours: int = 6,
) -> None:
    """Serve the local dashboard until interrupted."""
    config = DashboardServerConfig(
        db_path=db_path,
        output_path=output_path,
        days=days,
        candidate_limit=candidate_limit,
        ashby_limit=ashby_limit,
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
            if self.path != "/api/refresh":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            result = refresh_jobs(
                db_path=config.db_path,
                output_path=config.output_path,
                days=config.days,
                candidate_limit=config.candidate_limit,
                ashby_limit=config.ashby_limit,
                cooldown_hours=config.cooldown_hours,
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
            self._send_bytes(
                json.dumps(payload).encode("utf-8"),
                content_type="application/json; charset=utf-8",
            )

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_bytes(self, body: bytes, *, content_type: str) -> None:
            self.send_response(HTTPStatus.OK)
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
