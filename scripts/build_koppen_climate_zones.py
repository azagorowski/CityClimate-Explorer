#!/usr/bin/env python3
"""Build the runtime-sized detailed Köppen layer from reviewed zone extents.

The reviewed extents are a deliberately coarse cartographic generalization of
the CC BY 4.0 Beck et al. (2018) present-day 0.5-degree map. This developer-only
builder never runs in Streamlit and performs no network access.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/preloaded/koppen_climate_zones_simplified.geojson"
SOURCE_URL = "https://doi.org/10.6084/m9.figshare.6396959.v2"
SOURCE_DOI = "10.6084/m9.figshare.6396959.v2"

KOPPEN_NAMES = {
    "Af": "Tropical rainforest", "Am": "Tropical monsoon", "Aw": "Tropical savanna",
    "BWh": "Hot desert", "BWk": "Cold desert", "BSh": "Hot semi-arid", "BSk": "Cold semi-arid",
    "Csa": "Hot-summer Mediterranean", "Csb": "Warm-summer Mediterranean",
    "Cfa": "Humid subtropical", "Cfb": "Oceanic", "Cwa": "Dry-winter humid subtropical",
    "Cwb": "Dry-winter subtropical highland", "Dfa": "Hot-summer humid continental",
    "Dfb": "Warm-summer humid continental", "Dfc": "Subarctic", "Dwa": "Dry-winter humid continental",
    "ET": "Tundra", "EF": "Ice cap", "H": "Highland / mountain",
}
GROUPS = {"A": "Tropical", "B": "Dry / Arid", "C": "Temperate", "D": "Continental", "E": "Polar", "H": "Highland / Mountain"}
COLORS = {
    "Af": "#006d2c", "Am": "#31a354", "Aw": "#78c679", "BWh": "#d97706", "BWk": "#b45309",
    "BSh": "#f59e0b", "BSk": "#fbbf24", "Csa": "#1d4ed8", "Csb": "#3b82f6", "Cfa": "#0ea5e9",
    "Cfb": "#60a5fa", "Cwa": "#0284c7", "Cwb": "#38bdf8", "Dfa": "#6d28d9", "Dfb": "#7c3aed",
    "Dfc": "#8b5cf6", "Dwa": "#5b21b6", "ET": "#06b6d4", "EF": "#a5f3fc", "H": "#92400e",
}

# (label, code, west, south, east, north). These intentionally low-vertex,
# overlapping extents preserve quick map rendering and are not site-level data.
REVIEWED_EXTENTS = [
    ("Amazon rainforest", "Af", -78, -12, -48, 6), ("Congo rainforest", "Af", 10, -7, 31, 6),
    ("Maritime Southeast Asia rainforest", "Af", 95, -10, 150, 8),
    ("West African monsoon", "Am", -18, 4, 15, 14), ("South Asian monsoon", "Am", 72, 8, 100, 25),
    ("Tropical savanna belt north", "Aw", -180, 8, 180, 24), ("Tropical savanna belt south", "Aw", -180, -24, 180, -8),
    ("Sahara and Arabian hot desert", "BWh", -18, 15, 60, 33), ("Australian hot desert", "BWh", 112, -34, 145, -18),
    ("Southwest North America hot desert", "BWh", -120, 20, -98, 38), ("Central Asian cold desert", "BWk", 45, 35, 110, 49),
    ("Patagonian cold desert", "BWk", -74, -50, -62, -38), ("Sahel hot steppe", "BSh", -18, 10, 38, 18),
    ("Eurasian cold steppe", "BSk", 25, 40, 120, 55), ("Mediterranean basin", "Csa", -10, 30, 40, 45),
    ("California Mediterranean", "Csa", -125, 31, -116, 42), ("Pacific marine west coast", "Csb", -130, 40, -120, 52),
    ("Western Europe oceanic", "Cfb", -12, 43, 25, 61), ("Southeast North America humid subtropical", "Cfa", -100, 25, -72, 39),
    ("East Asia humid subtropical", "Cfa", 105, 22, 145, 38), ("East Asian dry-winter temperate", "Cwa", 95, 20, 125, 35),
    ("Subtropical highlands", "Cwb", -80, -22, 42, 25), ("North American hot-summer continental", "Dfa", -100, 38, -70, 47),
    ("Northern warm-summer continental", "Dfb", -165, 42, 155, 58), ("Northern subarctic", "Dfc", -170, 55, 170, 68),
    ("Northeast Asian dry-winter continental", "Dwa", 100, 38, 145, 55), ("Arctic tundra", "ET", -180, 66, 180, 78),
    ("Antarctic tundra fringe", "ET", -180, -68, 180, -50), ("Polar ice caps", "EF", -180, 78, 180, 90),
    ("Antarctic ice cap", "EF", -180, -90, 180, -68), ("Andean highlands", "H", -80, -38, -66, 10),
    ("Himalayan and Tibetan highlands", "H", 70, 26, 103, 39), ("East African highlands", "H", 28, -12, 42, 12),
]


def polygon(west: float, south: float, east: float, north: float) -> list[list[list[float]]]:
    return [[[west, south], [east, south], [east, north], [west, north], [west, south]]]


def build(output: Path = OUTPUT) -> dict:
    features = []
    for index, (label, code, west, south, east, north) in enumerate(REVIEWED_EXTENTS, start=1):
        features.append({
            "type": "Feature", "id": f"koppen-{index}",
            "properties": {
                "name": label, "koppen_code": code, "koppen_name": KOPPEN_NAMES[code],
                "climate_group": GROUPS[code[0]], "color": COLORS[code],
                "detail_level": "simplified cartographic generalization",
            },
            "geometry": {"type": "Polygon", "coordinates": polygon(west, south, east, north)},
        })
    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "source_name": "Beck et al. (2018) present-day Köppen-Geiger climate classification map",
            "source_url": SOURCE_URL, "source_doi": SOURCE_DOI, "source_period": "1980-2016",
            "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
            "commercial_use_status": "permitted with attribution", "runtime_network_required": False,
            "attribution_text": "Beck, H.E. et al. (2018), Scientific Data 5:180214; generalized by CityClimate Explorer contributors.",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "processing_steps": [
                "review the published present-day 0.5-degree map", "generalize representative type extents into low-vertex polygons",
                "attach Köppen code, human-readable name, broad group, and display color", "serialize runtime-only local GeoJSON",
            ],
            "limitations": "Highly simplified visual context only; overlapping generalized extents are not scientific boundaries and must not be used for site-level analysis.",
        },
        "features": features,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    payload = build(args.output)
    print(f"Wrote {len(payload['features'])} simplified Köppen features to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
