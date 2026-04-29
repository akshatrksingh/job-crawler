# Decisions

This file records design choices that are worth revisiting.

## Initial Constraints

- Do not auto-apply to jobs.
- Discover company career pages dynamically instead of maintaining a hardcoded list.
- Store crawl state, dedupe keys, job records, and scores in SQLite.
- Produce a daily Markdown digest containing only jobs with score >= 7.
