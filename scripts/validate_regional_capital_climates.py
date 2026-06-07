#!/usr/bin/env python3
"""Audit all locally bundled regional-capital climate classifications."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.climate_parser import koppen_climate_group  # noqa: E402
from src.locations import load_polar_border_capitals, load_top15_regional_capitals  # noqa: E402
from src.map_view import CLIMATE_COLORS  # noqa: E402

DEFAULT_REPORT = ROOT / "data" / "preloaded" / "regional_capital_climate_audit.json"


def audit_records() -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for record in load_top15_regional_capitals() + load_polar_border_capitals():
        label = f"{record.get('name')}, {record.get('country')}"
        primary = record.get("primary_koppen_code")
        secondary = record.get("secondary_koppen_codes") or []
        group = record.get("climate_group")
        classification = record.get("climate_classification_label") or record.get("climate_classification")
        def add(code: str, message: str, severity: str = "warning") -> None:
            findings.append({"record": label, "scope": str(record.get("record_scope")), "severity": severity, "code": code, "message": message})
        if not classification or str(classification).casefold() == "unknown":
            add("missing_classification", "No usable climate classification is bundled.", "error")
        if group not in CLIMATE_COLORS or group == "Unknown":
            add("missing_broad_group", "No valid broad climate group is bundled.", "error")
        expected = koppen_climate_group(str(primary)) if primary else None
        if expected and expected != group:
            add("primary_group_mismatch", f"Primary {primary} maps to {expected}, not {group}.", "error")
        if primary and primary in secondary:
            add("primary_repeated_as_secondary", f"Primary code {primary} is also listed as secondary.", "error")
        if not primary:
            add("primary_code_not_detected", "Broad reviewed classification has no primary Köppen code; review on next developer refresh.", "review")
        if secondary and not primary:
            add("secondary_without_primary", "Secondary codes exist without a primary code.", "error")
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--strict", action="store_true", help="Fail on review findings as well as errors.")
    args = parser.parse_args()
    findings = audit_records()
    args.report.write_text(json.dumps({"records_audited": len(load_top15_regional_capitals()) + len(load_polar_border_capitals()), "findings": findings}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    errors = [item for item in findings if item["severity"] == "error"]
    reviews = [item for item in findings if item["severity"] == "review"]
    print(f"Audited regional-capital climates: {len(errors)} errors, {len(reviews)} review items; report: {args.report}")
    for item in (errors + reviews)[:25]:
        print(f"- [{item['severity']}] {item['record']}: {item['message']}")
    return 1 if errors or (args.strict and reviews) else 0


if __name__ == "__main__":
    raise SystemExit(main())
