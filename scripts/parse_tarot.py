import json
import re
import os
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_DIR = DATA_DIR / ".cache"
CARDS_FILE = DATA_DIR / "tarot_card_list.json"
OUTPUT_FILE = DATA_DIR / "tarot_cards.json"
COMBOS_OUTPUT_FILE = DATA_DIR / "tarot_combinations.json"

BASE_URL = "https://uznayvse.ru"
CARDS_INDEX_URL = BASE_URL + "/tarot-cards/meaning/"

JSON_KWARGS = dict(ensure_ascii=False, indent=2)


def _http_get(url: str, retries: int = 3) -> str:
    """Download page HTML. Uses requests if available, else urllib."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    }
    for attempt in range(1, retries + 1):
        try:
            if HAS_REQUESTS:
                resp = requests.get(url, headers=headers, timeout=30)
                resp.raise_for_status()
                return resp.text
            else:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            if attempt < retries:
                wait = 2 ** attempt
                print(f"  [RETRY {attempt}/{retries}] {url} — {e}, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  [WARN] Failed to fetch {url}: {e}")
                return ""


def fetch_page(url: str, cache_key: str) -> dict:
    """Fetch page HTML with filesystem caching. Returns {"data": {"html": "..."}}."""
    cache_path = CACHE_DIR / f"{cache_key}.html"

    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            html = f.read()
        return {"data": {"html": html}}

    html = _http_get(url)
    if not html:
        return {}

    with open(cache_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return {"data": {"html": html}}


def strip_html(text: str) -> str:
    """Remove ALL HTML tags, entities, tabs, empty lines. Returns pure text."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)
    text = re.sub(r'&#\d+;', '', text)
    text = text.replace('\t', ' ')
    lines = []
    for line in text.split('\n'):
        stripped = line.strip()
        if stripped:
            lines.append(stripped)
    text = '\n\n'.join(lines)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def html_to_text(html: str) -> str:
    """Convert HTML to readable plain text, dropping all tags."""
    text = re.sub(r'<br\s*/?>', '\n', html, flags=re.IGNORECASE)
    text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</h[1-6]>', '\n\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</li>', '\n', text, flags=re.IGNORECASE)
    return strip_html(text)


def extract_article_body(html: str) -> str:
    """Extract the article body from page HTML."""
    match = re.search(
        r'itemprop="articleBody"[^>]*>([\s\S]*?)'
        r'(?=<div\s+class="[^"]*iku_adcontent|</article>|<footer)',
        html,
    )
    if match:
        return match.group(1)

    match = re.search(r'<article[^>]*>([\s\S]*?)</article>', html)
    if match:
        return match.group(1)

    return html


def build_card_list() -> list[dict]:
    """Скачивает страницу /tarot-cards/meaning/ и собирает 78 карт."""
    print(f"=== Building card list from {CARDS_INDEX_URL} ===")
    page = fetch_page(CARDS_INDEX_URL, "index")
    if not page:
        print("[ERROR] Could not fetch index page")
        sys.exit(1)

    html = page.get("data", page).get("html", "")
    if not html:
        print("[ERROR] Index page has no HTML")
        sys.exit(1)

    pattern = (
        r'href="/tarot-cards/meaning/([^".]+)\.html"'
        r'[^>]*title="Значение карты таро ([^"]+)"'
    )
    matches = re.findall(pattern, html)

    cards = []
    seen = set()
    for slug, name in matches:
        if slug in seen:
            continue
        seen.add(slug)
        cards.append({
            "name": name.strip(),
            "slug": slug,
            "url": f"{BASE_URL}/tarot-cards/meaning/{slug}.html",
        })

    cards.sort(key=lambda c: c["slug"])
    print(f"  Found {len(cards)} cards")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(CARDS_FILE, 'w', encoding='utf-8') as f:
        json.dump({"cards": cards}, f, **JSON_KWARGS)
    print(f"  Saved to {CARDS_FILE}")

    return cards


# ═══════════════════════════════════════════════════════════════════════
#  Шаг 1: Парсинг описаний карт
# ═══════════════════════════════════════════════════════════════════════

