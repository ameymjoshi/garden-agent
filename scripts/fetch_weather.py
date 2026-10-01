#!/usr/bin/env python3
"""Fetch today's weather for the garden from Open-Meteo (no API key required).

Open-Meteo is free for non-commercial use (CC BY 4.0) and needs no sign-up.
Docs: https://open-meteo.com/en/docs
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

# Pune default — change these (or pass lat/lon) if you move.
DEFAULT_LAT = 18.5204
DEFAULT_LON = 73.8567

DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "et0_fao_evapotranspiration",
    "uv_index_max",
    "sunrise",
    "sunset",
]
CURRENT_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
]


def fetch_weather(lat: float = DEFAULT_LAT, lon: float = DEFAULT_LON,
                  days: int = 3, tz: str = "Asia/Kolkata") -> dict:
    """Return the raw Open-Meteo forecast payload for the given coordinates."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ",".join(CURRENT_VARS),
        "daily": ",".join(DAILY_VARS),
        "timezone": tz,
        "forecast_days": days,
    }
    url = f"{OPEN_METEO}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def summarise(weather: dict) -> str:
    """One-line human summary of today's conditions."""
    cur = weather["current"]
    daily = weather["daily"]
    today = {k: v[0] for k, v in daily.items() if k != "time"}
    return (
        f"Now {cur['temperature_2m']}°C, {cur['relative_humidity_2m']}% RH, "
        f"rain {cur['precipitation']} mm\n"
        f"Today {today['temperature_2m_min']}-{today['temperature_2m_max']}°C, "
        f"rain {today['precipitation_probability_max']}% "
        f"({today['precipitation_sum']} mm), "
        f"ET0 {today['et0_fao_evapotranspiration']} mm, "
        f"UV {today['uv_index_max']}"
    )


if __name__ == "__main__":
    print(summarise(fetch_weather()))
