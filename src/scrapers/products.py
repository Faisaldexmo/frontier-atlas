import logging
import re
from datetime import datetime, timezone
from typing import Any

from playwright.async_api import async_playwright


logger = logging.getLogger(__name__)


BASE_URL = "https://tooldirectory.ai/tools"


class ProductScraper:
    """
    Scrape AI products from ToolDirectory.AI.
    """

    async def collect(
        self,
        max_products: int = 1000,
    ) -> list[dict[str, Any]]:

        logger.info(
            "Opening ToolDirectory.AI"
        )

        products: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        async with async_playwright() as p:

            browser = await p.chromium.launch(
                headless=True
            )

            page = await browser.new_page(
                viewport={
                    "width": 1440,
                    "height": 900,
                }
            )

            try:

                # ToolDirectory currently has
                # 26 pages.
                for page_number in range(1, 27):

                    if len(products) >= max_products:
                        break

                    if page_number == 1:
                        url = BASE_URL
                    else:
                        url = (
                            f"{BASE_URL}/page/"
                            f"{page_number}"
                        )

                    logger.info(
                        "Opening page %s: %s",
                        page_number,
                        url,
                    )

                    await page.goto(
                        url,
                        wait_until="domcontentloaded",
                        timeout=60_000,
                    )

                    await page.wait_for_timeout(
                        1200
                    )

                    links = page.locator(
                        'a[href^="/tools/"]'
                    )

                    link_count = await links.count()

                    logger.info(
                        "Page %s -> %s links found",
                        page_number,
                        link_count,
                    )

                    for index in range(link_count):

                        if len(products) >= max_products:
                            break

                        try:

                            link = links.nth(index)

                            href = (
                                await link.get_attribute(
                                    "href"
                                )
                            )

                            if not href:
                                continue

                            # Only actual tool pages.
                            if not href.startswith(
                                "/tools/"
                            ):
                                continue

                            # Ignore generic navigation.
                            if href in (
                                "/tools/",
                                "/tools",
                            ):
                                continue

                            source_url = (
                                "https://tooldirectory.ai"
                                + href
                            )

                            source_url = (
                                source_url.rstrip("/")
                            )

                            if source_url in seen_urls:
                                continue

                            text = await link.inner_text()

                            text = re.sub(
                                r"\s+",
                                " ",
                                text,
                            ).strip()

                            if not text:
                                continue

                            product_name = (
                                self._extract_product_name(
                                    text
                                )
                            )

                            if not product_name:
                                continue

                            pricing_model = (
                                self._extract_pricing(
                                    text
                                )
                            )

                            record = {
                                "schemaVersion": "1.0",
                                "recordType": "PRODUCT",
                                "source_name": (
                                    "ToolDirectory.AI"
                                ),
                                "source_url": source_url,
                                "product_name": (
                                    product_name
                                ),
                                "startup_name": None,
                                "pricing_model": (
                                    pricing_model
                                ),
                                "collected_at": (
                                    datetime.now(
                                        timezone.utc
                                    )
                                ),
                            }

                            seen_urls.add(
                                source_url
                            )

                            products.append(
                                record
                            )

                            if (
                                len(products) <= 10
                                or len(products) % 100 == 0
                            ):
                                logger.info(
                                    "Collected %s/%s: %s",
                                    len(products),
                                    max_products,
                                    product_name,
                                )

                        except Exception as exc:

                            logger.warning(
                                "Could not parse "
                                "product %s on page %s: %s",
                                index,
                                page_number,
                                exc,
                            )

                products = self.deduplicate(
                    products
                )

                logger.info(
                    "Total unique products: %s",
                    len(products),
                )

                if not products:
                    raise RuntimeError(
                        "No products were extracted."
                    )

                return products[:max_products]

            finally:

                await browser.close()

    @staticmethod
    def _extract_product_name(
        text: str,
    ) -> str | None:

        if not text:
            return None

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        # The directory listing format is:
        # Product Name + Category + Pricing + Rating.
        #
        # We take the first meaningful segment.
        parts = text.split()

        if not parts:
            return None

        pricing_words = {
            "Free",
            "Freemium",
            "Paid",
            "Trial",
        }

        cleaned = []

        for word in parts:

            if word in pricing_words:
                break

            # Stop before rating values.
            if re.fullmatch(
                r"\d+\.\d+",
                word,
            ):
                break

            cleaned.append(word)

        name = " ".join(
            cleaned
        ).strip()

        if not name:
            return None

        if len(name) > 120:
            name = name[:120].strip()

        return name

    @staticmethod
    def _extract_pricing(
        text: str,
    ) -> str | None:

        normalized = text.lower()

        if "freemium" in normalized:
            return "FREEMIUM"

        if "free trial" in normalized:
            return "PAID"

        if "paid" in normalized:
            return "PAID"

        if "free" in normalized:
            return "FREE"

        return None

    @staticmethod
    def deduplicate(
        products: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        unique: dict[str, dict[str, Any]] = {}

        for product in products:

            key = (
                product["source_url"]
                .lower()
                .rstrip("/")
            )

            if key not in unique:
                unique[key] = product

        return list(
            unique.values()
        )