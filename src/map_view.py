"""Folium map construction for CityClimate Explorer."""
from __future__ import annotations

from html import escape
import re
from typing import Any, Mapping
from urllib.parse import quote, unquote

import folium
import pandas as pd
from branca.element import Element

from .capitals import city_marker_id
from .climate_parser import koppen_climate_group
from .config import get_tile_provider
from .monthly_metrics import make_country_key

CLIMATE_LAYER_MODES = ("None", "Broad groups", "Köppen types")
CLIMATE_COLORS = {
    "Tropical": "#16a34a",
    "Dry / Arid": "#d97706",
    "Temperate": "#2563eb",
    "Continental": "#7c3aed",
    "Polar": "#06b6d4",
    "Highland / Mountain": "#92400e",
    "Unknown": "#6b7280",
}
KOPPEN_CLASS_COLORS = {
    "A": "#15803d",
    "B": "#d97706",
    "C": "#2563eb",
    "D": "#7c3aed",
    "E": "#0891b2",
    "H": "#92400e",
}
KOPPEN_CLASS_LABELS = {
    "A": "A — Tropical (Af, Am, Aw)",
    "B": "B — Dry (BWh, BWk, BSh, BSk)",
    "C": "C — Temperate (Cfa, Cfb, Csa, Cwa)",
    "D": "D — Continental (Dfa, Dfb, Dfc, Dwa)",
    "E": "E — Polar (ET, EF)",
    "H": "H — Highland / mountain",
}
_MARKER_TOKEN_RE = re.compile(r"cityclimate://city/([A-Za-z0-9._~%:-]+)")


def classification_value(city: dict[str, Any] | None) -> str:
    """Return a displayable climate classification value."""
    if not city:
        return "Unknown"
    return str(city.get("climate_classification_label") or city.get("climate_classification") or "Unknown")


def climate_category(value: str | None, code: str | None = None) -> str:
    """Map a classification to a broad group, honoring explicit highland labels."""
    text = (value or "").casefold().strip()
    if not text or text == "unknown":
        return "Unknown"
    # Elevation-based highland descriptions are more specific than the thermal
    # Köppen letter (often Cfb/Cwb), so they must win over code-only grouping.
    if any(token in text for token in ("highland", "mountain", "alpine")):
        return "Highland / Mountain"
    primary_group = koppen_climate_group(code)
    if primary_group:
        return primary_group
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
    codes = re.findall(r"\b(?:A[fmsw]|B[WS][hk]|C[fsw][abc]|D[fsw][abcd]|E[TF])\b", value or "", re.I)
    return koppen_climate_group(codes[0]) or "Unknown" if codes else "Unknown"


def climate_group(city: dict[str, Any] | None) -> str:
    """Return the authoritative cached group, deriving it for legacy records."""
    if not city:
        return "Unknown"
    cached = str(city.get("climate_group") or "").strip()
    if cached in CLIMATE_COLORS:
        return cached
    return climate_category(classification_value(city), str(city.get("primary_koppen_code") or city.get("climate_classification") or ""))


def color_for_classification(value: str | None) -> str:
    """Return the documented broad-category marker color."""
    return CLIMATE_COLORS[climate_category(value)]


def legend_entries(layer_mode: str, detailed_zones: dict[str, Any] | None = None) -> list[tuple[str, str]]:
    """Return legend labels and colors for the selected climate-zone mode."""
    if layer_mode != "Köppen types":
        return list(CLIMATE_COLORS.items())
    present = {
        str(feature.get("properties", {}).get("koppen_code") or "")[:1].upper()
        for feature in (detailed_zones or {}).get("features", [])
    }
    return [(KOPPEN_CLASS_LABELS[key], color) for key, color in KOPPEN_CLASS_COLORS.items() if key in present]


