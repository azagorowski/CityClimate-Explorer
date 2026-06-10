"""Normalization helpers for monthly climate data."""
from __future__ import annotations

import re
import unicodedata
from typing import Any

from .config import MONTHS

MONTH_ALIASES = {
    "january": "jan", "jan": "jan",
    "february": "feb", "feb": "feb",
    "march": "mar", "mar": "mar",
    "april": "apr", "apr": "apr",
    "may": "may",
    "june": "jun", "jun": "jun",
    "july": "jul", "jul": "jul",
    "august": "aug", "aug": "aug",
    "september": "sep", "sept": "sep", "sep": "sep",
    "october": "oct", "oct": "oct",
    "november": "nov", "nov": "nov",
    "december": "dec", "dec": "dec",
}

UNIT_PATTERNS = [
    (re.compile(r"\b(?:°|deg|degrees?)?\s*F\b|\bFahrenheit\b", re.I), "°F"),
    (re.compile(r"\b(?:°|deg|degrees?)?\s*C\b|\bCelsius\b", re.I), "°C"),
    (re.compile(r"\bmm\b", re.I), "mm"),
    (re.compile(r"\bin(?:ches)?\b", re.I), "in"),
    (re.compile(r"\bcm\b", re.I), "cm"),
    (re.compile(r"\bhours?\b", re.I), "hours"),
    (re.compile(r"\bdays?\b", re.I), "days"),
    (re.compile(r"%", re.I), "%"),
]


def month_key(value: str) -> str | None:
    """Return a normalized Jan-Dec key for a month-like label."""
    cleaned = re.sub(r"[^A-Za-z]", "", value or "").lower()
    return MONTH_ALIASES.get(cleaned)


def clean_text(value: Any) -> str:
    """Collapse whitespace and strip wiki/table cruft from a cell value."""
    text = "" if value is None else str(value)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\[\[([^]|]+\|)?([^]]+)\]\]", r"\2", text)
    text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = text.replace("&nbsp;", " ").replace("−", "-")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_number(value: Any) -> float | str | None:
    """Extract a numeric value when possible while preserving non-empty text fallback."""
    text = clean_text(value)
    if not text or text in {"—", "-", "N/A", "n/a"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            return text
    return text


def infer_unit(metric_name: str, explicit_unit: str | None = None) -> str | None:
    """Infer a display unit from explicit unit text or a metric label."""
    haystack = " ".join(part for part in [explicit_unit, metric_name] if part)
    for pattern, unit in UNIT_PATTERNS:
        if pattern.search(haystack):
            return unit
    return explicit_unit


def normalize_metric_name(raw_name: str) -> str:
    """Convert common Weather box field names into readable metric labels."""
    name = clean_text(raw_name)
    name = re.sub(r"^(?:average|mean)\s+", "Average ", name, flags=re.I)
    name = name.replace("avg", "Average")
    name = re.sub(r"\s+", " ", name).strip(" :-")
    return name[:1].upper() + name[1:] if name else "Unknown metric"


def empty_month_record(metric_name: str, unit: str | None = None, source: str | None = None) -> dict[str, Any]:
    """Create a normalized climate metric record with Jan-Dec columns."""
    record: dict[str, Any] = {"metric_name": normalize_metric_name(metric_name), "unit": unit}
    record.update({month: None for month in MONTHS})
    record["annual"] = None
    record["source"] = source
    return record
def normalized_search_key(value: object) -> str:
    """Return a case/diacritic-insensitive key without changing display text."""
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = "".join(character for character in text if not unicodedata.combining(character))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()
