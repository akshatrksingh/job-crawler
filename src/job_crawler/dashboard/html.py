"""Static HTML dashboard for locally fetched jobs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from html import escape
from pathlib import Path

from job_crawler.crawlers.base import JobPosting
from job_crawler.ranking import rank_job


@dataclass(frozen=True)
class DashboardJob:
    """A job prepared for the dashboard."""

    company: str
    title: str
    url: str
    location: str
    source: str
    visible_date: date
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
        ranked = rank_job(job)
        if ranked.excluded:
            continue
        visible_date = _visible_date(job)
        if visible_date < cutoff:
            continue
        selected.append(
            DashboardJob(
                company=job.company,
                title=job.title,
                url=job.url,
                location=job.location or "Unknown",
                source=job.source,
                visible_date=visible_date,
                rank_score=ranked.score,
            )
        )
    return sorted(
        selected,
        key=lambda job: (
            -_date_to_ordinal(job.visible_date),
            -job.rank_score,
            job.company.lower(),
            job.title.lower(),
        ),
    )


def render_dashboard(
    jobs: list[JobPosting],
    *,
    today: date | None = None,
    days: int = 14,
) -> str:
    """Render a standalone local HTML dashboard."""
    selected = select_dashboard_jobs(jobs, today=today, days=days)
    rows = "\n".join(_render_row(job) for job in selected)
    cities = sorted({job.location for job in selected})
    sources = sorted({job.source for job in selected})
    city_options = "\n".join(
        f'<option value="{escape(city)}">{escape(city)}</option>' for city in cities
    )
    source_options = "\n".join(
        f'<option value="{escape(source)}">{escape(source)}</option>' for source in sources
    )
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Job Crawler</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f7f8fa;
      --panel: #ffffff;
      --text: #172026;
      --muted: #5f6b76;
      --line: #d9dee5;
      --accent: #0f766e;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    main {{
      max-width: 1180px;
      margin: 0 auto;
      padding: 28px 20px 48px;
    }}
    header {{
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: end;
      margin-bottom: 18px;
    }}
    h1 {{
      margin: 0 0 4px;
      font-size: 28px;
      font-weight: 700;
      letter-spacing: 0;
    }}
    .meta {{
      color: var(--muted);
      font-size: 14px;
    }}
    .actions {{
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: end;
      flex-wrap: wrap;
    }}
    button {{
      min-height: 40px;
      border: 1px solid #0f766e;
      border-radius: 6px;
      padding: 0 12px;
      background: #0f766e;
      color: #ffffff;
      font-size: 14px;
      font-weight: 650;
      cursor: pointer;
    }}
    button:disabled {{
      cursor: wait;
      opacity: 0.72;
    }}
    .filters {{
      display: grid;
      grid-template-columns: minmax(180px, 1fr) minmax(160px, 220px) minmax(140px, 180px);
      gap: 10px;
      margin: 18px 0;
    }}
    input, select {{
      min-height: 40px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 0 10px;
      background: var(--panel);
      color: var(--text);
      font-size: 14px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
    }}
    th, td {{
      padding: 12px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      font-size: 14px;
    }}
    th {{
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0;
      background: #fbfcfd;
    }}
    a {{
      color: var(--accent);
      font-weight: 600;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .empty {{
      display: none;
      padding: 18px;
      background: var(--panel);
      border: 1px solid var(--line);
      color: var(--muted);
    }}
    @media (max-width: 760px) {{
      header, .filters {{
        display: block;
      }}
      input, select {{
        width: 100%;
        box-sizing: border-box;
        margin-bottom: 10px;
      }}
      th:nth-child(5), td:nth-child(5) {{
        display: none;
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
        <div id="status" class="meta">Updated {generated_at}</div>
      </div>
    </header>

    <section class="filters" aria-label="Filters">
      <input id="search" type="search" placeholder="Search company or title">
      <select id="city">
        <option value="">All locations</option>
        {city_options}
      </select>
      <select id="source">
        <option value="">All sources</option>
        {source_options}
      </select>
    </section>

    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Company</th>
          <th>Job</th>
          <th>Location</th>
          <th>Source</th>
        </tr>
      </thead>
      <tbody id="jobs">
        {rows}
      </tbody>
    </table>
    <div id="empty" class="empty">No jobs match the current filters.</div>
  </main>
  <script>
    const search = document.getElementById("search");
    const city = document.getElementById("city");
    const source = document.getElementById("source");
    const rows = Array.from(document.querySelectorAll("#jobs tr"));
    const empty = document.getElementById("empty");
    const refresh = document.getElementById("refresh");
    const status = document.getElementById("status");

    function applyFilters() {{
      const q = search.value.trim().toLowerCase();
      const location = city.value;
      const sourceValue = source.value;
      let shown = 0;
      for (const row of rows) {{
        const text = row.dataset.search;
        const matchesSearch = !q || text.includes(q);
        const matchesCity = !location || row.dataset.location === location;
        const matchesSource = !sourceValue || row.dataset.source === sourceValue;
        const visible = matchesSearch && matchesCity && matchesSource;
        row.style.display = visible ? "" : "none";
        shown += visible ? 1 : 0;
      }}
      empty.style.display = shown === 0 ? "block" : "none";
    }}

    search.addEventListener("input", applyFilters);
    city.addEventListener("change", applyFilters);
    source.addEventListener("change", applyFilters);
    refresh.addEventListener("click", async () => {{
      refresh.disabled = true;
      status.textContent = "Refreshing...";
      try {{
        const response = await fetch("/api/refresh", {{ method: "POST" }});
        if (!response.ok) throw new Error("refresh failed");
        window.location.reload();
      }} catch (error) {{
        status.textContent = "Refresh requires the local server.";
        refresh.disabled = false;
      }}
    }});
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
) -> Path:
    """Write the local dashboard HTML."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_dashboard(jobs, today=today, days=days), encoding="utf-8")
    return output_path


def _render_row(job: DashboardJob) -> str:
    company = escape(job.company)
    title = escape(job.title)
    location = escape(job.location)
    source = escape(job.source)
    url = escape(job.url, quote=True)
    search = escape(f"{job.company} {job.title} {job.location} {job.source}".lower(), quote=True)
    return (
        f'<tr data-search="{search}" data-location="{location}" data-source="{source}">'
        f"<td>{job.visible_date.isoformat()}</td>"
        f"<td>{company}</td>"
        f'<td><a href="{url}" target="_blank" rel="noopener noreferrer">{title}</a></td>'
        f"<td>{location}</td>"
        f"<td>{source}</td>"
        "</tr>"
    )


def _visible_date(job: JobPosting) -> date:
    if job.posted_at is not None:
        return job.posted_at.date()
    return datetime.now(UTC).date()


def _date_to_ordinal(value: date) -> int:
    return value.toordinal()
