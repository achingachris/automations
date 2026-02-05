#!/usr/bin/env python3
"""
Daily Social Media Scraper

Fetches social sources (profile URLs or direct feeds)
and compiles a daily Markdown digest of posts.
Uses Africa/Nairobi timezone for date filtering.

Output structure: content/social/YYYY/MM/DD.md
"""

import sys
from pathlib import Path

from shared import (
    logger,
    get_today,
    get_date_str,
    get_content_filepath,
    load_list,
    get_entry_date,
    is_today,
    clean_summary,
    escape_pipes,
    fetch_feeds_parallel,
    get_all_existing_urls,
    create_placeholder_file,
    append_entries_to_file,
)

# ---- Configuration ----
MAX_WORKERS = 5  # Fewer workers for social feeds

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT_DIR / "content"
FEEDS_DIR = ROOT_DIR / "content-source"
SOCIAL_SOURCES_FILE = FEEDS_DIR / "social.txt"

# Table columns for social posts
COLUMNS = ["date", "source", "content", "url"]


def extract_source_name(feed) -> str:
    """
    Extract source name from feed metadata.

    Args:
        feed: Parsed feedparser feed object

    Returns:
        Cleaned source name (e.g., "@Django@fosstodon.org")
    """
    if feed is None:
        return "Unknown"

    title = feed.feed.get("title", "")
    # Clean up common suffixes
    for suffix in [" RSS", " Feed", "'s posts"]:
        title = title.replace(suffix, "")
    return title.strip() or "Unknown"


def clean_social_content(raw: str, limit: int = 280) -> str:
    """
    Clean social media content for display.

    Args:
        raw: Raw HTML/text content
        limit: Maximum character length (default 280 for tweet-like content)

    Returns:
        Cleaned plain text content
    """
    # Use the shared clean_summary but with a higher limit for social posts
    return clean_summary(raw, limit=limit)


def main() -> int:
    """Main entry point for the social media scraper."""
    today = get_today()
    date_str = get_date_str(today)
    filepath = get_content_filepath(CONTENT_DIR, "social", today)

    # Ensure output directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Create placeholder if file doesn't exist
    if not filepath.exists():
        create_placeholder_file(
            filepath=filepath,
            title="Daily Social Media",
            date_str=date_str,
            columns=["#"] + COLUMNS,
            content_type="posts",
        )

    # Load social source URLs (profile pages or direct feed endpoints)
    social_sources = load_list(SOCIAL_SOURCES_FILE)
    if not social_sources:
        logger.info("No social sources configured — placeholder retained, skipping scrape.")
        return 0

    # Get existing URLs to avoid duplicates (checks all historical files)
    existing_urls = get_all_existing_urls(CONTENT_DIR / "social")

    # Fetch sources in parallel
    results, feeds_ok, feeds_failed = fetch_feeds_parallel(social_sources, max_workers=MAX_WORKERS)

    # Process entries
    new_entries = []
    for feed_url, feed, entries in results:
        if not entries:
            continue

        source_name = extract_source_name(feed)

        for entry in entries:
            url = entry.get("link", "").strip()
            # Social posts often use summary or content for the post text
            content = entry.get("summary", "") or entry.get("title", "")
            content = content.strip()

            # Skip if no URL or already exists
            if not url or url in existing_urls:
                continue

            # Date filtering: today only
            if not is_today(entry, today):
                continue

            entry_date = get_entry_date(entry)
            entry_date_str = entry_date.strftime("%d-%m-%Y") if entry_date else date_str

            new_entries.append({
                "date": entry_date_str,
                "source": escape_pipes(source_name),
                "content": escape_pipes(clean_social_content(content)),
                "url": url,
            })

            existing_urls.add(url)

    # Exit cleanly if nothing new
    if not new_entries:
        logger.info("No new social posts found today.")
        return 0

    # Append entries to file
    append_entries_to_file(
        filepath=filepath,
        entries=new_entries,
        columns=COLUMNS,
        section_title="New social posts",
    )

    logger.info(f"Added {len(new_entries)} social posts to {filepath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
