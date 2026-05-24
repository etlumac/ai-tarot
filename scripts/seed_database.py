import json
import os
import psycopg2
from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_CONFIG = {
    "host": "",
    "port": "",
    "dbname": "",
    "user": "",
    "password": "",
    "options": "",
}

DATA_DIR = PROJECT_ROOT / "data"
GRAPH_NAME = "tarot_graph"


def esc_cypher(s: str) -> str:
    if s is None:
        return "null"
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def build_meaning(desc: dict) -> str:
    if not desc or not isinstance(desc, dict):
        return ""
    parts = []
    for key in ("intro", "archetype", "key_meaning", "symbolism"):
        val = desc.get(key, "").strip()
        if val:
            parts.append(val)
    return "\n\n".join(parts)


def init_graph(cur):
    cur.execute("SELECT count(*) FROM ag_catalog.ag_graph WHERE name = %s", [GRAPH_NAME])
    exists = cur.fetchone()[0]
    if exists:
        cur.execute("SELECT drop_graph('%s', true)" % GRAPH_NAME)
        print(f"  [DROP] Старый граф '{GRAPH_NAME}' удалён")

    cur.execute("SELECT create_graph('%s')" % GRAPH_NAME)
    print(f"  [OK] Граф '{GRAPH_NAME}' создан")


def seed_cards(cur, cards):
    for i, card in enumerate(cards):
        card_id = i
        title = card.get("name", card.get("name_ru", ""))
        arcana = card.get("arcana", "major")
        meaning = build_meaning(card.get("description", {}))
        reversed_val = "false"

        meaning_escaped = esc_cypher(meaning)

        query = f"""
            SELECT * FROM cypher('{GRAPH_NAME}', $$
                CREATE (c:Card {{
                    card_id: {card_id},
                    title: {esc_cypher(title)},
                    meaning: {meaning_escaped},
                    arcana: {esc_cypher(arcana)},
                    reversed: {reversed_val}
                }})
                RETURN c
            $$) AS (v agtype)
        """
        cur.execute(query)

    print(f"  [OK] Создано {len(cards)} вершин Card")


def seed_relationships(cur, cards):
    slug_to_id = {card["slug"]: i for i, card in enumerate(cards)}

    seen = set()
    count = 0

    for card in cards:
        card1_slug = card["slug"]
        card1_id = slug_to_id[card1_slug]

        for combo in card.get("combinations", []):
            combo_slug = combo.get("combination_slug", "")
            short_meaning = combo.get("short_meaning", "")
            if not short_meaning:
                continue

            parts = combo_slug.split("-and-")
            if len(parts) != 2:
                continue

            card2_slug = parts[0] if parts[1] == card1_slug else parts[1]
            if card2_slug not in slug_to_id:
                continue
            card2_id = slug_to_id[card2_slug]

            pair = tuple(sorted([card1_id, card2_id]))
            if pair in seen:
                continue
            seen.add(pair)

            meaning_escaped = esc_cypher(short_meaning)

            query = f"""
                SELECT * FROM cypher('{GRAPH_NAME}', $$                     MATCH (a:Card {{card_id: {pair[0]}}})
                    MATCH (b:Card {{card_id: {pair[1]}}})
                    CREATE (a)-[r:Card_relationship {{
                        relation_id: {count},
                        from_card_id: {pair[0]},
                        to_card_id: {pair[1]},
                        meaning: {meaning_escaped}
                    }}]->(b)
                    RETURN r
                $$) AS (e agtype)
            """
            cur.execute(query)
            count += 1

    print(f"  [OK] Создано {count} рёбер Card_relationship")


def verify(cur):
    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH (c:Card)
            RETURN count(c) AS cnt
        $$) AS (cnt agtype)
    """)
    row = cur.fetchone()
    val = str(row[0])
    match = re.search(r'(\d+)', val)
    total_cards = int(match.group(1)) if match else 0
    print(f"\n  Card (вершины):         {total_cards}")

    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH ()-[r:Card_relationship]->()
            RETURN count(r) AS cnt
        $$) AS (cnt agtype)
    """)
    row = cur.fetchone()
    val = str(row[0])
    match = re.search(r'(\d+)', val)
    rel_count = int(match.group(1)) if match else 0
    print(f"  Card_relationship:      {rel_count}")

    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH (c:Card)
            WHERE c.card_id < 3
            RETURN c.card_id, c.title, c.arcana, c.reversed
            ORDER BY c.card_id
        $$) AS (cid agtype, title agtype, arcana agtype, rev agtype)
    """)
    print("\n  Пример карт:")
    for row in cur.fetchall():
        parts = []
        for v in row:
            s = str(v).strip('"').strip("'")
            if s:
                parts.append(s)
        print(f"    {' | '.join(parts)}")

    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH (a:Card)-[r:Card_relationship]->(b:Card)
            WHERE a.card_id = 0
            RETURN a.title, b.title, r.meaning
            LIMIT 5
        $$) AS (title1 agtype, title2 agtype, meaning agtype)
    """)
    print("\n  Пример комбинаций:")
    for row in cur.fetchall():
        parts = []
        for v in row:
            s = str(v).strip('"').strip("'")
            if s:
                parts.append(s)
        if len(parts) >= 3:
            print(f"    {parts[0]:25s} + {parts[1]:25s} = {parts[2]}")

    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH (c:Card)
            WHERE c.arcana = 'major'
            RETURN count(c) AS cnt
        $$) AS (cnt agtype)
    """)
    row = cur.fetchone()
    val = str(row[0])
    match = re.search(r'(\d+)', val)
    major = int(match.group(1)) if match else 0
    print(f"\n  Major arcana: {major}")
    print(f"  Minor arcana: {total_cards - major}")


def main():
    with open(DATA_DIR / "tarot_cards.json", "r", encoding="utf-8") as f:
        cards = json.load(f)
    print(f"Загружено {len(cards)} карт из tarot_cards.json\n")

    print(f"Подключение к {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        print("0. Загрузка Apache AGE...")
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path TO ag_catalog, public;")
        print("  [OK] AGE загружен")

        print("\n1. Инициализация графа...")
        init_graph(cur)

        print("\n2. Создание вершин Card...")
        seed_cards(cur, cards)

        print("\n3. Создание рёбер Card_relationship...")
        seed_relationships(cur, cards)

        verify(cur)

        print(f"\n{'='*50}")
        print(f"Граф '{GRAPH_NAME}' загружен")
        print(f"{'='*50}")

    except Exception as e:
        print(f"\n[ОШИБКА] {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
