import json
import os
import psycopg2
from pathlib import Path


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
GOLD_DIR = DATA_DIR / "gold_cards"
PINK_DIR = DATA_DIR / "pink_cards"
GRAPH_NAME = "tarot_graph"

MAJOR_ORDER = [
    "the-fool", "the-magician", "the-high-priestess", "the-empress",
    "the-emperor", "the-hierophant", "the-lovers", "the-chariot",
    "strength", "the-hermit", "wheel-of-fortune", "justice",
    "the-hanged-man", "death", "temperance", "the-devil",
    "the-tower", "the-star", "the-moon", "the-sun",
    "judgement", "the-world",
]

SUITS = ["wands", "cups", "swords", "pentacles"]


def slug_to_filename(slug: str) -> str:
    slug = slug.lower().replace(" ", "-")
    for i, m_slug in enumerate(MAJOR_ORDER):
        if slug == m_slug or slug == f"the-{m_slug}":
            return f"{i:02d}_{m_slug}"
    from re import match
    m = match(r"^([\w-]+)-of-(\w+)$", slug)
    if m:
        rank_raw, suit = m.group(1), m.group(2)
        rank_map = {
            "ace": "ace", "two": "02", "2": "02", "three": "03", "3": "03",
            "four": "04", "4": "04", "five": "05", "5": "05",
            "six": "06", "6": "06", "seven": "07", "7": "07",
            "eight": "08", "8": "08", "nine": "09", "9": "09",
            "ten": "10", "page": "page", "knight": "knight",
            "queen": "queen", "king": "king",
        }
        rank = rank_map.get(rank_raw)
        if rank and suit in SUITS:
            return f"{suit}_{rank}"
    return slug


def esc_cypher(s: str) -> str:
    if s is None:
        return "null"
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


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
        slug = card["slug"]
        name = card.get("name", card.get("name_ru", slug))
        arcana = card.get("arcana", "major")
        name_en = card.get("name_en", card.get("id", ""))

        suit = "null"
        if arcana == "minor":
            for s in SUITS:
                if f"-of-{s}" in slug:
                    suit = esc_cypher(s)
                    break

        desc = card.get("description", {})
        desc_str = json.dumps(desc, ensure_ascii=False)
        desc_str = desc_str.replace("\\", "\\\\").replace("'", "\\'")

        filename = slug_to_filename(slug)
        gold_img = f"{filename}.webp" if (GOLD_DIR / f"{filename}.webp").exists() else ""
        pink_img = f"{filename}.webp" if (PINK_DIR / f"{filename}.webp").exists() else ""

        query = f"""
            SELECT * FROM cypher('{GRAPH_NAME}', $$
                CREATE (c:Card {{
                    slug: {esc_cypher(slug)},
                    name: {esc_cypher(name)},
                    name_en: {esc_cypher(name_en)},
                    arcana: {esc_cypher(arcana)},
                    suit: {suit},
                    rank_order: {i},
                    description: '{desc_str}',
                    gold_image: {esc_cypher(gold_img)},
                    pink_image: {esc_cypher(pink_img)}
                }})
                RETURN c
            $$) AS (v agtype)
        """
        cur.execute(query)

    print(f"  [OK] Создано {len(cards)} вершин Card")


def seed_combinations(cur, cards):
    seen = set()
    count = 0

    for card in cards:
        card1_slug = card["slug"]

        for combo in card.get("combinations", []):
            combo_slug = combo.get("combination_slug", "")
            short_meaning = combo.get("short_meaning", "")
            if not short_meaning:
                continue

            parts = combo_slug.split("-and-")
            if len(parts) != 2:
                continue

            card2_slug = parts[1]

            pair = tuple(sorted([card1_slug, card2_slug]))
            if pair in seen:
                continue
            seen.add(pair)

            meaning_escaped = esc_cypher(short_meaning)

            query = f"""
                SELECT * FROM cypher('{GRAPH_NAME}', $$
                    MATCH (a:Card {{slug: "{pair[0]}"}})
                    MATCH (b:Card {{slug: "{pair[1]}"}})
                    CREATE (a)-[r:COMBINES_WITH {{short_meaning: {meaning_escaped}}}]->(b)
                    RETURN r
                $$) AS (e agtype)
            """
            cur.execute(query)
            count += 1

    print(f"  [OK] Создано {count} рёбер COMBINES_WITH")


def verify(cur):
    print("\n── Проверка ──")

    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH (c:Card)
            RETURN count(c) AS cnt
        $$) AS (cnt agtype)
    """)
    row = cur.fetchone()

    import re
    val = row[0]
    match = re.search(r'(\d+)', str(val))
    cnt = int(match.group(1)) if match else 0
    total_cards = cnt
    print(f"  Card (вершины):    {cnt}")

    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH ()-[r:COMBINES_WITH]->()
            RETURN count(r) AS cnt
        $$) AS (cnt agtype)
    """)
    row = cur.fetchone()
    val = row[0]
    match = re.search(r'(\d+)', str(val))
    cnt = int(match.group(1)) if match else 0
    print(f"  COMBINES_WITH:     {cnt}")

    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH (c:Card)
            WHERE c.rank_order < 3
            RETURN c.slug, c.name, c.arcana, c.gold_image, c.pink_image
            ORDER BY c.rank_order
        $$) AS (slug agtype, name agtype, arcana agtype, gold agtype, pink agtype)
    """)
    print("\n  Пример карт:")
    for row in cur.fetchall():
        slug = row[0]
        name = row[1]
        arcana = row[2]
        for val in [slug, name, arcana]:
            s = str(val).strip('"').strip("'")
            if s:
                print(f"    {s}", end=" | ")
        print()

    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH (a:Card)-[r:COMBINES_WITH]->(b:Card)
            WHERE a.rank_order = 0
            RETURN a.name, b.name, r.short_meaning
            LIMIT 5
        $$) AS (name1 agtype, name2 agtype, meaning agtype)
    """)
    print("\n  Пример комбинаций:")
    for row in cur.fetchall():
        parts = []
        for val in row:
            s = str(val).strip('"').strip("'")
            if s:
                parts.append(s)
        if len(parts) >= 3:
            print(f"    {parts[0]:25s} + {parts[1]:25s} = {parts[2]}")

    cur.execute(f"""
        SELECT * FROM cypher('{GRAPH_NAME}', $$
            MATCH (c:Card)
            WHERE c.suit IS NOT NULL
            RETURN count(c) AS cnt
        $$) AS (cnt agtype)
    """)
    row = cur.fetchone()
    val = str(row[0])
    match = re.search(r'(\d+)', val)
    minor = int(match.group(1)) if match else 0
    print(f"\n  Minor (suit != null): {minor}")
    print(f"  Major (suit = null):  {total_cards - minor}")


def main():
    with open(DATA_DIR / "tarot_cards.json", "r", encoding="utf-8") as f:
        cards = json.load(f)
    print(f"Загружено {len(cards)} карт из tarot_cards.json\n")

    print(f"Подключение к {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        print("Загрузка Apache AGE...")
        cur.execute("LOAD 'age';")
        cur.execute("SET search_path TO ag_catalog, public;")
        print("  [OK] AGE загружен")

        print("\n1. Инициализация графа...")
        init_graph(cur)

        print("\n2. Создание вершин Card...")
        seed_cards(cur, cards)

        print("\n3. Создание рёбер COMBINES_WITH...")
        seed_combinations(cur, cards)

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
