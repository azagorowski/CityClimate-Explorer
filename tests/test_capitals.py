from src.capitals import (
    SUPPORTED_CONTINENTS,
    load_preloaded_capitals,
)
from src.config import DEFAULT_POPULATION_THRESHOLD


def test_startup_capitals_load_from_local_dataset(monkeypatch):
    def fail_request(*args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("startup capital loading must not call Wikidata")

    monkeypatch.setattr("urllib.request.urlopen", fail_request)

    capitals = load_preloaded_capitals()

    assert len(capitals) >= 190
    assert {"name", "country", "latitude", "longitude", "qid"}.issubset(capitals[0])
    assert {city["region"] for city in capitals} & set(SUPPORTED_CONTINENTS)


def test_small_capitals_remain_included_below_additional_city_threshold():
    capitals = load_preloaded_capitals()
    by_name = {city["name"]: city for city in capitals}

    for name in ["Andorra la Vella", "San Marino", "Vaduz", "Monaco", "Ngerulmud", "Funafuti", "Malé", "Victoria"]:
        assert name in by_name
        population = by_name[name].get("population")
        assert population is None or population < DEFAULT_POPULATION_THRESHOLD


def test_capitals_not_filtered_by_missing_population_and_unknown_climate():
    capitals = load_preloaded_capitals()

    missing_population = [city for city in capitals if city.get("population") is None]
    unknown_climate = [city for city in capitals if city.get("climate_classification") == "Unknown"]

    assert missing_population
    assert any(city["name"] == "Funafuti" for city in missing_population)


def test_all_bundled_sovereign_state_capitals_validate():
    from scripts.validate_capitals import validate_capitals

    assert validate_capitals() == []


def test_preloaded_capital_climate_comes_from_local_cache_with_source_metadata():
    capitals = load_preloaded_capitals()
    bogota = next(city for city in capitals if city["name"] == "Bogotá")

    assert bogota["climate_classification"] == "Cfb"
    assert bogota["climate_classification_label"] == "oceanic climate"
    assert bogota["climate_classification_source_metadata"]["source_priority"] == "english_primary"


def test_regression_capitals_have_resolved_consistent_startup_climates():
    capitals = load_preloaded_capitals()
    by_name = {city["name"]: city for city in capitals}
    expected = {
        "Tirana", "Bratislava", "Budapest", "Bogotá", "Warsaw", "Vienna", "Prague", "Madrid", "Rome",
        "Paris", "Berlin", "London", "Cairo", "Nairobi", "Tokyo", "Seoul", "Canberra", "Wellington",
    }

    for name in expected:
        city = by_name[name]
        assert city["climate_classification"] != "Unknown"
        assert city["climate_group"] != "Unknown"
        assert city["climate_classification_label"] != "Unknown"
        assert city["climate_source_priority"] == "english_primary"


def test_every_capital_exposes_complete_startup_climate_schema():
    required = {
        "climate_classification", "climate_group", "climate_source_name", "climate_source_language",
        "climate_source_title", "climate_source_url", "climate_source_priority", "climate_extraction_status",
    }

    for city in load_preloaded_capitals():
        assert required.issubset(city), city["name"]


def test_every_preloaded_capital_has_an_english_wikipedia_title_or_url():
    capitals = load_preloaded_capitals()

    assert capitals
    assert all(city.get("wikipedia_title") or city.get("wikipedia_url") for city in capitals)
