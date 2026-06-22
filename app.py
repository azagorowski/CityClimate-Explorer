"""Streamlit application for exploring city climate classifications and tables."""
from __future__ import annotations

import hashlib
import logging
from collections.abc import Mapping, MutableMapping
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.capitals import SUPPORTED_CONTINENTS
from src.annual_values import populate_annual_values
from src.locations import load_all_capitals, load_climate_zones, load_country_boundaries, load_koppen_climate_zones
from src.config import (
    APP_NAME,
    CAPITAL_CLIMATE_CACHE,
    WIKIDATA_LICENSE_URL,
    WIKIPEDIA_LICENSE_URL,
    get_tile_provider,
)
from src.map_view import (
    CLIMATE_LAYER_MODES, build_city_map, classification_value,
    clicked_marker_id, legend_entries, marker_id,
)
from src.monthly_metrics import (
    METRIC_OPTIONS,
    format_overlay_value,
    get_metric_overlay_targets,
    load_monthly_metrics_cache,
    make_country_key,
    overlay_diagnostics,
    overlay_values,
)
from src.temperature import UNAVAILABLE_MESSAGE, normalize_monthly_temperature, temperature_chart_rows
from src.wikipedia import enrich_city_climate

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
LOGGER = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def load_capitals_dataset(cache_version: str) -> list[dict[str, Any]]:
    """Load capitals locally; cache version tracks the exact bundled cache contents."""
    del cache_version
    return load_all_capitals()


@st.cache_data(show_spinner=False)
def load_city_details(city: dict[str, Any]) -> dict[str, Any]:
    """Load optional monthly details without affecting startup classification."""
    return enrich_city_climate(city, force_refresh=False)


def merge_capital_details(capital: dict[str, Any], details: dict[str, Any]) -> dict[str, Any]:
    """Merge monthly details while preserving the authoritative startup climate."""
    merged = dict(details)
    for field in (
        "climate_classification", "climate_classification_label", "climate_group",
        "primary_koppen_code", "secondary_koppen_codes", "climate_source_excerpt",
        "climate_classification_source", "climate_classification_source_metadata",
        "climate_source_name", "climate_source_language", "climate_source_title",
        "climate_source_url", "climate_source_priority", "climate_extraction_status",
        "classification_source_priority",
    ):
        merged[field] = capital.get(field)
    return merged


def climate_dataframe(city: dict[str, Any]) -> pd.DataFrame:
    """Return climate records with stable metric and calendar-month ordering."""
    columns = [
        "metric_name", "unit", "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec", "annual",
    ]
    frame = pd.DataFrame(populate_annual_values(city.get("climate_data", [])))
    if frame.empty:
        return frame
    return frame.reindex(columns=columns).rename(columns={
        "metric_name": "Metric", "unit": "Unit", "jan": "Jan", "feb": "Feb",
        "mar": "Mar", "apr": "Apr", "may": "May", "jun": "Jun", "jul": "Jul",
        "aug": "Aug", "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec",
        "annual": "Annual",
    })


def annual_temperature_dataframe(city: dict[str, Any]) -> pd.DataFrame:
    """Return ordered Jan-Dec temperature values for charting only real parsed data."""
    return pd.DataFrame(temperature_chart_rows(city.get("climate_data", [])))


def render_annual_temperature_chart(city: dict[str, Any]) -> None:
    """Render selected-city annual temperature chart or a friendly unavailable message."""
    normalized = normalize_monthly_temperature(city.get("climate_data", []))
    if not normalized:
        st.info(UNAVAILABLE_MESSAGE)
        return
    chart_data = annual_temperature_dataframe(city)
    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True, color="#60a5fa")
        .encode(
            x=alt.X("Month:N", sort=list(chart_data["Month"]), title="Month"),
            y=alt.Y("Temperature (°C):Q", title="Temperature (°C)", scale=alt.Scale(zero=False)),
            tooltip=["Month:N", alt.Tooltip("Temperature (°C):Q", title="Temperature (°C)", format=".1f")],
        )
        .properties(title=f"Monthly average temperature in {city.get('name') or 'selected city'}", height=220)
        .configure_axis(labelColor="#e5e7eb", titleColor="#e5e7eb", gridColor="#374151")
        .configure_title(color="#f9fafb")
        .configure_view(strokeOpacity=0)
    )
    st.altair_chart(chart, width="stretch")
    st.caption(
        f"Chart source: {normalized['source_row_used']} row from climate table "
        f"({normalized['method']}); annual summary columns are not plotted."
    )


