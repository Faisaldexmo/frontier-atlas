import logging
from datetime import datetime, timezone

from src.scrapers.jobs import JobScraper
from src.entity.job import Job
from src.storage.json_storage import JSONStorage


logger = logging.getLogger(__name__)

OUTPUT_FILE = "data/output/jobs.json"


async def run_job_pipeline() -> list[dict]:
    """
    Collect fresh AI jobs from the configured job sources,
    validate them, and SAVE the final dataset.
    """

    scraper = JobScraper()

    logger.info("Starting job collection...")

    raw_jobs = await scraper.collect()

    logger.info(
        "Collected %s jobs.",
        len(raw_jobs),
    )

    processed_jobs = []

    for job in raw_jobs:

        try:
            # Make sure collected_at exists.
            if not job.get("collected_at"):
                job["collected_at"] = (
                    datetime.now(timezone.utc)
                    .isoformat()
                )

            validated_job = Job(
                **job
            )

            processed_jobs.append(
                validated_job.model_dump(
                    mode="json"
                )
            )

        except Exception as exc:

            logger.warning(
                "Job validation failed: %s",
                exc,
            )

    if not processed_jobs:
        raise RuntimeError(
            "No valid jobs were produced."
        )

    # --------------------------------------------------
    # SAVE JOBS
    # --------------------------------------------------

    storage = JSONStorage(
        OUTPUT_FILE
    )

    storage.save(
        processed_jobs
    )

    logger.info(
        "Saved %s jobs to %s",
        len(processed_jobs),
        OUTPUT_FILE,
    )

    return processed_jobs


def save_jobs(
    jobs: list[dict],
) -> None:

    if not jobs:
        raise ValueError(
            "Refusing to save an empty job dataset."
        )

    storage = JSONStorage(
        OUTPUT_FILE
    )

    storage.save(
        jobs
    )

    logger.info(
        "Saved %s jobs to %s",
        len(jobs),
        OUTPUT_FILE,
    )


if __name__ == "__main__":

    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    jobs = asyncio.run(
        run_job_pipeline()
    )

    print(
        f"\nJOBS SAVED: {len(jobs)}"
    )