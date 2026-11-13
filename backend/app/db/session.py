import logging
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

logger = logging.getLogger("studyflow.database")

settings = get_settings()
engine = create_async_engine(
    settings.DATABASE_URL.get_secret_value(),
    pool_pre_ping=True,
    hide_parameters=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    connect_args={
        "command_timeout": settings.DB_COMMAND_TIMEOUT,
        "timeout": settings.DB_POOL_TIMEOUT,
    },
)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        # Depends(scope="function") commits before FastAPI sends the response.
        try:
            async with session.begin():
                yield session
        except Exception:
            logger.warning("request_transaction_rolled_back")
            raise
        else:
            logger.debug("request_transaction_committed")
