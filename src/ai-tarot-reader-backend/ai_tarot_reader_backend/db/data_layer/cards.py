from itertools import combinations
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

    @staticmethod
    async def get_combination(card_id1: int, card_id2: int) -> Optional[str]:
        session = get_session()
        async with session.begin():
            await session.execute(text("LOAD 'age'"))
            await session.execute(text("SET search_path TO ag_catalog, public"))
            result = await session.execute(
                text(f"""
                    SELECT meaning FROM cypher('tarot_graph', $$
                        MATCH (a:Card)-[r:Card_relationship]->(b:Card)
                        WHERE (a.card_id = {card_id1} AND b.card_id = {card_id2})
                           OR (a.card_id = {card_id2} AND b.card_id = {card_id1})
                        RETURN r.meaning
                    $$) AS (meaning agtype)
                    LIMIT 1
                """)
            )
            row = result.fetchone()
            return str(row[0]).strip('"') if row else None

    @staticmethod
    async def get_combinations_for_spread(card_ids: list[int]) -> list[str]:
        results = []
        for id1, id2 in combinations(card_ids, 2):
            meaning = await CardGraphRepository.get_combination(id1, id2)
            if meaning:
                results.append(f"Карта {id1} + Карта {id2}: {meaning}")
        return results