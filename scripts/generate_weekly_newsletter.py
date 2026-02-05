#!/usr/bin/env python3
"""
Weekly Newsletter Generator

Collects articles from the past 7 days, fetches content from URLs,
and uses OpenAI API to generate a weekly newsletter digest.

Usage:
    python scripts/generate_weekly_newsletter.py

Environment Variables:
    OPENAI_API_KEY - Required for API access
"""
from __future__ import annotations

import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: requests library required. Install with: pip install requests")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("Error: openai library required. Install with: pip install openai")
    sys.exit(1)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, rely on system environment variables

from shared import (
    logger,
    LOCAL_TZ,
    get_today,
    URL_PATTERN,
)

# ---- Configuration ----
ROOT_DIR = Path(__file__).resolve().parent.parent
CONTENT_DIR = ROOT_DIR / "content"
RAW_DIR = ROOT_DIR / "weekly-raw"
PROMPT_FILE = ROOT_DIR / "content-source" / "newsletter-prompt.txt"
EDITOR_PROMPT_FILE = ROOT_DIR / "content-source" / "editor-prompt.txt"

MAX_ARTICLES_FOR_API = 100  # Limit articles sent to API to minimize tokens
MAX_FETCH_WORKERS = 5
FETCH_TIMEOUT = 10
FETCH_DELAY = 0.3  # Delay between fetches to avoid rate limiting

# OpenAI Configuration
OPENAI_MODEL = "gpt-4o-mini"
MAX_TOKENS = 4000  # Increased for comprehensive newsletter with full content


def get_week_number(d: datetime.date) -> tuple[int, int]:
    """Get ISO week number and year for a date."""
    iso_cal = d.isocalendar()
    return iso_cal[0], iso_cal[1]  # (year, week)


def get_past_7_days() -> list[datetime.date]:
    """Get list of dates for the past 7 days (oldest first)."""
    today = get_today()
    return [today - timedelta(days=i) for i in range(6, -1, -1)]


def parse_markdown_table(filepath: Path) -> list[dict]:
    """
    Parse a markdown file and extract article entries from tables.

    Returns list of dicts with keys: date, title, url, summary
    """
    if not filepath.exists():
        return []

    content = filepath.read_text(encoding="utf-8")
    entries = []

    for line in content.splitlines():
        # Skip non-data rows
        if not line.startswith("|") or "http" not in line:
            continue
        if "---" in line:
            continue

        # Split by pipe and clean
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]  # Remove empty strings

        if len(parts) < 4:
            continue

        # Try to extract fields (format varies slightly between article/newsletter)
        # Articles: # | date | title | url | summary
        # Newsletters: # | date | newsletter | title | url
        try:
            # Find the URL in parts
            url_idx = None
            for i, p in enumerate(parts):
                if p.startswith("http"):
                    url_idx = i
                    break

            if url_idx is None:
                continue

            url = parts[url_idx]

            # Title is usually before URL
            title = parts[url_idx - 1] if url_idx > 0 else ""

            # Date is usually second field (after #)
            date_str = parts[1] if len(parts) > 1 and not parts[1].startswith("http") else ""

            # Summary is after URL (if exists)
            summary = parts[url_idx + 1] if url_idx + 1 < len(parts) else ""

            # Unescape any escaped pipes
            title = title.replace("\\|", "|")
            summary = summary.replace("\\|", "|")

            entries.append({
                "date": date_str,
                "title": title,
                "url": url,
                "summary": summary,
            })
        except (IndexError, ValueError):
            continue

    return entries


def collect_weekly_content() -> list[dict]:
    """Collect all articles, newsletters, and social media content from the past 7 days."""
    all_content = []
    counts = {"articles": 0, "newsletters": 0, "social": 0}

    for d in get_past_7_days():
        # Check articles
        articles_path = CONTENT_DIR / "articles" / str(d.year) / f"{d.month:02d}" / f"{d.day:02d}.md"
        for entry in parse_markdown_table(articles_path):
            entry["content_type"] = "article"
            all_content.append(entry)
            counts["articles"] += 1

        # Check newsletters
        newsletters_path = CONTENT_DIR / "newsletters" / str(d.year) / f"{d.month:02d}" / f"{d.day:02d}.md"
        for entry in parse_markdown_table(newsletters_path):
            entry["content_type"] = "newsletter"
            all_content.append(entry)
            counts["newsletters"] += 1

        # Check social media
        social_path = CONTENT_DIR / "social" / str(d.year) / f"{d.month:02d}" / f"{d.day:02d}.md"
        for entry in parse_markdown_table(social_path):
            entry["content_type"] = "social"
            all_content.append(entry)
            counts["social"] += 1

    logger.info(f"Collected {len(all_content)} items from past 7 days: "
                f"{counts['articles']} articles, {counts['newsletters']} newsletters, {counts['social']} social")
    return all_content


