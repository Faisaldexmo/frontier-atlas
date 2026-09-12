import logging
import re
from typing import Optional

from src.scrapers.base import BaseScraper


logger = logging.getLogger(__name__)


GITHUB_URL_PATTERN = re.compile(
    r"https?://github\.com/[\w.-]+/[\w.-]+"
)


class GitHubResolver:
    """
    Resolve a research paper to a GitHub repository.

    GitHub enrichment is best-effort. If the GitHub API rate
    limit is reached, the resolver stops making further GitHub
    requests so the main pipeline can continue safely.
    """

    def __init__(
        self,
        scraper: Optional[BaseScraper] = None,
    ):
        self.scraper = scraper or BaseScraper(
            max_concurrency=3,
            max_retries=2,
        )

        self.rate_limited = False

    @staticmethod
    def extract_github_url(
        text: str,
    ) -> Optional[str]:
        """
        Extract the first GitHub repository URL from text.
        """

        if not text:
            return None

        match = GITHUB_URL_PATTERN.search(text)

        if not match:
            return None

        return match.group(0).rstrip(
            ".,;:)"
        )

    @staticmethod
    def tokenize(text: str) -> set[str]:
        """
        Convert text into normalized tokens.
        """

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
    ) -> float:
        """
        Calculate a simple token-overlap confidence score.
        """

        paper_tokens = cls.tokenize(
            paper_title
        )

        repo_tokens = cls.tokenize(
            f"{repo_name} {repo_description}"
        )

        if not paper_tokens:
            return 0.0

        overlap = paper_tokens.intersection(
            repo_tokens
        )

        return len(overlap) / len(
            paper_tokens
        )

    async def _fetch_json(
        self,
        url: str,
    ) -> Optional[dict]:
        """
        Fetch JSON while handling GitHub rate limits.

        Once a rate limit is detected, all future GitHub
        requests are skipped for this pipeline run.
        """

        if self.rate_limited:
            return None

        try:
            response = await self.scraper.fetch(
                url
            )

            import json

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
                    "Skipping remaining GitHub enrichment."
                )

                return None

            if "429" in error_text:
                self.rate_limited = True

                logger.warning(
                    "GitHub API returned 429. "
                    "Skipping remaining GitHub enrichment."
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
        """
        Fetch repository metadata from GitHub.
        """

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

        data = await self._fetch_json(
            api_url
        )

        if not data:
            return None

        return data

    async def resolve(
        self,
        paper_title: str,
        paper_summary: str = "",
    ) -> dict:
        """
        Resolve a paper to GitHub repository metadata.
        """

        empty_result = {
            "github_url": None,
            "github_stars": None,
            "github_confidence": 0.0,
        }

        if self.rate_limited:
            return empty_result

        combined_text = (
            f"{paper_title}\n"
            f"{paper_summary}"
        )

        direct_url = self.extract_github_url(
            combined_text
        )

        if direct_url:
            logger.info(
                "Found GitHub URL directly in paper: %s",
                direct_url,
            )

            repository = await self._get_repository(
                direct_url
            )

            if repository:
                return {
                    "github_url": direct_url,
                    "github_stars": repository.get(
                        "stargazers_count"
                    ),
                    "github_confidence": 1.0,
                }

            return empty_result

        logger.info(
            "Searching GitHub for: %s",
            paper_title,
        )

        if self.rate_limited:
            return empty_result

        import urllib.parse

        encoded_title = urllib.parse.quote(
            f'"{paper_title}"'
        )

        search_url = (
            "https://api.github.com/search/repositories"
            f"?q={encoded_title}"
            "&sort=stars"
            "&order=desc"
            "&per_page=5"
        )

        search_data = await self._fetch_json(
            search_url
        )

        if not search_data:
            return empty_result

        repositories = search_data.get(
            "items",
            []
        )

        if not repositories:
            return empty_result

        best_repository = None
        best_confidence = 0.0

        for repository in repositories:
            confidence = self.confidence_score(
                paper_title,
                repository.get(
                    "name",
                    "",
                ),
                repository.get(
                    "description",
                    "",
                ) or "",
            )

            if confidence > best_confidence:
                best_confidence = confidence
                best_repository = repository

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

        repository_data = await self._fetch_json(
            "https://api.github.com/repos/"
            f"{repo_full_name}"
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