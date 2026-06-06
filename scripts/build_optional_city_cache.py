#!/usr/bin/env python3
"""Developer-only refresh of one country's local optional-city cache."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import OPTIONAL_CITY_CACHE  # noqa: E402
from src.storage import read_json  # noqa: E402
from src.wikidata import fetch_cities  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--continent", required=True)
    parser.add_argument("--country", required=True)
    parser.add_argument("--country-qid")
    parser.add_argument("--min-population", type=int, default=200_000)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    fetched = fetch_cities(limit=10, min_population=args.min_population, force_refresh=args.force, continent=args.continent, country=args.country, country_qid=args.country_qid)
    payload = read_json(OPTIONAL_CITY_CACHE, default={})
    records = payload.get("records", []) if isinstance(payload, dict) else []
    records = [record for record in records if not (record.get("continent") == args.continent and record.get("country") == args.country)]
    records.extend(fetched[:10])
    # Keep per-record Wikidata/Wikipedia provenance intact for any redistribution.
    OPTIONAL_CITY_CACHE.write_text(json.dumps({"schema_version": 2, "generated_at": datetime.now(timezone.utc).isoformat(), "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Stored {min(10, len(fetched))} cities for {args.country} in {OPTIONAL_CITY_CACHE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
