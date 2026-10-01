#!/usr/bin/env python3
"""Send a message to a Telegram chat via the Bot API.

Credentials are read from the environment — never hardcode them here.

    export TELEGRAM_BOT_TOKEN=...   # token from @BotFather
    export TELEGRAM_CHAT_ID=...     # your chat / user id

Create a bot with @BotFather, then message it once and read your chat id from
https://api.telegram.org/bot<token>/getUpdates
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

API_BASE = "https://api.telegram.org"


def send_message(text: str, token: str | None = None,
                 chat_id: str | None = None) -> dict:
    """Send `text` to the configured chat. Raises if credentials are missing."""
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        raise RuntimeError(
            "Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the environment "
            "(see .env.example)."
        )
    payload = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    ).encode("utf-8")
    request = urllib.request.Request(f"{API_BASE}/bot{token}/sendMessage", data=payload)
    with urllib.request.urlopen(request, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


if __name__ == "__main__":
    import sys

    message = " ".join(sys.argv[1:]) or "garden-agent test message"
    print(json.dumps(send_message(message), indent=2))
