from src.climate_parser import koppen_climate_group, parse_climate_classification
from src.locations import load_all_capitals, load_polar_border_capitals
from src.map_view import CLIMATE_COLORS, build_city_map, climate_group


def test_polar_dataset_has_greenland_and_scandinavian_centers():
    records = load_polar_border_capitals()
    names = {record["name"] for record in records}
    assert {"Nuuk", "Sisimiut", "Ilulissat", "Qaqortoq", "Tasiilaq"} <= names
    assert {"Tromsø", "Bodø", "Vadsø", "Luleå", "Umeå", "Östersund", "Rovaniemi", "Oulu"} <= names


def test_polar_records_have_local_runtime_fields_and_provenance():
    for record in load_polar_border_capitals():
        assert record["latitude"] is not None and record["longitude"] is not None
        assert record["record_scope"] == "polar_border_regional_capital"
        assert record["record_type"] in {"regional_capital", "local_administrative_center"}
        assert record["climate_classification_source_metadata"]["source_url"]
        assert record["provenance"]["metadata_license"] == "CC0 1.0"
        assert record["climate_classification"] or record["climate_extraction_status"]


def test_ordered_koppen_parser_keeps_bordering_code_secondary():
    parsed = parse_climate_classification("== Climate ==\nKöppen: ET, bordering on Cfc.")
    assert parsed["primary_koppen_code"] == "ET"
    assert parsed["secondary_koppen_codes"] == ["Cfc"]
    assert parsed["climate_group"] == "Polar"
    assert parsed["description"].startswith("Tundra climate")


def test_primary_code_wins_over_highland_or_bordering_text():
    parsed = parse_climate_classification("The city has highland influences. Köppen climate classification is Cfb, transitional to ET.")
    assert parsed["primary_koppen_code"] == "Cfb"
    assert parsed["secondary_koppen_codes"] == ["ET"]
    assert parsed["climate_group"] == "Temperate"
    assert koppen_climate_group(parsed["primary_koppen_code"]) == "Temperate"


def test_ushuaia_regression_is_polar_everywhere():
    ushuaia = next(record for record in load_all_capitals() if record["name"] == "Ushuaia")
    assert ushuaia["primary_koppen_code"] == "ET"
    assert ushuaia["secondary_koppen_codes"] == ["Cfc"]
    assert ushuaia["climate_group"] == "Polar"
    assert climate_group(ushuaia) == "Polar"
    assert CLIMATE_COLORS[climate_group(ushuaia)] == CLIMATE_COLORS["Polar"]
    html = build_city_map([ushuaia]).get_root().render()
    assert "Primary Köppen code: ET" in html
    assert "Secondary/bordering codes: Cfc" in html


def test_runtime_combines_local_datasets_without_network_calls(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("runtime loader must not make HTTP requests")
    monkeypatch.setattr("requests.sessions.Session.request", fail)
    capitals = load_all_capitals()
    assert any(city.get("record_scope") == "polar_border_regional_capital" for city in capitals)
