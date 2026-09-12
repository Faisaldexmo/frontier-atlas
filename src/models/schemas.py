from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class Source(BaseModel):
    name: str
    url: str


class StartupData(BaseModel):
    employee_count: Optional[int] = None


class StartupEntity(BaseModel):
    schema_version: str = "1.0"
    record_type: str = "STARTUP"
    source: Source
    entity_name: str
    data: StartupData = Field(default_factory=StartupData)
    collected_at: datetime


class ProductEntity(BaseModel):
    schema_version: str = "1.0"
    record_type: str = "PRODUCT"
    source: Source
    startup_name: str
    pricing_model: str
    collected_at: datetime


class ResearchPaperEntity(BaseModel):
    schema_version: str = "1.0"
    record_type: str = "RESEARCH_PAPER"
    title: str
    authors: List[str]
    paper_url: str
    github_url: Optional[str] = None
    github_stars: Optional[int] = None
    published_date: datetime


class JobEntity(BaseModel):
    schema_version: str = "1.0"
    record_type: str = "JOB"
    company: str
    date: datetime
    is_remote: bool
    role_family: str