import logging

from app.repositories.jobs import JobRepository
from app.schemas.jobs import JobResponse

logger = logging.getLogger("studyflow.services.jobs")


class JobService:
    def __init__(self, repository: JobRepository) -> None:
        self.repository = repository

    async def enqueue_reset(self) -> JobResponse:
        logger.info("data_reset_requested")
        return JobResponse.model_validate(await self.repository.enqueue_reset())

    async def current(self) -> JobResponse | None:
        job = await self.repository.current()
        return JobResponse.model_validate(job) if job else None
