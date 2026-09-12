import re
from dataclasses import dataclass


@dataclass
class EntityMapping:
    raw_name: str
    canonical_name: str


class EntityResolver:
    """
    Deterministic entity resolver.

    Converts common variations of company/startup names
    into one canonical name without using an LLM.
    """

    KNOWN_ENTITIES = {
        "openai": "OpenAI",
        "anthropic": "Anthropic",
        "google": "Google",
        "google deepmind": "Google DeepMind",
        "microsoft": "Microsoft",
        "meta": "Meta",
        "meta ai": "Meta AI",
        "mistral ai": "Mistral AI",
        "xai": "xAI",
        "cohere": "Cohere",
        "perplexity": "Perplexity",
        "hugging face": "Hugging Face",
        "stability ai": "Stability AI",
        "runway": "Runway",
        "character ai": "Character AI",
        "inflection ai": "Inflection AI",
        "databricks": "Databricks",
        "nvidia": "NVIDIA",
        "amazon": "Amazon",
        "aws": "AWS",
        "apple": "Apple",
        "adobe": "Adobe",
        "ibm": "IBM",
    }

    COMPANY_SUFFIXES = {
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "co",
        "company",
        "ltd",
        "limited",
        "llc",
        "plc",
    }

    def normalize(self, name: str) -> str:
        """
        Normalize a raw entity name for matching.
        """

        if not name:
            return ""

        value = name.strip().lower()

        # Replace common punctuation with spaces.
        value = re.sub(r"[.,()&'\"/\\-]", " ", value)

        # Remove company suffixes.
        words = value.split()

        words = [
            word
            for word in words
            if word not in self.COMPANY_SUFFIXES
        ]

        value = " ".join(words)

        # Remove extra whitespace.
        value = re.sub(r"\s+", " ", value).strip()

        return value

    def resolve(self, raw_name: str) -> str:
        """
        Return the canonical entity name.
        """

        normalized = self.normalize(raw_name)

        if not normalized:
            return raw_name

        # Exact known-entity match.
        if normalized in self.KNOWN_ENTITIES:
            return self.KNOWN_ENTITIES[normalized]

        # Handle common variations such as:
        # "Open AI" -> "OpenAI"
        compact = normalized.replace(" ", "")

        for key, canonical in self.KNOWN_ENTITIES.items():

            if compact == key.replace(" ", ""):
                return canonical

        # If no known mapping exists, keep a cleaned version.
        return raw_name.strip()

    def create_mapping(self, raw_name: str) -> EntityMapping:
        """
        Create a raw -> canonical mapping record.
        """

        canonical_name = self.resolve(raw_name)

        return EntityMapping(
            raw_name=raw_name,
            canonical_name=canonical_name,
        )

    def resolve_many(
        self,
        names: list[str],
    ) -> list[EntityMapping]:
        """
        Resolve multiple entity names and remove
        duplicate raw-name mappings.
        """

        mappings = []
        seen = set()

        for name in names:

            if not name:
                continue

            if name in seen:
                continue

            seen.add(name)

            mappings.append(
                self.create_mapping(name)
            )

        return mappings