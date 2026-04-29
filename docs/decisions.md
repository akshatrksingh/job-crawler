# Decisions

This document is the project's decision log. It records durable product,
architecture, and workflow choices so the crawler does not drift silently as it
grows.

## Product Scope

- The project is a personal job discovery pipeline.
- The project must not auto-apply to jobs.
- The project should find jobs, filter/rank them with zero-cost heuristics, and
  create a daily Markdown digest.
- The daily digest should be simple and scannable: company, job title, link, and
  location are enough.
- The digest should prioritize the best jobs from each run using deterministic
  role, seniority, location, and recency heuristics.
- The target roles are ML engineer, AI engineer, agentic AI engineer, applied AI
  roles, SWE roles, SDE roles, and closely related engineering roles.
- The target seniority is new grad, entry level, junior, or roles expecting up to
  roughly 2-3 years of experience. This is a soft boundary, but senior, staff,
  principal, lead, manager, and architect roles should usually be avoided.
- The target locations prioritize New York City and San Francisco first, then
  other major US cities and nearby metro areas such as Seattle, Boston, Austin,
  Los Angeles, Chicago, Denver, Washington DC, and Atlanta. Remote US roles are
  also in scope.
- Any company type is acceptable. Startups, mid-size companies, larger companies,
  labs, and non-FAANG companies are all in scope.
- Indeed is intentionally out of scope.

## Sources

Planned crawl sources:

- Greenhouse startup career pages.
- Lever startup career pages.
- Ashby startup career pages.
- Hacker News Who is Hiring through the public Algolia API.
- YC Work at a Startup board, using visible public pages unless a stable free API
  is identified and approved.

Discovery requirements:

- Do not maintain a hardcoded company list as the main crawl input.
- Discover company career-page slugs dynamically from search queries such as
  `site:jobs.ashbyhq.com machine learning engineer San Francisco`.
- Store discovered source slugs in SQLite with enough metadata to audit where
  they came from.
- Live source discovery should prefer an explicit search API over direct Google
  scraping.
- Tavily is the approved optional live web discovery provider when
  `TAVILY_API_KEY` is set. It should use bounded basic searches and only extract
  supported ATS URLs.
- Tavily discovery should run roughly 100 targeted searches per refresh by
  default, spanning AI/ML/SWE/data/founding role groups, early-career wording,
  broad US targeting, and major cities such as NYC, SF, Seattle, Boston, Austin,
  Los Angeles, Chicago, Denver, Atlanta, and Washington DC.
- Persist an adaptive Tavily/web-discovery query budget. Start near 100 queries,
  back off by 10 after failures or empty discovery runs, never go below 10, and
  recover upward by 10 after successful discovery.
- Without a Tavily key, refresh must still work at $0 using stored ATS sources,
  GitHub-maintained job boards, YC, HN, and a conservative DuckDuckGo HTML
  fallback.
- Large hardcoded company lists are allowed only as fallback seed data, not as
  the primary discovery strategy.

## Rate Limits and Cost Control

- Avoid aggressive crawling. The crawler should run with conservative per-source
  limits, delays, and retry behavior.
- Persist crawl timestamps and discovered sources so reruns do not repeatedly hit
  the same endpoints unnecessarily.
- Prefer incremental crawling and cached state over full recrawls.
- Keep live-network smoke tests small and explicit.
- Do not add paid APIs or LLM calls unless the user explicitly approves them and
  provides the required key.
- The default pipeline should cost $0 to run aside from normal local compute and
  internet usage.
- Do not run Google Jobs live searches by default; they were removed because
  they repeatedly hit upstream 429 blocks and added noise without useful jobs.
- Any increase to crawl frequency, query breadth, paid API usage, or scheduled
  execution needs user approval.
- Cache discovered sources and inserted jobs so refresh does not reclassify or
  recrawl more than needed.
- Limit each individual Ashby, Greenhouse, or Lever company-board crawl to 10
  jobs by default. Increase this only when deliberately inspecting a specific
  company.

## Storage

- SQLite is the source of truth.
- Store raw crawl metadata where useful for debugging, but normalize job records
  into stable tables.
- Deduplicate jobs before ranking or including them in a digest.
- The dedupe logic should prevent the same job from appearing again after it has
  already been seen.
- Prefer stable source identifiers when available; otherwise derive a normalized
  fingerprint from source, company, title, location, and canonical URL.

## Ranking

