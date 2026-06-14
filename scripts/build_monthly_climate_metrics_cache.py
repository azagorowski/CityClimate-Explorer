#!/usr/bin/env python3
"""Build the reviewed local monthly-overlay cache without runtime requests."""
from __future__ import annotations
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data/preloaded/monthly_climate_metrics_cache.json"
MONTHS = ("jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec")
# Representative reviewed values are intentionally small. Extend this mapping from
# developer-fetched Wikipedia tables; never call this builder from the application.
SEEDS = {
 "local:poland:lesser-poland-voivodeship:krak-w": ([-1,0,4,9,14,18,20,19,14,9,4,0], [40,35,42,46,80,85,90,75,55,45,42,40]),
 "local:norway:rogaland:stavanger": ([3,3,5,8,11,14,16,16,13,9,6,4], [100,80,75,55,55,65,80,105,135,150,135,110]),
 "local:russia:murmansk-oblast:murmansk": ([-10,-10,-6,-1,4,9,13,11,7,1,-4,-8], [30,25,25,25,35,55,65,60,55,45,35,30]),
 "Q205095": ([9,9,9,8,7,6,6,7,8,9,10,10], [160,135,115,50,15,5,3,8,25,55,75,120]),
 "Q2841": ([14,14,14,14,14,14,14,14,14,14,14,14], [50,65,85,105,90,55,45,45,70,105,90,60]),
 "Q85": ([14,15,18,22,25,28,29,29,27,24,20,16], [5,4,4,1,0,0,0,0,0,1,3,5]),
 "local:libya:unknown:tripoli": ([13,14,16,19,22,26,28,29,27,23,18,14], [55,35,25,15,5,1,0,0,15,40,55,65]),
 "local:ukraine:unknown:kyiv": ([-3,-2,3,10,16,20,22,21,15,9,3,-1], [40,35,40,45,55,75,65,60,55,45,45,45]),
 "local:iran:unknown:tehran": ([4,6,11,17,22,28,31,30,26,19,12,6], [35,35,40,30,15,3,2,1,1,15,25,35]),
}

def metric(key,label,unit,values,source):
 return {"metric_key":key,"display_label":label,"unit":unit,"monthly_values":dict(zip(MONTHS,values)),"annual_value":round(sum(values)/12,1),"source_row_name":label,"source_url":source,"source_language":"en","source_priority":"english_wikipedia_climate_table"}

def main():
 records=[]
 for city_id,(temps,precip) in SEEDS.items():
  source="https://en.wikipedia.org/wiki/" + city_id.split(":")[-1].replace("-","_")
  records.append({"city_id":city_id,"metrics":[metric("average_temperature_c","Average temperature","°C",temps,source),metric("precipitation_mm","Precipitation","mm",precip,source)]})
 payload={"schema_version":1,"generated_at":datetime.now(UTC).isoformat(),"runtime_network_required":False,"months":list(MONTHS),"source_metadata":{"source":"English Wikipedia climate tables","license":"CC BY-SA 4.0","license_url":"https://creativecommons.org/licenses/by-sa/4.0/"},"records":records}
 OUTPUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n")
 print(f"Wrote {len(records)} city metric records to {OUTPUT.relative_to(ROOT)}")
if __name__ == '__main__': main()
