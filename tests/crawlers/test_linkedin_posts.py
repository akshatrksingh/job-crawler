from job_crawler.crawlers.linkedin_posts import (
    LINKEDIN_POST_SOURCE,
    SearchResult,
    fetch_linkedin_post_leads,
    parse_duckduckgo_results,
    parse_google_results,
)


def test_parse_google_results_extracts_linkedin_posts() -> None:
    html = """
<a href="/url?q=https://www.linkedin.com/posts/example_hiring-ai-engineer-activity-1&sa=U">
  Hiring AI Engineer | LinkedIn
</a>
<a href="/url?q=https://www.linkedin.com/jobs/view/123&sa=U">LinkedIn job</a>
"""

    results = parse_google_results(html, limit=5)

    assert len(results) == 1
    assert results[0].url == "https://www.linkedin.com/posts/example_hiring-ai-engineer-activity-1"
    assert results[0].title == "Hiring AI Engineer | LinkedIn"


def test_parse_duckduckgo_results_extracts_linkedin_posts_with_snippets() -> None:
    url = (
        "https%3A%2F%2Fwww.linkedin.com%2Fposts%2F"
        "person_hiring-applied-ai-engineer-activity-2"
    )
    html = f"""
<div class="result">
  <a class="result__a" href="//duckduckgo.com/l/?uddg={url}">
    Founder hiring Applied AI Engineer
  </a>
  <a class="result__snippet">Remote United States startup role.</a>
</div>
"""

    results = parse_duckduckgo_results(html, limit=5)

    assert len(results) == 1
    assert results[0].snippet == "Remote United States startup role."


def test_fetch_linkedin_post_leads_filters_and_dedupes_results() -> None:
    def fake_fetcher(query: str, limit: int):
        assert limit == 2
        return [
            SearchResult(
                url="https://www.linkedin.com/posts/founder_hiring-founding-ai-engineer-activity-1",
                title="Founder hiring Founding AI Engineer | LinkedIn",
                snippet="New York startup role, 0-3 YOE.",
            ),
            SearchResult(
                url="https://www.linkedin.com/posts/founder_hiring-founding-ai-engineer-activity-1?trk=public",
                title="Founder hiring Founding AI Engineer | LinkedIn",
                snippet="New York startup role, 0-3 YOE.",
            ),
            SearchResult(
                url="https://www.linkedin.com/posts/person_marketing-role-activity-3",
                title="Marketing role",
                snippet="Hiring a marketer.",
            ),
        ]

    leads = fetch_linkedin_post_leads(
        queries=("q1",),
        results_per_query=2,
        fetcher=fake_fetcher,
    )

    assert len(leads) == 1
    assert leads[0].source == LINKEDIN_POST_SOURCE
    assert leads[0].company == "Founder"
    assert leads[0].title == "Founder hiring Founding AI Engineer"
    assert leads[0].location == "New York, NY"
