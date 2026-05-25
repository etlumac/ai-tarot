from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import asyncpg
from loguru import logger
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from ai_tarot_reader_backend.core.database import SessionContextError, get_session
from ai_tarot_reader_backend.core.errors import (
    BaseAppError,
    InfrastructureError,
    NotFoundError,
    ResourceAlreadyExistsError,
    ValidationError,
)


@asynccontextmanager
async def transactional() -> AsyncGenerator[AsyncSession, None]:
    session: AsyncSession = get_session()

    if session.get_transaction() is not None:
        yield session
        return

    try:
        async with session.begin():
            yield session
    except IntegrityError as e:
        await _map_integrity_error(e)
    except OperationalError as e:
        logger.error(f"DB OperationalError: {e}")
        raise InfrastructureError(
            user_message="Database not available", developer_message=str(e)
        ) from e
    except SessionContextError:
        raise
    except Exception as e:
        logger.exception(f"Unexpected DB error: {type(e).__name__}")
        raise BaseAppError(
            user_message="Unknown server error", developer_message=str(e)
        ) from e


async def _map_integrity_error(e: IntegrityError) -> None:
    orig = getattr(e, "orig", None)

    if isinstance(orig, asyncpg.exceptions.UniqueViolationError):
        raise ResourceAlreadyExistsError(
            user_message="Resource already exists", developer_message=str(e)
        ) from e

    if isinstance(orig, asyncpg.exceptions.ForeignKeyViolationError):
        raise NotFoundError(
            user_message="Resource not found", developer_message=str(e)
        ) from e

    if isinstance(orig, asyncpg.exceptions.CheckViolationError):
        raise ValidationError(
            user_message="Database validation failed", developer_message=str(e)
        ) from e

    raise BaseAppError(
        user_message="Unknown database integrity error", developer_message=str(e)
    ) from e
