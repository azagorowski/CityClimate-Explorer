"""Parse Wikipedia Weather box templates and HTML climate tables."""
from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from typing import Any

try:  # mwparserfromhell is preferred when installed by requirements.txt.
    import mwparserfromhell  # type: ignore
except ImportError:  # pragma: no cover - exercised indirectly in minimal CI envs
    mwparserfromhell = None

try:  # BeautifulSoup is preferred for real Wikipedia HTML.
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:  # pragma: no cover
    BeautifulSoup = None

from .config import MONTHS
from .normalize import clean_text, empty_month_record, infer_unit, month_key, normalize_metric_name, parse_number

LOGGER = logging.getLogger(__name__)

WEATHER_BOX_NAMES = {"weather box", "weatherbox", "climate chart"}
MONTH_PARAM_RE = re.compile(r"^(?P<metric>.+?)\s+(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)$", re.I)
MONTH_FIRST_PARAM_RE = re.compile(r"^(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+(?P<metric>.+)$", re.I)
EXCLUDED_PREFIXES = {"location", "source", "single line", "collapsed", "width", "metric first", "float", "clear"}


class _SimpleTableParser(HTMLParser):
    """Tiny fallback table parser used only when BeautifulSoup is unavailable."""

    def __init__(self) -> None:
        super().__init__()
        self.tables: list[dict[str, Any]] = []
        self._in_table = False
        self._in_caption = False
        self._in_row = False
        self._in_cell = False
        self._table: dict[str, Any] | None = None
        self._row: list[str] = []
        self._cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
            self._table = {"caption": "", "rows": []}
        elif self._in_table and tag == "caption":
            self._in_caption = True
        elif self._in_table and tag == "tr":
            self._in_row = True
            self._row = []
        elif self._in_table and tag in {"th", "td"}:
            self._in_cell = True
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._in_caption and self._table is not None:
            self._table["caption"] += data + " "
        if self._in_cell:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._in_cell:
            self._row.append(clean_text(" ".join(self._cell)))
            self._in_cell = False
        elif tag == "tr" and self._in_row:
            if self._table is not None and self._row:
                self._table["rows"].append(self._row)
            self._in_row = False
        elif tag == "caption":
            self._in_caption = False
        elif tag == "table" and self._in_table:
            if self._table is not None:
                self.tables.append(self._table)
            self._in_table = False


def _template_name(template: Any) -> str:
    return clean_text(str(template.name)).lower().replace("_", " ")


def _iter_weather_template_params_fallback(wikitext: str) -> list[tuple[str, str]]:
    """Return template params with a lightweight parser for simple Weather boxes."""
    match = re.search(r"\{\{\s*(Weather box|Weatherbox|Climate chart)(?P<body>.*?)\n\}\}", wikitext, flags=re.I | re.S)
    if not match:
        return []
    params: list[tuple[str, str]] = []
    for line in match.group("body").splitlines():
        if not line.lstrip().startswith("|") or "=" not in line:
            continue
        key, value = line.lstrip()[1:].split("=", 1)
        params.append((clean_text(key).lower().replace("_", " "), clean_text(value)))
    return params


def _parse_template_params(params: list[tuple[str, str]], source_url: str | None) -> list[dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    source = source_url
    for key, value in params:
        if key == "source" and value:
            source = source_url or value
            continue
        if any(key.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
            continue
        match = MONTH_PARAM_RE.match(key) or MONTH_FIRST_PARAM_RE.match(key)
        if not match:
            continue
        raw_metric = match.group("metric")
        month = match.group("month").lower()
        metric_name = re.sub(r"\b([cf])\b", lambda m: m.group(1).upper(), normalize_metric_name(raw_metric))
        record = records.setdefault(metric_name, empty_month_record(metric_name, infer_unit(raw_metric), source))
        record[month] = parse_number(value)
        if not record.get("unit"):
            record["unit"] = infer_unit(raw_metric)
    return list(records.values())


def parse_weather_box_wikitext(wikitext: str, source_url: str | None = None) -> list[dict[str, Any]]:
    """Extract normalized climate metric rows from Weather box-like templates."""
    if mwparserfromhell is None:
        return _parse_template_params(_iter_weather_template_params_fallback(wikitext or ""), source_url)
    wikicode = mwparserfromhell.parse(wikitext or "")
    for template in wikicode.filter_templates(recursive=True):
        if _template_name(template) not in WEATHER_BOX_NAMES:
            continue
        params = [(clean_text(str(param.name)).lower().replace("_", " "), clean_text(str(param.value))) for param in template.params]
        records = _parse_template_params(params, source_url)
        if records:
            return records
    return []


def _records_from_rows(rows: list[list[str]], caption: str, source_url: str | None) -> list[dict[str, Any]]:
    if not rows:
        return []
    table_text = clean_text(" ".join(" ".join(row) for row in rows[:3])).lower()
    haystack = f"{caption} {table_text}".lower()
    if "climate" not in haystack and "weather" not in haystack:
        return []
    month_indexes: dict[int, str] = {}
    for idx, label in enumerate(rows[0]):
        key = month_key(label)
        if key:
            month_indexes[idx] = key
        elif clean_text(label).lower() in {"year", "annual"}:
            month_indexes[idx] = "annual"
    if len([m for m in month_indexes.values() if m in MONTHS]) < 6:
        return []
    records: list[dict[str, Any]] = []
    for cells in rows[1:]:
        if len(cells) < 4:
            continue
        metric = normalize_metric_name(cells[0])
        if not metric or metric.lower() in {"month", "source"}:
            continue
        record = empty_month_record(metric, infer_unit(metric), source_url)
        for idx, cell in enumerate(cells):
            target = month_indexes.get(idx)
            if target:
                record[target] = parse_number(cell)
        if any(record[month] is not None for month in MONTHS):
            records.append(record)
    return records


def parse_html_climate_tables(html: str, source_url: str | None = None) -> list[dict[str, Any]]:
    """Extract normalized climate rows from rendered HTML climate tables."""
    if BeautifulSoup is None:
        parser = _SimpleTableParser()
        parser.feed(html or "")
        for table in parser.tables:
            records = _records_from_rows(table["rows"], clean_text(table.get("caption", "")), source_url)
            if records:
                return records
        return []

    soup = BeautifulSoup(html or "", "html.parser")
    for table in soup.find_all("table"):
        caption = clean_text(table.caption.get_text(" ") if table.caption else "")
        rows = [[clean_text(cell.get_text(" ")) for cell in row.find_all(["th", "td"])] for row in table.find_all("tr")]
        records = _records_from_rows(rows, caption, source_url)
        if records:
            return records
    return []


def parse_climate_data(wikitext: str = "", html: str = "", source_url: str | None = None) -> tuple[list[dict[str, Any]], str]:
    """Parse climate data from wikitext first, then from HTML as fallback."""
    try:
        records = parse_weather_box_wikitext(wikitext, source_url)
        if records:
            return records, "parsed_weather_box"
    except Exception as exc:  # noqa: BLE001 - preserve app usability on parser edge cases
        LOGGER.warning("Weather box parsing failed: %s", exc)
    try:
        records = parse_html_climate_tables(html, source_url)
        if records:
            return records, "parsed_html_table"
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("HTML table parsing failed: %s", exc)
    return [], "climate data unavailable"