def fetch_url_content(url: str) -> tuple[str, str]:
    """
    Fetch and extract text content from a URL.

    Returns tuple of (url, extracted_text)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; NewsletterBot/1.0)"
        }
        response = requests.get(url, headers=headers, timeout=FETCH_TIMEOUT)
        response.raise_for_status()

        # Basic HTML text extraction (no BeautifulSoup dependency)
        html = response.text

        # Remove script and style tags
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Unescape HTML entities
        text = unescape(text)

        # Normalize whitespace
        text = " ".join(text.split())

        time.sleep(FETCH_DELAY)  # Rate limiting
        return url, text

    except Exception as e:
        logger.debug(f"Failed to fetch {url}: {e}")
        return url, ""


def fetch_all_content(articles: list[dict], max_workers: int = MAX_FETCH_WORKERS) -> dict[str, str]:
    """
    Fetch content from all article URLs in parallel.

    Returns dict mapping URL to extracted text.
    """
    url_to_content = {}
    urls = list(set(a["url"] for a in articles if a.get("url")))

    logger.info(f"Fetching content from {len(urls)} unique URLs...")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_url_content, url): url for url in urls}

        for future in as_completed(futures):
            url, content = future.result()
            if content:
                url_to_content[url] = content

    logger.info(f"Successfully fetched {len(url_to_content)}/{len(urls)} URLs")
    return url_to_content


def save_raw_content(articles: list[dict], url_content: dict[str, str], week_str: str) -> Path:
    """Save raw fetched content to a text file for debugging."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    filepath = RAW_DIR / f"{week_str}.txt"

    lines = [
        f"Weekly Raw Content - {week_str}",
        f"Generated: {datetime.now(LOCAL_TZ).isoformat()}",
        f"Total articles: {len(articles)}",
        f"URLs fetched: {len(url_content)}",
        "=" * 80,
        "",
    ]

    for article in articles:
        url = article.get("url", "")
        lines.append(f"Title: {article.get('title', 'N/A')}")
        lines.append(f"Date: {article.get('date', 'N/A')}")
        lines.append(f"URL: {url}")
        lines.append("")
        lines.append("--- FULL CONTENT ---")

        if url in url_content:
            lines.append(url_content[url])
        else:
            lines.append("[Content could not be fetched]")

        lines.append("")
        lines.append("=" * 80)
        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Saved raw content to {filepath}")
    return filepath


def prepare_articles_for_api(articles: list[dict], url_content: dict[str, str]) -> str:
    """
    Prepare article data for OpenAI API with full content.

    Includes title, URL, and full fetched content for each article.
    Content is truncated per article to manage token usage.
    """
    # Limit number of articles
    if len(articles) > MAX_ARTICLES_FOR_API:
        logger.info(f"Limiting articles from {len(articles)} to {MAX_ARTICLES_FOR_API}")
        articles = articles[:MAX_ARTICLES_FOR_API]

    lines = []
    max_content_per_article = 2000  # Chars per article to balance detail vs tokens

    for i, article in enumerate(articles, 1):
        title = article.get("title", "").strip()
        url = article.get("url", "").strip()
        date = article.get("date", "").strip()
        content_type = article.get("content_type", "article")

        type_label = {"article": "Article", "newsletter": "Newsletter", "social": "Social"}.get(content_type, "Item")
        lines.append(f"### {type_label} {i}")
        lines.append(f"**Title:** {title}")
        lines.append(f"**Date:** {date}")
        lines.append(f"**URL:** {url}")

        # Include full content (truncated to manage tokens)
        if url in url_content:
            content = url_content[url]
            if len(content) > max_content_per_article:
                content = content[:max_content_per_article] + "..."
            lines.append(f"**Content:**\n{content}")
        else:
            lines.append("**Content:** [Not available]")

        lines.append("")  # Blank line between articles

    return "\n".join(lines)


