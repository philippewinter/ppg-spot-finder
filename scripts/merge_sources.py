#!/usr/bin/env python3
"""Merge all PPG spot sources into one deduplicated dataset.

Sources (each normalized to a common schema):
  - XContest   : data/ppg_spots_source.json  (actual logged PPG flights, worldwide)
  - WingVoyagers: wingvoyagers_ppg.json        (PPG-friendly community spots)
  - BASULM     : basulm_terrains.json          (official French ULM terrains)

Output: data/ppg_spots.json  (list of unified spot records)

Unified schema:
  {name, lat, lon, country, source, flights, last, info, url}

Cross-source dedup: spots within DEDUP_KM of each other are merged into one pin.
"""
import json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEDUP_KM = 0.8

def hav(a, b):
    R = 6371; p = math.pi/180
    dlat = (b[0]-a[0])*p; dlon = (b[1]-a[1])*p
    x = math.sin(dlat/2)**2 + math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin(dlon/2)**2
    return R*2*math.atan2(math.sqrt(x), math.sqrt(1-x))

# ---- load + normalize each source ----
records = []

# XContest — current seasons (2025-26) already clustered
xc = json.load(open(ROOT/"data"/"ppg_spots_source.json"))
xc_current = 0
for s in xc["spots"]:
    xc_current += 1
    records.append({
        "name": s["name"], "lat": s["lat"], "lon": s["lon"],
        "country": s.get("country"), "source": "XContest",
        "flights": s.get("flights"), "last": s.get("last"),
        "info": s.get("cat", ""), "url": None,
    })

# XContest — historical seasons 2021-2024 (aggregated ~100m). Cross-dedup with
# the current seasons happens in the clustering step below.
xc_hist = 0
hist_path = ROOT/"xcontest_2021_2024.json"
if hist_path.exists():
    for s in json.load(open(hist_path)):
        xc_hist += 1
        records.append({
            "name": s["name"], "lat": s["lat"], "lon": s["lon"],
            "country": s.get("country"), "source": "XContest",
            "flights": s.get("flights"), "last": s.get("last"),
            "info": s.get("cat", ""), "url": None,
        })
print(f"XContest: {xc_current} current + {xc_hist} historical = {xc_current+xc_hist} raw")

# WingVoyagers
wv = json.load(open(ROOT/"wingvoyagers_ppg.json"))
for s in wv:
    records.append({
        "name": s["name"], "lat": s["lat"], "lon": s["lon"],
        "country": s.get("country"), "source": "WingVoyagers",
        "flights": None, "last": None,
        "info": s.get("access", ""), "url": s.get("url"),
    })

# BASULM  — filter out fields not usable for PPG.
# Policy: drop terrains forbidden to ULM, closed, admin-reserved, or undefined.
#         keep everything legally open to ULM (incl. public aerodromes open to ULM).
import re
def basulm_excluded(text):
    """text = access label + name. Exclude fields that are not usable
    paramotor takeoff/landing sites."""
    a = (text or "").lower()
    # forbidden / closed / admin-only / undefined
    if re.search(r"interdit|réservé administrations|mal défini|fermé|fermée", a):
        return True
    # non-ground special surfaces (not paramotor spots):
    #   water landing (hydrosurface/hydrobase), mountain airstrip (altisurface/altiport),
    #   glider strip (vélisurface), helipad (hélistation)
    if re.search(r"hydro|altisurface|altiport|vélisurface|velisurface|hélistation|helistation", a):
        return True
    # fields requiring mandatory prior authorization (can't just show up and fly)
    if re.search(r"autorisation obligatoire", a):
        return True
    return False

ba = json.load(open(ROOT/"basulm_terrains.json"))
ba_kept = 0
for s in ba:
    if basulm_excluded(s.get("access", "") + " " + s.get("name", "")):
        continue
    ba_kept += 1
    info = s.get("access", "")
    if s.get("city"): info = (info + " · " + s["city"]).strip(" ·")
    records.append({
        "name": s["name"], "lat": s["lat"], "lon": s["lon"],
        "country": "FR", "source": "BASULM",
        "flights": None, "last": s.get("last"),
        # BASULM has no reliable per-terrain deep link, so no source URL
        # (the app always provides a Google Maps location link instead).
        "info": info, "url": None,
    })

