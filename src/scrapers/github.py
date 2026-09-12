import json
import logging
import os
import re
import urllib.parse
from typing import Optional

from dotenv import load_dotenv

from src.scrapers.base import BaseScraper

load_dotenv()

logger = logging.getLogger(__name__)

GITHUB_URL_PATTERN = re.compile(
    r"https?://github\.com/[\w.-]+/[\w.-]+"
)


class GitHubResolver:
    """
    Resolve research papers to legitimate GitHub repositories.

    Matching strategy:
    1. Direct GitHub URL found in source text.
    2. Exact paper-title repository search.
    3. Normalized/keyword repository search.
    4. Deterministic confidence scoring.
    5. Current GitHub stars fetched from repository API.

    No repository is attached unless the match passes
    the confidence threshold.
    """

    def __init__(
        self,
        scraper: Optional[BaseScraper] = None,
    ):
        self.scraper = scraper or BaseScraper(
            max_concurrency=2,
            max_retries=2,
        )

        self.rate_limited = False

        self.github_headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        github_token = os.getenv("GITHUB_TOKEN")

        if github_token:
            self.github_headers[
                "Authorization"
            ] = f"Bearer {github_token}"

            logger.info(
                "GitHub authentication enabled."
            )
        else:
            logger.warning(
                "GITHUB_TOKEN is not configured."
            )

    @staticmethod
    def extract_github_url(text: str) -> Optional[str]:
        if not text:
            return None

        match = GITHUB_URL_PATTERN.search(text)

        if not match:
            return None

        return match.group(0).rstrip(
            ".,;:)"
        )

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize text for deterministic comparison.
        """
        if not text:
            return ""

        text = text.lower()

        text = re.sub(
            r"[^a-z0-9\s]",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    @staticmethod
    def tokenize(text: str) -> set[str]:
        if not text:
            return set()

        words = re.findall(
            r"[a-zA-Z0-9]+",
            text.lower(),
        )

        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "using",
            "based",
            "into",
            "toward",
            "towards",
            "via",
            "on",
            "of",
            "in",
            "to",
            "a",
            "an",
            "by",
            "through",
            "towards",
            "model",
            "models",
            "learning",
            "large",
            "language",
        }

        return {
            word
            for word in words
            if len(word) >= 3
            and word not in stop_words
        }

    @classmethod
    def confidence_score(
        cls,
        paper_title: str,
        repo_name: str,
        repo_description: str = "",
        repo_topics: Optional[list[str]] = None,
    ) -> float:

        paper_tokens = cls.tokenize(
            paper_title
        )

        repo_text = " ".join(
            [
                repo_name or "",
                repo_description or "",
                " ".join(repo_topics or []),
            ]
        )

        repo_tokens = cls.tokenize(
            repo_text
        )

        if not paper_tokens:
            return 0.0

        overlap = paper_tokens.intersection(
            repo_tokens
        )

        token_score = (
            len(overlap)
            / len(paper_tokens)
        )

        normalized_title = cls.normalize(
            paper_title
        )

        normalized_repo = cls.normalize(
            repo_name
        )

        name_score = 0.0

        if (
            normalized_title
            and normalized_title == normalized_repo
        ):
            name_score = 1.0

        elif (
            normalized_repo
            and normalized_repo in normalized_title
        ):
            name_score = 0.8

        elif (
            normalized_title
            and normalized_title in normalized_repo
        ):
            name_score = 0.8

        return round(
            max(
                token_score,
                name_score,
            ),
            3,
        )

    @staticmethod
    def build_search_terms(
        paper_title: str,
    ) -> list[str]:

        tokens = re.findall(
            r"[a-zA-Z0-9]+",
            paper_title.lower(),
        )

        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "from",
            "using",
            "based",
            "into",
            "toward",
            "towards",
            "via",
            "on",
            "of",
            "in",
            "to",
            "a",
            "an",
            "by",
            "through",
            "model",
            "models",
            "large",
            "language",
            "learning",
        }

        meaningful = [
            word
            for word in tokens
            if len(word) >= 4
            and word not in stop_words
        ]

        # Keep the most descriptive terms.
        meaningful = meaningful[:8]

        if not meaningful:
            return []

        searches = []

        # Search using all meaningful terms.
        searches.append(
            " ".join(meaningful)
        )

        # Also search the strongest first terms.
        if len(meaningful) >= 4:
            searches.append(
                " ".join(
                    meaningful[:4]
                )
            )

        return list(
            dict.fromkeys(searches)
        )

    async def _fetch_json(
        self,
        url: str,
    ) -> Optional[dict]:

        if self.rate_limited:
            return None

        try:
            response = await self.scraper.fetch(
                url,
                headers=self.github_headers,
            )

            return json.loads(response)

        except Exception as exc:

            error_text = str(exc).lower()

            if (
                "403" in error_text
                or "rate limit" in error_text
            ):
                self.rate_limited = True

                logger.warning(
                    "GitHub API rate limit reached. "
                    "Stopping GitHub enrichment."
                )

                return None

            if "429" in error_text:

                self.rate_limited = True

                logger.warning(
                    "GitHub API returned 429. "
                    "Stopping GitHub enrichment."
                )

                return None

            logger.warning(
                "GitHub request failed: %s",
                exc,
            )

            return None

    async def _get_repository(
        self,
        repo_url: str,
    ) -> Optional[dict]:

        if self.rate_limited:
            return None

        parts = repo_url.rstrip(
            "/"
        ).split("/")

        if len(parts) < 2:
            return None

        owner = parts[-2]
        repo = parts[-1]

        api_url = (
            "https://api.github.com/repos/"
            f"{owner}/{repo}"
        )

        return await self._fetch_json(
            api_url
        )

    async def _search_repositories(
        self,
        query: str,
    ) -> list[dict]:

        if self.rate_limited:
            return []

        encoded_query = urllib.parse.quote(
            query
        )

        search_url = (
            "https://api.github.com/search/repositories"
            f"?q={encoded_query}"
            "&sort=stars"
            "&order=desc"
            "&per_page=10"
        )

        search_data = await self._fetch_json(
            search_url
        )

        if not search_data:
            return []

        return search_data.get(
            "items",
            [],
        )

    async def resolve(
        self,
        paper_title: str,
        paper_summary: str = "",
    ) -> dict:

        empty_result = {
            "github_url": None,
            "github_stars": None,
            "github_confidence": 0.0,
        }

        if self.rate_limited:
            return empty_result

        if not paper_title.strip():
            return empty_result

        # --------------------------------------------------
        # STEP 1: Direct GitHub URL
        # --------------------------------------------------

        combined_text = (
            f"{paper_title}\n"
            f"{paper_summary}"
        )

        direct_url = (
            self.extract_github_url(
                combined_text
            )
        )

        if direct_url:

            logger.info(
                "Direct GitHub URL found: %s",
                direct_url,
            )

            repository = (
                await self._get_repository(
                    direct_url
                )
            )

            if repository:

                return {
                    "github_url": direct_url,
                    "github_stars": repository.get(
                        "stargazers_count"
                    ),
                    "github_confidence": 1.0,
                }

        # --------------------------------------------------
        # STEP 2: Search GitHub
        # --------------------------------------------------

        search_terms = (
            self.build_search_terms(
                paper_title
            )
        )

        if not search_terms:
            return empty_result

        all_repositories = {}

        for query in search_terms:

            repositories = (
                await self._search_repositories(
                    query
                )
            )

            for repository in repositories:

                full_name = repository.get(
                    "full_name"
                )

                if full_name:
                    all_repositories[
                        full_name
                    ] = repository

            if self.rate_limited:
                return empty_result

        if not all_repositories:
            return empty_result

        # --------------------------------------------------
        # STEP 3: Deterministic scoring
        # --------------------------------------------------

        best_repository = None
        best_confidence = 0.0

        for repository in (
            all_repositories.values()
        ):

            confidence = (
                self.confidence_score(
                    paper_title,
                    repository.get(
                        "name",
                        "",
                    ),
                    repository.get(
                        "description",
                        "",
                    )
                    or "",
                    repository.get(
                        "topics",
                        [],
                    ),
                )
            )

            if (
                confidence
                > best_confidence
            ):
                best_confidence = (
                    confidence
                )

                best_repository = (
                    repository
                )

        # Strong threshold to prevent
        # unrelated repositories.
        if (
            best_repository is None
            or best_confidence < 0.45
        ):
            return empty_result

        repo_full_name = (
            best_repository.get(
                "full_name"
            )
        )

        if not repo_full_name:
            return empty_result

        repo_url = (
            "https://github.com/"
            f"{repo_full_name}"
        )

        # --------------------------------------------------
        # STEP 4: Fetch current repository metrics
        # --------------------------------------------------

        repository_data = (
            await self._fetch_json(
                "https://api.github.com/repos/"
                f"{repo_full_name}"
            )
        )

        if not repository_data:
            return empty_result

        return {
            "github_url": repo_url,
            "github_stars": repository_data.get(
                "stargazers_count"
            ),
            "github_confidence": round(
                best_confidence,
                2,
            ),
        }