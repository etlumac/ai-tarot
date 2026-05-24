import json
import psycopg2
from psycopg2.extras import execute_values
from pathlib import Path

DB_CONFIG = {
    "host": "",
    "port": 0,
    "dbname": "",
    "user": "",
    "password": "",
    "options": "",
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
GOLD_DIR = DATA_DIR / "gold_cards"
PINK_DIR = DATA_DIR / "pink_cards"

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


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def init_schema(cur):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id          SERIAL PRIMARY KEY,
            slug        VARCHAR(100) UNIQUE NOT NULL,
            name        VARCHAR(200) NOT NULL,
            name_en     VARCHAR(200),
            arcana      VARCHAR(20) NOT NULL,
            suit        VARCHAR(20),
            rank_order  INTEGER NOT NULL,
            description JSONB
        );

        CREATE TABLE IF NOT EXISTS card_images (
            id          SERIAL PRIMARY KEY,
            card_id     INTEGER REFERENCES cards(id) ON DELETE CASCADE,
            theme       VARCHAR(50) NOT NULL,
            filename    VARCHAR(200) NOT NULL,
            UNIQUE(card_id, theme)
        );

        CREATE TABLE IF NOT EXISTS card_combinations (
            id              SERIAL PRIMARY KEY,
            card1_id        INTEGER REFERENCES cards(id) ON DELETE CASCADE,
            card2_id        INTEGER REFERENCES cards(id) ON DELETE CASCADE,
            short_meaning   TEXT NOT NULL,
            UNIQUE(card1_id, card2_id)
        );

        CREATE INDEX IF NOT EXISTS idx_cards_slug ON cards(slug);
        CREATE INDEX IF NOT EXISTS idx_cards_arcana ON cards(arcana);
        CREATE INDEX IF NOT EXISTS idx_card_images_card ON card_images(card_id);
        CREATE INDEX IF NOT EXISTS idx_card_images_theme ON card_images(theme);
        CREATE INDEX IF NOT EXISTS idx_combos_card1 ON card_combinations(card1_id);
        CREATE INDEX IF NOT EXISTS idx_combos_card2 ON card_combinations(card2_id);
    """)
    print("  [OK] Таблицы созданы / проверены")


def seed_cards(cur, cards):
    rows = []
    for i, card in enumerate(cards):
        slug = card["slug"]
        name = card.get("name", card.get("name_ru", slug))
        arcana = card.get("arcana", "major")
        name_en = card.get("name_en", card.get("id", ""))

        suit = None
        if arcana == "minor":
            for s in SUITS:
                if f"-of-{s}" in slug:
                    suit = s
                    break

        desc = card.get("description", {})
        rows.append((slug, name, name_en, arcana, suit, i, json.dumps(desc, ensure_ascii=False)))

    execute_values(cur, """
        INSERT INTO cards (slug, name, name_en, arcana, suit, rank_order, description)
        VALUES %s
        ON CONFLICT (slug) DO UPDATE SET
            name = EXCLUDED.name,
            name_en = EXCLUDED.name_en,
            arcana = EXCLUDED.arcana,
            suit = EXCLUDED.suit,
            rank_order = EXCLUDED.rank_order,
            description = EXCLUDED.description
    """, rows)
    print(f"  [OK] Загружено {len(rows)} карт")

    cur.execute("SELECT slug, id FROM cards")
    return {row[0]: row[1] for row in cur.fetchall()}


def seed_images(cur, cards, slug_to_id):
    rows = []
    for card in cards:
        slug = card["slug"]
        db_id = slug_to_id.get(slug)
        if not db_id:
            continue

        filename = slug_to_filename(slug)

        if (GOLD_DIR / f"{filename}.webp").exists():
            rows.append((db_id, "gold", f"{filename}.webp"))

        if (PINK_DIR / f"{filename}.webp").exists():
            rows.append((db_id, "pink", f"{filename}.webp"))

    execute_values(cur, """
        INSERT INTO card_images (card_id, theme, filename)
        VALUES %s
        ON CONFLICT (card_id, theme) DO UPDATE SET filename = EXCLUDED.filename
    """, rows)
    print(f"  [OK] Загружено {len(rows)} картинок")


def seed_combinations(cur, cards, slug_to_id):
    seen = set()
    rows = []

    for card in cards:
        card1_slug = card["slug"]
        card1_id = slug_to_id.get(card1_slug)
        if not card1_id:
            continue

        for combo in card.get("combinations", []):
            combo_slug = combo.get("combination_slug", "")
            short_meaning = combo.get("short_meaning", "")
            if not short_meaning:
                continue

            parts = combo_slug.split("-and-")
            if len(parts) != 2:
                continue

            card2_slug = parts[1]
            card2_id = slug_to_id.get(card2_slug)
            if not card2_id:
                continue

            pair = (min(card1_id, card2_id), max(card1_id, card2_id))
            if pair in seen:
                continue
            seen.add(pair)
            rows.append((pair[0], pair[1], short_meaning))

    execute_values(cur, """
        INSERT INTO card_combinations (card1_id, card2_id, short_meaning)
        VALUES %s
        ON CONFLICT (card1_id, card2_id) DO UPDATE SET short_meaning = EXCLUDED.short_meaning
    """, rows)
    print(f"  [OK] Загружено {len(rows)} комбинаций")


def main():
    with open(DATA_DIR / "tarot_cards.json", "r", encoding="utf-8") as f:
        cards = json.load(f)
    print(f"Загружено {len(cards)} карт из tarot_cards.json\n")

    print(f"Подключение к {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}...")
    conn = get_connection()
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("1. Инициализация схемы...")
        init_schema(cur)
        conn.commit()

        print("2. Загрузка карт...")
        slug_to_id = seed_cards(cur, cards)
        conn.commit()

        print("3. Загрузка картинок...")
        seed_images(cur, cards, slug_to_id)
        conn.commit()

        print("4. Загрузка комбинаций...")
        seed_combinations(cur, cards, slug_to_id)
        conn.commit()

        print("\n── Проверка ──")
        cur.execute("SELECT COUNT(*) FROM cards")
        print(f"  cards:              {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM card_images")
        print(f"  card_images:        {cur.fetchone()[0]}")
        cur.execute("SELECT COUNT(*) FROM card_combinations")
        print(f"  card_combinations:  {cur.fetchone()[0]}")

        cur.execute("SELECT slug, name, arcana FROM cards LIMIT 3")
        print("\n  Пример карт:")
        for row in cur.fetchall():
            print(f"    {row[0]:30s} | {row[1]:25s} | {row[2]}")

        cur.execute("""
            SELECT c.name, ci.theme, ci.filename
            FROM card_images ci
            JOIN cards c ON c.id = ci.card_id
            LIMIT 4
        """)
        print("\n  Пример картинок:")
        for row in cur.fetchall():
            print(f"    {row[0]:25s} | {row[1]:5s} | {row[2]}")

        print(f"\n{'='*50}")
        print("Все данные загружены в БД.")
        print(f"{'='*50}")

    except Exception as e:
        conn.rollback()
        print(f"\n[ОШИБКА] {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
