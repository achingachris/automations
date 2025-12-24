import feedparser
from datetime import datetime, timezone
import os
import re
from pathlib import Path
from html import unescape

BASE_DIR = Path(__file__).resolve().parent.parent / "daily-articles"

FEEDS = [
    "https://medium.com/feed/tag/python",
    "https://medium.com/feed/tag/artificial-intelligence",
    "https://medium.com/feed/tag/django",
    "https://dev.to/feed/tag/python",
    "https://dev.to/feed/tag/ai",
    "https://hnrss.org/frontpage",
    "https://hnrss.org/newest?q=ai",
    "https://techcrunch.com/feed/"
]

TOPICS = [
    "python",
    "ai",
    "artificial intelligence",
    "bots",
    "automation",
    "django",
    "chatgpt",
    "openai",
    "llm",
    "llms",
    "data",
    "data science",
    "data analysis",
    "open source",
    "open-source",
    "claude",
    "gemini",
    "codex",
    "grok",
    "javascript",
    "rust",
    "go"
]

URL_PATTERN = re.compile(r"https?://[^\s|)]+")

today = datetime.now(timezone.utc).date()
date_str = today.strftime("%d-%m-%Y")
filename = f"{date_str}.md"
filepath = BASE_DIR / filename

def is_today(entry):
    if entry.get("published_parsed"):
        d = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).date()
        return d == today
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
    plain = re.sub(r"<[^>]+>", "", unescape(raw_summary))
    plain = plain.replace("Continue reading on Medium »", "")
    plain = plain.replace("Continue reading on", "")
    plain = " ".join(plain.split())
    return (plain[: limit - 1] + "…") if len(plain) > limit else plain

def escape_pipes(text):
    return text.replace("|", "\\|")

os.makedirs(BASE_DIR, exist_ok=True)

existing_urls = set()

if filepath.exists():
    with open(filepath, "r", encoding="utf-8") as f:
        existing_urls.update(URL_PATTERN.findall(f.read()))

new_rows = []

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

        new_rows.append(
            f"| {date_str} | {title_text} | {url} | {tag} | {summary_text} |"
        )

        existing_urls.add(url)

if not new_rows:
    raise SystemExit(0)

file_exists = filepath.exists()

with open(filepath, "a", encoding="utf-8") as f:
    if not file_exists:
        f.write(f"# Daily Tech Articles ({date_str})\n\n")
        f.write("| date | title | url | tag | summary |\n")
        f.write("| --- | --- | --- | --- | --- |\n")

    f.write("\n".join(new_rows))
    f.write("\n")
