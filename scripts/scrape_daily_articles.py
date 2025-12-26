import feedparser
from datetime import datetime, timezone
import re
from collections import Counter
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo
import os
import sys

ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = ROOT_DIR / "daily-articles"
CONTENT_DIR = ROOT_DIR / "content-source"
TOPICS_FILE = CONTENT_DIR / "topics.txt"
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
            "| # | date | title/topic | url | tag | summary |",
            "| --- | --- | --- | --- | --- | --- |",
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
        line.strip().lower()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

topics = load_list(TOPICS_FILE)
feeds = load_list(FEEDS_FILE)

# ---- Soft exit (DO NOT CRASH CI) ----
if not topics or not feeds:
    print("Topics or feeds missing — placeholder retained, skipping scrape.")
    sys.exit(0)

def is_today(entry):
    if entry.get("published_parsed"):
        d = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(LOCAL_TZ)
        return d.date() == today
    return False

def matches_topics(text):
    text = text.lower()
    return any(t in text for t in topics)

def first_topic(text):
    text = text.lower()
    for t in topics:
        if t in text:
            return t
    return "n/a"

def clean_summary(raw, limit=220):
    plain = re.sub(r"<[^>]+>", "", unescape(raw))
    plain = plain.replace("Continue reading on Medium »", "")
    plain = " ".join(plain.split())
    return (plain[: limit - 1] + "…") if len(plain) > limit else plain

def escape_pipes(text):
    return text.replace("|", "\\|")

# ---- Read existing content ----
existing_content = filepath.read_text(encoding="utf-8")
existing_urls = set(URL_PATTERN.findall(existing_content))

existing_rows = [
    line for line in existing_content.splitlines()
    if line.startswith("|") and "http" in line
]

new_entries = []

for feed_url in feeds:
    feed = feedparser.parse(feed_url)
    for e in feed.entries:
        url = e.get("link", "").strip()
        title = e.get("title", "").strip()
        summary = e.get("summary", "").strip()

        if not url or url in existing_urls:
            continue
        if not is_today(e):
            continue

        blob = f"{title} {summary} {url}"
        if not matches_topics(blob):
            continue

        new_entries.append({
            "date": date_str,
            "title": escape_pipes(title),
            "url": url,
            "tag": first_topic(blob),
            "summary": escape_pipes(clean_summary(summary)),
        })

        existing_urls.add(url)

# ---- Nothing new: stop safely ----
if not new_entries:
    print("No new articles found today.")
    sys.exit(0)

# ---- Append entries ----
offset = len(existing_rows)
tag_counts = Counter(r["tag"] for r in new_entries)

summary = f"Summary: {len(new_entries)} new articles"
if tag_counts:
    top_tag, count = tag_counts.most_common(1)[0]
    summary += f"; top tag {top_tag}: {count}"

lines = [
    "",
    f"## Additional articles ({datetime.now(LOCAL_TZ).strftime('%H:%M %Z')})",
    "",
    summary,
    "",
    "| # | date | title/topic | url | tag | summary |",
    "| --- | --- | --- | --- | --- | --- |",
]

for idx, row in enumerate(new_entries, start=offset + 1):
    lines.append(
        f"| {idx} | {row['date']} | {row['title']} | {row['url']} | {row['tag']} | {row['summary']} |"
    )

with open(filepath, "a", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Added {len(new_entries)} articles to {filepath.name}")
