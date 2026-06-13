import json

from src.locations import (TOP_15_COUNTRIES, deduplicate_locations, load_all_capitals, load_climate_zones,
                           load_regional_capitals, load_top15_regional_capitals, load_top90_country_reference,
                           load_top90_regional_capitals, load_priority_regional_capitals)
from src.map_view import CLIMATE_COLORS, build_city_map, climate_group
from src.normalize import normalized_search_key


def test_regional_cache_covers_top_90_with_required_metadata():
    reference = load_top90_country_reference()
    records = load_top90_regional_capitals()
    assert len(reference) == 90
    assert [record["area_rank"] for record in reference] == list(range(1, 91))
    assert {record["country"] for record in reference} <= {record["country"] for record in records}
    for record in records:
        assert record["record_type"] == "regional_capital"
        assert record.get("latitude") is not None and record.get("longitude") is not None
        assert record.get("administrative_region") and record.get("administrative_region_type")
        assert record.get("climate_classification") or record.get("climate_extraction_status")
        assert record.get("provenance")


def test_representative_regional_capital_coverage():
    records = load_regional_capitals()
    by_country = {}
    for record in records:
        by_country.setdefault(record["country"], set()).add(record["name"])
    assert {"Montgomery", "Sacramento", "Austin"} <= by_country["United States"]
    assert {"Edmonton", "Victoria", "Iqaluit"} <= by_country["Canada"]
    assert {"Rio Branco", "São Paulo", "Porto Alegre"} <= by_country["Brazil"]
    assert {"Sydney", "Darwin", "Hobart"} <= by_country["Australia"]
    assert {"Amaravati", "Jaipur", "Shimla"} <= by_country["India"]
    assert {"Maykop", "Irkutsk", "Yakutsk"} <= by_country["Russia"]


def test_combined_dataset_preserves_national_capitals_and_removes_marker_duplicates():
    records = load_all_capitals()
    national = [record for record in records if record["record_type"] == "national_capital"]
    assert len(national) >= 190
    ids = [record["marker_id"] for record in records]
    assert len(ids) == len(set(ids))
    washington = [record for record in records if record["name"] == "Washington, D.C." and record["country"] == "United States"]
    assert len(washington) == 1 and washington[0]["record_type"] == "national_capital"


def test_climate_groups_have_colors_and_zone_geojson_is_valid():
    records = load_regional_capitals()
    assert all(climate_group(record) in CLIMATE_COLORS for record in records)
    zones = load_climate_zones()
    assert zones["type"] == "FeatureCollection" and zones["features"]
    assert {feature["properties"]["climate_group"] for feature in zones["features"]} <= set(CLIMATE_COLORS)


def test_map_contains_toggleable_zone_and_capital_layers():
    records = load_all_capitals()[:5] + load_regional_capitals()[:5]
    html = build_city_map(records, climate_zones=load_climate_zones()).get_root().render()
    assert "Broad climate zones" in html
    assert "National capitals" in html
    assert "Regional capitals" in html
    assert "layer_control" in html
    assert "National capital" in html and "Regional capital" in html


def test_startup_loaders_do_not_contain_runtime_wikimedia_calls(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("startup must not access the network")
    monkeypatch.setattr("urllib.request.urlopen", fail)
    assert load_all_capitals()
    assert load_climate_zones()["features"]


def test_generated_files_have_dataset_metadata():
    regional = json.load(open("data/preloaded/regional_capitals_top90_countries.json", encoding="utf-8"))
    zones = json.load(open("data/preloaded/climate_zones_simplified.geojson", encoding="utf-8"))
    assert regional["source_metadata"]["runtime_network_required"] is False
    assert zones["metadata"]["commercial_use_status"] == "permitted"


def test_representative_top90_country_coverage():
    records = load_top90_regional_capitals()
    represented = {record["country"] for record in records}
    required = {
        "Russia", "Canada", "China", "United States", "Brazil", "Australia", "India", "Argentina",
        "Kazakhstan", "Algeria", "Democratic Republic of the Congo", "Saudi Arabia", "Mexico",
        "Indonesia", "Sudan", "Norway", "Sweden", "Finland",
    }
    assert required <= represented
    assert all(record.get("latitude") is not None and record.get("longitude") is not None for record in records)
    assert all(record.get("id") or record.get("marker_id") for record in records)
    assert any(record.get("country") == "Greenland" for record in load_regional_capitals())


def test_krakow_and_stavanger_are_complete_runtime_regional_capitals():
    by_name = {record["name"]: record for record in load_all_capitals()}
    krakow = by_name["Kraków"]
    stavanger = by_name["Stavanger"]

    assert krakow["record_type"] == "regional_capital"
    assert krakow["record_scope"] == "priority_country_regional_capital"
    assert krakow["administrative_region"] == "Lesser Poland Voivodeship"
    assert normalized_search_key("Krakow") in krakow["search_keys"]
    assert normalized_search_key("Kraków") in krakow["search_keys"]
    assert stavanger["record_type"] in {"regional_capital", "local_administrative_center"}
    assert stavanger["record_scope"] == "priority_country_regional_capital"
    assert stavanger["administrative_region"] == "Rogaland"
    assert all(city.get("latitude") is not None and city.get("longitude") is not None for city in (krakow, stavanger))


def test_priority_snapshot_has_complete_country_coverage_and_correct_nordic_groups():
    records = load_priority_regional_capitals()
    counts = {}
    by_name = {}
    for record in records:
        counts[record["country"]] = counts.get(record["country"], 0) + 1
        by_name[record["name"]] = record
    assert counts == {
        "Poland": 18, "Germany": 16, "Spain": 20, "France": 18,
        "Norway": 18, "Sweden": 23, "Finland": 18, "Türkiye": 81,
    }
    for name in ("Tromsø", "Vadsø", "Rovaniemi", "Luleå", "Umeå", "Östersund"):
        assert by_name[name]["primary_koppen_code"] == "Dfc"
        assert climate_group(by_name[name]) == "Continental"
    assert by_name["Bodø"]["primary_koppen_code"] == "Cfc"
    assert climate_group(by_name["Bodø"]) == "Temperate"


def test_deduplication_preserves_same_named_regional_capitals_in_distinct_regions():
    first = {"name": "Springfield", "country": "Example", "administrative_region": "North"}
    second = {"name": "Springfield", "country": "Example", "administrative_region": "South"}
    assert len(deduplicate_locations([], [first, second])) == 2


def test_every_top90_country_has_explicit_processing_status():
    payload = json.load(open("data/preloaded/regional_capitals_top90_countries.json", encoding="utf-8"))
    statuses = payload["country_processing_status"]
    assert len(statuses) == 90
    assert {row["country"] for row in statuses} == {row["country"] for row in load_top90_country_reference()}
    assert all(row["status"] and row["coverage_reason"] for row in statuses)
    assert all(isinstance(row["regional_capitals_count"], int) for row in statuses)
