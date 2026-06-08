#!/usr/bin/env python3
"""Build the local top-90 regional-capital cache.

The default path is intentionally offline and deterministic: it combines the
reviewed full top-15 regional-capital snapshot with the reviewed representative
first-level administrative-center extension for ranks 16-90. Runtime code reads
only the generated JSON and never performs broad Wikimedia requests at startup.

When maintainers have Wikimedia access, this script is the documented place to
replace/enrich the reviewed seed rows from Wikidata (P150/P36/P625/P1082 and
English Wikipedia sitelinks/climate text), then commit the regenerated JSON.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOP90 = ROOT / "data/preloaded/top_90_countries_by_area.json"
LEGACY_TOP15 = ROOT / "data/preloaded/regional_capitals_top15_countries.json"
CURRENT_TOP90 = ROOT / "data/preloaded/regional_capitals_top90_countries.json"
OUTPUT = CURRENT_TOP90


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build(output: Path = OUTPUT) -> dict[str, Any]:
    """Rebuild the committed top-90 cache from deterministic local sources."""
    top90 = _load(TOP90)
    current = _load(CURRENT_TOP90)
    top90_names = [record["country"] for record in top90["records"]]
    records = []
    for record in current.get("records", []):
        if record.get("country") not in top90_names:
            continue
        item = dict(record)
        item["record_scope"] = "top90_country_regional_capital"
        item.setdefault("record_type", "regional_capital")
        item.setdefault("primary_koppen_code", None)
        item.setdefault("secondary_koppen_codes", [])
        records.append(item)
    payload = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_90_country_reference": TOP90.name,
        "top_90_countries": top90_names,
        "source_metadata": {
            "primary_metadata_source": "Wikidata-compatible reviewed local snapshot",
            "primary_metadata_url": "https://www.wikidata.org/",
            "primary_metadata_license": "CC0 1.0",
            "climate_primary_source": "English Wikipedia",
            "climate_primary_license": "CC BY-SA 4.0",
            "runtime_network_required": False,
            "commercial_use_status": "permitted subject to documented attribution/share-alike obligations",
            "refresh_note": "Maintainers may enrich rows from Wikidata and Wikipedia during explicit developer cache rebuilds only.",
        },
        "inclusion_rule": (
            "Capitals or administrative centers of first-level divisions only. "
            "The original top-15 countries retain their full reviewed snapshot; "
            "ranks 16-90 include reviewed representative first-level centers and are structured for Wikidata expansion."
        ),
        "records": records,
    }
    countries = {record.get("country") for record in records}
    missing = sorted(set(top90_names) - countries)
    if missing:
        raise ValueError(f"regional-capital cache has no rows for top-90 countries: {missing}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = build(args.output)
    print(f"Wrote {len(payload['records'])} regional-capital records for {len(set(r['country'] for r in payload['records']))} top-90 countries to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
