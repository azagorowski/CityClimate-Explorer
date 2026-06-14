from src.locations import load_all_capitals
from src.monthly_metrics import format_overlay_value, load_monthly_metrics_cache, overlay_values


def test_local_monthly_metric_cache_has_regression_cities():
    cities = {city["name"]: city["marker_id"] for city in load_all_capitals()}
    cache = load_monthly_metrics_cache()
    for name in ("Kraków", "Stavanger", "Murmansk", "Puno", "Bogotá", "Cairo", "Tripoli", "Kyiv", "Tehran"):
        values = overlay_values({cities[name]}, "average_temperature_c", "jan", cache)
        assert cities[name] in values
        assert values[cities[name]][1] == "°C"


def test_overlay_omits_missing_values_and_formats_units():
    assert overlay_values({"missing"}, "average_temperature_c", "jan") == {}
    assert format_overlay_value(0.3, "°C") == "0.3 °C"
    assert "None" not in format_overlay_value("", "mm")
