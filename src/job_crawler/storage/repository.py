"""Repository helpers for normalized job crawler data."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from job_crawler.crawlers.base import JobPosting


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
        _normalize_text(job.source),
        _normalize_text(job.company),
        _normalize_text(job.title),
        _normalize_text(job.location),
        canonicalize_url(job.url),
    ]
    payload = "\n".join(canonical_parts)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


class JobRepository:
    """Persistence operations for sources, jobs, crawl runs, and scores."""

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

    def insert_job(self, job: JobPosting, *, raw: dict[str, Any] | None = None) -> JobInsertResult:
        """Insert a job if it is new, otherwise refresh its last-seen timestamp."""
        fingerprint = build_job_fingerprint(job)
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

    def insert_score(
        self,
        *,
        job_id: int,
        model: str,
        score: float,
        reason: str | None = None,
        prompt_version: str = "v1",
    ) -> int:
        """Store a score once per job/model/prompt version."""
        row = self.connection.execute(
            """
            INSERT INTO job_scores (job_id, model, score, reason, prompt_version)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(job_id, model, prompt_version) DO UPDATE SET
                score = excluded.score,
                reason = excluded.reason,
                scored_at = datetime('now')
            RETURNING id
            """,
            (job_id, model, score, reason, prompt_version),
        ).fetchone()
        self.connection.commit()
        return int(row["id"])

    def list_unscored_jobs(
        self,
        *,
        model: str,
        prompt_version: str = "v1",
        limit: int = 25,
    ) -> list[sqlite3.Row]:
        """Return jobs without a score for the given scorer identity."""
        return list(
            self.connection.execute(
                """
                SELECT jobs.*
                FROM jobs
                LEFT JOIN job_scores
                    ON job_scores.job_id = jobs.id
                    AND job_scores.model = ?
                    AND job_scores.prompt_version = ?
                WHERE job_scores.id IS NULL
                ORDER BY jobs.first_seen_at ASC
                LIMIT ?
                """,
                (model, prompt_version, limit),
            )
        )

    def count_rows(self, table: str) -> int:
        """Count rows in a known project table."""
        allowed_tables = {"sources", "crawl_runs", "jobs", "job_scores", "schema_migrations"}
        if table not in allowed_tables:
            msg = f"Unsupported table: {table}"
            raise ValueError(msg)
        row = self.connection.execute(f"SELECT COUNT(*) AS count FROM {table}").fetchone()
        return int(row["count"])
