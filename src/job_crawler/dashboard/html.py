"""Static HTML dashboard for locally fetched jobs."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path
from typing import Any

from job_crawler.crawlers.base import JobPosting
from job_crawler.ranking import is_target_role, is_us_role, rank_job, role_category


@dataclass(frozen=True)
class DashboardJob:
    """A job prepared for the dashboard."""

    company: str
    title: str
    url: str
    location: str
    source: str
    role: str
    seen_date: date
    rank_score: int


def select_dashboard_jobs(
    jobs: list[JobPosting],
    *,
    today: date | None = None,
    days: int = 14,
) -> list[DashboardJob]:
    """Select non-senior jobs visible within the rolling dashboard window."""
    current_date = today or datetime.now(UTC).date()
    cutoff = current_date - timedelta(days=days)
    selected: list[DashboardJob] = []
    for job in jobs:
        if job.source == "yc" and "/jobs/role/" in job.url:
            continue
        if not is_target_role(job):
            continue
        if not is_us_role(job):
            continue
        ranked = rank_job(job)
        if ranked.excluded:
            continue
        visible_date = _window_date(job)
        if visible_date < cutoff:
            continue
        selected.append(
            DashboardJob(
                company=job.company,
                title=job.title,
                url=job.url,
                location=job.location or "Unknown",
                source=job.source,
                role=role_category(job.title),
                seen_date=_seen_date(job),
                rank_score=ranked.score,
            )
        )
    ranked = sorted(
        selected,
        key=lambda job: (
            -_date_to_ordinal(job.seen_date),
            -job.rank_score,
            job.company.lower(),
            job.title.lower(),
        ),
    )
    return _interleave_location_buckets(ranked)


def render_dashboard(
    jobs: list[JobPosting],
    *,
    today: date | None = None,
    days: int = 14,
    last_refresh_at: str | None = None,
    refresh_runs: list[Mapping[str, Any]] | None = None,
) -> str:
    """Render a standalone local HTML dashboard."""
    selected = select_dashboard_jobs(jobs, today=today, days=days)
    rows = "\n".join(_render_row(job) for job in selected)
    refresh_rows = "\n".join(_render_refresh_run(row) for row in (refresh_runs or []))
    refresh_status = refresh_rows or _render_empty_refresh_run()
    refresh_warning = _render_refresh_warning(refresh_runs or [])
    refresh = _refresh_metadata(last_refresh_at)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Job Crawler</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f5efe7;
      --panel: #fffbf4;
      --panel-2: #f9f1e6;
      --text: #2b211a;
      --muted: #7c6a5d;
      --line: #dfd0bf;
      --accent: #9f4f2f;
      --accent-2: #365f5a;
      --shadow: 0 16px 40px rgba(62, 39, 24, 0.08);
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: ui-serif, Georgia, "Times New Roman", serif;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 30px 20px 48px;
    }}
    header {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      align-items: end;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 6px;
      font-size: 31px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .meta, .status {{
      color: var(--muted);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
    }}
    .actions {{
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: end;
      flex-wrap: wrap;
      text-align: right;
    }}
    button {{
      min-height: 40px;
      border: 1px solid var(--accent);
      border-radius: 7px;
      padding: 0 14px;
      background: var(--accent);
      color: #fffaf3;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
      font-weight: 650;
      cursor: pointer;
    }}
    button.secondary {{
      border-color: var(--line);
      background: var(--panel);
      color: var(--text);
    }}
    button:disabled {{
      cursor: not-allowed;
      opacity: 0.58;
    }}
    .table-wrap {{
      overflow: auto;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
    }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: end;
      margin: 34px 0 12px;
    }}
    h2 {{
      margin: 0;
      font-size: 21px;
      letter-spacing: 0;
    }}
    .error-text {{
      color: #9f2f2f;
      max-width: 360px;
    }}
    .warning {{
      margin: 0 0 18px;
      padding: 12px 14px;
      border: 1px solid #c98252;
      border-radius: 8px;
      background: #fff5e8;
      color: #6c3d20;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      min-width: 780px;
    }}
    th, td {{
      padding: 13px 12px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
      background: var(--panel-2);
    }}
    a {{
      color: var(--accent-2);
      font-weight: 680;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .pager {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin: 14px 0 0;
      color: var(--muted);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 14px;
    }}
    .empty {{
      display: none;
      margin-top: 12px;
      padding: 18px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      color: var(--muted);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    @media (max-width: 860px) {{
      header {{
        display: block;
      }}
      .actions {{
        justify-content: start;
        text-align: left;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Job Crawler</h1>
        <div class="meta">{len(selected)} jobs from the last {days} days</div>
      </div>
      <div class="actions">
        <button id="refresh" type="button">Refresh</button>
        <div id="status" class="status">{escape(refresh["status"])}</div>
      </div>
    </header>
    {refresh_warning}

    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Company</th>
            <th>Job</th>
            <th>Location</th>
            <th>Role</th>
            <th>Source</th>
          </tr>
        </thead>
        <tbody id="jobs">
          {rows}
        </tbody>
      </table>
    </div>
    <div class="pager">
      <span id="page-summary"></span>
      <span>
        <button class="secondary" id="prev" type="button">Previous</button>
        <button class="secondary" id="next" type="button">Next</button>
      </span>
    </div>
    <div id="empty" class="empty">No jobs match the current filters.</div>

    <section>
      <div class="section-head">
        <div>
          <h2>Refresh Status</h2>
          <div class="meta">Most recent source runs</div>
        </div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Source</th>
              <th>Status</th>
              <th>Seen</th>
              <th>New</th>
              <th>Finished</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {refresh_status}
          </tbody>
        </table>
      </div>
    </section>
  </main>
  <script>
    const pageSize = 50;
    const rows = Array.from(document.querySelectorAll("#jobs tr"));
    const empty = document.getElementById("empty");
    const refresh = document.getElementById("refresh");
    const status = document.getElementById("status");
    const prev = document.getElementById("prev");
    const next = document.getElementById("next");
    const summary = document.getElementById("page-summary");
    let page = 1;
    let filteredRows = rows;

    function renderPage() {{
      const pages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
      page = Math.min(page, pages);
      const start = (page - 1) * pageSize;
      const end = start + pageSize;
      const visible = new Set(filteredRows.slice(start, end));
      for (const row of rows) {{
        row.style.display = visible.has(row) ? "" : "none";
      }}
      empty.style.display = filteredRows.length === 0 ? "block" : "none";
      prev.disabled = page <= 1;
      next.disabled = page >= pages;
      const shownStart = filteredRows.length === 0 ? 0 : start + 1;
      const shownEnd = Math.min(end, filteredRows.length);
      summary.textContent = `${{shownStart}}-${{shownEnd}} of ${{filteredRows.length}} jobs`;
    }}

    prev.addEventListener("click", () => {{
      page -= 1;
      renderPage();
    }});
    next.addEventListener("click", () => {{
      page += 1;
      renderPage();
    }});
    refresh.addEventListener("click", async () => {{
      refresh.disabled = true;
      status.textContent = "Starting refresh...";
      try {{
        const response = await fetch("/api/refresh", {{ method: "POST" }});
        if (!response.ok) throw new Error("refresh failed");
        await response.json();
        pollRefresh();
      }} catch (error) {{
        status.textContent = "Refresh requires the local server.";
        refresh.disabled = false;
      }}
    }});
    async function pollRefresh() {{
      try {{
        const response = await fetch("/api/refresh-progress");
        if (!response.ok) throw new Error("progress failed");
        const result = await response.json();
        status.textContent = formatProgress(result);
        if (result.running) {{
          setTimeout(pollRefresh, 1500);
          return;
        }}
        if (result.done) {{
          window.location.reload();
          return;
        }}
        refresh.disabled = false;
      }} catch (error) {{
        status.textContent = "Refresh status unavailable.";
        refresh.disabled = false;
      }}
    }}
    function formatProgress(result) {{
      const message = result.message || "Refreshing jobs...";
      if (Number.isFinite(result.completed) && Number.isFinite(result.total) && result.total > 0) {{
        const eta = Number.isFinite(result.eta_seconds)
          ? ` ETA ~${{formatEta(result.eta_seconds)}}.`
          : "";
        return `${{message}} (${{result.completed}}/${{result.total}})${{eta}}`;
      }}
      return message;
    }}
    function formatEta(seconds) {{
      const value = Math.max(0, Math.round(seconds));
      if (value < 60) return `${{value}}s`;
      return `${{Math.ceil(value / 60)}}m`;
    }}
    renderPage();
  </script>
</body>
</html>
"""


