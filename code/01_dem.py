"""Step 1: the terrain and the sea.
- Mosaic the 450 zoom-9 Terrarium tiles (read from the shared packs in RAW, never modified) into one height grid (int16 m,
  Web Mercator pixels, x 244..258, y 145..174), despiked as in sunless-valleys.
- Fetch the OpenFreeMap zoom-9 vector tiles for the same block one at a time, rasterise the water layer's class "ocean"
  onto the same pixels (pixel centre rule) and delete each tile at once.
- Heights: sea pixels 0 m; land pixels below -5 m (bathymetry bleeding over the shore) set to 0.
Outputs in SCR: dem.npy (int16, sea 0), sea.npy (bool), meta.json."""
import io, time, urllib.request
import numpy as np
from PIL import Image
import mapbox_vector_tile as mvt
from rasterio.features import rasterize
from shapely.geometry import shape
from shapely.affinity import scale
from scipy.ndimage import median_filter, maximum_filter, minimum_filter
from common import *

dem = np.full((NY, NX), -32768, np.int32)
n_tiles = 0
for k in range(6):
    idx = jload(f"{RAW}/terrarium_z9_pack{k}.json")
    with open(f"{RAW}/terrarium_z9_pack{k}.bin", "rb") as f:
        blob = f.read()
    for fn, off, ln in idx:
        _, tx, ty = fn[:-4].split("_"); tx, ty = int(tx), int(ty)
        a = np.asarray(Image.open(io.BytesIO(blob[off:off + ln])).convert("RGB"), np.float32)
        h = a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768
        dem[(ty - Y0) * 256:(ty - Y0 + 1) * 256, (tx - X0) * 256:(tx - X0 + 1) * 256] = np.round(h)
        n_tiles += 1
    del blob
assert n_tiles == (X1 - X0 + 1) * (Y1 - Y0 + 1) and (dem > -32768).all(), n_tiles
print("tiles", n_tiles, "range", dem.min(), dem.max())

fp = np.ones((3, 3), bool); fp[1, 1] = False
d = dem.astype(np.float32); fixed = 0
for it in range(4):
    med = median_filter(d, size=7)
    nmax = maximum_filter(d, footprint=fp); nmin = minimum_filter(d, footprint=fp)
    bad = ((np.abs(d - med) > 150) | (d - nmax > 60) | (nmin - d > 60)) & (d > -50)   # leave the sea floor alone
    nb = int(bad.sum()); fixed += nb
    print("despike pass", it, nb)
    if not nb:
        break
    d[bad] = med[bad]
del med, nmax, nmin, bad

# sea mask from OpenFreeMap
tj = json.load(urllib.request.urlopen(urllib.request.Request("https://tiles.openfreemap.org/planet", headers=UA)))
URL = tj["tiles"][0]
VERSION = URL.split("/")[-4]
sea = np.zeros((NY, NX), bool)
nbytes = 0
tmpdir = f"{SCR}/tiles"; os.makedirs(tmpdir, exist_ok=True)
t0 = time.time()
for tx in range(X0, X1 + 1):
    for ty in range(Y0, Y1 + 1):
        for k in range(6):
            try:
                b = urllib.request.urlopen(urllib.request.Request(URL.format(z=Z, x=tx, y=ty), headers=UA), timeout=60).read()
                break
            except Exception:
                time.sleep(2 + 4 * k)
        else:
            raise RuntimeError(f"tile {tx},{ty}")
        nbytes += len(b)
        tmp = f"{tmpdir}/{tx}_{ty}.pbf"
        open(tmp, "wb").write(b)
        dd = mvt.decode(open(tmp, "rb").read(), default_options={"y_coord_down": True})
        os.remove(tmp)
        W = dd.get("water", {}); ext = W.get("extent", 4096)
        shapes = [(scale(shape(f["geometry"]), 256 / ext, 256 / ext, origin=(0, 0)), 1)
                  for f in W.get("features", []) if f["properties"].get("class") == "ocean"]
        m = rasterize(shapes, out_shape=(256, 256), fill=0, dtype="uint8") if shapes else np.zeros((256, 256), np.uint8)
        sea[(ty - Y0) * 256:(ty - Y0 + 1) * 256, (tx - X0) * 256:(tx - X0 + 1) * 256] = m > 0
os.rmdir(tmpdir)
print("ofm", VERSION, round(nbytes / 1e6, 1), "MB", round(time.time() - t0), "s; sea share", sea.mean().round(3))

land_neg = (~sea) & (d < -5)
d[sea] = 0
d[land_neg] = 0
out = np.clip(np.round(d), -100, 2000).astype(np.int16)
np.save(f"{SCR}/dem.npy", out); np.save(f"{SCR}/sea.npy", sea)
jsave({"tiles": n_tiles, "despiked": fixed, "ofm_version": VERSION, "ofm_url": URL, "ofm_mb": round(nbytes / 1e6, 1),
       "land_below_m5_set0": int(land_neg.sum()), "land_below0": int(((~sea) & (out < 0)).sum()),
       "max_m": int(out.max())}, f"{SCR}/meta.json", indent=1)
print("saved; max", out.max(), "land<0 px", int(((~sea) & (out < 0)).sum()))
