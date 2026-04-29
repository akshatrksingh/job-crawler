# job-crawler

Personal job crawling pipeline for finding ML engineer, AI engineer, agentic AI, SWE, and SDE roles across major US tech hubs and remote.

The pipeline will:

- Discover companies dynamically from search results instead of using a hardcoded company list.
- Crawl Greenhouse, Lever, Ashby, Hacker News Who is Hiring, and YC Work at a Startup.
- Store jobs and crawl metadata in SQLite.
- Deduplicate jobs so previously seen roles are not shown again.
- Filter and rank jobs with zero-cost heuristics.
- Produce a daily Markdown digest with a simple list of the best jobs.
- Generate a private dashboard page showing recent fetched jobs and refresh errors.
- Run locally or in Docker with SQLite on a persistent volume.

Optional future semantic filtering can use Groq. Put a Groq key in `.env` as
`GROQ_API_KEY=...` only after the feature is implemented and explicitly enabled.

Optional live web discovery can use Tavily. Put a Tavily key in `.env` as
`TAVILY_API_KEY=...` to let refresh search for new Ashby, Greenhouse, and Lever
company boards before crawling. Discovery runs about 100 bounded searches across
AI, ML, SWE, data, founding/backend/full-stack role groups, early-career wording,
and major US cities. The query budget backs off by 10 after discovery failures
or empty runs, down to a floor of 10. Without that key, refresh stays zero-cost
and uses the built-in job boards, HN, YC, stored ATS boards, and a DuckDuckGo
HTML fallback.

No auto-apply behavior belongs in this project.

## Project Layout

```text
src/job_crawler/
  config/       Runtime settings and search targets
  crawlers/     Source-specific crawlers
  discovery/    Dynamic company/source discovery
  digest/       Markdown daily digest generation
  dashboard/    Local private HTML dashboard generation
  ranking/      Zero-cost job filtering and ranking
  storage/      SQLite schema, migrations, and repositories
scripts/        Local operational scripts
tests/          Unit and integration tests
data/           Local SQLite DB and crawl artifacts, ignored by git
digests/        Generated daily Markdown digests, ignored by git
docs/           Design notes and decisions
```

## Local Dashboard

```bash
PYTHONPATH=src uv run python -m job_crawler.cli serve --port 8782
```

Open `http://127.0.0.1:8782/` and click Refresh.

## Deployment

See `docs/deployment.md`. Deployed instances should set:

```text
JOB_CRAWLER_DB_PATH=/var/data/job_crawler.sqlite
JOB_CRAWLER_AUTH_USERNAME=<your username>
JOB_CRAWLER_AUTH_PASSWORD=<strong password>
```

SQLite must be on persistent disk if you want history to survive deploys.
