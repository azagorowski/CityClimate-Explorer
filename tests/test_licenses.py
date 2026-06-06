import json
from pathlib import Path

import pytest

from scripts.audit_dependency_licenses import APPROVED, FORBIDDEN_TERMS, audit, direct_dependencies
from scripts.validate_provenance import validate_provenance
from src.config import USER_AGENT, get_tile_provider


def test_required_license_and_provenance_documents_exist():
    for path in ("LICENSE", "THIRD_PARTY_NOTICES.md", "data/preloaded/SOURCES.md", "requirements-lock.txt"):
        assert Path(path).is_file(), path
    assert "MIT License" in Path("LICENSE").read_text(encoding="utf-8")


def test_direct_dependencies_are_documented_and_permissively_licensed():
    requirements = set(direct_dependencies())
    notices = Path("THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").casefold()

    assert requirements == set(APPROVED)
    assert all(name in notices for name in requirements)
    assert all(not any(term in license_name.casefold() for term in FORBIDDEN_TERMS) for license_name, _ in APPROVED.values())
    assert audit() == []
    for license_name in ("mit", "bsd-3-clause", "apache-2.0", "cc by-sa 4.0", "cc0 1.0"):
        assert license_name in notices


def test_bundled_records_pass_provenance_validation():
    assert validate_provenance() == []


def test_wikipedia_climate_cache_records_retain_required_attribution():
    records = json.loads(Path("data/capital_climate_cache.json").read_text(encoding="utf-8"))["records"]
    wikipedia_records = [record for record in records if record.get("source_priority") in {"english_primary", "native_fallback"}]
    assert wikipedia_records
    for record in wikipedia_records:
        assert record["source_url"].startswith("https://")
        assert record["source_page_title"]
        assert record["source_language"]
        assert record["license"] == "CC BY-SA 4.0"
        assert record["license_url"]
        assert record["contributors_url"].endswith("?action=history")


def test_wikimedia_user_agent_is_informative_and_not_placeholder():
    assert "CityClimateExplorer/" in USER_AGENT
    assert "contact:" in USER_AGENT
    assert "example.local" not in USER_AGENT
    assert "educational" not in USER_AGENT.casefold()


def test_tile_provider_is_configurable_and_production_rejects_demo(monkeypatch):
    monkeypatch.setenv("CITYCLIMATE_TILE_PROVIDER", "custom")
    monkeypatch.setenv("CITYCLIMATE_TILE_URL", "https://tiles.test/{z}/{x}/{y}.png")
    monkeypatch.setenv("CITYCLIMATE_TILE_ATTRIBUTION", "Test tiles")
    monkeypatch.setenv("CITYCLIMATE_DEPLOYMENT", "production")
    provider = get_tile_provider()
    assert provider.tiles.startswith("https://tiles.test/")
    assert provider.attribution == "Test tiles"

    monkeypatch.setenv("CITYCLIMATE_TILE_PROVIDER", "cartodb_positron")
    with pytest.raises(ValueError, match="Production deployment"):
        get_tile_provider()


def test_no_unattributed_hardcoded_default_tile_configuration():
    source = Path("src/map_view.py").read_text(encoding="utf-8")
    assert 'tiles="cartodbpositron"' not in source
    assert "get_tile_provider()" in source
    assert "attr=tile_provider.attribution" in source
