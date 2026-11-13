from datetime import datetime
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.resources import RequestModel, SafeId, Subject, Title

Content = Annotated[str, Field(strict=True, min_length=1, max_length=100_000)]


class NoteCreate(RequestModel):
    course_id: SafeId = Field(
        alias="courseId", description="An active course owned by this session user."
    )
    id: SafeId = Field(description="Positive JavaScript-safe numeric ID; immutable after creation.")
    title: Title = Field(description="Trimmed title, unique per owner among active resources.")
    subject: Subject = ""
    content: Content

    @field_validator("content")
    @classmethod
    def require_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Content must contain non-whitespace text.")
        return value


class NoteResponse(BaseModel):
    version: int
    updated_at: datetime = Field(serialization_alias="updatedAt")
    course_id: int = Field(serialization_alias="courseId")
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    subject: str
    content: str


class NotePatch(RequestModel):
    expected_version: int = Field(alias="expectedVersion", strict=True, ge=1)
    title: Title | None = None
    content: Content | None = None
    course_id: SafeId | None = Field(default=None, alias="courseId")

    @model_validator(mode="after")
    def valid_changes(self) -> Self:
        fields = self.model_fields_set - {"expected_version"}
        if not fields or any(getattr(self, name) is None for name in fields):
            raise ValueError("Provide non-null note changes.")
        if self.content is not None and not self.content.strip():
            raise ValueError("Content must contain text.")
        return self
