from pathlib import Path


def test_direct_dependencies_are_documented_with_licenses():
    requirements = {
        line.split(">=", 1)[0].strip().casefold()
        for line in Path("requirements.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }
    notices = Path("THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8").casefold()

    assert requirements <= {name for name in requirements if name in notices}
    for license_name in ("mit", "bsd-3-clause", "apache-2.0", "cc by-sa 4.0", "cc0 1.0"):
        assert license_name in notices
