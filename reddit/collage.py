"""Reddit collage (r/dataisbeautiful style, light background): the UK map of the nearest visible sea, the four eye heights,
the inland profile and the key numbers. Reads data/squares.csv.gz, data/profile.csv and data/results.json.
Run from the study root: python3 reddit/collage.py"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
import numpy as np
import pandas as pd
from matplotlib.patches import Patch, Polygon as MPoly
from matplotlib.collections import PatchCollection
from matplotlib.colors import ListedColormap
from shapely.geometry import shape
from pyproj import Transformer
from figstyle import *
from rasters import *

R = jload(f"{DATA}/results.json")
Q = load_squares()
idx = disp_index(Q)
TB = Transformer.from_crs(4326, 27700, always_xy=True)
CTX = []
for f in jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]:
    if f["properties"]["ADM0_A3"] in ("IRL", "IMN", "FRA"):
        g = shape(f["geometry"])
        for p in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
            x, y = np.asarray(p.exterior.coords).T
            if x.max() < -11 or x.min() > 3 or y.max() < 49 or y.min() > 61:
                continue
            X, Y = TB.transform(x, y); CTX.append(np.c_[X, Y])


def base(ax, ext):
    ax.set_facecolor(SEA)
    ax.add_collection(PatchCollection([MPoly(r, closed=True) for r in CTX], facecolor="#ECE8DF", edgecolor="#CFC8B8", lw=0.4, zorder=1))
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


cmap, norm = class_cmap()
cls = dist_class(np.nan_to_num(Q.near_sea_km.values, nan=1e9)).astype(float)
W_IN, H_IN = 16, 13.5
fig = plt.figure(figsize=(W_IN, H_IN), facecolor=PAPER)
M = R["main"]
fig.text(0.03, 0.972, "Can you see the sea? Every 1 km square of the UK", fontproperties=DISP, fontsize=34, color=FG, va="top")
fig.text(0.03, 0.928, f"Standing on the bare ground with eyes 1.7 m up, {M['uk_pc']:.0f}% of the UK's land has the sea in view within 50 km. "
         f"Climb to an upstairs window and it is {R['eyes']['5']['uk_pc']:.0f}%.", fontproperties=SERP, fontsize=16, color=MUT, va="top")
# big map
ax = fig.add_axes([0.01, 0.07, 0.47, 0.84])
ext = (E0 + 15000, E1, 0, 1230000)
base(ax, ext)
ax.imshow(np.ma.masked_invalid(to_raster(idx, cls)), extent=EXTENT, origin="upper", cmap=cmap, norm=norm, interpolation="nearest", zorder=2)
h = [Patch(facecolor=c, label=l) for c, l in zip(DCOL, DLAB)] + [Patch(facecolor=NOVIEW, label="no sea within 50 km")]
lg = ax.legend(handles=h, loc="upper left", fontsize=10.5, title="Nearest sea in view", title_fontsize=11.5, frameon=True, borderpad=0.6, bbox_to_anchor=(0.005, 0.995))
lg.get_frame().set_facecolor(PAPER); lg.get_frame().set_edgecolor(RULE)
F = R["farthest_seaview"][0]
ax.plot([F["E"]], [F["N"]], marker="*", ms=20, color=HOT, mec="white", zorder=6)
ax.annotate(f"Farthest from any sea view:\n{F['km']:.0f} km, in {F['county']}", (F["E"], F["N"]), xytext=(430000, 22000), ha="left", fontsize=11.5, color=FG,
            arrowprops=dict(arrowstyle="-", color=FG, lw=0.9, shrinkB=6), bbox=dict(boxstyle="round,pad=0.35", fc=PAPER, ec=RULE), zorder=7)
# eye heights
labels = [("1.7", "sea_rays", "Standing\n1.7 m"), ("5", "sea_rays_eye5", "Upstairs\n5 m"), ("15", "sea_rays_eye15", "Fifth floor\n15 m"), ("50", "sea_rays_eye50", "Tall tower\n50 m")]
for k, (e, c, lab) in enumerate(labels):
    a = fig.add_axes([0.49 + k * 0.125, 0.50, 0.12, 0.36])
    base(a, ext)
    rr = to_raster(idx, (Q[c].values > 0).astype(float))
    a.imshow(np.ma.masked_invalid(rr), extent=EXTENT, origin="upper", cmap=ListedColormap([NOVIEW, YES]), vmin=0, vmax=1, interpolation="nearest", zorder=2)
    a.set_title(f"{lab.replace(chr(10), ' ')}: {R['eyes'][e]['uk_pc']:.0f}%", fontsize=12.5, color=FG, loc="left", fontproperties=SERP)
fig.text(0.49, 0.875, "Higher eyes, more sea: share of UK land with the sea in view", fontproperties=DISPB, fontsize=16, color=FG, va="bottom")
fig.legend(handles=[Patch(facecolor=YES, label="sea in view"), Patch(facecolor=NOVIEW, label="no sea in view")], loc="lower left",
           bbox_to_anchor=(0.49, 0.455), ncol=2, fontsize=11, frameon=False)
# profile
P = pd.read_csv(f"{DATA}/profile.csv")
a = fig.add_axes([0.54, 0.10, 0.25, 0.28]); a.set_facecolor(PAPER); style_axes(a)
for b, g in P.groupby("band", sort=False):
    a.plot(g.km, g.pc, color=BANDCOL[b], lw=2.4, label=(f"ground {b} m" if b != "300+" else "over 300 m"))
a.axhline(50, color=MUT, lw=0.8, ls=(0, (3, 3)))
a.set_xlim(0, 60); a.set_ylim(0, 100); a.set_xlabel("km from the coast", fontsize=11); a.set_ylabel("% of squares seeing the sea", fontsize=11)
a.legend(frameon=False, fontsize=10, loc="upper right")
fig.text(0.54, 0.395, "How far inland the sea stays in view", fontproperties=DISPB, fontsize=15, color=FG, va="bottom")
# numbers
y = 0.37
ppl = R["pop"]["1.7"]["gb_pc"]
lines = [(f"{ppl:.0f}%", "of people in Great Britain\nsee the sea from their\nsettlement's point"),
         (f"{R['near']['median_km']:.0f} km", "median distance to the\nnearest sea in view\n(where there is one)"),
         (f"{R['validation']['published_50']} of {R['validation']['n']}", "named viewpoints with a\ndocumented sea view\nreproduced (surveyed heights)")]
for big_, small_ in lines:
    fig.text(0.815, y, big_, fontproperties=DISP, fontsize=28, color=HOT, va="top")
    fig.text(0.815, y - 0.04, small_, fontsize=11, color=FG, va="top", linespacing=1.25)
    y -= 0.115
fig.text(0.03, 0.018, "Data: AWS Terrain Tiles (zoom 9; SRTM, GMTED, ETOPO1); sea from OpenStreetMap (ODbL) via OpenFreeMap; Wikidata settlements; 2011 Census.\n"
         "All figures are upper bounds: bare terrain, no buildings or trees. Resolution-sensitive: finer terrain lowers the share by up to " + f"{R['z10']['max_abs_diff']:.1f}" + " points.\n"
         "Sea includes tidal estuaries and sea lochs; k = 0.13; 360 sight lines per square to 50 km; people: GB only.", fontsize=10, color=MUT, va="bottom")
fig.text(0.97, 0.012, "Dr Tristan Hotham  ·  maps.tristanhotham.com/sea-view", fontsize=11, color=FG, ha="right")
out = os.path.join(ROOT, "reddit", "sea_view_collage.png")
fig.savefig(out, dpi=170, facecolor=PAPER)
plt.close(fig)
from PIL import Image
im = Image.open(out); print(out, im.size)
assert im.size[0] >= 2400
