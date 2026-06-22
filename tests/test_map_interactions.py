import json
from pathlib import Path

from app import climate_dataframe, merge_capital_details, update_selected_city_from_map
from src.capitals import city_marker_id
from src.locations import load_all_capitals, load_climate_zones, load_koppen_climate_zones, validate_koppen_zone_features
from src.map_view import (
    CLIMATE_LAYER_MODES,
    build_city_map,
    clicked_marker_id,
    climate_legend_html,
    marker_click_token,
    marker_id,
)


def test_marker_ids_prefer_qid_and_fallback_includes_admin_region():
    assert city_marker_id({"qid": "Q123", "name": "Example"}) == "Q123"
    first = {"name": "Springfield", "country": "Example", "administrative_region": "North"}
    second = {"name": "Springfield", "country": "Example", "administrative_region": "South"}
    assert city_marker_id(first) == "local:example:north:springfield"
    assert city_marker_id(first) != city_marker_id(second)


def test_marker_click_updates_shared_session_selection():
    city = {"qid": "Q123", "name": "Example", "country": "Exampleland"}
    map_state = {"last_object_clicked_popup": f"<span>{marker_click_token(city)}</span>"}
    state = {"selected_city_id": None, "capital_selector": None}
    assert clicked_marker_id(map_state) == "Q123"
    assert update_selected_city_from_map(map_state, {"Q123"}, state) is True
    assert state["selected_city_id"] == "Q123"
    assert state["capital_selector"] is None  # synchronized before the next widget render


def test_unknown_or_unstructured_marker_click_does_not_replace_selection():
    state = {"selected_city_id": "Q1", "capital_selector": "Q1"}
    assert update_selected_city_from_map({"last_object_clicked_popup": "City text only"}, {"Q1"}, state) is False
    assert update_selected_city_from_map(
        {"last_object_clicked_tooltip": "cityclimate://city/Q999"}, {"Q1"}, state,
    ) is False
    assert state["selected_city_id"] == "Q1"


def test_map_marker_embeds_structured_id_and_keeps_popup_compact():
    city = next(city for city in load_all_capitals() if city.get("latitude") is not None)
    html = build_city_map([city]).get_root().render()
    assert marker_click_token(city) in html
    assert "Click marker to view climate details" in html
    assert "<th>Jan</th>" not in html
    assert "Broad group:" in html and "Primary Köppen code:" in html


def test_marker_and_dropdown_paths_resolve_identical_detail_table():
    base_city = load_all_capitals()[0]
    city = merge_capital_details(base_city, {**base_city, "climate_data": [{"metric_name": "Rainfall", "unit": "mm", "jan": 1, "annual": 12}]})
    city_id = marker_id(city)
    map_state = {"last_object_clicked_tooltip": marker_click_token(city)}
    state = {"selected_city_id": None, "capital_selector": None}
    update_selected_city_from_map(map_state, {city_id}, state)
    by_id = {city_id: city}
    marker_selected = by_id[state["selected_city_id"]]
    dropdown_selected = by_id[city_id]
    assert marker_selected == dropdown_selected
    assert climate_dataframe(marker_selected).equals(climate_dataframe(dropdown_selected))


def test_dropdown_labels_expose_ascii_alias_without_changing_canonical_name():
    from app import _city_option_label

    krakow = next(city for city in load_all_capitals() if city["name"] == "Kraków")
    label = _city_option_label(krakow)
    assert label.startswith("Kraków — Poland")
    assert "also: Krakow" in label


def test_layer_modes_local_geojson_and_legends_are_valid():
    assert CLIMATE_LAYER_MODES == ("None", "Broad groups", "Köppen types")
    broad = load_climate_zones()
    detailed = load_koppen_climate_zones()
    assert broad["features"] and detailed["features"]
    assert detailed["metadata"]["runtime_network_required"] is False
    assert detailed["metadata"]["license"] == "CC BY 4.0"
    assert validate_koppen_zone_features(detailed) == []
    for feature in detailed["features"]:
        properties = feature["properties"]
        assert properties["koppen_code"]
        assert properties["koppen_name"]
        assert properties["climate_group"]
    broad_legend = climate_legend_html("Broad groups", detailed)
    detailed_legend = climate_legend_html("Köppen types", detailed)
    assert "Tropical" in broad_legend and "Unknown" in broad_legend
    assert "A — Tropical" in detailed_legend and "E — Polar" in detailed_legend
    assert "background:rgba(255,255,255,.96);color:#111827" in detailed_legend
    assert ".map-legend *{color:#111827 !important}" in detailed_legend


def test_each_layer_mode_renders_expected_local_layer():
    cities = load_all_capitals()[:2]
    broad = load_climate_zones()
    detailed = load_koppen_climate_zones()
    none_html = build_city_map(cities, climate_zones=broad, climate_zone_mode="None", detailed_climate_zones=detailed).get_root().render()
    broad_html = build_city_map(cities, climate_zones=broad, climate_zone_mode="Broad groups", detailed_climate_zones=detailed).get_root().render()
    detailed_html = build_city_map(cities, climate_zones=broad, climate_zone_mode="Köppen types", detailed_climate_zones=detailed).get_root().render()
    assert "Detailed Köppen climate types" not in none_html and "Broad climate zones" not in none_html
    assert "Broad climate zones" in broad_html and "Detailed Köppen climate types" not in broad_html
    assert "Detailed" in detailed_html and "koppen_code" in detailed_html


