import logging

from sqlalchemy import select

from app.models.job import Job
from app.models.user import User
from app.repositories.owned import OwnedRepository

logger = logging.getLogger("studyflow.repositories.jobs")


class JobRepository(OwnedRepository):
    async def current(self) -> Job | None:
        logger.debug("repository_operation operation=current")
        return await self.session.scalar(
            select(Job)
            .where(Job.user_id == self.user_id, Job.kind == "study-data-reset")
            .order_by(Job.created_at.desc(), Job.id.desc())
            .limit(1)
        )

    async def enqueue_reset(self) -> Job:
        logger.debug("repository_operation operation=enqueue_reset")
        await self.lock_owner(allow_reset=True)
        existing = await self.current()
        if existing and existing.status in {"queued", "running"}:
            return existing
        owner = await self.session.get(User, self.user_id)
        assert owner is not None
        owner.reset_in_progress = True
        job = Job(user_id=self.user_id, kind="study-data-reset", status="queued")
        self.session.add(job)
        await self.session.flush()
        await self.session.refresh(job)
        return job
