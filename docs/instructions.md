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

- Keep the pipeline modular: discovery, crawling, storage, scoring, and digest
  generation should remain separable.
- Prefer typed Python and small functions with clear boundaries.
- Keep network fetching separate from parsing and normalization.
- Use structured APIs and JSON parsing rather than scraping when a source offers
  a public API.
- Store data in SQLite through a narrow storage layer instead of scattering SQL
  across crawlers.
- Make dedupe idempotent: rerunning a stage should not create duplicate jobs.
- Keep local secrets out of git. Use `.env` and document required variables in
  `.env.example`.
- Do not add auto-apply behavior.
- Do not add Indeed support unless the user explicitly re-adds it.

## Testing Rules

- Build in small testable stages.
- Each stage should have a clear success check before asking the user to commit.
- Prefer offline fixture tests for parsers and normalization.
- Add live-network smoke scripts only when useful, and label them clearly.
- Run the smallest meaningful test first; broaden tests when touching shared
  storage, dedupe, or CLI behavior.

## LLM Scoring Rules

- Use GPT-4o-mini for job scoring unless the user approves a change.
- Keep prompts explicit and structured.
- Request parseable structured output.
- Store score, reason, model name, and scoring timestamp.
- Add prompt/eval fixtures before changing scoring behavior materially.

## Manual Command Template

When a stage is ready, the assistant should give commands in this shape:

```bash
cd /Users/akshatsingh/Documents/Codex/2026-04-29/build-me-a-personal-job-crawling
git status
git add <files>
git commit -m "<type(scope): message>"
git push
```
