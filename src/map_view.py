"""Folium map construction for CityClimate Explorer."""
from __future__ import annotations

from html import escape
import re
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


def climate_category(value: str | None, code: str | None = None) -> str:
    """Map a specific label and optional Köppen code into a broad group."""
    text = (value or "").casefold().strip()
    normalized_code = (code or "").strip()
    if not text or text == "unknown":
        return "Unknown"
    if any(token in text for token in ("highland", "mountain", "alpine")):
        return "Highland / Mountain"
    if any(token in text for token in ("desert", "arid", "steppe", "semi-arid")):
        return "Dry / Arid"
    if any(token in text for token in ("polar", "tundra", "ice cap")):
        return "Polar"
    if any(token in text for token in ("continental", "subarctic")):
        return "Continental"
    if any(token in text for token in ("subtropical", "temperate", "oceanic", "mediterranean", "maritime")):
        return "Temperate"
    if re.search(r"\b(tropical|rainforest|monsoon|savanna)\b", text):
        return "Tropical"
    candidate = normalized_code or (value or "")
    codes = re.findall(r"\b(?:A[fmsw]|B[WS][hk]|C[fsw][abc]|D[fsw][abcd]|E[TF])\b", candidate, re.I)
    groups = {"A": "Tropical", "B": "Dry / Arid", "C": "Temperate", "D": "Continental", "E": "Polar"}
    return groups.get(codes[0][0].upper(), "Unknown") if codes else "Unknown"


def climate_group(city: dict[str, Any] | None) -> str:
    """Return the authoritative cached group, deriving it for legacy records."""
    if not city:
        return "Unknown"
    cached = str(city.get("climate_group") or "").strip()
    if cached in CLIMATE_COLORS:
        return cached
    return climate_category(classification_value(city), str(city.get("climate_classification") or ""))

def color_for_classification(value: str | None) -> str:
    """Return the documented broad-category marker color."""
    return CLIMATE_COLORS[climate_category(value)]


