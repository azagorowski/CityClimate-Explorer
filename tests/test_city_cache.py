from pathlib import Path

import pytest

from app import climate_dataframe, merge_capital_details
from src.capitals import load_preloaded_capitals
from src.map_view import CLIMATE_COLORS, build_city_map, classification_value, climate_category, climate_group


def test_every_startup_capital_has_local_climate_fields_and_metadata():
    capitals = load_preloaded_capitals()
    assert len(capitals) >= 190
    assert all(classification_value(city) for city in capitals)
    assert all(city.get("climate_group") in CLIMATE_COLORS for city in capitals)
    assert all(city.get("climate_classification_source_metadata") for city in capitals)


def test_required_english_supported_capitals_have_known_climate():
    by_name = {city["name"]: city for city in load_preloaded_capitals()}
    for name in ("Tirana", "Bogotá", "Bratislava", "Budapest", "Warsaw", "Vienna", "Prague"):
        assert classification_value(by_name[name]) != "Unknown"
        assert by_name[name]["climate_classification_source_metadata"]["source_priority"] == "english_primary"
    assert classification_value(by_name["Tirana"]) == "Humid subtropical climate"
    assert climate_group(by_name["Tirana"]) == "Temperate"


def test_initial_map_contains_capitals_climates_and_legend():
    capitals = load_preloaded_capitals()
    html = build_city_map(capitals).get_root().render()
    tirana = next(city for city in capitals if city["name"] == "Tirana")
    assert "Tirana" in html
    assert classification_value(tirana) in html
    assert 'id="climate-legend"' in html
    assert all(label in html for label in CLIMATE_COLORS)


def test_startup_cache_does_not_call_wikipedia(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("startup must not fetch Wikipedia")

    monkeypatch.setattr("src.wikipedia.fetch_article", fail)
    assert load_preloaded_capitals()


@pytest.mark.parametrize(
    ("value", "code", "expected"),
    [
        ("tropical rainforest", "Af", "Tropical"),
        ("hot desert climate", "BWh", "Dry / Arid"),
        ("oceanic climate", "Cfb", "Temperate"),
        ("humid subtropical climate", "Cfa", "Temperate"),
        ("humid continental climate", "Dfb", "Continental"),
        ("tundra", "ET", "Polar"),
        ("subtropical highland", None, "Highland / Mountain"),
        ("Unknown", None, "Unknown"),
    ],
)
def test_climate_categories(value, code, expected):
    assert climate_category(value, code) == expected



def test_detail_table_merge_cannot_replace_authoritative_selector_classification():
    capital = {
        "climate_classification": "Cfa",
        "climate_classification_label": "Humid subtropical climate",
        "climate_group": "Temperate",
        "climate_classification_source": "english_primary",
        "climate_classification_source_metadata": {"source_priority": "english_primary"},
    }
    details = {
        "climate_classification": "Unknown",
        "climate_classification_label": "Unknown",
        "climate_data": [{"metric_name": "Rainfall", "jan": 1}],
        "extraction_status": "parsed_weather_box",
    }
    merged = merge_capital_details(capital, details)
    assert classification_value(merged) == "Humid subtropical climate"
    assert merged["climate_group"] == "Temperate"
    assert merged["climate_data"] == details["climate_data"]
    assert merged["extraction_status"] == "parsed_weather_box"

def test_monthly_table_columns_use_calendar_order_and_annual_last():
    city = {"climate_data": [{"metric_name": "Rainfall", "unit": "mm", "apr": 4, "jan": 1, "annual": 99}]}
    frame = climate_dataframe(city)
    assert list(frame.columns) == [
        "Metric", "Unit", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul",
        "Aug", "Sep", "Oct", "Nov", "Dec", "Annual",
    ]
    assert frame.loc[0, "Jan"] == 1
    assert frame.loc[0, "Apr"] == 4
    assert frame.loc[0, "Annual"] == 99


def test_capitals_only_ui_has_no_additional_city_controls_or_runtime_imports():
    source = Path("app.py").read_text(encoding="utf-8")
    forbidden = (
        "Load cached cities for selected country", "Additional city limit",
        "load_additional_cities", "load_cached_optional_cities", "merge_city_datasets",
        "additional_cities", "Fetching 10 additional cities",
    )
    assert not [text for text in forbidden if text in source]
    assert "Filter capitals by continent" in source
