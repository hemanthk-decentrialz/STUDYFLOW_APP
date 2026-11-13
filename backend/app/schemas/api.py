from typing import Literal

from pydantic import BaseModel, Field


class ApiSuccess[T](BaseModel):
    ok: Literal[True] = True
    data: T


class ApiFailure(BaseModel):
    ok: Literal[False] = False
    error: str
    details: list[str] | None = None


class HealthResponse(BaseModel):
    status: Literal["ready", "unavailable"] = Field(
        description="Readiness, including required dependencies."
    )
    database: Literal["up", "down"]
