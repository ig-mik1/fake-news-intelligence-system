from typing import Literal, Optional

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


class FeedbackRequest(BaseModel):
    headline: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Verified headline text.",
    )
    content: Optional[str] = Field(
        default=None,
        max_length=10000,
        description="Optional article content/body used during verification.",
    )
    model_decision: Optional[Literal["REAL", "FAKE"]] = Field(
        default=None,
        description="Model decision shown to user at verification time.",
    )
    human_label: Literal["REAL", "FAKE"] = Field(
        ...,
        description="Human-corrected ground-truth label.",
    )
    notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional reviewer notes explaining correction.",
    )

    @field_validator("headline")
    @classmethod
    def validate_feedback_headline(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 10 or len(cleaned) > 500:
            raise ValueError("headline must be between 10 and 500 characters.")
        return cleaned

    @field_validator("content")
    @classmethod
    def validate_feedback_content(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @field_validator("notes")
    @classmethod
    def validate_feedback_notes(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None
