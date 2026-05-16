# job-crawler

Personal job crawling pipeline for finding ML engineer, AI engineer, agentic AI, SWE, and SDE roles across major US tech hubs and remote.

The pipeline will:

- Discover companies dynamically from search results instead of using a hardcoded company list.
- Crawl Greenhouse, Lever, Ashby, curated job boards, and YC Work at a Startup.
- Store jobs and crawl metadata in SQLite.
- Deduplicate jobs so previously seen roles are not shown again.
- Filter and rank jobs with zero-cost heuristics.
- Generate a private dashboard page showing recent fetched jobs and refresh errors.
- Run as a laptop-hosted personal app with local SQLite.
- Crawl stored ATS company boards with adaptive SQLite scheduling so quiet
  companies are revisited less often and useful companies are revisited sooner.
- Refresh ATS company boards in bounded parallel workers and show progress/ETA
  while the refresh is running.
- Let you stage job deletions in the dashboard, confirm the count, then remove
  those jobs from the active dashboard while keeping dismissal markers so they
  do not reappear on the next refresh.

Optional live web discovery can use Tavily. Put a Tavily key in `.env` as
`TAVILY_API_KEY=...`, then enable the Tavily search toggle in the dashboard before
refreshing to search for new Ashby, Greenhouse, and Lever company boards before
crawling. Discovery runs about 150 bounded searches, weighted toward Ashby and
covering AI engineer, applied AI, ML, AI platform/infrastructure, founding, SWE,
and member-of-technical-staff role groups across major US cities. The query
budget backs off by 10 after discovery failures or empty runs, down to a floor
of 10. Without the toggle, refresh stays zero-cost and uses the built-in job
boards, YC, stored ATS boards, and a DuckDuckGo HTML fallback.

Refresh also keeps a curated AI startup seed list for Ashby and Greenhouse boards.
This is only a head start for startup-heavy discovery; the adaptive scheduler
backs off quiet or broken company boards, and dynamic discovery can still add
new Ashby, Greenhouse, and Lever sources over time.

No auto-apply behavior belongs in this project.

## Project Layout

```text
src/job_crawler/
  crawlers/     Source-specific crawlers
  discovery/    Dynamic company/source discovery
  dashboard/    Local private HTML dashboard generation
  pipeline/     Refresh orchestration
  ranking/      Zero-cost job filtering and ranking
  storage/      SQLite schema, migrations, and repositories
scripts/        Local operational scripts
tests/          Unit and integration tests
data/           Local SQLite DB and crawl artifacts, ignored by git
site/           Generated local dashboard HTML, ignored by git
docs/           Design notes and decisions
```

## Local Dashboard

```bash
PYTHONPATH=src uv run python -m job_crawler.cli serve --port 8782
```

Open `http://127.0.0.1:8782/` and click Refresh.

Useful knobs:

```bash
PYTHONPATH=src uv run python -m job_crawler.cli serve \
  --port 8782 \
  --ats-workers 8 \
  --source-timeout-seconds 75
```

## Deployment

See `docs/deployment.md`.

The maintained target is **laptop-hosted**: run the dashboard on your machine,
keep SQLite in `data/`, and optionally access it from your other devices through
Tailscale. This is the strict `$0` path. Cloud deployment is optional/demo only
unless you accept paying for durable storage.

Internet-reachable instances, including temporary tunnels, should set:

```text
JOB_CRAWLER_AUTH_USERNAME=<your username>
JOB_CRAWLER_AUTH_PASSWORD=<strong password>
TAVILY_API_KEY=<optional Tavily key>
```

SQLite must be on persistent disk if you want history to survive deploys.
