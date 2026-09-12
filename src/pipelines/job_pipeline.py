import logging

from src.entity.job import Job
from src.scrapers.jobs import JobScraper
from src.storage.json_storage import JSONStorage


logger = logging.getLogger(__name__)


OUTPUT_FILE = (
    "data/output/jobs.json"
)


async def run_job_pipeline(
    max_jobs: int = 100,
) -> list[dict]:

    scraper = JobScraper()

    jobs = await scraper.collect(
        max_jobs=max_jobs
    )

    if not jobs:
        raise RuntimeError(
            "No fresh jobs were collected."
        )

    jobs = scraper.deduplicate(
        jobs
    )

    validated_jobs = []

    for index, job in enumerate(
        jobs,
        start=1,
    ):

        try:

            validated = Job(
                **job
            )

            validated_jobs.append(
                validated.model_dump(
                    mode="json"
                )
            )

            logger.info(
                "Validated %s/%s: %s",
                index,
                len(jobs),
                job["job_title"],
            )

        except Exception as exc:

            logger.error(
                "Job validation failed "
                "for %s: %s",
                job.get(
                    "job_title",
                    "Unknown",
                ),
                exc,
            )

    if not validated_jobs:
        raise RuntimeError(
            "No valid job records."
        )

    return validated_jobs


def save_jobs(
    jobs: list[dict],
) -> None:

    if not jobs:
        raise ValueError(
            "Refusing to save empty "
            "job data."
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