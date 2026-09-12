import pytest

from src.scrapers.base import BaseScraper


@pytest.mark.asyncio
async def test_fetch_many():
    urls = [
        "https://www.arxiv.org",
        "https://export.arxiv.org",
    ]

    scraper = BaseScraper(
        max_concurrency=5
    )

    results = await scraper.fetch_many(
        urls
    )

    assert len(results) == 2

    for html in results:
        assert html
        assert len(html) > 0