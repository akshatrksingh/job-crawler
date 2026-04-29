from job_crawler.crawlers.yc import parse_yc_jobs_html


def test_parse_yc_jobs_html_extracts_visible_job_links() -> None:
    html = """
    <html>
      <body>
        <a href="/jobs/example-ai-founding-engineer">
          Founding Engineer
        </a>
        <div>
          Example AI (S24) AI tools for developers.
          Founding Engineer
          Full-time Engineering San Francisco, CA, US / Remote (US)
        </div>
        <a href="/jobs">Jobs</a>
        <a href="/jobs/role/designer">Design & UI/UX</a>
      </body>
    </html>
    """

    jobs = parse_yc_jobs_html(html)

    assert len(jobs) == 1
    assert jobs[0].source == "yc"
    assert jobs[0].source_id == "example-ai-founding-engineer"
    assert jobs[0].title == "Founding Engineer"
    assert jobs[0].url == "https://www.ycombinator.com/jobs/example-ai-founding-engineer"
