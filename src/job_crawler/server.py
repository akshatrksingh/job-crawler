"""Local-only dashboard server."""

from __future__ import annotations

import base64
import hmac
import json
import threading
from datetime import UTC, datetime
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
        github_jobs_limit: int,
        hn_limit: int,
        yc_limit: int,
        ats_workers: int,
        source_timeout_seconds: float,
        auth_username: str | None = None,
        auth_password: str | None = None,
    ) -> None:
        self.db_path = db_path
        self.output_path = output_path
        self.days = days
        self.candidate_limit = candidate_limit
        self.ashby_limit = ashby_limit
        self.github_jobs_limit = github_jobs_limit
        self.hn_limit = hn_limit
        self.yc_limit = yc_limit
        self.ats_workers = ats_workers
        self.source_timeout_seconds = source_timeout_seconds
        self.auth_username = auth_username
        self.auth_password = auth_password
        self.refresh_lock = threading.Lock()
        self.progress_lock = threading.Lock()
        self.refresh_progress: dict[str, object] = _idle_progress()

    @property
    def auth_enabled(self) -> bool:
        """Whether requests should require Basic Auth."""
        return bool(self.auth_username and self.auth_password)


def run_dashboard_server(
    *,
    host: str = "127.0.0.1",
    port: int = 8765,
    db_path: Path = Path("data/job_crawler.sqlite"),
    output_path: Path = Path("site/index.html"),
    days: int = 14,
    candidate_limit: int = 10_000,
    ashby_limit: int = 10,
    github_jobs_limit: int = 250,
    hn_limit: int = 80,
    yc_limit: int = 80,
    ats_workers: int = 8,
    source_timeout_seconds: float = 75.0,
    auth_username: str | None = None,
    auth_password: str | None = None,
) -> None:
    """Serve the local dashboard until interrupted."""
    config = DashboardServerConfig(
        db_path=db_path,
        output_path=output_path,
        days=days,
        candidate_limit=candidate_limit,
        ashby_limit=ashby_limit,
        github_jobs_limit=github_jobs_limit,
        hn_limit=hn_limit,
        yc_limit=yc_limit,
        ats_workers=ats_workers,
        source_timeout_seconds=source_timeout_seconds,
        auth_username=auth_username,
        auth_password=auth_password,
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
            if self.path == "/health":
                self._send_bytes(b"ok\n", content_type="text/plain; charset=utf-8")
                return
            if not _is_authorized(self.headers.get("Authorization"), config):
                self._send_auth_required()
                return
            if self.path not in {"/", "/index.html"}:
                if self.path == "/api/refresh-progress":
                    self._send_json(_get_progress(config))
                    return
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            html = _render_current_dashboard(config)
            self._send_bytes(html.encode("utf-8"), content_type="text/html; charset=utf-8")

        def do_POST(self) -> None:
            if not _is_authorized(self.headers.get("Authorization"), config):
                self._send_auth_required()
                return
            if self.path == "/api/refresh":
                self._handle_refresh()
                return
            if self.path == "/api/jobs/delete":
                self._handle_delete_jobs()
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def _handle_refresh(self) -> None:
            if not config.refresh_lock.acquire(blocking=False):
                self._send_json(_get_progress(config))
                return
            _set_progress(
                config,
                ok=True,
                running=True,
                done=False,
                message="Starting refresh...",
                started_at=_now_iso(),
                phase="starting",
                completed=0,
                total=None,
                eta_seconds=None,
                refreshed=False,
                seen=0,
                inserted=0,
                candidates=0,
                sources=[],
                errors=[],
            )
            thread = threading.Thread(target=_run_refresh_background, args=(config,), daemon=True)
            thread.start()
            self._send_json(_get_progress(config), status=HTTPStatus.ACCEPTED)

        def _handle_delete_jobs(self) -> None:
            payload = self._read_json()
            raw_ids = payload.get("job_ids", [])
            if not isinstance(raw_ids, list):
                self._send_json(
                    {"ok": False, "deleted": 0, "error": "job_ids must be a list"},
                    status=HTTPStatus.BAD_REQUEST,
                )
                return
            job_ids: list[int] = []
            for raw_id in raw_ids:
                try:
                    job_ids.append(int(raw_id))
                except (TypeError, ValueError):
                    continue
            with open_database(config.db_path) as connection:
                repo = JobRepository(connection)
                deleted = repo.delete_jobs(job_ids)
                html = render_dashboard(
                    repo.list_recent_jobs(limit=config.candidate_limit),
                    days=config.days,
                    last_refresh_at=repo.get_app_state("last_refresh_at"),
                    refresh_runs=repo.list_recent_crawl_runs(),
                )
                config.output_path.parent.mkdir(parents=True, exist_ok=True)
                config.output_path.write_text(html, encoding="utf-8")
            self._send_json({"ok": True, "deleted": deleted})

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

        def _send_auth_required(self) -> None:
            self.send_response(HTTPStatus.UNAUTHORIZED)
            self.send_header("WWW-Authenticate", 'Basic realm="job-crawler"')
            self.send_header("Content-Length", "0")
            self.end_headers()

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


def _run_refresh_background(config: DashboardServerConfig) -> None:
    try:
        result = refresh_jobs(
            db_path=config.db_path,
            output_path=config.output_path,
            days=config.days,
            candidate_limit=config.candidate_limit,
            ashby_limit=config.ashby_limit,
            github_jobs_limit=config.github_jobs_limit,
            hn_limit=config.hn_limit,
            yc_limit=config.yc_limit,
            ats_workers=config.ats_workers,
            source_timeout_seconds=config.source_timeout_seconds,
            progress_callback=lambda payload: _set_progress(config, **payload),
        )
        _set_progress(
            config,
            ok=not result.errors,
            running=False,
            done=True,
            phase="done",
            message="Refresh complete.",
            completed=None,
            total=None,
            eta_seconds=0,
            refreshed=result.refreshed,
            seen=result.seen,
            inserted=result.inserted,
            candidates=result.candidates,
            last_refresh_at=result.last_refresh_at,
            sources=[source.__dict__ for source in result.sources],
            errors=result.errors,
            finished_at=_now_iso(),
        )
    except Exception as exc:
        _set_progress(
            config,
            ok=False,
            running=False,
            done=True,
            phase="failed",
            message=f"Refresh failed: {exc}",
            errors=[str(exc)],
            finished_at=_now_iso(),
        )
    finally:
        config.refresh_lock.release()


def _idle_progress() -> dict[str, object]:
    return {
        "ok": True,
        "running": False,
        "done": False,
        "message": "Idle.",
        "phase": "idle",
        "completed": None,
        "total": None,
        "eta_seconds": None,
        "refreshed": False,
        "seen": 0,
        "inserted": 0,
        "candidates": 0,
        "sources": [],
        "errors": [],
    }


def _get_progress(config: DashboardServerConfig) -> dict[str, object]:
    with config.progress_lock:
        return dict(config.refresh_progress)


def _set_progress(config: DashboardServerConfig, **updates: object) -> None:
    with config.progress_lock:
        config.refresh_progress.update(updates)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _is_authorized(header: str | None, config: DashboardServerConfig) -> bool:
    if not config.auth_enabled:
        return True
    if not header or not header.startswith("Basic "):
        return False
    try:
        decoded = base64.b64decode(header.removeprefix("Basic ").strip()).decode("utf-8")
    except ValueError:
        return False
    username, separator, password = decoded.partition(":")
    if separator != ":":
        return False
    return hmac.compare_digest(username, config.auth_username or "") and hmac.compare_digest(
        password,
        config.auth_password or "",
    )


def _render_current_dashboard(config: DashboardServerConfig) -> str:
    with open_database(config.db_path) as connection:
        repo = JobRepository(connection)
        return render_dashboard(
            repo.list_recent_jobs(limit=config.candidate_limit),
            days=config.days,
            last_refresh_at=repo.get_app_state("last_refresh_at"),
            refresh_runs=repo.list_recent_crawl_runs(),
        )
