import pytest

from src.pipelines.research_pipeline import run_pipeline


@pytest.mark.asyncio
async def test_pipeline_returns_research_papers():
    papers = await run_pipeline(
        max_papers=2
    )

    assert len(papers) == 2

    for paper in papers:
        assert paper["title"]
        assert paper["paper_url"]
        assert paper["authors"] is not None

        assert (
            paper["github_confidence"]
            >= 0.0
        )

        assert (
            paper["github_confidence"]
            <= 1.0
        )