def climate_legend_html() -> str:
    """Return a readable map legend for climate colors and capital symbols."""
    items = "".join(
        f'<div class="map-legend-item" style="margin:4px 0"><span style="display:inline-block;width:12px;height:12px;'
        f'border-radius:3px;background:{color};margin-right:7px;border:1px solid #374151;opacity:.75"></span>{label}</div>'
        for label, color in CLIMATE_COLORS.items()
    )
    symbols = (
        '<div style="margin-top:8px;border-top:1px solid #d1d5db;padding-top:6px"><strong>Capital markers</strong>'
        '<div style="margin:4px 0"><span style="display:inline-block;width:13px;height:13px;border-radius:50%;background:#fff;border:3px solid #374151;margin-right:7px"></span>National capital</div>'
        '<div style="margin:4px 0"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#fff;border:2px solid #374151;margin:0 9px 0 2px"></span>Regional capital</div></div>'
    )
    return (
        '<div id="climate-legend" class="map-legend" style="position:fixed;bottom:28px;left:28px;z-index:9999;'
        'background:rgba(255,255,255,.96);color:#111827;padding:12px 14px;border:1px solid #9ca3af;border-radius:8px;'
        'box-shadow:0 2px 8px rgba(0,0,0,.28);font:13px/1.3 Arial,sans-serif;opacity:1;max-height:360px;overflow:auto">'
        '<style>.map-legend,.map-legend *{color:#111827 !important}.map-legend-item{white-space:nowrap}</style>'
        '<strong>Marker &amp; zone climate groups</strong>' + items + symbols + '</div>'
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
        + "".join(f"<td>{metric.get(month) if metric.get(month) is not None else ''}</td>" for month in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec", "annual"])
        + "</tr>"
        for metric in city.get("climate_data", [])[:6]
    )
    table = "<p>No parsed monthly climate table is loaded. Select this city to load details.</p>"
    if rows:
        table = "<table border='1' style='border-collapse:collapse;font-size:11px'><tr><th>Metric</th><th>Unit</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>Annual</th></tr>" + rows + "</table>"
    record_type = "National capital" if city.get("record_type") == "national_capital" else "Regional capital"
    region = city.get("administrative_region")
    region_line = f"Administrative region: {escape(str(region))}<br>" if region else ""
    return f"""
    <b>{escape(str(city.get('name') or ''))}</b><br>
    {escape(str(city.get('country') or ''))}<br>
    Type: {record_type}<br>
    {region_line}
    Population: {population_label(city)}<br>
    Climate: {escape(climate)}<br>
    Climate group: {escape(climate_group(city))}<br>
    Climate source: {source_link}<br>
    Source priority: {escape(priority)}<br>
    Source license: {source_license} {history_link}<br>
    Status: {escape(str(status))}<br>
    <a href="{escape(str(url))}" target="_blank">City Wikipedia page</a><br>
    {table}
    """


def build_city_map(
    cities: list[dict[str, Any]], selected_qid: str | None = None,
    same_climate_only: bool = False, climate_zones: dict[str, Any] | None = None,
    show_climate_zones: bool = True,
) -> folium.Map:
    """Build the local-data Folium map with zones behind capital markers."""
    valid = [c for c in cities if c.get("latitude") is not None and c.get("longitude") is not None]
    center = [20, 0] if not valid else [pd.Series([c["latitude"] for c in valid]).mean(), pd.Series([c["longitude"] for c in valid]).mean()]
    tile_provider = get_tile_provider()
    fmap = folium.Map(location=center, zoom_start=2, tiles=None)
    folium.TileLayer(tiles=tile_provider.tiles, attr=tile_provider.attribution,
                     name=tile_provider.name.replace("_", " ").title(), overlay=False, control=False).add_to(fmap)

    if climate_zones and climate_zones.get("features"):
        zone_layer = folium.FeatureGroup(name="Broad climate zones", overlay=True, show=show_climate_zones)
        folium.GeoJson(
            climate_zones, name="Broad climate zones",
            style_function=lambda feature: {
                "fillColor": CLIMATE_COLORS.get(feature.get("properties", {}).get("climate_group"), CLIMATE_COLORS["Unknown"]),
                "color": "#4b5563", "weight": 0.45, "fillOpacity": 0.16,
            },
            tooltip=folium.GeoJsonTooltip(fields=["name", "climate_group"], aliases=["Zone", "Broad climate group"]),
        ).add_to(zone_layer)
        zone_layer.add_to(fmap)

    national_layer = folium.FeatureGroup(name="National capitals", overlay=True, show=True).add_to(fmap)
    regional_layer = folium.FeatureGroup(name="Regional capitals", overlay=True, show=True).add_to(fmap)
    fmap.get_root().html.add_child(Element(climate_legend_html()))
    selected = next((c for c in valid if marker_id(c) == selected_qid), None)
    selected_class = classification_value(selected) if selected else None

    for city in valid:
        climate = classification_value(city)
        hidden = bool(same_climate_only and selected_class and climate != selected_class)
        is_national = city.get("record_type", "national_capital") == "national_capital"
        radius = (6 if is_national else 3.5) + (3 if marker_id(city) == selected_qid else 0)
        opacity = 0.12 if hidden else (0.95 if is_national else 0.78)
        color = CLIMATE_COLORS[climate_group(city)]
        source_name, priority, _ = climate_source(city)
        region = f" | {city.get('administrative_region')}" if city.get("administrative_region") else ""
        folium.CircleMarker(
            location=[city["latitude"], city["longitude"]], radius=radius, color="#111827" if is_national else color,
            weight=2.2 if is_national else 1.2, fill=True, fill_color=color, fill_opacity=opacity, opacity=opacity,
            tooltip=(f"{city.get('name')}, {city.get('country')}{region} | "
                     f"{'national' if is_national else 'regional'} capital | {climate} | source: {source_name} ({priority})"),
            popup=folium.Popup(_popup_html(city), max_width=900),
        ).add_to(national_layer if is_national else regional_layer)
    folium.LayerControl(collapsed=True).add_to(fmap)
    return fmap
