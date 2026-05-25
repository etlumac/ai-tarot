import asyncio
import contextvars
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from ai_tarot_reader_backend.configs import PostgresConfig

Base = declarative_base()

_session_var: contextvars.ContextVar[Optional[AsyncSession]] = contextvars.ContextVar(
    "db_session", default=None
)

class SessionContextError(RuntimeError):
    """Выбрасывается при несоответствии сессии репозитория и текущего контекста"""


class DatabaseConnection:
    def __init__(self, engine: AsyncEngine, factory: async_sessionmaker, db_config: PostgresConfig) -> None:
        self._engine = engine
        self._factory = factory
        self.config = db_config

    @property
    def factory(self) -> async_sessionmaker:
        """Возвращает фабрику сессий"""
        return self._factory

    def create_session(self) -> AsyncSession:
        """Создаёт новую сессию через фабрику"""
        return self._factory()

    async def check_connection(self, timeout: float = 5.0) -> bool:
        """
        Проверяет доступность базы данных.
        """
        try:
            async with asyncio.timeout(timeout):
                async with self._engine.connect() as conn:
                    await conn.execute(text("SELECT 1"))
                    return True
        except asyncio.TimeoutError:
            logger.error(f"Database connection check timed out after {timeout}s")
            return False
        except Exception as e:
            logger.error(f"Database connection check failed: {type(e).__name__}: {e}")
            return False

    async def init_schema(self) -> None:
        """
        Инициализирует схему БД на основе моделей, унаследованных от Base.
        """
        try:
            async with self._engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database schema initialized")

        except Exception as e:
            logger.error(f"Failed to initialize schema: {type(e).__name__}: {e}")
            raise

    async def close(self) -> None:
        """Закрывает пул соединений и освобождает ресурсы"""
        await self._engine.dispose()
        logger.info("Database connections closed")


def get_session() -> AsyncSession:
    """Возвращает текущую сессию из контекста"""
    session = _session_var.get()
    if session is None:
        raise SessionContextError(
            "Database session not initialized. "
            "Ensure you're calling this within a dependency-injected context."
        )
    return session


def init_db_connection(db_config: PostgresConfig) -> DatabaseConnection:
    """Создаёт engine и фабрику сессий на основе конфигурации"""
    password = db_config.password.get_secret_value() if db_config.password else ""

    database_url = f"postgresql+asyncpg://{db_config.username}:{password}@{db_config.host}:{db_config.port}/{db_config.database}"

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=db_config.pool_size,
        connect_args={"server_settings": {"search_path": "public"}}
    )

    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autobegin=False,
    )
    logger.info(
        f"Database connection initialized: {db_config.host}:{db_config.port}/{db_config.database}"
    )
    return DatabaseConnection(engine, factory, db_config)


@asynccontextmanager
async def session_lifespan(db: DatabaseConnection) -> AsyncGenerator[None, None]:
    """Зависимость для создания сессии на время запроса"""
    session = db.create_session()
    logger.debug("Database session initialized")
    session.info["session_token"] = str(uuid.uuid4())
    _session_var.set(session)

    try:
        yield
    finally:
        await session.close()
        logger.debug("Database session closed")
        _session_var.set(None)


@asynccontextmanager
async def session_block() -> AsyncGenerator[None, None]:
    """Зависимость для блокировки доступа к сессии"""
    logger.debug("Database session blocked")
    _session_var.set(None)

    try:
        yield
    finally:
        pass