def climate_legend_html(layer_mode: str = "Broad groups", detailed_zones: dict[str, Any] | None = None) -> str:
    """Return a readable map legend matching the active climate-zone mode."""
    entries = legend_entries(layer_mode, detailed_zones)
    items = "".join(
        f'<div class="map-legend-item" style="margin:4px 0"><span style="display:inline-block;width:12px;height:12px;'
        f'border-radius:3px;background:{color};margin-right:7px;border:1px solid #374151;opacity:.78"></span>{escape(label)}</div>'
        for label, color in entries
    )
    title = {
        "None": "Capital marker climate groups",
        "Broad groups": "Broad climate groups",
        "Köppen types": "Detailed Köppen classes",
    }.get(layer_mode, "Climate legend")
    symbols = (
        '<div style="margin-top:8px;border-top:1px solid #d1d5db;padding-top:6px"><strong>Capital markers</strong>'
        '<div style="margin:4px 0"><span style="display:inline-block;width:13px;height:13px;border-radius:50%;background:#fff;border:3px solid #374151;margin-right:7px"></span>National capital</div>'
        '<div style="margin:4px 0"><span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:#fff;border:2px solid #374151;margin:0 9px 0 2px"></span>Regional capital</div>'
        '<div style="margin:4px 0"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:#fff;border:1px solid #374151;margin:0 11px 0 3px"></span>Local administrative center</div></div>'
    )
    return (
        '<div id="climate-legend" class="map-legend" style="position:fixed;bottom:28px;left:28px;z-index:9999;'
        'background:rgba(255,255,255,.96);color:#111827;padding:12px 14px;border:1px solid #9ca3af;border-radius:8px;'
        'box-shadow:0 2px 8px rgba(0,0,0,.28);font:13px/1.3 Arial,sans-serif;opacity:1;max-height:360px;overflow:auto">'
        '<style>.map-legend,.map-legend *{color:#111827 !important}.map-legend-item{white-space:nowrap}</style>'
        f'<strong>{escape(title)}</strong>{items}{symbols}</div>'
    )


def marker_id(city: dict[str, Any]) -> str:
    """Return the QID-first, normalized stable identifier used by every selector."""
    return str(city.get("marker_id") or city_marker_id(city))


def marker_click_token(city: dict[str, Any]) -> str:
    """Return an unambiguous machine token embedded in popup and tooltip HTML."""
    return f"cityclimate://city/{quote(marker_id(city), safe='')}"


def clicked_marker_id(map_state: Mapping[str, Any] | None) -> str | None:
    """Extract a stable city ID from streamlit-folium click output."""
    if not map_state:
        return None
    for field in ("last_object_clicked_popup", "last_object_clicked_tooltip"):
        content = map_state.get(field)
        if not isinstance(content, str):
            continue
        match = _MARKER_TOKEN_RE.search(content)
        if match:
            return unquote(match.group(1))
    return None


def population_label(city: dict[str, Any]) -> str:
    population = city.get("population")
    return f"{population:,.0f}" if isinstance(population, int | float) else "unavailable"


def climate_source(city: dict[str, Any]) -> tuple[str, str, str | None]:
    metadata = city.get("climate_classification_source_metadata") or city.get("climate_source_metadata") or {}
    name = str(metadata.get("source_name") or "Local cache")
    priority = str(metadata.get("source_priority") or metadata.get("source_role") or "unavailable")
    return name, priority, metadata.get("source_url")


def _popup_html(city: dict[str, Any]) -> str:
    climate = classification_value(city)
    source_name, priority, source_url = climate_source(city)
    source_link = escape(source_name)
    if source_url:
        source_link = f'<a href="{escape(str(source_url))}" target="_blank">{source_link}</a>'
    type_labels = {
        "national_capital": "National capital",
        "regional_capital": "Regional capital",
        "local_administrative_center": "Local administrative center",
    }
    record_type = type_labels.get(str(city.get("record_type")), "Regional capital")
    primary_code = str(city.get("primary_koppen_code") or "not detected")
    secondary_codes = ", ".join(city.get("secondary_koppen_codes") or []) or "none"
    token = marker_click_token(city)
    return f"""
    <span data-city-id="{escape(marker_id(city))}" style="display:none">{token}</span>
    <b>{escape(str(city.get('name') or ''))}</b> — {escape(str(city.get('country') or ''))}<br>
    {escape(record_type)}<br>
    Climate: {escape(climate)}<br>
    Primary Köppen code: {escape(primary_code)}<br>
    Secondary/bordering codes: {escape(secondary_codes)}<br>
    Broad group: {escape(climate_group(city))}<br>
    Population: {population_label(city)}<br>
    Source: {source_link} ({escape(priority)})<br>
    <strong>Click marker to view climate details.</strong>
    """


def _tooltip_html(city: dict[str, Any]) -> str:
    token = marker_click_token(city)
    code = city.get("primary_koppen_code") or "code unavailable"
    return (
        f"<strong>{escape(str(city.get('name') or ''))} — {escape(str(city.get('country') or ''))}</strong><br>"
        f"Climate: {escape(classification_value(city))} ({escape(str(code))})<br>"
        f"Broad group: {escape(climate_group(city))}"
        f'<span style="display:none">{token}</span>'
    )


