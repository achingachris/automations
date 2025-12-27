# automations
Small Python automation that scrapes RSS/Atom feeds and publishes a daily Markdown digest.

GitHub CI Status:

[![Daily Article Scrape](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml/badge.svg)](https://github.com/achingachris/automations/actions/workflows/daily-scrape.yml)

## Project Structure

- `scripts/scrape_daily_articles.py`: Main entrypoint (fetch feeds -> filter by topics -> write Markdown tables).
- `content-source/topics.txt`: Topic keywords used for filtering.
- `content-source/feeds.txt`: RSS/Atom feeds to scrape, including the approved Medium publications.
- `daily-articles/`: Generated output, one file per day named `DD-MM-YYYY.md`.
- `.github/workflows/daily-scrape.yml`: Scheduled GitHub Action that runs the scraper and commits changes.

## Usage

- `python -m pip install feedparser`
- `python scripts/scrape_daily_articles.py`

Optional local setup (do not commit):
`python -m venv .venv && source .venv/bin/activate && python -m pip install feedparser`

## Notes

- The workflow updates `daily-articles/` on schedule; avoid manual edits unless debugging formatting.
