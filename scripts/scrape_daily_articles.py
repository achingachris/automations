#!/usr/bin/env python3
"""
Daily Tech Articles Scraper

Fetches content sources (website/profile URLs or direct feeds) and compiles a daily Markdown digest.
Uses Africa/Nairobi timezone for date filtering.

Output structure: content/articles/YYYY/MM/DD.md
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
MAX_WORKERS = 10

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT_DIR / "content"
FEEDS_DIR = ROOT_DIR / "content-source"
SOURCES_FILE = FEEDS_DIR / "feeds.txt"

# Table columns for articles
COLUMNS = ["date", "title", "url", "summary"]


def main() -> int:
    """Main entry point for the article scraper."""
    today = get_today()
    date_str = get_date_str(today)
    filepath = get_content_filepath(CONTENT_DIR, "articles", today)

    # Ensure output directory exists
    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Create placeholder if file doesn't exist
    if not filepath.exists():
        create_placeholder_file(
            filepath=filepath,
            title="Daily Tech Articles",
            date_str=date_str,
            columns=["#"] + COLUMNS,
            content_type="articles",
        )

    # Load source URLs (site pages or direct feed endpoints)
    sources = load_list(SOURCES_FILE)
    if not sources:
        logger.info("No article sources configured — placeholder retained, skipping scrape.")
        return 0

    # Get existing URLs to avoid duplicates (checks all historical files)
    existing_urls = get_all_existing_urls(CONTENT_DIR / "articles")

    # Fetch sources in parallel
    results, feeds_ok, feeds_failed = fetch_feeds_parallel(sources, max_workers=MAX_WORKERS)

    # Process entries
    new_entries = []
    for feed_url, feed, entries in results:
        if not entries:
            continue

        for entry in entries:
            url = entry.get("link", "").strip()
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "").strip()

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
                "title": escape_pipes(title),
                "url": url,
                "summary": escape_pipes(clean_summary(summary)),
            })

            existing_urls.add(url)

    # Exit cleanly if nothing new
    if not new_entries:
        logger.info("No new articles found today.")
        return 0

    # Append entries to file
    append_entries_to_file(
        filepath=filepath,
        entries=new_entries,
        columns=COLUMNS,
        section_title="Additional articles",
    )

    logger.info(f"Added {len(new_entries)} articles to {filepath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
