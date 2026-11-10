"""Shared paths, constants and helpers for the sea-view study ("Can you see the sea? Every square of Britain").

Inputs (read in place, never modified or moved):
  RAW/terrarium_z9_pack{0..5}.bin + .json  AWS Terrain Tiles (Mapzen "terrarium" PNG encoding: height = R*256 + G + B/256 -
                       32768 m), zoom 9, x 244..258, y 145..174 (Britain and Ireland). Each .json lists [file t9_x_y.png,
                       byte offset, length] into the matching .bin. Sources: SRTM, GMTED, ETOPO1 (Terrain Tiles attribution list).
  DEM10                /home/claude/newdata/raw_new8/terrain/tiles/10/{x}/{y}.png: the same tiles at zoom 10 (about 88 m), used
                       only for the resolution check in four test windows.
  OFM vector tiles     https://tiles.openfreemap.org/planet (OpenMapTiles schema; OpenStreetMap, ODbL) zoom 9: water layer,
                       class "ocean", rasterised to the terrain grid. Each tile is written, read and deleted at once.
  GEO/counties_uk.geojson  ONS-derived counties with nation (OGL v3): which nation a square is in.
  SETT                 /home/claude/studies/sunless-valleys/data/settlements_sun.csv: 36,692 living UK settlements from Wikidata
                       (CC0) with point, nation, county and population where Wikidata has one.
  SEATS                /home/claude/studies/beeching-leave/data/constituencies.csv (2011 Census population of the 632 GB
                       Westminster seats of 2010, ONS, OGL v3) and /home/claude/studies/twins-remain/data/seats.geojson (their
                       boundaries).
Scratch (DEM mosaic, sea mask, test windows) goes to SCR, outside the repo, and is deleted at the end.
"""
import json, gzip, os, re, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.environ.get("SV_RAW", "/home/claude/newdata/raw_new13")
DEM10 = os.environ.get("SV_DEM10", "/home/claude/newdata/raw_new8/terrain/tiles/10")
GEO = os.environ.get("SV_GEO", "/home/claude/newdata/raw/geo")
SETT = os.environ.get("SV_SETT", "/home/claude/studies/sunless-valleys/data/settlements_sun.csv")
SEATCSV = os.environ.get("SV_SEATCSV", "/home/claude/studies/beeching-leave/data/constituencies.csv")
SEATGEO = os.environ.get("SV_SEATGEO", "/home/claude/studies/twins-remain/data/seats.geojson")
FONTS = os.environ.get("SV_FONTS", "/home/claude/ref/fonts")
SCR = os.environ.get("SV_SCRATCH", "/home/claude/scratch/sea-view")
DATA = os.path.join(ROOT, "data")
IMG = os.path.join(ROOT, "img")
REL = os.path.join(ROOT, "release")
for d in (DATA, IMG, SCR):
    os.makedirs(d, exist_ok=True)

SLUG = "sea-view"
PAGE = f"https://maps.tristanhotham.com/{SLUG}/"
REPO = f"https://github.com/Tristan-Hotham/{SLUG}"
AI = ("I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped "
      "prepare the analysis code. I reviewed and checked all text and results.")
BYLINE = "Dr Tristan Hotham · Independent researcher · 2026"
UA = {"User-Agent": "sea-view-study/1.0 (research; maps.tristanhotham.com)"}
TERRAIN_URL = "https://registry.opendata.aws/terrain-tiles/"
TERRAIN_ATTR = "https://github.com/tilezen/joerd/blob/master/docs/attribution.md"

# terrain block, zoom 9
Z = 9
X0, X1, Y0, Y1 = 244, 258, 145, 174            # inclusive tile range
NX, NY = (X1 - X0 + 1) * 256, (Y1 - Y0 + 1) * 256
R_EARTH = 6371000.0
K_REFR = 0.13
EYE = 1.7
DMAX = 50000.0
NAZ = 360
C_MERC = 2 * math.pi * 6378137.0
EYES = [1.7, 5.0, 15.0, 50.0]                    # map slider and S1
NATIONS = ["England", "Scotland", "Wales", "Northern Ireland"]


def px2ll(X, Y, z=Z):
    """global pixel coordinates at zoom z (pixel centres at +0.5) to lon, lat"""
    import numpy as np
    n = 256 * 2 ** z
    lon = np.asarray(X, float) / n * 360.0 - 180.0
    lat = np.degrees(np.arctan(np.sinh(np.pi * (1 - 2 * np.asarray(Y, float) / n))))
    return lon, lat


def ll2px(lon, lat, z=Z):
    import numpy as np
    n = 256 * 2 ** z
    lat = np.radians(np.asarray(lat, float))
    return (np.asarray(lon, float) + 180.0) / 360.0 * n, (1 - np.log(np.tan(lat) + 1 / np.cos(lat)) / np.pi) / 2 * n


def jload(path):
    op = gzip.open if path.endswith(".gz") else open
    with op(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def nonan(v):
    if isinstance(v, float) and (v != v or v in (float("inf"), float("-inf"))):
        return None
    if isinstance(v, (list, tuple)):
        return [nonan(x) for x in v]
    if isinstance(v, dict):
        return {str(k): nonan(x) for k, x in v.items()}
    if hasattr(v, "item"):
        return nonan(v.item())
    return v


def jsave(obj, path, indent=None):
    obj = nonan(obj)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, allow_nan=False, indent=indent, separators=None if indent else (",", ":"))


def get(R, path):
    """dotted path into results; a key that itself contains a dot (eye height "1.7") is found by joining parts"""
    v = R
    parts = path.split(".")
    i = 0
    while i < len(parts):
        if isinstance(v, list):
            v = v[int(parts[i])]; i += 1; continue
        for j in range(len(parts), i, -1):
            k = ".".join(parts[i:j])
            if k in v:
                v = v[k]; i = j; break
        else:
            raise KeyError(path)
    return v


def fmt(v, f=None):
    if f is None or f == "raw": return str(v)
    if f == "int": return f"{round(float(v)):,}"
    if f == "pc": return f"{round(float(v))}%"
    if f == "pc1": return f"{float(v):.1f}%"
    if f == "f0": return f"{float(v):.0f}"
    if f == "f1": return f"{float(v):.1f}"
    if f == "f2": return f"{float(v):.2f}"
    if f == "f3": return f"{float(v):.3f}"
    raise ValueError(f)


def gc_km(lat1, lon1, lat2, lon2):
    import numpy as np
    p1, p2, l1, l2 = map(np.radians, (lat1, lat2, lon1, lon2))
    return 6371.0 * 2 * np.arcsin(np.sqrt(np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin((l2 - l1) / 2) ** 2))
