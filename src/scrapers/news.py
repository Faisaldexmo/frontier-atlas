import logging
import re
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from src.scrapers.base import BaseScraper


logger = logging.getLogger(__name__)


AI_KEYWORDS = [
    "artificial intelligence",
    "artificial-intelligence",
    "machine learning",
    "machine-learning",
    "generative ai",
    "generative-ai",
    "genai",
    "large language model",
    "llm",
    "openai",
    "anthropic",
    "google deepmind",
    "deepmind",
    "gemini",
    "chatgpt",
    "claude",
    "copilot",
    "computer vision",
    "natural language processing",
    "robotics",
    "ai model",
    "ai models",
]


NEWS_SOURCES = [
    (
        "TechCrunch",
        "https://techcrunch.com/tag/artificial-intelligence/feed/",
    ),
    (
        "VentureBeat",
        "https://venturebeat.com/category/ai/feed/",
    ),
    (
        "The Verge",
        "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    ),
    (
        "WIRED",
        "https://www.wired.com/feed/tag/ai/latest/rss",
    ),
    (
        "Ars Technica",
        "https://arstechnica.com/ai/feed/",
    ),
]


class ArticleTextParser(HTMLParser):
    """
    Simple HTML article text extractor.
    """

    def __init__(self):
        super().__init__()

        self.in_article = False
        self.in_main = False
        self.skip = False

        self.parts: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ):

        tag = tag.lower()

        if tag in {
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
            "header",
        }:
            self.skip = True
            return

        if tag == "article":
            self.in_article = True

        if tag == "main":
            self.in_main = True

    def handle_endtag(
        self,
        tag: str,
    ):

        tag = tag.lower()

        if tag in {
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
            "header",
        }:
            self.skip = False

        if tag == "article":
            self.in_article = False

        if tag == "main":
            self.in_main = False

    def handle_data(
        self,
        data: str,
    ):

        if self.skip:
            return

        if not (
            self.in_article
            or self.in_main
        ):
            return

        text = data.strip()

        if text:
            self.parts.append(text)

    def text(self) -> str:

        text = " ".join(
            self.parts
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()


class NewsScraper:

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
        max_news: int = 100,
    ) -> list[dict[str, Any]]:

        cutoff = (
            datetime.now(timezone.utc)
            - timedelta(hours=24)
        )

        all_news: list[
            dict[str, Any]
        ] = []

        for source_name, feed_url in NEWS_SOURCES:

            logger.info(
                "Fetching news from %s",
                source_name,
            )

            try:

                raw = await self.scraper.fetch(
                    feed_url
                )

                items = self._parse_feed(
                    raw
                )

                logger.info(
                    "%s -> %s feed items",
                    source_name,
                    len(items),
                )

                for item in items:

                    published_at = self._parse_date(
                        item.get(
                            "published_at"
                        )
                    )

                    if not self._is_fresh(
                        published_at,
                        cutoff,
                    ):
                        continue

                    title = str(
                        item.get(
                            "title",
                            "",
                        )
                    ).strip()

                    description = str(
                        item.get(
                            "description",
                            "",
                        )
                    ).strip()

                    url = str(
                        item.get(
                            "url",
                            "",
                        )
                    ).strip()

                    if not title or not url:
                        continue

                    combined = (
                        title
                        + " "
                        + description
                    ).lower()

                    if not self._is_ai_news(
                        combined
                    ):
                        continue

                    article_text = (
                        await self._fetch_article_text(
                            url
                        )
                    )

                    if not article_text:
                        article_text = description

                    all_news.append(
                        self._build_record(
                            source_name=source_name,
                            source_url=url,
                            title=title,
                            description=description,
                            article_text=article_text,
                            published_at=published_at,
                        )
                    )

            except Exception as exc:

                logger.warning(
                    "Failed to fetch %s: %s",
                    source_name,
                    exc,
                )

        unique_news = self.deduplicate(
            all_news
        )

        unique_news.sort(
            key=lambda item: item["published_at"],
            reverse=True,
        )

        logger.info(
            "Total fresh AI news: %s",
            len(unique_news),
        )

        return unique_news[:max_news]

    def _parse_feed(
        self,
        raw: str,
    ) -> list[dict[str, Any]]:

        root = ET.fromstring(
            raw
        )

        results = []

        # RSS
        for item in root.findall(
            ".//item"
        ):

            title = self._xml_text(
                item,
                "title",
            )

            url = self._xml_text(
                item,
                "link",
            )

            description = self._xml_text(
                item,
                "description",
            )

            published = (
                self._xml_text(
                    item,
                    "pubDate",
                )
                or self._xml_text(
                    item,
                    "published",
                )
            )

            results.append(
                {
                    "title": title,
                    "url": url,
                    "description": description,
                    "published_at": published,
                }
            )

        # Atom
        if not results:

            namespace = (
                "{http://www.w3.org/2005/Atom}"
            )

            for entry in root.findall(
                f".//{namespace}entry"
            ):

                title = self._child_text(
                    entry,
                    f"{namespace}title",
                )

                description = (
                    self._child_text(
                        entry,
                        f"{namespace}summary",
                    )
                    or self._child_text(
                        entry,
                        f"{namespace}content",
                    )
                )

                published = (
                    self._child_text(
                        entry,
                        f"{namespace}published",
                    )
                    or self._child_text(
                        entry,
                        f"{namespace}updated",
                    )
                )

                url = ""

                for link in entry.findall(
                    f"{namespace}link"
                ):

                    href = link.attrib.get(
                        "href"
                    )

                    rel = link.attrib.get(
                        "rel",
                        "alternate",
                    )

                    if href and rel == "alternate":
                        url = href
                        break

                results.append(
                    {
                        "title": title,
                        "url": url,
                        "description": description,
                        "published_at": published,
                    }
                )

        return results

    @staticmethod
    def _xml_text(
        element: ET.Element,
        name: str,
    ) -> str:

        child = element.find(
            name
        )

        if child is None:
            return ""

        return "".join(
            child.itertext()
        ).strip()

    @staticmethod
    def _child_text(
        element: ET.Element,
        name: str,
    ) -> str:

        child = element.find(
            name
        )

        if child is None:
            return ""

        return "".join(
            child.itertext()
        ).strip()

    async def _fetch_article_text(
        self,
        url: str,
    ) -> str:

        try:

            html = await self.scraper.fetch(
                url
            )

            parser = ArticleTextParser()

            parser.feed(
                html
            )

            text = parser.text()

            # Keep output manageable.
            if len(text) > 30000:
                text = text[:30000]

            return text

        except Exception as exc:

            logger.warning(
                "Article text fetch failed for %s: %s",
                url,
                exc,
            )

            return ""

    @staticmethod
    def _is_ai_news(
        text: str,
    ) -> bool:

        text = text.lower()

        return any(
            keyword in text
            for keyword in AI_KEYWORDS
        )

    @staticmethod
    def _is_fresh(
        published_at: datetime | None,
        cutoff: datetime,
    ) -> bool:

        if published_at is None:
            return False

        now = datetime.now(
            timezone.utc
        )

        if published_at > now:
            return False

        return published_at >= cutoff

    @staticmethod
    def _parse_date(
        value: Any,
    ) -> datetime | None:

        if value is None:
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
            pass

        formats = [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%d %H:%M:%S",
        ]

        for fmt in formats:

            try:

                parsed = datetime.strptime(
                    text,
                    fmt,
                )

                if parsed.tzinfo is None:

                    parsed = parsed.replace(
                        tzinfo=timezone.utc
                    )

                return parsed.astimezone(
                    timezone.utc
                )

            except ValueError:
                continue

        return None

    @staticmethod
    def _build_record(
        source_name: str,
        source_url: str,
        title: str,
        description: str,
        article_text: str,
        published_at: datetime | None,
    ) -> dict[str, Any]:

        return {
            "schemaVersion": "1.0",
            "recordType": "NEWS",
            "source_name": source_name,
            "source_url": source_url,
            "title": title,
            "description": description,
            "article_text": article_text,
            "published_at": published_at,
            "collected_at": datetime.now(
                timezone.utc
            ),
        }

    @staticmethod
    def deduplicate(
        news: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        unique = {}

        for item in news:

            key = (
                item["source_url"]
                .strip()
                .lower()
                .rstrip("/")
            )

            if key not in unique:

                unique[key] = item

        return list(
            unique.values()
        )