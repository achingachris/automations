#!/usr/bin/env python3
"""
Daily Newsletter Scraper

Fetches newsletter sources (website URLs or direct feeds) and compiles a daily Markdown digest.
Uses Africa/Nairobi timezone for date filtering.

Output structure: content/newsletters/YYYY/MM/DD.md
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
    escape_pipes,
    fetch_feeds_parallel,
    get_all_existing_urls,
    create_placeholder_file,
    append_entries_to_file,
)

# ---- Configuration ----
MAX_WORKERS = 5  # Fewer workers for newsletters (typically fewer feeds)

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT_DIR / "content"
FEEDS_DIR = ROOT_DIR / "content-source"
NEWSLETTER_SOURCES_FILE = FEEDS_DIR / "newsletters.txt"

# Table columns for newsletters
COLUMNS = ["date", "newsletter", "title", "url"]


def extract_newsletter_name(feed) -> str:
    """
    Extract newsletter name from feed metadata.

    Args:
        feed: Parsed feedparser feed object

    Returns:
        Cleaned newsletter title
    """
    if feed is None:
        return "Unknown"

    title = feed.feed.get("title", "")
    # Clean up common suffixes
    for suffix in [" - All Issues", " RSS", " Feed", " Newsletter"]:
        title = title.replace(suffix, "")
    return title.strip() or "Unknown"


def main() -> int:
    """Main entry point for the newsletter scraper."""
    today = get_today()
    date_str = get_date_str(today)
    filepath = get_content_filepath(CONTENT_DIR, "newsletters", today)

    # Ensure output directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Create placeholder if file doesn't exist
    if not filepath.exists():
        create_placeholder_file(
            filepath=filepath,
            title="Daily Newsletters",
            date_str=date_str,
            columns=["#"] + COLUMNS,
            content_type="newsletters",
        )

    # Load newsletter source URLs (site pages or direct feed endpoints)
    newsletter_sources = load_list(NEWSLETTER_SOURCES_FILE)
    if not newsletter_sources:
        logger.info("No newsletter sources configured — placeholder retained, skipping scrape.")
        return 0

    # Get existing URLs to avoid duplicates (checks all historical files)
    existing_urls = get_all_existing_urls(CONTENT_DIR / "newsletters")

    # Fetch sources in parallel
    results, feeds_ok, feeds_failed = fetch_feeds_parallel(newsletter_sources, max_workers=MAX_WORKERS)

    # Process entries
    new_entries = []
    for feed_url, feed, entries in results:
        if not entries:
            continue

        newsletter_name = extract_newsletter_name(feed)

        for entry in entries:
            url = entry.get("link", "").strip()
            title = entry.get("title", "").strip()

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
                "newsletter": escape_pipes(newsletter_name),
                "title": escape_pipes(title),
                "url": url,
            })

            existing_urls.add(url)

    # Exit cleanly if nothing new
    if not new_entries:
        logger.info("No new newsletters found today.")
        return 0

    # Append entries to file
    append_entries_to_file(
        filepath=filepath,
        entries=new_entries,
        columns=COLUMNS,
        section_title="New newsletters",
    )

    logger.info(f"Added {len(new_entries)} newsletter issues to {filepath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
