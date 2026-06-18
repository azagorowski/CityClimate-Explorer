import math

from src.locations import load_all_capitals
from src.monthly_metrics import (
    format_overlay_value,
    get_monthly_metric_for_city,
    load_monthly_metrics_cache,
    normalize_month_key,
    normalized_metric_key,
    overlay_diagnostics,
    overlay_values,
    resolve_monthly_metric_value,
)


def _metric(key="Average C", month_key="May", value=12.5):
    return {"metric_key": key, "unit": "°C", "monthly_values": {month_key: value}}


def test_local_monthly_metric_cache_has_regression_cities():
    cities = {city["name"]: city for city in load_all_capitals()}
    cache = load_monthly_metrics_cache()
    for name in ("Kraków", "Stavanger", "Rovaniemi", "Luleå", "Kyiv", "Tehran", "Puno", "Murmansk", "Bogotá", "Cairo"):
        values = overlay_values([cities[name]], "Average temperature", "May", cache)
        assert cities[name]["marker_id"] in values
        assert values[cities[name]["marker_id"]][1] == "°C"


def test_lookup_prefers_id_then_supports_qid_and_normalized_fallbacks():
    city = {"marker_id": "runtime-id", "qid": "Q42", "name": "São Teste", "country": "Test Land", "administrative_region": "North"}
    for record in (
        {"city_id": "runtime-id", "metrics": [_metric()]},
        {"city_id": "old-id", "qid": "Q42", "metrics": [_metric()]},
        {"city_id": "old-id", "city": "Sao Teste", "country": "Test Land", "metrics": [_metric()]},
        {"city_id": "old-id", "city": "Sao Teste", "country": "Test Land", "administrative_region": "North", "metrics": [_metric()]},
    ):
        value, unit, _match = get_monthly_metric_for_city(city, "average_temperature_c", "may", [record])
        assert (value, unit) == (12.5, "°C")


def test_old_metric_and_full_month_names_are_normalized_without_annual():
    assert normalized_metric_key("Average °C") == "average_temperature_c"
    assert normalized_metric_key("Daily mean C") == "average_temperature_c"
    assert normalized_metric_key("Mean C") == "average_temperature_c"
    assert normalized_metric_key("Sun") == "sunshine_hours"
    assert normalized_metric_key("Sunshine hours") == "sunshine_hours"
    assert normalize_month_key("February") == "feb"
    assert normalize_month_key("Annual") is None
    city = {"marker_id": "x"}
    record = {"city_id": "x", "metrics": [_metric(month_key="January")]}
    assert get_monthly_metric_for_city(city, "Average temperature", "Jan", [record])[:2] == (12.5, "°C")
    assert get_monthly_metric_for_city(city, "Average temperature", "Annual", [record])[0] is None


def test_average_temperature_falls_back_to_local_parsed_rows():
    city = {"marker_id": "x", "climate_data": [
        {"metric_name": "High C", "unit": "°C", **{month: 20 for month in ("jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec")}},
        {"metric_name": "Low C", "unit": "°C", **{month: 10 for month in ("jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec")}},
    ]}
    assert get_monthly_metric_for_city(city, "Average temperature", "May", [])[0:2] == (15.0, "°C")


def test_resolver_uses_selected_parsed_table_cache_by_qid():
    city = {"marker_id": "generated-regional-id", "qid": "Q123", "name": "Regional City", "country": "Testland"}
    table_cache = {"old-id": {
        "qid": "Q123",
        "climate_data": [{"metric_name": "Average C", "unit": "°C", "May": "8.5"}],
    }}
    resolved, reason = resolve_monthly_metric_value(
        city, "Average temperature", "may", metrics_cache=[], table_cache=table_cache
    )
    assert reason == ""
    assert resolved == (8.5, "°C", "parsed climate table cache (qid)")


def test_resolver_uses_normalized_city_country_table_cache():
    city = {"marker_id": "new-id", "name": "İstanbul", "country": "Türkiye"}
    table_cache = {"legacy-id": {
        "city": "Istanbul", "country": "Türkiye",
        "climate_table": {"rows": [{"Metric": "Mean daily temperature C", "January": 6.5}]},
    }}
    assert get_monthly_metric_for_city(
        city, "Average temperature", "January", [], table_cache
    )[:2] == (6.5, "°C")


def test_diagnostics_group_missing_reasons():
    cities = [
        {"marker_id": "known"},
        {"marker_id": "unknown"},
    ]
    diagnostics = overlay_diagnostics(
        cities, "Average temperature", "May",
        [{"city_id": "known", "metrics": [_metric(value=None)]}],
    )
    assert diagnostics.visible_markers == 2
    assert diagnostics.labels_rendered == 0
    assert diagnostics.missing_reasons == {"non-numeric value": 1, "no city key match": 1}


def test_overlay_omits_non_numeric_values_and_formats_units():
    assert overlay_values({"missing"}, "average_temperature_c", "jan") == {}
    assert format_overlay_value(0.3, "°C") == "0.3 °C"
    assert format_overlay_value(58.6, "mm") == "58.6 mm"
    assert format_overlay_value(10, "days") == "10 days"
    assert format_overlay_value(236, "hours") == "236 h"
    assert format_overlay_value(75, "%") == "75%"
    for value in (None, "None", "nan", math.nan, ""):
        assert format_overlay_value(value, "mm") == ""


