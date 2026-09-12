import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse


logger = logging.getLogger(__name__)


DATA_DIR = Path("data/output")


class DataQualityValidator:
    """
    Validates the final Frontier Atlas JSON datasets.

    Checks:
    - record counts
    - required fields
    - duplicate records
    - source URL validity
    - freshness of Jobs and News
    """

    def __init__(self, data_dir: str | Path = DATA_DIR):
        self.data_dir = Path(data_dir)
        self.errors: list[str] = []
        self.warnings: list[str] = []

    # --------------------------------------------------
    # File loading
    # --------------------------------------------------

    def load_file(self, filename: str) -> list[dict]:
        path = self.data_dir / filename

        if not path.exists():
            self.errors.append(
                f"Missing file: {path}"
            )
            return []

        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)

        except json.JSONDecodeError as exc:
            self.errors.append(
                f"Invalid JSON in {filename}: {exc}"
            )
            return []

        if not isinstance(data, list):
            self.errors.append(
                f"{filename} must contain a JSON list."
            )
            return []

        return data

    # --------------------------------------------------
    # URL validation
    # --------------------------------------------------

    def valid_url(self, value: str | None) -> bool:

        if not value:
            return False

        try:
            parsed = urlparse(value)

            return (
                parsed.scheme in {"http", "https"}
                and bool(parsed.netloc)
            )

        except Exception:
            return False

    # --------------------------------------------------
    # Duplicate check
    # --------------------------------------------------

    def check_duplicates(
        self,
        records: list[dict],
        dataset_name: str,
        key: str,
    ) -> int:

        seen = set()
        duplicates = 0

        for record in records:

            value = record.get(key)

            if not value:
                continue

            if value in seen:
                duplicates += 1

            else:
                seen.add(value)

        if duplicates:

            self.errors.append(
                f"{dataset_name}: "
                f"{duplicates} duplicate records "
                f"found using '{key}'."
            )

        return duplicates

    # --------------------------------------------------
    # Startup validation
    # --------------------------------------------------

    def validate_startups(
        self,
        records: list[dict],
    ) -> None:

        logger.info(
            "Validating Startups: %s records",
            len(records),
        )

        if len(records) < 1000:
            self.errors.append(
                f"Startups has only {len(records)} records. "
                "Minimum required: 1000."
            )

        for index, record in enumerate(
            records,
            start=1,
        ):

            if not record.get("entity_name"):
                self.errors.append(
                    f"Startups record {index}: "
                    "missing entity_name."
                )

            if not self.valid_url(
                record.get("source_url")
            ):
                self.errors.append(
                    f"Startups record {index}: "
                    "invalid source_url."
                )

        self.check_duplicates(
            records,
            "Startups",
            "source_url",
        )

    # --------------------------------------------------
    # Product validation
    # --------------------------------------------------

    def validate_products(
        self,
        records: list[dict],
    ) -> None:

        logger.info(
            "Validating Products: %s records",
            len(records),
        )

        if len(records) < 1000:
            self.errors.append(
                f"Products has only {len(records)} records. "
                "Minimum required: 1000."
            )

        for index, record in enumerate(
            records,
            start=1,
        ):

            if not record.get("product_name"):
                self.errors.append(
                    f"Products record {index}: "
                    "missing product_name."
                )

            if not self.valid_url(
                record.get("source_url")
            ):
                self.errors.append(
                    f"Products record {index}: "
                    "invalid source_url."
                )

        self.check_duplicates(
            records,
            "Products",
            "source_url",
        )

    # --------------------------------------------------
    # Research paper validation
    # --------------------------------------------------

    def validate_research_papers(
        self,
        records: list[dict],
    ) -> None:

        logger.info(
            "Validating Research Papers: %s records",
            len(records),
        )

        if len(records) < 1000:
            self.errors.append(
                f"Research Papers has only "
                f"{len(records)} records. "
                "Minimum required: 1000."
            )

        for index, record in enumerate(
            records,
            start=1,
        ):

            if not record.get("title"):
                self.errors.append(
                    f"Research Paper {index}: "
                    "missing title."
                )

            if not self.valid_url(
                record.get("paper_url")
            ):
                self.errors.append(
                    f"Research Paper {index}: "
                    "invalid paper_url."
                )

            if not record.get("arxiv_id"):
                self.warnings.append(
                    f"Research Paper {index}: "
                    "missing arxiv_id."
                )

            github_stars = record.get(
                "github_stars"
            )

            if github_stars is not None:

                if not isinstance(
                    github_stars,
                    int,
                ):
                    self.errors.append(
                        f"Research Paper {index}: "
                        "github_stars must be an integer."
                    )

                elif github_stars < 0:
                    self.errors.append(
                        f"Research Paper {index}: "
                        "github_stars cannot be negative."
                    )

        self.check_duplicates(
            records,
            "Research Papers",
            "arxiv_id",
        )

    # --------------------------------------------------
    # Job validation
    # --------------------------------------------------

    def validate_jobs(
        self,
        records: list[dict],
    ) -> None:

        logger.info(
            "Validating Jobs: %s records",
            len(records),
        )

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)

        for index, record in enumerate(
            records,
            start=1,
        ):

            if not record.get("job_title"):
                self.errors.append(
                    f"Job {index}: "
                    "missing job_title."
                )

            if not self.valid_url(
                record.get("source_url")
            ):
                self.errors.append(
                    f"Job {index}: "
                    "invalid source_url."
                )

            posted_at = self.parse_datetime(
                record.get("posted_at")
            )

            if posted_at is None:
                self.errors.append(
                    f"Job {index}: "
                    "invalid posted_at."
                )

            elif posted_at < cutoff:
                self.errors.append(
                    f"Job {index}: "
                    "posted_at is older than 24 hours."
                )

    # --------------------------------------------------
    # News validation
    # --------------------------------------------------

    def validate_news(
        self,
        records: list[dict],
    ) -> None:

        logger.info(
            "Validating News: %s records",
            len(records),
        )

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=24)

        for index, record in enumerate(
            records,
            start=1,
        ):

            if not record.get("title"):
                self.errors.append(
                    f"News {index}: "
                    "missing title."
                )

            if not self.valid_url(
                record.get("source_url")
            ):
                self.errors.append(
                    f"News {index}: "
                    "invalid source_url."
                )

            if not record.get("article_text"):
                self.warnings.append(
                    f"News {index}: "
                    "article_text is empty."
                )

            published_at = self.parse_datetime(
                record.get("published_at")
            )

            if published_at is None:
                self.errors.append(
                    f"News {index}: "
                    "invalid published_at."
                )

            elif published_at < cutoff:
                self.errors.append(
                    f"News {index}: "
                    "published_at is older than 24 hours."
                )

    # --------------------------------------------------
    # Entity mapping validation
    # --------------------------------------------------

    def validate_entity_mapping(
        self,
        records: list[dict],
    ) -> None:

        logger.info(
            "Validating Entity Mapping: %s records",
            len(records),
        )

        for index, record in enumerate(
            records,
            start=1,
        ):

            if not record.get("raw_name"):
                self.errors.append(
                    f"Entity Mapping {index}: "
                    "missing raw_name."
                )

            if not record.get("canonical_name"):
                self.errors.append(
                    f"Entity Mapping {index}: "
                    "missing canonical_name."
                )

        self.check_duplicates(
            records,
            "Entity Mapping",
            "raw_name",
        )

    # --------------------------------------------------
    # Datetime parser
    # --------------------------------------------------

    @staticmethod
    def parse_datetime(
        value: str | None,
    ) -> datetime | None:

        if not value:
            return None

        try:

            parsed = datetime.fromisoformat(
                value.replace(
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

        except (
            ValueError,
            TypeError,
        ):
            return None

    # --------------------------------------------------
    # Full validation
    # --------------------------------------------------

    def validate_all(self) -> dict:

        self.errors = []
        self.warnings = []

        startups = self.load_file(
            "startups.json"
        )

        products = self.load_file(
            "products.json"
        )

        research_papers = self.load_file(
            "research_papers.json"
        )

        jobs = self.load_file(
            "jobs.json"
        )

        news = self.load_file(
            "news.json"
        )

        entity_mapping = self.load_file(
            "entity_mapping_log.json"
        )

        self.validate_startups(
            startups
        )

        self.validate_products(
            products
        )

        self.validate_research_papers(
            research_papers
        )

        self.validate_jobs(
            jobs
        )

        self.validate_news(
            news
        )

        self.validate_entity_mapping(
            entity_mapping
        )

        return {
            "status": (
                "PASS"
                if not self.errors
                else "FAIL"
            ),
            "errors": self.errors,
            "warnings": self.warnings,
            "counts": {
                "startups": len(startups),
                "products": len(products),
                "research_papers": len(
                    research_papers
                ),
                "jobs": len(jobs),
                "news": len(news),
                "entity_mapping": len(
                    entity_mapping
                ),
            },
        }


def main():

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    validator = DataQualityValidator()

    report = validator.validate_all()

    print("\n" + "=" * 60)
    print("FRONTIER ATLAS DATA QUALITY REPORT")
    print("=" * 60)

    print(
        f"\nSTATUS: {report['status']}"
    )

    print("\nRECORD COUNTS:")

    for name, count in report[
        "counts"
    ].items():

        print(
            f"  {name}: {count}"
        )

    print(
        f"\nERRORS: "
        f"{len(report['errors'])}"
    )

    print(
        f"WARNINGS: "
        f"{len(report['warnings'])}"
    )

    if report["errors"]:

        print("\nERROR DETAILS:")

        for error in report[
            "errors"
        ][:20]:

            print(
                f"  - {error}"
            )

        if len(report["errors"]) > 20:

            print(
                f"  ... and "
                f"{len(report['errors']) - 20}"
                " more errors."
            )

    if report["warnings"]:

        print("\nWARNING DETAILS:")

        for warning in report[
            "warnings"
        ][:20]:

            print(
                f"  - {warning}"
            )

        if len(report["warnings"]) > 20:

            print(
                f"  ... and "
                f"{len(report['warnings']) - 20}"
                " more warnings."
            )

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()