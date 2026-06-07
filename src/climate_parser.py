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
CLIMATE_HINT_RE = re.compile(r"\b(climate|weather|temperature|precipitation|rainfall|snowfall|humidity|sunshine|record high|record low)\b", re.I)
UNRELATED_HINT_RE = re.compile(r"\b(demographics?|population|economy|transport|politics|government|elections?|religion|languages?|ethnic|education|sports?)\b", re.I)
METRIC_HINT_RE = re.compile(
    r"\b(record\s+(?:high|low)|average|mean|daily|maximum|minimum|high|low|precipitation|rainfall|snowfall|snowy|humidity|sunshine|dew point|ultraviolet|uv|days?)\b",
    re.I,
)


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
    return [record for record in records.values() if _record_month_count(record) >= 6]


def parse_weather_box_wikitext(wikitext: str, source_url: str | None = None) -> list[dict[str, Any]]:
    """Extract normalized climate metric rows from Weather box-like templates."""
    if mwparserfromhell is None:
        return _parse_template_params(_iter_weather_template_params_fallback(wikitext or ""), source_url)
    best: list[dict[str, Any]] = []
    wikicode = mwparserfromhell.parse(wikitext or "")
    for template in wikicode.filter_templates(recursive=True):
        if _template_name(template) not in WEATHER_BOX_NAMES:
            continue
        params = [(clean_text(str(param.name)).lower().replace("_", " "), clean_text(str(param.value))) for param in template.params]
        records = _parse_template_params(params, source_url)
        if _score_records(records, "") > _score_records(best, ""):
            best = records
    return best


def _record_month_count(record: dict[str, Any]) -> int:
    return sum(1 for month in MONTHS if record.get(month) is not None)


def _score_records(records: list[dict[str, Any]], caption: str) -> int:
    if not records:
        return 0
    score = len(records) * 10 + sum(_record_month_count(record) for record in records)
    if re.search(r"climate data for", caption, re.I):
        score += 50
    if CLIMATE_HINT_RE.search(caption):
        score += 20
    if re.search(r"airport|station", caption, re.I):
        score -= 5
    return score


def _expanded_rows_from_table(table: Any) -> list[list[str]]:
    """Expand table cells with colspan/rowspan into a simple rectangular grid."""
    grid: list[list[str]] = []
    rowspans: dict[int, tuple[str, int]] = {}
    for tr in table.find_all("tr"):
        row: list[str] = []
        col = 0
        for cell in tr.find_all(["th", "td"]):
            while col in rowspans:
                text, remaining = rowspans[col]
                row.append(text)
                if remaining <= 1:
                    del rowspans[col]
                else:
                    rowspans[col] = (text, remaining - 1)
                col += 1
            # Wikipedia tables often include references and hidden alternate-unit
            # spans.  Remove them before flattening the visible cell text so the
            # first parsed number is the value users actually see.
            clone = BeautifulSoup(str(cell), "html.parser")
            for hidden in clone.select("sup.reference, .reference, .sortkey, [aria-hidden=true]"):
                hidden.decompose()
            text = clean_text(clone.get_text(" "))
            colspan = max(1, int(cell.get("colspan", 1) or 1))
            rowspan = max(1, int(cell.get("rowspan", 1) or 1))
            for _ in range(colspan):
                row.append(text)
                if rowspan > 1:
                    rowspans[col] = (text, rowspan - 1)
                col += 1
        while col in rowspans:
            text, remaining = rowspans[col]
            row.append(text)
            if remaining <= 1:
                del rowspans[col]
            else:
                rowspans[col] = (text, remaining - 1)
            col += 1
        if row:
            grid.append(row)
    return grid


def _find_header_row(rows: list[list[str]]) -> tuple[int, dict[int, str]]:
    best_index = -1
    best_months: dict[int, str] = {}
    for idx, row in enumerate(rows[:6]):
        months: dict[int, str] = {}
        for col, label in enumerate(row):
            key = month_key(label)
            if key:
                months[col] = key
            elif clean_text(label).lower() in {"year", "annual"}:
                months[col] = "annual"
        if len([m for m in months.values() if m in MONTHS]) > len([m for m in best_months.values() if m in MONTHS]):
            best_index = idx
            best_months = months
    return best_index, best_months