def split_meaning_sections(text: str) -> dict:
    """Split card description into sections: upright, reversed, love, etc."""
    sections = {}

    patterns = [
        ("archetype",       r"Архетип\s+(?:карты\s+)?(.+?)(?=\n)",            r"(?=\n(?:Ключевое|Символика|Общее|Значение|Карта\s+|О\s+чём|Сочетания))"),
        ("key_meaning",     r"Ключевое\s+значение\s+(?:карты\s+)?(.+?)(?=\n)",  r"(?=\n(?:Символика|Общее|Значение|Карта\s+|О\s+чём|Сочетания))"),
        ("symbolism",       r"Символика\s+карты\s+(.+?)(?=\n)",                r"(?=\n(?:Общее|Значение|Карта\s+|О\s+чём|Сочетания))"),
        ("general_upright", r"Общее\s+значение\s+карты\s+.+?\s+в\s+прям[оы]м\s+положени[ия]",       r"(?=\n(?:Общее\s+значение\s+карты\s+.+?\s+в\s+перев|Значение\s+карты\s+.+?\s+в\s+люб|Карта\s+.+?\s+как\s+карта|О\s+чём\s+предупреждает|Сочетания))"),
        ("general_reversed",r"Общее\s+значение\s+карты\s+.+?\s+в\s+перевёрнут[оы]м\s+положени[ия]", r"(?=\n(?:Значение\s+карты\s+.+?\s+в\s+люб|Карта\s+.+?\s+как\s+карта|О\s+чём\s+предупреждает|Сочетания))"),
        ("love_upright",    r"Значение\s+карты\s+.+?\s+в\s+любви\s+в\s+прям[оы]м\s+положени[ия]",   r"(?=\n(?:Значение\s+карты\s+.+?\s+в\s+любви\s+в\s+перев|Карта\s+.+?\s+как\s+карта|О\s+чём\s+предупреждает|Сочетания))"),
        ("love_reversed",   r"Значение\s+карты\s+.+?\s+в\s+любви\s+в\s+перевёрнут[оы]м\s+положени[ия]", r"(?=\n(?:Карта\s+.+?\s+как\s+карта|О\s+чём\s+предупреждает|Сочетания))"),
        ("card_of_day",     r"Карта\s+.+?\s+как\s+карта\s+дня",              r"(?=\n(?:О\s+чём\s+предупреждает|Сочетания))"),
        ("warning",         r"О\s+чём\s+предупреждает\s+карта\s+(.+?)(?=\n)", r"(?=\nСочетания)"),
    ]

    for key, start_pat, end_pat in patterns:
        start_match = re.search(start_pat, text)
        if start_match:
            remaining = text[start_match.end():]
            end_match = re.search(end_pat, remaining)
            section_text = remaining[:end_match.start()].strip() if end_match else remaining.strip()
            if section_text:
                sections[key] = section_text

    intro_match = re.match(r"(.+?)(?=\nАрхетип|\nКлючевое|\nСимволика|\nОбщее|\nЗначение)", text, re.DOTALL)
    if intro_match:
        intro = intro_match.group(1).strip()
        if len(intro) > 20:
            sections["intro"] = intro

    return sections


def extract_combinations_table(html_article: str) -> list:
    """Extract combination table from card page."""
    combos = []
    pattern = (
        r'<tr[^>]*data-spoiler_needle="combinations_table"[^>]*>'
        r'.*?<a\s+href="(/tarot-cards/combination/([^"]+))"[^>]*>'
        r'.*?<span[^>]*>([^<]+)</span>.*?</a>'
        r'.*?<td[^>]*itemprop="description"[^>]*>\s*(.*?)\s*</td>'
        r'.*?</tr>'
    )
    matches = re.findall(pattern, html_article, re.DOTALL)

    for full_url, combo_slug, card_name, value in matches:
        combos.append({
            "combination_url": BASE_URL + full_url,
            "combination_slug": combo_slug.replace('.html', ''),
            "card_name": card_name.strip(),
            "short_meaning": strip_html(value),
        })

    return combos


MAJOR_ARCANA_SLUGS = {
    "the-fool", "the-magician", "the-high-priestess", "the-empress",
    "the-emperor", "the-hierophant", "the-lovers", "the-chariot",
    "the-strength", "the-hermit", "wheel-of-fortune", "the-justice",
    "the-hanged-man", "death", "temperance", "the-devil", "the-tower",
    "the-star", "the-moon", "the-sun", "judgement", "the-world",
}


