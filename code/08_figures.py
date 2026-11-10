"""Step 8: figures for the paper (release/paper/f_*.pdf), the blog (release/blog/b_*.png, 1800 px) and the page (img/*.jpg),
and the social card header.png. Everything is drawn from data/*.csv and data/results.json (plus the terrain for the
viewpoint fans)."""
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon as MPoly, Patch
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D
from shapely.geometry import shape
from pyproj import Transformer
from figstyle import *
from rasters import *
from viewshed import viewshed

R = jload(f"{DATA}/results.json")
Q = load_squares()
idx = disp_index(Q)
TB = Transformer.from_crs(4326, 27700, always_xy=True)
NE = jload(f"{GEO}/ne_10m_admin_0_countries.geojson")["features"]
CTX = []
for f in NE:
    if f["properties"]["ADM0_A3"] in ("IRL", "IMN", "FRA", "BEL", "NLD"):
        g = shape(f["geometry"])
        for p in (g.geoms if g.geom_type == "MultiPolygon" else [g]):
            x, y = np.asarray(p.exterior.coords).T
            if x.max() < -11 or x.min() > 3 or y.max() < 49 or y.min() > 61:
                continue
            X, Y = TB.transform(x, y)
            CTX.append(np.c_[X, Y])


def base(ax, extent=EXTENT, ctx=True):
    ax.set_facecolor(SEA)
    if ctx:
        ax.add_collection(PatchCollection([MPoly(r, closed=True) for r in CTX], facecolor="#ECE8DF", edgecolor="#CFC8B8", lw=0.4, zorder=1))
    ax.set_xlim(extent[0], extent[1]); ax.set_ylim(extent[2], extent[3]); ax.set_aspect("equal")
    ax.set_xticks([]); ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


cmap, norm = class_cmap()
near = Q.near_sea_km.values
cls = dist_class(np.nan_to_num(near, nan=1e9))
rast_cls = to_raster(idx, cls.astype(float))
rast_cls_m = np.ma.masked_invalid(rast_cls)
M = R["main"]


def legend_dist(ax, loc="upper left", title="Nearest sea you can see", fs=9.5):
    h = [Patch(facecolor=c, edgecolor="none", label=l) for c, l in zip(DCOL, DLAB)] + [Patch(facecolor=NOVIEW, edgecolor="none", label="no sea within 50 km")]
    lg = ax.legend(handles=h, loc=loc, frameon=True, fontsize=fs, title=title, title_fontsize=fs + 0.5, borderpad=0.7)
    lg.get_frame().set_facecolor(PAPER); lg.get_frame().set_edgecolor(RULE)
    lg._legend_box.align = "left"
    return lg


# 1. the main map
fig = plt.figure(figsize=(7.2, 10.4), facecolor=PAPER)
ax = fig.add_axes([0.0, 0.035, 1.0, 0.875])
base(ax, (E0 + 10000, E1, 0, 1230000))
ax.imshow(rast_cls_m, extent=EXTENT, origin="upper", cmap=cmap, norm=norm, interpolation="nearest", zorder=2)
fig.text(0.04, 0.975, "Can you see the sea?", fontproperties=DISP, fontsize=24, color=FG, va="top")
fig.text(0.04, 0.938, f"Every 1 km square of the UK, standing on the bare ground with eyes 1.7 m up.\n{M['uk_pc']:.0f}% of the land has the sea in view within 50 km.",
         fontproperties=SERP, fontsize=10.5, color=MUT, va="top")
lg = legend_dist(ax, loc="upper left", fs=8.5); lg.set_bbox_to_anchor((0.005, 0.995), transform=ax.transAxes)
fig.text(0.02, 0.012, "AWS Terrain Tiles (zoom 9); sea: OpenStreetMap via OpenFreeMap. Line of sight with curvature and refraction (k = 0.13),\n360 rays to 50 km. Dr Tristan Hotham, maps.tristanhotham.com/sea-view", fontsize=6.5, color=MUT)
savefig(fig, "map", blog="map", img="map")