def write_dashboard(
    jobs: list[JobPosting],
    *,
    output_path: Path,
    today: date | None = None,
    days: int = 14,
    last_refresh_at: str | None = None,
    refresh_runs: list[Mapping[str, Any]] | None = None,
) -> Path:
    """Write the local dashboard HTML."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_dashboard(
            jobs,
            today=today,
            days=days,
            last_refresh_at=last_refresh_at,
            refresh_runs=refresh_runs,
        ),
        encoding="utf-8",
    )
    return output_path


def _render_row(job: DashboardJob) -> str:
    company = escape(job.company)
    title = escape(job.title)
    location = escape(job.location)
    role = escape(job.role)
    source = escape(job.source)
    url = escape(job.url, quote=True)
    return (
        "<tr>"
        f"<td>{company}</td>"
        f'<td><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></td>'
        f"<td>{location}</td>"
        f"<td>{role}</td>"
        f"<td>{source}</td>"
        "</tr>"
    )


def _render_refresh_run(row: Mapping[str, Any]) -> str:
    source_slug = _row_value(row, "source_slug")
    source = str(_row_value(row, "source_type") or "")
    if source_slug:
        source = f"{source}:{source_slug}"
    status = escape(str(_row_value(row, "status") or "unknown"))
    seen = escape(str(_row_value(row, "jobs_seen") or 0))
    inserted = escape(str(_row_value(row, "jobs_inserted") or 0))
    finished = _format_refresh_time(
        _row_value(row, "finished_at") or _row_value(row, "started_at")
    )
    error = escape(str(_row_value(row, "error") or ""))
    return (
        "<tr>"
        f"<td>{escape(source)}</td>"
        f"<td>{status}</td>"
        f"<td>{seen}</td>"
        f"<td>{inserted}</td>"
        f"<td>{escape(finished)}</td>"
        f'<td class="error-text">{error}</td>'
        "</tr>"
    )


def _render_refresh_warning(refresh_runs: list[Mapping[str, Any]]) -> str:
    web_discovery_run = next(
        (
            row
            for row in refresh_runs
            if _row_value(row, "source_type") == "web_search_discovery"
        ),
        None,
    )
    if not web_discovery_run or _row_value(web_discovery_run, "status") != "failed":
        return ""
    error = str(_row_value(web_discovery_run, "error") or "web discovery failed")
    return (
        '<div class="warning">'
        "Tavily/web discovery failed for this refresh, so latest newly discovered "
        "company boards may be missing. Other sources still refreshed. "
        f"Next refresh will try discovery again. <span>{escape(error)}</span>"
        "</div>"
    )


def _row_value(row: Mapping[str, Any], key: str) -> Any:
    if hasattr(row, "keys") and key in row.keys():
        return row[key]
    return row.get(key)


def _render_empty_refresh_run() -> str:
    return (
        "<tr>"
        '<td colspan="6">No refresh runs yet.</td>'
        "</tr>"
    )


def _interleave_location_buckets(jobs: list[DashboardJob]) -> list[DashboardJob]:
    """Keep high-ranked jobs while avoiding one metro dominating the first pages."""
    buckets: dict[str, list[DashboardJob]] = {}
    bucket_order: list[str] = []
    for job in jobs:
        bucket = _location_bucket(job.location)
        if bucket not in buckets:
            buckets[bucket] = []
            bucket_order.append(bucket)
        buckets[bucket].append(job)

    interleaved: list[DashboardJob] = []
    while any(buckets.values()):
        for bucket in list(bucket_order):
            if buckets[bucket]:
                interleaved.append(buckets[bucket].pop(0))
    return interleaved


def _location_bucket(location: str) -> str:
    value = location.lower()
    bucket_keywords = (
        ("seattle", ("seattle", "seatle")),
        ("boston", ("boston", "cambridge")),
        ("austin", ("austin",)),
        ("denver", ("denver",)),
        ("los-angeles", ("los angeles",)),
        ("dc", ("washington", "d.c.", "dc")),
        ("chicago", ("chicago",)),
        ("atlanta", ("atlanta",)),
        ("portland", ("portland",)),
        ("raleigh-durham", ("raleigh", "durham", "chapel hill")),
        ("sf-bay", ("san francisco", "sf", "bay area", "foster city", "sunnyvale")),
        ("nyc", ("new york", "nyc")),
        ("remote-us", ("united states", "usa", "remote us", "remote (united states)")),
    )
    for bucket, keywords in bucket_keywords:
        if any(keyword in value for keyword in keywords):
            return bucket
    if value == "remote":
        return "remote"
    return "other-us"


def _window_date(job: JobPosting) -> date:
    return _seen_date(job)


def _seen_date(job: JobPosting) -> date:
    if job.first_seen_at is not None:
        return job.first_seen_at.date()
    return datetime.now(UTC).date()


def _date_to_ordinal(value: date) -> int:
    return value.toordinal()


def _refresh_metadata(last_refresh_at: str | None) -> dict[str, object]:
    if last_refresh_at is None:
        return {"disabled": False, "status": "Never refreshed"}
    parsed = _parse_datetime(last_refresh_at)
    if parsed is None:
        return {"disabled": False, "status": "Last refresh unknown"}
    return {
        "disabled": False,
        "status": f"Last refresh {parsed.strftime('%Y-%m-%d %H:%M UTC')}",
    }


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _format_refresh_time(value: object) -> str:
    if not value:
        return "n/a"
    parsed = _parse_datetime(str(value))
    if parsed is None:
        return str(value)
    return parsed.strftime("%Y-%m-%d %H:%M UTC")
