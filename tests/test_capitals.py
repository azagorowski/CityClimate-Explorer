from src.capitals import SUPPORTED_CONTINENTS, load_preloaded_capitals, merge_city_datasets


def test_startup_capitals_load_from_local_dataset(monkeypatch):
    def fail_request(*args, **kwargs):  # pragma: no cover - should never be called
        raise AssertionError("startup capital loading must not call Wikidata")

    monkeypatch.setattr("urllib.request.urlopen", fail_request)

    capitals = load_preloaded_capitals()

    assert capitals
    assert {"name", "country", "latitude", "longitude", "qid"}.issubset(capitals[0])
    assert {city["region"] for city in capitals} & set(SUPPORTED_CONTINENTS)


def test_merge_city_datasets_deduplicates_by_qid_and_keeps_capital_first():
    capitals = [{"qid": "Q90", "name": "Paris", "country": "France", "source": "preloaded_capitals"}]
    additional = [
        {"qid": "Q90", "name": "Paris", "country": "France", "source": "wikidata"},
        {"qid": "Q64", "name": "Berlin", "country": "Germany", "source": "wikidata"},
    ]

    merged = merge_city_datasets(capitals, additional)

    assert [city["qid"] for city in merged] == ["Q90", "Q64"]
    assert merged[0]["source"] == "preloaded_capitals"
