from pathlib import Path


def test_deprecated_use_container_width_is_absent():
    paths = [Path("app.py"), *Path("src").glob("*.py"), *Path("scripts").glob("*.py")]
    assert not [path for path in paths if "use_container_width" in path.read_text(encoding="utf-8")]
