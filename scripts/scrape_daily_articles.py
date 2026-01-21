import feedparser
from datetime import datetime, timezone
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo
import sys

# ---- Configuration ----
MAX_WORKERS = 10  # parallel feed fetches
FEED_TIMEOUT = 30  # seconds

ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = ROOT_DIR / "daily-articles"
CONTENT_DIR = ROOT_DIR / "content-source"
FEEDS_FILE = CONTENT_DIR / "feeds.txt"

# ---- Timezone (CI-safe) ----
try:
    LOCAL_TZ = ZoneInfo("Africa/Nairobi")
except Exception:
    LOCAL_TZ = timezone.utc

today = datetime.now(LOCAL_TZ).date()
date_str = today.strftime("%d-%m-%Y")
filename = f"{date_str}.md"
filepath = BASE_DIR / filename

BASE_DIR.mkdir(parents=True, exist_ok=True)

# ---- Always ensure placeholder exists ----
if not filepath.exists():
    filepath.write_text(
        "\n".join([
            f"# Daily Tech Articles ({date_str})",
            "",
            "Summary: 0 articles yet (placeholder created by scraper)",
            "",
            "| # | date | title | url | summary |",
            "| --- | --- | --- | --- | --- |",
            ""
        ]),
        encoding="utf-8"
    )

# ---- Helpers ----
URL_PATTERN = re.compile(r"https?://[^\s|)]+")

def load_list(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

feeds = load_list(FEEDS_FILE)

# ---- Soft exit (DO NOT CRASH CI) ----
if not feeds:
    print("Feeds missing — placeholder retained, skipping scrape.")
    sys.exit(0)

def get_entry_date(entry):
    """Extract date from entry, trying multiple fields."""
    for field in ["published_parsed", "updated_parsed"]:
        parsed = entry.get(field)
        if parsed:
            return datetime(*parsed[:6], tzinfo=timezone.utc).astimezone(LOCAL_TZ)
    return None

def is_today(entry):
    d = get_entry_date(entry)
    return d.date() == today if d else False

def is_this_month(entry):
    """Check if entry is from the current month."""
    d = get_entry_date(entry)
    if not d:
        return False
    return d.year == today.year and d.month == today.month

def clean_summary(raw, limit=220):
    plain = re.sub(r"<[^>]+>", "", unescape(raw))
    plain = plain.replace("Continue reading on Medium »", "")
    plain = " ".join(plain.split())
    return (plain[: limit - 1] + "…") if len(plain) > limit else plain

def escape_pipes(text):
    return text.replace("|", "\\|")

def fetch_feed(feed_url):
    """Fetch and parse a single feed with error handling."""
    try:
        feed = feedparser.parse(feed_url, request_headers={'User-Agent': 'Mozilla/5.0'})
        if feed.bozo and not feed.entries:
            print(f"Warning: malformed feed {feed_url}: {feed.bozo_exception}")
            return feed_url, []
        return feed_url, feed.entries
    except Exception as e:
        print(f"Error fetching {feed_url}: {e}")
        return feed_url, []

# ---- Read existing content ----
existing_content = filepath.read_text(encoding="utf-8")
existing_urls = set(URL_PATTERN.findall(existing_content))

existing_rows = [
    line for line in existing_content.splitlines()
    if line.startswith("|") and "http" in line
]

# ---- Detect first run (no existing articles) ----
first_run = len(existing_rows) == 0
if first_run:
    print("First run detected — fetching articles from this month")

new_entries = []
feeds_ok = 0
feeds_failed = 0

# ---- Fetch feeds in parallel ----
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(fetch_feed, url): url for url in feeds}

    for future in as_completed(futures):
        feed_url, entries = future.result()

        if not entries:
            feeds_failed += 1
            continue

        feeds_ok += 1
        for e in entries:
            url = e.get("link", "").strip()
            title = e.get("title", "").strip()
            summary = e.get("summary", "").strip()

            if not url or url in existing_urls:
                continue

            # First run: get this month's entries; otherwise: today only
            if first_run:
                if not is_this_month(e):
                    continue
            else:
                if not is_today(e):
                    continue

            entry_date = get_entry_date(e)
            entry_date_str = entry_date.strftime("%d-%m-%Y") if entry_date else date_str

            new_entries.append({
                "date": entry_date_str,
                "title": escape_pipes(title),
                "url": url,
                "summary": escape_pipes(clean_summary(summary)),
            })

            existing_urls.add(url)

print(f"Fetched {feeds_ok}/{len(feeds)} feeds successfully ({feeds_failed} failed)")

# ---- Nothing new: stop safely ----
if not new_entries:
    print("No new articles found this month." if first_run else "No new articles found today.")
    sys.exit(0)

# ---- Append entries ----
offset = len(existing_rows)

lines = [
    "",
    f"## Additional articles ({datetime.now(LOCAL_TZ).strftime('%H:%M %Z')})",
    "",
    f"Summary: {len(new_entries)} new articles",
    "",
    "| # | date | title | url | summary |",
    "| --- | --- | --- | --- | --- |",
]

for idx, row in enumerate(new_entries, start=offset + 1):
    lines.append(
        f"| {idx} | {row['date']} | {row['title']} | {row['url']} | {row['summary']} |"
    )

with open(filepath, "a", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Added {len(new_entries)} articles to {filepath.name}")
