from src.climate_parser import parse_climate_data, parse_html_climate_tables, parse_weather_box_wikitext

SAMPLE_WEATHER_BOX = """
{{Weather box
|location = Example City
|metric first = yes
|single line = yes
|Jan high C = 10
|Feb high C = 12
|Mar high C = 15
|Apr high C = 18
|May high C = 22
|Jun high C = 27
|Jul high C = 30
|Aug high C = 29
|Sep high C = 25
|Oct high C = 20
|Nov high C = 14
|Dec high C = 11
|Jan precipitation mm = 50
|Feb precipitation mm = 45
|Mar precipitation mm = 40
|Apr precipitation mm = 55
|May precipitation mm = 60
|Jun precipitation mm = 35
|Jul precipitation mm = 20
|Aug precipitation mm = 22
|Sep precipitation mm = 30
|Oct precipitation mm = 65
|Nov precipitation mm = 70
|Dec precipitation mm = 80
|source = National climate normal
}}
"""


def test_parse_weather_box_wikitext_extracts_monthly_metrics():
    rows = parse_weather_box_wikitext(SAMPLE_WEATHER_BOX, "https://example.test/wiki/Example")
    names = {row["metric_name"] for row in rows}
    assert "High C" in names
    assert "Precipitation mm" in names
    high = next(row for row in rows if row["metric_name"] == "High C")
    assert high["jan"] == 10.0
    assert high["dec"] == 11.0
    assert high["unit"] == "°C"


def test_parse_html_climate_tables_fallback():
    html = """
    <table><caption>Climate data for Example</caption>
      <tr><th>Month</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th></tr>
      <tr><th>Average precipitation mm</th><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>10</td><td>11</td><td>12</td></tr>
    </table>
    """
    rows = parse_html_climate_tables(html, "https://example.test")
    assert len(rows) == 1
    assert rows[0]["metric_name"] == "Average precipitation mm"
    assert rows[0]["jan"] == 1.0
    assert rows[0]["dec"] == 12.0


def test_parse_climate_data_handles_missing_fields_gracefully():
    rows, status = parse_climate_data("No climate template", "<p>No useful table</p>", "https://example.test")
    assert rows == []
    assert status == "climate data unavailable"
