# Deployment

The maintained deployment target is a laptop-hosted personal app. Run the app on
your own machine, keep SQLite in `data/`, and access it privately when needed.
Hosted services with durable SQLite usually need paid persistent disk, so cloud
deployment is optional/demo only unless you accept that tradeoff.

## Recommended Free Setup

Run the dashboard locally:

```bash
PYTHONPATH=src uv run python -m job_crawler.cli serve --port 8782
```

Open:

```text
http://127.0.0.1:8782/
```

For private access from your other devices, use Tailscale and keep SQLite on your
laptop. To listen on your local network/Tailscale interface, run with
`--host 0.0.0.0` and keep auth enabled:

```bash
PYTHONPATH=src uv run python -m job_crawler.cli serve --host 0.0.0.0 --port 8782
```

Cloudflare Quick Tunnels are another free option for temporary access, but they
create an internet-reachable URL. Keep Basic Auth enabled if you use that route.

## Required Settings

For local-only use, `.env` can stay like:

```text
JOB_CRAWLER_DB_PATH=data/job_crawler.sqlite
TAVILY_API_KEY=<optional Tavily key for dashboard-enabled ATS discovery>
```

For any internet-reachable service, also set:

```text
JOB_CRAWLER_AUTH_USERNAME=<your username>
JOB_CRAWLER_AUTH_PASSWORD=<strong password>
```

Without `JOB_CRAWLER_AUTH_USERNAME` and `JOB_CRAWLER_AUTH_PASSWORD`, the dashboard is
open to anyone who can reach the deployed URL.

Without `TAVILY_API_KEY`, refresh still works, but live web discovery falls back
to free sources and DuckDuckGo HTML. Tavily is only used when the key is present
and the dashboard's Tavily search toggle is enabled for that refresh.

## Persistent SQLite

SQLite is fine for this personal app, but the database file must live on a persistent
volume. Do not rely on an ephemeral app filesystem, because deploys or restarts can
wipe the job history.

Good options:

- Local-only deployment on a machine you control.
- A paid server or hosted service with durable disk, only if you later decide
  always-on hosting is worth it.

Most free web tiers either sleep or do not include durable disk. If the host has
no persistent disk, treat it as a demo only.

## Refresh

The dashboard still refreshes on button click. That avoids scheduled compute cost and
keeps crawling deliberate.
