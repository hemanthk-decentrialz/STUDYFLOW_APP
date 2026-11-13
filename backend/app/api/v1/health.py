from fastapi import APIRouter, Response

from app.schemas.api import HealthResponse
from app.services.health import HealthService

router = APIRouter(tags=["operations"])


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
    summary="Check PostgreSQL readiness",
)
async def health(response: Response) -> HealthResponse:
    result = await HealthService().readiness()
    response.status_code = 200 if result.status == "ready" else 503
    return result
