"""Calculate missing annual climate-table values from Jan–Dec observations."""
from __future__ import annotations

import logging
import re
from typing import Any, Literal

from .config import MONTHS
from .normalize import clean_text

LOGGER = logging.getLogger(__name__)

AnnualMethod = Literal["mean", "sum", "none"]
MIN_MONTHS_FOR_ANNUAL = 12

_REFERENCE_RE = re.compile(r"<sup\b[^>]*>.*?</sup>|\[(?:\d+|[a-z]|note\s*\d*)\]", re.I | re.S)
_NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
_MISSING = {"", "-", "—", "–", "n/a", "na", "none", "null", "missing", "unavailable"}


def parse_climate_number(value: Any) -> float | None:
    """Parse a climate value while retaining signs and ignoring annotations."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    text = str(value).replace("\xa0", " ")
    text = _REFERENCE_RE.sub(" ", text)
    text = clean_text(text).translate(str.maketrans({"−": "-", "‒": "-", "–": "-", "—": "-"}))
    if text.casefold() in _MISSING:
        return None
    match = _NUMBER_RE.search(text.replace(",", ""))
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


def _normalized_metric(metric_name: Any) -> str:
    name = clean_text(metric_name).casefold()
    name = re.sub(r"\([^)]*\)", " ", name)
    name = name.replace("º", "°")
    name = re.sub(r"°\s*[cf]\b|\b(?:degrees?\s*)?[cf]\b|\b(?:celsius|fahrenheit)\b", " ", name)
    name = re.sub(r"\b(?:mm|cm|millimetres?|millimeters?|centimetres?|centimeters?)\b", " ", name)
    name = re.sub(r"[^a-z]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def annual_calculation_method(metric_name: Any, unit: Any = None) -> AnnualMethod:
    """Return the documented annual aggregation method for a known metric."""
    metric = _normalized_metric(metric_name)
    base_metric = metric.removeprefix("average ").strip()
    unit_text = clean_text(unit).casefold()

    if metric in {
        "average", "high", "low", "record high", "record low", "daily mean", "mean",
        "daily mean temperature", "mean temperature",
    } and ("c" in unit_text or re.search(r"\b[cf]\b|°", clean_text(metric_name), re.I)):
        return "mean"
    if base_metric in {"humidity", "relative humidity"}:
        return "mean"
    if base_metric in {
        "precipitation", "rainfall", "snowfall", "precipitation days",
        "rain days", "snow days", "sun", "sunshine hours",
    }:
        return "sum"
    return "none"


def calculate_annual_value(
    metric_name: Any, unit: Any, monthly_values: list[Any] | tuple[Any, ...],
) -> float | int | None:
    """Calculate a formatted annual value for a supported, complete monthly row."""
    method = annual_calculation_method(metric_name, unit)
    parsed = [parse_climate_number(value) for value in monthly_values[:12]]
    valid = [value for value in parsed if value is not None]
    if method == "none":
        LOGGER.info("Annual value unavailable for unknown metric %r", metric_name)
        return None
    if len(parsed) < 12 or len(valid) < MIN_MONTHS_FOR_ANNUAL:
        LOGGER.info(
            "Annual value unavailable for %r: %s of 12 monthly values are numeric",
            metric_name, len(valid),
        )
        return None

    result = sum(valid) / len(valid) if method == "mean" else sum(valid)
    metric = _normalized_metric(metric_name).removeprefix("average ").strip()
    rounded = round(result, 1)
    if method == "sum" and metric in {"precipitation", "rainfall", "snowfall"}:
        return int(round(result)) if all(value.is_integer() for value in valid) else rounded
    if method == "sum" and metric in {"sun", "sunshine hours"}:
        return int(round(result)) if all(value.is_integer() for value in valid) else rounded
    return rounded


def populate_annual_values(rows: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Copy climate rows and populate missing annual values with provenance."""
    enriched: list[dict[str, Any]] = []
    for source_row in rows or []:
        row = dict(source_row)
        source_annual = parse_climate_number(row.get("annual"))
        method = annual_calculation_method(row.get("metric_name"), row.get("unit"))
        if source_annual is not None:
            row["annual_value_source"] = "source"
            row["annual_calculation_method"] = "none"
        else:
            calculated = calculate_annual_value(
                row.get("metric_name"), row.get("unit"), [row.get(month) for month in MONTHS],
            )
            row["annual"] = calculated
            row["annual_value_source"] = "calculated" if calculated is not None else "unavailable"
            row["annual_calculation_method"] = method if calculated is not None else "none"
        enriched.append(row)
    return enriched