def test_selector_is_in_details_column_and_no_optional_city_loader_returns():
    source = Path("app.py").read_text(encoding="utf-8")
    details_block = source.index("with col_details:")
    selector = source.index('"Select a capital or regional capital"')
    details_header = source.index('st.subheader("Capital details")', selector)
    map_block = source.index("with col_map:", details_header)
    assert details_block < selector < details_header < map_block
    assert '"Select a capital"' not in source
    assert "Load cached cities for selected country" not in source
    assert "Additional city limit" not in source
    assert "load_koppen_climate_zones()" in source
    assert "fetch_article" not in source


def test_koppen_asset_is_precomputed_and_has_source_metadata():
    payload = json.loads(Path("data/preloaded/koppen_climate_zones_simplified.geojson").read_text(encoding="utf-8"))
    assert payload["metadata"]["source_doi"] == "10.6084/m9.figshare.6396959.v2"
    assert payload["metadata"]["commercial_use_status"] == "permitted with attribution"
    assert len(payload["features"]) >= 20


def test_country_boundaries_load_locally_and_match_representative_countries():
    from src.locations import load_country_boundaries
    from src.map_view import country_bounds_for_city, find_country_boundary

    boundaries = load_country_boundaries()
    assert boundaries["metadata"]["runtime_network_required"] is False
    for country in ("United States", "Russia", "Canada", "Australia", "Brazil", "Greenland"):
        city = next(city for city in load_all_capitals() if city.get("country") == country)
        assert find_country_boundary(city, boundaries) is not None
        bounds = country_bounds_for_city(city, boundaries)
        assert bounds and bounds[0][0] < bounds[1][0] and bounds[0][1] < bounds[1][1]


def test_selected_city_map_fits_country_and_falls_back_to_marker_zoom():
    from src.locations import load_country_boundaries

    city = next(city for city in load_all_capitals() if city.get("country") == "United States")
    html = build_city_map([city], marker_id(city), country_boundaries=load_country_boundaries(), selected_city=city).get_root().render()
    assert "fitBounds" in html
    assert "dashArray" in html
    fallback_html = build_city_map([city], marker_id(city), country_boundaries={"features": []}, selected_city=city).get_root().render()
    assert 'zoom": 7' in fallback_html or 'zoom: 7' in fallback_html


def test_selected_country_zoom_does_not_remove_layers_or_selected_marker():
    from src.locations import load_country_boundaries

    cities = load_all_capitals()[:8]
    selected = cities[0]
    html = build_city_map(
        cities, marker_id(selected), climate_zones=load_climate_zones(),
        country_boundaries=load_country_boundaries(), selected_city=selected,
    ).get_root().render()
    assert "fitBounds" in html
    assert "Broad climate zones" in html
    assert "National capitals" in html and marker_click_token(selected) in html


def test_marker_click_and_dropdown_update_selected_country_consistently():
    from app import update_selected_country_state
    from src.monthly_metrics import get_country_overlay_targets

    capitals = load_all_capitals()
    by_id = {marker_id(city): city for city in capitals}
    warsaw = next(city for city in capitals if city["name"] == "Warsaw")
    warsaw_id = marker_id(warsaw)

    marker_state = {"selected_city_id": None, "capital_selector": None}
    assert update_selected_city_from_map(
        {"last_object_clicked_tooltip": marker_click_token(warsaw)}, set(by_id), marker_state, by_id
    )
    dropdown_state = {"selected_city_id": warsaw_id, "capital_selector": warsaw_id}
    update_selected_country_state(by_id[warsaw_id], dropdown_state)

    assert marker_state["selected_country_key"] == dropdown_state["selected_country_key"]
    assert {city["marker_id"] for city in get_country_overlay_targets(capitals, by_id[marker_state["selected_city_id"]])} == {
        city["marker_id"] for city in get_country_overlay_targets(capitals, by_id[dropdown_state["selected_city_id"]])
    }


def test_map_renders_with_missing_optional_metric_and_boundary_caches():
    city = next(city for city in load_all_capitals() if city.get("latitude") is not None)
    html = build_city_map([city], marker_id(city), country_boundaries={"features": []}, selected_city=city, metric_labels={}).get_root().render()
    assert marker_click_token(city) in html
    assert "Selected country metric labels" in html
    assert "fitBounds" not in html


def test_app_map_is_rendered_before_optional_detail_loading_and_diagnostics_hidden():
    source = Path("app.py").read_text(encoding="utf-8")
    assert "Metric overlay diagnostics" not in source
    map_render = source.index("st_folium(")
    optional_detail_load = source.index("load_city_details(selected_city)")
    assert map_render < optional_detail_load
