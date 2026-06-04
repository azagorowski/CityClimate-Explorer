from src.capitals import (
    SUPPORTED_CONTINENTS,
    countries_for_continent,
    country_identifier,
    load_preloaded_capitals,
    merge_city_datasets,
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


def test_capitals_not_filtered_by_missing_population_or_climate():
    capitals = load_preloaded_capitals()

    missing_population = [city for city in capitals if city.get("population") is None]
    missing_climate = [city for city in capitals if city.get("climate_classification") is None]

    assert missing_population
    assert missing_climate
    assert any(city["name"] == "Funafuti" for city in missing_population)


def test_country_dropdown_options_follow_selected_continent():
    capitals = load_preloaded_capitals()

    europe = countries_for_continent(capitals, "Europe")
    oceania = countries_for_continent(capitals, "Oceania")

    assert "France" in europe
    assert "Palau" not in europe
    assert "Palau" in oceania
    assert countries_for_continent(capitals, None) == []


def test_country_identifier_returns_country_qid_when_available():
    capitals = load_preloaded_capitals()

    assert country_identifier(capitals, "France") == {"country": "France", "country_qid": "Q142"}


def test_merge_city_datasets_deduplicates_by_qid_and_keeps_capital_first():
    capitals = [{"qid": "Q90", "name": "Paris", "country": "France", "source": "preloaded_capitals"}]
    additional = [
        {"qid": "Q90", "name": "Paris", "country": "France", "source": "wikidata"},
        {"qid": "Q64", "name": "Berlin", "country": "Germany", "source": "wikidata"},
    ]

    merged = merge_city_datasets(capitals, additional)

    assert [city["qid"] for city in merged] == ["Q90", "Q64"]
    assert merged[0]["source"] == "preloaded_capitals"


def test_merge_city_datasets_deduplicates_by_name_country_when_qid_missing():
    capitals = [{"name": "Ngerulmud", "country": "Palau", "source": "preloaded_capitals"}]
    additional = [{"qid": "Q516978", "name": "ngerulmud", "country": "palau", "source": "wikidata"}]

    merged = merge_city_datasets(capitals, additional)

    assert len(merged) == 1
    assert merged[0]["source"] == "preloaded_capitals"


def test_merge_city_datasets_fills_missing_capital_fields_from_duplicate_additional_city():
    capitals = [{"qid": "Q1780", "name": "Bratislava", "country": "Slovakia", "population": None, "source": "preloaded_capitals"}]
    additional = [{"qid": "Q1780", "name": "Bratislava", "country": "Slovakia", "population": 475_503, "wikipedia_title": "Bratislava", "source": "wikidata"}]

    merged = merge_city_datasets(capitals, additional)

    assert len(merged) == 1
    assert merged[0]["source"] == "preloaded_capitals"
    assert merged[0]["population"] == 475_503
    assert merged[0]["wikipedia_title"] == "Bratislava"
