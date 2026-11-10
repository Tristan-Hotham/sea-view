"""Step 12: README.md, reddit/post.md and release/paper/cover_note.md from data/results.json.
https://doi.org/10.5281/zenodo.24106076 and https://blog.tristanhotham.com/2026/10/31/sea-view/ are left for the publisher to fill."""
from common import *

R = jload(f"{DATA}/results.json")
M, E, P, F, FC, V, Z = R["main"], R["eyes"], R["pop"], R["farthest_seaview"][0], R["farthest_coast"], R["validation"], R["z10"]
rc = lambda b: f"{R['reach'][b]['km']:.1f} km (95% CI {R['reach'][b]['lo']:.1f} to {R['reach'][b]['hi']:.1f})"
readme = f"""# Can you see the sea?

A line-of-sight census of sea views from every 1 km square of the United Kingdom ({R['n']['squares']:,} squares: Ordnance Survey National Grid squares in Great Britain, Irish Grid squares in Northern Ireland). From the centre of each square, 360 sight lines over the open AWS Terrain Tiles (zoom 9, about 175 m) out to 50 km, with Earth curvature and standard refraction (k = 0.13), against OpenStreetMap's sea; four eye heights; settlements weighted by census population; validation against documented viewpoints and sensitivity checks, all pre-specified in a written plan before any result was computed (NOTES.md). A data study by Dr Tristan Hotham (Independent researcher).

Interactive page: {PAGE}
Paper: {{https://doi.org/10.5281/zenodo.24106076}}
Blog post: {{https://blog.tristanhotham.com/2026/10/31/sea-view/}}
Code and data: {REPO}

## Headline results

- Standing on the bare ground (eyes 1.7 m), the sea is in view within 50 km from {M['uk_km2']:,} squares, {M['uk_pc']:.1f}% of UK land: Scotland {M['Scotland']['pc']:.1f}%, Wales {M['Wales']['pc']:.1f}%, Northern Ireland {M['Northern Ireland']['pc']:.1f}%, England {M['England']['pc']:.1f}%.
- Eye height: {E['5']['uk_pc']:.1f}% at 5 m (an upstairs window), {E['15']['uk_pc']:.1f}% at 15 m, {E['50']['uk_pc']:.1f}% at 50 m.
- Where the sea is in view, the nearest visible sea is a median {R['near']['median_km']:.1f} km away; the median square with a view sees sea across {R['horizon']['median_pc_seaview']:.1f}% of the horizon; {R['horizon']['over_half_km2']:,} squares see sea across more than half of it.
- Half of squares lose sight of the sea at {rc('0 to 50')} from the coast on ground below 50 m, {rc('50 to 150')} at 50 to 150 m, {rc('150 to 300')} at 150 to 300 m and {rc('300+')} above 300 m.
- People: {P['1.7']['gb_pc']:.1f}% of Great Britain's 2011 population live at settlement points with a sea view (constituency populations split by Wikidata settlement populations); {P['5']['gb_pc']:.1f}% from 5 m. Northern Ireland: {P['1.7']['ni_pc']:.1f}% of the Wikidata settlement population.
- Farthest square from any sea view: {F['km']:.1f} km, near {F['near']['name']} ({F['county']}). Farthest from the coast: {FC['km']:.1f} km, near {FC['near']['name']} ({FC['county']}).
- Validation: {V['terrain_50']} of {V['n']} documented sea views reproduced at the terrain height, {V['published_50']} at published summit heights (misses: {', '.join(V['misses_published']) or 'none'}).
- Sensitivity (planned checks): the share ranges from {R['sens_range']['lo_pc']:.1f}% to {R['sens_range']['hi_pc']:.1f}%; terrain error (5 m) gives {R['mc']['sd5']['mean_pc']:.1f}% (95% interval {R['mc']['sd5']['lo']:.1f} to {R['mc']['sd5']['hi']:.1f}) against {R['mc']['base_pc']:.1f}% on the same 2,000 squares; zoom-10 terrain {Z['z10_pc']:.1f}% against {Z['z9_pc']:.1f}% in four test windows (lower in every window; by the planned rule the headline is resolution-sensitive).
- All figures are upper bounds: bare terrain, with no buildings, trees or hedges, which would lower every figure.
- The headline is resolution-sensitive: finer terrain (about 88 m) lowers the share in all four test windows, by up to {Z['max_abs_diff']:.1f} points.
- "Sea" is OpenStreetMap's coastline and includes tidal estuaries and sea lochs. Population figures cover Great Britain only (Northern Ireland separately); land figures cover the UK.
- Farthest from the coast compared with the Ordnance Survey's published point (Church Flatts Farm, near Coton in the Elms, about {R['os_compare']['published_km']:.0f} km from the sea at mean low water): the square found here is {R['os_compare']['farthest_coast_to_os_km']:.0f} km from it, because OpenStreetMap's coast runs up tidal estuaries.

## Files

| File | What it is |
|---|---|
| `index.html`, `js/page.js` | Interactive page: MapLibre on OpenFreeMap Positron; every square coloured by the nearest visible sea or the share of the horizon that is sea, an eye-height slider (1.7, 5, 15, 50 m), search for any settlement, the validation viewpoints and the farthest squares, layers panel, full screen. |
| `img/ov_near_*.png`, `img/ov_hz_*.png` | Map overlays (Web Mercator, zoom-8 pixels) for each eye height. `img/*.jpg`: figures on the page. |
| `header.png` | Social card, 1200 x 630. |
| `data/squares.csv.gz` | Every square: grid, easting and northing of the centre, lon/lat, nation, county, 2010 constituency, terrain height, distance to the coast, local relief, nearest visible sea (km) and sea sight lines (of 360) at each eye height, distance to the nearest square with a sea view. ODbL (derived from OpenStreetMap). |
| `data/settlements_sea.csv` | Every Wikidata settlement point (36,692) with its own result at each eye height. |
| `data/seats_sea.csv`, `data/counties_sea.csv` | Constituency and county summaries. |
| `data/profile.csv` | Share with a sea view by 1 km band of distance to the coast and height band. |
| `data/validation.csv` | The viewpoints, their documented views (quotations and sources) and the model's results. |
| `data/grid_*.png`, `data/places.json`, `data/site.json` | Page data (lookup grids in Web Mercator, search list). |
| `data/results.json` | Every number quoted anywhere. |
| `code/` | Scripts in order, the line-of-sight kernel (`viewshed.py`), templates, `qa.js`. |
| `release/` | Paper (PDF, LaTeX, figures, `cover_note.md`), blog post and figures, Zenodo files. |
| `reddit/` | Collage, its script, the looping GIF and the post text. |
| `NOTES.md` | Working notes and the analysis plan, written before any result. |

## Method in brief

- Terrain: AWS Terrain Tiles zoom 9 (x 244 to 258, y 145 to 174), despiked; sea pixels 0 m.
- Sea: OpenStreetMap ocean polygons from OpenFreeMap vector tiles (release {R['n']['ofm_version']}), rasterised on the terrain pixels; includes tidal estuaries and sea lochs.
- Sight lines: 360 per square, steps of half a pixel, true ground distance; a sea sample is visible if its apparent elevation (h - H)/d - d/(2R'), R' = R/(1 - 0.13), is at least that of everything nearer. Rays stop at the first visible sea, at 50 km, or when no farther sea can be visible.
- Checks: eye heights 5, 15, 50 m; 25 and 100 km; k = 0 and 0.25; open sea only; at least 3 rays; 720 rays (5% sample); 500 m quarter-points (25% sample); zoom-10 terrain in four windows; 2,000 squares x 20 realisations of correlated terrain error (5 and 10 m).
- Descriptive logistic model (M1) with errors clustered by 50 km block; reach distances with a block bootstrap.

## How to rerun

Needs Python 3 with numpy, scipy, numba, pandas, statsmodels, patsy, pyproj, rasterio, shapely, mapbox-vector-tile, matplotlib, Pillow, fontTools; xelatex; node with Playwright for QA. Inputs are listed in `code/common.py`; scratch goes to `/home/claude/scratch/sea-view` (delete when done).

```
python3 code/01_dem.py          # terrain mosaic and OpenStreetMap sea mask (fetches about 27 MB of tiles)
python3 code/02_grid.py         # the squares
python3 code/03_view.py         # sight lines: main and variants (about an hour on two shared cores)
python3 code/04_z10.py          # terrain resolution check
python3 code/05_mc.py           # terrain error simulation
python3 code/06_validate.py     # documented viewpoints
python3 code/07_results.py      # results.json and data files
python3 code/08_figures.py      # figures and header
python3 code/09_build_site.py   # overlays, page data, index.html
python3 code/10_paper.py        # paper (DOI=10.5281/zenodo.N to fill the DOI)
python3 code/11_release.py      # blog post, Zenodo files
python3 code/12_readme.py       # README, Reddit post, cover note
python3 reddit/collage.py       # collage
node code/qa.js                 # screenshots in qa/
```

## Sources and licences

- AWS Terrain Tiles (Mapzen/Tilezen), with the attribution list at https://github.com/tilezen/joerd/blob/master/docs/attribution.md (SRTM, GMTED2010, ETOPO1 and others).
- OpenStreetMap contributors, ODbL 1.0, via OpenFreeMap (https://openfreemap.org/).
- Wikidata (CC0). 2011 Census populations of the 2010 Westminster constituencies and ONS boundaries (Open Government Licence v3.0). Natural Earth (public domain).
- Viewpoint sources are cited in `data/validation.csv`.
- Code MIT; text and figures CC BY 4.0; data derived from the OpenStreetMap sea mask ODbL (see LICENSE).

## Citation

Hotham, T. (2026) Can you see the sea? A line-of-sight census of sea views from every 1 km square of the United Kingdom. Zenodo. {{https://doi.org/10.5281/zenodo.24106076}}

{AI}
"""
open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8").write(readme)

