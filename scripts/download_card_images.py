import re
import time
from pathlib import Path

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    HAS_REQUESTS = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CARDS_DIR = PROJECT_ROOT / "data" / "gold_cards"
BASE_URL = "https://deploytarot.com"
CARDS_PAGE = f"{BASE_URL}/cards"


def download_file(url: str, dest: Path) -> bool:
    try:
        if HAS_REQUESTS:
            resp = requests.get(url, timeout=30, stream=True)
            resp.raise_for_status()
            with open(dest, 'wb') as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
        else:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as resp:
                with open(dest, 'wb') as f:
                    while True:
                        chunk = resp.read(8192)
                        if not chunk:
                            break
                        f.write(chunk)
        return True
    except Exception as e:
        print(f"  [ERROR] {url}: {e}")
        return False


def main():
    CARDS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {CARDS_PAGE}...")
    if HAS_REQUESTS:
        resp = requests.get(CARDS_PAGE, timeout=30)
        html = resp.text
    else:
        req = urllib.request.Request(CARDS_PAGE)
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")

    # Pattern: url('/static/cards/NN_name.webp')
    pattern = r"url\('(/static/cards/[^']+)'\)"
    matches = re.findall(pattern, html)
    matches = sorted(set(matches))

    print(f"Found {len(matches)} card images")

    if len(matches) != 78:
        print(f"  [WARN] Expected 78, got {len(matches)}!")

    # Download each image
    ok = 0
    fail = 0
    for i, rel_path in enumerate(matches, 1):
        url = f"{BASE_URL}{rel_path}"
        filename = Path(rel_path).name
        dest = CARDS_DIR / filename

        if dest.exists():
            print(f"  [{i}/{len(matches)}] SKIP (exists): {filename}")
            ok += 1
            continue

        print(f"  [{i}/{len(matches)}] Downloading: {filename}...", end=" ")
        if download_file(url, dest):
            size_kb = dest.stat().st_size / 1024
            print(f"OK ({size_kb:.0f} KB)")
            ok += 1
        else:
            fail += 1

        # Small delay to be polite
        time.sleep(0.2)

    print(f"\n{'='*40}")
    print(f"Done: {ok} ok, {fail} failed")
    print(f"Saved to: {CARDS_DIR}")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
