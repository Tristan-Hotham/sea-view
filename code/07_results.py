"""Step 7: results.json and the data files.
Reads SCR/grid.npz, view.npz, sett.npz, z10.npz, mc.npz and data/validation.csv; writes data/squares.csv.gz (every square),
data/settlements_sea.csv, data/seats_sea.csv, data/results.json."""
import csv, gzip
import numpy as np
import pandas as pd
import statsmodels.api as sm
from patsy import dmatrix
from shapely.geometry import shape, Point
from shapely.strtree import STRtree
from scipy.ndimage import distance_transform_edt
from common import *

G = np.load(f"{SCR}/grid.npz")
Vw = {}
for v in ("main", "eye5", "eye15", "eye50", "d25", "d100", "k0", "k25", "opensea", "az720", "q500"):
    z = np.load(f"{SCR}/v_{v}.npz")
    for k in z.files:
        Vw[f"{v}_{k}" if k != "ground" else "ground"] = z[k]
counties = list(G["counties"])
cat = lambda k: np.concatenate([G[f"gb_{k}"], G[f"ni_{k}"]])
D = pd.DataFrame({"grid": np.r_[np.full(len(G["gb_E"]), "OSGB"), np.full(len(G["ni_E"]), "IG")],
                  "E": cat("E").astype(int), "N": cat("N").astype(int), "lon": cat("lon"), "lat": cat("lat"),
                  "nation": [NATIONS[i] for i in cat("nation")], "county": [counties[i] for i in cat("county")],
                  "dcoast_km": cat("dcoast") / 1000, "relief_m": cat("relief"), "ground_m": Vw["ground"]})
n = len(D)
R = {"n": {}, "model": {"eye_m": EYE, "dmax_km": DMAX / 1000, "k": K_REFR, "rays": NAZ, "step_m_approx": 88}}
SV = {}
for v in ("main", "eye5", "eye15", "eye50", "d25", "d100", "k0", "k25", "opensea"):
    SV[v] = Vw[f"{v}_nsea"] > 0
    D[f"near_{v}"] = np.where(np.isfinite(Vw[f"{v}_near"]), Vw[f"{v}_near"] / 1000, np.nan)
    D[f"nsea_{v}"] = Vw[f"{v}_nsea"]
D["sea"] = SV["main"]
meta = jload(f"{SCR}/meta.json")
R["n"] = {"squares": n, "gb": int((D.grid == "OSGB").sum()), "ni": int((D.grid == "IG").sum()),
          "oob_rays": int(Vw["main_oob"].sum()), "oob_squares": int((Vw["main_oob"] > 0).sum()),
          "dem_tiles": meta["tiles"], "despiked": meta["despiked"], "ofm_version": meta["ofm_version"]}
pc = lambda m: 100 * float(np.mean(m))


def shares(mask_sv, df=D):
    out = {"uk_pc": pc(mask_sv), "gb_pc": pc(mask_sv[(df.grid == "OSGB").values]), "uk_km2": int(mask_sv.sum())}
    for nat in NATIONS:
        m = (df.nation == nat).values
        out[nat] = {"pc": pc(mask_sv[m]), "km2": int(mask_sv[m].sum()), "squares": int(m.sum())}
    return out


R["main"] = shares(SV["main"])
R["eyes"] = {f"{e:g}": shares(SV[k]) for e, k in zip(EYES, ("main", "eye5", "eye15", "eye50"))}
sea = D[D.sea]
R["near"] = {"median_km": float(sea.near_main.median()), "q25_km": float(sea.near_main.quantile(.25)), "q75_km": float(sea.near_main.quantile(.75)),
             "within_5km_pc": pc(D.near_main.fillna(1e9) <= 5), "beyond_20km_of_seaview_pc": 100 * float((sea.near_main > 20).mean()),
             "max_km": float(sea.near_main.max())}
sh = D.nsea_main / NAZ
R["horizon"] = {"mean_pc_all": 100 * float(sh.mean()), "mean_pc_seaview": 100 * float(sh[D.sea].mean()), "median_pc_seaview": 100 * float(sh[D.sea].median()),
                "over_half_pc": pc(sh > .5), "over_half_km2": int((sh > .5).sum()), "glimpse_lt3_km2": int(((D.nsea_main > 0) & (D.nsea_main < 3)).sum()),
                "under_10pc_of_seaview_pc": 100 * float((sh[D.sea] < .10).mean())}