def parse_card_page(card: dict) -> dict | None:
    """Parse a single card page and return structured data."""
    slug = card["slug"]
    url = card["url"]

    print(f"  Parsing card: {card['name']} ({slug})")

    page_data = fetch_page(url, f"card_{slug}")
    if not page_data:
        return None

    html = page_data.get("data", page_data).get("html", "")
    if not html:
        return None

    article = extract_article_body(html)
    text = html_to_text(article)
    sections = split_meaning_sections(text)

    img_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
    image_url = img_match.group(1) if img_match else None

    combos_table = extract_combinations_table(article)

    return {
        "id": slug,
        "name": card["name"],
        "name_ru": (
            sections.get("intro", "").split("–")[0].split(" —")[0].split("(")[0].strip()
            if sections.get("intro") else card["name"]
        ),
        "slug": slug,
        "arcana": "major" if slug in MAJOR_ARCANA_SLUGS else "minor",
        "url": url,
        "image_url": image_url,
        "description": {
            "intro": sections.get("intro", ""),
            "general_upright": sections.get("general_upright", ""),
            "general_reversed": sections.get("general_reversed", ""),
            "love_upright": sections.get("love_upright", ""),
            "love_reversed": sections.get("love_reversed", ""),
            "archetype": sections.get("archetype", ""),
            "key_meaning": sections.get("key_meaning", ""),
            "symbolism": sections.get("symbolism", ""),
            "card_of_day": sections.get("card_of_day", ""),
            "warning": sections.get("warning", ""),
        },
        "combinations": combos_table,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Шаг 2: Парсинг комбинаций
# ═══════════════════════════════════════════════════════════════════════

def parse_combination_page(combo: dict, card_data_map: dict) -> dict | None:
    """Parse a combination detail page with 4 position variants."""
    slug = combo["combination_slug"]
    url = combo["combination_url"]

    page_data = fetch_page(url, f"combo_{slug}")
    if not page_data:
        return None

    html = page_data.get("data", page_data).get("html", "")
    if not html:
        return None

    article = extract_article_body(html)
    text = html_to_text(article)

    variants = {}
    h2_pattern = r'(Сочетание\s+(?:перевернутой\s+)?карты\s+.+?)(?=\n\n)'
    h2_matches = list(re.finditer(h2_pattern, text))

    for i, match in enumerate(h2_matches):
        heading = match.group(1).strip()
        start = match.end()
        end = h2_matches[i + 1].start() if i + 1 < len(h2_matches) else len(text)
        body = text[start:end].strip()

        # Cut footer / ads
        for marker in ["знака зодиака", "Данная информация освещает"]:
            idx = body.find(marker)
            if idx > 0:
                body = body[:idx].strip()

        if "перевернутой" not in heading:
            position = "both_upright"
        elif heading.count("перевернутой") == 2:
            position = "both_reversed"
        elif heading.startswith("Сочетание перевернутой"):
            position = "first_reversed_second_upright"
        else:
            position = "first_upright_second_reversed"

        variants[position] = {
            "heading": heading,
            "interpretation": body,
        }

    parts = slug.split("-and-")
    return {
        "slug": slug,
        "card1_slug": parts[0],
        "card2_slug": "-and-".join(parts[1:]) if len(parts) > 1 else "",
        "url": url,
        "variants": variants,
    }


# ═══════════════════════════════════════════════════════════════════════
#  Main
# ═══════════════════════════════════════════════════════════════════════

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Шаг 0: Список карт ────────────────────────────────────────────
    need_build = False
    if not CARDS_FILE.exists():
        need_build = True
    elif CARDS_FILE.stat().st_size == 0:
        need_build = True
    else:
        try:
            with open(CARDS_FILE, 'r', encoding='utf-8') as f:
                cards = json.load(f)["cards"]
        except (json.JSONDecodeError, KeyError):
            need_build = True

    if need_build:
        CARDS_FILE.unlink(missing_ok=True)
        cards = build_card_list()
    else:
        print(f"[INFO] Loaded {len(cards)} cards from {CARDS_FILE}")

    print(f"\n=== Parsing {len(cards)} tarot cards ===\n")

    # ── Шаг 1: Описания карт ──────────────────────────────────────────
    card_results = []
    failed_cards = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_card = {executor.submit(parse_card_page, card): card for card in cards}
        for future in as_completed(future_to_card):
            card = future_to_card[future]
            try:
                result = future.result()
                if result:
                    card_results.append(result)
                else:
                    failed_cards.append(card["name"])
            except Exception as e:
                print(f"  [ERROR] {card['name']}: {e}")
                failed_cards.append(card["name"])

    card_results.sort(key=lambda x: x["slug"])
    print(f"\n=== Cards: {len(card_results)} ok, {len(failed_cards)} failed ===")

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(card_results, f, **JSON_KWARGS)
    print(f"Saved -> {OUTPUT_FILE}")

    # ── Шаг 2: Комбинации ────────────────────────────────────────────
    all_combos = []
    seen = set()
    for card in card_results:
        for combo in card.get("combinations", []):
            s = combo["combination_slug"]
            if s not in seen:
                seen.add(s)
                all_combos.append(combo)

    print(f"\n=== Parsing {len(all_combos)} combination pages ===\n")

    combo_results = []
    failed_combos = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_to_combo = {
            executor.submit(parse_combination_page, combo, {c["slug"]: c for c in card_results}): combo
            for combo in all_combos
        }
        for future in as_completed(future_to_combo):
            combo = future_to_combo[future]
            try:
                result = future.result()
                if result:
                    combo_results.append(result)
                else:
                    failed_combos.append(combo["combination_slug"])
            except Exception as e:
                print(f"  [ERROR] {combo['combination_slug']}: {e}")
                failed_combos.append(combo["combination_slug"])

    combo_results.sort(key=lambda x: x["slug"])
    print(f"\n=== Combos: {len(combo_results)} ok, {len(failed_combos)} failed ===")

    with open(COMBOS_OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(combo_results, f, **JSON_KWARGS)
    print(f"Saved -> {COMBOS_OUTPUT_FILE}")

    total = sum(len(c.get("combinations", [])) for c in card_results)
    print(f"\n{'='*50}")
    print(f"Cards: {len(card_results)}/78")
    print(f"Combos: {total} links, {len(combo_results)} detail pages")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()