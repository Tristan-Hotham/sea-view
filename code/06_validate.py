"""Step 6 (check V1): named viewpoints with a documented sea view, computed at the exact point, with the terrain height there and
with the published height (eye 1.7 m; Leith Hill: the top of the tower). Rays every 0.5 degrees, 50 km and 100 km.
Output: data/validation.csv"""
import csv
import numpy as np
from pyproj import Transformer
from viewshed import viewshed
from common import *

dem = np.load(f"{SCR}/dem.npy").astype(np.float32)
sea = np.load(f"{SCR}/sea.npy")
# name, grid, easting, northing, published height m, extra eye m (tower), documented view, source
P = [
    ("Black Combe", "OSGB", 313500, 485400, 600, 0, "\"Half the view is the glittering sea, with the Isle of Man seen clearly to the west\"", "Wikipedia, Black Combe (retrieved 2026)"),
    ("Dunkery Beacon", "OSGB", 289100, 141500, 519, 0, "\"views over the surrounding moorland, the Bristol Channel and hills\"", "Wikipedia, Dunkery Hill (retrieved 2026)"),
    ("Pendle Hill", "OSGB", 380400, 441400, 557, 0, "George Fox, 1652: \"I saw the sea bordering upon Lancashire\"; \"On a clear day, spectacular 360 degree views stretch to the sea\"", "Pendle Radicals, Pendle Hill Summit (retrieved 2026)"),
    ("Leith Hill (tower top)", "OSGB", 513900, 143100, 294, 19.5, "\"on a clear day you can see the English Channel to the south\"", "National Trust, Visiting Leith Hill Tower (retrieved 2026)"),
    ("Ditchling Beacon", "OSGB", 533300, 113000, 248, 0, "\"360-degree views across the weald and out to the English Channel\"", "South Downs National Park Authority, Bird's Eye View (retrieved 2026)"),
    ("Brown Willy", "OSGB", 215800, 79900, 420, 0, "\"Views from the summit stretch to both sides of the coast, from Looe in the south, to Tintagel in the north\"", "Cornwall Guide, Brown Willy (retrieved 2026)"),
    ("Worcestershire Beacon", "OSGB", 376800, 245200, 425, 0, "\"Parts of a dozen or so counties can be seen, and the Bristol Channel\"", "Wikishire, Worcestershire Beacon (retrieved 2026)"),
    ("Snowdon (Yr Wyddfa)", "OSGB", 260989, 354379, 1085, 0, "\"On exceptionally clear days, Ireland, Scotland, England, and the Isle of Man are all visible\" (across the Irish Sea)", "Wikishire, Snowdon (retrieved 2026)"),
    ("Scafell Pike", "OSGB", 321500, 507200, 978, 0, "\"On a clear day you can see tops in Northern Ireland, Scotland, Wales, and the Isle of Man\" (across the Irish Sea)", "UKHillwalking, One Minute Mountain: Scafell Pike (retrieved 2026)"),
    ("Slieve Donard", "IG", 335800, 327700, 850, 0, "\"In very clear conditions the Galloway Hills, Isle of Man and the Wicklow Mts are visible\" (across the Irish Sea)", "MountainViews.ie, Slieve Donard (retrieved 2026)"),
]
rows = []
for name, grid, e, n, hpub, tower, quote, src in P:
    lon, lat = Transformer.from_crs("EPSG:27700" if grid == "OSGB" else "EPSG:29903", "EPSG:4326", always_xy=True).transform(e, n)
    X, Y = ll2px(lon, lat)
    u = np.array([X - X0 * 256 - 0.5]); v = np.array([Y - Y0 * 256 - 0.5])
    g = viewshed(dem, sea, u, v, Y0 * 256 + 0.5, 256 * 2 ** Z, C_MERC / (256 * 2 ** Z), 0.0, 1000.0, 4, K_REFR, 0.5, 0.0, np.zeros((0, 4), np.float32))[3][0]
    row = {"name": name, "grid": grid, "easting": e, "northing": n, "lon": round(float(lon), 5), "lat": round(float(lat), 5),
           "published_m": hpub, "terrain_m": round(float(g), 1), "tower_m": tower, "documented": quote, "source": src}
    for tag, eye in (("terrain", EYE + tower), ("published", (hpub - g) + EYE + tower)):
        for dmax in (50000.0, 100000.0):
            rays = np.full((1, 720), np.inf, np.float32)
            r = viewshed(dem, sea, u, v, Y0 * 256 + 0.5, 256 * 2 ** Z, C_MERC / (256 * 2 ** Z), float(eye), dmax, 720, K_REFR, 0.5, 0.0, rays)
            key = f"{tag}_{int(dmax / 1000)}"
            row[f"{key}_sea"] = int(r[1][0] > 0)
            row[f"{key}_near_km"] = round(float(r[0][0]) / 1000, 1) if np.isfinite(r[0][0]) else ""
            row[f"{key}_share_pc"] = round(100 * float(r[1][0]) / 720, 1)
            if np.isfinite(r[0][0]):
                a = int(np.argmin(rays[0])); row[f"{key}_near_bearing"] = a * 0.5
    rows.append(row)
    print(name, {k: row[k] for k in row if k.endswith("_sea") or k.endswith("near_km")}, flush=True)
keys = list(rows[0].keys())
for r in rows:
    for k in r:
        if k not in keys:
            keys.append(k)
with open(f"{DATA}/validation.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, keys); w.writeheader(); w.writerows(rows)
print("reproduced at terrain height, 50 km:", sum(r["terrain_50_sea"] for r in rows), "of", len(rows))
