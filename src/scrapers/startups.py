import logging
import re
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import async_playwright

from src.scrapers.base import BaseScraper


logger = logging.getLogger(__name__)


YC_COMPANIES_URL = (
    "https://www.ycombinator.com/companies"
)


class YCStartupScraper:
    """
    Collect startup records from the official
    Y Combinator startup directory.
    """

    def __init__(
        self,
        scraper: BaseScraper | None = None,
    ):
        self.scraper = scraper

    async def collect(
        self,
        max_startups: int = 1000,
    ) -> list[dict[str, Any]]:
        """
        Collect up to max_startups unique
        companies from YC.

        The YC directory uses dynamic loading,
        so Playwright scrolling is used to load
        additional companies.
        """

        logger.info(
            "Opening YC Startup Directory"
        )

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True
            )

            page = await browser.new_page(
                viewport={
                    "width": 1440,
                    "height": 900,
                },
                user_agent=(
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/140.0.0.0 "
                    "Safari/537.36"
                ),
            )

            try:

                await page.goto(
                    YC_COMPANIES_URL,
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )

                logger.info(
                    "YC directory loaded"
                )

                await page.wait_for_timeout(
                    3000
                )

                previous_count = 0
                stable_rounds = 0

                # Keep scrolling until we reach
                # the requested number of startups.
                for scroll_round in range(
                    1,
                    80,
                ):

                    company_links = page.locator(
                        'a[href^="/companies/"]'
                    )

                    current_count = (
                        await company_links.count()
                    )

                    logger.info(
                        "Scroll %s | "
                        "Company links currently loaded: %s",
                        scroll_round,
                        current_count,
                    )

                    if current_count >= max_startups:
                        logger.info(
                            "Reached target of %s companies.",
                            max_startups,
                        )
                        break

                    if current_count == previous_count:
                        stable_rounds += 1
                    else:
                        stable_rounds = 0

                    previous_count = current_count

                    # Try to trigger YC's dynamic
                    # "load more" behaviour.
                    await page.evaluate(
                        """
                        window.scrollTo(
                            0,
                            document.body.scrollHeight
                        );
                        """
                    )

                    await page.wait_for_timeout(
                        1800
                    )

                    # Some versions expose an actual
                    # load-more button.
                    load_more_selectors = [
                        'button:has-text("Load more")',
                        'button:has-text("Loading more")',
                        'a:has-text("Load more")',
                    ]

                    for selector in (
                        load_more_selectors
                    ):
                        try:
                            button = page.locator(
                                selector
                            ).first

                            if await button.is_visible(
                                timeout=500
                            ):
                                await button.click(
                                    timeout=3000
                                )

                                await page.wait_for_timeout(
                                    1800
                                )

                                break

                        except Exception:
                            continue

                    # If nothing new has appeared
                    # for several rounds, give YC a little
                    # extra time before stopping.
                    if stable_rounds >= 5:

                        logger.info(
                            "No new companies detected "
                            "for several rounds."
                        )

                        await page.wait_for_timeout(
                            4000
                        )

                        latest_count = (
                            await page.locator(
                                'a[href^="/companies/"]'
                            ).count()
                        )

                        if latest_count == current_count:
                            break

                # Extract all loaded company links.
                company_links = page.locator(
                    'a[href^="/companies/"]'
                )

                total_links = (
                    await company_links.count()
                )

                logger.info(
                    "Final loaded company links: %s",
                    total_links,
                )

                startups = []
                seen_urls = set()

                for index in range(
                    total_links
                ):

                    if len(startups) >= max_startups:
                        break

                    try:

                        link = company_links.nth(
                            index
                        )

                        href = (
                            await link.get_attribute(
                                "href"
                            )
                        )

                        if not href:
                            continue

                        if not href.startswith(
                            "/companies/"
                        ):
                            continue

                        # Ignore generic directory
                        # and category links.
                        parts = (
                            href.rstrip("/")
                            .split("/")
                        )

                        if len(parts) < 3:
                            continue

                        slug = parts[-1].strip()

                        if not slug:
                            continue

                        source_url = (
                            "https://www.ycombinator.com"
                            + href
                        )

                        source_url = (
                            source_url.rstrip("/")
                        )

                        if source_url in seen_urls:
                            continue

                        seen_urls.add(
                            source_url
                        )

                        # IMPORTANT:
                        # Use the URL slug for the canonical
                        # startup name instead of taking the
                        # entire card text.
                        entity_name = (
                            self._name_from_slug(
                                slug
                            )
                        )

                        if not entity_name:
                            continue

                        employee_count = (
                            await self._extract_employee_count(
                                link
                            )
                        )

                        startup = {
                            "schemaVersion": "1.0",
                            "recordType": "STARTUP",
                            "source_name": (
                                "Y Combinator"
                            ),
                            "source_url": source_url,
                            "entity_name": entity_name,
                            "employee_count": (
                                employee_count
                            ),
                            "collected_at": (
                                datetime.now(
                                    timezone.utc
                                )
                            ),
                        }

                        startups.append(
                            startup
                        )

                        if (
                            len(startups) % 50 == 0
                            or len(startups) <= 10
                        ):
                            logger.info(
                                "Collected %s/%s: %s",
                                len(startups),
                                max_startups,
                                entity_name,
                            )

                    except Exception as exc:

                        logger.warning(
                            "Could not parse company "
                            "link %s: %s",
                            index,
                            exc,
                        )

                startups = self._deduplicate(
                    startups
                )

                logger.info(
                    "Unique startups collected: %s",
                    len(startups),
                )

                if not startups:
                    raise RuntimeError(
                        "Could not extract startup "
                        "records from YC directory."
                    )

                if len(startups) < max_startups:
                    logger.warning(
                        "Requested %s startups, "
                        "but only %s unique startups "
                        "were loaded.",
                        max_startups,
                        len(startups),
                    )

                return startups[
                    :max_startups
                ]

            finally:

                await browser.close()

    @staticmethod
    def _name_from_slug(
        slug: str,
    ) -> str | None:
        """
        Convert a YC URL slug into a clean
        startup name.

        Example:
            doordash -> DoorDash
            airbnb -> Airbnb
            instacart -> Instacart
        """

        if not slug:
            return None

        slug = slug.strip()

        # Remove query-like fragments.
        slug = slug.split("?")[0]

        # Convert hyphens to spaces.
        name = slug.replace(
            "-",
            " ",
        )

        name = re.sub(
            r"\s+",
            " ",
            name,
        ).strip()

        if not name:
            return None

        # Preserve common brand-style names.
        known_names = {
            "airbnb": "Airbnb",
            "doordash": "DoorDash",
            "instacart": "Instacart",
            "coinbase": "Coinbase",
            "groww": "Groww",
            "openai": "OpenAI",
            "ramp": "Ramp",
            "stripe": "Stripe",
            "reddit": "Reddit",
            "brex": "Brex",
            "rippling": "Rippling",
            "scale ai": "Scale AI",
            "faire": "Faire",
            "whatnot": "Whatnot",
        }

        normalized = name.lower()

        if normalized in known_names:
            return known_names[
                normalized
            ]

        return name.title()

    async def _extract_employee_count(
        self,
        link,
    ) -> int | None:
        """
        Try to extract employee count from
        the startup card.
        """

        try:

            # Look at the closest card-like ancestor.
            card = link.locator(
                "xpath=ancestor::*[self::article or self::div][1]"
            )

            card_text = await card.inner_text()

            if not card_text:
                return None

            match = re.search(
                r"([\d,]+)\s+employees?",
                card_text,
                re.IGNORECASE,
            )

            if match:
                value = (
                    match.group(1)
                    .replace(",", "")
                )

                return int(value)

        except Exception:
            pass

        return None

    @staticmethod
    def _deduplicate(
        startups: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Remove duplicate startups using
        their canonical YC source URL.
        """

        unique = {}

        for startup in startups:

            key = (
                startup["source_url"]
                .lower()
                .rstrip("/")
            )

            if key not in unique:
                unique[key] = startup

        return list(
            unique.values()
        )