import asyncio
import logging
import random

from src.llm.providers import (
    BaseLLMProvider,
    LLMProviderError,
    create_providers,
)


logger = logging.getLogger(__name__)


class LLMOrchestrator:

    def __init__(
        self,
        providers: list[BaseLLMProvider] | None = None,
    ):
        self.providers = (
            providers
            if providers is not None
            else create_providers()
        )

        # Maximum approximate characters allowed in one LLM request.
        # This helps avoid very large payloads.
        self.max_chunk_size = 12000

    async def generate(
        self,
        prompt: str,
    ) -> str:

        if not self.providers:
            raise RuntimeError(
                "No LLM providers configured. "
                "Add API keys to the environment."
            )

        last_error = None

        for provider in self.providers:

            provider_name = provider.__class__.__name__

            logger.info(
                "Trying LLM provider: %s",
                provider_name,
            )

            try:

                result = await self._generate_with_chunking(
                    provider,
                    prompt,
                )

                if result and result.strip():

                    logger.info(
                        "LLM success: %s",
                        provider_name,
                    )

                    return result.strip()

            except Exception as exc:

                last_error = exc

                logger.warning(
                    "LLM provider failed: %s -> %s",
                    provider_name,
                    exc,
                )

                continue

        raise RuntimeError(
            "All LLM providers failed."
        ) from last_error

    async def _generate_with_chunking(
        self,
        provider: BaseLLMProvider,
        prompt: str,
    ) -> str:

        # Small prompts can be sent directly.
        if len(prompt) <= self.max_chunk_size:

            try:
                return await self._generate_with_retry(
                    provider,
                    prompt,
                )

            except LLMProviderError as exc:

                # 413 means the request is too large.
                if "413" not in str(exc):
                    raise

                logger.warning(
                    "413 payload error. "
                    "Splitting prompt into smaller chunks."
                )

        # Large prompts are automatically split.
        chunks = self._chunk_text(
            prompt,
            self.max_chunk_size,
        )

        logger.info(
            "Processing prompt in %s chunks.",
            len(chunks),
        )

        results = []

        for index, chunk in enumerate(
            chunks,
            start=1,
        ):

            logger.info(
                "Processing chunk %s/%s.",
                index,
                len(chunks),
            )

            chunk_prompt = (
                "Process the following chunk of text. "
                "Return only the useful extracted information.\n\n"
                f"CHUNK {index}/{len(chunks)}:\n"
                f"{chunk}"
            )

            result = await self._generate_with_retry(
                provider,
                chunk_prompt,
            )

            if result and result.strip():
                results.append(result.strip())

        if not results:
            raise RuntimeError(
                "LLM returned no results from chunks."
            )

        return "\n".join(results)

    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
    ) -> list[str]:

        chunks = []

        start = 0

        while start < len(text):

            end = min(
                start + chunk_size,
                len(text),
            )

            # Try to split at a natural boundary.
            if end < len(text):

                paragraph_break = text.rfind(
                    "\n\n",
                    start,
                    end,
                )

                sentence_break = text.rfind(
                    ". ",
                    start,
                    end,
                )

                best_break = max(
                    paragraph_break,
                    sentence_break,
                )

                if best_break > start + 1000:
                    end = best_break + 1

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            start = end

        return chunks

    async def _generate_with_retry(
        self,
        provider: BaseLLMProvider,
        prompt: str,
        max_attempts: int = 3,
    ) -> str:

        for attempt in range(
            1,
            max_attempts + 1,
        ):

            try:

                return await provider.generate(
                    prompt
                )

            except LLMProviderError as exc:

                message = str(exc)

                # 413 = request payload is too large.
                # Chunking is handled by _generate_with_chunking().
                if "413" in message:
                    raise

                # 429 = rate limit.
                # Retry using exponential backoff + jitter.
                if "429" not in message:
                    raise

                if attempt == max_attempts:
                    raise

                delay = (
                    2 ** (attempt - 1)
                    + random.uniform(
                        0,
                        1,
                    )
                )

                logger.warning(
                    "Rate limited. "
                    "Retrying in %.2f seconds.",
                    delay,
                )

                await asyncio.sleep(
                    delay
                )

        raise RuntimeError(
            "LLM retry loop failed."
        )