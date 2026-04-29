# job-crawler

Personal job crawling pipeline for finding ML engineer, AI engineer, agentic AI, SWE, and SDE roles across major US tech hubs and remote.

The pipeline will:

- Discover companies dynamically from search results instead of using a hardcoded company list.
- Crawl Greenhouse, Lever, Ashby, Google Jobs, Hacker News Who is Hiring, and YC Work at a Startup.
- Store jobs and crawl metadata in SQLite.
- Deduplicate jobs so previously seen roles are not shown again.
- Filter and rank jobs with zero-cost heuristics.
- Produce a daily Markdown digest with a simple list of the best jobs.
- Generate a local private dashboard page showing recent fetched jobs.

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

## Status

Initial scaffold only. Implementation will be added source by source.
