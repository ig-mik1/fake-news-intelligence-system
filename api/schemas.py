from typing import Optional

from pydantic import BaseModel, Field, field_validator


class VerifyRequest(BaseModel):
    headline: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="News headline to verify.",
    )
    content: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Optional article content/body to improve prediction reliability.",
    )

    @field_validator("headline")
    @classmethod
    def validate_headline(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10 or len(cleaned) > 500:
            raise ValueError("headline must be between 10 and 500 characters.")
        return cleaned

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
