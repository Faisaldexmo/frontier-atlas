import logging

from src.entity.startup import Startup
from src.scrapers.startups import YCStartupScraper
from src.storage.json_storage import JSONStorage


logger = logging.getLogger(__name__)


OUTPUT_FILE = (
    "data/output/startups.json"
)


async def run_startup_pipeline(
    max_startups: int = 1000,
) -> list[dict]:
    """
    Collect and validate startup records.
    """

    scraper = YCStartupScraper()

    startups = await scraper.collect(
        max_startups=max_startups
    )

    if not startups:
        raise RuntimeError(
            "No startups were collected."
        )

    validated_startups = []

    for index, startup in enumerate(
        startups,
        start=1,
    ):
        try:
            validated = Startup(
                **startup
            )

            validated_startups.append(
                validated.model_dump(
                    mode="json"
                )
            )

            logger.info(
                "Processed %s/%s: %s",
                index,
                len(startups),
                startup["entity_name"],
            )

        except Exception as exc:
            logger.error(
                "Startup validation failed: %s",
                exc,
            )

    if not validated_startups:
        raise RuntimeError(
            "No valid startup records."
        )

    return validated_startups


def save_startups(
    startups: list[dict],
) -> None:
    """
    Save startup records to JSON.
    """

    if not startups:
        raise ValueError(
            "Refusing to save empty startup data."
        )

    storage = JSONStorage(
        OUTPUT_FILE
    )

    storage.save(
        startups
    )

    logger.info(
        "Saved %s startups to %s",
        len(startups),
        OUTPUT_FILE,
    )