def render_source_metadata(label: str, metadata: dict[str, Any]) -> None:
    """Render complete provenance for a displayed classification or table."""
    if not metadata:
        return
    source_name = metadata.get("source_name") or "Source"
    page_title = metadata.get("source_page_title") or source_name
    source_url = metadata.get("source_url")
    source_text = f"[{page_title}]({source_url})" if source_url else str(page_title)
    st.markdown(
        f"**{label}:** {source_name} · {source_text} · language: "
        f"`{metadata.get('source_language') or 'not applicable'}` · priority: "
        f"`{metadata.get('source_priority') or metadata.get('source_role') or 'unavailable'}`"
    )
    details = []
    if metadata.get("retrieved_at"):
        details.append(f"retrieved: {metadata['retrieved_at']}")
    if metadata.get("license"):
        license_label = metadata["license"]
        license_url = metadata.get("license_url")
        details.append(f"license: [{license_label}]({license_url})" if license_url else f"license: {license_label}")
    if metadata.get("contributors_url"):
        details.append(f"[page history / contributors]({metadata['contributors_url']})")
    if metadata.get("source_note"):
        details.append(f"selection note: {metadata['source_note']}")
    if details:
        st.caption(" · ".join(details))


def update_selected_country_state(
    selected_city: MutableMapping[str, Any] | dict[str, Any] | None,
    session_state: MutableMapping[str, Any],
) -> None:
    """Persist selected-country identity derived from the selected city."""
    if not selected_city:
        session_state["selected_country_key"] = None
        session_state["selected_country_name"] = None
        return
    session_state["selected_country_key"] = make_country_key(selected_city)
    session_state["selected_country_name"] = selected_city.get("country")


def update_selected_city_from_map(
    map_state: dict[str, Any] | None, available_city_ids: set[str],
    session_state: MutableMapping[str, Any], city_by_id: Mapping[str, dict[str, Any]] | None = None,
) -> bool:
    """Synchronize a valid marker click into the shared selected-city and country state."""
    clicked_id = clicked_marker_id(map_state)
    if not clicked_id or clicked_id not in available_city_ids:
        return False
    changed = session_state.get("selected_city_id") != clicked_id
    session_state["selected_city_id"] = clicked_id
    if city_by_id is not None:
        update_selected_country_state(city_by_id.get(clicked_id), session_state)
    return changed


def _dropdown_selection_changed() -> None:
    """Use the dropdown as an alternative writer to the shared selection state."""
    st.session_state.selected_city_id = st.session_state.get("capital_selector")


