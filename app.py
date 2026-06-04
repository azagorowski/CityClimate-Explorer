"""Streamlit application for exploring city climate classifications and tables."""
from __future__ import annotations

import logging

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.config import APP_NAME, CITIES_PROCESSED, DEFAULT_POPULATION_THRESHOLD, DEFAULT_SAMPLE_LIMIT
from src.map_view import build_city_map, classification_value
from src.storage import read_json, write_json
from src.wikidata import WikidataRequestError, fetch_cities
from src.wikipedia import enrich_city_climate

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


@st.cache_data(show_spinner=False)
def load_dataset(limit: int, min_population: int, refresh: bool = False) -> list[dict]:
    """Load processed data, refreshing from Wikidata/Wikipedia when requested."""
    if not refresh:
        cached = read_json(CITIES_PROCESSED, default=[])
        if cached:
            return cached
    cities = fetch_cities(limit=limit, min_population=min_population, force_refresh=refresh)
    enriched = [enrich_city_climate(city, force_refresh=refresh) for city in cities]
    if enriched:
        write_json(CITIES_PROCESSED, enriched)
    return enriched


def safe_load_dataset(limit: int, min_population: int, refresh: bool = False) -> list[dict]:
    """Load data for Streamlit without exposing Wikidata tracebacks to users."""
    try:
        cities = load_dataset(limit, min_population, refresh)
    except WikidataRequestError:
        st.error(
            "Wikidata is slow or temporarily unavailable, so fresh city data could not be loaded. "
            "Try lowering the city limit, increasing the population threshold, or refreshing again later."
        )
        logging.warning("Wikidata load failed; attempting processed-data fallback", exc_info=True)
        cached = read_json(CITIES_PROCESSED, default=[])
        if cached:
            st.warning("Showing stale cached city data from the last successful run.")
            return cached
        st.warning("No cached city data is available yet, so the app is starting with an empty dataset.")
        return []
    except Exception:  # noqa: BLE001 - keep Streamlit usable when upstream data sources fail
        st.error(
            "City climate data could not be loaded right now. Try lowering the city limit, "
            "increasing the population threshold, or refreshing again later."
        )
        logging.exception("City dataset load failed")
        cached = read_json(CITIES_PROCESSED, default=[])
        if cached:
            st.warning("Showing stale cached city data from the last successful run.")
            return cached
        st.warning("No cached city data is available yet, so the app is starting with an empty dataset.")
        return []
    if not cities:
        st.warning("No cities are available for the current filters. Lower the population threshold or try again later.")
    return cities


def climate_dataframe(city: dict) -> pd.DataFrame:
    """Return a display dataframe for a city's climate records."""
    return pd.DataFrame(city.get("climate_data", []))


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)
    st.caption("Wikipedia/Wikidata-powered map of populated cities, climate classifications, and monthly climate-table data.")

    with st.sidebar:
        st.header("Data & filters")
        sample_limit = st.slider("Wikidata sample size", 10, 500, DEFAULT_SAMPLE_LIMIT, step=5)
        pop_threshold = st.slider("Minimum population", 50_000, 5_000_000, DEFAULT_POPULATION_THRESHOLD, step=50_000)
        refresh = st.button("Refresh cached data")
        st.caption("Refresh fetches from Wikidata and then Wikipedia. Use modest sample sizes to respect rate limits.")

    with st.spinner("Loading city and climate data..."):
        cities = safe_load_dataset(sample_limit, pop_threshold, refresh)

    countries = sorted({c.get("country") for c in cities if c.get("country")})
    climates = sorted({classification_value(c) for c in cities})
    with st.sidebar:
        country_filter = st.multiselect("Country", countries)
        climate_filter = st.multiselect("Climate classification", climates)

    filtered = [c for c in cities if c.get("population", 0) >= pop_threshold]
    if country_filter:
        filtered = [c for c in filtered if c.get("country") in country_filter]
    if climate_filter:
        filtered = [c for c in filtered if classification_value(c) in climate_filter]

    city_options = {f"{c.get('name')} — {c.get('country')} ({classification_value(c)})": c.get("qid") for c in filtered}
    selected_label = st.selectbox("Select a city", ["None"] + list(city_options.keys()))
    selected_qid = city_options.get(selected_label)
    same_climate = st.toggle("Show cities with the same climate classification", value=False, disabled=not selected_qid)

    selected_city = next((c for c in filtered if c.get("qid") == selected_qid), None)
    if same_climate and selected_city:
        st.info(f"Highlighting cities with classification: {classification_value(selected_city)}")

    col_map, col_details = st.columns([2, 1])
    with col_map:
        st_folium(build_city_map(filtered, selected_qid, same_climate), width=None, height=650)
        st.caption("Same-climate mode highlights city markers sharing a classification; it is not a continuous climate-zone polygon overlay.")

    with col_details:
        st.subheader("City details")
        if not selected_city:
            st.write("Choose a city from the dropdown to inspect parsed climate data.")
        else:
            st.markdown(f"### {selected_city.get('name')}")
            st.write(f"**Country:** {selected_city.get('country')}")
            st.write(f"**Population:** {selected_city.get('population'):,}")
            st.write(f"**Climate classification:** {classification_value(selected_city)}")
            st.write(f"**Extraction status:** {selected_city.get('extraction_status')}")
            if selected_city.get("wikipedia_url"):
                st.link_button("Open Wikipedia source", selected_city["wikipedia_url"])
            df = climate_dataframe(selected_city)
            if df.empty:
                st.warning("Climate data unavailable for this city from the parsed Wikipedia article.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Dataset status")
    st.write(f"Loaded {len(cities):,} cached/fetched cities; displaying {len(filtered):,} after filters.")


if __name__ == "__main__":
    main()
