"""Step 5 (check S9): terrain error, after Fisher's probable viewshed. 2,000 random squares; 20 realisations each of spatially
correlated Gaussian error added to every land pixel (Gaussian-filtered white noise, sigma 4 pixels, about 1 km correlation
length, rescaled to the target standard deviation), for standard deviations of 5 m and 10 m. The sea stays at 0 m.
Output: SCR/mc.npz (square index, rays with sea for every realisation)."""
import time
import numpy as np
import numba
from scipy.ndimage import gaussian_filter
from viewshed import viewshed
from common import *

numba.set_num_threads(int(os.environ.get("SV_THREADS", "2")))
dem = np.load(f"{SCR}/dem.npy").astype(np.float32)
sea = np.load(f"{SCR}/sea.npy")
G = np.load(f"{SCR}/grid.npz")
U = np.concatenate([G["gb_u"], G["ni_u"]]).astype(np.float64)
V = np.concatenate([G["gb_v"], G["ni_v"]]).astype(np.float64)
rng = np.random.default_rng(1993)
idx = np.sort(rng.choice(len(U), 2000, replace=False))
NREAL = 20
res = {}
for sd in (5.0, 10.0):
    out = np.zeros((NREAL, len(idx)), np.int16)
    for r in range(NREAL):
        t = time.time()
        e = gaussian_filter(rng.standard_normal(dem.shape, dtype=np.float32), sigma=4.0)
        e *= sd / e.std()
        d2 = np.where(sea, 0.0, dem + e).astype(np.float32)
        del e
        rr = viewshed(d2, sea, U[idx], V[idx], Y0 * 256 + 0.5, 256 * 2 ** Z, C_MERC / (256 * 2 ** Z), EYE, DMAX, NAZ, K_REFR, 0.5, 0.0,
                      np.zeros((0, NAZ), np.float32))
        out[r] = rr[1]
        del d2
        print("sd", sd, "real", r, round(time.time() - t), "s share", round(float((rr[1] > 0).mean()), 4), flush=True)
    res[f"sd{int(sd)}"] = out
np.savez_compressed(f"{SCR}/mc.npz", idx=idx, **res)
