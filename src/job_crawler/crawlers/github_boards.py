"""Curated GitHub job-board adapters.

These boards are not company lists. They are public, community-maintained
indexes that already aggregate early-career roles across many companies.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import datetime
from html import unescape
from typing import Literal

import httpx
from bs4 import BeautifulSoup

from job_crawler.crawlers.base import JobPosting, clean_html

BoardFormat = Literal["markdown", "html"]


@dataclass(frozen=True)
class GitHubJobBoard:
    """A public README-backed job board."""

    name: str
    url: str
    format: BoardFormat
    description: str


DEFAULT_GITHUB_JOB_BOARDS = (
    GitHubJobBoard(
        name="jobright_swe_new_grad_2026",
        url=(
            "https://raw.githubusercontent.com/"
            "jobright-ai/2026-Software-Engineer-New-Grad/master/README.md"
        ),
        format="markdown",
        description="Jobright 2026 SWE new-grad board",
    ),
    GitHubJobBoard(
        name="jobright_data_analysis_new_grad_2026",
        url=(
            "https://raw.githubusercontent.com/"
            "jobright-ai/2026-Data-Analysis-New-Grad/master/README.md"
        ),
        format="markdown",
        description="Jobright 2026 data-analysis new-grad board",
    ),
    GitHubJobBoard(
        name="simplify_new_grad_positions",
        url="https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/README.md",
        format="html",
        description="Simplify/Coder Quad new-grad board",
    ),
)


def fetch_default_github_board_jobs(*, limit: int = 250) -> list[JobPosting]:
    """Fetch all default GitHub boards with a global cap."""
    postings: list[JobPosting] = []
    per_board_limit = max(1, math.ceil(limit / len(DEFAULT_GITHUB_JOB_BOARDS)))
    for board in DEFAULT_GITHUB_JOB_BOARDS:
        postings.extend(fetch_github_board_jobs(board=board, limit=per_board_limit))
    return postings[:limit]


def fetch_github_board_jobs(*, board: GitHubJobBoard, limit: int = 250) -> list[JobPosting]:
    """Fetch and parse one README-backed job board."""
    response = httpx.get(
        board.url,
        follow_redirects=True,
        timeout=20,
        headers={"User-Agent": "job-crawler/0.1"},
    )
    response.raise_for_status()
    if board.format == "html":
        return parse_html_board(response.text, board=board, limit=limit)
    return parse_markdown_board(response.text, board=board, limit=limit)


def parse_markdown_board(
    markdown: str,
    *,
    board: GitHubJobBoard,
    limit: int = 250,
) -> list[JobPosting]:
    """Parse GitHub Markdown pipe tables like Jobright's README."""
    postings: list[JobPosting] = []
    headers: list[str] | None = None
    previous_company: str | None = None

    for line in markdown.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [_clean_cell(cell) for cell in stripped.strip("|").split("|")]
        if len(cells) < 3:
            continue
        if _is_separator_row(cells):
            continue
        normalized = [_normalize_header(cell) for cell in cells]
        if "company" in normalized and any(value in normalized for value in ("job title", "role")):
            headers = normalized
            continue
        if headers is None or len(postings) >= limit:
            continue

        row = _row_by_header(headers, cells)
        company = _cell_text(row.get("company"))
        if company == "↳":
            company = previous_company
        elif company:
            previous_company = company
        title = _cell_text(row.get("job title") or row.get("role"))
        location = _cell_text(row.get("location"))
        url = _first_link(row.get("job title") or "") or _first_link(row.get("application") or "")
        date_text = _cell_text(row.get("date posted"))

        if not _is_valid_board_job(company=company, title=title, location=location, url=url):
            continue
        postings.append(
            _posting(
                board=board,
                company=company,
                title=title,
                location=location,
                url=url,
                date_text=date_text,
            )
        )

    return postings


