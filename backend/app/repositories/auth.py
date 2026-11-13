import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ApiError
from app.models.auth_session import AuthSession
from app.models.user import User

logger = logging.getLogger("studyflow.repositories.auth")


class AuthRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def find_by_email(self, email: str) -> User | None:
        logger.debug("repository_operation operation=find_by_email")
        return await self.session.scalar(select(User).where(User.email == email))

    async def create_user(self, name: str, email: str, password_hash: str) -> User:
        logger.debug("repository_operation operation=create_user")
        user = User(name=name, email=email, password_hash=password_hash)
        self.session.add(user)
        await self.session.flush()
        return user

    async def add_session(self, token_hash: str, user_id: UUID, expires_at: datetime) -> None:
        logger.debug("repository_operation operation=add_session")
        self.session.add(AuthSession(token_hash=token_hash, user_id=user_id, expires_at=expires_at))
        await self.session.flush()

    async def resolve_user(self, token_hash: str) -> User | None:
        logger.debug("repository_operation operation=resolve_user")
        return await self.session.scalar(
            select(User)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(
                AuthSession.token_hash == token_hash,
                AuthSession.expires_at > datetime.now(UTC),
            )
        )

    async def revoke(self, token_hash: str) -> None:
        logger.debug("repository_operation operation=revoke")
        await self.session.execute(delete(AuthSession).where(AuthSession.token_hash == token_hash))

    async def update_name(self, user_id: UUID, name: str) -> User:
        logger.debug("repository_operation operation=update_profile")
        user = await self.session.scalar(select(User).where(User.id == user_id).with_for_update())
        if user is None:
            raise ApiError(401, "Please log in to continue.")
        user.name = name
        await self.session.flush()
        return user
