from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class Product(BaseModel):
    """
    Standardized AI product record.
    """

    schemaVersion: str = "1.0"

    recordType: str = "PRODUCT"

    source_name: str = Field(
        min_length=1
    )

    source_url: str = Field(
        min_length=1
    )

    product_name: str = Field(
        min_length=1
    )

    startup_name: Optional[str] = None

    pricing_model: Optional[str] = None

    collected_at: datetime