import logging

import pytest

from app import climate_dataframe
from src.annual_values import calculate_annual_value, parse_climate_number, populate_annual_values
from src.config import MONTHS
from src.temperature import temperature_chart_rows


def climate_row(metric, values, unit="", annual=None):
    return {
        "metric_name": metric,
        "unit": unit,
        **dict(zip(MONTHS, values, strict=True)),
        "annual": annual,
    }


@pytest.mark.parametrize(
    ("metric", "unit"),
    [("Average C", "°C"), ("High C", "°C"), ("Low C", "°C")],
)
def test_temperature_rows_calculate_annual_mean(metric, unit):
    assert calculate_annual_value(metric, unit, list(range(1, 13))) == 6.5


@pytest.mark.parametrize(
    ("metric", "unit", "expected"),
    [
        ("Precipitation mm", "mm", 78),
        ("Precipitation days", "days", 78.0),
        ("Humidity", "%", 6.5),
        ("Sun", "hours", 78),
        ("Sunshine hours", "hours", 78),
    ],
)
def test_metric_appropriate_annual_aggregation(metric, unit, expected):
    assert calculate_annual_value(metric, unit, list(range(1, 13))) == expected


def test_source_annual_is_preserved_and_provenance_is_recorded():
    row = climate_row("Average C", list(range(12)), "°C", "99.9[1]")
    enriched = populate_annual_values([row])[0]
    assert enriched["annual"] == "99.9[1]"
    assert enriched["annual_value_source"] == "source"
    assert enriched["annual_calculation_method"] == "none"


def test_visible_table_regression_populates_none_annual_without_changing_chart_months():
    row = climate_row(
        "Average C",
        ["−2.2", "0.1[1]", 4, 8, 12, 16, 20, 19, 15, 10, 5, "0\xa0"],
        "°C",
    )
    frame = climate_dataframe({"climate_data": [row]})
    chart = temperature_chart_rows(populate_annual_values([row]))
    assert frame.loc[0, "Annual"] == 8.9
    assert frame.loc[0, "Unit"] == "°C"
    assert frame.loc[0, "Annual"] is not None
    assert len(chart) == 12
    assert [point["Month"] for point in chart] == [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]


def test_numeric_parser_handles_annotations_unicode_minus_and_missing_values():
    assert parse_climate_number("−2.2\xa0[12]") == -2.2
    assert parse_climate_number("20.0 °C") == 20.0
    assert parse_climate_number("—") is None
    assert parse_climate_number("N/A") is None
    assert parse_climate_number(None) is None


def test_incomplete_and_unknown_rows_remain_cleanly_unavailable(caplog):
    incomplete = climate_row("Rainfall mm", [1] * 11 + ["N/A"], "mm")
    unknown = climate_row("Wind speed", [1] * 12, "km/h")
    with caplog.at_level(logging.INFO, logger="src.annual_values"):
        rows = populate_annual_values([incomplete, unknown])
    assert [row["annual"] for row in rows] == [None, None]
    assert all(row["annual_value_source"] == "unavailable" for row in rows)
    assert "11 of 12 monthly values are numeric" in caplog.text
