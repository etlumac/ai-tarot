import json
import os
import psycopg2
from pathlib import Path
from psycopg2.extras import execute_values

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

NUM_TO_WORD = {
    "02": "two",   "2": "two",
    "03": "three", "3": "three",
    "04": "four",  "4": "four",
    "05": "five",  "5": "five",
    "06": "six",   "6": "six",
    "07": "seven", "7": "seven",
    "08": "eight", "8": "eight",
    "09": "nine",  "9": "nine",
    "10": "ten",
}


def drop_all_tables(cur):
    for table in ("reviews", "messages", "sessions", "users", "images"):
        try:
            cur.execute(f"DROP TABLE IF EXISTS ag_catalog.{table} CASCADE;")
        except Exception:
            pass

    cur.execute("DROP TABLE IF EXISTS public.reviews CASCADE;")
    cur.execute("DROP TABLE IF EXISTS public.messages CASCADE;")
    cur.execute("DROP TABLE IF EXISTS public.sessions CASCADE;")
    cur.execute("DROP TABLE IF EXISTS public.images CASCADE;")
    cur.execute("DROP TABLE IF EXISTS public.users CASCADE;")
    print("  [OK] Все старые таблицы удалены")


def create_users_table(cur):
    cur.execute("""
        CREATE TABLE public.users (
            user_id     SERIAL PRIMARY KEY,
            ip_address  VARCHAR(45) NOT NULL,
            name        VARCHAR(255),
            description TEXT
        );
    """)
    print("  [OK] public.users создана")


def create_sessions_table(cur):
    cur.execute("""
        CREATE TABLE public.sessions (
            session_id          SERIAL PRIMARY KEY,
            tone                VARCHAR(20) NOT NULL DEFAULT 'neutral'
                CHECK (tone IN ('positive', 'neutral', 'negative')),
            status              VARCHAR(20) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'in_progress', 'done', 'failed')),
            stage               VARCHAR(20) NOT NULL DEFAULT 'prediction'
                CHECK (stage IN ('prediction', 'clarification')),
            theme               VARCHAR(20) NOT NULL DEFAULT 'other'
                CHECK (theme IN ('career', 'love', 'self', 'social', 'other', 'health')),
            prediction_cards    INTEGER[] NOT NULL DEFAULT '{}',
            clarification_card  INTEGER,
            user_id             INTEGER REFERENCES public.users(user_id),
            created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
            title               VARCHAR(255)
        );
    """)
    print("  [OK] public.sessions создана")


def create_messages_table(cur):
    cur.execute("""
        CREATE TABLE public.messages (
            message_id  SERIAL PRIMARY KEY,
            session_id  INTEGER NOT NULL REFERENCES public.sessions(session_id)
                ON DELETE CASCADE,
            role        VARCHAR(20) NOT NULL
                CHECK (role IN ('user', 'assistant', 'system')),
            content     TEXT NOT NULL
        );
    """)
    print("  [OK] public.messages создана")


def create_reviews_table(cur):
    cur.execute("""
        CREATE TABLE public.reviews (
            review_id  SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES public.sessions(session_id)
                ON DELETE CASCADE,
            rating     INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
            comment    TEXT,
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    print("  [OK] public.reviews создана")


def create_images_table(cur):
    cur.execute("""
        CREATE TABLE public.images (
            image_id   SERIAL PRIMARY KEY,
            card_id    INTEGER NOT NULL,
            ui_theme   VARCHAR(20) NOT NULL
                CHECK (ui_theme IN ('gold', 'pink')),
            image      BYTEA NOT NULL
        );
    """)
    print("  [OK] public.images создана")


def filename_to_card_id(filename_stem, slug_to_id):
    if "_" not in filename_stem:
        return None

    parts = filename_stem.split("_", 1)
    prefix, rest = parts[0], parts[1]

    if prefix.isdigit():
        for slug in (f"the-{rest}", rest):
            if slug in slug_to_id:
                return slug_to_id[slug]
        return None

    rank = NUM_TO_WORD.get(rest, rest)
    slug = f"{rank}-of-{prefix}"
    if slug in slug_to_id:
        return slug_to_id[slug]

    return None


def seed_images(cur):
    with open(DATA_DIR / "tarot_cards.json", "r", encoding="utf-8") as f:
        cards = json.load(f)

    slug_to_id = {card["slug"]: i for i, card in enumerate(cards)}

    rows = []
    count_gold = 0
    count_pink = 0

    if GOLD_DIR.exists():
        for f in sorted(GOLD_DIR.glob("*.webp")):
            card_id = filename_to_card_id(f.stem, slug_to_id)
            if card_id is None:
                print(f"  [WARN] Не найден card_id для {f.name}")
                continue
            data = f.read_bytes()
            rows.append((card_id, "gold", data))
            count_gold += 1

    if PINK_DIR.exists():
        for f in sorted(PINK_DIR.glob("*.webp")):
            card_id = filename_to_card_id(f.stem, slug_to_id)
            if card_id is None:
                print(f"  [WARN] Не найден card_id для {f.name}")
                continue
            data = f.read_bytes()
            rows.append((card_id, "pink", data))
            count_pink += 1

    if rows:
        execute_values(
            cur,
            "INSERT INTO public.images (card_id, ui_theme, image) VALUES %s",
            rows,
        )

    print(f"  [OK] Загружено {count_gold} gold + {count_pink} pink = {len(rows)} картинок")


def verify(cur):
    print("\n── Данные ──")
    for table in ("users", "sessions", "messages", "reviews", "images"):
        cur.execute(f"SELECT count(*) FROM public.{table}")
        cnt = cur.fetchone()[0]
        print(f"  {table:15s}: {cnt} строк")

    print("\n── Структура ──")
    for table in ("users", "sessions", "messages", "reviews", "images"):
        cur.execute(f"""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = '{table}'
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
        col_str = ", ".join(f"{c[0]} ({c[1]})" for c in cols)
        print(f"  {table}: {col_str}")

    print("\n── CHECK-ограничения ──")
    cur.execute("""
        SELECT constraint_name, check_clause
        FROM information_schema.check_constraints
        WHERE constraint_schema = 'public'
        ORDER BY constraint_name
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")


def main():
    print("Создание реляционных таблиц...\n")

    print(f"Подключение к {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['dbname']}...")
    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    try:
        print("Очистка...")
        cur.execute("SET search_path TO ag_catalog, public;")
        drop_all_tables(cur)

        print("\n1. Создание таблиц в public schema...")
        create_users_table(cur)
        create_sessions_table(cur)
        create_messages_table(cur)
        create_reviews_table(cur)
        create_images_table(cur)

        print("\n2. Загрузка картинок...")
        seed_images(cur)

        verify(cur)

        print(f"\n{'='*50}")
        print("Все таблицы созданы")
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
