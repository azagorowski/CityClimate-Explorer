from pathlib import Path

import pytest

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


def test_average_c_ui_table_row_is_preferred_and_annual_is_excluded():
    months = {
        "Jan": "0.3[1] °C",
        "Feb": "−2.8\xa0°C",
        "Mar": "<span style=\"display:none\">999</span>3.0 °C",
        "Apr": "4",
        "May": "5.0",
        "Jun": "6",
        "Jul": "7",
        "Aug": "8",
        "Sep": "9",
        "Oct": "10",
        "Nov": "11",
        "Dec": "12",
    }
    average = {"Metric": "  Average (°C)  ", "Unit": "°C", **months, "Annual": "999 °C"}
    daily_mean = row("Daily mean C", start=100)
    normalized = normalize_monthly_temperature([daily_mean, average])
    chart_rows = temperature_chart_rows([daily_mean, average])

    assert normalized is not None
    assert normalized["source_row_used"] == "Average (°C)"
    assert normalized["conversion_applied"] is False
    assert normalized["temperature_unit"] == "°C"
    assert [item["Month"] for item in chart_rows] == MONTH_LABELS
    assert [item["Temperature (°C)"] for item in chart_rows] == [0.3, -2.8, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0]
    assert all(item["Unit"] == "°C" for item in chart_rows)
    assert 999 not in [item["Temperature (°C)"] for item in chart_rows]


def test_average_c_is_used_instead_of_computing_high_low_mean():
    data = [row("High C", start=20), row("Low C", start=0), row("Average C", start=7)]
    normalized = normalize_monthly_temperature(data)

    assert normalized is not None
    assert normalized["source_row_used"] == "Average C"
    assert normalized["source_rows_used"] == ["Average C"]
    assert normalized["monthly_temperature_mean_c"][0] == 7


def test_high_low_celsius_mean_is_only_used_when_average_is_missing():
    data = [row("High C", start=20), row("Low C", start=0)]
    normalized = normalize_monthly_temperature(data)
    chart_rows = temperature_chart_rows(data)

    assert normalized is not None
    assert normalized["source_rows_used"] == ["High C", "Low C"]
    assert normalized["method"] == "average of reported high and low"
    assert normalized["monthly_temperature_mean_c"][0] == 10.0
    assert [item["Month"] for item in chart_rows] == MONTH_LABELS


def test_unavailable_temperature_logs_metrics_units_checks_and_rejections(caplog):
    data = [row("Record high C", unit="°C"), row("Average", unit="mystery")]

    with caplog.at_level("WARNING", logger="src.temperature"):
        assert normalize_monthly_temperature(data) is None

    message = caplog.messages[-1]
    assert "Record high C" in message
    assert "Average C" in message
    assert "mystery" in message
    assert "checked mean labels" in message
    assert "candidate rejections" in message

@pytest.mark.parametrize(
    "label",
    [
        "Average C",
        "Average °C",
        "Average",
        "Avg C",
        "Avg °C",
        "Daily mean C",
        "Daily mean °C",
        "Mean C",
        "Mean °C",
        "Mean daily temperature C",
        "Mean daily temperature °C",
        "  average   ( °C )  ",
    ],
)
def test_supported_average_temperature_labels_are_case_and_format_tolerant(label):
    unit = "°C" if label.strip().casefold() == "average" else None
    normalized = normalize_monthly_temperature([row(label, unit=unit)])

    assert normalized is not None
    assert normalized["temperature_unit"] == "°C"
    assert normalized["conversion_applied"] is False


def test_dual_unit_wikipedia_label_uses_first_displayed_celsius_value():
    data = [row("Daily mean °C (°F)", unit="°F", start=0.3)]
    normalized = normalize_monthly_temperature(data)

    assert normalized is not None
    assert normalized["temperature_unit"] == "°C"
    assert normalized["conversion_applied"] is False
    assert normalized["monthly_temperature_mean_c"][0] == 0.3
