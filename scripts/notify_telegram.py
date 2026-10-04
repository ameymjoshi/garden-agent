#!/usr/bin/env python3
"""Send a message to Telegram. Thin CLI over telegram_api.send_message().

Credentials come from the environment — never hardcode them here.

    export TELEGRAM_BOT_TOKEN=...   # token from @BotFather
    export TELEGRAM_CHAT_ID=...     # your chat / user id
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from telegram_api import send_message  # noqa: E402,F401  (re-exported for callers)


def main() -> None:
    message = " ".join(sys.argv[1:]) or "garden-agent test message"
    print(json.dumps(send_message(message, parse_mode="Markdown"), indent=2))


if __name__ == "__main__":
    main()
