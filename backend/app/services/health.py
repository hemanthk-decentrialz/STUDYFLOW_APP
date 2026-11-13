import asyncio
import logging
from typing import Literal

from sqlalchemy import text

from app.db.session import engine
from app.schemas.api import HealthResponse

logger = logging.getLogger("studyflow.health")


class HealthService:
    async def readiness(self) -> HealthResponse:
        database: Literal["up", "down"] = "down"
        try:
            async with asyncio.timeout(3):
                async with engine.connect() as connection:
                    await connection.execute(text("SELECT 1"))
                database = "up"
        except Exception:
            logger.critical("database_readiness_failed")
        return HealthResponse(
            status="ready" if database == "up" else "unavailable",
            database=database,
        )
