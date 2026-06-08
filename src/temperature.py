"""Normalize selected-city climate rows for annual temperature charts."""
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


def _metric_kind(metric_name: Any) -> str | None:
    name = clean_text(metric_name).casefold()
    if any(pattern.search(name) for pattern in _MEAN_PATTERNS):
        return "mean"
    if any(pattern.search(name) for pattern in _HIGH_PATTERNS):
        return "high"
    if any(pattern.search(name) for pattern in _LOW_PATTERNS):
        return "low"
    return None


def _temperature_unit(row: dict[str, Any]) -> str | None:
    text = f"{row.get('unit') or ''} {row.get('metric_name') or ''}"
    if re.search(r"°\s*C|\bCelsius\b", text, re.I):
        return "°C"
    if re.search(r"°\s*F|\bFahrenheit\b", text, re.I):
        return "°F"
    return None


def _monthly_values(row: dict[str, Any]) -> list[float | None]:
    values: list[float | None] = []
    for month in MONTHS:
        value = row.get(month)
        parsed = value if isinstance(value, int | float) else parse_number(value)
        values.append(float(parsed) if isinstance(parsed, int | float) else None)
    return values


def normalize_monthly_temperature(climate_data: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    """Return a reusable Jan-Dec temperature series without using annual values.

    Celsius rows are preferred. A direct mean row wins; otherwise a mean is
    calculated only for months where both average-high and average-low exist.
    """
    candidates: dict[tuple[str, str], tuple[dict[str, Any], list[float | None]]] = {}
    for row in climate_data or []:
        if not isinstance(row, dict):
            continue
        kind = _metric_kind(row.get("metric_name"))
        unit = _temperature_unit(row)
        if kind and unit:
            candidates.setdefault((kind, unit), (row, _monthly_values(row)))

    for unit in ("°C", "°F"):
        direct = candidates.get(("mean", unit))
        if direct and sum(value is not None for value in direct[1]) >= 6:
            return {
                "monthly_temperature_mean": direct[1],
                "monthly_average_high": candidates.get(("high", unit), ({}, [None] * 12))[1],
                "monthly_average_low": candidates.get(("low", unit), ({}, [None] * 12))[1],
                "temperature_unit": unit,
                "method": "reported monthly mean",
                "months": list(MONTH_LABELS),
            }
        high = candidates.get(("high", unit))
        low = candidates.get(("low", unit))
        if high and low:
            means = [
                round((high_value + low_value) / 2, 2)
                if high_value is not None and low_value is not None else None
                for high_value, low_value in zip(high[1], low[1], strict=True)
            ]
            if sum(value is not None for value in means) >= 6:
                return {
                    "monthly_temperature_mean": means,
                    "monthly_average_high": high[1],
                    "monthly_average_low": low[1],
                    "temperature_unit": unit,
                    "method": "average of reported high and low",
                    "months": list(MONTH_LABELS),
                }
    return None


def temperature_chart_rows(climate_data: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Return ordered chart rows, or an empty list when no real series exists."""
    normalized = normalize_monthly_temperature(climate_data)
    if not normalized:
        return []
    return [
        {"Month": month, "Month order": index, "Temperature": value, "Unit": normalized["temperature_unit"]}
        for index, (month, value) in enumerate(
            zip(normalized["months"], normalized["monthly_temperature_mean"], strict=True), start=1
        )
        if value is not None
    ]
