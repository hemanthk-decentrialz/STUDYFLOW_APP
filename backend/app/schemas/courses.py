from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.resources import RequestModel, ResourceListParams, ResourcePatch, SafeId, Title


class CourseCreate(RequestModel):
    id: SafeId
    title: Title
    description: str = Field(default="", max_length=2000, strict=True)


class CoursePatch(ResourcePatch):
    title: Title | None = None
    description: str | None = Field(default=None, max_length=2000, strict=True)


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str


class CourseListParams(ResourceListParams):
    sort_by: Literal["position", "title", "created_at", "updated_at", "id"] = "position"
