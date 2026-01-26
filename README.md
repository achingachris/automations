# automations
Small Python automation that scrapes RSS/Atom feeds and publishes a daily Markdown digest.

## Stats

<!-- STATS_START -->
| Metric | Count |
| --- | --- |
| Total Articles | 5386 |
| Total Newsletters | 42 |
| Last Updated | 2026-01-26 19:06 EAT |
<!-- STATS_END -->

## Recent Updates

<!-- DAILY_LOG_START -->
| Date | Articles | Newsletters |
| --- | --- | --- |
| 26-01-2026 | 58 | 7 |
| Date | Articles | Newsletters |
| 25-01-2026 | 55 | 7 |
| Date | Articles | Newsletters |
| 24-01-2026 | 55 | 7 |
| Date | Articles | Newsletters |
| 23-01-2026 | 54 | 7 |
| Date | Articles | Newsletters |
| 22-01-2026 | 53 | 6 |
| 21-01-2026 | 84 | 8 |
<!-- DAILY_LOG_END -->

GitHub CI Status:

[![Daily Article Scrape](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml/badge.svg)](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml)

## Project Structure

- `scripts/scrape_daily_articles.py`: Article scraper (fetch feeds -> write Markdown tables).
- `scripts/scrape_newsletters.py`: Newsletter scraper (fetch newsletter feeds -> write Markdown tables).
- `content-source/feeds.txt`: RSS/Atom feeds for articles.
- `content-source/newsletters.txt`: RSS/Atom feeds for newsletters.
- `daily-articles/`: Generated article output, one file per day named `DD-MM-YYYY.md`.
- `daily-newsletters/`: Generated newsletter output, one file per day named `DD-MM-YYYY.md`.
- `.github/workflows/daily-scrape.yml`: Scheduled GitHub Action that runs both scrapers and commits changes.

## Usage

```bash
# Install dependencies
python -m pip install -r requirements.txt

# Run article scraper
python scripts/scrape_daily_articles.py

# Run newsletter scraper
python scripts/scrape_newsletters.py
```

Optional local setup (do not commit):
```bash
python -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt
```

## Notes

- The workflow updates `daily-articles/` and `daily-newsletters/` on schedule; avoid manual edits unless debugging formatting.
- On first run, scrapers fetch all content from the current month.
