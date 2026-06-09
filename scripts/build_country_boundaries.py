#!/usr/bin/env python3
"""Developer-only normalizer for Natural Earth 1:110m Admin-0 GeoJSON."""
from __future__ import annotations
import argparse, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/preloaded/country_boundaries_simplified.geojson"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="Downloaded Natural Earth ne_110m_admin_0_countries GeoJSON")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    source = json.loads(args.source.read_text(encoding="utf-8"))
    features = []
    for feature in source.get("features", []):
        props = feature.get("properties", {})
        features.append({"type": "Feature", "properties": {
            "name": props.get("NAME") or props.get("ADMIN"), "country": props.get("ADMIN") or props.get("NAME"),
            "iso_a2": props.get("ISO_A2"), "iso_a3": props.get("ISO_A3") or props.get("ADM0_A3"),
            "wikidata_qid": props.get("WIKIDATAID"),
        }, "geometry": feature.get("geometry")})
    payload = {"type": "FeatureCollection", "metadata": {
        "source_name": "Natural Earth Admin 0 Countries, 1:110m", "source_url": "https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-0-countries/",
        "license": "Public Domain", "commercial_use_status": "permitted", "runtime_network_required": False,
        "processing": "Retain low-resolution geometry and only country lookup properties."}, "features": features}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Wrote {len(features)} country features to {args.output}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
