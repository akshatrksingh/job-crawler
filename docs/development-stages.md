# Development Stages

This file tracks the incremental build plan. Each stage should end with a small
test and a user-run commit/push.

## Stage 0: Project Scaffold

Status: Done.

Built:

- Python package skeleton.
- Local data and dashboard output directories.
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
- Record rate-limit, cost-control, and simple-dashboard requirements.

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
- Confirm new jobs can be selected for downstream ranking/dashboard generation.
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
available when `TAVILY_API_KEY` is configured and enabled from the dashboard.

Goal:

- Discover Ashby, Greenhouse, and Lever slugs from search queries.
- Store discovered slugs and provenance.
- Generate bounded ATS search queries across target role families.
- Extract ATS slugs from live search results or pasted/search-result URLs.
- Prefer optional Tavily live search over direct Google scraping.
- Keep a zero-cost fallback through DuckDuckGo HTML and job-board-derived ATS
  links.
- Keep a curated AI startup seed list as a fallback/head-start layer for
  Ashby- and Greenhouse-heavy startup discovery across SF, NYC, Boston, and
  other major US hubs.
- Keep Tavily discovery around 100 targeted searches by default.
- Back off the web-discovery query budget by 10 after failures or empty runs,
  down to a floor of 10, and recover by 10 after successful discovery.
- Keep individual ATS company-board crawls capped at 10 jobs by default.

End-to-end test:

- Generate a limited query set.
- Confirm slugs are extracted, deduped, and tied back to their source query.
- Confirm curated startup seed sources are upserted before due ATS boards are
  crawled.
- Run a no-network smoke test with representative URLs.
- With `TAVILY_API_KEY` set and the dashboard toggle enabled, run one bounded
  refresh and confirm new discovered Ashby, Greenhouse, or Lever sources are
  stored before ATS crawling.

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

## Stage 8: Markdown Digest

Status: Removed from maintained scope.

Goal:

- This stage was replaced by the local dashboard. Do not build or maintain the
  Markdown digest path unless the user explicitly asks for exports later.

End-to-end test:

- None for the removed path. Dashboard tests cover the current output surface.

Push after:

- No push for this removed stage.

Suggested commit:

```bash
# No commit. This stage is intentionally removed.
```

## Stage 9: Local Dashboard

Status: Done.

Goal:

- Generate `site/index.html` from SQLite.
- Show jobs from the last 14 days.
- Keep older jobs stored but hidden from the dashboard view.
- Keep the page as a ready-made list without manual search/source/role filters.
- Avoid a hard display limit.
- Keep the dashboard local/private by default.

End-to-end test:

- Seed fixture jobs inside and outside the 14-day window.
- Confirm old jobs are hidden from the generated page.
- Confirm senior roles are excluded.
- Confirm the generated HTML has no manual discovery/filter controls.
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

## Stage 10: Refresh Runner

Status: Done.

Goal:

- Keep the server refresh button as the primary runner.
- Make refresh status clear when Tavily/web discovery fails or hits limits.
- Keep Tavily behind a frontend toggle so a configured key is not used by
  default.
- Run due ATS company-board crawls in bounded parallel workers.
- Adapt each stored ATS source's next crawl time from recent usefulness.
- Clean up stale running crawl rows left behind by interrupted refreshes.
- Show refresh progress and an ETA while the browser waits.
- Keep Tavily discovery reliable by loading `.env` in the discovery layer.
- Support staged multi-delete from the dashboard with confirmation before active
  job rows are removed and dismissal markers are saved.
- Avoid automatic scheduling unless the user explicitly asks for it.

End-to-end test:

- Run the full pipeline with low limits.
- Confirm rerun remains idempotent and dashboard refresh errors are visible.
- Confirm quiet sources are skipped until their next due time.
- Confirm timed-out/stale source runs are marked failed.
- Confirm the dashboard polls refresh progress.
- Confirm local `.env` Tavily keys are picked up by discovery.
- Confirm Tavily is used only when the dashboard refresh payload enables it.
- Confirm selected dashboard jobs are visually marked before deletion, only
  deleted after confirmation, and treated as already seen on later refreshes.
- Confirm the page-wise delete control stages the visible page using the same
  saved deletion flow.

Push after:

- CLI tests pass.
- All 91 tests pass.

Suggested commit:

```bash
git add src/job_crawler scripts README.md tests docs
git commit -m "feat(pipeline): refine dashboard refresh runner"
git push
```

## Stage 11: Scheduling

Status: Deferred.

Goal:

- Do not add scheduling by default. Manual refresh keeps compute and API usage
  deliberate for the current personal `$0` setup.

Decision needed:

- Only revisit if the user asks for automatic refresh.

Push after:

- No push until scheduling is explicitly requested.

Suggested commit:

```bash
# No commit. Scheduling is intentionally deferred.
```
