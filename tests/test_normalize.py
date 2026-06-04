from src.normalize import empty_month_record, month_key, parse_number


def test_month_key_handles_common_labels():
    assert month_key("January") == "jan"
    assert month_key("Sept.") == "sep"
    assert month_key("Annual") is None


def test_parse_number_handles_unicode_minus_and_missing_values():
    assert parse_number("−12.5 °C") == -12.5
    assert parse_number("1,234.6 mm") == 1234.6
    assert parse_number("—") is None


def test_empty_month_record_contains_all_months_and_annual():
    record = empty_month_record("Rainfall", "mm", "source")
    assert record["metric_name"] == "Rainfall"
    assert record["jan"] is None
    assert record["dec"] is None
    assert record["annual"] is None
    assert record["source"] == "source"
