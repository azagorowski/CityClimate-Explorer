"""Folium map construction for CityClimate Explorer."""
from __future__ import annotations

from html import escape
from typing import Any

import folium
import pandas as pd
from branca.element import Element

from .config import get_tile_provider

CLIMATE_COLORS = {
    "Tropical": "#16a34a",
    "Dry / Arid": "#d97706",
    "Temperate": "#2563eb",
    "Continental": "#7c3aed",
    "Polar": "#06b6d4",
    "Highland / Mountain": "#92400e",
    "Unknown": "#6b7280",
}


def classification_value(city: dict[str, Any] | None) -> str:
    """Return a displayable climate classification value."""
    if not city:
        return "Unknown"
    return str(city.get("climate_classification_label") or city.get("climate_classification") or "Unknown")


def climate_category(value: str | None) -> str:
    """Map specific climate labels and Köppen codes into stable broad groups."""
    text = (value or "").casefold()
    if not text or text == "unknown":
        return "Unknown"
    if any(token in text for token in ("highland", "mountain", "alpine")):
        return "Highland / Mountain"
    if any(token in text for token in ("tropical", "rainforest", "monsoon", "savanna")) or any(code in value for code in ("Af", "Am", "Aw")):
        return "Tropical"
    if any(token in text for token in ("desert", "arid", "steppe")) or any(code in value for code in ("BWh", "BWk", "BSh", "BSk")):
        return "Dry / Arid"
    if any(token in text for token in ("polar", "tundra", "ice cap")) or any(code in value for code in ("ET", "EF")):
        return "Polar"
    if any(token in text for token in ("continental", "subarctic")) or any(code in value for code in ("Dfa", "Dfb", "Dfc", "Dwa", "Dwb")):
        return "Continental"
    if any(token in text for token in ("temperate", "subtropical", "oceanic", "mediterranean", "maritime")) or any(code in value for code in ("Cfa", "Cwa", "Cfb", "Cfc", "Csa", "Csb")):
        return "Temperate"
    first_code = value.strip()[:1].upper() if value else ""
    return {"A": "Tropical", "B": "Dry / Arid", "C": "Temperate", "D": "Continental", "E": "Polar"}.get(first_code, "Unknown")


def color_for_classification(value: str | None) -> str:
    """Return the documented broad-category marker color."""
    return CLIMATE_COLORS[climate_category(value)]


def climate_legend_html() -> str:
    """Return a reusable, readable map legend for every climate category."""
    items = "".join(
        f'<div style="margin:4px 0"><span style="display:inline-block;width:12px;height:12px;'
        f'border-radius:50%;background:{color};margin-right:7px;border:1px solid #fff"></span>{label}</div>'
        for label, color in CLIMATE_COLORS.items()
    )
    return (
        '<div id="climate-legend" style="position:fixed;bottom:28px;left:28px;z-index:9999;'
        'background:white;padding:10px 12px;border:1px solid #d1d5db;border-radius:6px;'
        'box-shadow:0 1px 5px rgba(0,0,0,.25);font-size:12px;line-height:1.2">'
        '<strong>Climate groups</strong>' + items + '</div>'
    )


def marker_id(city: dict[str, Any]) -> str:
    """Return a stable marker id for QID and local-only records."""
    qid = str(city.get("qid") or "").strip()
    if qid:
        return qid
    return str(city.get("marker_id") or f"local:{str(city.get('country') or '').casefold()}:{str(city.get('name') or '').casefold()}")


def population_label(city: dict[str, Any]) -> str:
    population = city.get("population")
    return f"{population:,.0f}" if isinstance(population, int | float) else "unavailable"


def climate_source(city: dict[str, Any]) -> tuple[str, str, str | None]:
    metadata = city.get("climate_classification_source_metadata") or city.get("climate_source_metadata") or {}
    name = str(metadata.get("source_name") or "Local cache")
    priority = str(metadata.get("source_priority") or city.get("climate_classification_source") or "unavailable")
    return name, priority, metadata.get("source_url")


def _popup_html(city: dict[str, Any]) -> str:
    url = city.get("wikipedia_url") or "#"
    climate = classification_value(city)
    source_name, priority, source_url = climate_source(city)
    source_link = f'<a href="{escape(str(source_url))}" target="_blank">{escape(source_name)}</a>' if source_url else escape(source_name)
    source_metadata = city.get("climate_classification_source_metadata") or city.get("climate_source_metadata") or {}
    source_license = escape(str(source_metadata.get("license") or "not specified"))
    history_url = source_metadata.get("contributors_url")
    history_link = f'<a href="{escape(str(history_url))}" target="_blank">page history / contributors</a>' if history_url else ""
    status = city.get("extraction_status", "not parsed")
    rows = "".join(
        f"<tr><td>{escape(str(metric.get('metric_name') or ''))}</td><td>{escape(str(metric.get('unit') or ''))}</td>"
        + "".join(f"<td>{metric.get(month) if metric.get(month) is not None else ''}</td>" for month in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])
        + "</tr>"
        for metric in city.get("climate_data", [])[:6]
    )
    table = "<p>No parsed monthly climate table is loaded. Select this city to load details.</p>"
    if rows:
        table = "<table border='1' style='border-collapse:collapse;font-size:11px'><tr><th>Metric</th><th>Unit</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th></tr>" + rows + "</table>"
    return f"""
    <b>{escape(str(city.get('name') or ''))}</b><br>
    {escape(str(city.get('country') or ''))}<br>
    Population: {population_label(city)}<br>
    Climate: {escape(climate)}<br>
    Climate group: {escape(climate_category(climate))}<br>
    Climate source: {source_link}<br>
    Source priority: {escape(priority)}<br>
    Source license: {source_license} {history_link}<br>
    Status: {escape(str(status))}<br>
    <a href="{escape(str(url))}" target="_blank">City Wikipedia page</a><br>
    {table}
    """


def build_city_map(cities: list[dict[str, Any]], selected_qid: str | None = None, same_climate_only: bool = False) -> folium.Map:
    """Build an interactive Folium map with preloaded climate styling and legend."""
    valid = [c for c in cities if c.get("latitude") is not None and c.get("longitude") is not None]
    center = [20, 0] if not valid else [pd.Series([c["latitude"] for c in valid]).mean(), pd.Series([c["longitude"] for c in valid]).mean()]
    tile_provider = get_tile_provider()
    fmap = folium.Map(location=center, zoom_start=2, tiles=None)
    folium.TileLayer(
        tiles=tile_provider.tiles,
        attr=tile_provider.attribution,
        name=tile_provider.name.replace("_", " ").title(),
        overlay=False,
        control=False,
    ).add_to(fmap)
    fmap.get_root().html.add_child(Element(climate_legend_html()))
    selected = next((c for c in valid if marker_id(c) == selected_qid), None)
    selected_class = classification_value(selected) if selected else None

    for city in valid:
        climate = classification_value(city)
        hidden_by_same_filter = bool(same_climate_only and selected_class and climate != selected_class)
        radius = 7 if marker_id(city) == selected_qid else 4
        opacity = 0.15 if hidden_by_same_filter else 0.85
        color = color_for_classification(climate)
        source_name, priority, _ = climate_source(city)
        folium.CircleMarker(
            location=[city["latitude"], city["longitude"]], radius=radius, color=color,
            fill=True, fill_color=color, fill_opacity=opacity, opacity=opacity,
            tooltip=(f"{city.get('name')}, {city.get('country')} | {climate} | "
                     f"source: {source_name} ({priority})"),
            popup=folium.Popup(_popup_html(city), max_width=900),
        ).add_to(fmap)
    return fmap
