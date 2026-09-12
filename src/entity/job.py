from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Job(BaseModel):
    """
    Standardized AI job record.
    """

    schemaVersion: str = "1.0"

    recordType: str = "JOB"

    source_name: str = Field(
        min_length=1
    )

    source_url: str = Field(
        min_length=1
    )

    company_name: Optional[str] = None

    job_title: str = Field(
        min_length=1
    )

    location: Optional[str] = None

    description: Optional[str] = None

    posted_at: datetime

    collected_at: datetime