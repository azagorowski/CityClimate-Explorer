"""Normalized, local-only monthly climate metrics used by map labels."""
from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable

from .config import MONTHLY_CLIMATE_METRICS_CACHE, MONTHS
from .normalize import normalized_search_key
from .storage import read_json
from .temperature import normalize_monthly_temperature

LOGGER = logging.getLogger(__name__)
MONTH_ALIASES = {name: MONTHS[index] for index, name in enumerate((
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
))}
MONTH_ALIASES.update({month: month for month in MONTHS})

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
    "sunshine_hours": ("Sunshine hours / Sun", "h"),
    "humidity_percent": ("Humidity", "%"),
}


def normalize_month_key(value: Any) -> str | None:
    """Return a Jan-Dec cache key; Annual is deliberately unsupported."""
    return MONTH_ALIASES.get(re.sub(r"[^a-z]", "", str(value or "").casefold()))


def normalized_metric_key(row_name: str, unit: str | None = None) -> str | None:
    """Map UI labels and common/legacy climate-table labels to overlay keys."""
    if row_name in METRIC_OPTIONS:
        return row_name
    text = re.sub(r"[^a-z0-9%°]+", " ", str(row_name or "").casefold()).strip()
    if "record high" in text:
        return "record_high_temperature_c"
    if "record low" in text:
        return "record_low_temperature_c"
    if "average high" in text or text.startswith("high "):
        return "high_temperature_c"
    if "average low" in text or text.startswith("low "):
        return "low_temperature_c"
    if text in {"average c", "average °c", "mean c", "mean °c"} or any(
        term in text for term in ("daily mean", "average temperature", "mean temperature")
    ):
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


def _identity(city: dict[str, Any], include_region: bool) -> tuple[str, ...]:
    values = [normalized_search_key(city.get("name") or city.get("city")), normalized_search_key(city.get("country"))]
    if include_region:
        values.append(normalized_search_key(city.get("administrative_region")))
    return tuple(values)


def load_monthly_metrics_cache() -> list[dict[str, Any]]:
    """Return complete cache records without network access."""
    payload = read_json(MONTHLY_CLIMATE_METRICS_CACHE, default={})
    records = payload.get("records", []) if isinstance(payload, dict) else []
    return [dict(record) for record in records if isinstance(record, dict)]


