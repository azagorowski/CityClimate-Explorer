#!/usr/bin/env python3
"""Validate overlay lookups and report local monthly-cache completeness."""
from __future__ import annotations
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import MONTHS  # noqa: E402
from src.locations import load_all_capitals  # noqa: E402
from src.monthly_metrics import (  # noqa: E402
    METRIC_OPTIONS, get_monthly_metric_for_city, load_monthly_metrics_cache,
    normalize_month_key, normalized_metric_key,
)

REQUIRED = ("average_temperature_c", "high_temperature_c", "low_temperature_c", "precipitation_mm",
            "sunshine_hours", "record_high_temperature_c", "record_low_temperature_c")
REPRESENTATIVE = {"Kraków", "Stavanger", "Rovaniemi", "Luleå", "Kyiv", "Tehran", "Puno", "Murmansk", "Bogotá", "Cairo"}


def main() -> int:
    records = load_monthly_metrics_cache()
    cities = load_all_capitals()
    runtime_ids = {city["marker_id"] for city in cities}
    errors: list[str] = []
    for record in records:
        city_id = str(record.get("city_id") or "")
        # Legacy IDs are allowed only when another stable fallback identifies a runtime city.
        if city_id not in runtime_ids and not any(
            get_monthly_metric_for_city(city, "average_temperature_c", "jan", [record])[0] is not None
            for city in cities
        ):
            errors.append(f"unmatched city identity: {city_id}")
        for metric in record.get("metrics", []):
            key = normalized_metric_key(str(metric.get("metric_key") or metric.get("display_label") or ""))
            normalized_months = {normalize_month_key(month) for month in metric.get("monthly_values", {})}
            if key not in METRIC_OPTIONS:
                errors.append(f"{city_id}: unsupported metric {metric.get('metric_key')}")
            if normalized_months != set(MONTHS) or None in normalized_months:
                errors.append(f"{city_id}/{key}: month keys must be Jan-Dec only")
            if key and key.endswith("_temperature_c") and metric.get("unit") != "°C":
                errors.append(f"{city_id}/{key}: temperature must use °C")
    for city in cities:
        if city["name"] in REPRESENTATIVE and get_monthly_metric_for_city(
            city, "average_temperature_c", "May", records
        )[0] is None:
            errors.append(f"representative city cannot render May average temperature: {city['name']}")

    coverage = Counter()
    parsed_without_cache = []
    for city in cities:
        found = []
        for key in REQUIRED:
            if get_monthly_metric_for_city(city, key, "may", records)[0] is not None:
                coverage[key] += 1
                found.append(key)
        if city.get("climate_data") and not found:
            parsed_without_cache.append(f"{city['name']}, {city['country']}")
    print(f"Runtime cities: {len(cities)}; monthly cache records: {len(records)}")
    for key in REQUIRED:
        print(f"  {key}: {coverage[key]}/{len(cities)}")
    if parsed_without_cache:
        errors.append("parsed climate tables without any monthly overlay metric: " + ", ".join(parsed_without_cache[:20]))
    if len(records) / max(len(cities), 1) < 0.01:
        errors.append("monthly metric cache coverage unexpectedly below 1%")
    if errors:
        print("ERRORS:\n" + "\n".join(errors))
        return 1
    print("Monthly metric cache validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