# 2. four eye heights
fig, axs = plt.subplots(1, 4, figsize=(12, 5.6), facecolor=PAPER)
fig.subplots_adjust(left=0.01, right=0.99, top=0.84, bottom=0.02, wspace=0.03)
cols = {"1.7": "nsea_main", "5": "sea_rays_eye5", "15": "sea_rays_eye15", "50": "sea_rays_eye50"}
cols = {"1.7": "sea_rays", "5": "sea_rays_eye5", "15": "sea_rays_eye15", "50": "sea_rays_eye50"}
labels = {"1.7": "Standing (1.7 m)", "5": "Upstairs window (5 m)", "15": "Fifth floor (15 m)", "50": "Tall tower (50 m)"}
from matplotlib.colors import ListedColormap as LC
for a, (e, c) in zip(axs, cols.items()):
    base(a, (E0 + 10000, E1, 0, 1230000))
    rr = to_raster(idx, (Q[c].values > 0).astype(float))
    a.imshow(np.ma.masked_invalid(rr), extent=EXTENT, origin="upper", cmap=LC([NOVIEW, YES]), vmin=0, vmax=1, interpolation="nearest", zorder=2)
    a.set_title(f"{labels[e]}\n{R['eyes'][e]['uk_pc']:.0f}% of land", fontsize=11, color=FG, loc="left", fontproperties=SERP)
fig.text(0.01, 0.975, "Climb higher, see more sea", fontproperties=DISP, fontsize=19, color=FG, va="top")
fig.legend(handles=[Patch(facecolor=YES, label="sea in view within 50 km"), Patch(facecolor=NOVIEW, label="no sea in view")], loc="upper right",
           frameon=False, fontsize=10, ncol=2, bbox_to_anchor=(0.99, 0.985))
savefig(fig, "eyes", blog="eyes", img="eyes")

# 3. profile by distance from the coast and height band
P = pd.read_csv(f"{DATA}/profile.csv")
fig, ax = plt.subplots(figsize=(8.4, 5.0), facecolor=PAPER)
ax.set_facecolor(PAPER); style_axes(ax)
for b, g in P.groupby("band", sort=False):
    ax.plot(g.km, g.pc, color=BANDCOL[b], lw=2.2, label=f"ground {b} m" if b != "300+" else "ground over 300 m")
    rch = R["reach"][b]
    if rch["km"] == rch["km"] and rch["km"] < 60:
        ax.plot([rch["km"]], [50], "o", color=BANDCOL[b], ms=7, mec="white", zorder=5)
ax.axhline(50, color=MUT, lw=0.8, ls=(0, (3, 3)))
ax.set_xlim(0, 60); ax.set_ylim(0, 100)
ax.set_xlabel("Distance from the coast (km)"); ax.set_ylabel("Squares that see the sea (%)")
lg = ax.legend(frameon=False, fontsize=9.5, loc="upper right")
ax.set_title("How far inland the sea stays in view", loc="left", fontproperties=DISP, fontsize=15, color=FG)
fig.tight_layout()
savefig(fig, "profile", blog="profile", img="profile")

