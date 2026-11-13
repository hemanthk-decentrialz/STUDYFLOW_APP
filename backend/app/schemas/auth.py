import re
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator

from app.schemas.resources import ResourcePatch

DisplayName = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
]


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("password")
    @classmethod
    def require_password_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password cannot consist only of whitespace.")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value


class SignupRequest(LoginRequest):
    name: DisplayName
    password: str = Field(
        min_length=12,
        max_length=1024,
        strict=True,
        description=(
            "At least 12 characters including lowercase, uppercase, a digit, "
            "and a symbol; never logged or returned."
        ),
    )

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        if not (
            re.search(r"[a-z]", value)
            and re.search(r"[A-Z]", value)
            and re.search(r"[0-9]", value)
            and re.search(r"[\x21-\x2F\x3A-\x40\x5B-\x60\x7B-\x7E]", value)
        ):
            raise ValueError("Use lowercase, uppercase, a digit, and a symbol in your password.")
        return value


class SessionUser(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: UUID
    name: str
    email: str
    created_at: datetime = Field(
        serialization_alias="createdAt", description="When this Studyflow account was created."
    )


class ProfilePatch(ResourcePatch):
    name: DisplayName | None = Field(
        default=None, description="Display name shown in the workspace."
    )
