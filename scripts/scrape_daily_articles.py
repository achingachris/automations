import feedparser
import os
from datetime import datetime, timezone
import re
from collections import Counter
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = ROOT_DIR / "daily-articles"
CONTENT_DIR = ROOT_DIR / "content-source"
TOPICS_FILE = CONTENT_DIR / "topics.txt"
FEEDS_FILE = CONTENT_DIR / "feeds.txt"
LOCAL_TZ = ZoneInfo("Africa/Nairobi")  # UTC+3

URL_PATTERN = re.compile(r"https?://[^\s|)]+")

def load_list(path: Path, fallback: list[str]) -> list[str]:
    if not path.exists():
        return fallback
    items = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return items or fallback

def dedupe_keep_order(items):
    seen = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        yield item

CONTENT_DIR.mkdir(parents=True, exist_ok=True)
topics = list(dedupe_keep_order(load_list(TOPICS_FILE, [])))
feeds = list(dedupe_keep_order(load_list(FEEDS_FILE, [])))

if not topics or not feeds:
    raise SystemExit("Topics and feeds files must be present and non-empty.")

TOPICS = topics
FEEDS = feeds

today = datetime.now(LOCAL_TZ).date()
date_str = today.strftime("%d-%m-%Y")
filename = f"{date_str}.md"
filepath = BASE_DIR / filename


def is_today(entry):
    if entry.get("published_parsed"):
        d = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(
            LOCAL_TZ
        )
        return d.date() == today
    return False


def matches_topics(text):
    text = text.lower()
    return any(t in text for t in TOPICS)


def first_topic(text):
    text = text.lower()
    for t in TOPICS:
        if t in text:
            return t
    return "n/a"


def clean_summary(raw_summary, limit=220):
    # Strip simple HTML tags and collapse whitespace; trim long summaries for readability.
    plain = re.sub(r"<[^>]+>", "", unescape(raw_summary))
    plain = plain.replace("Continue reading on Medium »", "")
    plain = plain.replace("Continue reading on", "")
    plain = " ".join(plain.split())
    return (plain[: limit - 1] + "…") if len(plain) > limit else plain


def escape_pipes(text):
    return text.replace("|", "\\|")


def parse_existing_rows(text):
    rows = []
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) < 5:
            continue
        if parts[0].isdigit() and len(parts) >= 6:
            date, title, url, tag, summary = parts[1:6]
        else:
            date, title, url, tag, summary = parts[:5]
        if not url.startswith("http"):
            continue
        rows.append(
            {
                "date": date,
                "title": title,
                "url": url,
                "tag": tag,
                "summary": summary,
            }
        )
    return rows


os.makedirs(BASE_DIR, exist_ok=True)

existing_urls = set()
existing_rows = []
existing_content = ""

if filepath.exists():
    existing_content = filepath.read_text(encoding="utf-8")
    existing_urls.update(URL_PATTERN.findall(existing_content))
    existing_rows = parse_existing_rows(existing_content)

new_entries = []

for feed_url in FEEDS:
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

        tag = first_topic(blob)
        title_text = escape_pipes(title)
        summary_text = escape_pipes(clean_summary(summary))

        new_entries.append(
            {
                "date": date_str,
                "title": title_text,
                "url": url,
                "tag": tag,
                "summary": summary_text,
            }
        )

        existing_urls.add(url)

if not existing_rows and not new_entries:
    raise SystemExit(0)

# First run of the day: create the file with the initial table.
if not existing_rows and new_entries:
    tag_counts = Counter(r["tag"] for r in new_entries)
    summary_line = f"Summary: {len(new_entries)} new articles today"
    if tag_counts:
        top_tag, top_tag_count = tag_counts.most_common(1)[0]
        summary_line += f"; top tag {top_tag}: {top_tag_count}"

    lines = [
        f"# Daily Tech Articles ({date_str})",
        "",
        summary_line,
        "",
        "| # | date | title/topic | url | tag | summary |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for idx, row in enumerate(new_entries, start=1):
        lines.append(
            f"| {idx} | {row['date']} | {row['title']} | {row['url']} | {row['tag']} | {row['summary']} |"
        )

    filepath.write_text("\n".join(lines) + "\n", encoding="utf-8")
    raise SystemExit(0)

# Nothing new to add.
if not new_entries:
    raise SystemExit(0)

# Subsequent run: append a new section with only the newly found entries.
if new_entries:
    offset = len(existing_rows)
    tag_counts = Counter(r["tag"] for r in new_entries)
    total_after = offset + len(new_entries)
    run_summary = f"Summary: {len(new_entries)} new articles this run; {total_after} total in file"
    if tag_counts:
        top_tag, top_tag_count = tag_counts.most_common(1)[0]
        run_summary += f"; top tag {top_tag}: {top_tag_count}"

    now_str = datetime.now(LOCAL_TZ).strftime("%H:%M %Z")
    section_lines = [
        "",
        f"## Additional articles ({now_str})",
        "",
        run_summary,
        "",
        "| # | date | title/topic | url | tag | summary |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for idx, row in enumerate(new_entries, start=offset + 1):
        section_lines.append(
            f"| {idx} | {row['date']} | {row['title']} | {row['url']} | {row['tag']} | {row['summary']} |"
        )

    with open(filepath, "a", encoding="utf-8") as f:
        if existing_content and not existing_content.endswith("\n"):
            f.write("\n")
        f.write("\n".join(section_lines) + "\n")