- Do not implement resume/GPT scoring in the current plan.
- Use zero-cost deterministic heuristics for filtering and ranking.
- Prioritize role match, early-career fit, location priority, source recency, and
  dedupe state.
- Penalize or exclude senior, staff, principal, lead, manager, director, and
  architect roles by default.
- Ranking is used to order the digest, not to make final application decisions.

## Digest

- Generate one clean Markdown file per day.
- Prioritize the strongest jobs from the run with zero-cost ranking heuristics.
- Each digest item should include only company, job title, direct job URL, and
  location by default.
- Internal rank metadata should stay out of the default digest unless the user
  asks to show it.
- Avoid repeated jobs across days unless a future decision explicitly allows
  resurfacing.

## Dashboard

- Generate a local private HTML dashboard from SQLite.
- The default dashboard path is `site/index.html`.
- The dashboard should show jobs from the last 14 days, using posted date when
  available and fetched/current date otherwise.
- Jobs older than the rolling window should be removed from view but remain in
  SQLite.
- The dashboard should not impose a hard display limit.
- The dashboard should show newest jobs first.
- The dashboard should provide simple filters such as search, location, and
  source.
- The dashboard should not include filter controls by default. Jobs are fetched
  broadly across the US and ranked with major-city preference.
- Do not publish the dashboard to the internet or add hosting/auth without user
  approval.

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
- Ranking changes should include deterministic tests around location priority,
  seniority exclusion, and role keyword handling.

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

Decision changed: Digest detail level.
Previous plan: Include score and match reason in each digest item.
New plan: Show only company, job title, link, and location by default.
Reason: User wants a compact list without summaries or "why it matches" text.
Impact: Scores remain internal for ranking/filtering but are not shown in the
default digest.
Temporary or permanent: Permanent unless the user asks for richer digest output.
Follow-up: Keep digest renderer minimal in Stage 8.

Decision changed: Dynamic discovery implementation sequence.
Previous plan: Run live Google-style searches as part of Stage 4.
New plan: First build provider-neutral query generation and URL extraction;
choose any live search provider separately.
Reason: Live search can trigger rate limits, brittle scraping behavior, or paid
API usage.
Impact: Discovery logic is testable now without network calls; live discovery
needs one more approved integration decision.
Temporary or permanent: Temporary sequencing decision.
Follow-up: Ask user before adding SerpAPI, Google Custom Search, browser-based
search, or another live search provider.

Decision changed: Resume/GPT scoring.
Previous plan: Score jobs against the user's resume with GPT-4o-mini.
New plan: Drop resume/GPT scoring from the current pipeline and use zero-cost
heuristic filtering/ranking.
Reason: User said resume scoring is not needed and wants costs to remain $0.
Impact: No OpenAI API key or credits are needed for the planned pipeline. Digest
ordering will be deterministic and simpler.
Temporary or permanent: Permanent unless the user re-adds resume scoring later.
Follow-up: Remove scoring-oriented stage planning and avoid paid model calls.

Decision changed: Location targeting.
Previous plan: Prioritize SF, NYC, and remote with vague support for other US
cities.
New plan: Prioritize NYC and SF first, then consider other major US cities and
nearby metro areas such as Seattle, Boston, Austin, Los Angeles, Chicago, Denver,
Washington DC, and Atlanta. Remote US remains in scope.
Reason: User clarified that the search should not be only SF/NYC.
Impact: Query generation, Google Jobs defaults, YC location parsing, and ranking
heuristics should all include major US cities.
Temporary or permanent: Permanent unless narrowed later.
Follow-up: Keep digest ordering NYC/SF first, then other strong US-city matches.

Decision changed: Daily output channel.
Previous plan: Send one daily email digest.
New plan: Generate a local private dashboard page from SQLite.
Reason: User prefers a personal page like a job board, with all recent fetched
jobs in one place.
Impact: No email provider, SMTP credentials, or daily email deliverability setup
is needed. The dashboard remains private on the local machine by default.
Temporary or permanent: Permanent unless the user asks for email or hosted access
later.
Follow-up: Add scheduling only after the manual dashboard update flow works.

Decision changed: Hacker News source.
Previous plan: Remove HN from the active crawler pipeline and dashboard.
New plan: Re-include HN Who is Hiring through Algolia.
Reason: User later asked to include HN again as another broad source of early
startup hiring leads.
Impact: HN is fetched during refresh and can also contribute direct ATS links
that become stored company sources.
Temporary or permanent: Permanent unless the user removes HN again.
Follow-up: Keep HN parsing bounded and rely on downstream relevance filters for
noisy comments.