def _detailed_zone_color(feature: dict[str, Any]) -> str:
    properties = feature.get("properties", {})
    configured = properties.get("color")
    if configured:
        return str(configured)
    climate_class = str(properties.get("koppen_code") or "")[:1].upper()
    return KOPPEN_CLASS_COLORS.get(climate_class, CLIMATE_COLORS["Unknown"])


def build_city_map(
    cities: list[dict[str, Any]], selected_qid: str | None = None,
    same_climate_only: bool = False, climate_zones: dict[str, Any] | None = None,
    climate_zone_mode: str = "Broad groups", detailed_climate_zones: dict[str, Any] | None = None,
    country_boundaries: dict[str, Any] | None = None, selected_city: dict[str, Any] | None = None,
    metric_labels: Mapping[str, str] | None = None,
) -> folium.Map:
    """Build the local-data Folium map with the selected zone layer behind markers."""
    if climate_zone_mode not in CLIMATE_LAYER_MODES:
        raise ValueError(f"Unsupported climate layer mode: {climate_zone_mode}")
    valid = [c for c in cities if c.get("latitude") is not None and c.get("longitude") is not None]
    center = [20, 0] if not valid else [pd.Series([c["latitude"] for c in valid]).mean(), pd.Series([c["longitude"] for c in valid]).mean()]
    tile_provider = get_tile_provider()
    fmap = folium.Map(location=center, zoom_start=2, tiles=None)
    folium.TileLayer(
        tiles=tile_provider.tiles, attr=tile_provider.attribution,
        name=tile_provider.name.replace("_", " ").title(), overlay=False, control=False,
    ).add_to(fmap)

    if climate_zone_mode == "Broad groups" and climate_zones and climate_zones.get("features"):
        zone_layer = folium.FeatureGroup(name="Broad climate zones", overlay=True, show=True)
        folium.GeoJson(
            climate_zones, name="Broad climate zones",
            style_function=lambda feature: {
                "fillColor": CLIMATE_COLORS.get(feature.get("properties", {}).get("climate_group"), CLIMATE_COLORS["Unknown"]),
                "color": "#4b5563", "weight": 0.45, "fillOpacity": 0.16,
            },
            tooltip=folium.GeoJsonTooltip(fields=["name", "climate_group"], aliases=["Zone", "Broad climate group"]),
        ).add_to(zone_layer)
        zone_layer.add_to(fmap)
    elif climate_zone_mode == "Köppen types" and detailed_climate_zones and detailed_climate_zones.get("features"):
        zone_layer = folium.FeatureGroup(name="Detailed Köppen climate types", overlay=True, show=True)
        folium.GeoJson(
            detailed_climate_zones, name="Detailed Köppen climate types",
            style_function=lambda feature: {
                "fillColor": _detailed_zone_color(feature), "color": "#374151",
                "weight": 0.35, "fillOpacity": 0.2,
            },
            tooltip=folium.GeoJsonTooltip(
                fields=["koppen_code", "koppen_name", "climate_group"],
                aliases=["Köppen code", "Climate type", "Broad group"],
            ),
        ).add_to(zone_layer)
        zone_layer.add_to(fmap)

    national_layer = folium.FeatureGroup(name="National capitals", overlay=True, show=True).add_to(fmap)
    regional_layer = folium.FeatureGroup(name="Regional capitals", overlay=True, show=True).add_to(fmap)
    metric_label_layer = folium.FeatureGroup(name="Selected country metric labels", overlay=True, show=True).add_to(fmap)
    fmap.get_root().html.add_child(Element(
        "<style>.city-metric-label-container{z-index:10000!important}"
        ".city-metric-label{position:relative;z-index:10000!important}</style>"
    ))
    fmap.get_root().html.add_child(Element(climate_legend_html(climate_zone_mode, detailed_climate_zones)))
    selected = selected_city or next((c for c in valid if marker_id(c) == selected_qid), None)
    selected_class = classification_value(selected) if selected else None
    selected_boundary = find_country_boundary(selected, country_boundaries)
    if selected_boundary:
        folium.GeoJson(
            selected_boundary, name="Selected country", control=False,
            style_function=lambda _feature: {
                "fillColor": "#f8fafc", "fillOpacity": 0.035, "color": "#f8fafc",
                "weight": 2.2, "opacity": 0.9, "dashArray": "6 4",
            },
        ).add_to(fmap)
        bounds = _geometry_bounds(selected_boundary.get("geometry", {}))
        if bounds:
            fmap.fit_bounds(bounds, padding=(18, 18), max_zoom=6)
    elif selected and selected.get("latitude") is not None and selected.get("longitude") is not None:
        fmap.location = [selected["latitude"], selected["longitude"]]
        fmap.options["zoom"] = 7

    for city in valid:
        climate = classification_value(city)
        hidden = bool(same_climate_only and selected_class and climate != selected_class)
        is_national = city.get("record_type", "national_capital") == "national_capital"
        is_local = city.get("record_type") == "local_administrative_center"
        radius = (6 if is_national else (3 if is_local else 3.8)) + (3 if marker_id(city) == selected_qid else 0)
        opacity = 0.12 if hidden else (0.95 if is_national else 0.78)
        color = CLIMATE_COLORS[climate_group(city)]
        folium.CircleMarker(
            location=[city["latitude"], city["longitude"]], radius=radius,
            color="#111827" if is_national else color,
            weight=2.2 if is_national else (0.9 if is_local else 1.4),
            fill=True, fill_color=color, fill_opacity=opacity, opacity=opacity,
            tooltip=folium.Tooltip(_tooltip_html(city)),
            popup=folium.Popup(_popup_html(city), max_width=360),
        ).add_to(national_layer if is_national else regional_layer)
        label = (metric_labels or {}).get(marker_id(city))
        if label and not hidden:
            folium.Marker(
                [city["latitude"], city["longitude"]],
                icon=folium.DivIcon(
                    icon_anchor=(-8, 7),
                    class_name="city-metric-label-container",
                    html=(
                        '<span class="city-metric-label" style="pointer-events:none;white-space:nowrap;'
                        'background:rgba(255,255,255,.92);color:#111827;border:1px solid #4b5563;'
                        'border-radius:4px;padding:1px 4px;font:600 11px/1.35 Arial,sans-serif;'
                        f'box-shadow:0 1px 3px rgba(0,0,0,.35)">{escape(label)}</span>'
                    ),
                ),
                interactive=False,
                z_index_offset=500,
            ).add_to(metric_label_layer)
    folium.LayerControl(collapsed=True).add_to(fmap)
    return fmap

