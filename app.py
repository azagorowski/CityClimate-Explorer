"""Streamlit application for exploring city climate classifications and tables."""
from __future__ import annotations

import logging
from typing import Any

import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src.capitals import SUPPORTED_CONTINENTS, load_preloaded_capitals, merge_city_datasets
from src.config import APP_NAME, DEFAULT_POPULATION_THRESHOLD, DEFAULT_SAMPLE_LIMIT
from src.map_view import build_city_map, classification_value
from src.wikidata import WikidataRequestError, fetch_cities
from src.wikipedia import enrich_city_climate

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
LOGGER = logging.getLogger(__name__)


@st.cache_data(show_spinner=False)
def load_capitals_dataset() -> list[dict[str, Any]]:
    """Load the local country-capital seed dataset without using Wikidata."""
    return load_preloaded_capitals()


@st.cache_data(show_spinner=False)
def load_additional_cities(continent: str, limit: int, min_population: int, refresh: bool = False) -> list[dict[str, Any]]:
    """Load optional additional cities for one selected continent."""
    cities = fetch_cities(limit=limit, min_population=min_population, force_refresh=refresh, continent=continent)
    return [enrich_city_climate(city, force_refresh=refresh) for city in cities]


@st.cache_data(show_spinner=False)
def load_city_details(city: dict[str, Any]) -> dict[str, Any]:
    """Parse Wikipedia climate details only after a user selects a city."""
    return enrich_city_climate(city, force_refresh=False)


def safe_load_additional_cities(continent: str | None, limit: int, min_population: int, refresh: bool = False) -> list[dict[str, Any]]:
    """Fetch optional Wikidata cities without hiding the preloaded capitals on failure."""
    if not continent:
        st.warning("Select a continent to load additional cities.")
        return []
    try:
        with st.spinner(f"Loading additional cities in {continent} from Wikidata. This may take some time..."):
            return load_additional_cities(continent, limit, min_population, refresh)
    except WikidataRequestError:
        LOGGER.warning("Additional city load failed for %s; relying on any Wikidata cache fallback", continent, exc_info=True)
        st.warning(
            "Could not load additional cities from Wikidata. Showing capitals and cached data if available."
        )
        try:
            return fetch_cities(limit=limit, min_population=min_population, force_refresh=False, continent=continent)
        except Exception:  # noqa: BLE001 - keep Streamlit responsive when cache fallback is unavailable
            return []
    except Exception:  # noqa: BLE001 - keep Streamlit responsive when upstream data sources fail
        LOGGER.exception("Additional city load failed for %s", continent)
        st.warning("Could not load additional cities from Wikidata. Showing capitals and cached data if available.")
        return []


def climate_dataframe(city: dict[str, Any]) -> pd.DataFrame:
    """Return a display dataframe for a city's climate records."""
    return pd.DataFrame(city.get("climate_data", []))


def main() -> None:
    st.set_page_config(page_title=APP_NAME, layout="wide")
    st.title(APP_NAME)
    st.caption(
        "Fast-start map of preloaded country capitals, with optional on-demand Wikidata loading by continent."
    )

    capitals = load_capitals_dataset()
    st.info("Showing preloaded country capitals. Additional cities are loaded only on demand.")

    with st.sidebar:
        st.header("Data & filters")
        st.caption("Region means continent. Select a continent before loading optional additional cities.")
        selected_continent = st.selectbox("Region / continent for additional cities", ["Select a continent"] + list(SUPPORTED_CONTINENTS))
        continent = None if selected_continent == "Select a continent" else selected_continent
        sample_limit = st.slider("Additional Wikidata city limit", 10, 500, DEFAULT_SAMPLE_LIMIT, step=5)
        pop_threshold = st.slider(
            "Minimum population for additional cities",
            200_000,
            5_000_000,
            DEFAULT_POPULATION_THRESHOLD,
            step=50_000,
        )
        st.caption("Loading additional cities may take some time and uses Wikidata only for the selected continent.")
        load_more = st.button("Load additional cities", disabled=continent is None)
        refresh = st.button("Refresh additional-city cache", disabled=continent is None)

    additional: list[dict[str, Any]] = st.session_state.get("additional_cities", [])
    if load_more or refresh:
        additional = safe_load_additional_cities(continent, sample_limit, pop_threshold, refresh)
        st.session_state["additional_cities"] = additional
        st.session_state["additional_context"] = {"continent": continent, "min_population": pop_threshold, "limit": sample_limit}
    elif continent is None:
        st.sidebar.info("Select a continent to load additional cities.")

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

    city_options = {f"{c.get('name')} — {c.get('country')} ({classification_value(c)})": c.get("qid") for c in filtered}
    selected_label = st.selectbox("Select a city", ["None"] + list(city_options.keys()))
    selected_qid = city_options.get(selected_label)
    same_climate = st.toggle("Show cities with the same climate classification", value=False, disabled=not selected_qid)

    selected_city = next((c for c in filtered if c.get("qid") == selected_qid), None)
    detailed_city = selected_city
    if selected_city:
        try:
            with st.spinner("Loading selected city's Wikipedia climate table..."):
                detailed_city = load_city_details(selected_city)
        except Exception:  # noqa: BLE001 - details are optional; keep map usable
            LOGGER.warning("Could not enrich selected city %s", selected_city.get("qid"), exc_info=True)
            st.warning("Climate table details could not be loaded right now; showing preloaded metadata.")
            detailed_city = selected_city
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
            st.write(f"**Population:** {detailed_city.get('population'):,}")
            st.write(f"**Climate classification:** {classification_value(detailed_city)}")
            st.write(f"**Extraction status:** {detailed_city.get('extraction_status')}")
            if detailed_city.get("wikipedia_url"):
                st.link_button("Open Wikipedia source", detailed_city["wikipedia_url"])
            df = climate_dataframe(detailed_city)
            if df.empty:
                st.warning("Climate data unavailable for this city from the parsed Wikipedia article.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Dataset status")
    context = st.session_state.get("additional_context")
    if context:
        st.write(
            f"Loaded {len(capitals):,} preloaded capitals plus {len(additional):,} optional "
            f"cities for {context['continent']} at ≥ {context['min_population']:,} inhabitants; "
            f"displaying {len(filtered):,} after filters."
        )
    else:
        st.write(f"Loaded {len(capitals):,} preloaded country capitals; displaying {len(filtered):,} after filters.")


if __name__ == "__main__":
    main()
