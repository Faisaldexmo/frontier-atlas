import logging

from src.entity.research_paper import ResearchPaper
from src.scrapers.github import GitHubResolver
from src.scrapers.papers import ArxivPaperScraper
from src.storage.json_storage import JSONStorage


logger = logging.getLogger(__name__)


OUTPUT_FILE = "data/output/research_papers.json"


async def run_pipeline(
    max_papers: int = 1000,
) -> list[dict]:

    storage = JSONStorage(OUTPUT_FILE)

    # --------------------------------------------------
    # STEP 1: Load existing papers
    # --------------------------------------------------

    existing_papers = storage.load()

    logger.info(
        "Existing research papers: %s",
        len(existing_papers),
    )

    # --------------------------------------------------
    # STEP 2: If papers already exist, enrich them
    # --------------------------------------------------

    if len(existing_papers) >= max_papers:

        papers_to_process = existing_papers[:max_papers]

        logger.info(
            "Target already reached. "
            "Running GitHub enrichment on %s existing papers.",
            len(papers_to_process),
        )

        github_resolver = GitHubResolver()

        enriched_papers = []

        for index, paper in enumerate(
            papers_to_process,
            start=1,
        ):

            # Preserve already valid GitHub data.
            github_data = {
                "github_url": paper.get("github_url"),
                "github_stars": paper.get("github_stars"),
                "github_confidence": paper.get(
                    "github_confidence",
                    0.0,
                ),
            }

            # Only search again when GitHub data is missing.
            if not paper.get("github_url"):

                try:

                    github_data = (
                        await github_resolver.resolve(
                            paper.get("title", ""),
                            paper.get("summary", ""),
                        )
                    )

                except Exception as exc:

                    logger.warning(
                        "GitHub enrichment failed for '%s': %s",
                        paper.get("title", "Unknown"),
                        exc,
                    )

            combined_data = {
                **paper,
                **github_data,
            }

            try:

                validated_paper = ResearchPaper(
                    **combined_data
                )

                enriched_papers.append(
                    validated_paper.model_dump(
                        mode="json"
                    )
                )

            except Exception as exc:

                logger.error(
                    "Validation failed for '%s': %s",
                    paper.get("title", "Unknown"),
                    exc,
                )

            logger.info(
                "Processed paper %s/%s",
                index,
                len(papers_to_process),
            )

        # Save enriched records.
        storage.save(enriched_papers)

        logger.info(
            "Saved enriched research papers: %s",
            len(enriched_papers),
        )

        return enriched_papers

    # --------------------------------------------------
    # STEP 3: Calculate how many new papers are needed
    # --------------------------------------------------

    papers_needed = (
        max_papers - len(existing_papers)
    )

    start_offset = len(existing_papers)

    logger.info(
        "Need %s additional papers.",
        papers_needed,
    )

    logger.info(
        "Starting Arxiv collection from offset %s.",
        start_offset,
    )

    # --------------------------------------------------
    # STEP 4: Collect new papers
    # --------------------------------------------------

    paper_scraper = ArxivPaperScraper()

    new_papers = await paper_scraper.collect(
        max_papers=papers_needed,
        start_offset=start_offset,
    )

    if not new_papers:

        raise RuntimeError(
            "No new research papers were collected."
        )

    # --------------------------------------------------
    # STEP 5: Remove duplicates
    # --------------------------------------------------

    existing_ids = {
        paper.get("arxiv_id")
        for paper in existing_papers
        if paper.get("arxiv_id")
    }

    unique_new_papers = []

    for paper in new_papers:

        arxiv_id = paper.get("arxiv_id")

        if not arxiv_id:
            continue

        if arxiv_id in existing_ids:

            logger.info(
                "Skipping duplicate paper: %s",
                arxiv_id,
            )

            continue

        existing_ids.add(arxiv_id)

        unique_new_papers.append(
            paper
        )

    logger.info(
        "Unique new papers: %s",
        len(unique_new_papers),
    )

    # --------------------------------------------------
    # STEP 6: GitHub enrichment for new papers
    # --------------------------------------------------

    github_resolver = GitHubResolver()

    processed_new_papers = []

    logger.info(
        "Starting GitHub enrichment for %s new papers.",
        len(unique_new_papers),
    )

    for index, paper in enumerate(
        unique_new_papers,
        start=1,
    ):

        github_data = {
            "github_url": None,
            "github_stars": None,
            "github_confidence": 0.0,
        }

        try:

            github_data = (
                await github_resolver.resolve(
                    paper["title"],
                    paper.get("summary", ""),
                )
            )

        except Exception as exc:

            logger.warning(
                "GitHub enrichment failed for '%s': %s",
                paper["title"],
                exc,
            )

        combined_data = {
            **paper,
            **github_data,
        }

        try:

            validated_paper = ResearchPaper(
                **combined_data
            )

            processed_new_papers.append(
                validated_paper.model_dump(
                    mode="json"
                )
            )

        except Exception as exc:

            logger.error(
                "Validation failed for '%s': %s",
                paper.get(
                    "title",
                    "Unknown",
                ),
                exc,
            )

        logger.info(
            "Processed new paper %s/%s",
            index,
            len(unique_new_papers),
        )

    # --------------------------------------------------
    # STEP 7: Combine old + new
    # --------------------------------------------------

    combined_papers = (
        existing_papers
        + processed_new_papers
    )

    # --------------------------------------------------
    # STEP 8: Final duplicate protection
    # --------------------------------------------------

    final_papers = []

    seen_ids = set()

    for paper in combined_papers:

        arxiv_id = paper.get("arxiv_id")

        if not arxiv_id:
            continue

        if arxiv_id in seen_ids:
            continue

        seen_ids.add(arxiv_id)

        final_papers.append(
            paper
        )

    # --------------------------------------------------
    # STEP 9: Make sure target was reached
    # --------------------------------------------------

    if len(final_papers) < max_papers:

        raise RuntimeError(
            f"Only {len(final_papers)} unique papers "
            f"available. Target was {max_papers}."
        )

    final_papers = final_papers[
        :max_papers
    ]

    # --------------------------------------------------
    # STEP 10: Save final dataset
    # --------------------------------------------------

    storage.save(
        final_papers
    )

    logger.info(
        "Final research paper count: %s",
        len(final_papers),
    )

    return final_papers


def save_papers(
    papers: list[dict],
) -> None:

    if not papers:

        raise ValueError(
            "Refusing to save an empty paper dataset."
        )

    storage = JSONStorage(
        OUTPUT_FILE
    )

    storage.save(
        papers
    )

    logger.info(
        "Saved %s research papers to %s",
        len(papers),
        OUTPUT_FILE,
    )