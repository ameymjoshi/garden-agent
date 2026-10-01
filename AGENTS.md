# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project

`garden-agent` is a personal balcony-garden care agent for Pune. It fuses a Markdown
plant inventory and care history with live local weather (Open-Meteo) to produce
specific daily care actions.

## Stack

- Python 3.12, standard library only (no third-party deps).
- Markdown state files under `garden/`.
- Telegram Bot API for notifications (credentials via environment variables).

## Conventions

### Always
- Keep `garden/` files valid Markdown with simple tables.
- Read weather only via `scripts/fetch_weather.py`.
- Read Telegram credentials from the environment — never hardcode them.
- Update `garden/schedule.md` and add a `garden/care-log/` entry when acting.

### Ask first
- Adding a third-party dependency.
- Changing the state-file schema.
- Committing anything to `garden/plants.md` that changes existing plants.

### Never
- Commit `.env` or any file containing secrets.
- Invent plant names that are not in `garden/plants.md`.
- Water or advise treatment for a plant not present in the inventory.

## Testing

- Run `python scripts/fetch_weather.py` — it should print a one-line weather summary.
- Run `python scripts/daily_digest.py` — it should print a digest without error.
- Notification path: `python scripts/notify_telegram.py "test"` (requires env vars).

## Gotchas

- Open-Meteo returns arrays; the first element is today.
- ET₀ is a *daily sum* in mm — the higher it is, the more water is lost.
- The digest must stay under ~150 words to be readable at a glance.
