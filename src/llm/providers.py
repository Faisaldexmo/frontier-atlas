import logging
import os

import aiohttp
from dotenv import load_dotenv


load_dotenv()


logger = logging.getLogger(__name__)

class LLMProviderError(Exception):
    """Raised when an LLM provider request fails."""


class BaseLLMProvider:
    def __init__(
        self,
        api_key: str,
        model: str,
    ):
        self.api_key = api_key
        self.model = model

    async def generate(
        self,
        prompt: str,
    ) -> str:
        raise NotImplementedError


class GeminiProvider(BaseLLMProvider):

    async def generate(
        self,
        prompt: str,
    ) -> str:

        url = (
            "https://generativelanguage.googleapis.com/"
            "v1beta/models/"
            f"{self.model}:generateContent"
            f"?key={self.api_key}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ]
        }

        timeout = aiohttp.ClientTimeout(
            total=60
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.post(
                url,
                json=payload,
            ) as response:

                text = await response.text()

                if response.status != 200:
                    raise LLMProviderError(
                        f"Gemini error "
                        f"{response.status}: "
                        f"{text[:500]}"
                    )

                data = await response.json()

                try:
                    return (
                        data["candidates"][0]
                        ["content"]["parts"][0]
                        ["text"]
                    )

                except (
                    KeyError,
                    IndexError,
                    TypeError,
                ) as exc:

                    raise LLMProviderError(
                        "Invalid Gemini response."
                    ) from exc


class GroqProvider(BaseLLMProvider):

    async def generate(
        self,
        prompt: str,
    ) -> str:

        url = (
            "https://api.groq.com/openai/v1/"
            "chat/completions"
        )

        headers = {
            "Authorization": (
                f"Bearer {self.api_key}"
            ),
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0,
        }

        timeout = aiohttp.ClientTimeout(
            total=60
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.post(
                url,
                headers=headers,
                json=payload,
            ) as response:

                text = await response.text()

                if response.status != 200:
                    raise LLMProviderError(
                        f"Groq error "
                        f"{response.status}: "
                        f"{text[:500]}"
                    )

                data = await response.json()

                try:
                    return (
                        data["choices"][0]
                        ["message"]["content"]
                    )

                except (
                    KeyError,
                    IndexError,
                    TypeError,
                ) as exc:

                    raise LLMProviderError(
                        "Invalid Groq response."
                    ) from exc


class DeepSeekProvider(BaseLLMProvider):

    async def generate(
        self,
        prompt: str,
    ) -> str:

        url = (
            "https://api.deepseek.com/"
            "chat/completions"
        )

        headers = {
            "Authorization": (
                f"Bearer {self.api_key}"
            ),
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            "temperature": 0,
        }

        timeout = aiohttp.ClientTimeout(
            total=60
        )

        async with aiohttp.ClientSession(
            timeout=timeout
        ) as session:

            async with session.post(
                url,
                headers=headers,
                json=payload,
            ) as response:

                text = await response.text()

                if response.status != 200:
                    raise LLMProviderError(
                        f"DeepSeek error "
                        f"{response.status}: "
                        f"{text[:500]}"
                    )

                data = await response.json()

                try:
                    return (
                        data["choices"][0]
                        ["message"]["content"]
                    )

                except (
                    KeyError,
                    IndexError,
                    TypeError,
                ) as exc:

                    raise LLMProviderError(
                        "Invalid DeepSeek response."
                    ) from exc


def create_providers() -> list[BaseLLMProvider]:

    providers: list[
        BaseLLMProvider
    ] = []

    gemini_key = os.getenv(
        "GEMINI_API_KEY"
    )

    groq_key = os.getenv(
        "GROQ_API_KEY"
    )

    deepseek_key = os.getenv(
        "DEEPSEEK_API_KEY"
    )

    if gemini_key:

        providers.append(
            GeminiProvider(
                api_key=gemini_key,
                model="gemini-3.6-flash",
            )
        )

    if groq_key:

        providers.append(
            GroqProvider(
                api_key=groq_key,
                model="llama-3.3-70b-versatile",
            )
        )

    if deepseek_key:

        providers.append(
            DeepSeekProvider(
                api_key=deepseek_key,
                model="deepseek-chat",
            )
        )

    return providers