def test_overlay_targets_all_visible_cities_in_selected_country_not_only_selection():
    from src.monthly_metrics import get_overlay_target_cities

    warsaw = {"marker_id": "warsaw", "name": "Warsaw", "country": "Poland"}
    krakow = {"marker_id": "krakow", "name": "Kraków", "country": "Poland"}
    gdansk = {"marker_id": "gdansk", "name": "Gdańsk", "country": "Poland"}
    berlin = {"marker_id": "berlin", "name": "Berlin", "country": "Germany"}

    targets = get_overlay_target_cities([warsaw, krakow, gdansk, berlin], warsaw)

    assert {city["marker_id"] for city in targets} == {"warsaw", "krakow", "gdansk"}
    assert len(targets) > 1


def test_overlay_targets_regression_countries_from_loaded_visible_records():
    from src.monthly_metrics import get_overlay_target_cities

    capitals = load_all_capitals()
    by_name = {city["name"]: city for city in capitals}
    regression = {
        "Warsaw": "Poland",
        "Kraków": "Poland",
        "Stavanger": "Norway",
        "Kyiv": "Ukraine",
        "Tehran": "Iran",
    }
    for selected_name, country in regression.items():
        visible_country_cities = [city for city in capitals if city.get("country") == country]
        targets = get_overlay_target_cities(capitals, by_name[selected_name])
        assert {city["marker_id"] for city in targets} == {
            city["marker_id"] for city in visible_country_cities
        }
        assert by_name[selected_name]["marker_id"] in {city["marker_id"] for city in targets}
        if len(visible_country_cities) > 1:
            assert len(targets) > 1



def test_poland_regression_selections_have_multiple_january_labels():
    from src.monthly_metrics import get_metric_overlay_scope

    capitals = load_all_capitals()
    cache = load_monthly_metrics_cache()
    by_name = {city["name"]: city for city in capitals}
    for selected_name in ("Warsaw", "Kraków", "Gdańsk"):
        targets = get_metric_overlay_scope(capitals, by_name[selected_name])
        values = overlay_values(targets, "Average temperature", "Jan", cache)
        assert {by_name[name]["marker_id"] for name in ("Warsaw", "Kraków", "Gdańsk")} <= set(values)
        assert len(values) > 1
        assert set(values) != {by_name[selected_name]["marker_id"]}

def test_overlay_targets_respect_pre_filtered_visible_records():
    from src.monthly_metrics import get_overlay_target_cities

    selected = {
        "marker_id": "warsaw", "country": "Poland",
        "continent": "Europe", "climate_classification": "Dfb",
    }
    visible_after_filters = [
        selected,
        {
            "marker_id": "krakow", "country": "Poland",
            "continent": "Europe", "climate_classification": "Dfb",
        },
        # Hidden by an upstream climate/record filter, so not in visible_after_filters:
        # {"marker_id": "gdansk", "country": "Poland", "climate_classification": "Cfb"},
        {
            "marker_id": "berlin", "country": "Germany",
            "continent": "Europe", "climate_classification": "Dfb",
        },
    ]

    assert [city["marker_id"] for city in get_overlay_target_cities(visible_after_filters, selected)] == [
        "warsaw", "krakow",
    ]


def test_country_overlay_matching_supports_aliases_and_stable_ids():
    from src.monthly_metrics import get_overlay_target_cities, same_country

    assert same_country({"country": "Turkey"}, {"country": "Türkiye"})
    assert same_country({"country": "RSA"}, {"country": "South Africa"})
    assert same_country({"country": "Czech Republic"}, {"country": "Czechia"})
    assert same_country({"country": "USA"}, {"country": "United States"})
    assert same_country({"country": "UK"}, {"country": "United Kingdom"})
    selected = {"marker_id": "selected", "country": "Legacy Name", "country_qid": "Q999"}
    assert get_overlay_target_cities([
        {"marker_id": "same", "country": "Different Label", "country_qid": "Q999"},
        {"marker_id": "other", "country": "Legacy Name", "country_qid": "Q1"},
    ], selected) == [{"marker_id": "same", "country": "Different Label", "country_qid": "Q999"}]


def test_overlay_values_uses_fallback_keys_for_each_country_target_and_omits_missing():
    from src.monthly_metrics import get_overlay_target_cities

    selected = {"marker_id": "warsaw", "name": "Warsaw", "country": "Poland"}
    krakow = {"marker_id": "runtime-krakow", "qid": "Q31487", "name": "Kraków", "country": "Poland"}
    gdansk = {
        "marker_id": "runtime-gdansk", "name": "Gdańsk",
        "country": "Poland", "administrative_region": "Pomeranian",
    }
    berlin = {"marker_id": "berlin", "name": "Berlin", "country": "Germany"}
    targets = get_overlay_target_cities([selected, krakow, gdansk, berlin], selected)
    values = overlay_values(targets, "Average temperature", "May", [
        {"city_id": "warsaw", "metrics": [_metric(value=9)]},
        {"city_id": "old", "qid": "Q31487", "metrics": [_metric(value=9.2)]},
        {
            "city": "Gdansk", "country": "Poland",
            "administrative_region": "Pomeranian", "metrics": [_metric(value=None)],
        },
    ])

    assert values == {"warsaw": (9.0, "°C"), "runtime-krakow": (9.2, "°C")}
    assert "runtime-gdansk" not in values
    assert all(format_overlay_value(value, unit) for value, unit in values.values())


def test_no_selected_city_targets_all_visible_cities_and_diagnostics_ui_removed():
    from pathlib import Path
    from src.monthly_metrics import get_overlay_target_cities

    visible = [{"marker_id": "a", "country": "A"}, {"marker_id": "b", "country": "B"}]
    assert get_overlay_target_cities(visible, None) == visible
    assert "Metric overlay diagnostics" not in Path("app.py").read_text()
