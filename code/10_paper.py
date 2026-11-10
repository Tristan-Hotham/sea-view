"""Step 10: the paper. Fills code/paper_template.tex (+ paper_body.tex) from data/results.json, adds the tables and compiles with
xelatex. Output: release/paper/Hotham_Sea_View.pdf and .tex beside the f_*.pdf figures. The DOI stays a placeholder
(https://doi.org/10.5281/zenodo.24106076 printed) unless DOI is set: DOI=10.5281/zenodo.N python3 code/10_paper.py"""
import subprocess
import pandas as pd
from common import *

R = jload(f"{DATA}/results.json")
OUT = os.path.join(REL, "paper"); NAME = "Hotham_Sea_View"
tex = lambda s: str(s).replace("\\", "").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("$", "\\$")


def tfmt(v, f):
    if f == "int": return f"{int(round(float(v))):,}"
    for k in ("f0", "f1", "f2", "f3"):
        if f == k: return f"{float(v):.{k[1]}f}".replace("-", "$-$")
    return tex(str(v))


E = ["1.7", "5", "15", "50"]
rows = ""
for nat in NATIONS + ["UK"]:
    cells = []
    for e in E:
        x = R["eyes"][e]
        pcv = x["uk_pc"] if nat == "UK" else x[nat]["pc"]
        cells.append(f"{pcv:.1f}")
    sq = R["n"]["squares"] if nat == "UK" else R["main"][nat]["squares"]
    km2 = R["main"]["uk_km2"] if nat == "UK" else R["main"][nat]["km2"]
    rows += ("\\midrule " if nat == "UK" else "") + f"{'United Kingdom' if nat == 'UK' else nat} & {sq:,} & {km2:,} & " + " & ".join(cells) + "\\\\\n"