post = f"""**Title:** [OC] Can you see the sea? Standing on the bare ground, the sea is in view from {M['uk_pc']:.0f}% of the UK's land. From an upstairs window, {E['5']['uk_pc']:.0f}%.

**Body:**

I traced 360 sight lines from the middle of every 1 km square of the UK ({R['n']['squares']:,} of them) over the terrain, out to 50 km, allowing for the curve of the Earth and refraction, and checked whether any of them reach the sea.

- Scotland {M['Scotland']['pc']:.0f}% of land, Wales {M['Wales']['pc']:.0f}%, Northern Ireland {M['Northern Ireland']['pc']:.0f}%, England {M['England']['pc']:.0f}%.
- Eyes at 5 m: {E['5']['uk_pc']:.0f}%. 15 m: {E['15']['uk_pc']:.0f}%. 50 m: {E['50']['uk_pc']:.0f}%.
- Where you can see it, the nearest visible sea is a median {R['near']['median_km']:.0f} km away.
- On low ground the sea is gone for half of squares about {R['reach']['0 to 50']['km']:.0f} km inland; on ground of 150 to 300 m, about {R['reach']['150 to 300']['km']:.0f} km.
- Farthest square from any sea view: near {F['near']['name']}, {F['county']}, {F['km']:.0f} km from one.
- {V['published_50']} of {V['n']} hills with a documented sea view check out at their surveyed heights ({V['terrain_50']} of {V['n']} at the coarser terrain's own heights), Pendle Hill included, as George Fox said in 1652.

Caveats: every figure is an upper bound (bare terrain, no buildings or trees), the most the land allows on a clear day. The headline is resolution-sensitive: finer terrain (about 88 m) lowers it by up to {Z['max_abs_diff']:.1f} points in test areas. \"Sea\" includes tidal estuaries and sea lochs.

Interactive map with an eye-height slider and search: https://maps.tristanhotham.com/sea-view/

**Source comment:**

Data: AWS Terrain Tiles (SRTM, GMTED2010, ETOPO1; zoom 9, about 175 m); sea from OpenStreetMap (ODbL) via OpenFreeMap; Wikidata settlements; 2011 Census. Method: line of sight with Earth curvature and refraction (k = 0.13), 360 rays per square to 50 km, every check pre-specified in a written plan. Tools: Python (numpy, numba, pandas, matplotlib), MapLibre. Paper and code: {REPO}
"""
open(os.path.join(ROOT, "reddit", "post.md"), "w", encoding="utf-8").write(post)

