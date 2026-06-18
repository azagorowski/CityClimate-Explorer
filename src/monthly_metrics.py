"""Normalized, local-only monthly climate metrics used by map labels."""
from __future__ import annotations

import logging
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from collections.abc import Mapping
from typing import Any, Iterable, NamedTuple

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

TABLE_DATA_FIELDS = ("climate_data", "climate_table", "monthly_climate_data", "monthly_metrics")

_COUNTRY_ALIASES = {
    "turkey": "turkiye",
    "turkiye": "turkiye",
    "republic of turkiye": "turkiye",
    "republic of turkey": "turkiye",
    "rsa": "south africa",
    "republic of south africa": "south africa",
    "czech republic": "czechia",
    "czechia": "czechia",
    "united states of america": "united states",
    "usa": "united states",
    "us": "united states",
    "u s a": "united states",
    "uk": "united kingdom",
    "u k": "united kingdom",
    "great britain": "united kingdom",
    "britain": "united kingdom",
}


def _normalized_country_name(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    key = re.sub(r"[^a-z0-9]+", " ", text).strip()
    return _COUNTRY_ALIASES.get(key, key)


def country_identity(city: Mapping[str, Any] | None) -> tuple[str, str]:
    """Return a stable country identity, preferring IDs/codes before names.

    Country-level metric overlays compare these identities so labels follow the
    selected city's country even when records use common aliases such as
    Türkiye/Turkey, Czechia/Czech Republic, USA/United States, or UK/United Kingdom.
    """
    if not city:
        return "", ""
    qid = str(city.get("country_qid") or city.get("country_wikidata_qid") or "").strip()
    if qid:
        return "qid", qid
    for field in ("country_iso_a2", "iso_a2", "country_iso_a3", "iso_a3"):
        code = str(city.get(field) or "").strip().upper()
        if code:
            return "iso", code
    return "name", _normalized_country_name(city.get("country"))


def same_country(left: Mapping[str, Any] | None, right: Mapping[str, Any] | None) -> bool:
    """Return True when two city records describe the same country robustly."""
    left_kind, left_value = country_identity(left)
    right_kind, right_value = country_identity(right)
    if not left_value or not right_value:
        return False
    if left_kind == right_kind:
        return left_value == right_value
    # When only one side has a stable ID/code, fall back to normalized names if
    # both names are present; this keeps mixed legacy/cache records matchable.
    return _normalized_country_name((left or {}).get("country")) == _normalized_country_name(
        (right or {}).get("country")
    )


def get_overlay_target_cities(
    visible_cities: Iterable[dict[str, Any]],
    selected_city: Mapping[str, Any] | None = None,
    filters: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return visible city records eligible for monthly metric labels.

    ``visible_cities`` is expected to already reflect active country, continent,
    climate, record-scope, and marker-toggle filters. When a city is selected,
    labels are scoped to every still-visible marker in the selected city's
    country. With no selected city, the chosen UX is to label all currently
    visible cities so the overlay can be explored before a country is selected.
    The optional ``filters`` argument documents that filtering happens upstream
    and is reserved for future filter-aware diagnostics.
    """
    del filters
    city_list = list(visible_cities)
    if not selected_city:
        return city_list
    return [city for city in city_list if same_country(city, selected_city)]


class MetricValue(NamedTuple):
    """A resolved numeric value plus display and diagnostic metadata."""

    value: float
    unit: str
    source: str


def normalize_month_key(value: Any) -> str | None:
    """Return a Jan-Dec cache key; Annual is deliberately unsupported."""
    return MONTH_ALIASES.get(re.sub(r"[^a-z]", "", str(value or "").casefold()))


def normalized_metric_key(row_name: str, unit: str | None = None) -> str | None:
    """Map UI labels and common/legacy climate-table labels to overlay keys."""
    if row_name in METRIC_OPTIONS:
        return row_name
    text = re.sub(r"[^a-z0-9%°]+", " ", str(row_name or "").casefold()).strip()
    compact = text.replace(" ", "_")
    canonical_aliases = {
        "average_temperature_c": "average_temperature_c",
        "high_temperature_c": "high_temperature_c",
        "low_temperature_c": "low_temperature_c",
        "record_high_temperature_c": "record_high_temperature_c",
        "record_low_temperature_c": "record_low_temperature_c",
        "precipitation_mm": "precipitation_mm",
        "rainfall_mm": "rainfall_mm",
        "snowfall_mm": "snowfall",
        "snowfall_cm": "snowfall",
        "precipitation_days": "precipitation_days",
        "snow_days": "snow_days",
        "sunshine_hours": "sunshine_hours",
        "humidity_percent": "humidity_percent",
    }
    if compact in canonical_aliases:
        return canonical_aliases[compact]
    if "record high" in text:
        return "record_high_temperature_c"
    if "record low" in text:
        return "record_low_temperature_c"
    if "average high" in text or text.startswith("high "):
        return "high_temperature_c"
    if "average low" in text or text.startswith("low "):
        return "low_temperature_c"
    if text in {"average", "avg c", "average c", "average °c", "mean c", "mean °c"} or any(
        term in text for term in ("daily mean", "mean daily temperature", "average temperature", "mean temperature")
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


def city_lookup_keys(city: Mapping[str, Any]) -> dict[str, str]:
    """Return stable and normalized identities shared by runtime and cache records."""
    name = city.get("name") or city.get("city")
    country = city.get("country")
    region = city.get("administrative_region") or city.get("admin_region")
    city_country = str(city.get("normalized_city_country_key") or "").strip() or "|".join(filter(None, (
        normalized_search_key(name), normalized_search_key(country),
    )))
    city_country_region = str(city.get("normalized_city_country_region_key") or "").strip() or "|".join(filter(None, (
        normalized_search_key(name), normalized_search_key(country), normalized_search_key(region),
    )))
    return {
        "city_id": str(city.get("marker_id") or city.get("city_id") or "").strip(),
        "qid": str(city.get("qid") or "").strip(),
        "normalized_city_country_key": city_country,
        "normalized_city_country_region_key": city_country_region,
    }


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
        keys = city_lookup_keys(record)
        if keys["city_id"]:
            by_id[keys["city_id"]] = record
        if keys["qid"]:
            by_qid[keys["qid"]] = record
        if keys["normalized_city_country_key"]:
            by_name_country.setdefault(tuple(keys["normalized_city_country_key"].split("|")), record)
        if keys["normalized_city_country_region_key"]:
            by_name_country_region.setdefault(tuple(keys["normalized_city_country_region_key"].split("|")), record)
    return by_id, by_qid, by_name_country, by_name_country_region


def _find_record(city: dict[str, Any], records: Iterable[dict[str, Any]]) -> tuple[dict[str, Any] | None, str]:
    by_id, by_qid, by_pair, by_region = _record_indexes(records)
    keys = city_lookup_keys(city)
    city_id, qid = keys["city_id"], keys["qid"]
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


def _rows_from_record(record: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not record:
        return []
    for field in TABLE_DATA_FIELDS:
        value = record.get(field)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
        if isinstance(value, dict):
            rows = value.get("rows") or value.get("records")
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def _parsed_fallback(record: Mapping[str, Any], metric_key: str, month: str) -> tuple[float | None, str, str]:
    rows = _rows_from_record(record)
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
        monthly_values = row.get("monthly_values") if isinstance(row.get("monthly_values"), dict) else row
        value = next((v for k, v in monthly_values.items() if normalize_month_key(k) == month), None)
        number = _numeric(value)
        if number is not None:
            unit = "°C" if metric_key.endswith("_temperature_c") else str(row.get("unit") or METRIC_OPTIONS[metric_key][1] or "")
            return number, unit, "parsed climate table"
    return None, "", "metric key missing"


def _table_cache_records(table_cache: Any) -> list[dict[str, Any]]:
    if table_cache is None:
        return []
    if isinstance(table_cache, Mapping):
        records = []
        for key, value in table_cache.items():
            if isinstance(value, dict):
                record = dict(value)
                record.setdefault("city_id", str(key))
            elif isinstance(value, list):
                record = {"city_id": str(key), "climate_data": value}
            else:
                continue
            records.append(record)
        return records
    return [dict(record) for record in table_cache if isinstance(record, dict)]


def resolve_monthly_metric_value(
    city_record: dict[str, Any],
    metric_key: str,
    month: str,
    metrics_cache: list[dict[str, Any]] | None = None,
    table_cache: Any = None,
) -> tuple[MetricValue | None, str]:
    """Resolve all local sources before declaring a visible marker's value missing."""
    key = normalized_metric_key(metric_key)
    normalized_month = normalize_month_key(month)
    if key not in METRIC_OPTIONS:
        return None, "metric unavailable"
    if normalized_month is None:
        return None, "month unavailable"

    cache_record, cache_match = _find_record(
        city_record, metrics_cache if metrics_cache is not None else load_monthly_metrics_cache()
    )
    best_reason = "no city key match"
    if cache_record:
        value, unit, reason = _metric_value(cache_record, key, normalized_month)
        if value is not None:
            return MetricValue(value, unit, f"monthly metrics cache ({cache_match})"), ""
        best_reason = {
            "metric key missing": "metric unavailable",
            "month key missing": "month unavailable",
            "value non-numeric": "non-numeric value",
        }.get(reason, reason)

    table_record, table_match = _find_record(city_record, _table_cache_records(table_cache))
    if table_record:
        value, unit, reason = _parsed_fallback(table_record, key, normalized_month)
        if value is not None:
            return MetricValue(value, unit, f"parsed climate table cache ({table_match})"), ""
        if best_reason == "no city key match":
            best_reason = "metric unavailable" if reason == "metric key missing" else reason

    value, unit, reason = _parsed_fallback(city_record, key, normalized_month)
    if value is not None:
        return MetricValue(value, unit, "embedded city climate data"), ""
    if best_reason == "no city key match" and _rows_from_record(city_record):
        best_reason = "metric unavailable" if reason == "metric key missing" else reason
    return None, best_reason


def get_monthly_metric_for_city(
    city_record: dict[str, Any], metric_key: str, month: str,
    cache: list[dict[str, Any]] | None = None,
    table_cache: Any = None,
) -> tuple[float | None, str, str]:
    """Compatibility wrapper around the central local metric resolver."""
    resolved, reason = resolve_monthly_metric_value(city_record, metric_key, month, cache, table_cache)
    return (resolved.value, resolved.unit, resolved.source) if resolved else (None, "", reason)


@dataclass(frozen=True)
class OverlayDiagnostics:
    visible_markers: int
    labels_rendered: int
    missing_reasons: dict[str, int]


def overlay_values(
    cities: Iterable[dict[str, Any]] | set[str], metric_key: str, month: str,
    cache: list[dict[str, Any]] | dict[str, list[dict[str, Any]]] | None = None,
    table_cache: Any = None,
) -> dict[str, tuple[float, str]]:
    """Return values for visible city records (legacy ID sets remain supported)."""
    if isinstance(cache, dict):
        records = [{"city_id": city_id, "metrics": metrics} for city_id, metrics in cache.items()]
    else:
        records = cache
    city_records = [{"marker_id": city_id} for city_id in cities] if isinstance(cities, set) else list(cities)
    result: dict[str, tuple[float, str]] = {}
    for city in city_records:
        value, unit, _reason = get_monthly_metric_for_city(city, metric_key, month, records, table_cache)
        city_id = str(city.get("marker_id") or city.get("city_id") or "")
        if city_id and value is not None:
            result[city_id] = (value, unit)
    return result


def overlay_diagnostics(cities: Iterable[dict[str, Any]], metric_key: str, month: str,
                        cache: list[dict[str, Any]] | None = None,
                        table_cache: Any = None) -> OverlayDiagnostics:
    reasons: Counter[str] = Counter()
    city_list = list(cities)
    rendered = 0
    for city in city_list:
        value, _unit, reason = get_monthly_metric_for_city(city, metric_key, month, cache, table_cache)
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
