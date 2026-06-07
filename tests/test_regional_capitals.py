import json

from src.locations import TOP_15_COUNTRIES, load_all_capitals, load_climate_zones, load_regional_capitals, load_top15_regional_capitals
from src.map_view import CLIMATE_COLORS, build_city_map, climate_group


def test_regional_cache_covers_top_15_with_required_metadata():
    records = load_top15_regional_capitals()
    assert records
    assert set(TOP_15_COUNTRIES) <= {record["country"] for record in records}
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
    regional = json.load(open("data/preloaded/regional_capitals_top15_countries.json", encoding="utf-8"))
    zones = json.load(open("data/preloaded/climate_zones_simplified.geojson", encoding="utf-8"))
    assert regional["source_metadata"]["runtime_network_required"] is False
    assert zones["metadata"]["commercial_use_status"] == "permitted"
