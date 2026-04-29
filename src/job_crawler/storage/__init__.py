"""SQLite persistence layer."""

from job_crawler.storage.db import SCHEMA_VERSION, initialize_database, open_database
from job_crawler.storage.repository import (
    JobInsertResult,
    JobRepository,
    build_job_fingerprint,
    canonicalize_url,
)

__all__ = [
    "SCHEMA_VERSION",
    "JobInsertResult",
    "JobRepository",
    "build_job_fingerprint",
    "canonicalize_url",
    "initialize_database",
    "open_database",
]
