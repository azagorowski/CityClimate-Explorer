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
    country_identifier,
    load_preloaded_capitals,
    filter_optional_non_capital_cities,
    merge_city_datasets,
)
from src.config import APP_NAME, DEFAULT_POPULATION_THRESHOLD, DEFAULT_SAMPLE_LIMIT
from src.map_view import build_city_map, classification_value, marker_id
from src.wikidata import WikidataRequestError, fetch_cities
from src.wikipedia import enrich_city_climate

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
LOGGER = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def load_capitals_dataset() -> list[dict[str, Any]]:
    """Load the local country-capital seed dataset without using Wikidata."""
    return load_preloaded_capitals()


@st.cache_data(show_spinner=False)
def load_additional_cities(
    continent: str,
    country: str,
    country_qid: str | None,
    limit: int,
    min_population: int,
    refresh: bool = False,
) -> list[dict[str, Any]]:
    """Load optional additional cities for one selected country."""
    return fetch_cities(
        limit=limit,
        min_population=min_population,
        force_refresh=refresh,
        continent=continent,
        country=country,
        country_qid=country_qid,
    )


@st.cache_data(show_spinner=False)
def load_city_details(city: dict[str, Any]) -> dict[str, Any]:
    """Parse Wikipedia climate details only after a user selects a city."""
    return enrich_city_climate(city, force_refresh=False)


def safe_load_additional_cities(
    continent: str | None,
    country: str | None,
    country_qid: str | None,
    limit: int,
    min_population: int,
    refresh: bool = False,
) -> list[dict[str, Any]]:
    """Fetch optional Wikidata cities without hiding the preloaded capitals on failure."""
    if not continent or not country:
        st.warning("Select a continent and country before loading additional cities.")
        return []
    try:
        with st.spinner("Loading additional cities for selected country..."):
            cities = load_additional_cities(continent, country, country_qid, limit, min_population, refresh)
        if not cities:
            st.info(f"No additional non-capital cities were found for {country} at ≥ {min_population:,} inhabitants.")
        return cities
    except WikidataRequestError:
        LOGGER.warning("Additional city load failed for %s/%s; relying on any Wikidata cache fallback", continent, country, exc_info=True)
        st.warning("Could not load additional cities. Showing preloaded capitals.")
        try:
            return fetch_cities(
                limit=limit,
                min_population=min_population,
                force_refresh=False,
                continent=continent,
                country=country,
                country_qid=country_qid,
            )
        except Exception:  # noqa: BLE001 - keep Streamlit responsive when cache fallback is unavailable
            return []
    except Exception:  # noqa: BLE001 - keep Streamlit responsive when upstream data sources fail
        LOGGER.exception("Additional city load failed for %s/%s", continent, country)
        st.warning("Could not load additional cities. Showing preloaded capitals.")
        return []


def climate_dataframe(city: dict[str, Any]) -> pd.DataFrame:
    """Return a display dataframe for a city's climate records."""
    return pd.DataFrame(city.get("climate_data", []))


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)
    st.caption(
        "Fast-start map of preloaded world capitals, with optional on-demand Wikidata loading by selected continent and country."
    )

    capitals = load_capitals_dataset()
    st.info("Showing preloaded world capitals. Select a continent and country to load up to 10 major non-capital cities.")

    with st.sidebar:
        st.header("Data & filters")
        st.caption("Region means continent. Select a continent, then select a country before loading optional additional cities.")
        selected_continent = st.selectbox("Select a continent", ["Select a continent"] + list(SUPPORTED_CONTINENTS))
        continent = None if selected_continent == "Select a continent" else selected_continent
        country_options = countries_for_continent(capitals, continent)
        selected_country = st.selectbox("Select a country", ["Select a country"] + country_options, disabled=continent is None)
        country = None if selected_country == "Select a country" else selected_country
        country_meta = country_identifier(capitals, country)
        country_qid = country_meta.get("country_qid")
        sample_limit = st.slider("Additional Wikidata city limit", 1, 10, DEFAULT_SAMPLE_LIMIT, step=1)
        pop_threshold = st.slider(
            "Minimum population for additional cities",
            200_000,
            5_000_000,
            DEFAULT_POPULATION_THRESHOLD,
            step=50_000,
        )
        st.caption("Additional city loading uses Wikidata and may take some time. Queries are restricted to the selected country.")
        can_load_additional = continent is not None and country is not None
        load_more = st.button("Load additional cities for selected country", disabled=not can_load_additional)
        refresh = st.button("Refresh additional-city cache", disabled=not can_load_additional)

    additional: list[dict[str, Any]] = st.session_state.get("additional_cities", [])
    existing_context = st.session_state.get("additional_context")
    if existing_context and (existing_context.get("continent") != continent or existing_context.get("country") != country):
        additional = []
    if load_more or refresh:
        loaded = safe_load_additional_cities(continent, country, country_qid, sample_limit, pop_threshold, refresh)
        additional = filter_optional_non_capital_cities(capitals, loaded, limit=sample_limit)
        if additional and country:
            st.success(f"Loaded {len(additional)} major non-capital cities for {country}.")
        st.session_state["additional_cities"] = additional
        st.session_state["additional_context"] = {"continent": continent, "country": country, "min_population": pop_threshold, "limit": sample_limit}
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
            if detailed_city.get("climate_classification_source") == "wikidata_fallback":
                st.caption("Wikidata climate classification used as fallback.")
            elif classification_source.get("source_language") == "en":
                st.caption("Climate classification source: English Wikipedia.")
            elif classification_source:
                st.caption("Climate classification source: native-language Wikipedia fallback.")
            if classification_source.get("source_url"):
                st.markdown(
                    f"Classification source: [{classification_source.get('source_page_title') or classification_source.get('source_name')}]"
                    f"({classification_source['source_url']}) · language: `{classification_source.get('source_language')}`"
                )
            st.write(f"**Extraction status:** {detailed_city.get('extraction_status')}")
            if detailed_city.get("climate_source_priority") == "english_primary":
                st.caption("Climate data source: English Wikipedia.")
            elif detailed_city.get("climate_source_priority") == "native_fallback":
                st.caption("Native-language Wikipedia used as fallback because English climate data was unavailable.")
            table_source = detailed_city.get("climate_table_source_metadata") or {}
            if table_source.get("source_url"):
                st.markdown(
                    f"Table source: [{table_source.get('source_page_title') or table_source.get('source_name')}]"
                    f"({table_source['source_url']}) · language: `{table_source.get('source_language')}` · role: `{table_source.get('source_role')}`"
                )
            elif detailed_city.get("wikipedia_url"):
                st.link_button("Open Wikipedia source", detailed_city["wikipedia_url"])
            df = climate_dataframe(detailed_city)
            if df.empty:
                st.warning("No supported climate table was found for this city on Wikipedia.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Dataset status")
    context = st.session_state.get("additional_context")
    if context:
        st.write(
            f"Loaded {len(capitals):,} preloaded capitals plus {len(additional):,} optional "
            f"major non-capital cities for {context['country']} ({context['continent']}) at ≥ {context['min_population']:,} inhabitants; "
            f"displaying {len(filtered):,} after filters."
        )
    else:
        st.write(f"Loaded {len(capitals):,} preloaded world capitals; displaying {len(filtered):,} after filters.")

    st.caption(
        "Data attribution: Wikipedia climate content is available under CC BY-SA 4.0; "
        "Wikidata structured data is available under CC0 1.0. Exact source pages are shown with selected-city results."
    )


if __name__ == "__main__":
    main()
