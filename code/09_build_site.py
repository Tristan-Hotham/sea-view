"""Step 9: the page. Map overlays and lookup grids in Web Mercator (so MapLibre can lay them as image sources and the page
can read a clicked square without a projection library), the search list, site.json, and index.html from
code/page_template.html filled from data/results.json.
  img/ov_near_<eye>.png   nearest visible sea class (palette PNG, transparent off the squares), zoom-8 pixels (about 350 m)
  img/ov_hz_<eye>.png     share of the horizon that is sea
  data/grid_a.png         lookup at zoom-7 pixels (about 700 m), RGB: nearest sea at 1.7 m (km x 5; 255 none), horizon share at
                          1.7 m (% x 2; 255 off the squares), ground height (m / 6)
  data/grid_b.png         RGB: nearest sea at 5, 15, 50 m (km x 5; 255 none)
  data/grid_c.png         RGB: horizon share at 5, 15, 50 m (% x 2)
  data/places.json        every settlement point with its own result at each eye height
10.5281/zenodo.24106076, https://doi.org/10.5281/zenodo.24106076 and https://blog.tristanhotham.com/2026/10/31/sea-view/ are left for the publisher to fill."""
import numpy as np
import pandas as pd
from PIL import Image
from pyproj import Transformer
from rasters import *
from figstyle import DCOL, NOVIEW, dist_class
from common import *

R = jload(f"{DATA}/results.json")
Q = load_squares()
idx = disp_index(Q)
LON0, LON1, LAT0, LAT1 = -8.25, 1.85, 49.85, 60.92
BOUNDS = [[LON0, LAT1], [LON1, LAT1], [LON1, LAT0], [LON0, LAT0]]
ZZ = 9                                                      # overlay at zoom 8 pixels (about 350 m at 55 N), lookup at zoom 7 (700 m)


def merc_grid(z):
    x0, y0 = ll2px(LON0, LAT1, z); x1, y1 = ll2px(LON1, LAT0, z)
    W_, H_ = int(round(x1 - x0)), int(round(y1 - y0))
    xs = x0 + (np.arange(W_) + 0.5) * (x1 - x0) / W_; ys = y0 + (np.arange(H_) + 0.5) * (y1 - y0) / H_
    gx, gy = np.meshgrid(xs, ys)
    lon, lat = px2ll(gx, gy, z)
    E, N = Transformer.from_crs(4326, 27700, always_xy=True).transform(lon, lat)
    c = np.floor((E - E0) / 1000).astype(int); r = np.floor((N1 - N) / 1000).astype(int)
    ok = (c >= 0) & (c < W) & (r >= 0) & (r < H)
    look = np.full(gx.shape, -1, np.int32)
    look[ok] = idx[r[ok], c[ok]]
    return look


look = merc_grid(ZZ - 1)
os.makedirs(IMG, exist_ok=True)
pal_near = [int(DCOL[i][k:k + 2], 16) for i in range(6) for k in (1, 3, 5)] + [int(NOVIEW[k:k + 2], 16) for k in (1, 3, 5)]
HZC = ["#D2E4F1", "#A6CBE6", "#6FA9D6", "#2D6FAE", "#08306B"]
pal_hz = [int(c[k:k + 2], 16) for c in HZC for k in (1, 3, 5)] + [int(NOVIEW[k:k + 2], 16) for k in (1, 3, 5)]
EYEK = {"1.7": ("near_sea_km", "sea_rays"), "5": ("near_sea_km_eye5", "sea_rays_eye5"), "15": ("near_sea_km_eye15", "sea_rays_eye15"),
        "50": ("near_sea_km_eye50", "sea_rays_eye50")}


