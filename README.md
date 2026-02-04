# automations
Small Python automation that scrapes RSS/Atom feeds and publishes a daily Markdown digest.

## Stats

<!-- STATS_START -->
| Metric | Count |
| --- | --- |
| Total Articles | 5700 |
| Total Newsletters | 80 |
| Total Social Posts | 0 |
| Last Updated | 2026-02-04 12:13 EAT |
<!-- STATS_END -->

## Recent Updates

<!-- DAILY_LOG_START -->
| Date | Articles | Newsletters | Social |
| --- | --- | --- | --- |
| 26-01-2026 | 58 | 7 | 0 |
| 25-01-2026 | 55 | 7 | 0 |
| 24-01-2026 | 55 | 7 | 0 |
| 23-01-2026 | 54 | 7 | 0 |
| 22-01-2026 | 53 | 6 | 0 |
| 21-01-2026 | 84 | 8 | 0 |
<!-- DAILY_LOG_END -->

GitHub CI Status:

[![Daily Article Scrape](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml/badge.svg)](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml)

## Project Structure

```
├── scripts/
│   ├── shared.py                 # Shared utilities (logging, feed fetching, date handling)
│   ├── scrape_daily_articles.py  # Article scraper
│   ├── scrape_newsletters.py     # Newsletter scraper
│   └── scrape_social.py          # Social media scraper
├── content/
│   ├── articles/YYYY/MM/DD.md    # Daily article digests
│   ├── newsletters/YYYY/MM/DD.md # Daily newsletter digests
│   └── social/YYYY/MM/DD.md      # Daily social media digests
├── content-source/
│   ├── feeds.txt                 # RSS/Atom feeds for articles
│   ├── newsletters.txt           # RSS/Atom feeds for newsletters
│   └── social.txt                # RSS/Atom feeds for social media
└── .github/workflows/
    └── daily-scrape.yml          # Scheduled GitHub Action (5x daily)
```

## Usage

```bash
# Install dependencies
python -m pip install -r requirements.txt

# Run scrapers
python scripts/scrape_daily_articles.py
python scripts/scrape_newsletters.py
python scripts/scrape_social.py
```

Optional local setup (do not commit):
```bash
python -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt
```

## Notes

- The workflow updates `content/` directories on schedule; avoid manual edits unless debugging formatting.
- On first run, scrapers fetch all content from the current month.
- Content is organized by date: `content/{type}/YYYY/MM/DD.md`