import subprocess
_txt = subprocess.run(["pdftotext", os.path.join(REL, "paper", "Hotham_Sea_View.pdf"), "-"], capture_output=True, text=True).stdout
ABSTRACT_WORDS = len(_txt.split("Abstract")[1].split("Keywords")[0].split())
cover = f"""# Cover note: Can you see the sea?

## Suitable journals (no article processing charge for the author)

Checked online in 2026; confirm on the publisher's page before submission.

1. **Transactions in GIS** (Wiley). Open access is optional and author-paid (listed at EUR 3,020 in the Cirad "Ou publier" directory, updated 2023); publishing under the standard agreement costs the author nothing. Wiley's author guidelines set no word limit for research articles but cap the abstract at 150 words, so the abstract ({ABSTRACT_WORDS} words) must be cut. Suits the method (exact early-stopping line of sight, national scale) and the uncertainty checks after Fisher.
2. **The Cartographic Journal** (Taylor and Francis, for the British Cartographic Society). Word limit: refereed papers up to 8,000 words (stated in a call for papers for a special issue of the journal on geospatial ethics); the paper is about 7,000 words before references, including tables, so it fits. Charges: a subscription journal; the publisher's page could not be opened in this check, so confirm that no charge applies without open access. Suits a national map product with a transparent method and an interactive map.
3. **Area** (Royal Geographical Society with IBG, Wiley). Hybrid open access (Max Planck Digital Library OA directory): no charge unless open access is chosen. Word limit: not confirmed (Wiley's Area author page could not be opened); Area papers are short, so expect to cut the paper substantially. Suits short, accessible geography with an amenity and blue-space angle.

Excluded: **Journal of Maps** (Taylor and Francis) is fully open access with an article processing charge (EUR 730 in the Cirad "Ou publier" directory, updated 2022).

## Comparison with the Ordnance Survey's farthest point from the sea

The Ordnance Survey placed Great Britain's farthest point from the sea at Church Flatts Farm near Coton in the Elms, Derbyshire, about 70 miles ({R['os_compare']['published_km']:.0f} km) from the sea at mean low water (BBC News, 23 July 2003). The farthest square from this study's coast is {FC['km']:.1f} km from it, near {FC['near']['name']} ({FC['county']}), {R['os_compare']['farthest_coast_to_os_km']:.0f} km from the Ordnance Survey point, because OpenStreetMap's coastline runs up tidal estuaries and rivers. The paper reports this as a planned check that the coastline definition fails.

## Summary of the contribution (for a cover letter)

Sea views are valued in housing markets and associated with well-being in blue-space research, but I have found no national estimate of where the sea is visible for the United Kingdom. This paper computes one: 360 sight lines from every 1 km square ({R['n']['squares']:,} squares) over open terrain data to 50 km, with curvature and refraction, against OpenStreetMap's sea (including tidal estuaries and sea lochs). Standing on bare ground, {M['uk_pc']:.1f}% of UK land has a sea view ({M['Scotland']['pc']:.0f}% of Scotland, {M['England']['pc']:.0f}% of England), rising to {E['5']['uk_pc']:.1f}% at 5 m; {P['1.7']['gb_pc']:.1f}% of Great Britain's population lives at settlement points with a view. Half of low-lying squares lose the sea within {R['reach']['0 to 50']['km']:.1f} km of the coast. Every figure is an upper bound for bare terrain, and the headline is resolution-sensitive (finer terrain lowers it by up to {Z['max_abs_diff']:.1f} points in test windows). Every check was pre-specified in a written plan; documented summit views, alternative distances, refraction, sea definitions, resolution and simulated terrain error test the result. A per-square indicator and open code are released for use in coastal amenity and health research.
"""
open(os.path.join(REL, "paper", "cover_note.md"), "w", encoding="utf-8").write(cover)
for txt in (readme, post, cover):
    for bad in ("—", "–", "DSIT", "DCMS", "civil serv", "pre-registered"):
        assert bad not in txt, bad
print("README, post, cover note written")
