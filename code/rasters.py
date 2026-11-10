"""Display rasters: every square of data/squares.csv.gz placed on one British National Grid 1 km raster (GB squares are its
cells; Northern Ireland's Irish Grid squares are looked up at each BNG cell centre). Used by the figures, collage and GIF."""
import numpy as np
import pandas as pd
from pyproj import Transformer
from common import *

E0, E1, N0, N1 = -80000, 700000, 0, 1250000          # display extent (BNG metres)
W, H = (E1 - E0) // 1000, (N1 - N0) // 1000


def load_squares():
    return pd.read_csv(f"{DATA}/squares.csv.gz")


def disp_index(Q):
    """(H, W) int32 array: row of Q for each BNG display cell (row 0 = north), -1 where no square"""
    p = f"{SCR}/disp_idx_{len(Q)}.npy"
    if os.path.exists(p):
        a = np.load(p)
        if a.max() < len(Q):
            return a
    idx = np.full((H, W), -1, np.int32)
    gb = Q[Q.grid == "OSGB"]
    r = ((N1 - 500 - gb.N.values) // 1000).astype(int); c = ((gb.E.values - 500 - E0) // 1000).astype(int)
    idx[r, c] = gb.index.values
    ni = Q[Q.grid == "IG"]
    lookup = {(e, n): i for e, n, i in zip(ni.E.values, ni.N.values, ni.index.values)}
    cc, rr = np.meshgrid(np.arange(W), np.arange(H))
    Ec = E0 + 500 + cc * 1000.0; Nc = N1 - 500 - rr * 1000.0
    box = (Ec < 260000) & (Nc > 450000) & (Nc < 650000) & (idx < 0)
    lon, lat = Transformer.from_crs("EPSG:27700", "EPSG:4326", always_xy=True).transform(Ec[box], Nc[box])
    ie, inn = Transformer.from_crs("EPSG:4326", "EPSG:29903", always_xy=True).transform(lon, lat)
    ke = (np.floor(ie / 1000) * 1000 + 500).astype(int); kn = (np.floor(inn / 1000) * 1000 + 500).astype(int)
    vals = np.array([lookup.get((a, b), -1) for a, b in zip(ke, kn)], np.int32)
    idx[box] = vals
    np.save(p, idx)
    return idx


def to_raster(idx, values, fill=np.nan):
    out = np.full(idx.shape, fill, dtype=np.asarray(values).dtype if fill is None else np.result_type(np.asarray(values).dtype, type(fill)))
    m = idx >= 0
    out[m] = np.asarray(values)[idx[m]]
    return out


EXTENT = (E0, E1, N0, N1)                               # for imshow(origin="upper")
