# Deployment

The app can run anywhere a long-lived Python web process and persistent disk are available.

## Required Settings

Set these in the deployed service:

```text
JOB_CRAWLER_DB_PATH=/var/data/job_crawler.sqlite
JOB_CRAWLER_AUTH_USERNAME=<your username>
JOB_CRAWLER_AUTH_PASSWORD=<strong password>
```

Without `JOB_CRAWLER_AUTH_USERNAME` and `JOB_CRAWLER_AUTH_PASSWORD`, the dashboard is
open to anyone who can reach the deployed URL.

## Persistent SQLite

SQLite is fine for this personal app, but the database file must live on a persistent
volume. Do not rely on an ephemeral app filesystem, because deploys or restarts can
wipe the job history.

Good options:

- Render/Fly/Railway style service with a mounted persistent disk.
- A small VPS with Docker and a mounted host directory.
- Local-only deployment on a machine you control.

Most free web tiers either sleep or do not include durable disk. If the host has no
persistent disk, treat it as a demo only.

## Docker

Build locally:

```bash
docker build -t job-crawler .
```

Run with a local persistent data directory:

```bash
docker run --rm \
  -p 8765:8765 \
  -v "$PWD/data:/var/data" \
  -e JOB_CRAWLER_DB_PATH=/var/data/job_crawler.sqlite \
  -e JOB_CRAWLER_AUTH_USERNAME=akshat \
  -e JOB_CRAWLER_AUTH_PASSWORD='change-me' \
  job-crawler
```

Open:

```text
http://127.0.0.1:8765/
```

## Render Blueprint

`render.yaml` defines:

- Docker web service
- `/health` health check
- 1 GB persistent disk mounted at `/var/data`
- private auth env vars

After creating the Render service, set the auth env vars in the Render dashboard before
making the URL public.

## Refresh

The dashboard still refreshes on button click. That avoids scheduled compute cost and
keeps crawling deliberate.
