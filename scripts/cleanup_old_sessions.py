"""
Использование:
    python scripts/cleanup_old_sessions.py --once
    python scripts/cleanup_old_sessions.py --once --days 7
    python scripts/cleanup_old_sessions.py
"""

import argparse
import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger
from sqlalchemy import text

_SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "ai-tarot-reader-backend"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from ai_tarot_reader_backend.configs import PathSettings, set_config, get_config

APP_DIR = Path(__file__).resolve().parent.parent / "src" / "ai-tarot-reader-backend"


async def cleanup_sessions(days: int) -> int:
    from ai_tarot_reader_backend.core.database import init_db_connection

    config = get_config()
    db = init_db_connection(config.postgres)

    try:
        async with db._engine.begin() as conn:
            count = await conn.scalar(
                text(
                    "SELECT COUNT(*) FROM public.sessions "
                    "WHERE created_at < NOW() - (:days || ' days')::interval"
                ),
                {"days": str(days)},
            )

            if count and count > 0:
                await conn.execute(
                    text(
                        "DELETE FROM public.sessions "
                        "WHERE created_at < NOW() - (:days || ' days')::interval"
                    ),
                    {"days": str(days)},
                )
                logger.info(
                    "Удалено {} сессий старше {} дней (cutoff: {})",
                    count, days, datetime.now(timezone.utc).isoformat(),
                )
            else:
                logger.info("Нет сессий старше {} дней для удаления.", days)

            return count or 0
    finally:
        await db.close()


async def run_once(days: int) -> None:
    logger.info("Запуск одноразовой очистки (порог: {} дней)...", days)
    deleted = await cleanup_sessions(days)
    logger.info("Готово. Удалено сессий: {}", deleted)


async def run_loop(days: int, interval_seconds: int) -> None:
    logger.info("Запуск циклической очистки: каждые {} сек, порог: {} дней", interval_seconds, days)
    while True:
        try:
            await cleanup_sessions(days)
        except Exception as e:
            logger.error("Ошибка при очистке: {}", e)
        await asyncio.sleep(interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="Очистка старых сессий из БД")
    parser.add_argument("--once", action="store_true", help="Одноразовый запуск")
    parser.add_argument("--days", type=int, default=None, help="Порог в днях (дефолт: 30)")
    args = parser.parse_args()

    set_config(PathSettings(
        yaml_path=str(APP_DIR / "config.yml"),
        env_path=str(APP_DIR / ".env.local"),
    ))
    config = get_config()
    days = args.days if args.days is not None else config.cleanup.sessions_older_than_days

    if args.once:
        asyncio.run(run_once(days))
    else:
        asyncio.run(run_loop(days, interval_seconds=86400))


if __name__ == "__main__":
    main()