# by distance from the coast
bins = [0, 1, 2, 5, 10, 20, 30, 50, 200]
D["dbin"] = pd.cut(D.dcoast_km, bins, right=False, labels=[f"{a} to {b}" for a, b in zip(bins[:-1], bins[1:])])
R["by_dist"] = [{"bin": str(b), "squares": int(len(g)), "pc": pc(g.sea)} for b, g in D.groupby("dbin", observed=True)]
# counties
cty = D.groupby(["county", "nation"]).agg(squares=("sea", "size"), sv=("sea", "sum"), dco=("dcoast_km", "max")).reset_index()
cty["pc"] = 100 * cty.sv / cty.squares
big = cty[cty.squares >= 200]
R["counties"] = {"n": int(len(cty)), "n_none": int((cty.sv == 0).sum()), "none": sorted(cty[cty.sv == 0].county.tolist()),
                 "top": big.sort_values("pc", ascending=False).head(8)[["county", "nation", "squares", "pc"]].to_dict("records"),
                 "bottom": big.sort_values("pc").head(8)[["county", "nation", "squares", "pc"]].to_dict("records")}
R["counties"]["n_ge200"] = int(len(big))
cty.to_csv(f"{DATA}/counties_sea.csv", index=False, float_format="%.2f")

# E3: distance inland at which half of squares see the sea, by height band; block bootstrap over 50 km blocks
D["block"] = (D.grid + "_" + (D.E // 50000).astype(str) + "_" + (D.N // 50000).astype(str))
HB = [(0, 50), (50, 150), (150, 300), (300, 5000)]
D["hb"] = np.select([(D.ground_m >= a) & (D.ground_m < b) for a, b in HB], [f"{a} to {b}" if b < 5000 else f"{a}+" for a, b in HB], "neg")
D.loc[D.ground_m < 0, "hb"] = "0 to 50"
edges = np.arange(0, 61, 1.0)


def d50_counts(num, den):
    """distance at which the 3-band smoothed share first falls below a half, from per-bin counts"""
    p = np.where(den > 0, num / np.maximum(den, 1), np.nan)
    ps = pd.Series(p).rolling(3, center=True, min_periods=1).mean().values
    for i in range(1, len(ps)):
        if ps[i - 1] >= .5 > ps[i]:
            x0, x1 = edges[i - 1] + .5, edges[i] + .5
            return float(x0 + (ps[i - 1] - .5) / (ps[i - 1] - ps[i]) * (x1 - x0))
    return float("nan") if ps[0] < .5 else float(edges[-1])


rng = np.random.default_rng(7)
R["reach"] = {}
nb = len(edges) - 1
kbin = np.digitize(D.dcoast_km.values, edges) - 1
okb = (kbin >= 0) & (kbin < nb)
bcode, blocks = pd.factorize(D.block)
seav = D.sea.values.astype(float)
for hb in [f"{a} to {b}" if b < 5000 else f"{a}+" for a, b in HB] + ["all"]:
    m = okb & ((D.hb.values == hb) if hb != "all" else True)
    key = bcode[m] * nb + kbin[m]
    NUM = np.bincount(key, weights=seav[m], minlength=len(blocks) * nb).reshape(len(blocks), nb)
    DEN = np.bincount(key, minlength=len(blocks) * nb).reshape(len(blocks), nb)
    est = d50_counts(NUM.sum(0), DEN.sum(0))
    boots = []
    for r in range(1000):
        w = np.bincount(rng.integers(0, len(blocks), len(blocks)), minlength=len(blocks))
        boots.append(d50_counts(w @ NUM, w @ DEN))
    boots = np.array(boots)
    sub = D if hb == "all" else D[D.hb == hb]
    R["reach"][hb] = {"km": est, "lo": float(np.nanpercentile(boots, 2.5)), "hi": float(np.nanpercentile(boots, 97.5)), "squares": int(len(sub)),
                      "pc": pc(sub.sea), "boot_nan": int(np.isnan(boots).sum())}
    print("reach", hb, R["reach"][hb], flush=True)
prof = []
for hb in ["0 to 50", "50 to 150", "150 to 300", "300+"]:
    sub = D[D.hb == hb]
    k = np.digitize(sub.dcoast_km.values, edges) - 1
    for i in range(len(edges) - 1):
        m = k == i
        if m.sum() >= 30:
            prof.append({"band": hb, "km": float(edges[i] + .5), "n": int(m.sum()), "pc": pc(sub.sea.values[m])})
pd.DataFrame(prof).to_csv(f"{DATA}/profile.csv", index=False, float_format="%.2f")

# M1: logistic model, clustered by 50 km blocks
X = dmatrix("cr(np.log(dcoast_km + 0.1), df=4, constraints='center') + np.log1p(np.clip(ground_m, 0, None)) + relief_m + C(nation)", D, return_type="dataframe")
y = D.sea.astype(float).values
grp = pd.factorize(D.block)[0]
m1 = sm.GLM(y, X, family=sm.families.Binomial()).fit(cov_type="cluster", cov_kwds={"groups": grp})
p0 = m1.predict(X)


def ame(col, delta):
    X2 = X.copy()
    if col == "h":
        D2 = D.copy(); D2["ground_m"] = np.clip(D.ground_m, 0, None) + delta
        X2 = dmatrix(X.design_info, D2, return_type="dataframe")
    elif col == "r":
        X2["relief_m"] = X2["relief_m"] + delta
    # delta method by simulation from the clustered covariance
    sims = rng.multivariate_normal(m1.params.values, m1.cov_params().values, 300)
    eff = [np.mean(1 / (1 + np.exp(-(X2.values @ b))) - 1 / (1 + np.exp(-(X.values @ b)))) for b in sims]
    pt = float(np.mean(m1.predict(X2) - p0))
    return {"pp": 100 * pt, "lo": 100 * float(np.percentile(eff, 2.5)), "hi": 100 * float(np.percentile(eff, 97.5))}


R["m1"] = {"n": int(m1.nobs), "clusters": int(len(np.unique(grp))), "ame_height_100m": ame("h", 100.0), "ame_relief_50m": ame("r", 50.0),
           "pseudo_r2": float(1 - m1.deviance / m1.null_deviance), "params": {k: float(v) for k, v in m1.params.items()},
           "se": {k: float(v) for k, v in m1.bse.items()}}
# effect of distance: predicted share at 2, 5, 10, 20 km holding everything else as observed
for km in (2, 5, 10, 20):
    D2 = D.copy(); D2["dcoast_km"] = float(km)
    X2 = dmatrix(X.design_info, D2, return_type="dataframe")
    sims = rng.multivariate_normal(m1.params.values, m1.cov_params().values, 300)
    vals = [float(np.mean(1 / (1 + np.exp(-(X2.values @ b))))) for b in sims]
    R["m1"][f"pred_{km}km"] = {"pc": 100 * float(np.mean(m1.predict(X2))), "lo": 100 * float(np.percentile(vals, 2.5)), "hi": 100 * float(np.percentile(vals, 97.5))}
for nat in NATIONS[1:]:
    key = f"C(nation)[T.{nat}]"
    if key in m1.params:
        R["m1"][f"nation_{nat}"] = {"b": float(m1.params[key]), "lo": float(m1.conf_int().loc[key, 0]), "hi": float(m1.conf_int().loc[key, 1])}
print("m1", R["m1"]["ame_height_100m"], R["m1"]["ame_relief_50m"], flush=True)

# sensitivity
sens = []
base = SV["main"]
for key, lab in (("d25", "Maximum distance 25 km"), ("d100", "Maximum distance 100 km"), ("k0", "No refraction (k = 0)"),
                 ("k25", "Strong refraction (k = 0.25)"), ("opensea", "Open sea only (channels under about 1 km removed)")):
    sens.append({"key": key, "label": lab, "pc": pc(SV[key]), "diff": pc(SV[key]) - pc(base), "agree_pc": pc(SV[key] == base)})
gl = Vw["main_nsea"] >= 3
sens.append({"key": "glimpse3", "label": "Sea on at least 3 of 360 rays", "pc": pc(gl), "diff": pc(gl) - pc(base), "agree_pc": pc(gl == base)})
i4 = Vw["az720_idx"]
s4a, s4b = base[i4], Vw["az720_nsea"] > 0
sens.append({"key": "az720", "label": "720 rays (5% sample)", "pc": pc(s4b), "diff": pc(s4b) - pc(s4a), "agree_pc": pc(s4a == s4b), "base_pc": pc(s4a), "n": int(len(i4))})
qn = Vw["q500_nsea"]                     # -1 = quarter point at sea
qsv = (qn > 0) | (qn == -1)
qland = qn >= 0
q_share = float(((qn > 0).sum()) / max(qland.sum(), 1))
qb = base[Vw["q500_idx"]]
sens.append({"key": "q500", "label": "500 m grid (four points per square, 25% sample)", "pc": 100 * q_share, "diff": 100 * q_share - pc(qb), "base_pc": pc(qb), "n": int(len(qb)),
             "agree_pc": None, "any_pc": pc((qn > 0).any(axis=1)), "all_pc": pc(((qn > 0) | (qn == -1)).all(axis=1) & (qn > 0).any(axis=1)),
             "mixed_pc": pc((qn > 0).any(axis=1) & ((qn == 0).any(axis=1)))})
z = np.load(f"{SCR}/z10.npz")
zm = jload(f"{SCR}/z10_meta.json")
z10 = {"windows": []}
for wi, name in enumerate(z["names"]):
    m = z["win"] == wi
    a = base[z["idx"][m]]; b = z["nsea"][m] > 0
    z10["windows"].append({"name": str(name), "squares": int(m.sum()), "z9_pc": pc(a), "z10_pc": pc(b), "diff": pc(b) - pc(a), "agree_pc": pc(a == b),
                           "coverage": zm[str(name)]["z10_coverage"]})
a = base[z["idx"]]; b = z["nsea"] > 0
z10.update({"squares": int(len(a)), "z9_pc": pc(a), "z10_pc": pc(b), "diff": pc(b) - pc(a), "agree_pc": pc(a == b),
            "max_abs_diff": max(abs(w["diff"]) for w in z10["windows"])})
z10["sensitive"] = bool(z10["max_abs_diff"] > 3)
z10["rel"] = z10["z10_pc"] / z10["z9_pc"]
z10["adj_uk_pc"] = pc(base) * z10["rel"]          # exploratory: the windows' relative change applied to the UK share
z10["rel_drop_pc"] = 100 * (1 - z10["rel"])
R["z10"] = z10
sens.append({"key": "z10", "label": "Terrain at about 88 m (zoom 10), four windows", "pc": z10["z10_pc"], "diff": z10["diff"], "agree_pc": z10["agree_pc"],
             "base_pc": z10["z9_pc"], "n": z10["squares"]})
mc = np.load(f"{SCR}/mc.npz")
R["mc"] = {"n": int(len(mc["idx"])), "base_pc": pc(base[mc["idx"]])}
for sd in ("sd5", "sd10"):
    sh_r = (mc[sd] > 0).mean(axis=1) * 100
    p = (mc[sd] > 0).mean(axis=0)
    R["mc"][sd] = {"mean_pc": float(sh_r.mean()), "lo": float(np.percentile(sh_r, 2.5)), "hi": float(np.percentile(sh_r, 97.5)),
                   "expected_pc": 100 * float(p.mean()), "uncertain_pc": 100 * float(((p > 0) & (p < 1)).mean()),
                   "flip_vs_main_pc": 100 * float(np.mean(np.abs(p - base[mc["idx"]]) >= .5))}
    sens.append({"key": f"mc_{sd}", "label": f"Terrain error, sd {sd[2:]} m (2,000 squares, 20 draws)", "pc": R["mc"][sd]["mean_pc"],
                 "diff": R["mc"][sd]["mean_pc"] - R["mc"]["base_pc"], "agree_pc": None, "base_pc": R["mc"]["base_pc"], "n": R["mc"]["n"]})
R["sens"] = sens
diffs = [s["diff"] for s in sens]
R["sens_range"] = {"lo_pc": pc(base) + min(diffs), "hi_pc": pc(base) + max(diffs), "min_diff": min(diffs), "max_diff": max(diffs)}
print("sens", [(s["key"], round(s["pc"], 2), round(s["diff"], 2)) for s in sens], flush=True)

# farthest squares: from any sea-view square (each grid on its own) and from the coast
S = pd.read_csv(SETT)
far = {}
for gname in ("OSGB", "IG"):
    g = D[D.grid == gname]
    e0, n0 = g.E.min(), g.N.min()
    W, H = int((g.E.max() - e0) / 1000) + 1, int((g.N.max() - n0) / 1000) + 1
    sv = np.zeros((H, W), bool); land = np.zeros((H, W), bool)
    ii = ((g.N - n0) / 1000).astype(int).values; jj = ((g.E - e0) / 1000).astype(int).values
    land[ii, jj] = True; sv[ii, jj] = g.sea.values
    dist = distance_transform_edt(~sv)
    dd = dist[ii, jj]
    far[gname] = dd
D["km_to_seaview"] = np.nan
D.loc[D.grid == "OSGB", "km_to_seaview"] = far["OSGB"]
D.loc[D.grid == "IG", "km_to_seaview"] = far["IG"]


def nearest_place(lon, lat, minpop=0):
    s = S[S["pop"].fillna(0) >= minpop]
    d = gc_km(lat, lon, s.lat.values, s.lon.values)
    j = int(np.argmin(d))
    return {"name": s.name.values[j], "county": s.county.values[j], "km": float(d[j])}


top = D.sort_values("km_to_seaview", ascending=False)
fs = []
seen = []
for _, r in top.iterrows():
    if any(gc_km(r.lat, r.lon, a, b) < 15 for a, b in seen):
        continue
    seen.append((r.lat, r.lon))
    fs.append({"lon": float(r.lon), "lat": float(r.lat), "E": int(r.E), "N": int(r.N), "grid": r.grid, "km": float(r.km_to_seaview), "county": r.county,
               "nation": r.nation, "ground_m": float(r.ground_m), "dcoast_km": float(r.dcoast_km), "near": nearest_place(r.lon, r.lat)})
    if len(fs) == 5:
        break
R["farthest_seaview"] = fs
tc = D.sort_values("dcoast_km", ascending=False).iloc[0]
R["farthest_coast"] = {"lon": float(tc.lon), "lat": float(tc.lat), "E": int(tc.E), "N": int(tc.N), "km": float(tc.dcoast_km), "county": tc.county,
                       "near": nearest_place(tc.lon, tc.lat)}
R["seaview_far_inland"] = {}
sv_in = D[D.sea].sort_values("dcoast_km", ascending=False)
R["seaview_far_inland"]["top"] = [{"lon": float(r.lon), "lat": float(r.lat), "km_coast": float(r.dcoast_km), "near_km": float(r.near_main), "ground_m": float(r.ground_m),
                                   "county": r.county, "near": nearest_place(r.lon, r.lat)} for _, r in sv_in.head(3).iterrows()]
R["seaview_far_inland"]["n_300_40km"] = int(((D.dcoast_km >= 40) & (D.ground_m > 300) & D.sea).sum())
R["seaview_far_inland"]["n_40km"] = int(((D.dcoast_km >= 40) & D.sea).sum())
# Ordnance Survey's published farthest point from the sea (mean low water): Church Flatts Farm near Coton in the Elms, SK 253 144,
# about 70 miles (113 km) from Fosdyke Wash, Neston and Westbury-on-Severn (BBC News, 23 July 2003). Compare at its square.
_os = D[(D.E == 425500) & (D.N == 314500)].iloc[0]
R["os_compare"] = {"E": 425500, "N": 314500, "published_km": 113.0, "dcoast_km": float(_os.dcoast_km), "km_to_seaview": float(_os.km_to_seaview),
                   "farthest_coast_to_os_km": float(np.hypot(R["farthest_coast"]["E"] - 425500, R["farthest_coast"]["N"] - 314500) / 1000)}
R["no_seaview_by_coast"] = {"within_1km_pc": pc(~D.sea[D.dcoast_km < 1]), "within_2km_pc": pc(~D.sea[D.dcoast_km < 2]),
                            "within_5km_pc": pc(~D.sea[D.dcoast_km < 5])}

# settlements and population
St = np.load(f"{SCR}/v_sett.npz", allow_pickle=True)
assert (St["qid"] == S.qid.values).all()
for eye in EYES:
    S[f"near_{eye:g}"] = np.where(np.isfinite(St[f"near_{eye:g}"]), St[f"near_{eye:g}"] / 1000, np.nan)
    S[f"nsea_{eye:g}"] = St[f"nsea_{eye:g}"]
    S[f"sea_{eye:g}"] = St[f"nsea_{eye:g}"] > 0
S["ground_sea_m"] = St["ground"]
S["at_sea_pixel"] = St["atsea"]
seats = jload(SEATGEO)["features"]
sg = [shape(f["geometry"]) for f in seats]
tree = STRtree(sg)
codes = [f["properties"]["code"] for f in seats]


import shapely


def seats_of(lon, lat):
    """2010 seat code for each point: containing polygon, else nearest within about 3 km (points on the shore)"""
    pts = shapely.points(np.asarray(lon), np.asarray(lat))
    out = np.full(len(pts), "", object)
    pi, gi = tree.query(pts, predicate="intersects")
    out[pi] = np.array(codes, object)[gi]
    miss = np.where(out == "")[0]
    if len(miss):
        (mi, mg), dist = tree.query_nearest(pts[miss], return_distance=True, all_matches=False)
        ok = dist * 111 < 3
        out[miss[mi[ok]]] = np.array(codes, object)[mg[ok]]
    return out


S["seat"] = np.where(S.nation.values != "Northern Ireland", seats_of(S.lon.values, S.lat.values), "")
gbm = (D.grid == "OSGB").values
D["seat"] = ""
D.loc[gbm, "seat"] = seats_of(D.lon.values[gbm], D.lat.values[gbm])
C = pd.read_csv(SEATCSV)[["code", "name", "country", "pop2011"]]
pop = {}
seat_rows = []
for eye in EYES:
    tot = 0.0; svp = 0.0; fallback = 0; agg_dropped = 0
    for _, c in C.iterrows():
        s = S[(S.seat == c.code) & S["pop"].notna()]
        agg = s["pop"] > c.pop2011
        agg_dropped += int(agg.sum())
        s = s[~agg]
        if s["pop"].sum() > 0:
            share = float((s["pop"] * s[f"sea_{eye:g}"]).sum() / s["pop"].sum())
        else:
            fallback += 1
            k = {1.7: "main", 5.0: "eye5", 15.0: "eye15", 50.0: "eye50"}[eye]
            share = float(SV[k][(D.seat == c.code).values].mean()) if (D.seat == c.code).any() else 0.0
        tot += c.pop2011; svp += share * c.pop2011
        if eye == EYE:
            seat_rows.append({"code": c.code, "name": c["name"], "country": c.country, "pop2011": int(c.pop2011), "settlements_used": int(len(s)),
                              "share_pc": 100 * share, "squares": int((D.seat == c.code).sum()), "squares_sea_pc": pc(SV["main"][(D.seat == c.code).values]) if (D.seat == c.code).any() else None})
    ni = S[(S.nation == "Northern Ireland") & S["pop"].notna()]
    wd = S[S["pop"].notna() & (S.nation != "Northern Ireland") & (S.seat != "")]
    wd = wd[wd["pop"] <= wd.seat.map(dict(zip(C.code, C.pop2011)))]
    allp = S[S["pop"].notna()]
    pop[f"{eye:g}"] = {"gb_pc": 100 * svp / tot, "gb_people_m": svp / 1e6, "gb_total_m": tot / 1e6, "fallback_seats": fallback, "aggregates_dropped": agg_dropped,
                       "ni_pc": 100 * float((ni["pop"] * ni[f"sea_{eye:g}"]).sum() / ni["pop"].sum()), "ni_settlements": int(len(ni)),
                       "gb_wikidata_pc": 100 * float((wd["pop"] * wd[f"sea_{eye:g}"]).sum() / wd["pop"].sum()),
                       "settlements_pc": pc(S[f"sea_{eye:g}"]), "settlements_withpop_pc": pc(allp[f"sea_{eye:g}"])}
R["pop"] = pop
R["n"]["settlements"] = int(len(S)); R["n"]["settlements_pop"] = int(S["pop"].notna().sum()); R["n"]["seats"] = int(len(C))
print("pop", pop, flush=True)
pd.DataFrame(seat_rows).to_csv(f"{DATA}/seats_sea.csv", index=False, float_format="%.2f")
# towns: the largest settlements with and without a sea view
T = S[S["pop"].fillna(0) >= 20000].copy()
T = T[~T.type.str.contains("Urban Area|Built-up|urban area|built-up|county|region", na=False)]
R["towns"] = {"n_20k": int(len(T)), "sea_pc": pc(T["sea_1.7"]),
              "coast_nosea": [], "inland_sea": []}
dco = []
from scipy.ndimage import map_coordinates
dem_sea = np.load(f"{SCR}/sea.npy")
X, Y = ll2px(T.lon.values, T.lat.values)
from scipy.spatial import cKDTree
_kd = cKDTree(np.c_[D.lon.values * np.cos(np.radians(D.lat.values)), D.lat.values])
T["dcoast_km"] = D.dcoast_km.values[_kd.query(np.c_[T.lon.values * np.cos(np.radians(T.lat.values)), T.lat.values])[1]]
for _, r in T[(T.dcoast_km < 3) & (~T["sea_1.7"])].sort_values("pop", ascending=False).head(12).iterrows():
    R["towns"]["coast_nosea"].append({"name": r["name"], "county": r.county, "pop": int(r["pop"]), "dcoast_km": r.dcoast_km, "sea5": bool(r["sea_5"]), "sea15": bool(r["sea_15"])})
for _, r in T[(T["sea_1.7"])].sort_values("dcoast_km", ascending=False).head(12).iterrows():
    R["towns"]["inland_sea"].append({"name": r["name"], "county": r.county, "pop": int(r["pop"]), "dcoast_km": r.dcoast_km, "near_km": float(r["near_1.7"])})

# validation
Vd = pd.read_csv(f"{DATA}/validation.csv")
R["validation"] = {"n": int(len(Vd)), "terrain_50": int(Vd.terrain_50_sea.sum()), "published_50": int(Vd.published_50_sea.sum()),
                   "terrain_100": int(Vd.terrain_100_sea.sum()), "published_100": int(Vd.published_100_sea.sum()),
                   "rule_met": bool(Vd.terrain_50_sea.mean() >= .8),
                   "misses_terrain": Vd[Vd.terrain_50_sea == 0].name.tolist(), "misses_published": Vd[Vd.published_50_sea == 0].name.tolist(),
                   "points": Vd[["name", "published_m", "terrain_m", "terrain_50_sea", "terrain_50_near_km", "published_50_sea", "published_50_near_km"]].to_dict("records")}

# files
keep = ["grid", "E", "N", "lon", "lat", "nation", "county", "ground_m", "dcoast_km", "relief_m", "seat",
        "near_main", "nsea_main", "near_eye5", "nsea_eye5", "near_eye15", "nsea_eye15", "near_eye50", "nsea_eye50", "km_to_seaview"]
out = D[keep].rename(columns={"near_main": "near_sea_km", "nsea_main": "sea_rays", "near_eye5": "near_sea_km_eye5", "nsea_eye5": "sea_rays_eye5",
                              "near_eye15": "near_sea_km_eye15", "nsea_eye15": "sea_rays_eye15", "near_eye50": "near_sea_km_eye50", "nsea_eye50": "sea_rays_eye50"})
out.to_csv(f"{DATA}/squares.csv.gz", index=False, float_format="%.3f", compression={"method": "gzip", "mtime": 0})
sk = ["qid", "name", "type", "nation", "county", "lon", "lat", "pop", "seat", "ground_sea_m", "at_sea_pixel"] + [f"{p}_{e:g}" for e in EYES for p in ("near", "nsea")]
S[sk].to_csv(f"{DATA}/settlements_sea.csv", index=False, float_format="%.3f")
D[["grid", "E", "N", "sea", "near_main", "nsea_main", "dcoast_km", "ground_m", "km_to_seaview"]].to_pickle(f"{SCR}/D.pkl")
S[sk].to_pickle(f"{SCR}/S.pkl")
jsave(R, f"{DATA}/results.json", indent=1)
print("main", R["main"]["uk_pc"], R["main"]["gb_pc"], "farthest", R["farthest_seaview"][0], R["farthest_coast"])
