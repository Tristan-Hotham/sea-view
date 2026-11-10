# Can you see the sea?

A line-of-sight census of sea views from every 1 km square of the United Kingdom (244,595 squares: Ordnance Survey National Grid squares in Great Britain, Irish Grid squares in Northern Ireland). From the centre of each square, 360 sight lines over the open AWS Terrain Tiles (zoom 9, about 175 m) out to 50 km, with Earth curvature and standard refraction (k = 0.13), against OpenStreetMap's sea; four eye heights; settlements weighted by census population; validation against documented viewpoints and sensitivity checks, all pre-specified in a written plan before any result was computed (NOTES.md). A data study by Dr Tristan Hotham (Independent researcher).

Interactive page: https://maps.tristanhotham.com/sea-view/
Paper: https://doi.org/10.5281/zenodo.24106076
Blog post: https://blog.tristanhotham.com/2026/10/31/sea-view/
Code and data: https://github.com/Tristan-Hotham/sea-view

## Headline results

- Standing on the bare ground (eyes 1.7 m), the sea is in view within 50 km from 64,277 squares, 26.3% of UK land: Scotland 41.3%, Wales 33.6%, Northern Ireland 22.5%, England 16.4%.
- Eye height: 29.2% at 5 m (an upstairs window), 34.5% at 15 m, 45.1% at 50 m.
- Where the sea is in view, the nearest visible sea is a median 5.9 km away; the median square with a view sees sea across 14.2% of the horizon; 2,789 squares see sea across more than half of it.
- Half of squares lose sight of the sea at 3.5 km (95% CI 3.1 to 3.9) from the coast on ground below 50 m, 6.5 km (95% CI 5.8 to 7.3) at 50 to 150 m, 9.0 km (95% CI 8.1 to 10.2) at 150 to 300 m and 8.6 km (95% CI 7.1 to 13.6) above 300 m.
- People: 22.6% of Great Britain's 2011 population live at settlement points with a sea view (constituency populations split by Wikidata settlement populations); 25.2% from 5 m. Northern Ireland: 56.0% of the Wikidata settlement population.
- Farthest square from any sea view: 94.4 km, near Donington le Heath (Leicestershire). Farthest from the coast: 114.4 km, near Akeley (Buckinghamshire).
- Validation: 8 of 10 documented sea views reproduced at the terrain height, 9 at published summit heights (misses: Worcestershire Beacon).
- Sensitivity (planned checks): the share ranges from 22.1% to 27.0%; terrain error (5 m) gives 25.2% (95% interval 24.6 to 25.8) against 25.0% on the same 2,000 squares; zoom-10 terrain 32.8% against 37.0% in four test windows (lower in every window; by the planned rule the headline is resolution-sensitive).
- All figures are upper bounds: bare terrain, with no buildings, trees or hedges, which would lower every figure.
- The headline is resolution-sensitive: finer terrain (about 88 m) lowers the share in all four test windows, by up to 7.3 points.
- "Sea" is OpenStreetMap's coastline and includes tidal estuaries and sea lochs. Population figures cover Great Britain only (Northern Ireland separately); land figures cover the UK.
- Farthest from the coast compared with the Ordnance Survey's published point (Church Flatts Farm, near Coton in the Elms, about 113 km from the sea at mean low water): the square found here is 90 km from it, because OpenStreetMap's coast runs up tidal estuaries.

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
- Sea: OpenStreetMap ocean polygons from OpenFreeMap vector tiles (release 20261101_080013_pt), rasterised on the terrain pixels; includes tidal estuaries and sea lochs.
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

Hotham, T. (2026) Can you see the sea? A line-of-sight census of sea views from every 1 km square of the United Kingdom. Zenodo. https://doi.org/10.5281/zenodo.24106076

I wrote the text, with drafting and editing assistance from Claude (Anthropic), which also helped prepare the analysis code. I reviewed and checked all text and results.