def parse_html_board(
    html: str,
    *,
    board: GitHubJobBoard,
    limit: int = 250,
) -> list[JobPosting]:
    """Parse README HTML tables like Simplify's current board."""
    html = re.sub(r"</br\s*>", "<br/>", html, flags=re.IGNORECASE)
    soup = BeautifulSoup(html, "html.parser")
    postings: list[JobPosting] = []
    previous_company: str | None = None

    for table in soup.find_all("table"):
        headers = [
            _normalize_header(header.get_text(" ", strip=True))
            for header in table.find_all("th")
        ]
        if not headers or "company" not in headers or "location" not in headers:
            continue
        for row_node in table.find_all("tr"):
            if len(postings) >= limit:
                return postings
            cells = row_node.find_all("td")
            if len(cells) < len(headers):
                continue
            row = dict(zip(headers, cells, strict=False))
            application_cell = row.get("application")
            if application_cell and "🔒" in application_cell.get_text(" ", strip=True):
                continue

            company = _cell_text(str(row.get("company") or ""))
            if company == "↳":
                company = previous_company
            elif company:
                previous_company = company
            title = _cell_text(str(row.get("role") or row.get("job title") or ""))
            location = _cell_text(str(row.get("location") or ""))
            url = _first_apply_link(application_cell) if application_cell else None
            age = _cell_text(str(row.get("age") or ""))

            if not _is_valid_board_job(company=company, title=title, location=location, url=url):
                continue
            postings.append(
                _posting(
                    board=board,
                    company=company,
                    title=title,
                    location=location,
                    url=url,
                    date_text=age,
                )
            )

    return postings


def _posting(
    *,
    board: GitHubJobBoard,
    company: str,
    title: str,
    location: str,
    url: str,
    date_text: str | None,
) -> JobPosting:
    normalized = "|".join((board.name, company, title, location, url))
    source_id = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return JobPosting(
        source=board.name,
        source_id=source_id,
        company=company,
        title=title,
        location=location,
        url=url,
        description=f"{board.description}. Board freshness: {date_text or 'n/a'}.",
        posted_at=_parse_month_day(date_text),
    )


def _clean_cell(value: str) -> str:
    return " ".join(value.strip().split())


def _normalize_header(value: str) -> str:
    return _cell_text(value).lower()


def _row_by_header(headers: list[str], cells: list[str]) -> dict[str, str]:
    return {header: cells[index] for index, header in enumerate(headers) if index < len(cells)}


def _is_separator_row(cells: list[str]) -> bool:
    return all(set(cell.replace(" ", "")) <= {"-"} for cell in cells if cell)


def _cell_text(value: str | None) -> str:
    if not value:
        return ""
    normalized_value = re.sub(r"</?br\s*/?>", ", ", unescape(value), flags=re.IGNORECASE)
    text = BeautifulSoup(normalized_value, "html.parser").get_text(", ", strip=True)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[*_`]+", "", text)
    text = text.replace("🔥", "").replace("🛂", "").replace("🇺🇸", "")
    text = re.sub(r"\s*,\s*,+\s*", ", ", text)
    return " ".join(text.split())


def _first_link(markdown: str) -> str | None:
    match = re.search(r"\[[^\]]+\]\((https?://[^)]+)\)", markdown)
    if match:
        return match.group(1).strip()
    match = re.search(r"https?://[^\s|)]+", markdown)
    if match:
        return match.group(0).strip()
    return None


def _first_apply_link(cell) -> str | None:
    for link in cell.find_all("a", href=True):
        href = str(link["href"]).strip()
        image_alt = " ".join(image.get("alt", "") for image in link.find_all("img")).lower()
        if "simplify.jobs/p/" in href:
            continue
        if "apply" in image_alt or "simplify.jobs/p/" not in href:
            return href
    return None


def _is_valid_board_job(*, company: str | None, title: str, location: str, url: str | None) -> bool:
    return bool(company and title and location and url and _looks_like_location(location))


def _looks_like_location(value: str) -> bool:
    normalized = value.lower()
    if "http://" in normalized or "https://" in normalized:
        return False
    return any(
        token in normalized
        for token in (
            "remote",
            "united states",
            "usa",
            "us",
            "nyc",
            "sf",
            "ca",
            "ny",
            "wa",
            "ma",
            "tx",
            "il",
            "co",
            "ga",
            "fl",
            "dc",
            "va",
            "nc",
            "oh",
            "nj",
            "pa",
            "az",
            "or",
            "ut",
            "mi",
            "mn",
            "tn",
            "mo",
        )
    )


def _parse_month_day(value: str | None) -> datetime | None:
    if not value:
        return None
    text = clean_html(value) or ""
    match = re.search(r"\b([A-Z][a-z]{2})\s+(\d{1,2})\b", text)
    if not match:
        return None
    try:
        return datetime.strptime(f"{match.group(1)} {match.group(2)} 2026", "%b %d %Y")
    except ValueError:
        return None
