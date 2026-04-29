"""Runtime settings for the job crawler."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven crawler settings."""

    model_config = SettingsConfigDict(env_prefix="JOB_CRAWLER_", env_file=".env")

    db_path: Path = Path("data/job_crawler.sqlite")
    digest_limit: int = Field(default=25, ge=1, le=100)
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
