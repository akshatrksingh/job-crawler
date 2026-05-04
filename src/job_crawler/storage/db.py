"""SQLite connection and schema management."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCHEMA_VERSION = 3


SCHEMA_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY,
    source_type TEXT NOT NULL,
    slug TEXT NOT NULL,
    base_url TEXT,
    discovered_from TEXT,
    last_discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_crawled_at TEXT,
    next_crawl_after TEXT,
    crawl_interval_seconds INTEGER NOT NULL DEFAULT 86400,
    usefulness_score REAL NOT NULL DEFAULT 50,
    consecutive_empty_runs INTEGER NOT NULL DEFAULT 0,
    consecutive_error_runs INTEGER NOT NULL DEFAULT 0,
    last_jobs_seen INTEGER NOT NULL DEFAULT 0,
    last_jobs_inserted INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (source_type, slug)
);

CREATE TABLE IF NOT EXISTS crawl_runs (
    id INTEGER PRIMARY KEY,
    source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL,
    started_at TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    jobs_seen INTEGER NOT NULL DEFAULT 0,
    jobs_inserted INTEGER NOT NULL DEFAULT 0,
    error TEXT
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,
    source_id TEXT NOT NULL,
    fingerprint TEXT NOT NULL UNIQUE,
    company TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT,
    url TEXT NOT NULL,
    description TEXT,
    posted_at TEXT,
    first_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
    raw_json TEXT,
    UNIQUE (source, source_id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_first_seen_at ON jobs(first_seen_at);
CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);

CREATE TABLE IF NOT EXISTS app_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_migrations (version) VALUES (1);
INSERT OR IGNORE INTO schema_migrations (version) VALUES (2);
INSERT OR IGNORE INTO schema_migrations (version) VALUES (3);
"""

SOURCE_SCHEDULING_MIGRATIONS = (
    "ALTER TABLE sources ADD COLUMN usefulness_score REAL NOT NULL DEFAULT 50",
    "ALTER TABLE sources ADD COLUMN consecutive_empty_runs INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE sources ADD COLUMN consecutive_error_runs INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE sources ADD COLUMN last_jobs_seen INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE sources ADD COLUMN last_jobs_inserted INTEGER NOT NULL DEFAULT 0",
)


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a SQLite connection configured for this project."""
    path = Path(db_path)
    if path != Path(":memory:"):
        path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    return connection


def initialize_database(connection: sqlite3.Connection) -> None:
    """Create all schema objects if they do not already exist."""
    connection.executescript(SCHEMA_SQL)
    for statement in SOURCE_SCHEDULING_MIGRATIONS:
        try:
            connection.execute(statement)
        except sqlite3.OperationalError as exc:
            if "duplicate column name" not in str(exc).lower():
                raise
    connection.commit()


@contextmanager
def open_database(db_path: str | Path) -> Iterator[sqlite3.Connection]:
    """Open and initialize a database, then close it when done."""
    connection = connect(db_path)
    try:
        initialize_database(connection)
        yield connection
    finally:
        connection.close()
