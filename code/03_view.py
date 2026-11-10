"""Step 3: run the line-of-sight kernel for every square, for the main specification and the planned variants.
Variants (NOTES.md): main (eye 1.7 m, 50 km, k 0.13, 360 rays); eye 5, 15, 50 m; D 25 and 100 km; k 0 and 0.25; open sea
only (S7); 720 rays on a 5% sample (S4); four quarter-points per square on a 500 m grid for a random quarter of squares (S5). Settlements (Wikidata points) for
every eye height. Output: SCR/v_<variant>.npz (per square: nearest visible sea m as float32, rays with sea int16; written as each variant
finishes, and skipped when rerun), SCR/rays_main.npy (packed bits of the 360 rays with sea, main run), SCR/v_sett.npz."""
import sys, time
import numpy as np
import numba
import pandas as pd
from scipy.ndimage import binary_opening
from viewshed import viewshed
from common import *

numba.set_num_threads(int(os.environ.get("SV_THREADS", "2")))
dem = np.load(f"{SCR}/dem.npy").astype(np.float32)
sea = np.load(f"{SCR}/sea.npy")
G = np.load(f"{SCR}/grid.npz")
U = np.concatenate([G["gb_u"], G["ni_u"]]).astype(np.float64)
V = np.concatenate([G["gb_v"], G["ni_v"]]).astype(np.float64)
n = len(U)
GY0, NT, PIX0 = Y0 * 256 + 0.5, 256 * 2 ** Z, C_MERC / (256 * 2 ** Z)
NOR = np.zeros((0, NAZ), np.float32)


def done(name):
    return os.path.exists(f"{SCR}/v_{name}.npz")


def save(name, **a):
    np.savez_compressed(f"{SCR}/v_{name}.npz", **a)


def run(u, v, eye=EYE, dmax=DMAX, k=K_REFR, naz=NAZ, seamask=sea, rays=None, az0=0.0):
    t = time.time()
    r = viewshed(dem, seamask, u, v, GY0, NT, PIX0, eye, dmax, naz, k, 0.5, az0, NOR if rays is None else rays)
    return r, time.time() - t


times = jload(f"{SCR}/times.json") if os.path.exists(f"{SCR}/times.json") else {}
if not done("main"):
    rays = np.full((n, NAZ), np.inf, np.float32)
    (r, dt) = run(U, V, rays=rays); times["main"] = dt
    np.save(f"{SCR}/rays_main.npy", np.packbits(np.isfinite(rays), axis=1))
    del rays
    save("main", near=r[0], nsea=r[1], oob=r[2], ground=r[3]); jsave(times, f"{SCR}/times.json", indent=1)
    print("main", round(dt), "s; share", round(float((r[1] > 0).mean()), 4), "rays leaving mosaic", int(r[2].sum()), flush=True)

VARS = (("eye5", dict(eye=5.0)), ("eye15", dict(eye=15.0)), ("eye50", dict(eye=50.0)), ("d25", dict(dmax=25000.0)),
                 ("d100", dict(dmax=100000.0)), ("k0", dict(k=0.0)), ("k25", dict(k=0.25)))
for name, kw in (VARS[::-1] if os.environ.get("SV_REVERSE") else VARS):
    if done(name) or os.environ.get("SV_SKIPLOOP"):        # SV_SKIPLOOP=1: a second process for the later checks
        continue
    (r, dt) = run(U, V, **kw); times[name] = dt
    save(name, near=r[0], nsea=r[1]); jsave(times, f"{SCR}/times.json", indent=1)
    print(name, round(dt), "s; share", round(float((r[1] > 0).mean()), 4), flush=True)

