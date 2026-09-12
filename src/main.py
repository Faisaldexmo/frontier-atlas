import asyncio
import logging

from src.pipelines.research_pipeline import run_pipeline, save_papers


def print_banner() -> None:
    print()
    print("=" * 60)
    print("              FRONTIER ATLAS")
    print("       Research Intelligence System")
    print("=" * 60)


def print_menu() -> None:
    print()
    print("1. Collect Research Papers")
    print("2. Exit")
    print()


async def collect_research_papers() -> None:
    print()
    print("Starting research paper collection...")
    print("Target: 1,000 unique research papers")
    print()

    papers = await run_pipeline(
        max_papers=1000
    )

    save_papers(papers)

    print()
    print("-" * 60)
    print(
        f"Successfully collected {len(papers)} research papers."
    )
    print("-" * 60)


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(message)s",
    )

    print_banner()

    while True:
        print_menu()

        choice = input(
            "Select an option: "
        ).strip()

        if choice == "1":
            try:
                await collect_research_papers()

            except Exception as exc:
                logger = logging.getLogger(__name__)

                logger.error(
                    "Collection failed: %s",
                    exc,
                )

                print()
                print(
                    "Something went wrong. "
                    "Please check the logs."
                )

        elif choice == "2":
            print()
            print(
                "Thank you for using Frontier Atlas."
            )
            break

        else:
            print()
            print(
                "Invalid option. "
                "Please select 1 or 2."
            )


if __name__ == "__main__":
    asyncio.run(main())