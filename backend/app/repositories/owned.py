import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApiError
from app.models.course import Course
from app.models.user import User

logger = logging.getLogger("studyflow.repositories.owned")


class OwnedRepository:
    def __init__(self, session: AsyncSession, user_id: UUID) -> None:
        self.session = session
        self.user_id = user_id

    async def active_course(self, course_id: int) -> Course | None:
        return await self.session.scalar(
            select(Course).where(
                Course.id == course_id, Course.user_id == self.user_id, Course.deleted_at.is_(None)
            )
        )

    async def lock_owner(self, *, allow_reset: bool = False) -> None:
        logger.debug("owner_write_lock_requested")
        # Serialize mutations and reset for one owner, never between unrelated users.
        owner = await self.session.scalar(
            select(User).where(User.id == self.user_id).with_for_update()
        )
        if owner is None:
            raise ApiError(401, "Please log in to continue.")

        if owner.reset_in_progress and not allow_reset:
            raise ApiError(409, "A data reset is in progress. Please wait for completion.")