def generate_newsletter_with_openai(articles: list[dict], url_content: dict[str, str], prompt_template: str) -> str:
    """
    Use OpenAI API to generate newsletter from articles.

    Uses gpt-4o-mini for cost efficiency.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=api_key)

    # Prepare article data with full content
    articles_text = prepare_articles_for_api(articles, url_content)

    # Build the prompt
    user_message = f"""Here are {len(articles)} tech articles from this week with their full content:

{articles_text}

Based on the above articles and their content, please create a comprehensive weekly newsletter digest."""

    logger.info(f"Sending {len(articles)} articles to OpenAI API...")
    logger.info(f"Input tokens (estimated): ~{len(user_message.split()) * 1.3:.0f}")

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": user_message}
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.7,
        )

        newsletter_content = response.choices[0].message.content

        # Log token usage
        usage = response.usage
        logger.info(f"API tokens used - Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}")

        return newsletter_content

    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        raise


def edit_newsletter_with_openai(draft: str) -> str:
    """
    Use OpenAI API to edit and polish the newsletter draft.

    Acts as a copyeditor to improve clarity and style.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Load editor prompt from file
    if EDITOR_PROMPT_FILE.exists():
        editor_prompt = EDITOR_PROMPT_FILE.read_text(encoding="utf-8")
    else:
        logger.warning(f"Editor prompt file not found: {EDITOR_PROMPT_FILE}, using default")
        editor_prompt = "You are an expert copyeditor. Improve the draft while preserving meaning and the author's voice."

    client = OpenAI(api_key=api_key)

    logger.info("Sending newsletter to editor...")

    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": editor_prompt},
                {"role": "user", "content": f"Please edit and improve this newsletter draft:\n\n{draft}"}
            ],
            max_tokens=MAX_TOKENS,
            temperature=0.3,  # Lower temperature for more consistent editing
        )

        edited_content = response.choices[0].message.content

        # Log token usage
        usage = response.usage
        logger.info(f"Editor tokens used - Prompt: {usage.prompt_tokens}, Completion: {usage.completion_tokens}, Total: {usage.total_tokens}")

        return edited_content

    except Exception as e:
        logger.error(f"Editor API error: {e}")
        # Return original draft if editing fails
        logger.warning("Returning unedited draft due to editor error")
        return draft


def save_newsletter(content: str, week_str: str, year: int) -> Path:
    """Save the generated newsletter to markdown file."""
    output_dir = CONTENT_DIR / "weekly" / str(year)
    output_dir.mkdir(parents=True, exist_ok=True)

    filepath = output_dir / f"{week_str.split('-')[1]}.md"  # e.g., "W05.md"

    # Add header
    today = get_today()
    full_content = f"""# Weekly Tech Digest - {week_str}

*Generated on {today.strftime('%Y-%m-%d')} | Covering {(today - timedelta(days=7)).strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}*

{content}

---
*This newsletter was automatically generated from {week_str} scraped articles.*
"""

    filepath.write_text(full_content, encoding="utf-8")
    logger.info(f"Saved newsletter to {filepath}")
    return filepath


def main() -> int:
    """Main entry point for the weekly newsletter generator."""
    today = get_today()
    year, week = get_week_number(today)
    week_str = f"{year}-W{week:02d}"

    logger.info(f"Generating weekly newsletter for {week_str}")

    # Load prompt template
    if PROMPT_FILE.exists():
        prompt_template = PROMPT_FILE.read_text(encoding="utf-8")
    else:
        logger.warning(f"Prompt file not found: {PROMPT_FILE}, using default")
        prompt_template = "Create a concise weekly tech newsletter from the provided articles."

    # Collect all content from past 7 days
    articles = collect_weekly_content()

    if not articles:
        logger.info("No content found for the past week. Skipping newsletter generation.")
        return 0

    # Fetch URL content
    url_content = fetch_all_content(articles)

    # Save raw content for reference
    save_raw_content(articles, url_content, week_str)

    # Generate newsletter with OpenAI using full content
    try:
        newsletter_content = generate_newsletter_with_openai(articles, url_content, prompt_template)
    except ValueError as e:
        logger.error(str(e))
        return 1
    except Exception as e:
        logger.error(f"Failed to generate newsletter: {e}")
        return 1

    # Edit and polish the newsletter
    newsletter_content = edit_newsletter_with_openai(newsletter_content)

    # Save newsletter
    save_newsletter(newsletter_content, week_str, year)

    logger.info("Weekly newsletter generation complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