def _records_from_rows(rows: list[list[str]], caption: str, source_url: str | None) -> list[dict[str, Any]]:
    if not rows:
        return []
    normalized_caption = clean_text(caption)
    table_text = clean_text(" ".join(" ".join(row) for row in rows[:5]))
    haystack = f"{normalized_caption} {table_text}"
    if UNRELATED_HINT_RE.search(haystack) and not CLIMATE_HINT_RE.search(haystack):
        return []

    header_idx, month_indexes = _find_header_row(rows)
    if len([m for m in month_indexes.values() if m in MONTHS]) < 6:
        return []
    if not CLIMATE_HINT_RE.search(haystack):
        LOGGER.debug("Skipping month-like table without climate/weather hints: %s", normalized_caption or table_text[:120])
        return []

    records: list[dict[str, Any]] = []
    for cells in rows[header_idx + 1 :]:
        if len(cells) < 4:
            continue
        metric_cell_index = next((idx for idx in range(min(len(cells), min(month_indexes) if month_indexes else len(cells))) if clean_text(cells[idx])), 0)
        raw_metric = cells[metric_cell_index]
        metric = normalize_metric_name(raw_metric)
        metric_lower = metric.lower()
        if not metric or metric_lower in {"month", "source", "source 1", "source 2", "year", "annual"}:
            continue
        if metric_lower.startswith("source"):
            continue
        if not METRIC_HINT_RE.search(metric):
            continue
        record = empty_month_record(metric, infer_unit(metric), source_url)
        for idx, cell in enumerate(cells):
            target = month_indexes.get(idx)
            if target:
                record[target] = parse_number(cell)
        if _record_month_count(record) >= 6:
            records.append(record)
    return records


def parse_html_climate_tables(html: str, source_url: str | None = None) -> list[dict[str, Any]]:
    """Extract normalized climate rows from rendered HTML climate tables."""
    candidates: list[tuple[int, list[dict[str, Any]], str]] = []
    if BeautifulSoup is None:
        parser = _SimpleTableParser()
        parser.feed(html or "")
        for table in parser.tables:
            caption = clean_text(table.get("caption", ""))
            records = _records_from_rows(table["rows"], caption, source_url)
            if records:
                candidates.append((_score_records(records, caption), records, caption))
    else:
        soup = BeautifulSoup(html or "", "html.parser")
        for table in soup.find_all("table"):
            caption = clean_text(table.caption.get_text(" ") if table.caption else "")
            rows = _expanded_rows_from_table(table)
            records = _records_from_rows(rows, caption, source_url)
            if records:
                candidates.append((_score_records(records, caption), records, caption))
    if not candidates:
        LOGGER.debug("No supported rendered HTML climate table found")
        return []
    candidates.sort(key=lambda item: item[0], reverse=True)
    LOGGER.debug("Selected rendered climate table %r with score %s", candidates[0][2], candidates[0][0])
    return candidates[0][1]


def parse_climate_data(wikitext: str = "", html: str = "", source_url: str | None = None) -> tuple[list[dict[str, Any]], str]:
    """Parse climate data from wikitext first, then from HTML as fallback."""
    try:
        records = parse_weather_box_wikitext(wikitext, source_url)
        if records:
            LOGGER.debug("Parsed %s climate rows from Weather box template", len(records))
            return records, "parsed_weather_box"
        LOGGER.debug("No supported Weather box template with monthly climate data was found")
    except Exception as exc:  # noqa: BLE001 - preserve app usability on parser edge cases
        LOGGER.warning("Weather box parsing failed: %s", exc)
    try:
        records = parse_html_climate_tables(html, source_url)
        if records:
            LOGGER.debug("Parsed %s climate rows from rendered HTML climate table", len(records))
            return records, "parsed_html_table"
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("HTML table parsing failed: %s", exc)
    return [], "no supported climate table found"

KOPPEN_CODE_RE = re.compile(
    r"\b(?P<code>Af|Am|Aw|BWh|BWk|BSh|BSk|Cfa|Cfb|Cfc|Csa|Csb|Cwa|Cwb|Cwc|Dfa|Dfb|Dfc|Dfd|Dwa|Dwb|Dwc|Dwd|Dsa|Dsb|Dsc|Dsd|ET|EF)\b",
    re.I,
)
CLIMATE_DESCRIPTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bsubtropical highland climate\b", re.I), "Subtropical highland climate"),
    (re.compile(r"\btropical rainforest climate\b", re.I), "Tropical rainforest climate"),
    (re.compile(r"\btropical monsoon climate\b", re.I), "Tropical monsoon climate"),
    (re.compile(r"\btropical (?:wet and dry|savanna) climate\b", re.I), "Tropical savanna climate"),
    (re.compile(r"\bhot desert climate\b", re.I), "Hot desert climate"),
    (re.compile(r"\bcold desert climate\b", re.I), "Cold desert climate"),
    (re.compile(r"\bhot semi[-–— ]arid climate\b", re.I), "Hot semi-arid climate"),
    (re.compile(r"\bcold semi[-–— ]arid climate\b", re.I), "Cold semi-arid climate"),
    (re.compile(r"\bsemi[-–— ]arid climate\b", re.I), "Semi-arid climate"),
    (re.compile(r"\bhumid subtropical climate\b", re.I), "Humid subtropical climate"),
    (re.compile(r"\b(?:temperate )?oceanic climate\b", re.I), "Oceanic climate"),
    (re.compile(r"\b(?:hot-summer |warm-summer )?mediterranean climate\b", re.I), "Mediterranean climate"),
    (re.compile(r"\b(?:humid )?continental climate\b", re.I), "Continental climate"),
    (re.compile(r"\bsubarctic climate\b", re.I), "Subarctic climate"),
    (re.compile(r"\btundra climate\b", re.I), "Tundra climate"),
    (re.compile(r"\bice cap climate\b", re.I), "Ice cap climate"),
    (re.compile(r"\b(?:alpine|highland|mountain) climate\b", re.I), "Highland climate"),
)

