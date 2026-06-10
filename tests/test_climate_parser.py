from src.climate_parser import (
    parse_climate_classification, parse_climate_data, parse_html_climate_tables, parse_weather_box_wikitext,
)

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
    assert status == "no supported climate table found"

BRATISLAVA_RENDERED_TABLE = """
<table class="wikitable">
<caption>Climate data for <a>Bratislava Airport</a> (1991–2020 normals)</caption>
<tr><th>Month</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>Year</th></tr>
<tr><th>Record high °C (°F)</th><td>19.8 (67.6)</td><td>19.7 (67.5)</td><td>25.0 (77.0)</td><td>30.3 (86.5)</td><td>33.4 (92.1)</td><td>36.3 (97.3)</td><td>38.2 (100.8)</td><td>39.4 (102.9)</td><td>34.0 (93.2)</td><td>28.0 (82.4)</td><td>21.6 (70.9)</td><td>17.9 (64.2)</td><td>39.4 (102.9)</td></tr>
<tr><th>Daily mean °C (°F)</th><td>0.3 (32.5)</td><td>1.9 (35.4)</td><td>6.1 (43.0)</td><td>11.7 (53.1)</td><td>16.2 (61.2)</td><td>20.2 (68.4)</td><td>22.0 (71.6)</td><td>21.5 (70.7)</td><td>16.2 (61.2)</td><td>10.7 (51.3)</td><td>5.7 (42.3)</td><td>1.1 (34.0)</td><td>11.1 (52.0)</td></tr>
<tr><th>Average precipitation mm (inches)</th><td>37.4 (1.47)</td><td>32.9 (1.30)</td><td>36.8 (1.45)</td><td>35.9 (1.41)</td><td>58.6 (2.31)</td><td>59.2 (2.33)</td><td>61.8 (2.43)</td><td>60.5 (2.38)</td><td>58.6 (2.31)</td><td>43.6 (1.72)</td><td>46.2 (1.82)</td><td>42.7 (1.68)</td><td>574.3 (22.61)</td></tr>
</table>
"""

BUDAPEST_RENDERED_TABLE = """
<table class="wikitable">
<caption>Climate data for Budapest, 1991–2020, (extremes 1870-present)</caption>
<tr><th>Month</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th><th>Year</th></tr>
<tr><th>Average daily maximum °C (°F)</th><td>3.0 (37.4)</td><td>5.8 (42.4)</td><td>11.3 (52.3)</td><td>17.9 (64.2)</td><td>22.6 (72.7)</td><td>26.2 (79.2)</td><td>28.1 (82.6)</td><td>28.0 (82.4)</td><td>22.5 (72.5)</td><td>16.4 (61.5)</td><td>9.4 (48.9)</td><td>3.5 (38.3)</td><td>16.2 (61.2)</td></tr>
<tr><th>Daily mean °C (°F)</th><td>0.0 (32.0)</td><td>2.0 (35.6)</td><td>6.6 (43.9)</td><td>12.4 (54.3)</td><td>16.9 (62.4)</td><td>20.7 (69.3)</td><td>22.5 (72.5)</td><td>22.3 (72.1)</td><td>16.9 (62.4)</td><td>11.3 (52.3)</td><td>5.9 (42.6)</td><td>0.8 (33.4)</td><td>11.5 (52.7)</td></tr>
<tr><th>Average precipitation days (≥ 1.0 mm)</th><td>6</td><td>6</td><td>5.7</td><td>5.7</td><td>8</td><td>6.6</td><td>6.4</td><td>5.6</td><td>5.6</td><td>6.7</td><td>7.1</td><td>6.8</td><td>76.2</td></tr>
</table>
"""


def test_bratislava_rendered_html_regression_returns_climate_rows():
    rows = parse_html_climate_tables(BRATISLAVA_RENDERED_TABLE, "https://en.wikipedia.org/wiki/Bratislava")

    assert rows
    daily_mean = next(row for row in rows if row["metric_name"] == "Daily mean °C (°F)")
    assert daily_mean["jan"] == 0.3
    assert daily_mean["jul"] == 22.0


def test_budapest_rendered_html_regression_returns_climate_rows():
    rows = parse_html_climate_tables(BUDAPEST_RENDERED_TABLE, "https://en.wikipedia.org/wiki/Budapest")

    assert rows
    max_temp = next(row for row in rows if row["metric_name"] == "Average daily maximum °C (°F)")
    assert max_temp["jan"] == 3.0
    assert max_temp["aug"] == 28.0


def test_html_parser_chooses_climate_table_over_unrelated_monthly_table():
    html = """
    <table><caption>Population by month</caption>
      <tr><th>Month</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th></tr>
      <tr><th>Population</th><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>10</td><td>11</td><td>12</td></tr>
    </table>
    """ + BUDAPEST_RENDERED_TABLE

    rows = parse_html_climate_tables(html, "https://en.wikipedia.org/wiki/Budapest")

    assert rows[0]["metric_name"] == "Average daily maximum °C (°F)"


def test_parse_climate_classification_prefers_wikipedia_description_for_bogota():
    from src.climate_parser import parse_climate_classification

    parsed = parse_climate_classification(
        "== Climate ==\nBogotá has a subtropical highland climate (Köppen Cfb) with mild conditions.",
        "",
    )

    assert parsed["code"] == "Cfb"
    assert parsed["description"] == "Subtropical highland climate"
    assert "Oceanic" not in parsed["description"]


def test_classification_keeps_textual_description_without_koppen_code():
    from src.climate_parser import parse_climate_classification

    parsed = parse_climate_classification(
        "== Climate ==\nThe city has a humid subtropical climate with warm summers.",
        "",
    )

    assert parsed["description"] == "Humid subtropical climate"


def test_tropical_highland_description_overrides_temperate_code_group():
    parsed = parse_climate_classification(
        "== Climate ==\nBogotá has a tropical highland climate (Köppen Cfb).",
        "",
    )

    assert parsed["description"] == "Tropical highland climate"
    assert parsed["primary_koppen_code"] == "Cfb"
    assert parsed["climate_group"] == "Highland / Mountain"


def test_classification_reads_nearby_text_around_rendered_climate_table():
    html = """
    <h2>Climate</h2><p>The capital has a cold semi-arid climate.</p>
    <table><caption>Climate data for Example</caption><tr><th>Temperature</th></tr></table>
    """

    assert parse_climate_classification("", html)["description"] == "Cold semi-arid climate"


def test_classification_infers_readable_label_from_case_insensitive_koppen_code():
    parsed = parse_climate_classification("== Climate ==\nThe Köppen classification is bwh.", "")

    assert parsed["code"] == "Bwh"
    assert parsed["description"] == "Hot desert climate"
    assert parsed["climate_group"] == "Dry / Arid"


def test_weather_data_and_climate_normals_captions_are_supported():
    for caption in ("Weather data for Example", "Climate normals for Example"):
        html = f"""
        <table><caption>{caption}</caption>
          <tr><th>Month</th><th>Jan</th><th>Feb</th><th>Mar</th><th>Apr</th><th>May</th><th>Jun</th><th>Jul</th><th>Aug</th><th>Sep</th><th>Oct</th><th>Nov</th><th>Dec</th></tr>
          <tr><th>Average low °C</th><td>1</td><td>2</td><td>3</td><td>4</td><td>5</td><td>6</td><td>7</td><td>8</td><td>9</td><td>10</td><td>11</td><td>12</td></tr>
        </table>
        """
        assert parse_html_climate_tables(html)
