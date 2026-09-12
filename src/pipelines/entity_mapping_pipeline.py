import logging
from pathlib import Path

from src.entity.entity_resolver import EntityResolver
from src.storage.json_storage import JSONStorage


logger = logging.getLogger(__name__)

STARTUPS_FILE = "data/output/startups.json"
PRODUCTS_FILE = "data/output/products.json"
OUTPUT_FILE = "data/output/entity_mapping_log.json"


def collect_entity_names() -> list[str]:
    """
    Collect startup/company names from the datasets.

    Only names that actually exist in the source data are used.
    """

    names = []

    # -------------------------
    # Startups
    # -------------------------

    startup_storage = JSONStorage(
        Path(STARTUPS_FILE)
    )

    startups = startup_storage.load()

    for startup in startups:

        name = startup.get("entity_name")

        if name:
            names.append(name)

    # -------------------------
    # Products
    # -------------------------

    product_storage = JSONStorage(
        Path(PRODUCTS_FILE)
    )

    products = product_storage.load()

    for product in products:

        startup_name = product.get("startup_name")

        if startup_name:
            names.append(startup_name)

    return names


def run_entity_mapping_pipeline() -> list[dict]:
    """
    Resolve all discovered entity names and create
    raw-name -> canonical-name mapping records.
    """

    resolver = EntityResolver()

    raw_names = collect_entity_names()

    if not raw_names:
        raise RuntimeError(
            "No entity names found in startup/product datasets."
        )

    mappings = resolver.resolve_many(raw_names)

    results = []

    for mapping in mappings:

        results.append(
            {
                "raw_name": mapping.raw_name,
                "canonical_name": mapping.canonical_name,
            }
        )

    logger.info(
        "Created %s entity mappings.",
        len(results),
    )

    return results


def save_entity_mappings(
    mappings: list[dict],
) -> None:

    if not mappings:
        raise ValueError(
            "Refusing to save empty entity mapping data."
        )

    storage = JSONStorage(OUTPUT_FILE)

    storage.save(mappings)

    logger.info(
        "Saved %s entity mappings to %s",
        len(mappings),
        OUTPUT_FILE,
    )


if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    mappings = run_entity_mapping_pipeline()

    save_entity_mappings(mappings)

    print(
        f"ENTITY MAPPINGS SAVED: {len(mappings)}"
    )

    print("\nSample mappings:")

    for mapping in mappings[:10]:
        print(
            f"{mapping['raw_name']} "
            f"-> "
            f"{mapping['canonical_name']}"
        )