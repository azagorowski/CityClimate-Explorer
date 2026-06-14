#!/usr/bin/env python3
"""Validate the local monthly map-overlay cache."""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.config import MONTHS  # noqa: E402
from src.locations import load_all_capitals  # noqa: E402
from src.monthly_metrics import METRIC_OPTIONS, load_monthly_metrics_cache, overlay_values  # noqa: E402


def main() -> int:
    cache = load_monthly_metrics_cache()
    runtime_ids = {city["marker_id"] for city in load_all_capitals()}
    errors = []
    for city_id, metrics in cache.items():
        if city_id not in runtime_ids:
            errors.append(f"unknown city ID: {city_id}")
        for metric in metrics:
            key = metric.get("metric_key")
            values = metric.get("monthly_values", {})
            if key not in METRIC_OPTIONS:
                errors.append(f"{city_id}: unsupported metric {key}")
            if set(values) != set(MONTHS) or "annual" in values:
                errors.append(f"{city_id}/{key}: month keys must be Jan-Dec only")
            if key and key.endswith("_temperature_c") and metric.get("unit") != "°C":
                errors.append(f"{city_id}/{key}: temperature must use °C")
            if key in {"precipitation_mm", "rainfall_mm"} and metric.get("unit") != "mm":
                errors.append(f"{city_id}/{key}: precipitation must use mm")
    representative = {"Kraków", "Stavanger", "Murmansk", "Puno", "Bogotá", "Cairo", "Tripoli", "Kyiv", "Tehran"}
    cities = {city["name"]: city["marker_id"] for city in load_all_capitals()}
    for name in representative:
        city_id = cities.get(name)
        if not city_id or not overlay_values({city_id}, "average_temperature_c", "jan", cache):
            errors.append(f"representative city cannot render January average temperature: {name}")
    if errors:
        print("\n".join(errors))
        return 1
    print(f"Monthly metric cache validation passed: {len(cache)} cities")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