def paletted(arr, pal, ntrans):
    """arr: int with -1 = transparent; pal: flat RGB list; index ntrans is the transparent slot"""
    a = np.where(arr < 0, ntrans, arr).astype(np.uint8)
    im = Image.fromarray(a, "P")
    full = pal + [0, 0, 0] * (256 - len(pal) // 3)
    im.putpalette(full)
    im.info["transparency"] = ntrans
    return im


sizes = {}
for e, (cn, cr) in EYEK.items():
    cls = dist_class(np.nan_to_num(Q[cn].values, nan=1e9)).astype(np.int16)
    a = np.where(look >= 0, cls[np.maximum(look, 0)], -1)
    paletted(a, pal_near, 7).save(f"{IMG}/ov_near_{e}.png", optimize=True, transparency=7)
    hz = Q[cr].values / NAZ * 100
    hb = np.where(hz <= 0, 5, np.digitize(hz, [10, 25, 50, 75])).astype(np.int16)
    a = np.where(look >= 0, hb[np.maximum(look, 0)], -1)
    paletted(a, pal_hz, 6).save(f"{IMG}/ov_hz_{e}.png", optimize=True, transparency=6)
    sizes[e] = (os.path.getsize(f"{IMG}/ov_near_{e}.png") + os.path.getsize(f"{IMG}/ov_hz_{e}.png")) // 1024

lk = merc_grid(ZZ - 2)
on = lk >= 0
j = np.maximum(lk, 0)
enc_near = lambda v: np.where(np.isfinite(v), np.clip(np.round(v * 5), 0, 250), 255)
enc_hz = lambda n_: np.clip(np.round(n_ / NAZ * 200), 0, 200)
A = np.zeros(lk.shape + (3,), np.uint8); B = np.zeros_like(A); Cc = np.zeros_like(A)
A[..., 0] = np.where(on, enc_near(Q.near_sea_km.values[j]), 255)
A[..., 1] = np.where(on, enc_hz(Q.sea_rays.values[j]), 255)
A[..., 2] = np.where(on, np.clip(np.round(np.maximum(Q.ground_m.values[j], 0) / 6), 0, 254), 255)
for k, e in enumerate(("5", "15", "50")):
    B[..., k] = np.where(on, enc_near(Q[EYEK[e][0]].values[j]), 255)
    Cc[..., k] = np.where(on, enc_hz(Q[EYEK[e][1]].values[j]), 255)
for nm, arr in (("grid_a", A), ("grid_b", B), ("grid_c", Cc)):
    Image.fromarray(arr, "RGB").save(f"{DATA}/{nm}.png", optimize=True)
gx0, gy0 = ll2px(LON0, LAT1, ZZ - 2); gx1, gy1 = ll2px(LON1, LAT0, ZZ - 2)

# search list: every settlement point
S = pd.read_csv(f"{DATA}/settlements_sea.csv")
S = S.sort_values("pop", ascending=False, na_position="last")
def enc(v):
    return None if not np.isfinite(v) else round(float(v), 1)
places = []
for _, s in S.iterrows():
    places.append([s["name"], s.county if isinstance(s.county, str) else "", round(s.lon, 4), round(s.lat, 4), int(s["pop"]) if s["pop"] == s["pop"] else 0,
                   [enc(s[f"near_{e}"]) for e in ("1.7", "5", "15", "50")], [int(s[f"nsea_{e}"]) for e in ("1.7", "5", "15", "50")]])
jsave({"fields": ["name", "county", "lon", "lat", "pop", "near_km_by_eye", "sea_rays_by_eye"], "eyes": EYES, "places": places}, f"{DATA}/places.json")
V = pd.read_csv(f"{DATA}/validation.csv")
site = {"bounds": BOUNDS, "grid": {"z": ZZ - 2, "x0": gx0, "y0": gy0, "x1": gx1, "y1": gy1, "w": int(lk.shape[1]), "h": int(lk.shape[0])},
        "eyes": ["1.7", "5", "15", "50"], "eye_pc": {e: R["eyes"][e]["uk_pc"] for e in ("1.7", "5", "15", "50")},
        "views": [{"name": r["name"], "lon": r.lon, "lat": r.lat, "h": int(r.published_m), "doc": r.documented, "src": r.source,
                   "t": int(r.terrain_50_sea), "p": int(r.published_50_sea),
                   "nt": None if r.terrain_50_near_km != r.terrain_50_near_km else float(r.terrain_50_near_km),
                   "np": None if r.published_50_near_km != r.published_50_near_km else float(r.published_50_near_km)} for _, r in V.iterrows()],
        "far": [{"lon": f["lon"], "lat": f["lat"], "km": round(f["km"], 1), "near": f["near"]["name"], "county": f["county"]} for f in R["farthest_seaview"][:3]]}
jsave(site, f"{DATA}/site.json")
print("overlay KB by eye", sizes, "grids KB", [os.path.getsize(f"{DATA}/{n}.png") // 1024 for n in ("grid_a", "grid_b", "grid_c")],
      "places KB", os.path.getsize(f"{DATA}/places.json") // 1024)

# index.html
KEEP = {"DOI", "DOI_URL", "BLOG_URL"}
t = open(os.path.join(ROOT, "code", "page_template.html"), encoding="utf-8").read()
t = t.replace("%%ESSAY%%", open(os.path.join(ROOT, "code", "page_essay.html"), encoding="utf-8").read())
t = t.replace("{{FULLSCREEN}}", open(os.path.join(ROOT, "code", "fullscreen_snippet.html"), encoding="utf-8").read())
t = t.replace("{{REPO}}", REPO).replace("{{AI}}", AI).replace("{{BYLINE}}", BYLINE).replace("{{VERSION}}", "2026a")
t = re.sub(r"\{\{([^{}|]+)(\|(\w+))?\}\}", lambda m: m.group(0) if m.group(1) in KEEP else fmt(get(R, m.group(1)), m.group(3)), t)
assert set(re.findall(r"\{\{([^}]+)\}\}", t)) <= KEEP, set(re.findall(r"\{\{([^}]+)\}\}", t))
vis = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", t, flags=re.S)
for bad in ("—", "–", "--", "DSIT", "DCMS", "civil serv", "pre-registered"):
    assert bad not in vis, bad
assert t.rstrip().endswith("</html>") and 'site-nav.js" defer></script>\n</body>' in t
open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(t)
print("index.html", len(t) // 1024, "KB")
