#!/usr/bin/env python3
"""Build today's garden digest from live weather + the local schedule.

Usage:
    python scripts/daily_digest.py            # print only
    python scripts/daily_digest.py --notify   # also send via Telegram

This is the deterministic skeleton of the agent loop: fetch weather, read state,
decide, output. Swap the decision rules for an LLM prompt to make it fully agentic.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_weather import fetch_weather  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE = ROOT / "garden" / "schedule.md"


def read_due_plants(path: Path, today: dt.date | None = None) -> list[str]:
    """Parse schedule.md rows (| Plant | cadence | last | YYYY-MM-DD |) and
    return only the plants whose next-due date is today or earlier."""
    today = today or dt.date.today()
    if not path.exists():
        return []
    due: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 4 and re.match(r"\d{4}-\d{2}-\d{2}$", cells[3]):
            try:
                next_due = dt.date.fromisoformat(cells[3])
            except ValueError:
                continue
            if next_due <= today:
                due.append(cells[0])
    return due


def build_digest() -> str:
    weather = fetch_weather()
    daily = weather["daily"]
    today = {k: v[0] for k, v in daily.items() if k != "time"}
    et0 = today["et0_fao_evapotranspiration"]
    rain = today["precipitation_probability_max"]
    tmax = today["temperature_2m_max"]

    lines = [
        f"Garden digest - {dt.date.today().isoformat()}",
        f"{today['temperature_2m_min']}-{tmax} deg C | rain {rain}% | "
        f"ET0 {et0} mm | UV {today['uv_index_max']}",
        "Water: " + (", ".join(read_due_plants(SCHEDULE)) or "nothing due - check the thirstiest pots"),
    ]
    if et0 >= 5:
        lines.append("Alert: high water loss (ET0 >= 5 mm) - water early morning or evening.")
    if rain >= 60:
        lines.append("Alert: rain likely - water lightly, then re-check; ensure drainage.")
    if tmax >= 36:
        lines.append("Alert: heat - shade tender seedlings and leafy greens at mid-day.")
    lines.append("Log this run in garden/care-log/.")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--notify", action="store_true", help="also send via Telegram")
    args = parser.parse_args()

    digest = build_digest()
    print(digest)
    if args.notify:
        from notify_telegram import send_message

        send_message(digest)
        print("\n[sent via Telegram]")
