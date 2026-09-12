import json
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class JSONStorage:
    """Store and retrieve application records using JSON files."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def save(
        self,
        records: list[dict[str, Any]],
    ) -> None:
        """Save records to a JSON file."""

        self.file_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with self.file_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                records,
                file,
                indent=2,
                ensure_ascii=False,
            )

        logger.info(
            "Saved %s records to %s",
            len(records),
            self.file_path,
        )

    def load(self) -> list[dict[str, Any]]:
        """Load records from the JSON file."""

        if not self.file_path.exists():
            logger.warning(
                "Storage file does not exist: %s",
                self.file_path,
            )
            return []

        with self.file_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError(
                "Storage file must contain a JSON list."
            )

        return data

    def count(self) -> int:
        """Return the number of stored records."""

        return len(self.load())