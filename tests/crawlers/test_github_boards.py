from job_crawler.crawlers.github_boards import (
    GitHubJobBoard,
    parse_html_board,
    parse_markdown_board,
)


def test_parse_markdown_board_extracts_jobright_rows_and_carries_company() -> None:
    board = GitHubJobBoard(
        name="jobright",
        url="https://example.com/jobright.md",
        format="markdown",
        description="Jobright",
    )
    markdown = "\n".join(
        (
            "| Company | Job Title | Location | Work Model | Date Posted |",
            "| ----- | --------- | -------- | ---------- | ----------- |",
            "| **[Google](https://google.com)** | "
            "**[Software Engineer](https://jobright.ai/jobs/info/123)** | "
            "Atlanta, GA | On Site | Apr 29 |",
            "| ↳ | **[Software Engineer](https://jobright.ai/jobs/info/456)** | "
            "Austin, TX | On Site | Apr 29 |",
        )
    )

    jobs = parse_markdown_board(markdown, board=board)

    assert len(jobs) == 2
    assert jobs[0].source == "jobright"
    assert jobs[0].company == "Google"
    assert jobs[0].title == "Software Engineer"
    assert jobs[0].location == "Atlanta, GA"
    assert jobs[0].url == "https://jobright.ai/jobs/info/123"
    assert jobs[0].posted_at is not None
    assert jobs[1].company == "Google"
    assert jobs[1].location == "Austin, TX"


def test_parse_html_board_extracts_simplify_direct_apply_links_and_skips_closed() -> None:
    board = GitHubJobBoard(
        name="simplify",
        url="https://example.com/simplify.md",
        format="html",
        description="Simplify",
    )
    html = """
<table>
<thead><tr><th>Company</th><th>Role</th><th>Location</th><th>Application</th><th>Age</th></tr></thead>
<tbody>
<tr>
  <td><strong><a href="https://simplify.jobs/c/Notion">🔥 Notion</a></strong></td>
  <td>Software Engineer – New Grad - AI</td>
  <td>Seattle, WA</br>SF</td>
  <td>
    <div>
      <a href="https://jobs.ashbyhq.com/notion/abc/application"><img alt="Apply"></a>
      <a href="https://simplify.jobs/p/abc"><img alt="Simplify"></a>
    </div>
  </td>
  <td>1d</td>
</tr>
<tr>
  <td><strong>Closed Co</strong></td>
  <td>Software Engineer I</td>
  <td>NYC</td>
  <td>🔒</td>
  <td>7mo</td>
</tr>
</tbody>
</table>
"""

    jobs = parse_html_board(html, board=board)

    assert len(jobs) == 1
    assert jobs[0].company == "Notion"
    assert jobs[0].title == "Software Engineer – New Grad - AI"
    assert jobs[0].location == "Seattle, WA, SF"
    assert jobs[0].url == "https://jobs.ashbyhq.com/notion/abc/application"


def test_parse_html_board_skips_rows_without_real_locations() -> None:
    board = GitHubJobBoard(
        name="simplify",
        url="https://example.com/simplify.md",
        format="html",
        description="Simplify",
    )
    html = """
<table>
<thead><tr><th>Company</th><th>Role</th><th>Location</th><th>Application</th></tr></thead>
<tbody>
<tr>
  <td>[Bad Co](https://bad.example)</td>
  <td>QA Analyst</td>
  <td>https://bad.example</td>
  <td><a href="https://bad.example/apply"><img alt="Apply"></a></td>
</tr>
</tbody>
</table>
"""

    assert parse_html_board(html, board=board) == []


def test_default_boards_include_swe_data_and_simplify_sources() -> None:
    from job_crawler.crawlers.github_boards import DEFAULT_GITHUB_JOB_BOARDS

    names = {board.name for board in DEFAULT_GITHUB_JOB_BOARDS}

    assert "jobright_swe_new_grad_2026" in names
    assert "jobright_data_analysis_new_grad_2026" in names
    assert "simplify_new_grad_positions" in names
