# Decisions

This document is the project's decision log. It records durable product,
architecture, and workflow choices so the crawler does not drift silently as it
grows.

## Product Scope

- The project is a personal job discovery pipeline.
- The project must not auto-apply to jobs.
- The project should find jobs, score them against the user's resume, and create
  a daily Markdown digest.
- The digest should prioritize the best jobs from each run rather than rely on a
  hard score cutoff. A threshold can be used as a starting heuristic, but it
  should adapt if the market is sparse or unusually strong.
- The target roles are ML engineer, AI engineer, agentic AI engineer, applied AI
  roles, SWE roles, SDE roles, and closely related engineering roles.
- The target seniority is new grad, entry level, junior, or roles expecting up to
  roughly 2-3 years of experience. This is a soft boundary, but senior, staff,
  principal, lead, manager, and architect roles should usually be avoided.
- The target locations prioritize San Francisco, New York City, and remote, but
  the crawler should also consider other large US cities and nearby metro areas
  when the role fit is strong.
- Any company type is acceptable. Startups, mid-size companies, larger companies,
  labs, and non-FAANG companies are all in scope.
- Indeed is intentionally out of scope.

## Sources

Planned crawl sources:

- Greenhouse startup career pages.
- Lever startup career pages.
- Ashby startup career pages.
- Google Jobs through `python-jobspy`.
- Hacker News "Who is Hiring" monthly thread through the Algolia API.
- YC Work at a Startup board.

Discovery requirements:

- Do not maintain a hardcoded company list as the main crawl input.
- Discover company career-page slugs dynamically from search queries such as
  `site:jobs.ashbyhq.com machine learning engineer San Francisco`.
- Store discovered source slugs in SQLite with enough metadata to audit where
  they came from.

## Storage

- SQLite is the source of truth.
- Store raw crawl metadata where useful for debugging, but normalize job records
  into stable tables.
- Deduplicate jobs before scoring or including them in a digest.
- The dedupe logic should prevent the same job from appearing again after it has
  already been seen.
- Prefer stable source identifiers when available; otherwise derive a normalized
  fingerprint from source, company, title, location, and canonical URL.

## Scoring

- Score new jobs against the user's resume with GPT-4o-mini unless the user
  approves a model change.
- Use a structured prompt and structured output so scores can be parsed and
  stored reliably.
- Score on a 1-10 scale.
- Store both the numeric score and a short reason.
- Treat scoring as ranking/filtering assistance, not truth. The final digest is a
  recommendation list, not an application decision.
- For LLM behavior changes, add small eval fixtures before trusting the new
  prompt broadly.

## Digest

- Generate one clean Markdown file per day.
- Prioritize the strongest jobs from the run. Prefer an adaptive threshold or
  top-N strategy over a rigid score cutoff.
- Each digest item should include company, title, location, source, score,
  reason, and direct job URL.
- Avoid repeated jobs across days unless a future decision explicitly allows
  resurfacing.

## Development Workflow

- Work in small vertical slices that can be tested end to end.
- After each successful slice, ask the user to run the git commands.
- The assistant must not run `git add`, `git commit`, or `git push`.
- Any user action, command, file edit, credential step, or manual setup step must
  be called out clearly when it is needed.
- Use Conventional Commit-style messages for suggested commits, such as
  `docs: expand project operating rules` or `feat(storage): add sqlite schema`.
- Prefer feature branches for larger work so `main` stays easy to reason about.

## Testing

- Every meaningful stage should have a small end-to-end check, even if it starts
  with fixtures instead of live network calls.
- Crawler code should separate fetching from parsing so parsing can be tested
  offline.
- Network-facing tests should be explicit and not required for every quick local
  test run.
- SQLite changes should include tests for schema creation and dedupe behavior.
- Scoring changes should include deterministic tests around prompt construction,
  response parsing, and threshold filtering.

## Diff Log

Use this section whenever the implementation deviates from a planned decision.
Each entry should explain what changed, why it changed, and whether the change is
temporary or permanent.

### Template

```text
Date:
Decision changed:
Previous plan:
New plan:
Reason:
Impact:
Temporary or permanent:
Follow-up:
```

### 2026-04-29

Decision changed: Source scope.
Previous plan: Crawl Indeed and Google Jobs through `python-jobspy`.
New plan: Drop Indeed. Keep Google Jobs through `python-jobspy`.
Reason: User explicitly said Indeed is not needed.
Impact: Fewer source-specific legal/rate-limit/product concerns; simpler source
priority.
Temporary or permanent: Permanent unless the user re-adds Indeed later.
Follow-up: Remove any future Indeed code paths if they appear.
