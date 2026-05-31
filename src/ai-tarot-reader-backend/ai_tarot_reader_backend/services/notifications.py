import uuid
import json
from typing import Callable
from loguru import logger
from contextlib import asynccontextmanager
from ai_tarot_reader_backend.core.database import DatabaseConnection
from asyncpg.exceptions import ConnectionDoesNotExistError


class StreamingNotificationsService:
    def __init__(self, db: DatabaseConnection):
        self.db = db

    @staticmethod
    def get_channel_name(session_id: uuid.UUID) -> str:
        return f"session_{str(session_id).replace('-', '_')}"

    async def notify_session(self, session_id: uuid.UUID, event_type: str, data: dict):
        payload = json.dumps({"type": event_type, "data": data}, ensure_ascii=False)
        async with self.db.notifications_pool.acquire() as conn:
            await conn.execute(f"NOTIFY {self.get_channel_name(session_id)}, '{payload}'")

    @asynccontextmanager
    async def session_listener(
            self,
            session_id: uuid.UUID,
            *,
            handler: Callable[[str], None]
    ):
        conn = await self.db.notifications_pool.acquire()

        def _pg_callback(_, __, ___, payload: str):
            try:
                handler(payload)
            except Exception:
                # Ошибка в обработчике не должна ронять соединение asyncpg
                logger.exception(f"Unhandled error in NOTIFY callback for '{session_id}'")

        try:
            await conn.add_listener(self.get_channel_name(session_id), _pg_callback)
            try:
                yield  # Время жизни подписки (SSE-стрим, фоновый цикл и т.д.)
            finally:
                # 1. Отписка всегда происходит ДО возврата соединения в пул
                try:
                    await conn.remove_listener(self.get_channel_name(session_id), _pg_callback)
                except ConnectionDoesNotExistError:
                    pass  # Соединение уже разорвано сетью/сервером
                except Exception as e:
                    logger.warning(f"Failed to remove listener '{session_id}': {e}")
        finally:
            # 2. Возврат соединения в пул (гарантирован даже при падении add_listener)
            try:
                await self.db.notifications_pool.release(conn)
            except Exception as e:
                logger.warning(f"Failed to release connection for '{session_id}': {e}")