TN = ("\\begin{table}[tbp]\\centering\\small\\caption{Land with a sea view by nation and eye height: squares (km$^2$), squares with a sea view at 1.7~m, and the share (\\%) at each eye height. Sight lines to 50~km, $k=0.13$.}\\label{tab:nations}"
      "\\begin{tabular}{lrrrrrr}\\toprule & Squares & Sea view & \\multicolumn{4}{c}{Share with a sea view (\\%), eyes at}\\\\\\cmidrule(lr){4-7} Nation & (km$^2$) & at 1.7~m & 1.7~m & 5~m & 15~m & 50~m\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = ""
for b in ["0 to 50", "50 to 150", "150 to 300", "300+", "all"]:
    x = R["reach"][b]
    lab = {"300+": "Over 300 m", "all": "All squares"}.get(b, b + " m")
    rows += ("\\midrule " if b == "all" else "") + f"{lab} & {x['squares']:,} & {x['pc']:.1f} & {x['km']:.1f} & [{x['lo']:.1f}, {x['hi']:.1f}]\\\\\n"
TR = ("\\begin{table}[tbp]\\centering\\small\\caption{How far inland the sea stays in view: the distance from the coast at which the share of squares with a sea view (1~km bands, smoothed over three bands) falls below a half, by terrain height. 95\\% intervals from a block bootstrap over 50~km grid blocks (1,000 replicates).}\\label{tab:reach}"
      "\\begin{tabular}{lrrrl}\\toprule Terrain height & Squares & Sea view (\\%) & Half-way distance (km) & 95\\% CI\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
V = pd.read_csv(f"{DATA}/validation.csv")
rows = ""
yn = lambda s, d: (f"yes, {d:.1f} km" if s == 1 else "no")
for _, r in V.iterrows():
    rows += f"{tex(r['name'])} & {int(r.published_m)} & {r.terrain_m:.0f} & {yn(r.terrain_50_sea, r.terrain_50_near_km if r.terrain_50_sea else 0)} & {yn(r.published_50_sea, r.published_50_near_km if r.published_50_sea else 0)} & {'yes' if r.published_100_sea else 'no'}\\\\\n"
TV = ("\\begin{table}[tbp]\\centering\\footnotesize\\setlength{\\tabcolsep}{4pt}\\caption{Validation against viewpoints with a documented sea view: published height, terrain height at the point (zoom 9), and whether the model finds visible sea (and the nearest, km) at the terrain height and at the published height (Leith Hill: plus the 19.5~m tower), with sight lines every half degree to 50~km, and at the published height to 100~km. Sources in data/validation.csv.}\\label{tab:valid}"
      "\\begin{tabular}{lrrlll}\\toprule Viewpoint & Published (m) & Terrain (m) & At terrain height & At published height & 100~km\\\\\\midrule\n" + rows +
      f"\\midrule Reproduced & & & {R['validation']['terrain_50']} of {R['validation']['n']} & {R['validation']['published_50']} of {R['validation']['n']} & {R['validation']['published_100']} of {R['validation']['n']}\\\\\\bottomrule\\end{{tabular}}\\end{{table}}")
rows = f"Main specification & {R['n']['squares']:,} & {R['main']['uk_pc']:.1f} & & \\\\\n"
for s in R["sens"]:
    n_ = s.get("n", R["n"]["squares"])
    ag = "" if s.get("agree_pc") is None else f"{s['agree_pc']:.1f}"
    rows += f"{tex(s['label'])} & {n_:,} & {s['pc']:.1f} & {s['diff']:+.1f} & {ag}\\\\\n".replace("+", "$+$").replace("-", "$-$") if False else f"{tex(s['label'])} & {n_:,} & {s['pc']:.1f} & {s['diff']:+.1f} & {ag}\\\\\n"
TS = ("\\begin{table}[tbp]\\centering\\small\\caption{Planned sensitivity checks: share of squares (or quarter-points) with a sea view, the difference from the main specification on the same squares (percentage points) and the share of squares with the same answer. Eye height variants are in Table~\\ref{tab:nations}.}\\label{tab:sens}"
      "\\begin{tabular}{p{7.2cm}rrrr}\\toprule Check & Squares & Sea view (\\%) & Difference & Agree (\\%)\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
m = R["m1"]
lab = {"Intercept": "Intercept", "np.log1p(np.clip(ground_m, 0, None))": "log(1 + height, m)", "relief_m": "Local relief (m)",
       "C(nation)[T.Scotland]": "Scotland", "C(nation)[T.Wales]": "Wales", "C(nation)[T.Northern Ireland]": "Northern Ireland"}
rows = ""
for k, v in m["params"].items():
    nm = lab.get(k, k.replace("cr(np.log(dcoast_km + 0.1), df=4, constraints='center')", "Spline in log distance, term ").replace("[", "").replace("]", ""))
    rows += f"{tex(nm)} & {v:.3f} & ({m['se'][k]:.3f})\\\\\n"
TM = ("\\begin{table}[tbp]\\centering\\small\\caption{Model M1: logistic regression of a square's sea view (1.7~m) on a natural cubic regression spline in log distance to the coast (4 df), log height, local relief and nation (reference England); standard errors clustered by 50~km grid block. "
      f"N = {m['n']:,} squares, {m['clusters']} clusters; deviance pseudo-$R^2$ = {m['pseudo_r2']:.3f}." + "}\\label{tab:m1}"
      "\\begin{tabular}{lrr}\\toprule Term & Coefficient & (SE)\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}").replace("-0.", "$-$0.").replace(" -", " $-$")
C = R["counties"]
rows = "\\multicolumn{3}{l}{\\textit{Highest share}}\\\\\n" + "".join(f"\\quad {tex(c['county'])} ({tex(c['nation'])}) & {c['squares']:,} & {c['pc']:.1f}\\\\\n" for c in C["top"])
rows += "\\multicolumn{3}{l}{\\textit{Lowest share}}\\\\\n" + "".join(f"\\quad {tex(c['county'])} ({tex(c['nation'])}) & {c['squares']:,} & {c['pc']:.1f}\\\\\n" for c in C["bottom"])
TC = ("\\begin{table}[tbp]\\centering\\small\\caption{Counties and council areas (of " + f"{C['n_ge200']}" + " with at least 200 squares) with the highest and lowest share of land with a sea view at 1.7~m. "
      + f"{C['n_none']} of {C['n']} areas have no square with a sea view. All areas are in data/counties\\_sea.csv." + "}\\label{tab:counties}"
      "\\begin{tabular}{lrr}\\toprule Area & Squares & Sea view (\\%)\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = "".join(f"{tex(w['name'])} & {w['squares']:,} & {w['coverage'] * 100:.0f} & {w['z9_pc']:.1f} & {w['z10_pc']:.1f} & {w['diff']:+.1f} & {w['agree_pc']:.1f}\\\\\n" for w in R["z10"]["windows"])
TZ = ("\\begin{table}[tbp]\\centering\\footnotesize\\setlength{\\tabcolsep}{4pt}\\caption{Terrain resolution check (S6): squares within 50~km of each window centre, share with a sea view using zoom-9 and zoom-10 terrain (same sea mask), difference (points) and agreement. Coverage: share of the window's pixels with zoom-10 tiles.}\\label{tab:z10}"
      "\\begin{tabular}{lrrrrrr}\\toprule Window & Squares & Coverage (\\%) & Zoom 9 (\\%) & Zoom 10 (\\%) & Difference & Agree (\\%)\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
z = R["z10"]
Z10S = ("By the planned rule (a difference above 3 points in any window) the headline is therefore resolution-sensitive, and the zoom-10 figures should be read alongside it (Appendix Table~\\ref{tab:z10})."
        if z["sensitive"] else "By the planned rule (a difference above 3 points in any window) the headline is not resolution-sensitive (Appendix Table~\\ref{tab:z10}).")
t = open(os.path.join(ROOT, "code", "paper_template.tex"), encoding="utf-8").read()
t = t.replace("%%BODY%%", open(os.path.join(ROOT, "code", "paper_body.tex"), encoding="utf-8").read())
t = t.replace("{{AI}}", AI).replace("{{Z10_SENTENCE}}", Z10S)
for k, v in (("TABLE_NATIONS", TN), ("TABLE_REACH", TR), ("TABLE_VALID", TV), ("TABLE_SENS", TS), ("TABLE_M1", TM), ("TABLE_COUNTIES", TC), ("TABLE_Z10", TZ)):
    t = t.replace("{{" + k + "}}", v)
t = re.sub(r"\{\{(?!TABLE_|DOI)([^}|]+)(\|(\w+))?\}\}", lambda m_: tfmt(get(R, m_.group(1)), m_.group(3) or "raw"), t)
DOI = os.environ.get("DOI")
t = t.replace("https://doi.org/10.5281/zenodo.24106076", f"\\url{{https://doi.org/{DOI}}}" if DOI else "\\{\\{DOI\\_URL\\}\\}")
assert "{{" not in t and "\u2014" not in t and "\u2013" not in t, re.findall(r"\{\{[^}]*\}\}", t)[:5]
for bad in ("DSIT", "DCMS", "pre-registered", "preregistered"):
    assert bad not in t, bad
cites = set(re.findall(r"\\cite[pt]?\{([^}]+)\}", t)); cites = {c.strip() for x in cites for c in x.split(",")}
items = set(re.findall(r"\\bibitem\[[^\]]*\]\{([^}]+)\}", t))
assert cites <= items, cites - items
print("references", len(items), "uncited", sorted(items - cites))
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
log = open(os.path.join(OUT, NAME + ".log"), encoding="utf-8", errors="ignore").read()
print([l for l in log.splitlines() if "Missing character" in l or "undefined" in l.lower() or "Overfull" in l or l.startswith("!")][:15])
for ext in (".aux", ".log", ".out", ".bbl", ".blg"):
    q = os.path.join(OUT, NAME + ext)
    if os.path.exists(q): os.remove(q)
txt = subprocess.run(["pdftotext", os.path.join(OUT, NAME + ".pdf"), "-"], capture_output=True, text=True).stdout
pages = subprocess.run(["pdfinfo", os.path.join(OUT, NAME + ".pdf")], capture_output=True, text=True).stdout
body = txt.split("\nReferences\n")[0]
ab = txt.split("Abstract")[1].split("Keywords")[0]
print("paper", r.returncode, len(txt.split()), "words total;", len(body.split()), "before references; abstract", len(ab.split()), "words;",
      [l for l in pages.splitlines() if l.startswith("Pages")], "dashes:", txt.count("\u2014") + txt.count("\u2013"))
