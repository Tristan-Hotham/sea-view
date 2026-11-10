"""Step 4 (check S6): terrain resolution. In four test windows the zoom-10 Terrarium tiles (about 88 m, raw_new8, read only) replace
the zoom-9 terrain; the sea mask is the zoom-9 mask at double resolution, so only the terrain changes. Observers are the main
grid squares within 50 km of the window centre (so every 50 km ray stays inside the 100 km half-width window).
Output: SCR/z10.npz (square index, z10 nearest, z10 rays with sea) and SCR/z10_meta.json."""
import time
import numpy as np
import numba
from PIL import Image
from scipy.ndimage import median_filter, maximum_filter, minimum_filter, zoom as ndzoom
from viewshed import viewshed
from common import *

numba.set_num_threads(int(os.environ.get("SV_THREADS", "2")))
WINDOWS = {"Cumbria and Lancashire coast": (-3.0, 54.3), "Cornwall": (-4.9, 50.4), "Lothian and Fife": (-3.0, 56.1),
           "Norfolk": (1.0, 52.7)}
dem9 = np.load(f"{SCR}/dem.npy").astype(np.float32)
sea9 = np.load(f"{SCR}/sea.npy")
G = np.load(f"{SCR}/grid.npz")
LON = np.concatenate([G["gb_lon"], G["ni_lon"]]); LAT = np.concatenate([G["gb_lat"], G["ni_lat"]])
Z10 = 10; NT10 = 256 * 2 ** Z10; PIX10 = C_MERC / NT10
idx_all, near_all, nsea_all, win_all = [], [], [], []
meta = {}
for wi, (name, (clon, clat)) in enumerate(WINDOWS.items()):
    t0 = time.time()
    cache = f"{SCR}/z10_w{wi}.npz"
    if os.path.exists(cache):
        c = np.load(cache, allow_pickle=True)
        idx_all.append(c["idx"]); near_all.append(c["near"]); nsea_all.append(c["nsea"]); win_all.append(c["win"]); meta[name] = c["meta"].item()
        continue
    cx, cy = ll2px(clon, clat, Z10)
    half = 100000.0 / (PIX10 * math.cos(math.radians(clat)))      # 100 km in z10 pixels
    gx0 = int((cx - half) // 256) * 256; gx1 = int((cx + half) // 256 + 1) * 256
    gy0 = int((cy - half) // 256) * 256; gy1 = int((cy + half) // 256 + 1) * 256
    H, W = gy1 - gy0, gx1 - gx0
    # z9 background (bilinear up) and z9 sea (nearest up) on the z10 pixel grid
    a0, a1 = gy0 // 2 - Y0 * 256 - 1, gy1 // 2 - Y0 * 256 + 1
    b0, b1 = gx0 // 2 - X0 * 256 - 1, gx1 // 2 - X0 * 256 + 1
    sub = dem9[max(a0, 0):a1, max(b0, 0):b1]
    up = ndzoom(sub, 2, order=1)
    off_y = (gy0 - 2 * (Y0 * 256 + max(a0, 0))); off_x = (gx0 - 2 * (X0 * 256 + max(b0, 0)))
    sup = np.repeat(np.repeat(sea9[max(a0, 0):a1, max(b0, 0):b1], 2, 0), 2, 1)
    dem = np.zeros((H, W), np.float32); sea = np.ones((H, W), bool)   # beyond the zoom-9 mosaic (east of 2.1 E): North Sea
    hh, ww = min(H, up.shape[0] - off_y), min(W, up.shape[1] - off_x)
    dem[:hh, :ww] = up[off_y:off_y + hh, off_x:off_x + ww]; sea[:hh, :ww] = sup[off_y:off_y + hh, off_x:off_x + ww]
    assert dem.shape == (H, W) and sea.shape == (H, W), (dem.shape, sea.shape, H, W)
    got = 0
    z = np.full((H, W), np.nan, np.float32)
    for tx in range(gx0 // 256, gx1 // 256):
        for ty in range(gy0 // 256, gy1 // 256):
            p = f"{DEM10}/{tx}/{ty}.png"
            if not os.path.exists(p):
                continue
            arr = np.asarray(Image.open(p).convert("RGB"), np.float32)
            z[(ty * 256 - gy0):(ty * 256 - gy0 + 256), (tx * 256 - gx0):(tx * 256 - gx0 + 256)] = arr[..., 0] * 256 + arr[..., 1] + arr[..., 2] / 256 - 32768
            got += 1
    have = np.isfinite(z)
    zf = np.where(have, z, dem)
    fp = np.ones((3, 3), bool); fp[1, 1] = False
    for it in range(4):                                   # the same despiking rule as step 1
        med = median_filter(zf, size=7); nmax = maximum_filter(zf, footprint=fp); nmin = minimum_filter(zf, footprint=fp)
        bad = ((np.abs(zf - med) > 150) | (zf - nmax > 60) | (nmin - zf > 60)) & (zf > -50)
        if not bad.any():
            break
        zf[bad] = med[bad]
    zf[sea] = 0
    zf[(~sea) & (zf < -5)] = 0
    # observers: main squares within 50 km of the centre
    d = gc_km(clat, clon, LAT, LON)
    idx = np.where(d <= 50)[0]
    X, Y = ll2px(LON[idx], LAT[idx], Z10)
    u, v = X - gx0 - 0.5, Y - gy0 - 0.5
    r = viewshed(zf, sea, u, v, gy0 + 0.5, NT10, PIX10, EYE, DMAX, NAZ, K_REFR, 0.5, 0.0, np.zeros((0, NAZ), np.float32))
    idx_all.append(idx); near_all.append(r[0]); nsea_all.append(r[1]); win_all.append(np.full(len(idx), wi, np.int8))
    meta[name] = m_ = {"centre": [clon, clat], "z10_tiles": got, "pixels": [W, H], "z10_coverage": round(float(have.mean()), 3),
                  "squares": int(len(idx)), "oob_rays": int(r[2].sum()), "seconds": round(time.time() - t0)}
    np.savez_compressed(cache, idx=idx, near=r[0], nsea=r[1], win=win_all[-1], meta=np.array(m_, dtype=object))
    print(name, meta[name], "z10 share", round(float((r[1] > 0).mean()), 4), flush=True)
np.savez_compressed(f"{SCR}/z10.npz", idx=np.concatenate(idx_all), near=np.concatenate(near_all), nsea=np.concatenate(nsea_all),
                    win=np.concatenate(win_all), names=np.array(list(WINDOWS)))
jsave(meta, f"{SCR}/z10_meta.json", indent=1)
