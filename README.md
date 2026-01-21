# automations
Small Python automation that scrapes RSS/Atom feeds and publishes a daily Markdown digest.

## Stats

<!-- STATS_START -->
| Metric | Count |
| --- | --- |
| Total Articles | 5056 |
| Total Newsletters | 8 |
| Last Updated | 2026-01-21 14:15 EAT |
<!-- STATS_END -->

## Recent Updates

<!-- DAILY_LOG_START -->
| Date | Articles | Newsletters |
| --- | --- | --- |
| 21-01-2026 | 29 | 8 |
<!-- DAILY_LOG_END -->

GitHub CI Status:

[![Daily Article Scrape](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml/badge.svg)](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml)

## Project Structure

- `scripts/scrape_daily_articles.py`: Article scraper (fetch feeds -> filter by topics -> write Markdown tables).
- `scripts/scrape_newsletters.py`: Newsletter scraper (fetch newsletter feeds -> write Markdown tables).
- `content-source/topics.txt`: Topic keywords used for filtering articles.
- `content-source/feeds.txt`: RSS/Atom feeds for articles.
- `content-source/newsletters.txt`: RSS/Atom feeds for newsletters.
- `daily-articles/`: Generated article output, one file per day named `DD-MM-YYYY.md`.
- `daily-newsletters/`: Generated newsletter output, one file per day named `DD-MM-YYYY.md`.
- `.github/workflows/daily-scrape.yml`: Scheduled GitHub Action that runs both scrapers and commits changes.

## Usage

```bash
# Install dependency
python -m pip install feedparser

# Run article scraper
python scripts/scrape_daily_articles.py

# Run newsletter scraper
python scripts/scrape_newsletters.py
```

Optional local setup (do not commit):
```bash
python -m venv .venv && source .venv/bin/activate && pip install feedparser
```

## Notes

- The workflow updates `daily-articles/` and `daily-newsletters/` on schedule; avoid manual edits unless debugging formatting.
- On first run, scrapers fetch all content from the current month.
