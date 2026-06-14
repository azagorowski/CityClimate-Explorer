"""Normalized, local-only monthly climate metrics used by map labels."""
from __future__ import annotations

import re
from typing import Any

from .config import MONTHLY_CLIMATE_METRICS_CACHE, MONTHS
from .storage import read_json

METRIC_OPTIONS = {
    "average_temperature_c": ("Average temperature", "°C"),
    "high_temperature_c": ("High temperature", "°C"),
    "low_temperature_c": ("Low temperature", "°C"),
    "record_high_temperature_c": ("Record high temperature", "°C"),
    "record_low_temperature_c": ("Record low temperature", "°C"),
    "precipitation_mm": ("Precipitation", "mm"),
    "rainfall_mm": ("Rainfall", "mm"),
    "snowfall": ("Snowfall", None),
    "precipitation_days": ("Precipitation days", "days"),
    "snow_days": ("Snow days", "days"),
    "sunshine_hours": ("Sunshine hours / Sun", "hours"),
    "humidity_percent": ("Humidity", "%"),
}


def normalized_metric_key(row_name: str, unit: str | None = None) -> str | None:
    """Map common Wikipedia climate-table row labels to overlay keys."""
    text = re.sub(r"[^a-z0-9%°]+", " ", row_name.casefold()).strip()
    if "record high" in text:
        return "record_high_temperature_c"
    if "record low" in text:
        return "record_low_temperature_c"
    if "average high" in text or text.startswith("high "):
        return "high_temperature_c"
    if "average low" in text or text.startswith("low "):
        return "low_temperature_c"
    if any(term in text for term in ("daily mean", "average temperature", "average c", "mean temperature")):
        return "average_temperature_c"
    if "precipitation days" in text:
        return "precipitation_days"
    if "snow days" in text or "snowy days" in text:
        return "snow_days"
    if "precipitation" in text:
        return "precipitation_mm"
    if "rainfall" in text:
        return "rainfall_mm"
    if "snowfall" in text:
        return "snowfall"
    if "sunshine" in text or text == "sun":
        return "sunshine_hours"
    if "humidity" in text:
        return "humidity_percent"
    return None


def load_monthly_metrics_cache() -> dict[str, list[dict[str, Any]]]:
    """Return stable-city-ID indexed metrics without network access."""
    payload = read_json(MONTHLY_CLIMATE_METRICS_CACHE, default={})
    records = payload.get("records", []) if isinstance(payload, dict) else []
    return {
        str(record["city_id"]): record.get("metrics", [])
        for record in records if isinstance(record, dict) and record.get("city_id")
    }


def overlay_values(
    city_ids: set[str], metric_key: str, month: str,
    cache: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, tuple[float | str, str]]:
    """Return display-ready values for visible cities only."""
    if month not in MONTHS or metric_key not in METRIC_OPTIONS:
        return {}
    result: dict[str, tuple[float | str, str]] = {}
    for city_id, metrics in (cache or load_monthly_metrics_cache()).items():
        if city_id not in city_ids:
            continue
        metric = next((item for item in metrics if item.get("metric_key") == metric_key), None)
        value = metric.get("monthly_values", {}).get(month) if metric else None
        if value is not None and str(value).casefold() != "none":
            result[city_id] = (value, str(metric.get("unit") or METRIC_OPTIONS[metric_key][1] or ""))
    return result


def format_overlay_value(value: float | str, unit: str) -> str:
    """Format compact labels while never exposing Python null text."""
    if isinstance(value, float):
        value_text = f"{value:.1f}".rstrip("0").rstrip(".")
    else:
        value_text = str(value)
    return f"{value_text} {unit}".strip()
