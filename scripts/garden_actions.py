#!/usr/bin/env python3
"""Parse free-text messages into garden actions and apply them to the Markdown
state files (schedule, care-log, health).

Deterministic and dependency-free, so it works offline and is easy to test.
Set GARDEN_ROOT to point at a different tree (used by the self-test).
"""
from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path

ROOT = Path(os.environ.get("GARDEN_ROOT") or Path(__file__).resolve().parent.parent)
GARDEN = ROOT / "garden"
PLANTS = GARDEN / "plants.md"
SCHEDULE = GARDEN / "schedule.md"
HEALTH = GARDEN / "health.md"
CARE_LOG_DIR = GARDEN / "care-log"

# Order matters: more specific intents first (skip before water, etc.).
ACTIONS: list[tuple[str, list[str]]] = [
    ("skip", ["skipped", "skip", "didn't water", "did not water", "not watered", "no water"]),
    ("water", ["watered", "water", "watering"]),
    ("fertilize", ["fertilized", "fertilised", "fertilizer", "fertiliser", "fed",
                   "manure", "compost", "npk"]),
    ("spray", ["sprayed", "spray", "spraying", "pesticide", "pesticides", "medicine",
               "neem", "fungicide", "insecticide"]),
    ("repot", ["repotted", "repot", "repotting"]),
    ("prune", ["pruned", "prune", "pruning", "trimmed", "trim"]),
    ("sow", ["sowed", "sow", "sowing", "planted", "seeded"]),
    ("rain", ["rained", "rain"]),
    ("note", ["note", "noted", "observed", "noticed"]),
]

VERB = {
    "water": "Watered",
    "skip": "Skipped watering",
    "fertilize": "Fertilised",
    "spray": "Sprayed",
    "repot": "Repotted",
    "prune": "Pruned",
    "sow": "Sowed",
    "rain": "Rain — skipped watering",
    "note": "Note",
}


# --------------------------------------------------------------------------- #
# Markdown table helpers
# --------------------------------------------------------------------------- #
def _table_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if not cells or set(cells[0]) <= set("- "):
            continue
        if cells[0].lower() == "plant":
            continue
        rows.append(cells)
    return rows


def load_plant_names() -> list[str]:
    return [r[0] for r in _table_rows(PLANTS)]


def _cadence_days(cadence: str) -> int | None:
    m = re.search(r"(\d+)", cadence)
    return int(m.group(1)) if m else None


def due_plants(day: dt.date | None = None) -> list[str]:
    day = day or dt.date.today()
    due: list[str] = []
    for r in _table_rows(SCHEDULE):
        if len(r) >= 4 and re.match(r"\d{4}-\d{2}-\d{2}$", r[3]):
            if dt.date.fromisoformat(r[3]) <= day:
                due.append(r[0])
    return due


def update_schedule(plants: set[str], day: dt.date,
                    force_interval: int | None = None) -> list[str]:
    """Set last-done = day and next-due = day + cadence for the given plants."""
    lines = SCHEDULE.read_text(encoding="utf-8").splitlines()
    out: list[str] = []
    changed: list[str] = []
    for line in lines:
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if (len(cells) >= 4 and cells[0] in plants
                    and cells[0].lower() != "plant"
                    and not set(cells[0]) <= set("- ")):
                interval = force_interval or _cadence_days(cells[1]) or 1
                cells[2] = day.isoformat()
                cells[3] = (day + dt.timedelta(days=interval)).isoformat()
                line = "| " + " | ".join(cells) + " |"
                changed.append(cells[0])
        out.append(line)
    SCHEDULE.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def _append_under_heading(path: Path, heading: str, bullet: str, day: dt.date) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {day.isoformat()}\n\n{heading}\n\n", encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    idx = next((i for i, l in enumerate(lines) if l.strip() == heading), None)
    if idx is None:
        text = text.rstrip() + f"\n\n{heading}\n\n{bullet}\n"
    else:
        j = idx + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        lines.insert(j, bullet)
        text = "\n".join(lines) + "\n"
    path.write_text(text, encoding="utf-8")


def log_care(day: dt.date, bullet: str) -> Path:
    path = CARE_LOG_DIR / f"{day.isoformat()}.md"
    _append_under_heading(path, "**Actions**", f"- {bullet}", day)
    return path


def log_health(day: dt.date, plant: str, note: str) -> None:
    """Append a row to the health.md table."""
    if not HEALTH.exists():
        return
    lines = HEALTH.read_text(encoding="utf-8").splitlines()
    new_row = f"| {day.isoformat()} | {plant} | {note} |  |  |  |"
    last = max((i for i, l in enumerate(lines) if l.strip().startswith("|")), default=None)
    if last is None:
        lines.append(new_row)
    else:
        lines.insert(last + 1, new_row)
    HEALTH.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --------------------------------------------------------------------------- #
# Parsing + applying
# --------------------------------------------------------------------------- #
def _match(low: str, keywords: list[str]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(kw)}(?!\w)", low) for kw in keywords)


def parse_message(text: str, plant_names: list[str] | None = None) -> dict:
    plant_names = plant_names if plant_names is not None else load_plant_names()
    low = text.lower().strip()
    action = next((canon for canon, kws in ACTIONS if _match(low, kws)), None)
    plants = [p for p in plant_names
              if re.search(rf"(?<!\w){re.escape(p.lower())}(?!\w)", low)]
    note = ""
    m = re.search(r"(?:note|observed|noticed)\b[:\s]+(.+)", text, re.IGNORECASE)
    if m:
        note = m.group(1).strip()
    return {"action": action, "plants": plants, "note": note, "raw": text}


def apply(message: str, day: dt.date | None = None) -> dict:
    """Parse `message`, update the state files, and return a result dict."""
    day = day or dt.date.today()
    parsed = parse_message(message)
    action, plants = parsed["action"], parsed["plants"]
    result: dict = {"parsed": parsed, "day": day.isoformat(), "changed": [], "reply": ""}

    if action is None:
        result["reply"] = ("I couldn't tell what you did. Try e.g. "
                           "\"watered Tulsi and Mint\", \"fertilised Tomato\", "
                           "\"sprayed neem on Chilli\", or /help.")
        return result

    if action in ("water", "skip", "rain"):
        targets = plants
        if action == "rain":
            targets = load_plant_names()
        if not targets:
            targets = due_plants(day)
        if not targets:
            result["reply"] = "Nothing matched. Check plant names in garden/plants.md."
            return result
        force = 1 if action in ("skip", "rain") else None
        changed = update_schedule(set(targets), day, force_interval=force)
        logged = changed or targets
        log_care(day, f"{VERB[action]}: {', '.join(logged)}")
        result["changed"] = logged
        if action == "rain":
            result["reply"] = "Noted rain - pushed watering for all plants. Logged."
        else:
            result["reply"] = f"{VERB[action]}: {', '.join(logged)}. Logged for {day.isoformat()}."
        return result

    if action in ("fertilize", "spray", "repot", "prune", "sow"):
        if not plants:
            result["reply"] = "Which plant(s)? Name at least one from garden/plants.md."
            return result
        log_care(day, f"{VERB[action]}: {', '.join(plants)}")
        if action == "spray":
            for p in plants:
                log_health(day, p, "spray / treatment")
        result["changed"] = plants
        result["reply"] = f"{VERB[action]}: {', '.join(plants)}. Logged for {day.isoformat()}."
        return result

    if action == "note":
        text = parsed["note"] or message
        log_care(day, f"Note: {text}")
        result["reply"] = f"Noted: {text}"
        return result

    result["reply"] = "Action not handled."
    return result