def _numeric(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _record_indexes(records: Iterable[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], ...]:
    by_id: dict[str, dict[str, Any]] = {}
    by_qid: dict[str, dict[str, Any]] = {}
    by_name_country: dict[tuple[str, ...], dict[str, Any]] = {}
    by_name_country_region: dict[tuple[str, ...], dict[str, Any]] = {}
    for record in records:
        if record.get("city_id"):
            by_id[str(record["city_id"])] = record
        if record.get("qid"):
            by_qid[str(record["qid"])] = record
        by_name_country.setdefault(_identity(record, False), record)
        by_name_country_region.setdefault(_identity(record, True), record)
    return by_id, by_qid, by_name_country, by_name_country_region


def _find_record(city: dict[str, Any], records: Iterable[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    by_id, by_qid, by_pair, by_region = _record_indexes(records)
    city_id = str(city.get("marker_id") or city.get("city_id") or "")
    qid = str(city.get("qid") or "")
    if city_id and city_id in by_id:
        return by_id[city_id], "city_id"
    if qid and qid in by_qid:
        return by_qid[qid], "qid"
    region_key = _identity(city, True)
    if all(region_key) and region_key in by_region:
        return by_region[region_key], "name_country_region"
    pair_key = _identity(city, False)
    if all(pair_key) and pair_key in by_pair:
        return by_pair[pair_key], "name_country"
    return None, "no city ID, QID, or normalized key match"


def _metric_value(record: dict[str, Any], metric_key: str, month: str) -> tuple[float | None, str, str]:
    normalized_requested = normalized_metric_key(metric_key)
    metrics = record.get("metrics", [])
    metric = next((item for item in metrics if normalized_metric_key(
        str(item.get("metric_key") or item.get("display_label") or item.get("source_row_name") or ""), item.get("unit")
    ) == normalized_requested), None)
    if not metric:
        return None, "", "metric key missing"
    values = metric.get("monthly_values", {})
    normalized_values = {normalize_month_key(key): value for key, value in values.items() if normalize_month_key(key)}
    if month not in normalized_values:
        return None, "", "month key missing"
    value = _numeric(normalized_values[month])
    if value is None:
        return None, "", "value non-numeric"
    unit = "°C" if normalized_requested and normalized_requested.endswith("_temperature_c") else str(
        metric.get("unit") or METRIC_OPTIONS[normalized_requested][1] or ""
    )
    return value, unit, "cache"


def _parsed_fallback(city: dict[str, Any], metric_key: str, month: str) -> tuple[float | None, str, str]:
    rows = city.get("climate_data") or []
    if not rows:
        return None, "", "metric key missing"
    if metric_key == "average_temperature_c":
        normalized = normalize_monthly_temperature(rows)
        if normalized:
            value = _numeric(normalized["monthly_temperature_mean_c"][MONTHS.index(month)])
            if value is not None:
                return value, "°C", "parsed climate table"
    for row in rows:
        key = normalized_metric_key(str(row.get("metric_name") or row.get("Metric") or ""), row.get("unit"))
        if key != metric_key:
            continue
        value = next((v for k, v in row.items() if normalize_month_key(k) == month), None)
        number = _numeric(value)
        if number is not None:
            unit = "°C" if metric_key.endswith("_temperature_c") else str(row.get("unit") or METRIC_OPTIONS[metric_key][1] or "")
            return number, unit, "parsed climate table"
    return None, "", "metric key missing"


def get_monthly_metric_for_city(
    city_record: dict[str, Any], metric_key: str, month: str,
    cache: list[dict[str, Any]] | None = None,
) -> tuple[float | None, str, str]:
    """Find a local metric using stable ID, QID, normalized keys, then parsed rows."""
    key = normalized_metric_key(metric_key)
    normalized_month = normalize_month_key(month)
    if key not in METRIC_OPTIONS or normalized_month is None:
        return None, "", "metric key missing" if key not in METRIC_OPTIONS else "month key missing"
    record, match = _find_record(city_record, cache if cache is not None else load_monthly_metrics_cache())
    if record:
        value, unit, reason = _metric_value(record, key, normalized_month)
        if value is not None:
            return value, unit, match
        fallback = _parsed_fallback(city_record, key, normalized_month)
        return fallback if fallback[0] is not None else (None, "", reason)
    fallback = _parsed_fallback(city_record, key, normalized_month)
    return fallback if fallback[0] is not None else (None, "", match)


@dataclass(frozen=True)
class OverlayDiagnostics:
    visible_markers: int
    labels_rendered: int
    missing_reasons: dict[str, int]


def overlay_values(
    cities: Iterable[dict[str, Any]] | set[str], metric_key: str, month: str,
    cache: list[dict[str, Any]] | dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, tuple[float, str]]:
    """Return values for visible city records (legacy ID sets remain supported)."""
    if isinstance(cache, dict):
        records = [{"city_id": city_id, "metrics": metrics} for city_id, metrics in cache.items()]
    else:
        records = cache
    city_records = [{"marker_id": city_id} for city_id in cities] if isinstance(cities, set) else list(cities)
    result: dict[str, tuple[float, str]] = {}
    for city in city_records:
        value, unit, _reason = get_monthly_metric_for_city(city, metric_key, month, records)
        city_id = str(city.get("marker_id") or city.get("city_id") or "")
        if city_id and value is not None:
            result[city_id] = (value, unit)
    return result


def overlay_diagnostics(cities: Iterable[dict[str, Any]], metric_key: str, month: str,
                        cache: list[dict[str, Any]] | None = None) -> OverlayDiagnostics:
    reasons: Counter[str] = Counter()
    city_list = list(cities)
    rendered = 0
    for city in city_list:
        value, _unit, reason = get_monthly_metric_for_city(city, metric_key, month, cache)
        if value is None:
            reasons[reason] += 1
        else:
            rendered += 1
    diagnostic = OverlayDiagnostics(len(city_list), rendered, dict(reasons.most_common()))
    LOGGER.debug("Monthly overlay: visible=%d metric=%s month=%s labels=%d missing=%d reasons=%s",
                 diagnostic.visible_markers, metric_key, normalize_month_key(month), rendered,
                 diagnostic.visible_markers - rendered, diagnostic.missing_reasons)
    return diagnostic


def format_overlay_value(value: float | str, unit: str) -> str:
    """Format compact labels while suppressing null and non-finite values."""
    number = _numeric(value)
    if number is None:
        return ""
    rounded = round(number, 1)
    text = f"{rounded:.1f}" if not rounded.is_integer() else str(int(rounded))
    normalized_unit = "h" if unit.casefold() in {"hour", "hours"} else unit
    return f"{text}{normalized_unit}" if normalized_unit == "%" else f"{text} {normalized_unit}".strip()