# 4. viewpoint fans
dem = np.load(f"{SCR}/dem.npy").astype(np.float32)
sea = np.load(f"{SCR}/sea.npy")
Vd = pd.read_csv(f"{DATA}/validation.csv").set_index("name")
from matplotlib.colors import LightSource
FANS = [("Pendle Hill", "published"), ("Leith Hill (tower top)", "published"), ("Worcestershire Beacon", "published")]
fig, axs = plt.subplots(1, 3, figsize=(12.5, 4.9), facecolor=PAPER)
fig.subplots_adjust(left=0.01, right=0.99, top=0.83, bottom=0.03, wspace=0.05)
pix = C_MERC / (256 * 2 ** Z)
for a, (nm, tag) in zip(axs, FANS):
    r = Vd.loc[nm]
    X, Y = ll2px(r.lon, r.lat)
    u, v = X - X0 * 256 - 0.5, Y - Y0 * 256 - 0.5
    eye = (r.published_m - r.terrain_m) + EYE + r.tower_m
    rays = np.full((1, 720), np.inf, np.float32)
    viewshed(dem, sea, np.array([u]), np.array([v]), Y0 * 256 + 0.5, 256 * 2 ** Z, pix, float(eye), DMAX, 720, K_REFR, 0.5, 0.0, rays)
    mpp = pix * math.cos(math.radians(r.lat))
    half = int(62000 / mpp)
    i0, j0 = int(v) - half, int(u) - half
    sub = dem[i0:i0 + 2 * half, j0:j0 + 2 * half]; ssub = sea[i0:i0 + 2 * half, j0:j0 + 2 * half]
    ls = LightSource(azdeg=315, altdeg=40)
    hs = ls.hillshade(sub, vert_exag=6, dx=mpp, dy=mpp)
    rgb = np.dstack([0.93 - 0.18 * (1 - hs)] * 3) * np.array([1.0, 0.97, 0.9])
    rgb[ssub] = np.array([0.82, 0.88, 0.92])
    a.imshow(np.clip(rgb, 0, 1), extent=(-half * mpp / 1000, half * mpp / 1000, -half * mpp / 1000, half * mpp / 1000), origin="upper")
    th = np.radians(np.arange(720) * 0.5)
    for k in np.where(np.isfinite(rays[0]))[0]:
        dkm = rays[0, k] / 1000
        a.plot([0, dkm * np.sin(th[k])], [0, dkm * np.cos(th[k])], color=HOT, lw=0.5, alpha=0.55)
        a.plot([dkm * np.sin(th[k])], [dkm * np.cos(th[k])], "o", color=HOT, ms=1.6)
    circ = plt.Circle((0, 0), 50, fill=False, ls=(0, (3, 3)), color=MUT, lw=0.8)
    a.add_patch(circ)
    a.plot([0], [0], "^", color=FG, ms=8, mec="white")
    a.set_xlim(-60, 60); a.set_ylim(-60, 60); a.set_aspect("equal"); a.set_xticks([]); a.set_yticks([])
    for s in a.spines.values():
        s.set_edgecolor(RULE)
    nsea = int(np.isfinite(rays[0]).sum())
    res = (f"sea on {nsea} of 720 sight lines, nearest {np.nanmin(np.where(np.isfinite(rays[0]), rays[0], np.nan)) / 1000:.0f} km" if nsea else "no sea within 50 km")
    a.set_title(f"{nm.replace(' (tower top)', ', tower top')}, {int(r.published_m)} m\n{res}", loc="left", fontsize=10.5, color=FG, fontproperties=SERP)
fig.text(0.01, 0.975, "Where the sea shows: sight lines from three viewpoints", fontproperties=DISP, fontsize=17, color=FG, va="top")
fig.text(0.99, 0.975, "red: first visible sea on each half-degree ray; dashed: 50 km", fontsize=9, color=MUT, va="top", ha="right")
savefig(fig, "fans", blog="fans", img="fans")

# 5. distance to the nearest sea-view square, England's interior, with the farthest point
F = R["farthest_seaview"][0]
fig = plt.figure(figsize=(8.4, 7.2), facecolor=PAPER)
ax = fig.add_axes([0.02, 0.02, 0.96, 0.86])
ext = (F["E"] - 150000, F["E"] + 150000, F["N"] - 130000, F["N"] + 130000)
base(ax, ext, ctx=False)
kd = to_raster(idx, Q.km_to_seaview.values)
from matplotlib.colors import ListedColormap
ylo = ListedColormap(["#2D6FAE", "#F1E7CF", "#E6D3A6", "#D8B676", "#C8934A", "#A9682C", "#7E4520"])
kb = np.digitize(np.nan_to_num(kd, nan=-1), [0.5, 10, 20, 30, 40, 50, 60]).astype(float)
kb[np.isnan(kd)] = np.nan
kb2 = np.where(kd == 0, 0, kb)
ax.imshow(np.ma.masked_invalid(kb2), extent=EXTENT, origin="upper", cmap=ylo, vmin=-0.5, vmax=6.5, interpolation="nearest", zorder=2)
ax.plot([F["E"]], [F["N"]], marker="*", ms=16, color=HOT, mec="white", zorder=6)
ax.annotate(f"{F['km']:.0f} km from any\nsquare with a sea view", (F["E"], F["N"]), xytext=(F["E"] + 32000, F["N"] - 52000), fontsize=10, color=FG,
            arrowprops=dict(arrowstyle="-", color=FG, lw=0.8), bbox=dict(boxstyle="round,pad=0.3", fc=PAPER, ec=RULE), zorder=7)
CITIES = {"Birmingham": (-1.8904, 52.4862), "Nottingham": (-1.1581, 52.9548), "Leicester": (-1.1398, 52.6369), "Derby": (-1.4746, 52.9225),
          "Stoke-on-Trent": (-2.1794, 53.0027), "Coventry": (-1.5197, 52.4068), "Oxford": (-1.2577, 51.752), "Sheffield": (-1.4701, 53.3811),
          "Northampton": (-0.8901, 52.2405), "Peterborough": (-0.2402, 52.5695)}
