#!/usr/bin/env python3
"""Offline self-test: apply sample messages to a COPY of the garden and show the
resulting schedule, care-log and health rows. Never touches your real files.

    python scripts/selftest.py
"""
from __future__ import annotations

import datetime as dt
import importlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SAMPLES = [
    "watered Tulsi and Mint",
    "fertilised Tomato",
    "sprayed neem on Chilli",
    "it rained",
    "note basil leaves curling",
    "watched a movie",  # unknown -> should ask for clarification
]


def main() -> None:
    tmp = Path(tempfile.mkdtemp(prefix="garden-selftest-"))
    shutil.copytree(REPO / "garden", tmp / "garden")
    os.environ["GARDEN_ROOT"] = str(tmp)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import garden_actions as ga

    importlib.reload(ga)  # ensure GARDEN_ROOT is picked up

    day = dt.date(2026, 10, 1)
    for sample in SAMPLES:
        print(f"< {sample}")
        print(f"> {ga.apply(sample, day=day)['reply']}\n")

    print("--- schedule.md (updated rows) ---")
    for line in (tmp / "garden" / "schedule.md").read_text(encoding="utf-8").splitlines():
        if any(line.strip().startswith(f"| {p} ") for p in ("Tulsi", "Tomato", "Chilli")):
            print(line)

    print("\n--- care-log/2026-10-01.md ---")
    print((tmp / "garden" / "care-log" / "2026-10-01.md").read_text(encoding="utf-8"))

    print("--- health.md (tail) ---")
    print("\n".join((tmp / "garden" / "health.md").read_text(encoding="utf-8").splitlines()[-3:]))


if __name__ == "__main__":
    main()
