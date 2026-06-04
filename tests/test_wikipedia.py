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
