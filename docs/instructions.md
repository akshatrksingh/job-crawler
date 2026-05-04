# Project Instructions

These are strict operating rules for this project.

## User Control

- The assistant must ask the user before any big product, architecture, model,
  cost, credential, hosting, or scheduling decision.
- The assistant must explicitly tell the user whenever the user needs to run a
  command, edit a file, add a credential, approve network access, or perform any
  setup outside the assistant's workspace.
- The assistant should make small implementation decisions that follow existing
  project patterns, then record durable decisions in `docs/decisions.md`.

## Git Rules

- The assistant must not run:
  - `git add`
  - `git commit`
  - `git push`
- After successful work, the assistant should provide exact commands for the user
  to run manually.
- Suggested commit messages should follow Conventional Commits:
  - `feat(scope): short description`
  - `fix(scope): short description`
  - `docs(scope): short description`
  - `test(scope): short description`
  - `refactor(scope): short description`
  - `chore(scope): short description`
- Keep commits focused around one tested development stage.
- For larger stages, prefer a feature branch and ask the user to create/push it.

## Coding Rules

- Keep the pipeline modular: discovery, crawling, storage, ranking, dashboard,
  and refresh orchestration should remain separable.
- Prefer typed Python and small functions with clear boundaries.
- Keep network fetching separate from parsing and normalization.
- Use structured APIs and JSON parsing rather than scraping when a source offers
  a public API.
- Store data in SQLite through a narrow storage layer instead of scattering SQL
  across crawlers.
- Keep personal-app state in SQLite by default. Do not add Redis or another
  service unless the single-user SQLite path stops being enough.
- Make dedupe idempotent: rerunning a stage should not create duplicate jobs.
- Keep local secrets out of git. Use `.env` and document required variables in
  `.env.example`.
- Do not add auto-apply behavior.
- Do not add Indeed support unless the user explicitly re-adds it.
- Protect against rate limits and accidental spend. Use conservative limits,
  adaptive source scheduling, persisted crawl state, idempotent retries, and
  explicit user approval before increasing crawl volume, schedule frequency, or
  paid API usage.

## Testing Rules

- Build in small testable stages.
- Each stage should have a clear success check before asking the user to commit.
- Prefer offline fixture tests for parsers and normalization.
- Add live-network smoke scripts only when useful, and label them clearly.
- Run the smallest meaningful test first; broaden tests when touching shared
  storage, dedupe, or CLI behavior.

## Ranking Rules

- Do not add LLM/resume scoring unless the user explicitly re-adds it.
- Keep default ranking cost-free and deterministic.
- If semantic filtering is added later, it must be optional, cached, and
  disabled unless the user explicitly configures the chosen provider key.
- Prioritize NYC and SF first, then other major US cities such as Seattle,
  Boston, Austin, Los Angeles, Chicago, Denver, Washington DC, and Atlanta.
- Include Remote US roles.
- Exclude or strongly penalize senior, staff, principal, lead, manager, director,
  and architect roles.
- Add deterministic tests before changing ranking behavior materially.

## Manual Command Template

When a stage is ready, the assistant should give commands in this shape:

```bash
cd /Users/akshatsingh/Documents/Codex/2026-04-29/build-me-a-personal-job-crawling
git status
git add <files>
git commit -m "<type(scope): message>"
git push
```
