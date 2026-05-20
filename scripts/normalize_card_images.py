import shutil
import re
from pathlib import Path
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

MAJOR_ORDER = [
    "the-fool", "the-magician", "the-high-priestess", "the-empress",
    "the-emperor", "the-hierophant", "the-lovers", "the-chariot",
    "strength", "the-hermit", "wheel-of-fortune", "justice",
    "the-hanged-man", "death", "temperance", "the-devil",
    "the-tower", "the-star", "the-moon", "the-sun",
    "judgement", "the-world",
]

SUITS = ["wands", "cups", "swords", "pentacles"]
RANK_WORDS = ["ace", "02", "03", "04", "05", "06", "07", "08", "09", "10",
              "page", "knight", "queen", "king"]

# rank-word → canonical rank
WORD_TO_RANK = {
    "ace": "ace", "a": "ace",
    "two": "02", "2": "02", "02": "02",
    "three": "03", "3": "03", "03": "03",
    "four": "04", "4": "04", "04": "04",
    "five": "05", "5": "05", "05": "05",
    "six": "06", "6": "06", "06": "06",
    "seven": "07", "7": "07", "07": "07",
    "eight": "08", "8": "08", "08": "08",
    "nine": "09", "9": "09", "09": "09",
    "ten": "10", "10": "10",
    "page": "page",
    "knight": "knight",
    "queen": "queen",
    "king": "king",
}


def build_canonical_map():
    """Вернёт dict: canonical_name (без .webp) → True для всех 78 карт."""
    names = {}
    for i, slug in enumerate(MAJOR_ORDER):
        names[f"{i:02d}_{slug}"] = True
    for suit in SUITS:
        for rank in RANK_WORDS:
            names[f"{suit}_{rank}"] = True
    return names


def parse_gold(filename: str):
    stem = Path(filename).stem.lower()
    m = re.match(r"^(\d{2})_(.+)$", stem)
    if m:
        num, name = m.group(1), m.group(2)
        name_h = name.replace("_", "-")
        try:
            idx = int(num)
            expected = MAJOR_ORDER[idx]
            if name_h == expected or name_h == f"the-{expected}" or expected == f"the-{name_h}" or expected == name_h:
                return f"{num}_{expected}"
        except (ValueError, IndexError):
            pass

    m = re.match(r"^(\w+)_(\w+)$", stem)
    if m:
        suit, rank_raw = m.group(1), m.group(2)
        if suit in SUITS:
            rank = WORD_TO_RANK.get(rank_raw)
            if rank:
                return f"{suit}_{rank}"

    return None


def parse_pink(filename: str):
    stem = Path(filename).stem.lower()
    stem = stem.replace(" ", "-")

    for i, slug in enumerate(MAJOR_ORDER):
        if stem == slug:
            return f"{i:02d}_{slug}"
        if stem == f"the-{slug}" and not slug.startswith("the-"):
            return f"{i:02d}_{slug}"
        if slug.startswith("the-") and stem == slug[4:]:
            pass

    m = re.match(r"^([\w-]+)-of-(\w+)$", stem)
    if m:
        rank_raw, suit = m.group(1), m.group(2)
        if suit in SUITS:
            rank = WORD_TO_RANK.get(rank_raw)
            if rank:
                return f"{suit}_{rank}"

    return None


def normalize_folder(folder: Path, parser_fn, to_webp: bool = False,
                     webp_quality: int = 85, dest: Path = None):
    if not folder.exists():
        print(f"  [SKIP] Папка не существует: {folder}")
        return 0, 0

    if dest is not None:
        dest.mkdir(parents=True, exist_ok=True)

    out_dir = dest if dest else folder

    images = sorted([f for f in folder.iterdir()
                     if f.is_file() and f.suffix.lower()
                     in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}])
    print(f"  Найдено файлов: {len(images)}")

    ok = 0
    fail = 0
    for img_path in images:
        canonical = parser_fn(img_path.name)

        if canonical is None:
            print(f"  [WARN] Не удалось разобрать: {img_path.name}")
            fail += 1
            continue

        target_name = f"{canonical}.webp"
        target_path = out_dir / target_name

        if dest is None and img_path.name == target_name:
            print(f"  [OK]   {img_path.name}")
            ok += 1
            continue

        if dest is not None and target_path.exists():
            print(f"  [OK]   {img_path.name} → {target_name}  (уже есть)")
            ok += 1
            continue

        need_convert = to_webp or img_path.suffix.lower() != ".webp"

        try:
            if need_convert:
                im = Image.open(img_path).convert("RGBA")
                im.save(target_path, "WEBP", quality=webp_quality)
                size_kb = target_path.stat().st_size / 1024
                label = "→" if dest else "→"
                print(f"  [OK]   {img_path.name} {label} {target_name}  ({size_kb:.0f} KB)")
            else:
                if target_path.exists():
                    target_path.unlink()
                shutil.move(str(img_path), str(target_path))
                print(f"  [OK]   {img_path.name} → {target_name}")
            ok += 1
        except Exception as e:
            print(f"  [ERR]  {img_path.name}: {e}")
            fail += 1

    return ok, fail


def main():
    expected = build_canonical_map()
    print(f"Ожидается {len(expected)} канонических имён (22 major + 56 minor)\n")

    old_cards = DATA_DIR / "cards"
    gold_cards = DATA_DIR / "gold_cards"

    if old_cards.exists() and not gold_cards.exists():
        old_cards.rename(gold_cards)
        print(f"[MOVE] {old_cards} → {gold_cards}")
    elif gold_cards.exists():
        print(f"[OK]   {gold_cards} уже существует")
    else:
        print(f"[WARN] Ни {old_cards}, ни {gold_cards} не найдены")

    print("\n── Нормализация gold_cards (rename only) ──")
    ok_g, fail_g = normalize_folder(gold_cards, parse_gold, to_webp=False)

    images_src = DATA_DIR / "images"
    pink_cards = DATA_DIR / "pink_cards"
    print("\n── Конвертация images → pink_cards (png → webp + rename) ──")
    ok_p, fail_p = normalize_folder(images_src, parse_pink, to_webp=True, dest=pink_cards)

    total_ok = ok_g + ok_p
    total_fail = fail_g + fail_p
    print(f"\n{'='*50}")
    print(f"gold_cards: {ok_g} ok, {fail_g} failed")
    print(f"pink_cards: {ok_p} ok, {fail_p} failed")
    print(f"Итого:       {total_ok} ok, {total_fail} failed")
    if total_fail:
        print("\n[!] Проверьте файлы с [WARN]")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
