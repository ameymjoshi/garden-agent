#!/usr/bin/env python3
"""Thin helpers over the Telegram Bot API. Credentials come from the environment.

    TELEGRAM_BOT_TOKEN  — token from @BotFather
    TELEGRAM_CHAT_ID    — your chat / user id (used for outbound messages)
"""
from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request

API_BASE = "https://api.telegram.org"


def _token(token: str | None) -> str:
    token = token or os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in the environment (see .env.example).")
    return token


def send_message(text: str, token: str | None = None, chat_id: str | None = None,
                 parse_mode: str | None = None) -> dict:
    """Send `text` to a chat. `chat_id` defaults to $TELEGRAM_CHAT_ID."""
    chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID")
    if not chat_id:
        raise RuntimeError("Set TELEGRAM_CHAT_ID (or pass chat_id).")
    params = {"chat_id": chat_id, "text": text}
    if parse_mode:
        params["parse_mode"] = parse_mode
    data = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(f"{API_BASE}/bot{_token(token)}/sendMessage", data=data)
    with urllib.request.urlopen(request, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_updates(offset: int | None = None, timeout: int = 25,
                token: str | None = None) -> list[dict]:
    """Long-poll for new messages. `offset` acknowledges everything before it."""
    params: dict[str, object] = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    url = f"{API_BASE}/bot{_token(token)}/getUpdates?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=timeout + 10) as resp:
        return json.loads(resp.read().decode("utf-8")).get("result", [])
