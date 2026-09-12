import asyncio
import logging
import random
import ssl
from typing import Iterable, Optional

import aiohttp
import certifi
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)


logger = logging.getLogger(__name__)


class BaseScraper:
    """
    Base asynchronous HTTP scraper.

    Features:
    - Async HTTP requests
    - Concurrency control
    - Automatic retries
    - Exponential backoff
    - 429 rate-limit handling
    - Retry-After support
    - SSL certificate verification
    - Custom User-Agent
    - Optional per-request headers
    """

    def __init__(
        self,
        max_concurrency: int = 5,
        max_retries: int = 3,
        timeout_seconds: int = 30,
    ):
        self.max_concurrency = max_concurrency
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

        self.semaphore = asyncio.Semaphore(
            max_concurrency
        )

        self.ssl_context = ssl.create_default_context(
            cafile=certifi.where()
        )

        self.headers = {
            "User-Agent": (
                "Frontier-Atlas/1.0 "
                "(Research Intelligence System)"
            ),
            "Accept": "*/*",
        }

    async def _request(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Perform one HTTP GET request.

        Optional headers allow authenticated APIs such as
        GitHub to provide their own credentials without
        exposing those credentials to unrelated websites.
        """

        request_headers = dict(self.headers)

        if headers:
            request_headers.update(headers)

        timeout = aiohttp.ClientTimeout(
            total=self.timeout_seconds
        )

        connector = aiohttp.TCPConnector(
            limit=self.max_concurrency,
            limit_per_host=self.max_concurrency,
            ttl_dns_cache=300,
            ssl=self.ssl_context,
        )

        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=request_headers,
        ) as session:

            async with session.get(
                url
            ) as response:

                if response.status == 429:
                    retry_after = response.headers.get(
                        "Retry-After"
                    )

                    if retry_after:
                        try:
                            wait_seconds = int(
                                retry_after
                            )
                        except ValueError:
                            wait_seconds = 5
                    else:
                        wait_seconds = 5

                    logger.warning(
                        "Rate limited (429). "
                        "Waiting %s seconds.",
                        wait_seconds,
                    )

                    await asyncio.sleep(
                        wait_seconds
                    )

                    raise RuntimeError(
                        "429 Too Many Requests"
                    )

                if response.status >= 500:
                    raise RuntimeError(
                        f"Server error: "
                        f"{response.status}"
                    )

                response.raise_for_status()

                return await response.text()

    async def fetch(
        self,
        url: str,
        headers: Optional[dict[str, str]] = None,
    ) -> str:
        """
        Fetch a URL with concurrency control
        and automatic retries.
        """

        logger.info(
            "Fetching: %s",
            url,
        )

        async with self.semaphore:

            @retry(
                retry=retry_if_exception_type(
                    (
                        aiohttp.ClientError,
                        asyncio.TimeoutError,
                        RuntimeError,
                    )
                ),
                wait=wait_exponential_jitter(
                    initial=1,
                    max=15,
                ),
                stop=stop_after_attempt(
                    self.max_retries
                ),
                reraise=True,
            )
            async def _fetch_with_retry():
                return await self._request(
                    url,
                    headers=headers,
                )

            return await _fetch_with_retry()

    async def fetch_many(
        self,
        urls: Iterable[str],
    ) -> list[str]:
        """
        Fetch multiple URLs concurrently.
        """

        tasks = [
            self.fetch(url)
            for url in urls
        ]

        results = []

        for task in asyncio.as_completed(
            tasks
        ):
            try:
                result = await task
                results.append(result)

            except Exception as exc:
                logger.error(
                    "Request failed: %s",
                    exc,
                )

        return results