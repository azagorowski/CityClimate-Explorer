"""Folium map construction for CityClimate Explorer."""
from __future__ import annotations

import hashlib
from typing import Any

import folium
import pandas as pd

DEFAULT_COLOR = "#6b7280"


def classification_value(city: dict[str, Any]) -> str:
    """Return a displayable climate classification value."""
    return city.get("climate_classification_label") or city.get("climate_classification") or "Unknown"


def color_for_classification(value: str | None) -> str:
    """Assign a stable marker color for a classification label."""
    if not value or value == "Unknown":
        return DEFAULT_COLOR
    digest = hashlib.md5(value.encode("utf-8")).hexdigest()  # stable UI color, not security-sensitive
    hue = int(digest[:2], 16) / 255 * 360
    return f"hsl({hue:.0f}, 70%, 45%)"


def marker_id(city: dict[str, Any]) -> str:
    """Return a stable marker id for QID and local-only records."""
    qid = str(city.get("qid") or "").strip()
    if qid:
        return qid
    return str(city.get("marker_id") or f"local:{str(city.get('country') or '').casefold()}:{str(city.get('name') or '').casefold()}")


def population_label(city: dict[str, Any]) -> str:
    population = city.get("population")
    return f"{population:,}" if isinstance(population, int | float) else "unavailable"


def _popup_html(city: dict[str, Any]) -> str:
    url = city.get("wikipedia_url") or "#"
    climate = classification_value(city)
    status = city.get("extraction_status", "not parsed")
    rows = "".join(
        f"<tr><td>{metric.get('metric_name')}</td><td>{metric.get('unit') or ''}</td>"
        + "".join(f"<td>{metric.get(month) if metric.get(month) is not None else ''}</td>" for month in ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])
        + "</tr>"
        for metric in city.get("climate_data", [])[:6]
    )
    table = "<p>No parsed climate table is available.</p>"
    if rows:
        table = "<table border='1' style='border-collapse:collapse;font-size:11px'><tr><th>Metric</th><th>Unit</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th></tr>" + rows + "</table>"
    return f"""
    <b>{city.get('name')}</b><br>
    {city.get('country')}<br>
    Population: {population_label(city)}<br>
    Climate: {climate}<br>
    Status: {status}<br>
    <a href="{url}" target="_blank">Wikipedia source</a><br>
    {table}
    """


def build_city_map(
    cities: list[dict[str, Any]],
    selected_qid: str | None = None,
    same_climate_only: bool = False,
) -> folium.Map:
    """Build an interactive Folium map for city climate records."""
    valid = [c for c in cities if c.get("latitude") is not None and c.get("longitude") is not None]
    center = [20, 0] if not valid else [pd.Series([c["latitude"] for c in valid]).mean(), pd.Series([c["longitude"] for c in valid]).mean()]
    fmap = folium.Map(location=center, zoom_start=2, tiles="cartodbpositron")
    selected = next((c for c in valid if marker_id(c) == selected_qid), None)
    selected_class = classification_value(selected) if selected else None

    for city in valid:
        climate = classification_value(city)
        hidden_by_same_filter = same_climate_only and selected_class and climate != selected_class
        radius = 7 if marker_id(city) == selected_qid else 4
        opacity = 0.15 if hidden_by_same_filter else 0.85
        folium.CircleMarker(
            location=[city["latitude"], city["longitude"]],
            radius=radius,
            color=color_for_classification(climate),
            fill=True,
            fill_color=color_for_classification(climate),
            fill_opacity=opacity,
            opacity=opacity,
            tooltip=f"{city.get('name')}, {city.get('country')} | pop. {population_label(city)} | {climate}",
            popup=folium.Popup(_popup_html(city), max_width=900),
        ).add_to(fmap)
    return fmap
