from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Startup(BaseModel):
    """
    Standardized startup record.
    """

    schemaVersion: str = "1.0"

    recordType: str = "STARTUP"

    source_name: str = Field(
        min_length=1
    )

    source_url: str = Field(
        min_length=1
    )

    entity_name: str = Field(
        min_length=1
    )

    employee_count: Optional[int] = None

    collected_at: datetime