_COUNTRY_NAME_ALIASES = {
    "united states of america": "united states",
    "usa": "united states",
    "russian federation": "russia",
    "democratic republic of congo": "democratic republic of the congo",
    "dr congo": "democratic republic of the congo",
    "republic of the congo": "congo",
    "czechia": "czech republic",
    "the bahamas": "bahamas",
    "gambia": "the gambia",
    "greenland (denmark)": "greenland",
}


def _country_key(value: Any) -> str:
    return make_country_key({"country": value}) or ""


def find_country_boundary(
    city: dict[str, Any] | None, country_boundaries: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Find a local boundary feature using stable IDs first, then aliases."""
    if not city or not country_boundaries:
        return None
    qid = str(city.get("country_qid") or "").strip()
    iso_values = {
        str(city.get(field) or "").upper().strip()
        for field in ("country_iso_a2", "country_iso_a3", "iso_a2", "iso_a3")
        if city.get(field)
    }
    country_key = _country_key(city.get("country"))
    for feature in country_boundaries.get("features", []):
        properties = feature.get("properties", {})
        if qid and qid == str(properties.get("country_qid") or properties.get("wikidata_qid") or ""):
            return feature
        feature_isos = {
            str(properties.get(field) or "").upper().strip()
            for field in ("iso_a2", "iso_a3", "ISO_A2", "ISO_A3", "ADM0_A3")
            if properties.get(field)
        }
        if iso_values & feature_isos:
            return feature
        names = (properties.get("country"), properties.get("name"), properties.get("ADMIN"), properties.get("SOVEREIGNT"))
        if country_key and country_key in {_country_key(name) for name in names if name}:
            return feature
    return None


def _geometry_bounds(geometry: dict[str, Any]) -> list[list[float]] | None:
    points: list[tuple[float, float]] = []

    def visit(value: Any) -> None:
        if isinstance(value, list) and len(value) >= 2 and all(isinstance(item, int | float) for item in value[:2]):
            points.append((float(value[0]), float(value[1])))
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(geometry.get("coordinates", []))
    if not points:
        return None
    longitudes = [point[0] for point in points]
    latitudes = [point[1] for point in points]
    return [[min(latitudes), min(longitudes)], [max(latitudes), max(longitudes)]]


def country_bounds_for_city(
    city: dict[str, Any] | None, country_boundaries: dict[str, Any] | None,
) -> list[list[float]] | None:
    """Return Leaflet fit-bounds coordinates for a selected city's country."""
    feature = find_country_boundary(city, country_boundaries)
    return _geometry_bounds(feature.get("geometry", {})) if feature else None
