"""Streamlit application for exploring city climate classifications and tables."""
from __future__ import annotations

import hashlib
import logging
from typing import Any

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.capitals import SUPPORTED_CONTINENTS
from src.locations import load_all_capitals, load_climate_zones
from src.config import (
    APP_NAME,
    CAPITAL_CLIMATE_CACHE,
    WIKIDATA_LICENSE_URL,
    WIKIPEDIA_LICENSE_URL,
    get_tile_provider,
)
from src.map_view import CLIMATE_COLORS, build_city_map, classification_value, marker_id
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
    ):
        merged[field] = capital.get(field)
    return merged


def climate_dataframe(city: dict[str, Any]) -> pd.DataFrame:
    """Return climate records with stable metric and calendar-month ordering."""
    columns = [
        "metric_name", "unit", "jan", "feb", "mar", "apr", "may", "jun",
        "jul", "aug", "sep", "oct", "nov", "dec", "annual",
    ]
    frame = pd.DataFrame(city.get("climate_data", []))
    if frame.empty:
        return frame
    return frame.reindex(columns=columns).rename(columns={
        "metric_name": "Metric", "unit": "Unit", "jan": "Jan", "feb": "Feb",
        "mar": "Mar", "apr": "Apr", "may": "May", "jun": "Jun", "jul": "Jul",
        "aug": "Aug", "sep": "Sep", "oct": "Oct", "nov": "Nov", "dec": "Dec",
        "annual": "Annual",
    })


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
    if details:
        st.caption(" · ".join(details))


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)
    st.caption("Fast-start map of world and regional capitals with locally preloaded climate classifications.")

    preloaded_dir = CAPITAL_CLIMATE_CACHE.parent / "preloaded"
    regional_paths = [
        preloaded_dir / "regional_capitals_top15_countries.json",
        preloaded_dir / "regional_capitals_polar_border.json",
    ]
    cache_bytes = CAPITAL_CLIMATE_CACHE.read_bytes() + b"".join(path.read_bytes() for path in regional_paths)
    cache_version = hashlib.sha256(cache_bytes).hexdigest()
    capitals = load_capitals_dataset(cache_version)
    zones = load_climate_zones()
    st.info("Showing locally preloaded world national capitals, top-15-country regional capitals, and polar-border administrative capitals. Startup makes no Wikimedia requests.")

    with st.sidebar:
        st.header("Filter capitals")
        show_national = st.checkbox("Show national capitals", value=True)
        show_regional = st.checkbox("Show regional/local capitals", value=True)
        scope_labels = {
            "world_national_capital": "World national capitals",
            "top15_country_regional_capital": "Top-15 country regional capitals",
            "polar_border_regional_capital": "Polar-border regional/local capitals",
        }
        available_scopes = sorted({str(city.get("record_scope")) for city in capitals if city.get("record_scope")})
        scope_filter = st.multiselect("Filter by record scope", available_scopes, format_func=lambda value: scope_labels.get(value, value))
        show_zones = st.checkbox("Show climate zones", value=True, help="Lightweight schematic broad-climate grouping; not a scientific boundary product.")
        capital_type = st.radio("Capital type", ["Both", "National", "Regional"], horizontal=True)
        continent_filter = st.multiselect("Filter capitals by continent", list(SUPPORTED_CONTINENTS))
        countries = sorted({str(city["country"]) for city in capitals if city.get("country")})
        country_filter = st.multiselect("Filter capitals by country", countries)
        climates = sorted({classification_value(city) for city in capitals})
        climate_filter = st.multiselect("Filter capitals by climate classification", climates)
        st.subheader("Climate legend")
        for label, color in CLIMATE_COLORS.items():
            st.markdown(
                f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{color};margin-right:8px"></span>{label}',
                unsafe_allow_html=True,
            )
        st.markdown("**Marker meaning**")
        st.markdown("◉ **National capital** — larger, dark outline")
        st.markdown("● **Regional capital** — smaller, climate-colored outline")
        st.markdown("· **Local administrative center** — smallest, thin outline")
        st.caption("The same colors are used for semi-transparent climate zones.")
        st.divider()
        st.subheader("Data sources and licenses")
        st.markdown(f"- [Wikipedia climate content]({WIKIPEDIA_LICENSE_URL}): CC BY-SA 4.0")
        st.markdown(f"- [Wikidata metadata]({WIKIDATA_LICENSE_URL}): CC0 1.0")
        st.markdown("- Regional-capital snapshot: Wikidata-compatible metadata (CC0) with linked Wikipedia review sources (CC BY-SA 4.0)")
        st.markdown("- Climate-zone visualization: project-authored generalized GeoJSON (MIT; commercial use permitted)")
        tile_provider = get_tile_provider()
        st.caption(f"Map tiles: {tile_provider.name}; provider attribution is displayed on the map.")
        st.caption("Software dependency notices: THIRD_PARTY_NOTICES.md in the application repository.")

    filtered = capitals
    if not show_national or capital_type == "Regional":
        filtered = [city for city in filtered if city.get("record_type") != "national_capital"]
    if not show_regional or capital_type == "National":
        filtered = [city for city in filtered if city.get("record_type") == "national_capital"]
    if scope_filter:
        filtered = [city for city in filtered if city.get("record_scope") in scope_filter]
    if continent_filter:
        filtered = [city for city in filtered if (city.get("continent") or city.get("region")) in continent_filter]
    if country_filter:
        filtered = [city for city in filtered if city.get("country") in country_filter]
    if climate_filter:
        filtered = [city for city in filtered if classification_value(city) in climate_filter]

    city_options = {f"{city.get('name')} — {city.get('country')} ({classification_value(city)})": marker_id(city) for city in filtered}
    selected_label = st.selectbox("Select a capital", ["None"] + list(city_options))
    selected_qid = city_options.get(selected_label)
    same_climate = st.toggle("Show capitals with the same climate classification", value=False, disabled=not selected_qid)

    selected_city = next((city for city in filtered if marker_id(city) == selected_qid), None)
    detailed_city = selected_city
    if selected_city:
        try:
            with st.spinner("Loading selected capital's detailed Wikipedia climate table..."):
                parsed_details = load_city_details(selected_city)
            # The bundled startup classification is authoritative. On-demand
            # parsing supplies table details only and must not make selector,
            # marker, popup, and detail classifications disagree.
            detailed_city = merge_capital_details(selected_city, parsed_details)
        except Exception:  # noqa: BLE001 - details are optional; keep map usable
            LOGGER.warning("Could not enrich selected capital %s", selected_city.get("qid"), exc_info=True)
            st.warning("Climate table details could not be loaded right now; showing preloaded metadata.")
            detailed_city = selected_city
        filtered = [detailed_city if marker_id(city) == selected_qid else city for city in filtered]
    if same_climate and detailed_city:
        st.info(f"Highlighting capitals with classification: {classification_value(detailed_city)}")

    col_map, col_details = st.columns([2, 1])
    with col_map:
        st_folium(build_city_map(filtered, selected_qid, same_climate, zones, show_zones), width=None, height=650)
        st.caption("Climate zones are a lightweight, generalized visual grouping layer. Same-climate mode compares the selected capital's cached classification across both capital types.")

    with col_details:
        st.subheader("Capital details")
        if not detailed_city:
            st.write("Choose a capital from the dropdown to inspect its climate classification and monthly table.")
        else:
            st.write(f"**{detailed_city.get('name')}, {detailed_city.get('country')}**")
            capital_label = {"national_capital": "National capital", "regional_capital": "Regional capital", "local_administrative_center": "Local administrative center"}.get(detailed_city.get("record_type"), "Regional capital")
            st.write(f"**Capital type:** {capital_label}")
            st.write(f"**Record scope:** `{detailed_city.get('record_scope') or 'not specified'}`")
            if detailed_city.get("administrative_region"):
                st.write(f"**Administrative region:** {detailed_city['administrative_region']} ({detailed_city.get('administrative_region_type') or 'first-level division'})")
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
            df = climate_dataframe(detailed_city)
            if df.empty:
                st.info("No supported monthly climate table is cached for this capital.")
            else:
                st.dataframe(df, hide_index=True, width="stretch")

    national_count = sum(city.get("record_type") == "national_capital" for city in capitals)
    regional_count = sum(city.get("record_type") != "national_capital" for city in capitals)
    st.caption(f"Loaded {national_count:,} national and {regional_count:,} deduplicated regional/local capitals; displaying {len(filtered):,} after filters.")
    st.caption(
        "Data attribution: locally cached Wikipedia climate classifications and on-demand climate content are available "
        "under CC BY-SA 4.0; Wikidata structured metadata is CC0 1.0. Source pages are retained per record."
    )


if __name__ == "__main__":
    main()
