from job_crawler.crawlers.base import JobPosting
from job_crawler.ranking import LocationTier, is_senior_role, location_tier, rank_job


def make_job(title: str, location: str | None, description: str | None = None) -> JobPosting:
    return JobPosting(
        source="fixture",
        source_id=f"{title}-{location}",
        company="Example Co",
        title=title,
        location=location,
        url="https://example.com/job",
        description=description,
    )


def test_location_tier_prioritizes_nyc_and_sf_first() -> None:
    assert location_tier("New York, NY") == LocationTier.PRIMARY
    assert location_tier("San Francisco, CA") == LocationTier.PRIMARY
    assert location_tier("Seattle, WA") == LocationTier.MAJOR_US_CITY
    assert location_tier("Boston, MA") == LocationTier.MAJOR_US_CITY
    assert location_tier("Austin, TX") == LocationTier.MAJOR_US_CITY
    assert location_tier("Remote (US)") == LocationTier.REMOTE_US


def test_rank_job_prefers_major_us_city_over_unknown_when_role_fit_matches() -> None:
    seattle = rank_job(make_job("AI Engineer", "Seattle, WA", "Entry level role"))
    unknown = rank_job(make_job("AI Engineer", "London", "Entry level role"))

    assert seattle.score > unknown.score
    assert seattle.location_tier == LocationTier.MAJOR_US_CITY


def test_rank_job_excludes_senior_staff_and_lead_roles() -> None:
    senior = make_job("Senior Machine Learning Engineer", "New York, NY")
    staff = make_job("Staff AI Engineer", "San Francisco, CA")
    junior = make_job("Software Engineer I", "Boston, MA")

    assert is_senior_role(senior)
    assert is_senior_role(staff)
    assert not is_senior_role(junior)
    assert rank_job(senior).excluded is True
    assert rank_job(staff).excluded is True
    assert rank_job(junior).excluded is False
