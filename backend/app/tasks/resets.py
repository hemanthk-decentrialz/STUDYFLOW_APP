import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.auth_session import AuthSession
from app.models.job import Job
from app.models.user import User
from app.repositories.settings import SettingsRepository

logger = logging.getLogger("studyflow.tasks")
_capacity = asyncio.Semaphore(2)


async def execute_reset(job_id: UUID) -> None:
    """Idempotent worker entry point reusable by a future external queue.

    Row locks claim one job; reset and job completion commit atomically. A
    process interruption rolls back to queued, allowing bounded recovery.
    """
    async with _capacity:
        try:
            async with SessionLocal() as session:
                async with session.begin():
                    job = await session.scalar(
                        select(Job)
                        .where(Job.id == job_id, Job.status == "queued")
                        .with_for_update(skip_locked=True)
                    )
                    if job is None:
                        return
                    owner_id = job.user_id
                    job.status = "running"
                    repository = SettingsRepository(session, owner_id)
                    await repository.reset_study_data(allow_reset=True)
                    owner = await session.get(User, owner_id)
                    assert owner is not None
                    owner.reset_in_progress = False
                    job.status = "completed"
                    job.completed_at = datetime.now(UTC)
            logger.info("background_reset_completed job_id=%s", job_id)
        except Exception as exc:
            logger.error(
                "background_reset_failed job_id=%s",
                job_id,
                exc_info=(type(exc), exc, exc.__traceback__),
            )
            try:
                async with SessionLocal() as session:
                    async with session.begin():
                        job = await session.scalar(
                            select(Job).where(Job.id == job_id).with_for_update()
                        )
                        if job is not None and job.status != "completed":
                            job.status = "failed"
                            job.error = "Reset could not be completed. Please request it again."
                            job.completed_at = datetime.now(UTC)
                            owner = await session.scalar(
                                select(User).where(User.id == job.user_id).with_for_update()
                            )
                            if owner is not None:
                                owner.reset_in_progress = False
            except Exception:
                # The queued transaction remains recoverable after DB recovery.
                logger.critical("background_reset_failure_record_unavailable job_id=%s", job_id)


class NativeTaskDispatcher:
    def enqueue_reset(self, tasks: BackgroundTasks, job_id: UUID) -> None:
        tasks.add_task(execute_reset, job_id)


async def recover_pending_jobs() -> None:
    while True:
        try:
            async with SessionLocal() as session:
                ids = list(
                    await session.scalars(
                        select(Job.id)
                        .where(Job.status == "queued")
                        .order_by(Job.created_at)
                        .limit(100)
                    )
                )
            async with SessionLocal() as cleanup:
                async with cleanup.begin():
                    expired = (
                        select(AuthSession.token_hash)
                        .where(AuthSession.expires_at <= datetime.now(UTC))
                        .limit(1000)
                    )
                    await cleanup.execute(
                        delete(AuthSession).where(AuthSession.token_hash.in_(expired))
                    )
            for job_id in ids:
                await execute_reset(job_id)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.error("background_job_recovery_unavailable")
        await asyncio.sleep(15)
