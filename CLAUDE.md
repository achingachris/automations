# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python automation that scrapes RSS/Atom feeds and publishes a daily Markdown digest of tech articles, plus a weekly AI-generated newsletter. Daily scrapers run 5 times daily; weekly newsletter runs Fridays at 4PM EAT.

## Commands

```bash
# Install dependencies
pip install feedparser requests openai python-dotenv

# Run article scraper (creates/updates today's file in content/articles/)
python scripts/scrape_daily_articles.py

# Run newsletter scraper (creates/updates today's file in content/newsletters/)
python scripts/scrape_newsletters.py

# Run social scraper (creates/updates today's file in content/social/)
python scripts/scrape_social.py

# Generate weekly newsletter (requires OPENAI_API_KEY)
python scripts/generate_weekly_newsletter.py

# Syntax check before pushing
python -m compileall scripts

# Local dev setup (don't commit venv)
python -m venv .venv && source .venv/bin/activate
pip install feedparser requests openai python-dotenv
```

## Architecture

**Article scraper** (`scripts/scrape_daily_articles.py`):
1. Loads feeds from `content-source/feeds.txt`
2. Fetches RSS/Atom feeds in parallel via `feedparser`
3. Filters entries by today's date (Africa/Nairobi timezone)
4. Appends new articles to `content/articles/YYYY/MM/DD.md` as Markdown tables
5. Deduplicates by URL against all historical files

**Newsletter scraper** (`scripts/scrape_newsletters.py`):
1. Loads newsletter feeds from `content-source/newsletters.txt`
2. Fetches feeds in parallel
3. Appends new issues to `content/newsletters/YYYY/MM/DD.md`
4. Deduplicates by URL against all historical files

**Social scraper** (`scripts/scrape_social.py`):
1. Loads social feeds from `content-source/social.txt`
2. Fetches feeds in parallel
3. Appends new posts to `content/social/YYYY/MM/DD.md`

**Weekly newsletter generator** (`scripts/generate_weekly_newsletter.py`):
1. Collects all content from past 7 days (articles, newsletters, social)
2. Fetches full text content from each URL
3. Saves raw content to `weekly-raw/YYYY-WXX.txt`
4. Sends to OpenAI (gpt-4o-mini) with prompt from `content-source/newsletter-prompt.txt`
5. Applies editor pass with prompt from `content-source/editor-prompt.txt`
6. Outputs final newsletter to `content/weekly/YYYY/WXX.md`

**Content sources**:
- `content-source/feeds.txt`: RSS/Atom feed URLs for articles
- `content-source/newsletters.txt`: RSS/Atom feed URLs for newsletters
- `content-source/social.txt`: RSS/Atom feed URLs for social media
- `content-source/newsletter-prompt.txt`: Newsletter generation prompt (customizable)
- `content-source/editor-prompt.txt`: Copyeditor prompt (customizable)

**Output**:
- `content/articles/` — daily article digests
- `content/newsletters/` — daily newsletter digests
- `content/social/` — daily social media digests
- `content/weekly/` — weekly AI-generated newsletters
- `weekly-raw/` — raw fetched content for debugging

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
- Do not modify `.github/workflows/weekly-newsletter.yml` unless explicitly asked
- Avoid manual edits to `content/` directories — CI will overwrite them
- Weekly newsletter requires `OPENAI_API_KEY` in environment or `.env` file
- No test suite exists; validate by running scripts and checking output
