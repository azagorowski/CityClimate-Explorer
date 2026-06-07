#!/usr/bin/env python3
"""Validate bundled Wikimedia provenance and license metadata."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRELOADED = ROOT / "data" / "preloaded" / "country_capitals.json"
CLIMATE = ROOT / "data" / "capital_climate_cache.json"
WIKIPEDIA_PRIORITIES = {"english_primary", "native_fallback"}


def _records(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["records"] if isinstance(payload, dict) else payload


def validate_provenance() -> list[str]:
    errors: list[str] = []
    for record in _records(PRELOADED):
        label = f"{record.get('name')}, {record.get('country')}"
        provenance = record.get("provenance") or {}
        for field in ("record_source_name", "record_source_url", "record_source_page_title", "record_license", "wikidata_license"):
            if not provenance.get(field):
                errors.append(f"{label}: missing provenance.{field}")
    for path in (CLIMATE,):
        for record in _records(path):
            metadata = record
            if metadata.get("source_priority") in WIKIPEDIA_PRIORITIES:
                for field in ("source_url", "source_page_title", "source_language", "license", "license_url", "contributors_url"):
                    if not metadata.get(field):
                        errors.append(f"{path.name}:{record.get('name')}: missing Wikipedia {field}")
    return errors


def main() -> int:
    errors = validate_provenance()
    if errors:
        print("Provenance validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("Bundled Wikimedia provenance validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
