FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV JOB_CRAWLER_DB_PATH=/var/data/job_crawler.sqlite

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .
RUN mkdir -p /var/data /tmp/job-crawler/site

EXPOSE 8765

CMD ["sh", "-c", "job-crawler serve --host 0.0.0.0 --port ${PORT:-8765} --db ${JOB_CRAWLER_DB_PATH:-/var/data/job_crawler.sqlite} --output /tmp/job-crawler/site/index.html"]
