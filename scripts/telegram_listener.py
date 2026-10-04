#!/usr/bin/env python3
"""Two-way Telegram control for the garden.

Long-polls Telegram, applies each message as a garden action, and replies with a
confirmation. Run it on your own machine as a foreground process (or via Task
Scheduler / a service):

    export TELEGRAM_BOT_TOKEN=...
    python scripts/telegram_listener.py

The update offset is persisted in garden/.telegram_offset so restarts don't
replay old messages. Only messages from your own chat are accepted if
TELEGRAM_CHAT_ID is set.
"""
from __future__ import annotations

import datetime as dt
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import garden_actions as ga  # noqa: E402
from telegram_api import get_updates, send_message  # noqa: E402

OFFSET_FILE = ga.GARDEN / ".telegram_offset"

HELP = (
    "Garden bot\n"
    "Log what you did, in plain words:\n"
    "  - watered Tulsi and Mint\n"
    "  - fertilised Tomato\n"
    "  - sprayed neem on Chilli\n"
    "  - repotted Aloe\n"
    "  - it rained\n"
    "  - note basil leaves curling\n"
    "Commands: /status  /log  /help\n"
    "Parser: rules by default; set GARDEN_PARSER=llm (or pass --llm) for free phrasing."
)


def _load_offset() -> int | None:
    if OFFSET_FILE.exists():
        try:
            return int(OFFSET_FILE.read_text(encoding="utf-8").strip())
        except ValueError:
            return None
    return None


def _save_offset(offset: int) -> None:
    OFFSET_FILE.parent.mkdir(parents=True, exist_ok=True)
    OFFSET_FILE.write_text(str(offset), encoding="utf-8")


def handle(text: str, use_llm: bool | None = None) -> str:
    cmd = text.strip().lower()
    if cmd in ("/start", "/help"):
        return HELP
    if cmd == "/status":
        due = ga.due_plants()
        return "Due today: " + (", ".join(due) if due else "nothing - all watered.")
    if cmd == "/log":
        path = ga.CARE_LOG_DIR / f"{dt.date.today().isoformat()}.md"
        return path.read_text(encoding="utf-8") if path.exists() else "No log for today yet."
    if cmd.startswith("/"):
        return "Unknown command. Try /help."
    return ga.apply(text, use_llm=use_llm)["reply"]


def _authorised(chat_id: object) -> bool:
    allowed = os.environ.get("TELEGRAM_CHAT_ID")
    return not allowed or str(chat_id) == str(allowed)


def main() -> None:
    offset = _load_offset()
    use_llm = "--llm" in sys.argv or os.environ.get("GARDEN_PARSER", "rules").lower() == "llm"
    print(f"garden bot listening... parser={'llm' if use_llm else 'rules'} (Ctrl+C to stop)")
    while True:
        updates = get_updates(offset, timeout=25)
        for u in updates:
            offset = u["update_id"] + 1
            msg = u.get("message") or {}
            text = msg.get("text")
            chat_id = (msg.get("chat") or {}).get("id")
            if not text or chat_id is None or not _authorised(chat_id):
                continue
            try:
                reply = handle(text, use_llm=use_llm)
            except Exception as exc:  # noqa: BLE001
                reply = f"Error: {exc}"
            send_message(reply, chat_id=str(chat_id))
            print(f"< {text}\n> {reply}\n")
        if offset is not None:
            _save_offset(offset)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped.")
