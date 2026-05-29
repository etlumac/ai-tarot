from typing import Optional
from sqlalchemy import text
from ai_tarot_reader_backend.core.database import get_session


class CardGraphRepository:

    @staticmethod
    async def get_card_data(card_id: int) -> Optional[dict]:
        session = get_session()
        async with session.begin():
            await session.execute(text("LOAD 'age'"))
            await session.execute(text("SET search_path TO ag_catalog, public"))
            result = await session.execute(
                text(f"""
                    SELECT card_id, title, meaning
                    FROM cypher('tarot_graph', $$
                        MATCH (c:Card)
                        WHERE c.card_id = {card_id}
                        RETURN c.card_id, c.title, c.meaning
                    $$) AS (card_id agtype, title agtype, meaning agtype)
                """)
            )
            row = result.fetchone()
            if not row:
                return None
            return {
                "card_id": card_id,
                "title": str(row[1]).strip('"'),
                "meaning": str(row[2]).strip('"'),
            }