Decision changed: Refresh cadence.
Previous plan: Refresh could be clicked repeatedly while the server is running.
New plan: Persist refresh time and disable refresh for 6 hours after a successful
refresh.
Reason: User wants to avoid repeated fetching, rate limits, and abuse.
Impact: The dashboard shows last refresh time and next allowed refresh time.
Temporary or permanent: Permanent default; cooldown length can be changed later.
Follow-up: Apply the same cooldown/backoff pattern when ATS refresh is added.

Decision changed: Dashboard filters.
Previous plan: Include search, location, role, and source filters.
New plan: Remove all dashboard filters.
Reason: User wants the page to stay simple and not require role/source filtering.
Impact: Fetching should stay broad; ranking can still favor relevant roles and
bigger US cities behind the scenes.
Temporary or permanent: Permanent unless the dashboard gets too noisy.
Follow-up: Add semantic role filtering only after a free Groq path is wired in.

Decision changed: Semantic role filtering.
Previous plan: Use deterministic role heuristics only.
New plan: Keep deterministic heuristics now, but allow a future optional Groq
semantic role filter.
Reason: User is interested in semantic filtering for adjacent tech roles.
Impact: No Groq calls are made yet. If added, the key belongs in `.env` as
`GROQ_API_KEY`.
Temporary or permanent: Planned optional enhancement.
Follow-up: Add Groq only behind explicit opt-in and cache classifications so
jobs are not reclassified repeatedly.

Decision changed: Google Jobs source.
Previous plan: Keep Google Jobs through `python-jobspy`.
New plan: Remove Google Jobs from the active crawler and project dependency list.
Reason: Live refreshes repeatedly hit Google 429 / sorry pages and produced noisy
failure rows without useful job records.
Impact: Refresh status is cleaner, fewer network calls are made, and the app no
longer depends on `python-jobspy`.
Temporary or permanent: Permanent unless a stable, compliant, free Google Jobs
API path is found later.
Follow-up: Prefer ATS APIs, GitHub boards, YC, HN Algolia, and company-source
expansion.

Decision changed: Dynamic source discovery.
Previous plan: Rely on stored company sources plus direct Google-style searches,
with a possible hardcoded company list to broaden coverage.
New plan: Run source expansion before ATS crawling. Refresh first discovers ATS
boards from bounded web search, GitHub job-board apply links, HN links, and YC
links, then crawls stored Ashby, Greenhouse, and Lever boards. Optional Tavily
search is used when `TAVILY_API_KEY` is configured; otherwise discovery stays on
free sources and DuckDuckGo fallback.
Reason: A static company list would miss new companies and direct Google
scraping triggered 429 blocks. Tavily gives a cleaner opt-in search path without
making the app depend on paid calls.
Impact: New ATS companies can enter SQLite before the same refresh crawls ATS
boards, and the source cap is raised so the app is not limited to the first few
hundred discovered companies.
Temporary or permanent: Permanent architecture direction; provider details can
change.
Follow-up: Add a curated seed list only if dynamic discovery still leaves major
coverage gaps.

Decision changed: Per-company crawl breadth.
Previous plan: Fetch up to 100 jobs from each Ashby, Greenhouse, or Lever board.
New plan: Fetch up to 10 jobs per ATS company board by default while keeping
curated aggregate boards broader.
Reason: Large companies can return hundreds of unrelated postings, creating DB
noise and longer refreshes without improving the top dashboard results.
Impact: Refresh is lighter and the database grows more slowly. Deep company
inspection can still be done later with an explicit higher limit.
Temporary or permanent: Permanent default.
Follow-up: Add a company-specific "crawl more" control only if needed.

Decision changed: Tavily/web-discovery backoff.
Previous plan: Run the configured web-discovery query count every refresh.
New plan: Persist an adaptive query budget in SQLite. Discovery starts near 100
queries, drops by 10 after failures or empty runs until a floor of 10, and
recovers by 10 after successful discovery.
Reason: A flaky search connection can otherwise make refresh feel stuck and burn
unnecessary search calls.
Impact: Refresh becomes less aggressive after bad Tavily/network runs, while
still preserving a minimum discovery path.
Temporary or permanent: Permanent default.
Follow-up: Surface the current query budget in the dashboard if it becomes useful
for debugging.
