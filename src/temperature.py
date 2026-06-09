"""Normalize selected-city climate rows to Celsius for annual charts."""
from __future__ import annotations

import logging
import re
from typing import Any

from .config import MONTH_LABELS, MONTHS
from .normalize import clean_text

LOGGER = logging.getLogger(__name__)

UNAVAILABLE_MESSAGE = "Annual temperature chart unavailable because monthly temperature data was not found."
MIN_VALID_MONTHS = 3

# These normalized labels document the direct monthly-average rows that the
# chart accepts. Units may also live in the row's separate ``unit`` field.
_CHECKED_MEAN_LABELS = (
    "Average C",
    "Average °C",
    "Average",
    "Avg C",
    "Avg °C",
    "Daily mean C",
    "Daily mean °C",
    "Mean C",
    "Mean °C",
    "Mean daily temperature C",
    "Mean daily temperature °C",
)
_EXCLUDED_PATTERNS = re.compile(
    r"\b(record|precipitation|rainfall|snow|sunshine|humidity|dew point|wind|heat index)\b", re.I,
)
_HIDDEN_ELEMENT_RE = re.compile(
    r"<(?:span|div)[^>]*(?:display\s*:\s*none|visibility\s*:\s*hidden|class=[\"'][^\"']*(?:sortkey|reference)[^\"']*)[^>]*>.*?</(?:span|div)>",
    re.I | re.S,
)
_REFERENCE_RE = re.compile(r"<sup\b[^>]*>.*?</sup>|\[(?:\d+|[a-z]|note\s*\d*)\]", re.I | re.S)
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _row_value(row: dict[str, Any], key: str) -> Any:
    """Read normalized parser keys or their title-cased UI equivalents."""
    aliases = {"metric_name": ("metric_name", "metric"), "unit": ("unit",)}
    wanted = aliases.get(key, (key,))
    for name, value in row.items():
        normalized_name = str(name).casefold().replace(" ", "_")
        if normalized_name in wanted:
            return value
    return None


