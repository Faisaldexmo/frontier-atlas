import json
import logging
from pathlib import Path
from typing import Any

from src.llm.orchestrator import LLMOrchestrator


logger = logging.getLogger(__name__)


class LLMExtractionPipeline:
    """
    Safely converts source text into structured JSON using the
    configured multi-provider LLM orchestrator.

    The source URL is always preserved so every extracted record
    remains traceable to its original source.
    """

    def __init__(self, output_dir: str = "data/output"):
        self.orchestrator = LLMOrchestrator()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def extract(
        self,
        source_text: str,
        source_url: str,
        record_type: str,
    ) -> dict[str, Any]:
        if not source_text.strip():
            raise ValueError("Source text cannot be empty.")

        if not source_url.strip():
            raise ValueError("Source URL cannot be empty.")

        if not record_type.strip():
            raise ValueError("Record type cannot be empty.")

        prompt = self._build_prompt(
            source_text=source_text,
            source_url=source_url,
            record_type=record_type,
        )

        logger.info(
            "Starting LLM extraction for %s: %s",
            record_type,
            source_url,
        )

        response = await self.orchestrator.generate(prompt)

        extracted = self._parse_json(response)

        # Never allow the LLM to replace the real source URL.
        extracted["source_url"] = source_url
        extracted["record_type"] = record_type

        logger.info(
            "LLM extraction completed for %s",
            source_url,
        )

        return extracted

    def _build_prompt(
        self,
        source_text: str,
        source_url: str,
        record_type: str,
    ) -> str:
        return f"""
You are a data extraction engine.

Your job is ONLY to extract information that is explicitly
present in the supplied source text.

IMPORTANT RULES:
1. Never invent or hallucinate information.
2. Never guess missing values.
3. If a value is not present, use null.
4. Do not create facts from general knowledge.
5. Preserve the original source URL.
6. Return ONLY valid JSON.
7. Do not include markdown fences.
8. Extract only information relevant to the requested record type.

Record type:
{record_type}

Source URL:
{source_url}

Source text:
{source_text}

Return a single JSON object.
""".strip()

    def _parse_json(self, response: str) -> dict[str, Any]:
        cleaned = response.strip()

        # Remove markdown code fences if a provider returns them.
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()

            if lines and lines[0].startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            logger.error(
                "LLM returned invalid JSON: %s",
                cleaned[:500],
            )
            raise ValueError(
                "LLM response was not valid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "LLM response must be a JSON object."
            )

        return data


async def extract_record(
    source_text: str,
    source_url: str,
    record_type: str,
) -> dict[str, Any]:
    """
    Convenience function for using the extraction pipeline.
    """

    pipeline = LLMExtractionPipeline()

    return await pipeline.extract(
        source_text=source_text,
        source_url=source_url,
        record_type=record_type,
    )