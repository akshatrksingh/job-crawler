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
- Add job, source, crawl run, and score/rank-support tables.
- Add idempotent insert/dedupe behavior.

End-to-end test:

- Insert fixture jobs from two fake sources.
- Confirm duplicate inserts do not create duplicate job rows.
- Confirm new jobs can be selected for downstream ranking/digest generation.
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

Status: Done for provider-neutral extraction. Optional Tavily live search is
available when `TAVILY_API_KEY` is configured.

Goal:

- Discover Ashby, Greenhouse, and Lever slugs from search queries.
- Store discovered slugs and provenance.
- Generate bounded ATS search queries across target role families.
- Extract ATS slugs from live search results or pasted/search-result URLs.
- Prefer optional Tavily live search over direct Google scraping.
- Keep a zero-cost fallback through DuckDuckGo HTML and job-board-derived ATS
  links.
- Keep Tavily discovery around 100 targeted searches by default.
- Back off the web-discovery query budget by 10 after failures or empty runs,
  down to a floor of 10, and recover by 10 after successful discovery.
- Keep individual ATS company-board crawls capped at 10 jobs by default.

End-to-end test:

- Generate a limited query set.
- Confirm slugs are extracted, deduped, and tied back to their source query.
- Run a no-network smoke test with representative URLs.
- With `TAVILY_API_KEY` set, run one bounded refresh and confirm new discovered
  Ashby, Greenhouse, or Lever sources are stored before ATS crawling.

Push after:

- URL extraction and Tavily parser tests pass.
- No-network discovery smoke run succeeds.
- A bounded refresh does not show Google 429 errors.
- Refresh status shows source discovery before per-company ATS crawls.

Suggested commit:

```bash
git add src/job_crawler/discovery src/job_crawler/storage/repository.py scripts/smoke_discovery_from_urls.py tests/discovery pyproject.toml docs/development-stages.md docs/decisions.md
git commit -m "feat(discovery): add dynamic ats source discovery"
git push
```

## Stage 5: YC Source

Status: Done. HN was later removed from active scope.

Goal:

- Parse YC Work at a Startup public job listings cautiously from visible HTML.
- Add bounded optional smoke scripts.

End-to-end test:

- Parse YC roles into normalized records from fixture HTML.

Push after:

- Fixture tests pass.
- Optional live smoke run stores new jobs without duplicates.

Suggested commit:

```bash
git add src/job_crawler/crawlers scripts/smoke_yc.py tests/crawlers docs/development-stages.md docs/decisions.md
git commit -m "feat(crawlers): add yc source"
git push
```

## Stage 6: Google Jobs via JobSpy

Status: Removed.

Goal:

- This stage was implemented, then removed after live refreshes repeatedly hit
  Google 429 / sorry pages.
- Indeed remains disabled/out of scope.

End-to-end test:

- No active tests. Historical adapter code was removed.

Push after:

- Removal tests pass.

Suggested commit:

```bash
git add pyproject.toml src/job_crawler tests docs/development-stages.md docs/decisions.md
git commit -m "refactor(crawlers): remove google jobs source"
git push
```

## Stage 7: Zero-Cost Ranking

Status: Done.

Goal:

- Rank jobs without paid APIs or LLM calls.
- Prioritize NYC/SF first, then other major US cities and Remote US.
- Exclude or strongly penalize senior/staff/lead-style roles.

End-to-end test:

- Use fixture jobs covering primary cities, other major cities, Remote US, and
  senior-role exclusion.

Push after:

- Ranking heuristic tests pass.
- Full test suite passes.

Suggested commit:

```bash
git add README.md .env.example pyproject.toml docs src/job_crawler/ranking tests/ranking
git commit -m "feat(ranking): add zero-cost job ranking"
git push
```

## Stage 8: Daily Digest

Status: Done.

Goal:

- Generate `digests/YYYY-MM-DD.md`.
- Include a simple list of company, job title, link, and location.
- Use zero-cost ranking/top-N rather than a fixed score-only cutoff.

End-to-end test:

- Seed ranked fixture jobs.
- Generate a digest.
- Confirm strongest fixture jobs are present.
- Confirm digest output does not include match summaries by default.
- Confirm the SQLite repository can provide jobs for digest generation.

Push after:

- Digest tests pass.
- Local generated digest looks clean.

Suggested commit:

```bash
git add src/job_crawler/digest src/job_crawler/storage/repository.py scripts/generate_digest.py tests/digest docs/development-stages.md
git commit -m "feat(digest): generate daily markdown digest"
git push
```

## Stage 9: Local Dashboard

Status: Done.

Goal:

- Generate `site/index.html` from SQLite.
- Show jobs from the last 14 days.
- Keep older jobs stored but hidden from the dashboard view.
- Provide search, location, and source filters.
- Avoid a hard display limit.
- Keep the dashboard local/private by default.

End-to-end test:

- Seed fixture jobs inside and outside the 14-day window.
- Confirm old jobs are hidden from the generated page.
- Confirm senior roles are excluded.
- Confirm filters exist in the generated HTML.
- Generate the dashboard from the local SQLite DB.

Push after:

- Dashboard tests pass.
- Local `site/index.html` generates successfully.

Suggested commit:

```bash
git add .gitignore README.md docs/decisions.md docs/development-stages.md site/.gitkeep src/job_crawler/dashboard scripts/generate_dashboard.py tests/dashboard
git commit -m "feat(dashboard): generate local jobs page"
git push
```

## Stage 10: Daily Runner

Status: Planned.

Goal:

- Add a single command that runs discovery, crawling, ranking, and digest
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

## Stage 11: Scheduling

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
