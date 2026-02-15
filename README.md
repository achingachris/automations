# automations
Small Python automation that scrapes RSS/Atom feeds and publishes a daily Markdown digest, plus a weekly AI-generated newsletter.

## Stats

<!-- STATS_START -->
| Metric | Count |
| --- | --- |
| Total Articles | 5171 |
| Total Newsletters | 14 |
| Total Social Posts | 4 |
| Last Updated | 2026-02-15 19:04 EAT |
<!-- STATS_END -->

## Recent Updates

<!-- DAILY_LOG_START -->
| Date | Articles | Newsletters | Social |
| --- | --- | --- | --- |
| 15-02-2026 | [0
0](content/articles/2026/02/15.md) | [0
0](content/newsletters/2026/02/15.md) | [0
0](content/social/2026/02/15.md) |
0](content/articles/2026/02/15.md) | [0
0](content/newsletters/2026/02/15.md) | [0
0](content/social/2026/02/15.md) |
0](content/articles/2026/02/15.md) | [0
0](content/newsletters/2026/02/15.md) | [0
0](content/social/2026/02/15.md) |
0](content/articles/2026/02/15.md) | [0
0](content/newsletters/2026/02/15.md) | [0
0](content/social/2026/02/15.md) |
<!-- DAILY_LOG_END -->

GitHub CI Status:

[![Daily Article Scrape](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml/badge.svg)](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml)
[![Weekly Newsletter](https://github.com/achingachris/automations/actions/workflows/weekly-newsletter.yml/badge.svg)](https://github.com/achingachris/automations/actions/workflows/weekly-newsletter.yml)

## Project Structure

```
├── scripts/
│   ├── shared.py                      # Shared utilities (logging, feed fetching, date handling)
│   ├── scrape_daily_articles.py       # Article scraper
│   ├── scrape_newsletters.py          # Newsletter scraper
│   ├── scrape_social.py               # Social media scraper
│   └── generate_weekly_newsletter.py  # Weekly newsletter generator (OpenAI)
├── content/
│   ├── articles/YYYY/MM/DD.md         # Daily article digests
│   ├── newsletters/YYYY/MM/DD.md      # Daily newsletter digests
│   ├── social/YYYY/MM/DD.md           # Daily social media digests
│   └── weekly/YYYY/WXX.md             # Weekly AI-generated newsletters
├── weekly-raw/
│   └── YYYY-WXX.txt                   # Raw fetched content for newsletters
├── content-source/
│   ├── feeds.txt                      # RSS/Atom feeds for articles
│   ├── newsletters.txt                # RSS/Atom feeds for newsletters
│   ├── social.txt                     # RSS/Atom feeds for social media
│   ├── newsletter-prompt.txt          # Newsletter generation prompt
│   └── editor-prompt.txt              # Editor/copyeditor prompt
└── .github/workflows/
    ├── daily-scrape.yml               # Scheduled GitHub Action (5x daily)
    └── weekly-newsletter.yml          # Weekly newsletter (Fridays 4PM EAT)
```

## Usage

```bash
# Install dependencies
pip install feedparser requests openai python-dotenv

# Run daily scrapers
python scripts/scrape_daily_articles.py
python scripts/scrape_newsletters.py
python scripts/scrape_social.py

# Generate weekly newsletter (requires OPENAI_API_KEY in .env or environment)
python scripts/generate_weekly_newsletter.py
```

Optional local setup (do not commit):
```bash
python -m venv .venv && source .venv/bin/activate
pip install feedparser requests openai python-dotenv
```

## Weekly Newsletter

The weekly newsletter generator:
1. Collects all articles, newsletters, and social posts from the past 7 days
2. Fetches full content from each URL
3. Sends content to OpenAI (gpt-4o-mini) for summarization
4. Applies an editor pass for polish and style consistency
5. Outputs to `content/weekly/YYYY/WXX.md`

Requires `OPENAI_API_KEY` set in environment or `.env` file.

## Notes

- The workflow updates `content/` directories on schedule; avoid manual edits unless debugging formatting.
- On first run, scrapers fetch all content from the current month.
- Content is organized by date: `content/{type}/YYYY/MM/DD.md`
