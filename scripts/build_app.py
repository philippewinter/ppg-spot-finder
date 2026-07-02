#!/usr/bin/env python3
"""Build PPG-Spot-Finder.html by inlining airport + spot data into the template.

Usage: python3 build_app.py
Reads:  data/airports.json, data/ppg_spots.json, scripts/app_template.html
Writes: PPG-Spot-Finder.html (project root)
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

airports = (ROOT / "data" / "airports.json").read_text(encoding="utf-8")
spots_raw = (ROOT / "data" / "ppg_spots.json").read_text(encoding="utf-8")
spots = json.loads(spots_raw)
template = (ROOT / "scripts" / "app_template.html").read_text(encoding="utf-8")

html = (
    template
    .replace("__AIRPORTS__", airports)
    .replace("__SPOTS__", json.dumps(spots, ensure_ascii=False, separators=(",", ":")))
    .replace("__SPOT_COUNT__", str(len(spots)))
    .replace("__BUILD_DATE__", date.today().isoformat())
)

out = ROOT / "PPG-Spot-Finder.html"
out.write_text(html, encoding="utf-8")
print(f"Built {out.name}: {len(spots)} spots, {out.stat().st_size // 1024} KB")
