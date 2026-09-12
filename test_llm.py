import asyncio

from src.llm.providers import create_providers


async def main():
    providers = create_providers()

    print(
        "Providers:",
        [p.__class__.__name__ for p in providers]
    )

    if not providers:
        print("No LLM provider found.")
        return

    response = await providers[0].generate(
        "Reply with exactly: LLM TEST SUCCESS"
    )

    print("Response:", response)


if __name__ == "__main__":
    asyncio.run(main())