for nm, (lo, la) in CITIES.items():
    x, y = TB.transform(lo, la)
    if ext[0] < x < ext[1] and ext[2] < y < ext[3]:
        ax.plot([x], [y], "o", ms=4, color=FG, zorder=6)
        ax.text(x + 3000, y + 3000, nm, fontsize=8.5, color=FG, zorder=6, bbox=dict(boxstyle="round,pad=0.12", fc=(1, 1, 1, 0.65), ec="none"))
h = [Patch(facecolor="#2D6FAE", label="sea in view")] + [Patch(facecolor=c, label=l) for c, l in zip(ylo.colors[1:], ["under 10 km", "10 to 20 km", "20 to 30 km", "30 to 40 km", "40 to 50 km", "50 km or more"])]
lg = ax.legend(handles=h, loc="lower left", fontsize=8.5, title="Distance to the nearest\nsquare with a sea view", title_fontsize=9, frameon=True)
lg.get_frame().set_facecolor(PAPER); lg.get_frame().set_edgecolor(RULE)
fig.text(0.02, 0.975, "Britain's sea-view desert", fontproperties=DISP, fontsize=19, color=FG, va="top")
fig.text(0.02, 0.925, f"The farthest square from any sea view is near {F['near']['name']}, {F['county']}", fontproperties=SERP, fontsize=11, color=MUT, va="top")
savefig(fig, "farthest", blog="farthest", img="farthest")

# 6. nations by eye height (land) and people
fig, axs = plt.subplots(1, 2, figsize=(11, 4.6), facecolor=PAPER, gridspec_kw={"width_ratios": [1.6, 1]})
ax = axs[0]; ax.set_facecolor(PAPER); style_axes(ax)
nats = NATIONS
ecol = ["#A6CBE6", "#6FA9D6", "#2D6FAE", "#08306B"]
w = 0.2
for k, e in enumerate(["1.7", "5", "15", "50"]):
    vals = [R["eyes"][e][n]["pc"] for n in nats]
    ax.bar(np.arange(4) + (k - 1.5) * w, vals, w, color=ecol[k], label=f"eyes at {e} m")
    for x, v in zip(np.arange(4) + (k - 1.5) * w, vals):
        ax.text(x, v + 1, f"{v:.0f}", ha="center", fontsize=7.5, color=FG)
ax.set_xticks(np.arange(4)); ax.set_xticklabels(nats)
ax.set_ylabel("Land that sees the sea (%)"); ax.set_ylim(0, 100)
ax.legend(frameon=False, fontsize=9, ncol=2, loc="upper left")
ax.set_title("Land, by nation", loc="left", fontproperties=DISPB, fontsize=13, color=FG)
ax = axs[1]; ax.set_facecolor(PAPER); style_axes(ax)
pv = [R["pop"][e]["gb_pc"] for e in ["1.7", "5", "15", "50"]]
lv = [R["eyes"][e]["gb_pc"] for e in ["1.7", "5", "15", "50"]]
x = np.arange(4)
ax.bar(x - 0.18, lv, 0.36, color="#C9BE9A", label="land (GB)")
ax.bar(x + 0.18, pv, 0.36, color=HOT, label="people (GB)")
for i in range(4):
    ax.text(x[i] - 0.18, lv[i] + 1, f"{lv[i]:.0f}", ha="center", fontsize=8, color=FG)
    ax.text(x[i] + 0.18, pv[i] + 1, f"{pv[i]:.0f}", ha="center", fontsize=8, color=FG)
ax.set_xticks(x); ax.set_xticklabels(["1.7 m", "5 m", "15 m", "50 m"]); ax.set_xlabel("Eye height")
ax.set_ylim(0, 100); ax.legend(frameon=False, fontsize=9, loc="upper left")
ax.set_title("Land and people, Great Britain", loc="left", fontproperties=DISPB, fontsize=13, color=FG)
fig.tight_layout()
savefig(fig, "nations", blog="nations", img="nations")

# 7. sensitivity (paper only)
S = R["sens"]
fig, ax = plt.subplots(figsize=(8.4, 4.6), facecolor=PAPER)
ax.set_facecolor(PAPER)
ys = np.arange(len(S))[::-1]
ax.axvline(0, color=FG, lw=0.8)
for y, s in zip(ys, S):
    ax.plot([s["diff"]], [y], "o", color=HOT if abs(s["diff"]) > 3 else "#2D6FAE", ms=7)
    ax.text(s["diff"] + (0.25 if s["diff"] >= 0 else -0.25), y, f"{s['diff']:+.1f}", va="center", ha="left" if s["diff"] >= 0 else "right", fontsize=8.5, color=FG)
