from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ResearchPaper(BaseModel):
    """Standardized research paper record."""

    title: str = Field(min_length=1)
    authors: list[str] = Field(default_factory=list)

    paper_url: str
    arxiv_id: Optional[str] = None

    published_date: Optional[datetime] = None

    summary: Optional[str] = None

    github_url: Optional[str] = None
    github_stars: Optional[int] = None

    github_confidence: float = 0.0