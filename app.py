"""Streamlit application for exploring city climate classifications and tables."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.capitals import (
    SUPPORTED_CONTINENTS,
    countries_for_continent,
    load_preloaded_capitals,
    merge_city_datasets,
)
from src.config import (
    APP_NAME,
    DEFAULT_SAMPLE_LIMIT,
    WIKIDATA_LICENSE_URL,
    WIKIPEDIA_LICENSE_URL,
    get_tile_provider,
)
from src.city_cache import load_cached_optional_cities
from src.map_view import CLIMATE_COLORS, build_city_map, classification_value, marker_id
from src.wikipedia import enrich_city_climate

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
LOGGER = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def load_capitals_dataset() -> list[dict[str, Any]]:
    """Load the local country-capital seed dataset without using Wikidata."""
    return load_preloaded_capitals()


@st.cache_data(show_spinner=False)
def load_additional_cities(
    capitals: list[dict[str, Any]], continent: str, country: str, limit: int = 10
) -> list[dict[str, Any]]:
    """Load optional cities from the bundled country-scoped cache only."""
    return load_cached_optional_cities(capitals, continent, country, min(10, limit))


@st.cache_data(show_spinner=False)
def load_city_details(city: dict[str, Any]) -> dict[str, Any]:
    """Parse Wikipedia climate details only after a user selects a city."""
    return enrich_city_climate(city, force_refresh=False)


def safe_load_additional_cities(
    capitals: list[dict[str, Any]], continent: str | None, country: str | None, limit: int = 10
) -> list[dict[str, Any]]:
    """Read bounded optional-city records while guarding required selectors."""
    if not continent or not country:
        st.warning("Select a continent and country before loading additional cities.")
        return []
    cities = load_additional_cities(capitals, continent, country, min(10, limit))
    if not cities:
        st.info(f"No cached non-capital cities are currently available for {country}.")
    return cities


def climate_dataframe(city: dict[str, Any]) -> pd.DataFrame:
    """Return a display dataframe for a city's climate records."""
    return pd.DataFrame(city.get("climate_data", []))


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
    st.caption(
        "Fast-start map of world capitals with locally preloaded climate classifications and optional cached cities."
    )

    capitals = load_capitals_dataset()
    st.info("Showing all preloaded world capitals with local climate classifications. Select a continent and country to add up to 10 cached non-capital cities.")

    with st.sidebar:
        st.header("Data & filters")
        st.caption("Region means continent. Select a continent, then select a country before loading optional additional cities.")
        selected_continent = st.selectbox("Select a continent", ["Select a continent"] + list(SUPPORTED_CONTINENTS))
        continent = None if selected_continent == "Select a continent" else selected_continent
        country_options = countries_for_continent(capitals, continent)
        selected_country = st.selectbox("Select a country", ["Select a country"] + country_options, disabled=continent is None)
        country = None if selected_country == "Select a country" else selected_country
        sample_limit = st.slider("Additional city limit", 1, 10, DEFAULT_SAMPLE_LIMIT, step=1)
        st.caption("Optional cities load instantly from a local open-data cache. Live refresh is a separate developer CLI action.")
        can_load_additional = continent is not None and country is not None
        load_more = st.button("Load cached cities for selected country", disabled=not can_load_additional, width="stretch")
        st.subheader("Climate legend")
        for label, color in CLIMATE_COLORS.items():
            st.markdown(
                f'<span style="display:inline-block;width:12px;height:12px;border-radius:50%;background:{color};margin-right:8px"></span>{label}',
                unsafe_allow_html=True,
            )
        st.divider()
        st.subheader("Data sources and licenses")
        st.markdown(f"- [Wikipedia climate content]({WIKIPEDIA_LICENSE_URL}): CC BY-SA 4.0")
        st.markdown(f"- [Wikidata metadata]({WIKIDATA_LICENSE_URL}): CC0 1.0")
        tile_provider = get_tile_provider()
        st.caption(f"Map tiles: {tile_provider.name}; provider attribution is displayed on the map.")
        st.caption("Software dependency notices: THIRD_PARTY_NOTICES.md in the application repository.")

    additional: list[dict[str, Any]] = st.session_state.get("additional_cities", [])
    existing_context = st.session_state.get("additional_context")
    if existing_context and (existing_context.get("continent") != continent or existing_context.get("country") != country):
        additional = []
    if load_more:
        additional = safe_load_additional_cities(capitals, continent, country, sample_limit)
        if additional and country:
            st.success(f"Loaded {len(additional)} major non-capital cities for {country}.")
        st.session_state["additional_cities"] = additional
        st.session_state["additional_context"] = {"continent": continent, "country": country, "limit": sample_limit}
    elif continent is None or country is None:
        st.sidebar.info("Select a continent and country before loading additional cities.")

    cities = merge_city_datasets(capitals, additional)
    countries = sorted({c.get("country") for c in cities if c.get("country")})
    regions = sorted({c.get("region") or c.get("continent") for c in cities if c.get("region") or c.get("continent")})
    climates = sorted({classification_value(c) for c in cities})
    with st.sidebar:
        region_filter = st.multiselect("Displayed regions / continents", regions)
        country_filter = st.multiselect("Country", countries)
        climate_filter = st.multiselect("Climate classification", climates)

    filtered = cities
    if region_filter:
        filtered = [c for c in filtered if (c.get("region") or c.get("continent")) in region_filter]
    if country_filter:
        filtered = [c for c in filtered if c.get("country") in country_filter]
    if climate_filter:
        filtered = [c for c in filtered if classification_value(c) in climate_filter]

    city_options = {f"{c.get('name')} — {c.get('country')} ({classification_value(c)})": marker_id(c) for c in filtered}
    selected_label = st.selectbox("Select a city", ["None"] + list(city_options.keys()))
    selected_qid = city_options.get(selected_label)
    same_climate = st.toggle("Show cities with the same climate classification", value=False, disabled=not selected_qid)

    selected_city = next((c for c in filtered if marker_id(c) == selected_qid), None)
    detailed_city = selected_city
    if selected_city:
        try:
            with st.spinner("Loading selected city's Wikipedia climate table..."):
                detailed_city = load_city_details(selected_city)
        except Exception:  # noqa: BLE001 - details are optional; keep map usable
            LOGGER.warning("Could not enrich selected city %s", selected_city.get("qid"), exc_info=True)
            st.warning("Climate table details could not be loaded right now; showing preloaded metadata.")
            detailed_city = selected_city
        # Replace the selected marker with its on-demand enriched record so the
        # map popup and same-climate highlighting use the newly parsed result.
        filtered = [detailed_city if marker_id(city) == selected_qid else city for city in filtered]
    if same_climate and detailed_city:
        st.info(f"Highlighting cities with classification: {classification_value(detailed_city)}")

    col_map, col_details = st.columns([2, 1])
    with col_map:
        st_folium(build_city_map(filtered, selected_qid, same_climate), width=None, height=650)
        st.caption("Same-climate mode highlights city markers sharing a classification; it is not a continuous climate-zone polygon overlay.")

    with col_details:
        st.subheader("City details")
        if not detailed_city:
            st.write("Choose a city from the dropdown to inspect parsed climate data.")
        else:
            st.markdown(f"### {detailed_city.get('name')}")
            st.write(f"**Country:** {detailed_city.get('country')}")
            if detailed_city.get("region") or detailed_city.get("continent"):
                st.write(f"**Region / continent:** {detailed_city.get('region') or detailed_city.get('continent')}")
            population = detailed_city.get("population")
            st.write(f"**Population:** {population:,}" if isinstance(population, int | float) else "**Population:** unavailable")
            st.write(f"**Climate classification:** {classification_value(detailed_city)}")
            classification_source = detailed_city.get("climate_classification_source_metadata") or {}
            render_source_metadata("Classification source", classification_source)
            if classification_source.get("license") == "CC BY-SA 4.0":
                st.info(
                    "This climate classification is derived from Wikipedia under CC BY-SA 4.0. "
                    "The linked page history identifies contributors; adaptations must preserve attribution and share-alike terms."
                )
            elif detailed_city.get("climate_classification_source") == "wikidata_fallback":
                st.caption("Wikidata CC0 climate classification used only because Wikipedia had no usable classification.")
            st.write(f"**Extraction status:** {detailed_city.get('extraction_status')}")
            table_source = detailed_city.get("climate_table_source_metadata") or {}
            render_source_metadata("Climate table source", table_source)
            if table_source.get("source_url"):
                st.info(
                    "Climate table derived from Wikipedia, licensed under CC BY-SA 4.0; "
                    "see the linked source page history for contributors."
                )
            elif detailed_city.get("wikipedia_url"):
                st.link_button("Open Wikipedia source", detailed_city["wikipedia_url"])
            df = climate_dataframe(detailed_city)
            if df.empty:
                st.warning("No supported climate table was found for this city on Wikipedia.")
            else:
                st.dataframe(df, width="stretch", hide_index=True)

    st.divider()
    st.subheader("Dataset status")
    context = st.session_state.get("additional_context")
    if context:
        st.write(
            f"Loaded {len(capitals):,} preloaded capitals plus {len(additional):,} optional "
            f"cached major non-capital cities for {context['country']} ({context['continent']}); "
            f"displaying {len(filtered):,} after filters."
        )
    else:
        st.write(f"Loaded {len(capitals):,} preloaded world capitals; displaying {len(filtered):,} after filters.")

    st.caption(
        "Data attribution: locally cached Wikipedia climate classifications and on-demand climate content are available "
        "under CC BY-SA 4.0; Wikidata structured metadata is CC0 1.0. Source pages are retained per record."
    )


if __name__ == "__main__":
    main()