ax.set_yticks(ys); ax.set_yticklabels([s["label"] for s in S], fontsize=8.5)
ax.set_xlabel("Change in the share of land with a sea view (percentage points; same squares)")
lim = max(4, max(abs(s["diff"]) for s in S) + 1.5)
ax.set_xlim(-lim, lim)
for s_ in ("top", "right", "left"):
    ax.spines[s_].set_visible(False)
ax.grid(axis="x", color=RULE, lw=0.6); ax.set_axisbelow(True)
fig.tight_layout()
savefig(fig, "sens")

# 8. share of the horizon that is sea
hz = Q.sea_rays.values / NAZ * 100
hb = np.digitize(hz, [0.0001, 10, 25, 50, 75]).astype(float)
rh = to_raster(idx, hb)
hcol = ListedColormap([NOVIEW, "#D2E4F1", "#A6CBE6", "#6FA9D6", "#2D6FAE", "#08306B"])
fig = plt.figure(figsize=(7.2, 10.4), facecolor=PAPER)
ax = fig.add_axes([0.0, 0.0, 1.0, 0.91])
base(ax, (E0 + 10000, E1, 0, 1230000))
ax.imshow(np.ma.masked_invalid(rh), extent=EXTENT, origin="upper", cmap=hcol, vmin=-0.5, vmax=5.5, interpolation="nearest", zorder=2)
h = [Patch(facecolor=c, label=l) for c, l in zip(hcol.colors, ["no sea", "under 10%", "10 to 25%", "25 to 50%", "50 to 75%", "75% or more"])]
lg = ax.legend(handles=h, loc="upper left", fontsize=9, title="Share of the horizon\nthat is sea", title_fontsize=10, bbox_to_anchor=(0.005, 0.995))
lg.get_frame().set_facecolor(PAPER); lg.get_frame().set_edgecolor(RULE)
fig.text(0.04, 0.975, "How much of the view is sea?", fontproperties=DISP, fontsize=22, color=FG, va="top")
fig.text(0.04, 0.938, "Share of 360 sight lines, one per degree, that reach visible sea\nwithin 50 km (eyes 1.7 m)", fontproperties=SERP, fontsize=10.5, color=MUT, va="top")
savefig(fig, "horizon", img="horizon")

# header 1200 x 630
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=PAPER)
ax = fig.add_axes([0.52, 0.0, 0.48, 1.0])
base(ax, (E0 + 60000, E1 - 10000, 0, 1230000))
ax.imshow(rast_cls_m, extent=EXTENT, origin="upper", cmap=cmap, norm=norm, interpolation="nearest", zorder=2)
fig.text(0.05, 0.86, "DATA STUDY · 2026", fontsize=12, color=MUT)
fig.text(0.05, 0.78, "Can you see\nthe sea?", fontproperties=DISP, fontsize=58, color=FG, va="top", linespacing=1.0)
fig.text(0.05, 0.445, f"From {M['uk_pc']:.0f}% of the UK's land, standing\non the bare ground, you can see the sea.", fontproperties=SERP, fontsize=18, color=FG, va="top", linespacing=1.25)
fig.text(0.05, 0.215, "An upper bound: bare terrain, no buildings or trees.", fontsize=9.5, color=MUT)
fig.text(0.05, 0.08, "Dr Tristan Hotham · maps.tristanhotham.com/sea-view", fontsize=11.5, color=MUT)
for i, (c, l) in enumerate(zip(DCOL[::2] + [NOVIEW], ["sea under 2 km", "sea 5 to 10 km", "sea 20 to 35 km", "no sea"])):
    fig.patches.append(plt.Rectangle((0.05 + i * 0.115, 0.145), 0.018, 0.034, transform=fig.transFigure, color=c))
    fig.text(0.072 + i * 0.115, 0.152, l, fontsize=8.5, color=MUT)
fig.savefig(f"{ROOT}/header.png", dpi=100, facecolor=PAPER)
plt.close(fig)
from PIL import Image
assert Image.open(f"{ROOT}/header.png").size == (1200, 630)
print("figures done")
