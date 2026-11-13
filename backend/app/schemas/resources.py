import re
from datetime import date
from typing import Annotated, ClassVar, Literal, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.core.types import FilterValue


def parse_calendar_date(value: object) -> object:
    if isinstance(value, str):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError("Date must use YYYY-MM-DD.")
        return date.fromisoformat(value)
    if value is not None and type(value) is not date:
        raise ValueError("Provide a calendar date.")
    return value


SafeId = Annotated[int, Field(strict=True, gt=0, le=9_007_199_254_740_991)]
Title = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=200)
]
Subject = Annotated[str, StringConstraints(strict=True, strip_whitespace=True, max_length=200)]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ResourcePatch(RequestModel):
    nullable_fields: ClassVar[frozenset[str]] = frozenset()

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        if any(
            getattr(self, name) is None for name in self.model_fields_set - self.nullable_fields
        ):
            raise ValueError("Resource fields cannot be null; omit unchanged fields instead.")
        return self


class Page[T](BaseModel):
    items: list[T] = Field(description="Only the requested owner-scoped page of active resources.")
    page: int
    limit: int
    total: int = Field(description="Database COUNT using the same owner/search/filter predicates.")
    total_pages: int = Field(description="Ceiling of total/limit; zero for no results.")


class ResourceListParams(RequestModel):
    sort_by: str = "position"
    page: int = Field(
        default=1,
        ge=1,
        le=10_001,
        description="One-based page; computed offset may not exceed 10000.",
    )
    limit: int = Field(default=10, ge=1, le=100, description="Page size, strictly capped at 100.")
    search: str | None = Field(default=None, min_length=1, max_length=200)
    order: Literal["asc", "desc"] = "asc"

    @model_validator(mode="after")
    def bounded_offset(self) -> Self:
        if (self.page - 1) * self.limit > 10_000:
            raise ValueError("Pagination offset must not exceed 10000; narrow the filters.")
        return self

    @field_validator("order", mode="before")
    @classmethod
    def normalize_order(cls, value: object) -> object:
        return value.lower() if isinstance(value, str) else value

    def filters(self) -> dict[str, FilterValue]:
        return self.model_dump(
            exclude={"page", "limit", "search", "order", "sort_by"}, exclude_none=True
        )


class NoteListParams(ResourceListParams):
    subject: str | None = Field(default=None, max_length=200)
    course_id: int | None = Field(default=None, gt=0, le=9_007_199_254_740_991)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    sort_by: Literal["position", "id", "title", "subject", "created_at", "updated_at"] = "position"


class GoalListParams(NoteListParams):
    goal_id: int | None = Field(default=None, gt=0, le=9_007_199_254_740_991)
    sort_by: Literal[
        "position", "id", "title", "subject", "deadline", "progress", "created_at", "updated_at"
    ] = "position"
    progress_min: int | None = Field(default=None, ge=0, le=100)
    progress_max: int | None = Field(default=None, ge=0, le=100)
    deadline_from: date | None = None
    deadline_to: date | None = None
    completed: bool | None = None

    @model_validator(mode="after")
    def validate_ranges(self) -> Self:
        if self.progress_min is not None and self.progress_max is not None:
            if self.progress_min > self.progress_max:
                raise ValueError("progress_min must not exceed progress_max.")
        if self.deadline_from and self.deadline_to and self.deadline_from > self.deadline_to:
            raise ValueError("deadline_from must not exceed deadline_to.")
        return self


class PlannerListParams(ResourceListParams):
    subject: str | None = Field(default=None, max_length=200)
    course_id: int | None = Field(default=None, gt=0, le=9_007_199_254_740_991)
    goal_id: int | None = Field(default=None, gt=0, le=9_007_199_254_740_991)
    sort_by: Literal[
        "position",
        "id",
        "subject",
        "time",
        "scheduled_date",
        "priority",
        "completed",
        "duration_minutes",
        "created_at",
        "updated_at",
    ] = "position"
    completed: bool | None = None
    priority: Literal["High", "Medium", "Low"] | None = None

    date_from: date | None = None
    date_to: date | None = None

    _dates = field_validator("date_from", "date_to", mode="before")(parse_calendar_date)

    @model_validator(mode="after")
    def valid_date_range(self) -> Self:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must not exceed date_to.")
        return self
