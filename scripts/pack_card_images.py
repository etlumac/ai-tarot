from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
ARCHIVE = DATA_DIR / "tarot_cards.zip"


def main():
    gold = DATA_DIR / "gold_cards"
    pink = DATA_DIR / "pink_cards"

    if not gold.exists():
        print(f"[ERR] Нет папки: {gold}")
        return
    if not pink.exists():
        print(f"[ERR] Нет папки: {pink}")
        return

    gold_files = list(gold.iterdir())
    pink_files = list(pink.iterdir())
    print(f"gold_cards: {len(gold_files)} файлов")
    print(f"pink_cards: {len(pink_files)} файлов")

    if ARCHIVE.exists():
        ARCHIVE.unlink()

    with open(ARCHIVE, "wb") as f_out:
        import zipfile
        with zipfile.ZipFile(f_out, "w", zipfile.ZIP_STORED) as zf:
            for p in gold_files:
                if p.is_file():
                    zf.write(p, f"gold_cards/{p.name}")
            for p in pink_files:
                if p.is_file():
                    zf.write(p, f"pink_cards/{p.name}")

    size_mb = ARCHIVE.stat().st_size / (1024 * 1024)
    print(f"\nГотово: {ARCHIVE} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
