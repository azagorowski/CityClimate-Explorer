from pathlib import Path

from app import annual_temperature_dataframe
from src.config import MONTH_LABELS
from src.temperature import (
    UNAVAILABLE_MESSAGE,
    normalize_monthly_temperature,
    normalize_monthly_temperatures_to_celsius,
    temperature_chart_rows,
)


def row(name, unit="°C", start=0, annual=999):
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    return {"metric_name": name, "unit": unit, **{month: start + i for i, month in enumerate(months)}, "annual": annual}


def test_celsius_fixture_stays_celsius_and_keeps_month_order_without_annual():
    data = [row("Daily mean °C", start=-5, annual=1234), row("Average high °C", start=0)]
    normalized = normalize_monthly_temperatures_to_celsius(data)
    chart_rows = temperature_chart_rows(data)
    assert normalized["method"] == "reported monthly mean"
    assert normalized["conversion_applied"] is False
    assert normalized["temperature_unit"] == "°C"
    assert [item["Month"] for item in chart_rows] == MONTH_LABELS
    assert [item["Temperature (°C)"] for item in chart_rows] == list(range(-5, 7))
    assert 1234 not in [item["Temperature (°C)"] for item in chart_rows]


def test_fahrenheit_only_fixture_is_converted_before_charting():
    data = [row("Average temperature °F", unit="°F", start=32)]
    normalized = normalize_monthly_temperature(data)
    values = [item["Temperature (°C)"] for item in temperature_chart_rows(data)]
    assert normalized["conversion_applied"] is True
    assert normalized["temperature_unit"] == "°C"
    assert values[0] == 0.0
    assert values[9] == 5.0
    assert all(item["Unit"] == "°C" for item in temperature_chart_rows(data))


def test_mixed_units_prefer_direct_celsius_mean():
    data = [row("Average temperature °F", unit="°F", start=50), row("Daily mean °C", unit="°C", start=2)]
    normalized = normalize_monthly_temperature(data)
    assert normalized["source_row_used"] == "Daily mean °C"
    assert normalized["monthly_temperature_mean_c"][0] == 2
    assert normalized["conversion_applied"] is False


def test_chart_computes_celsius_mean_from_matching_fahrenheit_high_and_low():
    data = [row("Average daily maximum °F", unit="°F", start=50), row("Average daily minimum °F", unit="°F", start=32)]
    normalized = normalize_monthly_temperature(data)
    assert normalized["method"] == "average of high and low converted from °F"
    assert normalized["monthly_temperature_mean_c"][0] == 5.0


def test_chart_excludes_non_mean_and_record_temperature_rows():
    assert normalize_monthly_temperature([row("Record high °C"), row("Average precipitation mm", unit="mm")]) is None
    assert temperature_chart_rows([]) == []
    assert UNAVAILABLE_MESSAGE == "Annual temperature chart unavailable because monthly temperature data was not found."


def test_app_chart_dataframe_and_labels_are_celsius_only():
    frame = annual_temperature_dataframe({"climate_data": [row("Mean daily temperature °F", unit="°F", start=32)]})
    assert frame["Month"].tolist() == MONTH_LABELS
    assert frame.columns.tolist() == ["Month", "Month order", "Temperature (°C)", "Unit"]
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'title="Temperature (°C)"' in source
    assert 'alt.Tooltip("Temperature (°C):Q", title="Temperature (°C)"' in source
