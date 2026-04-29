# Development Stages

This file tracks the incremental build plan. Each stage should end with a small
test and a user-run commit/push.

## Stage 0: Project Scaffold

Status: Done.

Built:

- Python package skeleton.
- Local data and digest directories.
- Basic README, `.env.example`, and `pyproject.toml`.
- Private GitHub repo setup.

Test before push:

```bash
git status
```

Suggested commit:

```bash
git add .
git commit -m "chore: create initial project scaffold"
git push
```

## Stage 1: Operating Docs

Status: Done.

Goal:

- Make project decisions, strict instructions, and stage flow explicit.
- Remove Indeed from scope.
- Record rate-limit, cost-control, and simple-digest requirements.

Test before push:

```bash
git diff -- README.md pyproject.toml docs/decisions.md docs/instructions.md docs/development-stages.md
```

Suggested commit:

```bash
git add README.md pyproject.toml docs/decisions.md docs/instructions.md docs/development-stages.md
git commit -m "docs: define crawler development workflow"
git push
```

## Stage 2: SQLite Schema and Dedupe

Status: Done.

Goal:

- Add SQLite schema creation.
- Add job, source, crawl run, and score tables.
- Add idempotent insert/dedupe behavior.

End-to-end test:

- Insert fixture jobs from two fake sources.
- Confirm duplicate inserts do not create duplicate job rows.
- Confirm new jobs can be selected for scoring.
- Confirm crawl state can record timestamps for rate-limit-friendly reruns.

Push after:

- Unit tests pass for schema and dedupe.
- A local smoke script creates a SQLite DB in `data/`.

Suggested commit:

```bash
git add src/job_crawler/storage tests
git commit -m "feat(storage): add sqlite schema and dedupe"
git push
```

## Stage 3: Career Page API Crawlers

Status: Done.

Goal:

- Implement Ashby, Greenhouse, and Lever API crawlers.
- Normalize jobs into the shared `JobPosting` shape.
- Add a bounded manual smoke script for one approved source/company at a time.

End-to-end test:

- Use fixture API responses for parser tests.
- Optionally run one live smoke crawl for a user-approved sample company/source.
- Store results in SQLite without duplicates.

Push after:

- Parser tests pass.
- Offline parser tests pass.
- Optional live smoke output looks reasonable.

Suggested commit:

```bash
git add src/job_crawler/crawlers scripts/smoke_ats.py tests docs/development-stages.md
git commit -m "feat(crawlers): add startup ats crawlers"
git push
```

## Stage 4: Dynamic Company Discovery

Status: Done for provider-neutral extraction. Live search provider decision is
pending.

Goal:

- Discover Ashby, Greenhouse, and Lever slugs from search queries.
- Store discovered slugs and provenance.
- Generate bounded Google-style search queries.
- Extract ATS slugs from pasted/search-result URLs without live scraping.

End-to-end test:

- Generate a limited query set.
- Confirm slugs are extracted, deduped, and tied back to their source query.
- Run a no-network smoke test with representative URLs.

Push after:

- URL extraction tests pass.
- No-network discovery smoke run succeeds.
- Live search provider is chosen separately with user approval.

Suggested commit:

```bash
git add src/job_crawler/discovery src/job_crawler/storage/repository.py scripts/smoke_discovery_from_urls.py tests/discovery pyproject.toml docs/development-stages.md docs/decisions.md
git commit -m "feat(discovery): add dynamic ats source discovery"
git push
```

## Stage 5: HN and YC Sources

Status: Done.

Goal:

- Crawl Hacker News Who is Hiring through Algolia.
- Parse YC Work at a Startup public job listings cautiously from visible HTML.
- Add bounded optional smoke scripts.

End-to-end test:

- Fetch current/recent HN thread metadata.
- Extract job-like posts into normalized records.
- Parse YC roles into normalized records from fixture HTML.

Push after:

- Fixture tests pass.
- Optional live smoke run stores new jobs without duplicates.

Suggested commit:

```bash
git add src/job_crawler/crawlers scripts/smoke_hn.py scripts/smoke_yc.py tests/crawlers docs/development-stages.md docs/decisions.md
git commit -m "feat(crawlers): add hn and yc sources"
git push
```

## Stage 6: Google Jobs via JobSpy

Status: Done.

Goal:

- Add Google Jobs search through `python-jobspy`.
- Keep Indeed disabled/out of scope.
- Keep live searches manual, tiny, and disabled unless the user runs the smoke
  command.

End-to-end test:

- Run a small Google Jobs search for one target role/location.
- Normalize and dedupe results into SQLite.
- Offline adapter tests use fixture records only.

Push after:

- Adapter tests pass.
- Optional smoke run returns plausible Google Jobs records.

Suggested commit:

```bash
git add src/job_crawler/crawlers scripts/smoke_google_jobs.py tests/crawlers docs/development-stages.md
git commit -m "feat(crawlers): add google jobs adapter"
git push
```

## Stage 7: Resume Scoring

Status: Planned.

Goal:

- Load resume from `JOB_CRAWLER_RESUME_PATH`.
- Score unscored jobs with GPT-4o-mini.
- Store score, reason, model, and timestamp.

End-to-end test:

- Use a fake scorer in tests.
- Run one user-approved live scoring smoke test with a small job batch.

Push after:

- Prompt construction and response parsing tests pass.
- Live smoke scoring succeeds.

Suggested commit:

```bash
git add src/job_crawler/scoring tests .env.example
git commit -m "feat(scoring): score jobs against resume"
git push
```

## Stage 8: Daily Digest

Status: Planned.

Goal:

- Generate `digests/YYYY-MM-DD.md`.
- Include a simple list of company, job title, link, and location.
- Use adaptive selection/top-N rather than a fixed score-only cutoff.

End-to-end test:

- Seed scored fixture jobs.
- Generate a digest.
- Confirm strongest fixture jobs are present.
- Confirm digest output does not include match summaries by default.

Push after:

- Digest tests pass.
- Local generated digest looks clean.

Suggested commit:

```bash
git add src/job_crawler/digest tests
git commit -m "feat(digest): generate daily markdown digest"
git push
```

## Stage 9: Daily Runner

Status: Planned.

Goal:

- Add a single command that runs discovery, crawling, scoring, and digest
  generation.
- Add clear docs for local scheduling.

End-to-end test:

- Run a small dry-run mode.
- Run the full pipeline with low limits.
- Confirm rerun remains idempotent.

Push after:

- CLI tests pass.
- Dry run and limited live run succeed.

Suggested commit:

```bash
git add src/job_crawler scripts README.md tests
git commit -m "feat(cli): add daily crawler runner"
git push
```

## Stage 10: Scheduling

Status: Planned.

Goal:

- Add user-approved scheduling, likely local `launchd` on macOS or GitHub
  Actions if secrets/storage decisions make sense.

Decision needed:

- Where should daily execution live: local laptop, server, or GitHub Actions?

Push after:

- The chosen schedule can run the command and place the digest where expected.

Suggested commit:

```bash
git add scripts docs README.md
git commit -m "docs(ops): document daily scheduling"
git push
```
