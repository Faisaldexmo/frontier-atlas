import logging

from src.scrapers.news import NewsScraper
from src.storage.json_storage import JSONStorage


logger = logging.getLogger(__name__)

OUTPUT_FILE = "data/output/news.json"


async def run_news_pipeline(
    max_news: int = 100,
) -> list[dict]:

    scraper = NewsScraper()

    news = await scraper.collect(
        max_news=max_news
    )

    if not news:
        raise RuntimeError(
            "No fresh AI news was collected."
        )

    news = scraper.deduplicate(
        news
    )

    # Convert datetime objects into
    # JSON-compatible ISO strings.
    for item in news:

        if item.get("published_at") is not None:
            item["published_at"] = (
                item["published_at"].isoformat()
            )

        if item.get("collected_at") is not None:
            item["collected_at"] = (
                item["collected_at"].isoformat()
            )

    logger.info(
        "Collected %s fresh AI news articles",
        len(news),
    )

    return news


def save_news(
    news: list[dict],
) -> None:

    if not news:
        raise ValueError(
            "Refusing to save empty news data."
        )

    storage = JSONStorage(
        OUTPUT_FILE
    )

    storage.save(
        news
    )

    logger.info(
        "Saved %s news articles to %s",
        len(news),
        OUTPUT_FILE,
    )