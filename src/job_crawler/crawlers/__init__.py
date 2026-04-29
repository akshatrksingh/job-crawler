"""Source-specific job crawlers."""

from job_crawler.crawlers.ashby import fetch_ashby_jobs, parse_ashby_jobs
from job_crawler.crawlers.github_boards import (
    DEFAULT_GITHUB_JOB_BOARDS,
    fetch_default_github_board_jobs,
    fetch_github_board_jobs,
    parse_html_board,
    parse_markdown_board,
)
from job_crawler.crawlers.google_jobs import (
    build_default_google_job_queries,
    fetch_google_jobs,
    parse_jobspy_records,
)
from job_crawler.crawlers.greenhouse import fetch_greenhouse_jobs, parse_greenhouse_jobs
from job_crawler.crawlers.lever import fetch_lever_jobs, parse_lever_jobs
from job_crawler.crawlers.linkedin_posts import (
    LINKEDIN_POST_SOURCE,
    fetch_linkedin_post_leads,
    parse_duckduckgo_results,
    parse_google_results,
)
from job_crawler.crawlers.yc import fetch_yc_jobs, parse_yc_jobs_html

__all__ = [
    "fetch_ashby_jobs",
    "fetch_greenhouse_jobs",
    "fetch_google_jobs",
    "fetch_default_github_board_jobs",
    "fetch_github_board_jobs",
    "fetch_lever_jobs",
    "fetch_linkedin_post_leads",
    "fetch_yc_jobs",
    "parse_ashby_jobs",
    "parse_greenhouse_jobs",
    "parse_html_board",
    "parse_jobspy_records",
    "parse_lever_jobs",
    "parse_google_results",
    "parse_duckduckgo_results",
    "parse_markdown_board",
    "parse_yc_jobs_html",
    "build_default_google_job_queries",
    "DEFAULT_GITHUB_JOB_BOARDS",
    "LINKEDIN_POST_SOURCE",
]
