# 🌿 garden-agent

A balcony-garden care agent for Pune. It keeps a living model of your pots — inventory, watering schedule, history — and fuses it with live local weather to hand you a short, specific list of care actions each morning.

The point is not the weather. The point is weather **fused with your plants and your history**: the same pot that needs water daily in April can go a week in July.

---

## Why this exists

A balcony garden is a small, high-stakes, weather-sensitive system. Pots have tiny soil volume, so there is no groundwater buffer — they dry out fast and flood fast. Pune swings hard between seasons:

- **Summer (Mar–May):** scorching and dry, often 35–40 °C with low humidity.
- **Monsoon (Jun–Sep):** the risk flips from underwatering to root rot and fungus.
- **Winter (Nov–Feb):** mild and dry, with occasional cold nights.

Generic advice fails because it does not know *your* plants, *your* pots, *your* balcony's sun, or *when you last watered*. This agent holds a model of your specific garden and turns vague plant-anxiety into a short, concrete daily action list.

## When you would call it

- **Daily digest (the workhorse):** scheduled each morning before you leave — "Water the tomato and mint; skip the snake plant, still moist; move seedlings into shade, 38 °C today; rain likely by evening, so hold the railing pots."
- **On demand:** "Should I water today?", "What is wrong with my basil leaves?", "What can I sow now?", "Plan my weekend repotting."
- **Event-triggered alerts:** heatwave > 38 °C → shade-net advice; first heavy monsoon rain → drainage and fungal check; winter cold snap < 10 °C → protect tender plants.
- **Weekly / seasonal review:** fertilising cadence, repotting windows, pest sweep.

A fixed reminder overwaters in monsoon and underwater in summer — the agent recalibrates.

## What it stores

Plain Markdown state, so it is diffable and human-readable (the same pattern as other agent projects):

| File | Purpose |
| --- | --- |
| `garden/config.md` | Balcony location, coordinates, orientation, notification prefs |
| `garden/plants.md` | Inventory: each plant's species, pot, sun, water need, notes |
| `garden/schedule.md` | Per-plant cadence, last-done date, next-due date |
| `garden/health.md` | Pest / disease incidents and treatments |
| `garden/season.md` | Current-season plan: sowing and repotting windows |
| `garden/care-log/YYYY-MM-DD.md` | One file per day: weather snapshot, actions, observations |

## Weather data

**[Open-Meteo](https://open-meteo.com/)** — free, no API key, no sign-up, CC BY 4.0, up to 10,000 calls/day for non-commercial use. It covers Pune cleanly (18.52 N, 73.86 E).

Live sample for Pune:

| Variable | Value (1 Oct) |
| --- | --- |
| Current temp / humidity | 26.4 °C / 68 % |
| Today max / min | 32.7 °C / 22.3 °C |
| Rain probability / sum | 51 % / 0.2 mm |
| **Reference ET₀** | **4.84 mm** |
| UV index max | 7.95 |
| Sunrise / sunset | 06:24 / 18:23 |

The key variable is **ET₀ (reference evapotranspiration)** — the standard irrigation metric, where 1 mm ET₀ ≈ 1 litre of water lost per square metre per day. That is what lets the agent *estimate* water need instead of guessing. The API also exposes soil temperature and soil moisture at several depths, plus a historical archive back to 1940.

## How it works

1. **Trigger** — a daily cron, or your on-demand question.
2. **Fetch weather** — one HTTP GET to Open-Meteo for your coordinates.
3. **Read state** — `plants.md`, `schedule.md`, yesterday's log.
4. **Reason** — per-plant water need × today's weather × days-since-watered → a decision per plant.
5. **Write** — append to today's `care-log`, update `schedule.md`.
6. **Notify** — push the digest via Telegram, or just leave the Markdown in the repo.

Worked example on the live data above: ET₀ of 4.84 mm means meaningful moisture loss, so most pots want morning water — but 51 % evening rain probability says water lightly and re-check after; UV 7.95 means shade tender seedlings; the 22.3 °C minimum is comfortable, so no cold protection needed.

## Two-way control (Telegram → garden)

The digest is outbound only. The listener makes it conversational: you text the bot what you actually did, and it updates the state files and replies.

```bash
export TELEGRAM_BOT_TOKEN=...
python scripts/telegram_listener.py     # long-polls; Ctrl+C to stop
```

Then send plain-language messages:

| You send | Effect |
| --- | --- |
| `watered Tulsi and Mint` | Sets last-done = today, next-due = today + cadence, logs it |
| `watered the plants` (no names) | Waters everything currently due |
| `it rained` | Pushes watering for all plants by a day |
| `fertilised Tomato` | Logs a fertilising action |
| `sprayed neem on Chilli` | Logs a spray and adds a row to `health.md` |
| `repotted Aloe` / `pruned Hibiscus` | Logs the action |
| `note basil leaves curling` | Adds a free observation to today's log |
| `/status` | Lists what is due today |
| `/log` | Prints today's care log |
| `/help` | Shows the command list |

Parsing is deterministic (keyword + plant-name matching against `plants.md`), so it works offline. Anything it cannot understand gets a clarifying reply rather than a silent guess. The listener is stateless apart from a `.telegram_offset` file, so restarts do not replay old messages, and if `TELEGRAM_CHAT_ID` is set only that chat is accepted.

## Quickstart

```bash
git clone https://github.com/ameymjoshi/garden-agent.git
cd garden-agent

python scripts/fetch_weather.py       # print today's weather
python scripts/daily_digest.py        # build the digest from weather + schedule

# Telegram notifications (optional)
export TELEGRAM_BOT_TOKEN=...          # from @BotFather
export TELEGRAM_CHAT_ID=...            # your chat id
python scripts/daily_digest.py --notify

# Two-way control: reply from Telegram to log what you did
python scripts/telegram_listener.py
```

No dependencies beyond the Python standard library.

## Repo layout

```text
garden-agent/
├── README.md
├── AGENTS.md
├── .github/agents/garden-agent.agent.md   # the agent definition
├── garden/
│   ├── config.md
│   ├── plants.md
│   ├── schedule.md
│   ├── health.md
│   ├── season.md
│   └── care-log/2026-10-01.md
├── scripts/
│   ├── fetch_weather.py
│   ├── telegram_api.py        # Telegram Bot API helpers
│   ├── notify_telegram.py     # outbound CLI
│   ├── garden_actions.py      # parse messages -> update state
│   ├── telegram_listener.py   # inbound: poll + apply + reply
│   ├── daily_digest.py
│   └── selftest.py
└── .env.example
```

## Roadmap

- [x] Two-way Telegram control — reply to log watering, fertilising, spraying.
- [ ] Wire the agent into Copilot / Kilo / Ollama (the `.agent.md` is runtime-agnostic).
- [ ] Plant photo diagnosis with a local vision model.
- [ ] Cron the daily digest.
- [ ] Seasonal sowing planner.

## License

MIT.
