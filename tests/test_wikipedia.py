from src.wikipedia import enrich_city_climate, resolve_city_article_title

from tests.test_climate_parser import BRATISLAVA_RENDERED_TABLE, BUDAPEST_RENDERED_TABLE


def test_resolve_city_article_title_uses_local_disambiguated_titles_when_qid_missing():
    assert resolve_city_article_title({"name": "Bratislava", "country": "Slovakia", "wikipedia_title": "Bratislava"}) == "Bratislava"
    assert resolve_city_article_title({"name": "Budapest", "country": "Hungary", "wikipedia_title": "Budapest"}) == "Budapest"
    assert resolve_city_article_title({"name": "Panama City", "country": "Panama"}) == "Panama City"


def test_enrich_bratislava_regression_parses_non_empty_html_climate_data(monkeypatch, tmp_path):
    from src import wikipedia

    monkeypatch.setattr(wikipedia, "CLIMATE_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        wikipedia,
        "fetch_article",
        lambda title, force_refresh=False: {
            "title": "Bratislava",
            "url": "https://en.wikipedia.org/wiki/Bratislava",
            "wikitext": "No template here",
            "html": BRATISLAVA_RENDERED_TABLE,
        },
    )

    city = {"name": "Bratislava", "country": "Slovakia", "wikipedia_title": "Bratislava"}
    enriched = enrich_city_climate(city, force_refresh=True)

    assert enriched["extraction_status"] == "parsed_html_table"
    assert enriched["climate_data"]


def test_enrich_budapest_regression_parses_non_empty_html_climate_data(monkeypatch, tmp_path):
    from src import wikipedia

    monkeypatch.setattr(wikipedia, "CLIMATE_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        wikipedia,
        "fetch_article",
        lambda title, force_refresh=False: {
            "title": "Budapest",
            "url": "https://en.wikipedia.org/wiki/Budapest",
            "wikitext": "No template here",
            "html": BUDAPEST_RENDERED_TABLE,
        },
    )

    city = {"name": "Budapest", "country": "Hungary", "wikipedia_title": "Budapest"}
    enriched = enrich_city_climate(city, force_refresh=True)

    assert enriched["extraction_status"] == "parsed_html_table"
    assert enriched["climate_data"]


def test_enrich_tries_english_before_native_fallback(monkeypatch, tmp_path):
    from src import wikipedia

    calls = []

    def fake_fetch(title, force_refresh=False, language="en"):
        calls.append((language, title))
        if language == "en":
            return {"language": "en", "title": title, "url": "https://en.wikipedia.org/wiki/Test", "wikitext": "No table", "html": ""}
        return {
            "language": language,
            "title": title,
            "url": f"https://{language}.wikipedia.org/wiki/Test",
            "wikitext": "{{Weather box\n| Jan high C = 1\n| Feb high C = 2\n| Mar high C = 3\n| Apr high C = 4\n| May high C = 5\n| Jun high C = 6\n| Jul high C = 7\n| Aug high C = 8\n| Sep high C = 9\n| Oct high C = 10\n| Nov high C = 11\n| Dec high C = 12\n}}",
            "html": "",
        }

    monkeypatch.setattr(wikipedia, "CLIMATE_CACHE_DIR", tmp_path)
    monkeypatch.setattr(wikipedia, "fetch_article", fake_fetch)

    enriched = wikipedia.enrich_city_climate(
        {"name": "Example", "country": "Exampleland", "wikipedia_title": "Example", "native_wikipedia_language": "es", "native_wikipedia_title": "Ejemplo"},
        force_refresh=True,
    )

    assert calls == [("en", "Example"), ("es", "Ejemplo")]
    assert enriched["climate_source_priority"] == "native_fallback"
    assert enriched["climate_data"]


def test_wikidata_classification_is_fallback_only(monkeypatch, tmp_path):
    from src import wikipedia

    monkeypatch.setattr(wikipedia, "CLIMATE_CACHE_DIR", tmp_path)
    monkeypatch.setattr(
        wikipedia,
        "fetch_article",
        lambda title, force_refresh=False, language="en": {
            "language": "en",
            "title": title,
            "url": "https://en.wikipedia.org/wiki/Bogot%C3%A1",
            "wikitext": "== Climate ==\nBogotá has a subtropical highland climate (Köppen Cfb).",
            "html": "",
        },
    )

    enriched = wikipedia.enrich_city_climate(
        {
            "name": "Bogotá",
            "country": "Colombia",
            "wikipedia_title": "Bogotá",
            "wikidata_climate_classification": "Cfb",
            "wikidata_climate_classification_label": "oceanic climate",
        },
        force_refresh=True,
    )

    assert enriched["climate_classification_label"] == "Subtropical highland climate"
    assert enriched["climate_classification_source"] == "wikipedia_primary"
    assert enriched["climate_classification_label"] != "oceanic climate"
