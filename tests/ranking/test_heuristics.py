from job_crawler.crawlers.base import JobPosting
from job_crawler.ranking import (
    LocationTier,
    is_senior_role,
    is_target_role,
    is_us_role,
    location_tier,
    rank_job,
    requires_too_much_experience,
    role_category,
)


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
    assert location_tier("Remote") == LocationTier.GENERIC_REMOTE


def test_rank_job_prefers_us_city_over_generic_remote_when_role_fit_matches() -> None:
    seattle = rank_job(make_job("AI Engineer", "Seattle, WA", "Entry level role"))
    remote = rank_job(make_job("AI Engineer", "Remote", "Entry level role"))

    assert seattle.score > remote.score
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


def test_rank_job_excludes_roles_requiring_more_than_three_years() -> None:
    too_much = make_job(
        "Software Engineer",
        "Austin, TX",
        "Requires 5+ years of professional experience building production systems.",
    )
    okay = make_job(
        "Machine Learning Engineer",
        "Seattle, WA",
        "Looking for 0-3 years of experience or equivalent internship work.",
    )

    assert requires_too_much_experience(too_much)
    assert not requires_too_much_experience(okay)
    assert rank_job(too_much).excluded is True
    assert rank_job(okay).excluded is False


def test_role_category_handles_target_role_variations() -> None:
    assert role_category("Machine Learning Engineer") == "ML"
    assert role_category("AI Engineer") == "AI"
    assert role_category("Software Development Engineer") == "SWE/SDE"
    assert role_category("Backend Platform Engineer") == "Infrastructure"
    assert role_category("Data Scientist") == "Data Science"
    assert role_category("Fullstack Engineer") == "SWE/SDE"
    assert role_category("Founding Engineer") == "Founding"
    assert role_category("Autonomy Engineer, Computer Vision") == "Engineering"
    assert role_category("CUDA Kernel Engineer") == "Engineering"


def test_is_us_role_excludes_non_us_only_locations_but_keeps_us_and_generic_remote() -> None:
    assert is_us_role(make_job("AI Engineer", "Seattle, WA"))
    assert is_us_role(make_job("AI Engineer", "Seatle, Remote"))
    assert is_us_role(make_job("AI Engineer", "Boise, ID"))
    assert is_us_role(make_job("AI Engineer", "Bentonville, Arkansas"))
    assert is_us_role(make_job("AI Engineer", "Tulsa"))
    assert is_us_role(make_job("AI Engineer", "New York, London"))
    assert is_us_role(make_job("AI Engineer", "Remote"))
    assert is_us_role(make_job("AI Engineer", "Remote (United States)"))
    assert not is_us_role(make_job("AI Engineer", "Canada, Remote"))
    assert not is_us_role(make_job("AI Engineer", "Remote - United Kingdom"))
    assert not is_us_role(make_job("AI Engineer", "Shanghai, Remote"))
    assert not is_us_role(make_job("AI Engineer", "Gdańsk, Poland, Remote"))
    assert not is_us_role(make_job("AI Engineer", "Ottawa, Canada"))
    assert not is_us_role(make_job("AI Engineer", "Amsterdam, Netherlands"))
    assert not is_us_role(make_job("AI Engineer", "Lisbon, Portugal"))
    assert not is_us_role(make_job("AI Engineer", "Tokyo, Japan"))


def test_is_target_role_keeps_relevant_technical_roles_and_drops_noise() -> None:
    assert is_target_role(make_job("Machine Learning Engineer", "Boston, US"))
    assert is_target_role(make_job("Applied AI Engineer", "Austin"))
    assert is_target_role(make_job("LLM Engineer", "New York"))
    assert is_target_role(make_job("Generative AI Engineer", "San Francisco"))
    assert is_target_role(make_job("Research Scientist, Deep Learning", "Seattle"))
    assert is_target_role(make_job("Data Science Engineer", "Boston"))
    assert is_target_role(make_job("Software Engineer, ML Ops", "Atlanta"))
    assert is_target_role(make_job("Software Development Engineer", "Seattle"))
    assert is_target_role(make_job("Data Scientist", "Chicago"))
    assert is_target_role(make_job("Forward Deployed Software Engineer", "Denver"))
    assert is_target_role(make_job("Founding Engineer", "New York"))
    assert is_target_role(make_job("Backend Engineer", "Austin"))
    assert is_target_role(make_job("Full Stack Engineer", "Seattle"))
    assert is_target_role(make_job("Autonomy Engineer, Computer Vision", "Seattle"))
    assert is_target_role(make_job("CUDA Kernel Engineer", "Boston"))
    assert not is_target_role(make_job("Recruiter", "Seattle"))
    assert not is_target_role(make_job("Product Manager, AI", "New York"))
    assert not is_target_role(make_job("Growth Operations Associate", "San Francisco"))
    assert not is_target_role(make_job("Cloud Security Engineer", "Seattle"))
    assert not is_target_role(make_job("Support Engineer", "Remote"))
    assert not is_target_role(make_job("Field Engineer", "Austin"))
    assert not is_target_role(make_job("Social Media Manager", "New York"))


def test_is_target_role_can_use_description_for_ai_context() -> None:
    assert is_target_role(
        make_job(
            "Product Engineer",
            "New York",
            "Build applied AI agents and LLM workflows for customers.",
        )
    )
    assert not is_target_role(
        make_job(
            "QA Analyst",
            "Chicago",
            "Jobright 2026 SWE new-grad board. Board freshness: 1d.",
        )
    )
