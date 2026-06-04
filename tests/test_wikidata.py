import pytest

requests = pytest.importorskip("requests")

from src import wikidata


class DummyResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {"results": {"bindings": []}}

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error

    def json(self):
        return self._payload


class DummySession:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def get(self, *args, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def binding(qid, name, population, coord, instance_qids):
    return {
        "city": {"value": f"http://www.wikidata.org/entity/{qid}"},
        "cityLabel": {"value": name},
        "countryLabel": {"value": "Exampleland"},
        "population": {"value": str(population)},
        "coord": {"value": coord},
        "instanceOfQids": {"value": ",".join(instance_qids)},
        "instanceOfLabels": {"value": "|".join(instance_qids)},
    }


def test_request_retries_timeout_then_succeeds(monkeypatch):
    session = DummySession([
        requests.exceptions.Timeout("read timed out"),
        DummyResponse(payload={"ok": True}),
    ])
    monkeypatch.setattr(wikidata, "_SESSION", session)
    monkeypatch.setattr(wikidata.time, "sleep", lambda _: None)
    monkeypatch.setattr(wikidata.random, "uniform", lambda *_: 0)

    assert wikidata._request_with_retries({"query": "SELECT * WHERE {}"}) == {"ok": True}
    assert session.calls == 2


def test_request_retries_transient_http_status(monkeypatch):
    session = DummySession([
        DummyResponse(status_code=503),
        DummyResponse(payload={"ok": True}),
    ])
    monkeypatch.setattr(wikidata, "_SESSION", session)
    monkeypatch.setattr(wikidata.time, "sleep", lambda _: None)
    monkeypatch.setattr(wikidata.random, "uniform", lambda *_: 0)

    assert wikidata._request_with_retries({"query": "SELECT * WHERE {}"}) == {"ok": True}
    assert session.calls == 2


def test_request_final_failure_has_helpful_message(monkeypatch):
    session = DummySession([
        requests.exceptions.Timeout("first timeout"),
        requests.exceptions.Timeout("second timeout"),
        requests.exceptions.Timeout("third timeout"),
    ])
    monkeypatch.setattr(wikidata, "_SESSION", session)
    monkeypatch.setattr(wikidata.time, "sleep", lambda _: None)
    monkeypatch.setattr(wikidata.random, "uniform", lambda *_: 0)

    try:
        wikidata._request_with_retries({"query": "SELECT * WHERE {}"})
    except wikidata.WikidataRequestError as exc:
        message = str(exc)
    else:
        raise AssertionError("Expected WikidataRequestError")

    assert "Wikidata request failed after" in message
    assert "third timeout" in message
    assert session.calls == 3


def test_rows_to_cities_filters_countries_and_administrative_regions():
    rows = [
        binding("Q90", "Paris", 2_100_000, "Point(2.3522 48.8566)", ["Q515"]),
        binding("Q142", "France", 68_000_000, "Point(2 47)", ["Q6256"]),
        binding("Q99", "Example Province", 900_000, "Point(10 45)", ["Q34876"]),
        binding("Q100", "Coordinate-free town", 75_000, "", ["Q3957"]),
    ]

    cities = wikidata._rows_to_cities(rows)

    assert [city["qid"] for city in cities] == ["Q90"]
    assert cities[0]["name"] == "Paris"