KOPPEN_DESCRIPTIONS = {
    "AF": "Tropical rainforest climate", "AM": "Tropical monsoon climate", "AW": "Tropical savanna climate",
    "BWH": "Hot desert climate", "BWK": "Cold desert climate", "BSH": "Hot semi-arid climate",
    "BSK": "Cold semi-arid climate", "CFA": "Humid subtropical climate", "CWA": "Humid subtropical climate",
    "CFB": "Oceanic climate", "CFC": "Oceanic climate", "CSA": "Mediterranean climate",
    "CSB": "Mediterranean climate", "DFA": "Humid continental climate", "DFB": "Humid continental climate",
    "DWA": "Humid continental climate", "DWB": "Humid continental climate", "DFC": "Subarctic climate",
    "ET": "Tundra climate", "EF": "Ice cap climate",
}


def _plain_text_from_html(html: str) -> str:
    if not html:
        return ""
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for hidden in soup.select("style,script,sup.reference,span.mw-editsection,.sortkey,[style*=display\\:none],[aria-hidden=true]"):
            hidden.decompose()
        return clean_text(soup.get_text(" "))
    return clean_text(re.sub(r"<[^>]+>", " ", html))


def _plain_text_from_wikitext(wikitext: str) -> str:
    text = re.sub(r"<ref[^>]*>.*?</ref>", " ", wikitext or "", flags=re.I | re.S)
    text = re.sub(r"<ref[^/]*/>", " ", text, flags=re.I)
    text = re.sub(r"\{\{[^{}]*\}\}", " ", text)
    text = re.sub(r"\[\[([^]|]+\|)?([^]]+)\]\]", r"\2", text)
    return clean_text(text)


def _climate_relevant_text(wikitext: str, html: str) -> str:
    """Put climate sections, weather boxes, tables, and nearby prose first."""
    match = re.search(r"(?:^|\n)==+\s*Climate\s*==+(?P<section>.*?)(?:\n==[^=]|\Z)", wikitext or "", flags=re.I | re.S)
    section = _plain_text_from_wikitext(match.group("section")) if match else ""
    weather_boxes = " ".join(
        _plain_text_from_wikitext(template)
        for template in re.findall(r"\{\{(?:Weather box|Infobox weather).*?\n\}\}", wikitext or "", flags=re.I | re.S)
    )
    table_contexts: list[str] = []
    if html and BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        for table in soup.find_all("table"):
            table_text = clean_text(table.get_text(" "))
            caption = clean_text(table.caption.get_text(" ") if table.caption else "")
            if not re.search(r"\b(climate|weather|temperature|precipitation)\b", f"{caption} {table_text}", re.I):
                continue
            nearby = []
            sibling = table.find_previous_sibling()
            for _ in range(3):
                if sibling is None:
                    break
                if getattr(sibling, "name", None) in {"p", "h2", "h3", "h4"}:
                    nearby.append(clean_text(sibling.get_text(" ")))
                sibling = sibling.find_previous_sibling()
            table_contexts.append(clean_text(" ".join(reversed(nearby)) + " " + caption + " " + table_text[:1500]))
    full_wikitext = _plain_text_from_wikitext(wikitext)
    html_text = _plain_text_from_html(html)
    return clean_text(" ".join([section, weather_boxes, *table_contexts, full_wikitext, html_text]))


def parse_climate_classification(wikitext: str = "", html: str = "") -> dict[str, str] | None:
    """Extract a Wikipedia-supported Köppen code and/or textual climate label.

    Wording is preserved even when no code is present.  This is important for
    descriptions such as Bogotá's "subtropical highland climate", which should
    not be replaced by a generic code expansion.
    """
    text = _climate_relevant_text(wikitext, html)
    if not text:
        return None
    description: str | None = None
    description_position = len(text) + 1
    for pattern, label in CLIMATE_DESCRIPTIONS:
        match = pattern.search(text)
        if match and match.start() < description_position:
            description = label
            description_position = match.start()
    code_match = KOPPEN_CODE_RE.search(text)
    if not code_match and not description:
        return None
    result: dict[str, str] = {}
    if code_match:
        result["code"] = code_match.group("code")
    if description:
        result["description"] = description
    elif code_match:
        inferred = KOPPEN_DESCRIPTIONS.get(code_match.group("code").upper())
        if inferred:
            result["description"] = inferred
    return result
