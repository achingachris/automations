from __future__ import annotations

"""
Shared utilities for RSS feed scraping.

This module provides common functions used by both the article and newsletter scrapers,
including timezone handling, date parsing, feed fetching with retry logic, and text processing.
"""

import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, date
from html.parser import HTMLParser
from html import unescape
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import feedparser

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # type: ignore

# ---- Logging Setup ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---- Timezone Configuration ----
try:
    LOCAL_TZ = ZoneInfo("Africa/Nairobi")
except Exception:
    logger.warning("Could not load Africa/Nairobi timezone, falling back to UTC")
    LOCAL_TZ = timezone.utc

# ---- Constants ----
DEFAULT_MAX_WORKERS = 10
DEFAULT_FEED_TIMEOUT = 30
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_BACKOFF = 2
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; FeedScraper/1.0)"

# More robust URL pattern that avoids trailing punctuation
URL_PATTERN = re.compile(r"https?://[^\s|)>\]\"']+(?<![.,;:!?])")


class FeedLinkParser(HTMLParser):
    """Extract RSS/Atom alternate links from an HTML document."""

    def __init__(self) -> None:
        super().__init__()
        self.feed_urls: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return

        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        rel = attrs_dict.get("rel", "").lower()
        type_attr = attrs_dict.get("type", "").lower()
        href = attrs_dict.get("href", "").strip()

        if not href:
            return

        # Most sites expose feeds as <link rel="alternate" type="application/rss+xml" ...>
        is_alternate = "alternate" in rel
        looks_like_feed = any(token in type_attr for token in ("rss", "atom", "xml"))
        if is_alternate and looks_like_feed:
            self.feed_urls.append(href)


def get_today() -> date:
    """Get today's date in the local timezone."""
    return datetime.now(LOCAL_TZ).date()


def get_date_str(d: date | None = None) -> str:
    """Format a date as DD-MM-YYYY string."""
    if d is None:
        d = get_today()
    return d.strftime("%d-%m-%Y")


def get_content_filepath(base_dir: Path, content_type: str, d: date | None = None) -> Path:
    """
    Get the filepath for content using hierarchical structure.

    Structure: content/{content_type}/YYYY/MM/DD.md

    Args:
        base_dir: Root content directory (e.g., /path/to/content)
        content_type: Type of content (articles, newsletters, social)
        d: Date for the file (defaults to today)

    Returns:
        Path object for the content file
    """
    if d is None:
        d = get_today()

    return base_dir / content_type / str(d.year) / f"{d.month:02d}" / f"{d.day:02d}.md"


def get_day_str(d: date | None = None) -> str:
    """Format a date as DD string (day only)."""
    if d is None:
        d = get_today()
    return f"{d.day:02d}"


def load_list(path: Path) -> list[str]:
    """
    Load non-empty, non-comment lines from a text file.

    Args:
        path: Path to the text file

    Returns:
        List of stripped, non-empty lines that don't start with #
    """
    if not path.exists():
        logger.warning(f"File not found: {path}")
        return []
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]


def get_entry_date(entry: dict, local_tz=LOCAL_TZ) -> datetime | None:
    """
    Extract date from a feed entry, trying multiple fields.

    Args:
        entry: Feed entry dictionary
        local_tz: Timezone to convert to

    Returns:
        Datetime in local timezone, or None if no date found
    """
    for field in ["published_parsed", "updated_parsed"]:
        parsed = entry.get(field)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc).astimezone(local_tz)
            except (TypeError, ValueError) as e:
                logger.debug(f"Failed to parse date from {field}: {e}")
    return None


def is_today(entry: dict, today: date | None = None) -> bool:
    """Check if entry was published today."""
    if today is None:
        today = get_today()
    d = get_entry_date(entry)
    return d.date() == today if d else False


def is_this_month(entry: dict, today: date | None = None) -> bool:
    """Check if entry is from the current month."""
    if today is None:
        today = get_today()
    d = get_entry_date(entry)
    if not d:
        return False
    return d.year == today.year and d.month == today.month


def clean_summary(raw: str, limit: int = 220) -> str:
    """
    Clean HTML from summary and truncate to limit.

    Args:
        raw: Raw HTML/text summary
        limit: Maximum character length

    Returns:
        Cleaned plain text summary
    """
    # Strip HTML tags
    plain = re.sub(r"<[^>]+>", "", unescape(raw))
    # Remove common Medium suffix
    plain = plain.replace("Continue reading on Medium »", "")
    # Normalize whitespace (handles newlines, tabs, multiple spaces)
    plain = " ".join(plain.split())
    # Truncate with ellipsis if needed
    return (plain[: limit - 1] + "…") if len(plain) > limit else plain


def escape_pipes(text: str) -> str:
    """Escape pipe characters for Markdown tables."""
    return text.replace("|", "\\|")


