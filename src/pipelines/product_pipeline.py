import logging

from src.entity.product import Product
from src.scrapers.products import ProductScraper
from src.storage.json_storage import JSONStorage


logger = logging.getLogger(__name__)


OUTPUT_FILE = (
    "data/output/products.json"
)


async def run_product_pipeline(
    max_products: int = 1000,
) -> list[dict]:

    scraper = ProductScraper()

    products = await scraper.collect(
        max_products=max_products
    )

    if not products:
        raise RuntimeError(
            "No products were collected."
        )

    products = scraper.deduplicate(
        products
    )

    validated_products = []

    for index, product in enumerate(
        products,
        start=1,
    ):

        try:

            validated = Product(
                **product
            )

            validated_products.append(
                validated.model_dump(
                    mode="json"
                )
            )

            logger.info(
                "Validated %s/%s: %s",
                index,
                len(products),
                product["product_name"],
            )

        except Exception as exc:

            logger.error(
                "Product validation failed "
                "for %s: %s",
                product.get(
                    "product_name",
                    "Unknown",
                ),
                exc,
            )

    if not validated_products:
        raise RuntimeError(
            "No valid product records."
        )

    return validated_products


def save_products(
    products: list[dict],
) -> None:

    if not products:
        raise ValueError(
            "Refusing to save empty "
            "product data."
        )

    storage = JSONStorage(
        OUTPUT_FILE
    )

    storage.save(
        products
    )

    logger.info(
        "Saved %s products to %s",
        len(products),
        OUTPUT_FILE,
    )