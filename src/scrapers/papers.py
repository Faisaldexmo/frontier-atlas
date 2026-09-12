import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any

from src.scrapers.base import BaseScraper


logger = logging.getLogger(__name__)


ARXIV_API = (
    "https://export.arxiv.org/api/query"
)


class ArxivPaperScraper:
    """
    Fetch research papers from the Arxiv API.

    Supports pagination through start_offset so that
    existing papers can be preserved and only new
    papers can be collected.
    """

    def __init__(
        self,
        scraper: BaseScraper | None = None,
    ):
        self.scraper = scraper or BaseScraper(
            max_concurrency=2,
            max_retries=3,
            timeout_seconds=60,
        )

    async def collect(
        self,
        max_papers: int = 1000,
        start_offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Collect research papers from Arxiv.

        max_papers:
            Number of papers to collect.

        start_offset:
            Arxiv result offset from which collection starts.
        """

        papers: list[dict[str, Any]] = []

        batch_size = 100

        for batch_number in range(
            0,
            max_papers,
            batch_size,
        ):
            current_size = min(
                batch_size,
                max_papers - batch_number,
            )

            current_offset = (
                start_offset + batch_number
            )

            logger.info(
                "Fetching Arxiv batch: "
                "start=%s size=%s",
                current_offset,
                current_size,
            )

            url = (
                f"{ARXIV_API}"
                f"?search_query=cat:cs.AI"
                f"&start={current_offset}"
                f"&max_results={current_size}"
                f"&sortBy=submittedDate"
                f"&sortOrder=descending"
            )

            try:
                xml_data = await self.scraper.fetch(
                    url
                )

                batch = self._parse_response(
                    xml_data
                )

                if not batch:
                    logger.warning(
                        "Arxiv returned an empty batch "
                        "at start=%s",
                        current_offset,
                    )
                    break

                papers.extend(batch)

                logger.info(
                    "Collected %s new papers so far",
                    len(papers),
                )

            except Exception as exc:
                logger.error(
                    "Arxiv batch failed: %r",
                    exc,
                )

                if not papers:
                    raise RuntimeError(
                        "Arxiv collection failed before "
                        "any new papers were collected."
                    ) from exc

                logger.warning(
                    "Stopping Arxiv collection after "
                    "collecting %s new papers.",
                    len(papers),
                )

                break

            # Give Arxiv API some breathing room.
            if (
                batch_number + current_size
                < max_papers
            ):
                logger.info(
                    "Waiting 3 seconds before "
                    "next Arxiv batch..."
                )

                await asyncio.sleep(3)

        if not papers:
            raise RuntimeError(
                "No research papers were collected "
                "from Arxiv."
            )

        return papers[:max_papers]

    def _parse_response(
        self,
        xml_data: str,
    ) -> list[dict[str, Any]]:
        """
        Parse Arxiv Atom XML response.
        """

        root = ET.fromstring(
            xml_data
        )

        namespace = {
            "atom": (
                "http://www.w3.org/2005/Atom"
            )
        }

        papers: list[dict[str, Any]] = []

        for entry in root.findall(
            "atom:entry",
            namespace,
        ):
            title_element = entry.find(
                "atom:title",
                namespace,
            )

            id_element = entry.find(
                "atom:id",
                namespace,
            )

            published_element = entry.find(
                "atom:published",
                namespace,
            )

            summary_element = entry.find(
                "atom:summary",
                namespace,
            )

            if title_element is None:
                continue

            if id_element is None:
                continue

            title = (
                title_element.text or ""
            ).strip()

            paper_url = (
                id_element.text or ""
            ).strip()

            summary = ""

            if summary_element is not None:
                summary = (
                    summary_element.text or ""
                ).strip()

            arxiv_id = (
                paper_url.rstrip("/")
                .split("/")[-1]
            )

            published_date = None

            if published_element is not None:
                published_text = (
                    published_element.text or ""
                ).strip()

                if published_text:
                    try:
                        published_date = (
                            datetime.fromisoformat(
                                published_text.replace(
                                    "Z",
                                    "+00:00",
                                )
                            )
                        )
                    except ValueError:
                        published_date = None

            authors = []

            for author in entry.findall(
                "atom:author",
                namespace,
            ):
                name_element = author.find(
                    "atom:name",
                    namespace,
                )

                if (
                    name_element is not None
                    and name_element.text
                ):
                    authors.append(
                        name_element.text.strip()
                    )

            papers.append(
                {
                    "title": title,
                    "authors": authors,
                    "paper_url": paper_url,
                    "arxiv_id": arxiv_id,
                    "published_date": published_date,
                    "summary": summary,
                    "github_url": None,
                    "github_stars": None,
                    "github_confidence": 0.0,
                }
            )

        return papers