#!/usr/bin/env python3
"""Validate/re-serialize the deterministic top-90 country-by-area reference.

Area ranks and values are reviewed from the cited source before changing the
committed seed; this script performs no runtime or build-time network access.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/preloaded/top_90_countries_by_area.json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=SOURCE)
    args = parser.parse_args()
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    if len(records) != 90 or [row.get("area_rank") for row in records] != list(range(1, 91)):
        raise ValueError("top-90 reference must contain exactly ranks 1 through 90")
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote deterministic {len(records)}-country area reference to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
