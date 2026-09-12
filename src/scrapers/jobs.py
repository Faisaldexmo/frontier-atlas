import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from src.scrapers.base import BaseScraper


logger = logging.getLogger(__name__)


AI_KEYWORDS = [
    "artificial intelligence",
    "artificial-intelligence",
    "machine learning",
    "machine-learning",
    "deep learning",
    "deep-learning",
    "generative ai",
    "genai",
    "large language model",
    "llm",
    "ai engineer",
    "ai developer",
    "ai researcher",
    "machine learning engineer",
    "ml engineer",
    "computer vision",
    "natural language processing",
    "nlp",
    "robotics",
    "reinforcement learning",
    "prompt engineer",
]


class JobScraper:
    """
    Collect fresh AI jobs from public job APIs.
    """

    def __init__(
        self,
        scraper: BaseScraper | None = None,
    ):
        self.scraper = scraper or BaseScraper(
            max_concurrency=5,
            max_retries=3,
            timeout_seconds=60,
        )

    async def collect(
        self,
        max_jobs: int = 100,
    ) -> list[dict[str, Any]]:

        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(hours=24)
        )

        jobs: list[dict[str, Any]] = []

        sources = [
            (
                "Remotive",
                "https://remotive.com/api/remote-jobs",
            ),
            (
                "Remote OK",
                "https://remoteok.com/api",
            ),
            (
                "Jobicy",
                "https://jobicy.com/api/v2/remote-jobs?count=200",
            ),
            (
                "Himalayas",
                "https://himalayas.app/jobs/api/search?q=ai&sort=recent&page=1",
            ),
            (
                "Arbeitnow",
                "https://www.arbeitnow.com/api/job-board-api",
            ),
        ]

        for source_name, url in sources:

            if len(jobs) >= max_jobs:
                break

            logger.info(
                "Fetching %s",
                source_name,
            )

            try:

                raw = await self.scraper.fetch(
                    url
                )

                data = json.loads(
                    raw
                )

                if source_name == "Remotive":
                    source_jobs = (
                        self._remotive(
                            data,
                            cutoff,
                        )
                    )

                elif source_name == "Remote OK":
                    source_jobs = (
                        self._remote_ok(
                            data,
                            cutoff,
                        )
                    )

                elif source_name == "Jobicy":
                    source_jobs = (
                        self._jobicy(
                            data,
                            cutoff,
                        )
                    )

                elif source_name == "Himalayas":
                    source_jobs = (
                        self._himalayas(
                            data,
                            cutoff,
                        )
                    )

                else:
                    source_jobs = (
                        self._arbeitnow(
                            data,
                            cutoff,
                        )
                    )

                logger.info(
                    "%s -> %s fresh AI jobs",
                    source_name,
                    len(source_jobs),
                )

                jobs.extend(
                    source_jobs
                )

            except Exception as exc:

                logger.warning(
                    "%s failed: %s",
                    source_name,
                    exc,
                )

        jobs = self.deduplicate(
            jobs
        )

        jobs.sort(
            key=lambda job: job["posted_at"],
            reverse=True,
        )

        logger.info(
            "Total fresh AI jobs: %s",
            len(jobs),
        )

        return jobs[:max_jobs]

    def _remotive(
        self,
        data: dict,
        cutoff: datetime,
    ) -> list[dict[str, Any]]:

        results = []

        for item in data.get(
            "jobs",
            [],
        ):

            posted_at = self._date(
                item.get(
                    "publication_date"
                )
            )

            if not self._fresh(
                posted_at,
                cutoff,
            ):
                continue

            title = str(
                item.get(
                    "title",
                    "",
                )
            )

            description = str(
                item.get(
                    "description",
                    "",
                )
            )

            if not self._is_ai(
                title,
                description,
            ):
                continue

            url = item.get(
                "url"
            )

            if not url:
                continue

            results.append(
                self._record(
                    "Remotive",
                    url,
                    item.get(
                        "company_name"
                    ),
                    title,
                    item.get(
                        "candidate_required_location"
                    ),
                    description,
                    posted_at,
                )
            )

        return results

    def _remote_ok(
        self,
        data: list,
        cutoff: datetime,
    ) -> list[dict[str, Any]]:

        results = []

        for item in data:

            if not isinstance(
                item,
                dict,
            ):
                continue

            posted_at = self._date(
                item.get(
                    "date"
                )
            )

            if not self._fresh(
                posted_at,
                cutoff,
            ):
                continue

            title = str(
                item.get(
                    "position",
                    "",
                )
            )

            description = str(
                item.get(
                    "description",
                    "",
                )
            )

            tags = str(
                item.get(
                    "tags",
                    "",
                )
            )

            if not self._is_ai(
                title,
                description,
                tags,
            ):
                continue

            url = item.get(
                "url"
            )

            if not url:
                continue

            results.append(
                self._record(
                    "Remote OK",
                    url,
                    item.get(
                        "company"
                    ),
                    title,
                    item.get(
                        "location"
                    ),
                    description,
                    posted_at,
                )
            )

        return results

    def _jobicy(
        self,
        data: dict,
        cutoff: datetime,
    ) -> list[dict[str, Any]]:

        results = []

        for item in data.get(
            "jobs",
            [],
        ):

            posted_at = self._date(
                item.get(
                    "pubDate"
                )
            )

            if not self._fresh(
                posted_at,
                cutoff,
            ):
                continue

            title = str(
                item.get(
                    "jobTitle",
                    "",
                )
            )

            description = str(
                item.get(
                    "jobDescription",
                    "",
                )
            )

            industry = str(
                item.get(
                    "jobIndustry",
                    "",
                )
            )

            if not self._is_ai(
                title,
                description,
                industry,
            ):
                continue

            url = item.get(
                "url"
            )

            if not url:
                continue

            results.append(
                self._record(
                    "Jobicy",
                    url,
                    item.get(
                        "companyName"
                    ),
                    title,
                    item.get(
                        "jobGeo"
                    ),
                    description,
                    posted_at,
                )
            )

        return results

    def _himalayas(
        self,
        data: dict,
        cutoff: datetime,
    ) -> list[dict[str, Any]]:

        results = []

        for item in data.get(
            "jobs",
            [],
        ):

            posted_at = self._date(
                item.get(
                    "pubDate"
                )
            )

            if not self._fresh(
                posted_at,
                cutoff,
            ):
                continue

            title = str(
                item.get(
                    "title",
                    "",
                )
            )

            description = str(
                item.get(
                    "description",
                    "",
                )
            )

            categories = str(
                item.get(
                    "categories",
                    "",
                )
            )

            if not self._is_ai(
                title,
                description,
                categories,
            ):
                continue

            url = item.get(
                "applicationLink"
            )

            if not url:
                continue

            results.append(
                self._record(
                    "Himalayas",
                    url,
                    item.get(
                        "companyName"
                    ),
                    title,
                    "Worldwide",
                    description,
                    posted_at,
                )
            )

        return results

    def _arbeitnow(
        self,
        data: dict,
        cutoff: datetime,
    ) -> list[dict[str, Any]]:

        results = []

        for item in data.get(
            "data",
            [],
        ):

            posted_at = self._date(
                item.get(
                    "created_at"
                )
            )

            if not self._fresh(
                posted_at,
                cutoff,
            ):
                continue

            title = str(
                item.get(
                    "title",
                    "",
                )
            )

            description = str(
                item.get(
                    "description",
                    "",
                )
            )

            tags = str(
                item.get(
                    "tags",
                    "",
                )
            )

            if not self._is_ai(
                title,
                description,
                tags,
            ):
                continue

            url = item.get(
                "url"
            )

            if not url:
                continue

            results.append(
                self._record(
                    "Arbeitnow",
                    url,
                    item.get(
                        "company_name"
                    ),
                    title,
                    item.get(
                        "location"
                    ),
                    description,
                    posted_at,
                )
            )

        return results

    @staticmethod
    def _is_ai(
        title: str,
        description: str = "",
        tags: str = "",
    ) -> bool:

        title = title.lower()
        description = description.lower()
        tags = tags.lower()

        # Strong AI title signal.
        if any(
            keyword in title
            for keyword in AI_KEYWORDS
        ):
            return True

        # Strong AI signals in body/tags.
        combined = (
            description
            + " "
            + tags
        )

        matches = 0

        for keyword in AI_KEYWORDS:

            if keyword in combined:
                matches += 1

        return matches >= 2

    @staticmethod
    def _fresh(
        posted_at: datetime | None,
        cutoff: datetime,
    ) -> bool:

        if posted_at is None:
            return False

        now = datetime.now(
            timezone.utc
        )

        if posted_at > now:
            return False

        return posted_at >= cutoff

    @staticmethod
    def _date(
        value: Any,
    ) -> datetime | None:

        if value is None:
            return None

        if isinstance(
            value,
            (int, float),
        ):

            try:

                timestamp = float(
                    value
                )

                if timestamp > 10_000_000_000:
                    timestamp /= 1000

                return datetime.fromtimestamp(
                    timestamp,
                    timezone.utc,
                )

            except (
                ValueError,
                OverflowError,
                OSError,
            ):
                return None

        text = str(
            value
        ).strip()

        if not text:
            return None

        try:

            parsed = datetime.fromisoformat(
                text.replace(
                    "Z",
                    "+00:00",
                )
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                timezone.utc
            )

        except ValueError:
            return None

    @staticmethod
    def _record(
        source_name: str,
        source_url: str,
        company_name: str | None,
        job_title: str,
        location: str | None,
        description: str | None,
        posted_at: datetime | None,
    ) -> dict[str, Any]:

        return {
            "schemaVersion": "1.0",
            "recordType": "JOB",
            "source_name": source_name,
            "source_url": source_url,
            "company_name": company_name,
            "job_title": job_title.strip(),
            "location": location,
            "description": description,
            "posted_at": posted_at,
            "collected_at": datetime.now(
                timezone.utc
            ),
        }

    @staticmethod
    def deduplicate(
        jobs: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        unique = {}

        for job in jobs:

            url = (
                job["source_url"]
                .strip()
                .lower()
                .rstrip("/")
            )

            if url not in unique:
                unique[url] = job

        return list(
            unique.values()
        )