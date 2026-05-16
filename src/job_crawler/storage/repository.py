"""Repository helpers for normalized job crawler data."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from job_crawler.crawlers.base import JobPosting
from job_crawler.discovery.sources import DiscoveredSource


@dataclass(frozen=True)
class JobInsertResult:
    """Result of inserting a normalized job."""

    job_id: int
    inserted: bool


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def canonicalize_url(url: str) -> str:
    """Canonicalize a URL enough for dedupe without hiding meaningful paths."""
    parsed = urlsplit(url.strip())
    scheme = parsed.scheme.lower() or "https"
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, "", ""))


def build_job_fingerprint(job: JobPosting) -> str:
    """Build a stable dedupe fingerprint for a posting."""
    canonical_parts = [
        _normalize_text(job.company),
        _normalize_text(job.title),
        _normalize_text(job.location),
    ]
    payload = "\n".join(canonical_parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


def _sqlite_datetime(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S")


class JobRepository:
    """Persistence operations for sources, jobs, crawl runs, and app state."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def upsert_source(
        self,
        *,
        source_type: str,
        slug: str,
        base_url: str | None = None,
        discovered_from: str | None = None,
        crawl_interval_seconds: int = 86_400,
    ) -> int:
        """Insert or update a source and return its id."""
        row = self.connection.execute(
            """
            INSERT INTO sources (
                source_type,
                slug,
                base_url,
                discovered_from,
                crawl_interval_seconds,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(source_type, slug) DO UPDATE SET
                base_url = COALESCE(excluded.base_url, sources.base_url),
                discovered_from = COALESCE(excluded.discovered_from, sources.discovered_from),
                last_discovered_at = datetime('now'),
                crawl_interval_seconds = excluded.crawl_interval_seconds,
                updated_at = datetime('now')
            RETURNING id
            """,
            (source_type, slug, base_url, discovered_from, crawl_interval_seconds),
        ).fetchone()
        self.connection.commit()
        return int(row["id"])

    def mark_source_crawled(
        self,
        *,
        source_id: int,
        next_crawl_after: str | None = None,
    ) -> None:
        """Record a source crawl timestamp for conservative reruns."""
        self.connection.execute(
            """
            UPDATE sources
            SET last_crawled_at = datetime('now'),
                next_crawl_after = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (next_crawl_after, source_id),
        )
        self.connection.commit()

    def upsert_discovered_source(self, source: DiscoveredSource) -> int:
        """Store a discovered source and preserve search provenance."""
        return self.upsert_source(
            source_type=source.source_type,
            slug=source.slug,
            base_url=source.base_url,
            discovered_from=source.discovered_from,
        )

    def list_sources(self, *, source_type: str | None = None) -> list[sqlite3.Row]:
        """List discovered sources for crawl planning."""
        if source_type is None:
            return list(
                self.connection.execute(
                    """
                    SELECT *
                    FROM sources
                    ORDER BY source_type, slug
                    """
                )
            )
        return list(
            self.connection.execute(
                """
                SELECT *
                FROM sources
                WHERE source_type = ?
                ORDER BY slug
                """,
                (source_type,),
            )
        )

    def list_due_sources(
        self,
        *,
        source_type: str,
        limit: int,
        now: datetime | None = None,
    ) -> list[sqlite3.Row]:
        """List sources whose adaptive schedule says they are worth crawling now."""
        now_sql = _sqlite_datetime(now or datetime.now(UTC))
        return list(
            self.connection.execute(
                """
                SELECT *
                FROM sources
                WHERE source_type = ?
                  AND (
                    next_crawl_after IS NULL
                    OR datetime(next_crawl_after) <= datetime(?)
                  )
                ORDER BY
                    usefulness_score DESC,
                    last_crawled_at IS NULL DESC,
                    last_crawled_at ASC,
                    slug ASC
                LIMIT ?
                """,
                (source_type, now_sql, limit),
            )
        )

    def start_crawl_run(self, *, source_type: str, source_id: int | None = None) -> int:
        """Create a crawl run record and return its id."""
        cursor = self.connection.execute(
            """
            INSERT INTO crawl_runs (source_id, source_type)
            VALUES (?, ?)
            """,
            (source_id, source_type),
        )
        self.connection.commit()
        return int(cursor.lastrowid)

    def finish_crawl_run(
        self,
        *,
        crawl_run_id: int,
        status: str,
        jobs_seen: int,
        jobs_inserted: int,
        error: str | None = None,
    ) -> None:
        """Finish a crawl run with counts and status."""
        self.connection.execute(
            """
            UPDATE crawl_runs
            SET finished_at = datetime('now'),
                status = ?,
                jobs_seen = ?,
                jobs_inserted = ?,
                error = ?
            WHERE id = ?
            """,
            (status, jobs_seen, jobs_inserted, error, crawl_run_id),
        )
        self.connection.commit()

    def cleanup_stale_crawl_runs(self, *, stale_after_minutes: int = 90) -> int:
        """Mark abandoned running crawl rows as failed so the dashboard is honest."""
        cutoff = _sqlite_datetime(datetime.now(UTC) - timedelta(minutes=stale_after_minutes))
        cursor = self.connection.execute(
            """
            UPDATE crawl_runs
            SET status = 'failed',
                finished_at = datetime('now'),
                error = 'stale running crawl cleaned up after process exit or interruption'
            WHERE status = 'running'
              AND datetime(started_at) <= datetime(?)
            """,
            (cutoff,),
        )
        self.connection.commit()
        return int(cursor.rowcount)

    def record_source_crawl_outcome(
        self,
        *,
        source_id: int,
        jobs_seen: int,
        jobs_inserted: int,
        error: str | None = None,
        now: datetime | None = None,
    ) -> None:
        """Update source usefulness and next crawl time from the latest outcome."""
        source = self.connection.execute(
            """
            SELECT usefulness_score, consecutive_empty_runs, consecutive_error_runs
            FROM sources
            WHERE id = ?
            """,
            (source_id,),
        ).fetchone()
        if source is None:
            return

        current_score = float(source["usefulness_score"])
        empty_runs = int(source["consecutive_empty_runs"])
        error_runs = int(source["consecutive_error_runs"])
        crawl_time = now or datetime.now(UTC)

        if error:
            error_runs += 1
            empty_runs = 0
            is_not_found = "404" in error or "not found" in error.lower()
            delay_days = 30 if is_not_found else min(14, 2 * error_runs)
            score = max(0.0, current_score - (35 if delay_days == 30 else 18))
        elif jobs_inserted > 0:
            error_runs = 0
            empty_runs = 0
            delay_days = 1
            score = min(100.0, current_score + 20 + min(jobs_inserted, 5) * 3)
        elif jobs_seen > 0:
            error_runs = 0
            empty_runs += 1
            delay_days = 3 if empty_runs == 1 else 7 if empty_runs == 2 else 14
            score = max(5.0, current_score - 8)
        else:
            error_runs = 0
            empty_runs += 1
            delay_days = 7 if empty_runs <= 1 else 14
            score = max(5.0, current_score - 14)

        next_crawl_after = _sqlite_datetime(crawl_time + timedelta(days=delay_days))
        self.connection.execute(
            """
            UPDATE sources
            SET last_crawled_at = ?,
                next_crawl_after = ?,
                usefulness_score = ?,
                consecutive_empty_runs = ?,
                consecutive_error_runs = ?,
                last_jobs_seen = ?,
                last_jobs_inserted = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (
                _sqlite_datetime(crawl_time),
                next_crawl_after,
                score,
                empty_runs,
                error_runs,
                jobs_seen,
                jobs_inserted,
                source_id,
            ),
        )
        self.connection.commit()

    def insert_job(self, job: JobPosting, *, raw: dict[str, Any] | None = None) -> JobInsertResult:
        """Insert a job if it is new, otherwise refresh its last-seen timestamp."""
        fingerprint = build_job_fingerprint(job)
        if self._is_dismissed_job(job, fingerprint=fingerprint):
            return JobInsertResult(job_id=0, inserted=False)
        existing_id = self._find_semantic_duplicate(job)
        if existing_id is not None:
            self.connection.execute(
                """
                UPDATE jobs
                SET last_seen_at = datetime('now'),
                    url = CASE
                        WHEN source = 'github_jobs' THEN ?
                        ELSE url
                    END
                WHERE id = ?
                """,
                (canonicalize_url(job.url), existing_id),
            )
            self.connection.commit()
            return JobInsertResult(job_id=existing_id, inserted=False)

        raw_json = json.dumps(raw, sort_keys=True) if raw is not None else None
        cursor = self.connection.execute(
            """
            INSERT OR IGNORE INTO jobs (
                source,
                source_id,
                fingerprint,
                company,
                title,
                location,
                url,
                description,
                posted_at,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.source,
                job.source_id,
                fingerprint,
                job.company,
                job.title,
                job.location,
                canonicalize_url(job.url),
                job.description,
                _to_iso(job.posted_at),
                raw_json,
            ),
        )
        inserted = cursor.rowcount == 1
        if not inserted:
            self.connection.execute(
                """
                UPDATE jobs
                SET last_seen_at = datetime('now')
                WHERE fingerprint = ? OR (source = ? AND source_id = ?)
                """,
                (fingerprint, job.source, job.source_id),
        )
        row = self.connection.execute(
            """
            SELECT id
            FROM jobs
            WHERE fingerprint = ? OR (source = ? AND source_id = ?)
            ORDER BY id
            LIMIT 1
            """,
            (fingerprint, job.source, job.source_id),
        ).fetchone()
        self.connection.commit()
        return JobInsertResult(job_id=int(row["id"]), inserted=inserted)

    def _find_semantic_duplicate(self, job: JobPosting) -> int | None:
        row = self.connection.execute(
            """
            SELECT id
            FROM jobs
            WHERE lower(company) = ?
              AND lower(title) = ?
              AND lower(COALESCE(location, '')) = ?
            ORDER BY
                CASE WHEN source = 'github_jobs' THEN 1 ELSE 0 END,
                id
            LIMIT 1
            """,
            (
                _normalize_text(job.company),
                _normalize_text(job.title),
                _normalize_text(job.location),
            ),
        ).fetchone()
        return int(row["id"]) if row else None

    def _is_dismissed_job(self, job: JobPosting, *, fingerprint: str) -> bool:
        row = self.connection.execute(
            """
            SELECT 1
            FROM dismissed_jobs
            WHERE fingerprint = ? OR (source = ? AND source_id = ?)
            LIMIT 1
            """,
            (fingerprint, job.source, job.source_id),
        ).fetchone()
        return row is not None

    def list_recent_jobs(
        self,
        *,
        limit: int = 250,
        excluded_sources: tuple[str, ...] = (),
    ) -> list[JobPosting]:
        """Return recently seen jobs for dashboard filtering and ranking."""
        where_clause = ""
        params: list[object] = []
        if excluded_sources:
            placeholders = ", ".join("?" for _ in excluded_sources)
            where_clause = f"WHERE source NOT IN ({placeholders})"
            params.extend(excluded_sources)
        params.append(limit)
        rows = self.connection.execute(
            f"""
            SELECT
                id,
                source,
                source_id,
                company,
                title,
                location,
                url,
                description,
                posted_at,
                first_seen_at
            FROM jobs
            {where_clause}
            ORDER BY first_seen_at DESC, id DESC
            LIMIT ?
            """,
            params,
        ).fetchall()
        return [
            JobPosting(
                source=row["source"],
                source_id=row["source_id"],
                company=row["company"],
                title=row["title"],
                location=row["location"],
                url=row["url"],
                description=row["description"],
                posted_at=datetime.fromisoformat(row["posted_at"]) if row["posted_at"] else None,
                first_seen_at=datetime.fromisoformat(row["first_seen_at"])
                if row["first_seen_at"]
                else None,
                id=int(row["id"]),
            )
            for row in rows
        ]

    def delete_jobs(self, job_ids: list[int]) -> int:
        """Dismiss selected jobs and remove them from the active dashboard list."""
        unique_ids = sorted({int(job_id) for job_id in job_ids if int(job_id) > 0})
        if not unique_ids:
            return 0
        placeholders = ", ".join("?" for _ in unique_ids)
        rows = self.connection.execute(
            f"""
            SELECT source, source_id, fingerprint, company, title, location, url
            FROM jobs
            WHERE id IN ({placeholders})
            """,
            unique_ids,
        ).fetchall()
        for row in rows:
            self.connection.execute(
                """
                INSERT OR IGNORE INTO dismissed_jobs (
                    source,
                    source_id,
                    fingerprint,
                    company,
                    title,
                    location,
                    url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["source"],
                    row["source_id"],
                    row["fingerprint"],
                    row["company"],
                    row["title"],
                    row["location"],
                    row["url"],
                ),
            )
        cursor = self.connection.execute(
            f"DELETE FROM jobs WHERE id IN ({placeholders})",
            unique_ids,
        )
        self.connection.commit()
        return int(cursor.rowcount)

    def list_recent_crawl_runs(
        self,
        *,
        limit: int = 25,
        excluded_source_types: tuple[str, ...] = ("google_jobs",),
    ) -> list[sqlite3.Row]:
        """Return recent source refresh runs for dashboard diagnostics."""
        where_clause = ""
        params: list[object] = []
        if excluded_source_types:
            placeholders = ", ".join("?" for _ in excluded_source_types)
            where_clause = f"WHERE crawl_runs.source_type NOT IN ({placeholders})"
            params.extend(excluded_source_types)
        params.append(limit)
        return list(
            self.connection.execute(
                f"""
                SELECT
                    crawl_runs.source_type,
                    sources.slug AS source_slug,
                    crawl_runs.started_at,
                    crawl_runs.finished_at,
                    crawl_runs.status,
                    crawl_runs.jobs_seen,
                    crawl_runs.jobs_inserted,
                    crawl_runs.error
                FROM crawl_runs
                LEFT JOIN sources ON sources.id = crawl_runs.source_id
                {where_clause}
                ORDER BY crawl_runs.started_at DESC, crawl_runs.id DESC
                LIMIT ?
                """,
                params,
            )
        )

    def get_app_state(self, key: str) -> str | None:
        """Read a persisted app state value."""
        row = self.connection.execute(
            """
            SELECT value
            FROM app_state
            WHERE key = ?
            """,
            (key,),
        ).fetchone()
        return str(row["value"]) if row else None

    def set_app_state(self, key: str, value: str) -> None:
        """Persist an app state value."""
        self.connection.execute(
            """
            INSERT INTO app_state (key, value, updated_at)
            VALUES (?, ?, datetime('now'))
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = datetime('now')
            """,
            (key, value),
        )
        self.connection.commit()

    def count_rows(self, table: str) -> int:
        """Count rows in a known project table."""
        allowed_tables = {
            "sources",
            "crawl_runs",
            "jobs",
            "dismissed_jobs",
            "app_state",
            "schema_migrations",
        }
        if table not in allowed_tables:
            msg = f"Unsupported table: {table}"
            raise ValueError(msg)
        row = self.connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        return int(row["count"])