# S7: open sea only. Remove ocean pixels in channels narrower than about 1 km (opening with a 7 x 7 disc, about 1.2 km at
# 175 m pixels): estuaries and narrow sea lochs become non-sea at height 0 (they still do not block anything).
yy, xx = np.mgrid[-3:4, -3:4]
if not done("opensea"):
    open_sea = binary_opening(sea, structure=(xx ** 2 + yy ** 2) <= 9.5)
    (r, dt) = run(U, V, seamask=open_sea); times["opensea"] = dt
    save("opensea", near=r[0], nsea=r[1], removed=int(sea.sum() - open_sea.sum())); jsave(times, f"{SCR}/times.json", indent=1)
    print("opensea", round(dt), "s; share", round(float((r[1] > 0).mean()), 4), "sea px removed", int(sea.sum() - open_sea.sum()), flush=True)
    del open_sea

# S4: 720 rays on a 5% random sample
rng = np.random.default_rng(20261110)
s4 = np.sort(rng.choice(n, n // 20, replace=False))
if not done("az720"):
    (r, dt) = run(U[s4], V[s4], naz=720); times["az720"] = dt
    save("az720", idx=s4, near=r[0], nsea=r[1]); jsave(times, f"{SCR}/times.json", indent=1)
    print("az720", round(dt), "s", flush=True)

# S5: four quarter-points per square (offsets of 250 m along the grid axes), on each square's own grid, for a random 25%
# of squares (the machine is shared: the full grid would take four times the main run)
s5 = np.sort(rng.choice(n, n // 4, replace=False))
from pyproj import Transformer
E = np.concatenate([G["gb_E"], G["ni_E"]]); N = np.concatenate([G["gb_N"], G["ni_N"]])
isgb = np.r_[np.ones(len(G["gb_E"]), bool), np.zeros(len(G["ni_E"]), bool)]
E, N, isgb = E[s5], N[s5], isgb[s5]
m5 = len(s5)
if not done("q500"):
    q_near = np.full((m5, 4), np.inf, np.float32); q_nsea = np.zeros((m5, 4), np.int16)
    for qi, (de, dn) in enumerate(((-250, -250), (250, -250), (-250, 250), (250, 250))):
        qu = np.empty(m5); qv = np.empty(m5)
        for epsg, m in (("EPSG:27700", isgb), ("EPSG:29903", ~isgb)):
            lon, lat = Transformer.from_crs(epsg, "EPSG:4326", always_xy=True).transform(E[m] + de, N[m] + dn)
            X, Y = ll2px(lon, lat)
            qu[m], qv[m] = X - X0 * 256 - 0.5, Y - Y0 * 256 - 0.5
        qsea = sea[np.round(qv).astype(int), np.round(qu).astype(int)]
        (r, dt) = run(qu, qv); times[f"q{qi}"] = dt
        q_near[:, qi] = np.where(qsea, 0, r[0]); q_nsea[:, qi] = np.where(qsea, -1, r[1])   # a quarter-point at sea: -1
        print("quarter", qi, round(dt), "s", flush=True)
    save("q500", idx=s5, near=q_near, nsea=q_nsea); jsave(times, f"{SCR}/times.json", indent=1)

# settlements: their own points, every eye height
if done("sett"):
    sys.exit(0)
S = pd.read_csv(SETT)
X, Y = ll2px(S.lon.values, S.lat.values)
su, sv = X - X0 * 256 - 0.5, Y - Y0 * 256 - 0.5
ssea = sea[np.clip(np.round(sv).astype(int), 0, NY - 1), np.clip(np.round(su).astype(int), 0, NX - 1)]
sres = {"qid": S.qid.values, "atsea": ssea}
for eye in EYES:
    (r, dt) = run(su, sv, eye=eye)
    sres[f"near_{eye:g}"], sres[f"nsea_{eye:g}"] = r[0], r[1]
    if eye == EYE:
        sres["ground"] = r[3]
save("sett", **sres)
print("settlements", len(S), "at sea pixel", int(ssea.sum()), "share 1.7", round(float((sres["nsea_1.7"] > 0).mean()), 4), flush=True)
jsave(times, f"{SCR}/times.json", indent=1)
print("total", round(sum(times.values())), "s")
