# Repository Guidelines

This repository is a small Python automation that scrapes RSS/Atom feeds and publishes a daily Markdown digest.

## Project Structure & Module Organization

- `scripts/scrape_daily_articles.py`: Main entrypoint (fetch feeds → filter by topics → write Markdown tables).
- `config/topics.txt`: Topic keywords; also used to generate Medium tag feed URLs.
- `config/feeds.txt`: Extra (non‑Medium) RSS/Atom feeds.
- `daily-articles/`: Generated output, one file per day named `DD-MM-YYYY.md`.
- `.github/workflows/daily-scrape.yml`: Scheduled GitHub Action that runs the scraper and commits changes.

## Build, Test, and Development Commands

- `python -m pip install feedparser`: Install the runtime dependency used by CI.
- `python scripts/scrape_daily_articles.py`: Run the scraper locally; updates today’s file in `daily-articles/`.
- `python -m compileall scripts`: Quick syntax sanity check before pushing.

Example local setup (recommended; don’t commit it):
`python -m venv .venv && source .venv/bin/activate && python -m pip install feedparser`

## Coding Style & Naming Conventions

- Python: 4‑space indentation, `snake_case` for functions/vars, `UPPER_SNAKE_CASE` for constants.
- Keep diffs focused in `scripts/` and `config/`.
- No formatter/linter is enforced today; keep changes readable and consistent with existing style.

## Testing Guidelines

There is no dedicated test suite yet.

- Prefer small, deterministic helper functions when changing parsing/filtering logic.
- Validate by running the script and verifying Markdown table output (headers intact, pipe characters escaped).

## Commit & Pull Request Guidelines

- Commit messages follow a simple “type: summary” convention (e.g., `chore: ...`, `refactor: ...`, `docs: ...`).
- PRs should include: a clear description, relevant `config/*.txt` changes, and output diffs/screenshots if behavior changes.
- Keep CI green; the workflow runs on Python 3.11 and will overwrite `daily-articles/` on schedule.

## Automation Notes

`daily-articles/` is typically updated by CI. Avoid manual edits unless you’re debugging formatting; they may be overwritten on the next run.