def _city_option_label(city: dict[str, Any]) -> str:
    region = f" — {city['administrative_region']}" if city.get("administrative_region") else ""
    aliases = [alias for alias in city.get("aliases", []) if alias]
    alias_text = f" · also: {', '.join(aliases)}" if aliases else ""
    return f"{city.get('name')} — {city.get('country')}{region} ({classification_value(city)}){alias_text}"


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)
    st.caption("Fast-start map of world and regional capitals with locally preloaded climate classifications.")

    preloaded_dir = CAPITAL_CLIMATE_CACHE.parent / "preloaded"
    regional_paths = [
        preloaded_dir / "regional_capitals_top90_countries.json",
        preloaded_dir / "top_90_countries_by_area.json",
        preloaded_dir / "regional_capitals_polar_border.json",
        preloaded_dir / "regional_capitals_priority_countries.json",
        preloaded_dir / "country_boundaries_simplified.geojson",
        preloaded_dir / "climate_classification_overrides.json",
    ]
    cache_bytes = CAPITAL_CLIMATE_CACHE.read_bytes() + b"".join(path.read_bytes() for path in regional_paths)
    cache_version = hashlib.sha256(cache_bytes).hexdigest()
    capitals = load_capitals_dataset(cache_version)
    zones = load_climate_zones()
    koppen_zones = load_koppen_climate_zones()
    country_boundaries = load_country_boundaries()
    st.info("Showing locally preloaded world national capitals, top-90 and curated priority-country regional capitals, and polar-border administrative capitals. Startup and climate-layer toggling make no Wikimedia requests.")

    with st.sidebar:
        st.header("Filter capitals")
        show_national = st.checkbox("Show national capitals", value=True)
        show_regional = st.checkbox("Show regional capitals (top 90 + curated priority countries)", value=True)
        show_polar = st.checkbox("Show polar-border regional/local capitals", value=True)
        scope_labels = {
            "world_national_capital": "World national capitals",
            "top15_country_regional_capital": "Top-15 country regional capitals (legacy)",
            "top90_country_regional_capital": "Top-90 country regional capitals",
            "polar_border_regional_capital": "Polar-border regional/local capitals",
            "priority_country_regional_capital": "Curated priority-country regional capitals",
        }
        available_scopes = sorted({str(city.get("record_scope")) for city in capitals if city.get("record_scope")})
        scope_filter = st.multiselect("Filter by record scope", available_scopes, format_func=lambda value: scope_labels.get(value, value))
        climate_zone_mode = st.radio(
            "Climate zone layer", CLIMATE_LAYER_MODES, index=1,
            help="Choose no polygons, schematic broad groups, or locally precomputed simplified Köppen types.",
        )
        capital_type = st.radio("Capital type", ["Both", "National", "Regional"], horizontal=True)
        continent_filter = st.multiselect("Filter capitals by continent", list(SUPPORTED_CONTINENTS))
        countries = sorted({str(city["country"]) for city in capitals if city.get("country")})
        country_filter = st.multiselect("Filter capitals by country", countries)
        climates = sorted({classification_value(city) for city in capitals})
        climate_filter = st.multiselect("Filter capitals by climate classification", climates)
        st.subheader("Monthly map metric overlay")
        show_metric_labels = st.toggle("Show metric labels", value=False)
        metric_key = st.selectbox(
            "Metric", list(METRIC_OPTIONS),
            format_func=lambda value: METRIC_OPTIONS[value][0],
            disabled=not show_metric_labels,
        )
        month_label = st.selectbox(
            "Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
            disabled=not show_metric_labels,
        )
        st.caption(
            "Labels use bundled local cache only. With a selected city, labels are scoped to all visible "
            "markers in that city’s country; before selection, all visible markers are eligible. "
            "Missing values are omitted."
        )
        st.subheader("Climate legend")
        for label, color in legend_entries(climate_zone_mode, koppen_zones):
            st.markdown(
                f'<span style="display:inline-block;width:12px;height:12px;border:1px solid #374151;border-radius:3px;background:{color};margin-right:8px"></span>{label}',
                unsafe_allow_html=True,
            )
        if climate_zone_mode == "None":
            st.caption("No zone polygons are shown; legend colors still describe capital markers.")
        elif climate_zone_mode == "Broad groups":
            st.caption("Semi-transparent schematic broad-group polygons are shown behind markers.")
        else:
            st.caption("Grouped A/B/C/D/E/H legend for the simplified detailed Köppen polygons.")
        st.markdown("**Marker meaning**")
        st.markdown("◉ **National capital** — larger, dark outline")
        st.markdown("● **Regional capital** — smaller, climate-colored outline")
        st.markdown("· **Local administrative center** — smallest, thin outline")
        st.divider()
        st.subheader("Data sources and licenses")
        st.markdown(f"- [Wikipedia climate content]({WIKIPEDIA_LICENSE_URL}): CC BY-SA 4.0")
        st.markdown(f"- [Wikidata metadata]({WIKIDATA_LICENSE_URL}): CC0 1.0")
        st.markdown("- Regional-capital snapshot: Wikidata-compatible metadata (CC0) with linked Wikipedia review sources (CC BY-SA 4.0)")
        st.markdown("- Broad climate layer: project-authored generalized GeoJSON (MIT)")
        st.markdown("- Detailed Köppen layer: Beck et al. (2018), CC BY 4.0; locally generalized for display")
        tile_provider = get_tile_provider()
        st.caption(f"Map tiles: {tile_provider.name}; provider attribution is displayed on the map.")
        st.caption("Software dependency notices: THIRD_PARTY_NOTICES.md in the application repository.")

    filtered = capitals
    if not show_national or capital_type == "Regional":
        filtered = [city for city in filtered if city.get("record_type") != "national_capital"]
    if not show_regional:
        filtered = [city for city in filtered if city.get("record_scope") not in {
            "top90_country_regional_capital", "priority_country_regional_capital",
        }]
    if not show_polar:
        filtered = [city for city in filtered if city.get("record_scope") != "polar_border_regional_capital"]
    if capital_type == "National":
        filtered = [city for city in filtered if city.get("record_type") == "national_capital"]
    if scope_filter:
        filtered = [city for city in filtered if city.get("record_scope") in scope_filter]
    if continent_filter:
        filtered = [city for city in filtered if (city.get("continent") or city.get("region")) in continent_filter]
    if country_filter:
        filtered = [city for city in filtered if city.get("country") in country_filter]
    if climate_filter:
        filtered = [city for city in filtered if classification_value(city) in climate_filter]

    all_cities_by_id = {marker_id(city): city for city in capitals}
    city_by_id = {marker_id(city): city for city in filtered}
    available_city_ids = set(city_by_id)
    st.session_state.setdefault("selected_city_id", None)
    selection_filtered_out = bool(st.session_state.selected_city_id and st.session_state.selected_city_id not in available_city_ids)
    selected_id = st.session_state.selected_city_id
    if selection_filtered_out and selected_id in all_cities_by_id:
        selected_record = all_cities_by_id[selected_id]
        filtered = [*filtered, selected_record]
        city_by_id[selected_id] = selected_record
        available_city_ids.add(selected_id)
    selector_options: list[str | None] = [None, *city_by_id]
    if st.session_state.get("capital_selector") != selected_id:
        st.session_state.capital_selector = selected_id

    selected_id = st.session_state.selected_city_id
    selected_city = city_by_id.get(selected_id) if selected_id else None
    update_selected_country_state(selected_city, st.session_state)
    if not selected_city:
        st.session_state.same_climate_only = False

    col_map, col_details = st.columns([2.15, 1], gap="large")
    with col_details:
        st.selectbox(
            "Select a capital or regional capital", selector_options, key="capital_selector",
            format_func=lambda value: "None" if value is None else _city_option_label(city_by_id[value]),
            on_change=_dropdown_selection_changed,
        )
        st.subheader("Capital details")
        if selection_filtered_out:
            st.warning("The selected capital is outside the active filters, so its highlighted marker remains visible.")
        same_climate = st.toggle(
            "Show capitals with the same climate classification", value=False,
            disabled=not selected_city, key="same_climate_only",
        )

    # Map-first phase: create marker map and optional overlays from already-local
    # data before loading selected-city details or any other optional table work.
    table_cache: dict[str, Any] = dict(st.session_state.get("climate_table_cache", {}))
    selected_country_key = st.session_state.get("selected_country_key")
    selected_country_name = st.session_state.get("selected_country_name")
    overlay_target_cities = get_metric_overlay_targets(filtered, selected_country_key)
    raw_overlay_values: dict[str, tuple[float, str]] = {}
    missing_data_count = 0
    missing_reasons: dict[str, int] = {}
    if show_metric_labels:
        try:
            monthly_metrics = load_monthly_metrics_cache()
            raw_overlay_values = overlay_values(overlay_target_cities, metric_key, month_label, monthly_metrics, table_cache)
            diagnostics = overlay_diagnostics(overlay_target_cities, metric_key, month_label, monthly_metrics, table_cache)
            missing_data_count = max(len(overlay_target_cities) - len(raw_overlay_values), 0)
            missing_reasons = diagnostics.missing_reasons
        except Exception:  # noqa: BLE001 - labels are optional; never block the base map
            LOGGER.warning("Monthly metric overlay failed; rendering map without labels", exc_info=True)
            raw_overlay_values = {}
            missing_data_count = len(overlay_target_cities)
            missing_reasons = {"overlay exception": missing_data_count}
    metric_labels = {
        city_id: label
        for city_id, (value, unit) in raw_overlay_values.items()
        if (label := format_overlay_value(value, unit))
    }
    LOGGER.info(
        "Metric overlay country=%s visible=%d targets=%d labels=%d missing=%d metric=%s month=%s reasons=%s selected_city_id=%s",
        selected_country_name or "all",
        len(filtered), len(overlay_target_cities), len(metric_labels), missing_data_count,
        metric_key, month_label, missing_reasons, selected_id,
    )
    if same_climate and selected_city:
        with col_map:
            st.info(f"Highlighting capitals with classification: {classification_value(selected_city)}")

    with col_map:
        filter_key = hashlib.sha256("|".join(sorted(available_city_ids)).encode()).hexdigest()[:10]
        map_state = st_folium(
            build_city_map(
                filtered, selected_id, same_climate, zones, climate_zone_mode, koppen_zones,
                country_boundaries, selected_city,
                metric_labels,
            ),
            key=f"capital-map-{selected_id or 'none'}-{climate_zone_mode}-{metric_key}-{month_label}-{show_metric_labels}-{filter_key}",
            returned_objects=["last_object_clicked_popup", "last_object_clicked_tooltip"],
            width=None, height=650,
        )
        layer_description = {
            "None": "Climate-zone polygons are hidden.",
            "Broad groups": "Showing lightweight generalized broad-climate groups.",
            "Köppen types": "Showing locally precomputed simplified Köppen climate types (CC BY 4.0 source).",
        }[climate_zone_mode]
        st.caption(f"{layer_description} Marker colors always represent broad climate groups; click a marker to open its details in the right panel.")
    if update_selected_city_from_map(map_state, available_city_ids, st.session_state, city_by_id):
        st.rerun()

    # Optional details phase: load and display the selected city's climate table
    # after the base map has already been rendered for this rerun.
    detailed_city = selected_city
    with col_details:
        if selected_city:
            try:
                with st.spinner("Loading selected capital's detailed Wikipedia climate table..."):
                    parsed_details = load_city_details(selected_city)
                detailed_city = merge_capital_details(selected_city, parsed_details)
                if detailed_city.get("climate_data"):
                    st.session_state.setdefault("climate_table_cache", {})[marker_id(selected_city)] = {
                        **selected_city,
                        "climate_data": detailed_city.get("climate_data", []),
                    }
            except Exception:  # noqa: BLE001 - details are optional; keep map usable
                LOGGER.warning("Could not enrich selected capital %s", selected_city.get("qid"), exc_info=True)
                st.warning("Climate table details could not be loaded right now; showing preloaded metadata.")
                detailed_city = selected_city
        if not detailed_city:
            st.write("Click a map marker or use the dropdown to inspect its climate classification and monthly table.")
        else:
            st.write(f"**{detailed_city.get('name')}, {detailed_city.get('country')}**")
            st.write(f"**Region / continent:** {detailed_city.get('continent') or detailed_city.get('region') or 'not specified'}")
            capital_label = {
                "national_capital": "National capital", "regional_capital": "Regional capital",
                "local_administrative_center": "Local administrative center",
            }.get(detailed_city.get("record_type"), "Regional capital")
            st.write(f"**Capital type:** {capital_label}")
            st.write(f"**Record scope:** `{detailed_city.get('record_scope') or 'not specified'}`")
            if detailed_city.get("administrative_region"):
                st.write(f"**Administrative region:** {detailed_city['administrative_region']} ({detailed_city.get('administrative_region_type') or 'first-level division'})")
            population = detailed_city.get("population")
            if isinstance(population, int | float):
                st.write(f"**Population:** {population:,.0f}")
            st.write(f"**Climate classification:** {classification_value(detailed_city)}")
            st.write(f"**Climate group:** {detailed_city.get('climate_group') or 'Unknown'}")
            st.write(f"**Primary Köppen code:** `{detailed_city.get('primary_koppen_code') or 'not detected'}`")
            secondary_codes = detailed_city.get("secondary_koppen_codes") or []
            if secondary_codes:
                st.write(f"**Secondary/bordering codes:** `{', '.join(secondary_codes)}`")
            if detailed_city.get("climate_source_excerpt"):
                st.caption(f"Parsed climate note: {detailed_city['climate_source_excerpt']}")
            st.write(f"**Extraction status:** {detailed_city.get('extraction_status', 'unavailable')}")
            render_source_metadata("Classification source", detailed_city.get("climate_classification_source_metadata") or {})
            table_metadata = detailed_city.get("climate_table_source_metadata") or {}
            if table_metadata:
                render_source_metadata("Climate table source", table_metadata)
            render_annual_temperature_chart(detailed_city)
            df = climate_dataframe(detailed_city)
            if df.empty:
                st.info("No supported monthly climate table is cached for this capital.")
            else:
                st.dataframe(df, hide_index=True, width="stretch")
                st.caption("Annual values are calculated from Jan–Dec monthly data when not provided by the source.")

    national_count = sum(city.get("record_type") == "national_capital" for city in capitals)
    regional_count = sum(city.get("record_type") != "national_capital" for city in capitals)
    st.caption(f"Loaded {national_count:,} national and {regional_count:,} deduplicated regional/local capitals; displaying {len(filtered):,} after filters.")
    st.caption(
        "Data attribution: locally cached Wikipedia climate classifications and on-demand climate content are available "
        "under CC BY-SA 4.0; Wikidata structured metadata is CC0 1.0; the detailed Köppen layer is derived from "
        "Beck et al. (2018) under CC BY 4.0. Source pages are retained per record."
    )


if __name__ == "__main__":
    main()
