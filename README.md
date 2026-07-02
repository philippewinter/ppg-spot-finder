# PPG Spot Finder

Find paramotor (PPG) takeoff/landing locations near any airport. Enter an ICAO
code, pick a radius, and see PPG spots within it on a map — sourced from actual
logged flights and PPG-specific databases (no free-flight/paragliding-only sites).

The whole app is a single self-contained HTML file (`PPG-Spot-Finder.html`) with
all data inlined; only the map library and tiles load from CDNs.

## Data sources
| Source | What it is | Colour |
|---|---|---|
| **XContest** (Paramotors) | Actual logged PPG flights, worldwide (flight counts + last-flight dates) | blue |
| **WingVoyagers** | PPG-friendly community spots, mostly US | green |
| **BASULM** | Official French ULM terrains (filtered to ground fields open to ULM) | amber |
| **PPG Schools** | School training/home fields (curated sample) | purple |

## Rebuild the app
```bash
python3 scripts/merge_sources.py   # merge + dedupe all sources -> data/ppg_spots.json
python3 scripts/build_app.py       # inline data into PPG-Spot-Finder.html
```

Source data files: `data/ppg_spots_source.json` (XContest), `wingvoyagers_ppg.json`,
`basulm_terrains.json`, `ppg_schools.json`. `data/airports.json` is the ICAO lookup.

## Deploy
See `deploy/README.md`. In short: a tiny nginx container serves the static file.
Point a self-hosted panel (Dokploy/Coolify) at this repo, deploy `compose.yaml`,
then attach a domain with HTTPS.
