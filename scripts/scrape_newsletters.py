#!/usr/bin/env python3
"""
Daily Newsletter Scraper

Fetches RSS/Atom feeds from newsletters and compiles a daily Markdown digest.
Uses Africa/Nairobi timezone for date filtering.

Output structure: content/newsletters/YYYY/MM/DD.md
"""

import sys
from pathlib import Path

from shared import (
    logger,
    LOCAL_TZ,
    get_today,
    get_date_str,
    get_content_filepath,
    load_list,
    get_entry_date,
    is_today,
    is_this_month,
    escape_pipes,
    fetch_feeds_parallel,
    get_existing_urls,
    count_existing_rows,
    create_placeholder_file,
)

# ---- Configuration ----
MAX_WORKERS = 5  # Fewer workers for newsletters (typically fewer feeds)

ROOT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT_DIR / "content"
FEEDS_DIR = ROOT_DIR / "content-source"
NEWSLETTERS_FILE = FEEDS_DIR / "newsletters.txt"

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

    # Load newsletter URLs
    newsletters = load_list(NEWSLETTERS_FILE)
    if not newsletters:
        logger.info("No newsletters configured — placeholder retained, skipping scrape.")
        return 0

    # Get existing URLs to avoid duplicates
    existing_urls = get_existing_urls(filepath)

    # Detect first run (no existing newsletters)
    first_run = count_existing_rows(filepath) == 0
    if first_run:
        logger.info("First run detected — fetching newsletters from this month")

    # Fetch feeds in parallel
    results, feeds_ok, feeds_failed = fetch_feeds_parallel(newsletters, max_workers=MAX_WORKERS)

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

            # Date filtering: first run gets this month, otherwise today only
            if first_run:
                if not is_this_month(entry, today):
                    continue
            else:
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
        msg = "No new newsletters found this month." if first_run else "No new newsletters found today."
        logger.info(msg)
        return 0

    # Append entries to file
    offset = count_existing_rows(filepath)

    lines = [
        "",
        f"## New newsletters ({get_date_str()} {LOCAL_TZ})",
        "",
        f"Summary: {len(new_entries)} new newsletter issues",
        "",
        "| # | date | newsletter | title | url |",
        "| --- | --- | --- | --- | --- |",
    ]

    for idx, row in enumerate(new_entries, start=offset + 1):
        lines.append(
            f"| {idx} | {row['date']} | {row['newsletter']} | {row['title']} | {row['url']} |"
        )

    with open(filepath, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    logger.info(f"Added {len(new_entries)} newsletter issues to {filepath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
