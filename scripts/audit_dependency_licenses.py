#!/usr/bin/env python3
"""List and validate direct dependency licenses using the reviewed allowlist."""
from __future__ import annotations

import argparse
from importlib.metadata import PackageNotFoundError, metadata, version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIREMENTS = ROOT / "requirements.txt"
APPROVED = {
    "streamlit": ("Apache-2.0", "https://github.com/streamlit/streamlit"),
    "streamlit-folium": ("MIT", "https://github.com/randyzwitch/streamlit-folium"),
    "folium": ("MIT", "https://github.com/python-visualization/folium"),
    "branca": ("MIT", "https://github.com/python-visualization/branca"),
    "requests": ("Apache-2.0", "https://github.com/psf/requests"),
    "pandas": ("BSD-3-Clause", "https://github.com/pandas-dev/pandas"),
    "beautifulsoup4": ("MIT", "https://www.crummy.com/software/BeautifulSoup/"),
    "mwparserfromhell": ("MIT", "https://github.com/earwig/mwparserfromhell"),
    "pytest": ("MIT", "https://github.com/pytest-dev/pytest"),
}
FORBIDDEN_TERMS = {"gpl", "agpl", "non-commercial", "noncommercial", "proprietary", "unknown"}


def direct_dependencies() -> list[str]:
    names = []
    for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            names.append(line.split("[", 1)[0].split("=", 1)[0].split("<", 1)[0].split(">", 1)[0].strip().casefold())
    return names


def audit(show_installed: bool = False) -> list[str]:
    errors: list[str] = []
    print("Package | Reviewed license | Commercial use | Installed version | Project")
    print("--- | --- | --- | --- | ---")
    for name in direct_dependencies():
        reviewed = APPROVED.get(name)
        if not reviewed:
            errors.append(f"{name}: no reviewed license entry")
            continue
        license_name, url = reviewed
        if any(term in license_name.casefold() for term in FORBIDDEN_TERMS):
            errors.append(f"{name}: forbidden or unclear license {license_name}")
        installed = "not installed"
        try:
            installed = version(name)
            if show_installed:
                package_metadata = metadata(name)
                declared = package_metadata.get("License-Expression") or package_metadata.get("License") or "not declared"
                print(f"<!-- installed metadata for {name}: {str(declared).splitlines()[0]} -->")
        except PackageNotFoundError:
            pass
        print(f"{name} | {license_name} | allowed | {installed} | {url}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-metadata", action="store_true", help="Also print installed package license metadata comments.")
    args = parser.parse_args()
    errors = audit(args.installed_metadata)
    if errors:
        print("\nFAILED:")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("\nDirect dependency license allowlist passed. Audit transitive packages before release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
