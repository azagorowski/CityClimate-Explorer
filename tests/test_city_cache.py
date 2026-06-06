from pathlib import Path

import pytest

from src.capitals import load_preloaded_capitals, merge_city_datasets
from src.city_cache import load_cached_optional_cities, load_optional_city_cache
from src.map_view import CLIMATE_COLORS, build_city_map, classification_value, climate_category


def test_every_startup_capital_has_local_climate_field():
    capitals = load_preloaded_capitals()
    assert len(capitals) >= 190
    assert all(classification_value(city) for city in capitals)
    assert all(city.get("climate_classification_source_metadata") for city in capitals)


def test_required_english_supported_capitals_have_known_climate():
    by_name = {city["name"]: city for city in load_preloaded_capitals()}
    for name in ("Bogotá", "Bratislava", "Budapest", "Warsaw", "Vienna", "Prague"):
        assert classification_value(by_name[name]) != "Unknown"
        assert by_name[name]["climate_classification_source_metadata"]["source_priority"] == "english_primary"


def test_initial_map_contains_capitals_climates_and_legend():
    capitals = load_preloaded_capitals()
    html = build_city_map(capitals).get_root().render()
    assert "Bogotá" in html
    assert classification_value(next(city for city in capitals if city["name"] == "Bogotá")) in html
    assert 'id="climate-legend"' in html
    assert all(label in html for label in CLIMATE_COLORS)


def test_startup_cache_does_not_import_runtime_wikipedia(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("startup must not fetch Wikipedia")
    monkeypatch.setattr("src.wikipedia.fetch_article", fail)
    assert load_preloaded_capitals()


def test_optional_loading_requires_continent_and_country():
    capitals = load_preloaded_capitals()
    with pytest.raises(ValueError, match="continent"):
        load_cached_optional_cities(capitals, None, None)
    with pytest.raises(ValueError, match="country"):
        load_cached_optional_cities(capitals, "Africa", None)


def test_algeria_optional_cities_are_local_ranked_and_bounded(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("normal optional loading must not query Wikidata")
    monkeypatch.setattr("src.wikidata.fetch_cities", fail)
    capitals = load_preloaded_capitals()
    cities = load_cached_optional_cities(capitals, "Africa", "Algeria", limit=50)
    assert 1 <= len(cities) <= 10
    assert cities == sorted(cities, key=lambda city: city.get("population") or 0, reverse=True)
    assert all(city["country"] == "Algeria" for city in cities)
    assert all(city["name"] != "Algiers" for city in cities)
    merged = merge_city_datasets(capitals, cities)
    assert sum(city["name"] == "Algiers" for city in merged) == 1


def test_optional_cache_is_bundled_json():
    assert load_optional_city_cache()
    assert Path("data/top_non_capital_cities_by_country.json").is_file()


@pytest.mark.parametrize(
    ("value", "expected"),
    [("Af tropical rainforest", "Tropical"), ("BWh hot desert", "Dry / Arid"),
     ("Cfb oceanic", "Temperate"), ("Dfb continental", "Continental"),
     ("ET tundra", "Polar"), ("subtropical highland", "Highland / Mountain"),
     ("Unknown", "Unknown")],
)
def test_climate_categories(value, expected):
    assert climate_category(value) == expected
