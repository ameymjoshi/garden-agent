#!/usr/bin/env python3
"""Optional LLM-backed message parser.

Uses an OpenAI-compatible chat endpoint, so the same code works with a local
Ollama server, Sarvam's cloud API, or Google Gemini (the model behind the
Antigravity IDE). If anything fails (server down, bad JSON, unknown action) the
caller falls back to the deterministic parser in garden_actions.

Environment:
  GARDEN_PARSER=llm                         # enable (default is 'rules')
  GARDEN_LLM_PROVIDER=ollama|sarvam|gemini  # default 'ollama' ('antigravity' = gemini)
  GARDEN_LLM_MODEL=...                      # default per provider
  GARDEN_LLM_BASE_URL=...                   # override the OpenAI-compatible base
  OLLAMA_HOST=...                           # default http://localhost:11434
  SARVAM_API_KEY=...                        # required when provider=sarvam
  GEMINI_API_KEY=...                        # required when provider=gemini/antigravity
"""
from __future__ import annotations

import json
import os
import urllib.request

ACTIONS = ["water", "skip", "fertilize", "spray", "repot", "prune", "sow",
           "rain", "note", "unknown"]

SYSTEM = (
    "You convert a gardener's short message into a single JSON action. "
    "Reply with ONLY compact JSON - no prose, no code fences.\n"
    'Schema: {"action": <string>, "plants": [<string>], "note": <string>}\n'
    "Allowed actions:\n"
    "  water     - watered the plants\n"
    "  skip      - deliberately did not water\n"
    "  fertilize - fed / manure / compost\n"
    "  spray     - pesticide / fungicide / neem / medicine\n"
    "  repot, prune, sow\n"
    "  rain      - it rained\n"
    "  note      - a free observation\n"
    "  unknown   - none of the above / cannot tell\n"
    "Rules:\n"
    "- plants must be EXACT names from the plant list below; use [] if none.\n"
    "- put any free-text observation in note (else empty string).\n"
)


def _config() -> tuple[str, str, str]:
    """Return (base_url, model, api_key) for the configured provider."""
    provider = os.environ.get("GARDEN_LLM_PROVIDER", "ollama").lower()
    if provider in ("gemini", "antigravity"):
        # Gemini API, OpenAI-compatible endpoint. Antigravity is powered by
        # Gemini, so 'antigravity' is accepted as an alias for 'gemini'.
        base = os.environ.get(
            "GARDEN_LLM_BASE_URL",
            "https://generativelanguage.googleapis.com/v1beta/openai",
        )
        model = os.environ.get("GARDEN_LLM_MODEL", "gemini-3.6-flash")
        key = os.environ.get("GEMINI_API_KEY", "")
    elif provider == "sarvam":
        base = os.environ.get("GARDEN_LLM_BASE_URL", "https://api.sarvam.ai/v1")
        model = os.environ.get("GARDEN_LLM_MODEL", "sarvam-105b")
        key = os.environ.get("SARVAM_API_KEY", "")
    else:  # ollama (default)
        host = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
        base = os.environ.get("GARDEN_LLM_BASE_URL", f"{host}/v1")
        model = os.environ.get("GARDEN_LLM_MODEL", "qwen2.5:1.5b")
        key = os.environ.get("GARDEN_LLM_API_KEY", "ollama")
    return base.rstrip("/"), model, key


def _coerce(content: str, plant_names: list[str]) -> dict | None:
    """Turn a model reply into a validated action dict, or None if unusable."""
    s = content.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        obj = json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return None

    action = obj.get("action")
    if action not in ACTIONS:
        return None
    if action == "unknown":
        action = None

    canon = {p.lower(): p for p in plant_names}
    plants: list[str] = []
    for p in obj.get("plants") or []:
        c = canon.get(str(p).lower())
        if c and c not in plants:
            plants.append(c)
    return {"action": action, "plants": plants,
            "note": str(obj.get("note") or ""), "raw": content}


def parse_with_llm(text: str, plant_names: list[str] | None = None,
                   timeout: int = 30) -> dict | None:
    """Parse `text` via the configured LLM. Returns None on any failure so the
    caller can fall back to the deterministic parser."""
    from garden_actions import load_plant_names  # deferred to avoid an import cycle

    plant_names = plant_names if plant_names is not None else load_plant_names()
    base, model, key = _config()
    payload = {
        "model": model,
        "messages": [
            {"role": "system",
             "content": SYSTEM + "Plant list: " + ", ".join(plant_names)},
            {"role": "user", "content": text},
        ],
        "temperature": 0,
        "stream": False,
    }
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as resp:
        out = json.loads(resp.read().decode("utf-8"))
    content = out["choices"][0]["message"]["content"]
    return _coerce(content, plant_names)
