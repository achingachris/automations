# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python automation that scrapes RSS/Atom feeds and publishes a daily Markdown digest of tech articles. Runs on a scheduled GitHub Action (5 times daily in Africa/Nairobi timezone).

## Commands

```bash
# Install dependency
python -m pip install feedparser

# Run article scraper (creates/updates today's file in daily-articles/)
python scripts/scrape_daily_articles.py

# Run newsletter scraper (creates/updates today's file in daily-newsletters/)
python scripts/scrape_newsletters.py

# Syntax check before pushing
python -m compileall scripts

# Local dev setup (don't commit venv)
python -m venv .venv && source .venv/bin/activate && pip install feedparser
```

## Architecture

**Article scraper** (`scripts/scrape_daily_articles.py`):
1. Loads topics from `content-source/topics.txt` and feeds from `content-source/feeds.txt`
2. Fetches RSS/Atom feeds in parallel via `feedparser`
3. Filters entries by today's date (Africa/Nairobi timezone) and topic keywords
4. Appends new articles to `daily-articles/DD-MM-YYYY.md` as Markdown tables
5. Deduplicates by URL against existing file content

**Newsletter scraper** (`scripts/scrape_newsletters.py`):
1. Loads newsletter feeds from `content-source/newsletters.txt`
2. Fetches feeds in parallel, no topic filtering (newsletters are curated)
3. Appends new issues to `daily-newsletters/DD-MM-YYYY.md`

**Content sources**:
- `content-source/topics.txt`: Keywords for filtering articles (one per line, case-insensitive)
- `content-source/feeds.txt`: RSS/Atom feed URLs for articles
- `content-source/newsletters.txt`: RSS/Atom feed URLs for newsletters

**Output**:
- `daily-articles/` — article digests by date
- `daily-newsletters/` — newsletter issues by date

## Key Behaviors

- Script exits with code 0 even when no articles found (to avoid failing CI)
- Creates placeholder file if none exists for today
- Timezone is `Africa/Nairobi` with UTC fallback
- Pipe characters in content are escaped for Markdown tables
- CI runs on Python 3.11

## Commit Convention

Use `type: summary` format (e.g., `chore:`, `refactor:`, `docs:`).

## Important Notes

- Do not modify `.github/workflows/daily-scrape.yml` unless explicitly asked
- Avoid manual edits to `daily-articles/` — CI will overwrite them
- No test suite exists; validate by running the script and checking output
