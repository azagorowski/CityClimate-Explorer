"""Normalize selected-city climate rows to Celsius for annual charts."""
from __future__ import annotations

import re
from typing import Any

from .config import MONTH_LABELS, MONTHS
from .normalize import clean_text, parse_number

UNAVAILABLE_MESSAGE = "Annual temperature chart unavailable because monthly temperature data was not found."

_MEAN_PATTERNS = (
    re.compile(r"\bdaily mean\b", re.I),
    re.compile(r"\bmean daily temperature\b", re.I),
    re.compile(r"\baverage (?:daily )?temperature\b", re.I),
    re.compile(r"\bmean temperature\b", re.I),
)
_HIGH_PATTERNS = (
    re.compile(r"\baverage (?:daily )?(?:high|maximum)\b", re.I),
    re.compile(r"\bmean maximum\b", re.I),
)
_LOW_PATTERNS = (
    re.compile(r"\baverage (?:daily )?(?:low|minimum)\b", re.I),
    re.compile(r"\bmean minimum\b", re.I),
)
_EXCLUDED_PATTERNS = re.compile(
    r"\b(record|precipitation|rainfall|snow|sunshine|humidity|dew point|wind|heat index)\b", re.I,
)


def _metric_kind(metric_name: Any) -> str | None:
    name = clean_text(metric_name).casefold()
    if not name or _EXCLUDED_PATTERNS.search(name):
        return None
    if any(pattern.search(name) for pattern in _MEAN_PATTERNS):
        return "mean"
    if any(pattern.search(name) for pattern in _HIGH_PATTERNS):
        return "high"
    if any(pattern.search(name) for pattern in _LOW_PATTERNS):
        return "low"
    return None


def _temperature_unit(row: dict[str, Any]) -> str | None:
    text = f"{row.get('unit') or ''} {row.get('metric_name') or ''}"
    has_celsius = bool(re.search(r"°\s*C|\bCelsius\b", text, re.I))
    has_fahrenheit = bool(re.search(r"°\s*F|\bFahrenheit\b", text, re.I))
    # Some Wikipedia labels contain both display units. The parsed row's unit
    # is authoritative; otherwise prefer Celsius as required by the chart.
    unit_text = clean_text(row.get("unit"))
    if re.search(r"°\s*C|\bCelsius\b", unit_text, re.I):
        return "°C"
    if re.search(r"°\s*F|\bFahrenheit\b", unit_text, re.I):
        return "°F"
    if has_celsius:
        return "°C"
    if has_fahrenheit:
        return "°F"
    return None


def _monthly_values(row: dict[str, Any]) -> list[float | None]:
    """Read Jan-Dec only; the annual summary is deliberately ignored."""
    values: list[float | None] = []
    for month in MONTHS:
        value = row.get(month)
        parsed = value if isinstance(value, int | float) else parse_number(value)
        values.append(float(parsed) if isinstance(parsed, int | float) else None)
    return values


def _to_celsius(values: list[float | None], unit: str) -> list[float | None]:
    if unit == "°C":
        return values
    return [round((value - 32) * 5 / 9, 1) if value is not None else None for value in values]


def normalize_monthly_temperatures_to_celsius(
    climate_table: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Return the best real Jan-Dec monthly mean series, always in Celsius.

    Selection order is direct Celsius mean, mean of Celsius highs/lows,
    Fahrenheit mean converted to Celsius, then converted Fahrenheit highs/lows.
    At least six valid months are required; missing months are never guessed.
    """
    candidates: dict[tuple[str, str], tuple[dict[str, Any], list[float | None]]] = {}
    for row in climate_table or []:
        if not isinstance(row, dict):
            continue
        kind = _metric_kind(row.get("metric_name"))
        unit = _temperature_unit(row)
        if kind and unit:
            candidates.setdefault((kind, unit), (row, _monthly_values(row)))

    for unit in ("°C", "°F"):
        direct = candidates.get(("mean", unit))
        if direct and sum(value is not None for value in direct[1]) >= 6:
            values = _to_celsius(direct[1], unit)
            return {
                "months": list(MONTH_LABELS),
                "monthly_temperature_mean_c": values,
                "monthly_temperature_mean": values,
                "temperature_unit": "°C",
                "source_row_used": clean_text(direct[0].get("metric_name")),
                "source_rows_used": [clean_text(direct[0].get("metric_name"))],
                "conversion_applied": unit == "°F",
                "method": "reported monthly mean" if unit == "°C" else "reported monthly mean converted from °F",
            }

        high = candidates.get(("high", unit))
        low = candidates.get(("low", unit))
        if high and low:
            high_c = _to_celsius(high[1], unit)
            low_c = _to_celsius(low[1], unit)
            means = [
                round((high_value + low_value) / 2, 1)
                if high_value is not None and low_value is not None else None
                for high_value, low_value in zip(high_c, low_c, strict=True)
            ]
            if sum(value is not None for value in means) >= 6:
                source_rows = [clean_text(high[0].get("metric_name")), clean_text(low[0].get("metric_name"))]
                return {
                    "months": list(MONTH_LABELS),
                    "monthly_temperature_mean_c": means,
                    "monthly_temperature_mean": means,
                    "temperature_unit": "°C",
                    "source_row_used": " + ".join(source_rows),
                    "source_rows_used": source_rows,
                    "conversion_applied": unit == "°F",
                    "method": "average of reported high and low" if unit == "°C" else "average of high and low converted from °F",
                }
    return None


def normalize_monthly_temperature(climate_data: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Backward-compatible alias for Celsius-only normalization."""
    return normalize_monthly_temperatures_to_celsius(climate_data)


def temperature_chart_rows(climate_data: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return ordered Celsius chart rows, or no rows when no real series exists."""
    normalized = normalize_monthly_temperatures_to_celsius(climate_data)
    if not normalized:
        return []
    return [
        {"Month": month, "Month order": index, "Temperature (°C)": value, "Unit": "°C"}
        for index, (month, value) in enumerate(
            zip(normalized["months"], normalized["monthly_temperature_mean_c"], strict=True), start=1
        )
        if value is not None
    ]