# PPG Schools + clubs (home/training fields, geocoded). Combines the global
# sample (ppg_schools.json) and the per-country school/club research (ppg_clubs.json).
ACC_LABEL = {"field": "", "verify": "field approx — verify", "approx": "⚠ town-level (approximate)"}
sch = []
for fname in ("ppg_schools.json", "ppg_clubs.json"):
    p = ROOT/fname
    if p.exists(): sch.extend(json.load(open(p)))
for s in sch:
    note = ACC_LABEL.get(s.get("accuracy", "field"), "")
    info = s.get("field", "")
    if note: info = (info + " · " + note).strip(" ·")
    records.append({
        "name": s["name"], "lat": s["lat"], "lon": s["lon"],
        "country": s.get("country"), "source": "PPGSchool",
        "flights": None, "last": None,
        "info": info, "url": s.get("url"),
    })

print(f"Loaded: {xc_current+xc_hist} XContest, {len(wv)} WingVoyagers, "
      f"{ba_kept} BASULM (of {len(ba)}, dropped {len(ba)-ba_kept} forbidden/closed), "
      f"{len(sch)} PPGSchool/clubs = {len(records)} raw")

# ---- spatial grid index for fast proximity dedup ----
CELL = 0.02  # ~2km lat; good enough as a bucket for a 0.8km search
grid = {}
def cell(lat, lon): return (round(lat/CELL), round(lon/CELL))

SRC_RANK = {"XContest": 0, "WingVoyagers": 1, "BASULM": 2, "PPGSchool": 3}

clusters = []
for r in records:
    c = cell(r["lat"], r["lon"])
    home = None
    # search this + 8 neighboring cells
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            for idx in grid.get((c[0]+dx, c[1]+dy), []):
                cl = clusters[idx]
                if hav((cl["lat"],cl["lon"]), (r["lat"],r["lon"])) < DEDUP_KM:
                    home = idx; break
            if home is not None: break
        if home is not None: break

    if home is None:
        cl = {
            "name": r["name"], "lat": r["lat"], "lon": r["lon"],
            "country": r["country"], "sources": {r["source"]},
            "flights": r["flights"] or 0, "last": r["last"],
            "info": r["info"], "url": r["url"],
            "_wname_src": r["source"],
        }
        clusters.append(cl)
        grid.setdefault(c, []).append(len(clusters)-1)
    else:
        cl = clusters[home]
        cl["sources"].add(r["source"])
        if r["flights"]: cl["flights"] += r["flights"]
        if r["last"] and (not cl["last"] or r["last"] > cl["last"]): cl["last"] = r["last"]
        if not cl["country"] and r["country"]: cl["country"] = r["country"]
        # prefer a community URL (WingVoyagers/BASULM) over none
        if not cl["url"] and r["url"]: cl["url"] = r["url"]
        # prefer a real name over "?"/"Unnamed"/"Unknown Takeoff"
        def is_placeholder(n): return n.strip() in ("?","") or n.lower().startswith(("unnamed","unknown takeoff"))
        if is_placeholder(cl["name"]) and not is_placeholder(r["name"]):
            cl["name"] = r["name"]
        elif not is_placeholder(r["name"]) and len(r["name"]) > len(cl["name"]) and r["source"] != "XContest":
            cl["name"] = r["name"]
        if r["info"] and not cl["info"]: cl["info"] = r["info"]

# ---- finalize ----
out = []
for cl in clusters:
    srcs = sorted(cl["sources"], key=lambda s: SRC_RANK[s])
    out.append({
        "name": cl["name"] or "Unnamed spot",
        "lat": round(cl["lat"], 5), "lon": round(cl["lon"], 5),
        "country": cl["country"],
        "source": "+".join(srcs),
        "flights": cl["flights"] or None,
        "last": cl["last"],
        "info": cl["info"] or "",
        "url": cl["url"],
    })

json.dump(out, open(ROOT/"data"/"ppg_spots.json","w"), ensure_ascii=False, separators=(",",":"))

# stats
from collections import Counter
by_src = Counter(s["source"] for s in out)
print(f"Merged -> {len(out)} unique spots")
for k,v in sorted(by_src.items(), key=lambda x:-x[1]):
    print(f"  {v:5d}  {k}")
