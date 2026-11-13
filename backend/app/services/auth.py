import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.exceptions import ApiError
from app.core.security import (
    create_session_token,
    digest_session_token,
    hash_password,
    verify_password,
)
from app.repositories.auth import AuthRepository
from app.schemas.auth import LoginRequest, ProfilePatch, SessionUser, SignupRequest

logger = logging.getLogger("studyflow.services.auth")


class AuthService:
    def __init__(self, repository: AuthRepository, settings: Settings) -> None:
        self.repository = repository
        self.settings = settings

    async def signup(self, payload: SignupRequest) -> SessionUser:
        logger.info("account_signup_started")
        email = str(payload.email).lower()
        if await self.repository.find_by_email(email) is not None:
            raise ApiError(409, "An account with this email already exists.")
        password_hash = await hash_password(payload.password)
        try:
            async with self.repository.session.begin_nested():
                user = await self.repository.create_user(payload.name, email, password_hash)
        except IntegrityError as exc:
            # The unique DB constraint also handles concurrent signups for one email.
            raise ApiError(409, "An account with this email already exists.") from exc
        return SessionUser.model_validate(user)

    async def login(self, payload: LoginRequest, old_token: str | None) -> tuple[SessionUser, str]:
        logger.info("session_creation_started")
        user = await self.repository.find_by_email(str(payload.email).lower())
        stored_hash = user.password_hash if user is not None else None
        valid = await verify_password(payload.password, stored_hash)
        if user is None or not valid:
            raise ApiError(401, "Invalid email or password.")
        if old_token:
            await self.repository.revoke(digest_session_token(old_token))
        token = create_session_token()
        expires = datetime.now(UTC) + timedelta(seconds=self.settings.SESSION_MAX_AGE_SECONDS)
        await self.repository.add_session(digest_session_token(token), user.id, expires)
        return SessionUser.model_validate(user), token

    async def current_user(self, token: str | None) -> SessionUser:
        if not token or len(token) > 256:
            raise ApiError(401, "Please log in to continue.")
        user = await self.repository.resolve_user(digest_session_token(token))
        if user is None:
            raise ApiError(401, "Your session has expired. Please log in again.")
        return SessionUser.model_validate(user)

    async def logout(self, token: str | None) -> None:
        logger.info("session_revocation_started")
        if token:
            await self.repository.revoke(digest_session_token(token))

    async def update_profile(self, user: SessionUser, payload: ProfilePatch) -> SessionUser:
        logger.info("profile_update_started")
        changes = payload.model_dump(exclude_unset=True)
        updated = await self.repository.update_name(user.id, changes["name"])
        return SessionUser.model_validate(updated)
