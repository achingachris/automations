# Repository Guidelines

This repository is a small Python automation that scrapes website/profile sources (with feed auto-discovery) and publishes a daily Markdown digest.

## Project Structure & Module Organization

- `scripts/shared.py`: Shared utilities (logging, date handling, feed fetching, Markdown helpers).
- `scripts/scrape_daily_articles.py`: Article scraper (source URLs/feed URLs → filter by date → write Markdown tables).
- `scripts/scrape_newsletters.py`: Newsletter scraper (source URLs/feed URLs → filter by date → write Markdown tables).
- `scripts/scrape_social.py`: Social scraper (source URLs/feed URLs → filter by date → write Markdown tables).
- `scripts/generate_weekly_newsletter.py`: Weekly newsletter generator (OpenAI).
- `content-source/feeds.txt`: Article source URLs (website/profile URLs preferred).
- `content-source/newsletters.txt`: Newsletter source URLs (website URLs preferred).
- `content-source/social.txt`: Social source URLs (profile URLs preferred).
- `content-source/newsletter-prompt.txt`: Prompt for weekly newsletter generation.
- `content-source/editor-prompt.txt`: Editor/copyeditor prompt for weekly newsletters.
- `content/`: Generated output (`articles/`, `newsletters/`, `social/`, `weekly/`).
- `.github/workflows/daily-scrape.yml`: Scheduled GitHub Action for daily scraping.
- `.github/workflows/weekly-newsletter.yml`: Scheduled GitHub Action for weekly newsletter generation.

## Build, Test, and Development Commands

- `python -m pip install feedparser`: Install the runtime dependency used by CI.
- `python scripts/scrape_daily_articles.py`: Run the article scraper; updates today’s file in `content/articles/`.
- `python scripts/scrape_newsletters.py`: Run the newsletter scraper; updates today’s file in `content/newsletters/`.
- `python scripts/scrape_social.py`: Run the social scraper; updates today’s file in `content/social/`.
- `python scripts/generate_weekly_newsletter.py`: Generate weekly newsletter (requires `OPENAI_API_KEY`).
- `python -m compileall scripts`: Quick syntax sanity check before pushing.

Example local setup (recommended; don’t commit it):
`python -m venv .venv && source .venv/bin/activate && python -m pip install feedparser`

## Coding Style & Naming Conventions

- Python: 4‑space indentation, `snake_case` for functions/vars, `UPPER_SNAKE_CASE` for constants.
- Follow DRY and KISS principles.
- Keep diffs focused in `scripts/` and `content-source/`.
- No formatter/linter is enforced today; keep changes readable and consistent with existing style.

## Testing Guidelines

There is no dedicated test suite yet.

- Prefer small, deterministic helper functions when changing parsing/filtering logic.
- Validate by running the script and verifying Markdown table output (headers intact, pipe characters escaped).

## Commit & Pull Request Guidelines

- Commit messages follow a simple “type: summary” convention (e.g., `chore: ...`, `refactor: ...`, `docs: ...`).
- PRs should include: a clear description, relevant `content-source/*.txt` changes, and output diffs/screenshots if behavior changes.
- Keep CI green; the workflow runs on Python 3.11 and will overwrite `daily-articles/` on schedule.
- Do not change `.github/workflows/daily-scrape.yml` unless explicitly asked.
- Keep `README.md` up to date with current instructions.

## Automation Notes

Scrapers only include entries with a published date matching **today** in Africa/Nairobi timezone.
Social scraper deduplicates against all historical social content files.
Source files can contain website/profile URLs; scrapers auto-discover RSS/Atom links when needed.
`content/` is typically updated by CI. Avoid manual edits unless you’re debugging formatting; they may be overwritten on the next run.

## File Safety

- Do not delete any file in this repo or on the desktop.
