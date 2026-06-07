#!/usr/bin/env python3
"""Build a tiny schematic broad-climate GeoJSON for map context.

The layer is intentionally generalized and project-authored rather than a
redistribution of a restricted scientific raster. It is a visual grouping aid,
not a parcel-level or scientific Köppen boundary product.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/preloaded/climate_zones_simplified.geojson"


def polygon(west: float, south: float, east: float, north: float) -> list[list[list[float]]]:
    return [[[west, south], [east, south], [east, north], [west, north], [west, south]]]

# Non-overlapping generalized world bands keep rendering deterministic and tiny.
ZONES = [
    ("North polar", "Polar", -180, 66.5, 180, 90),
    ("North continental", "Continental", -180, 45, 180, 66.5),
    ("North temperate", "Temperate", -180, 28, 180, 45),
    ("North tropical", "Tropical", -180, 0, 180, 28),
    ("South tropical", "Tropical", -180, -28, 180, 0),
    ("South temperate", "Temperate", -180, -50, 180, -28),
    ("South polar", "Polar", -180, -90, 180, -50),
]
# Broad dry/highland overlays add recognizable visual grouping while remaining
# only a small set of rectangles. They render after the base bands.
OVERLAYS = [
    ("Sahara and Arabian dry belt", "Dry / Arid", -18, 15, 60, 33),
    ("Central Asian dry belt", "Dry / Arid", 45, 32, 110, 48),
    ("Australian interior dry belt", "Dry / Arid", 112, -34, 145, -18),
    ("Southwestern North America dry belt", "Dry / Arid", -120, 20, -98, 38),
    ("Andean highlands", "Highland / Mountain", -80, -38, -66, 10),
    ("Himalayan/Tibetan highlands", "Highland / Mountain", 70, 26, 103, 39),
    ("East African highlands", "Highland / Mountain", 28, -12, 42, 12),
]


def build(output: Path = OUTPUT) -> dict:
    features = []
    for index, (name, group, west, south, east, north) in enumerate([*ZONES, *OVERLAYS], start=1):
        features.append({
            "type": "Feature", "id": f"zone-{index}",
            "properties": {"name": name, "climate_group": group, "detail_level": "schematic broad grouping"},
            "geometry": {"type": "Polygon", "coordinates": polygon(west, south, east, north)},
        })
    payload = {
        "type": "FeatureCollection",
        "metadata": {
            "source_name": "CityClimate Explorer generalized broad-climate visualization",
            "source_url": "https://github.com/azagorowski/CityClimate-Explorer",
            "license": "MIT", "license_url": "https://opensource.org/license/mit",
            "commercial_use_status": "permitted",
            "attribution_text": "CityClimate Explorer contributors",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "processing_steps": ["define broad latitude bands", "add generalized dry/highland overlays", "serialize low-vertex GeoJSON"],
            "limitations": "Schematic visual grouping only; boundaries are deliberately generalized and are not a scientific Köppen-Geiger product.",
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
    print(f"Wrote {len(payload['features'])} lightweight climate-zone features to {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
