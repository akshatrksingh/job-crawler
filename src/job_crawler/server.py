"""Local-only dashboard server."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from job_crawler.dashboard import render_dashboard, write_dashboard
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
    ) -> None:
        self.db_path = db_path
        self.output_path = output_path
        self.days = days
        self.candidate_limit = candidate_limit


def run_dashboard_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: Path = Path("data/job_crawler.sqlite"),
    output_path: Path = Path("site/index.html"),
    days: int = 14,
    candidate_limit: int = 10_000,
) -> None:
    """Serve the local dashboard until interrupted."""
    config = DashboardServerConfig(
        db_path=db_path,
        output_path=output_path,
        days=days,
        candidate_limit=candidate_limit,
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
            jobs = _load_jobs(config)
            write_dashboard(
                jobs,
                output_path=config.output_path,
                days=config.days,
            )
            payload = {
                "ok": True,
                "message": "Dashboard refreshed from SQLite.",
                "candidates": len(jobs),
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
    return render_dashboard(_load_jobs(config), days=config.days)


def _load_jobs(config: DashboardServerConfig):
    with open_database(config.db_path) as connection:
        repo = JobRepository(connection)
        return repo.list_jobs_for_digest(limit=config.candidate_limit)
