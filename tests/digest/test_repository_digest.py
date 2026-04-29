from job_crawler.crawlers.base import JobPosting
from job_crawler.storage import JobRepository, open_database


def test_list_jobs_for_digest_returns_recent_jobs_as_postings() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        repo.insert_job(
            JobPosting(
                source="ashby",
                source_id="job-1",
                company="Example Co",
                title="Software Engineer I",
                location="New York, NY",
                url="https://example.com/job-1",
                description="Entry level role.",
            )
        )

        jobs = repo.list_jobs_for_digest()

        assert len(jobs) == 1
        assert jobs[0].company == "Example Co"
        assert jobs[0].title == "Software Engineer I"
        assert jobs[0].location == "New York, NY"


def test_list_jobs_for_digest_includes_hn_by_default() -> None:
    with open_database(":memory:") as connection:
        repo = JobRepository(connection)
        repo.insert_job(
            JobPosting(
                source="hn",
                source_id="comment-1",
                company="Example Labs",
                title="Applied AI Engineer",
                location="Remote (US)",
                url="https://news.ycombinator.com/item?id=1",
                description="Hiring applied AI engineers.",
            )
        )

        jobs = repo.list_jobs_for_digest()

        assert len(jobs) == 1
        assert jobs[0].source == "hn"