def _normalized_metric_words(metric_name: Any) -> str:
    """Return a punctuation/unit-insensitive metric label for matching."""
    name = clean_text(metric_name).casefold()
    name = name.replace("º", "°")
    name = re.sub(r"[()]", " ", name)
    name = re.sub(r"°\s*[cf]\b|\b(?:degrees?\s*)?[cf]\b|\b(?:celsius|fahrenheit)\b", " ", name)
    name = re.sub(r"\bavg\.?\b", "average", name)
    name = re.sub(r"[^a-z]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def _metric_kind(metric_name: Any) -> str | None:
    """Classify supported temperature rows, keeping average above daily mean."""
    raw_name = clean_text(metric_name)
    if not raw_name or _EXCLUDED_PATTERNS.search(raw_name):
        return None
    name = _normalized_metric_words(raw_name)
    if name in {"average", "average temperature"}:
        return "average"
    if name in {"average daily temperature", "daily mean", "mean", "mean temperature", "mean daily temperature", "daily mean temperature"}:
        return "daily_mean"
    if name in {"high", "average high", "average daily high", "average maximum", "average daily maximum", "mean maximum"}:
        return "high"
    if name in {"low", "average low", "average daily low", "average minimum", "average daily minimum", "mean minimum"}:
        return "low"
    return None


def _temperature_unit(row: dict[str, Any]) -> str | None:
    metric_name = _row_value(row, "metric_name")
    explicit_unit = clean_text(_row_value(row, "unit"))
    combined_text = f"{explicit_unit} {metric_name or ''}"
    celsius_pattern = r"°\s*C\b|\b(?:degrees?\s*)?C\b|\bCelsius\b"
    fahrenheit_pattern = r"°\s*F\b|\b(?:degrees?\s*)?F\b|\bFahrenheit\b"

    # Rendered Wikipedia rows can list both units while their cells put the
    # first unit first (for example, "0.3 (32.5)" under "°C (°F)"). In that
    # case the label order is more informative than an inferred unit field.
    metric_text = clean_text(metric_name)
    metric_celsius = re.search(celsius_pattern, metric_text, re.I)
    metric_fahrenheit = re.search(fahrenheit_pattern, metric_text, re.I)
    if metric_celsius and metric_fahrenheit:
        return "°C" if metric_celsius.start() < metric_fahrenheit.start() else "°F"
    if re.search(celsius_pattern, explicit_unit, re.I):
        return "°C"
    if re.search(fahrenheit_pattern, explicit_unit, re.I):
        return "°F"
    if re.search(celsius_pattern, combined_text, re.I):
        return "°C"
    if re.search(fahrenheit_pattern, combined_text, re.I):
        return "°F"
    return None


def _parse_temperature_number(value: Any) -> float | None:
    """Parse one temperature while discarding references, hidden text, and units."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)

    text = str(value).replace("\xa0", " ")
    text = _HIDDEN_ELEMENT_RE.sub(" ", text)
    text = _REFERENCE_RE.sub(" ", text)
    text = clean_text(text).translate(str.maketrans({"−": "-", "‒": "-", "–": "-", "—": "-"}))
    if not text or text.casefold() in {"-", "n/a", "na", "missing"}:
        return None
    match = _NUMBER_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _monthly_values(row: dict[str, Any]) -> list[float | None]:
    """Read Jan-Dec in calendar order; the annual summary is ignored."""
    return [_parse_temperature_number(_row_value(row, month)) for month in MONTHS]


def _to_celsius(values: list[float | None], unit: str) -> list[float | None]:
    if unit == "°C":
        return values
    return [round((value - 32) * 5 / 9, 1) if value is not None else None for value in values]


def _result_for_direct(
    row: dict[str, Any], values: list[float | None], unit: str,
) -> dict[str, Any]:
    celsius_values = _to_celsius(values, unit)
    source_name = clean_text(_row_value(row, "metric_name"))
    return {
        "months": list(MONTH_LABELS),
        "monthly_temperature_mean_c": celsius_values,
        "monthly_temperature_mean": celsius_values,
        "temperature_unit": "°C",
        "source_row_used": source_name,
        "source_rows_used": [source_name],
        "conversion_applied": unit == "°F",
        "method": "reported monthly mean" if unit == "°C" else "reported monthly mean converted from °F",
    }


def normalize_monthly_temperatures_to_celsius(
    climate_table: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    """Return the best available Jan-Dec monthly mean series in Celsius.

    Priority is reported Celsius average, reported Celsius daily mean, a mean
    computed from Celsius high/low rows, then the equivalent Fahrenheit
    sources converted to Celsius. At least three valid months are required;
    missing months are skipped rather than guessed.
    """
    candidates: dict[tuple[str, str], tuple[dict[str, Any], list[float | None]]] = {}
    rejection_reasons: list[str] = []
    rows = climate_table or []

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            rejection_reasons.append(f"row {index}: rejected because it is not a mapping")
            continue
        metric_name = clean_text(_row_value(row, "metric_name"))
        kind = _metric_kind(metric_name)
        unit = _temperature_unit(row)
        values = _monthly_values(row)
        valid_months = sum(value is not None for value in values)
        if not kind:
            rejection_reasons.append(f"{metric_name or '<blank metric>'}: unsupported metric label")
            continue
        if not unit:
            rejection_reasons.append(f"{metric_name}: temperature unit was not recognized")
            continue
        if valid_months < MIN_VALID_MONTHS:
            rejection_reasons.append(
                f"{metric_name}: only {valid_months} valid monthly values; {MIN_VALID_MONTHS} required"
            )
            continue
        key = (kind, unit)
        if key in candidates:
            rejection_reasons.append(f"{metric_name}: lower-priority duplicate of {key}")
            continue
        candidates[key] = (row, values)

    # Direct Celsius sources always win, with the short "Average C" style row
    # deliberately preferred over daily-mean variants.
    for kind in ("average", "daily_mean"):
        direct = candidates.get((kind, "°C"))
        if direct:
            return _result_for_direct(*direct, "°C")

    high = candidates.get(("high", "°C"))
    low = candidates.get(("low", "°C"))
    if high and low:
        means = [
            round((high_value + low_value) / 2, 1)
            if high_value is not None and low_value is not None else None
            for high_value, low_value in zip(high[1], low[1], strict=True)
        ]
        if sum(value is not None for value in means) >= MIN_VALID_MONTHS:
            source_rows = [clean_text(_row_value(high[0], "metric_name")), clean_text(_row_value(low[0], "metric_name"))]
            return {
                "months": list(MONTH_LABELS),
                "monthly_temperature_mean_c": means,
                "monthly_temperature_mean": means,
                "temperature_unit": "°C",
                "source_row_used": " + ".join(source_rows),
                "source_rows_used": source_rows,
                "conversion_applied": False,
                "method": "average of reported high and low",
            }
        rejection_reasons.append("Celsius high/low pair: too few months contain both values")
    elif high or low:
        rejection_reasons.append("Celsius high/low fallback: matching high or low row is missing")

    for kind in ("average", "daily_mean"):
        direct = candidates.get((kind, "°F"))
        if direct:
            return _result_for_direct(*direct, "°F")

    high = candidates.get(("high", "°F"))
    low = candidates.get(("low", "°F"))
    if high and low:
        high_c = _to_celsius(high[1], "°F")
        low_c = _to_celsius(low[1], "°F")
        means = [
            round((high_value + low_value) / 2, 1)
            if high_value is not None and low_value is not None else None
            for high_value, low_value in zip(high_c, low_c, strict=True)
        ]
        if sum(value is not None for value in means) >= MIN_VALID_MONTHS:
            source_rows = [clean_text(_row_value(high[0], "metric_name")), clean_text(_row_value(low[0], "metric_name"))]
            return {
                "months": list(MONTH_LABELS),
                "monthly_temperature_mean_c": means,
                "monthly_temperature_mean": means,
                "temperature_unit": "°C",
                "source_row_used": " + ".join(source_rows),
                "source_rows_used": source_rows,
                "conversion_applied": True,
                "method": "average of high and low converted from °F",
            }
        rejection_reasons.append("Fahrenheit high/low pair: too few months contain both values")
    elif high or low:
        rejection_reasons.append("Fahrenheit high/low fallback: matching high or low row is missing")

    available_metrics = [clean_text(_row_value(row, "metric_name")) for row in rows if isinstance(row, dict)]
    available_units = [clean_text(_row_value(row, "unit")) for row in rows if isinstance(row, dict)]
    LOGGER.warning(
        "Annual temperature chart data unavailable. Available metrics=%s; available units=%s; "
        "checked mean labels=%s; candidate rejections=%s",
        available_metrics,
        available_units,
        list(_CHECKED_MEAN_LABELS),
        rejection_reasons or ["no climate rows were provided"],
    )
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
