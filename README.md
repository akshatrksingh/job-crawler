# job-crawler

Personal job crawling pipeline for finding ML engineer, AI engineer, and agentic AI roles in SF, NYC, and remote.

The pipeline will:

- Discover companies dynamically from search results instead of using a hardcoded company list.
- Crawl Greenhouse, Lever, Ashby, Google Jobs, Hacker News Who is Hiring, and YC Work at a Startup.
- Store jobs and crawl metadata in SQLite.
- Deduplicate jobs so previously seen roles are not shown again.
- Score new jobs against a resume with GPT-4o-mini.
- Produce a daily Markdown digest with jobs scoring 7 or above.

No auto-apply behavior belongs in this project.

## Project Layout

```text
src/job_crawler/
  config/       Runtime settings and search targets
  crawlers/     Source-specific crawlers
  discovery/    Dynamic company/source discovery
  digest/       Markdown daily digest generation
  scoring/      Resume/job scoring
  storage/      SQLite schema, migrations, and repositories
scripts/        Local operational scripts
tests/          Unit and integration tests
data/           Local SQLite DB and crawl artifacts, ignored by git
digests/        Generated daily Markdown digests, ignored by git
docs/           Design notes and decisions
```

## Status

Initial scaffold only. Implementation will be added source by source.
