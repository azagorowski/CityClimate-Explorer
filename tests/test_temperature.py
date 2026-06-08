from app import annual_temperature_dataframe
from src.config import MONTH_LABELS
from src.temperature import UNAVAILABLE_MESSAGE, normalize_monthly_temperature, temperature_chart_rows


def row(name, unit="°C", start=0, annual=999):
    months = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
    return {"metric_name": name, "unit": unit, **{month: start + i for i, month in enumerate(months)}, "annual": annual}


def test_chart_prefers_daily_mean_and_keeps_calendar_order_without_annual():
    data = [row("Daily mean °C", start=-5, annual=1234), row("Average high °C", start=0)]
    normalized = normalize_monthly_temperature(data)
    chart_rows = temperature_chart_rows(data)
    assert normalized["method"] == "reported monthly mean"
    assert [item["Month"] for item in chart_rows] == MONTH_LABELS
    assert [item["Temperature"] for item in chart_rows] == list(range(-5, 7))
    assert 1234 not in [item["Temperature"] for item in chart_rows]


def test_chart_computes_mean_only_from_matching_high_and_low_rows():
    data = [row("Average daily maximum °C", start=10), row("Average daily minimum °C", start=0)]
    normalized = normalize_monthly_temperature(data)
    assert normalized["method"] == "average of reported high and low"
    assert normalized["monthly_temperature_mean"][0] == 5
    assert normalized["temperature_unit"] == "°C"


def test_chart_supports_unicode_minus_references_and_fahrenheit_fallback():
    data = [row("Average temperature °F", unit="°F")]
    data[0]["jan"] = "−4.5[1]\u00a0"
    normalized = normalize_monthly_temperature(data)
    assert normalized["monthly_temperature_mean"][0] == -4.5
    assert normalized["temperature_unit"] == "°F"


def test_chart_unavailable_without_real_temperature_rows():
    assert normalize_monthly_temperature([row("Average precipitation mm", unit="mm")]) is None
    assert temperature_chart_rows([]) == []
    assert UNAVAILABLE_MESSAGE == "Annual temperature chart unavailable because monthly temperature data was not found."


def test_app_chart_dataframe_matches_selection_pipeline():
    frame = annual_temperature_dataframe({"climate_data": [row("Mean daily temperature °C", start=1)]})
    assert frame["Month"].tolist() == MONTH_LABELS
    assert len(frame) == 12
