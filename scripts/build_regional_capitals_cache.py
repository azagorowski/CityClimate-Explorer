#!/usr/bin/env python3
"""Developer-only builder for the committed top-90 regional-capital cache.

Normal application startup never runs this script and never discovers regional
capitals through Wikimedia. Maintainers may refresh a reviewed JSON snapshot
produced from Wikidata first-level-division/capital metadata and Wikipedia
climate review, then validate and commit the resulting local file.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOP90 = ROOT / "data/preloaded/top_90_countries_by_area.json"
CURRENT = ROOT / "data/preloaded/regional_capitals_top90_countries.json"
OUTPUT = CURRENT


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build(output: Path = OUTPUT, source: Path = CURRENT) -> dict[str, Any]:
    """Normalize a reviewed developer snapshot into the deterministic cache."""
    reference = _load(TOP90)["records"]
    source_payload = _load(source)
    names = [record["country"] for record in reference]
    records: list[dict[str, Any]] = []
    for record in source_payload.get("records", []):
        if record.get("country") not in names:
            continue
        item = dict(record)
        item["record_scope"] = "top90_country_regional_capital"
        item.setdefault("record_type", "regional_capital")
        item.setdefault("primary_koppen_code", None)
        item.setdefault("secondary_koppen_codes", [])
        records.append(item)
    counts = Counter(record.get("country") for record in records)
    prior_status = {row.get("country"): row for row in source_payload.get("country_processing_status", [])}
    statuses = []
    for country in reference:
        previous = prior_status.get(country["country"], {})
        count = counts[country["country"]]
        status = {
            "area_rank": country["area_rank"], "country": country["country"],
            "country_qid": country.get("country_qid"),
            "status": previous.get("status") or ("complete" if count else "incomplete"),
            "first_level_divisions_exist": previous.get("first_level_divisions_exist", bool(count)),
            "regional_capitals_count": count,
            "coverage_reason": previous.get("coverage_reason") or "Reviewed developer snapshot.",
            "missing_coordinates_count": sum(1 for row in records if row.get("country") == country["country"] and (row.get("latitude") is None or row.get("longitude") is None)),
            "missing_climate_count": sum(1 for row in records if row.get("country") == country["country"] and not row.get("climate_classification") and not row.get("climate_extraction_status")),
        }
        statuses.append(status)
    payload = {
        "schema_version": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top_90_country_reference": TOP90.name,
        "top_90_countries": 90,
        "country_processing_status": statuses,
        "source_metadata": {
            "primary_metadata_source": "Wikidata reviewed developer snapshot",
            "primary_metadata_url": "https://www.wikidata.org/", "primary_metadata_license": "CC0 1.0",
            "climate_primary_source": "English Wikipedia", "climate_primary_license": "CC BY-SA 4.0",
            "climate_fallback_order": ["native-language Wikipedia", "Wikidata climate classification"],
            "runtime_network_required": False,
            "commercial_use_status": "permitted subject to documented attribution/share-alike obligations",
            "developer_only": True,
        },
        "inclusion_rule": "Reviewed capitals or administrative centers of first-level divisions for all top-90 countries.",
        "records": records,
    }
    missing = sorted(set(names) - set(counts))
    undocumented = [row["country"] for row in statuses if row["country"] in missing and not row.get("coverage_reason")]
    if undocumented:
        raise ValueError(f"countries without records or documented reasons: {undocumented}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=CURRENT, help="Reviewed developer snapshot; may be produced with approved Wikimedia sources.")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = build(args.output, args.source)
    print(f"Wrote {len(payload['records'])} records and {len(payload['country_processing_status'])} country statuses to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
