"""Step 2: the observer squares.
GB: every Ordnance Survey National Grid 1 km square (EPSG:27700) whose centre is not OSM ocean and lies in England, Scotland or
Wales (counties_uk.geojson, nearest nation polygon within 2 km for centres on the shore). NI: Irish Grid 1 km squares
(EPSG:29903) in Northern Ireland, same rules. For each square: centre lon/lat, mosaic pixel position, nation and county,
ground height, distance to the coast (OSM ocean, metres), local relief (ground minus the mean of land within about 5 km).
Output: SCR/grid.npz"""
import numpy as np
from pyproj import Transformer
from shapely.geometry import shape
from shapely.ops import transform as stransform
from rasterio.features import rasterize
from rasterio.transform import Affine
from scipy.ndimage import distance_transform_edt, uniform_filter
from common import *

dem = np.load(f"{SCR}/dem.npy").astype(np.float32)
sea = np.load(f"{SCR}/sea.npy")
ox, oy = X0 * 256, Y0 * 256

feats = jload(f"{GEO}/counties_uk.geojson")["features"]
counties = [f["properties"]["county"] for f in feats]
to_px = lambda x, y, z=None: tuple(np.asarray(v) for v in ((lambda X, Y: (X - ox, Y - oy))(*ll2px(x, y))))
cr = rasterize([(stransform(to_px, shape(f["geometry"])), i + 1) for i, f in enumerate(feats)], out_shape=(NY, NX),
               transform=Affine.identity(), dtype="int32")
# nearest county pixel for every pixel (to place shore centres that fall just outside the coarse polygons)
dist_c, (iy_c, ix_c) = distance_transform_edt(cr == 0, return_indices=True)
dist_c = dist_c.astype(np.float32)
# Ireland and the Isle of Man (Natural Earth): centres there are never UK squares, however close to the border
cs = jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]
foreign = rasterize([(stransform(to_px, shape(f["geometry"])), 1) for f in cs if f["properties"]["ADM0_A3"] in ("IRL", "IMN")],
                    out_shape=(NY, NX), transform=Affine.identity(), dtype="uint8") > 0
lat_rows = px2ll(np.zeros(NY) + ox, np.arange(NY) + oy + 0.5)[1]
mpp_rows = (C_MERC / (256 * 2 ** Z)) * np.cos(np.radians(lat_rows))
dcoast = distance_transform_edt(~sea).astype(np.float32) * mpp_rows[:, None].astype(np.float32)
landh = np.where(sea, np.nan, dem)
w = (~sea).astype(np.float32)
k = 57                                   # about 10 km box (5 km radius) at 175 m pixels
num = uniform_filter(np.where(sea, 0, dem), size=k); den = uniform_filter(w, size=k)
meanland = num / np.maximum(den, 1e-6)
del num, den, w, landh


def squares(epsg, e0, e1, n0, n1, keep_nations):
    E, N = np.meshgrid(np.arange(e0, e1, 1000) + 500.0, np.arange(n0, n1, 1000) + 500.0)
    E, N = E.ravel(), N.ravel()
    lon, lat = Transformer.from_crs(epsg, "EPSG:4326", always_xy=True).transform(E, N)
    X, Y = ll2px(lon, lat)
    u, v = X - ox - 0.5, Y - oy - 0.5
    ok = (u > 2) & (v > 2) & (u < NX - 3) & (v < NY - 3)
    E, N, lon, lat, u, v = (a[ok] for a in (E, N, lon, lat, u, v))
    iu, iv = np.round(u).astype(int), np.round(v).astype(int)
    notsea = ~sea[iv, iu]
    c = cr[iv, iu]
    # nearest county within 2 km for centres just outside the coarse polygons: on the shore, and in the slivers between
    # neighbouring county polygons inland (the simplified ONS outlines do not share edges exactly)
    near = (dist_c[iv, iu] * mpp_rows[iv] <= 2000) & ~foreign[iv, iu]
    c = np.where(c > 0, c, np.where(near, cr[iy_c[iv, iu], ix_c[iv, iu]], 0))
    nat = np.array([feats[i - 1]["properties"]["nation"] if i > 0 else "" for i in c])
    keep = notsea & np.isin(nat, keep_nations)
    sel = lambda a: a[keep]
    return dict(E=sel(E), N=sel(N), lon=sel(lon), lat=sel(lat), u=sel(u), v=sel(v), county=sel(c) - 1,
                nation=np.array([NATIONS.index(x) for x in nat[keep]], np.int8),
                dcoast=dcoast[iv, iu][keep], relief=(dem[iv, iu] - meanland[iv, iu])[keep])


gb = squares("EPSG:27700", 0, 700000, 0, 1250000, ["England", "Scotland", "Wales"])
ni = squares("EPSG:29903", 180000, 380000, 300000, 470000, ["Northern Ireland"])
out = {}
for key, g in (("gb", gb), ("ni", ni)):
    for f, a in g.items():
        out[f"{key}_{f}"] = a
np.savez_compressed(f"{SCR}/grid.npz", counties=np.array(counties), **out)
for key, g in (("gb", gb), ("ni", ni)):
    print(key, len(g["E"]), {NATIONS[i]: int((g["nation"] == i).sum()) for i in range(4)}, "max dcoast km", round(float(g["dcoast"].max()) / 1000, 1))