def fetch_feed(
    source_url: str,
    max_retries: int = DEFAULT_MAX_RETRIES,
    backoff: int = DEFAULT_RETRY_BACKOFF,
) -> tuple[str, object | None, list]:
    """
    Fetch and parse a single feed with retry logic.

    Args:
        source_url: URL of a website/profile page or direct RSS/Atom feed
        max_retries: Maximum number of retry attempts
        backoff: Base backoff time in seconds (exponential)

    Returns:
        Tuple of (source_url, feed_object, entries_list)
    """
    def parse_feed(url: str) -> tuple[object | None, list]:
        feed = feedparser.parse(
            url,
            request_headers={"User-Agent": DEFAULT_USER_AGENT},
        )
        if feed.bozo and not feed.entries:
            return None, []
        return feed, feed.entries

    def discover_feed_urls(url: str) -> list[str]:
        try:
            req = Request(url, headers={"User-Agent": DEFAULT_USER_AGENT})
            with urlopen(req, timeout=DEFAULT_FEED_TIMEOUT) as response:
                html = response.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"Failed to fetch source page {url}: {e}")
            return []

        parser = FeedLinkParser()
        parser.feed(html)

        # Preserve order while deduplicating
        seen = set()
        discovered = []
        for href in parser.feed_urls:
            absolute_url = urljoin(url, href)
            if absolute_url not in seen:
                seen.add(absolute_url)
                discovered.append(absolute_url)
        return discovered

    for attempt in range(max_retries):
        try:
            feed, entries = parse_feed(source_url)
            if entries:
                return source_url, feed, entries

            # If direct parsing fails, treat source as a normal webpage and discover feed URLs.
            discovered_feed_urls = discover_feed_urls(source_url)
            for discovered_url in discovered_feed_urls:
                feed, entries = parse_feed(discovered_url)
                if entries:
                    logger.info(f"Discovered feed for {source_url}: {discovered_url}")
                    return source_url, feed, entries
                logger.debug(f"Discovered feed had no entries: {discovered_url}")

            logger.warning(f"No parseable feed entries found for source: {source_url}")
            return source_url, None, []

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = backoff ** attempt
                logger.debug(f"Retry {attempt + 1}/{max_retries} for {source_url} after {wait_time}s")
                time.sleep(wait_time)
                continue
            logger.error(f"Failed to fetch {source_url} after {max_retries} attempts: {e}")
            return source_url, None, []

    return source_url, None, []


def fetch_feeds_parallel(
    source_urls: list[str],
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> tuple[list[tuple[str, object | None, list]], int, int]:
    """
    Fetch multiple feeds in parallel.

    Args:
        source_urls: List of source URLs to fetch
        max_workers: Maximum number of parallel workers

    Returns:
        Tuple of (results_list, success_count, failure_count)
    """
    results = []
    feeds_ok = 0
    feeds_failed = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_feed, url): url for url in source_urls}

        for future in as_completed(futures):
            result = future.result()
            feed_url, feed, entries = result

            if not entries:
                feeds_failed += 1
            else:
                feeds_ok += 1

            results.append(result)

    logger.info(f"Fetched {feeds_ok}/{len(source_urls)} sources successfully ({feeds_failed} failed)")
    return results, feeds_ok, feeds_failed


def get_existing_urls(filepath: Path) -> set[str]:
    """Extract all URLs from an existing file."""
    if not filepath.exists():
        return set()
    content = filepath.read_text(encoding="utf-8")
    return set(URL_PATTERN.findall(content))


def get_all_existing_urls(content_dir: Path) -> set[str]:
    """Extract all URLs from all .md files in a content directory (recursive)."""
    all_urls = set()
    if not content_dir.exists():
        return all_urls
    for md_file in content_dir.rglob("*.md"):
        content = md_file.read_text(encoding="utf-8")
        all_urls.update(URL_PATTERN.findall(content))
    return all_urls


def count_existing_rows(filepath: Path) -> int:
    """Count existing data rows in a Markdown table file."""
    if not filepath.exists():
        return 0
    content = filepath.read_text(encoding="utf-8")
    return len([
        line for line in content.splitlines()
        if line.startswith("|") and "http" in line
    ])


def create_placeholder_file(
    filepath: Path,
    title: str,
    date_str: str,
    columns: list[str],
    content_type: str = "items",
) -> None:
    """
    Create a placeholder Markdown file with table header.

    Args:
        filepath: Path to create the file
        title: Title for the document
        date_str: Date string for the title
        columns: List of column names for the table
        content_type: Type of content (e.g., "articles", "newsletters")
    """
    header_row = "| " + " | ".join(columns) + " |"
    separator_row = "| " + " | ".join(["---"] * len(columns)) + " |"

    content = "\n".join([
        f"# {title} ({date_str})",
        "",
        f"Summary: 0 {content_type} yet (placeholder created by scraper)",
        "",
        header_row,
        separator_row,
        "",
    ])

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    logger.info(f"Created placeholder file: {filepath}")


def append_entries_to_file(
    filepath: Path,
    entries: list[dict],
    columns: list[str],
    section_title: str,
) -> None:
    """
    Append new entries to an existing Markdown file.

    Args:
        filepath: Path to the Markdown file
        entries: List of entry dictionaries
        columns: Column names (keys in entry dicts)
        section_title: Title for the new section
    """
    offset = count_existing_rows(filepath)

    header_row = "| " + " | ".join(["#"] + columns) + " |"
    separator_row = "| " + " | ".join(["---"] * (len(columns) + 1)) + " |"

    lines = [
        "",
        f"## {section_title} ({datetime.now(LOCAL_TZ).strftime('%H:%M %Z')})",
        "",
        f"Summary: {len(entries)} new items",
        "",
        header_row,
        separator_row,
    ]

    for idx, row in enumerate(entries, start=offset + 1):
        values = [str(idx)] + [str(row.get(col, "")) for col in columns]
        lines.append("| " + " | ".join(values) + " |")

    with open(filepath, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    logger.info(f"Added {len(entries)} entries to {filepath.name}")
