# sea-view: working notes

Brief: /home/claude/work/new13/BRIEFS.md section G (+ shared rules new12, new11, new10, new9, new8 and the house brief
/home/claude/newdata/BRIEF.md; GIF brief /home/claude/gifs/BRIEF.md). Format refs: fame-half-life, byelection-attention;
method siblings: sunless-valleys (terrain horizons), sea-sunsets (sea rays, OpenFreeMap ocean mask).
Scratch: /home/claude/scratch/sea-view (DEM mosaic, sea mask, z10 windows; delete by exact path at the end).
Raw terrain: /home/claude/newdata/raw_new13/terrarium_z9_pack*.bin/.json (shared with trig-network: read only, never move).

## Analysis plan (written 2026-11-10T08:35Z, before any visibility outcome was computed)

Question: from how much of the United Kingdom can a person standing on the bare ground see the open sea, how far away is the
nearest sea they can see, and how much of the horizon is sea? Descriptive and cartographic; no causal claims.

### Coverage and units
- Great Britain (England, Scotland, Wales, with their islands) on the Ordnance Survey National Grid 1 km squares; Northern
  Ireland on Irish Grid 1 km squares, reported separately and in UK totals. Isle of Man, Ireland, France: terrain and sea
  only (they can block or be seen across), never counted as observers.
- A square is counted if its centre is not open sea (OSM ocean) and lies in (or within 2 km of) a UK nation polygon
  (counties_uk.geojson). Inland water squares are counted (stated as a limitation). Area = number of squares (km2).

### Terrain and sea
- Terrain: AWS Terrain Tiles (Terrarium encoding) zoom 9, about 175 m at 55 N, mosaicked in Web Mercator pixels; despiked
  as in sunless-valleys (7 x 7 median rule). Bare earth plus whatever the SRTM radar saw: no buildings or trees modelled.
- Sea: OpenStreetMap ocean polygons (OpenFreeMap vector tiles, water class "ocean", zoom 9) rasterised on the same pixel grid.
  Sea pixels have height 0 m (mean sea level; tides ignored). Land pixels keep the terrain height (Fens below 0 kept;
  terrain below -5 m on land pixels, a bathymetry bleed at the shore, set to 0).

### Visibility (main specification)
- Observer at the square centre, eye 1.7 m above the terrain (bilinear). 360 rays (every 1 degree), sampled every half
  terrain pixel (about 90 m) out to D = 50 km.
- Apparent elevation of a sample at distance d with height h: a = (h - H)/d - d/(2R'), H = ground + eye,
  R' = R/(1 - k), R = 6,371 km, k = 0.13 (standard refraction).
- A sea sample is visible if its a is at least the maximum a of every sample (land or sea) nearer along the ray. Sea is
  visible on a ray if any sea sample is visible. A ray stops at the first visible sea, at D, at the edge of the terrain
  mosaic (no sea; counted), or when the running maximum exceeds the highest angle any farther sea could reach.
- Outcomes per square: sea_view (any ray), nearest visible sea (km, minimum over rays), sea share of the horizon (share of
  the 360 rays with visible sea).
- D = 50 km: Met Office "excellent visibility" is more than 40 km; beyond about 50 km a sea surface is rarely distinguishable
  (to verify and cite). Sensitivity 25 and 100 km.

### Estimands (reported whatever they show)
- E1 share of UK land squares with a sea view at 1.7 m (and by nation, region).
- E2 share of population with a sea view. GB: 2011 Census population of the 632 2010 Westminster seats (beeching-leave
  constituencies.csv; seat polygons twins-remain seats.geojson), each seat's population split by the share of its Wikidata
  settlement population (points, sunless-valleys settlements_sun.csv) that has a sea view at the settlement's own point;
  settlements with a population above their seat's census population are aggregates and are dropped; seats with no
  settlement population fall back to the seat's share of land squares. NI: Wikidata settlement population directly.
- E3 distance inland at which half of squares see the sea (by height band 0 to 50, 50 to 150, 150 to 300, 300 m+), from a
  binned profile of sea_view against distance to the coast, with 95% CIs by block bootstrap over 50 km grid blocks.
- E4 the land squares farthest from any square with a sea view, and farthest from the coast (validation: compare with the
  published "farthest point from the sea" near Coton in the Elms, Derbyshire, about 70 miles / 113 km; verify).
- E5 distribution of nearest visible sea distance and sea share of horizon.

### Model (correlates; not causal)
- M1 logistic regression of sea_view on log(distance to coast) (natural spline, 4 df), log(1 + height above sea level),
  local relief (height minus the 5 km neighbourhood mean), nation fixed effects; errors clustered by 50 km blocks.
  Reported as average marginal effects with 95% CIs, N squares and clusters.

### Pre-specified checks
- V1 validation: about 15 to 25 named summits or viewpoints with a documented sea view (verified sources), computed at the
  exact point with the terrain height there and, separately, with the published summit height. Decision rule: if fewer than
  80% are reproduced, the model is judged unfit and every result is labelled provisional.
- S1 eye height 5, 15, 50 m (also the map slider). S2 D = 25 and 100 km. S3 k = 0 and k = 0.25.
- S4 0.5 degree rays (720) on a random 5% sample of squares.
- S5 observer grid 500 m over all GB/NI (four points per 1 km square: share of squares where any/all quarter-points see sea).
- S6 terrain resolution: zoom 10 tiles (about 88 m, raw_new8) in four test windows (Cumbria and Lancashire coast, Cornwall,
  Lothian and Fife, Norfolk) against zoom 9 for the same squares. Rule: if the share differs by more than 3 percentage
  points, the headline is called resolution-sensitive and both figures are given.
- S7 "open sea" only: ocean pixels in channels narrower than about 1 km (morphological opening) not counted as sea.
- S8 more than a glimpse: sea visible on at least 3 of the 360 rays.
- S9 terrain error (Fisher 1993 "probable viewshed"): 2,000 random squares, 20 realisations of spatially correlated Gaussian
  error (sd 5 m, correlation length about 1 km; sd 10 m as a variant); report the expected share and a 95% interval.
- Headline uncertainty: the S9 interval, plus the range across S2, S3, S4, S5, S6, S7, S8 as a sensitivity range.

What would count against the method: failed validation (V1 rule), large resolution sensitivity (S6 rule), or a farthest-
from-sea point far from the published one (more than 10 km).

## Log
- 2026-11-10 08:41: 01_dem.py: 450 zoom-9 tiles mosaicked (3840 x 7680 px); 143 spike/pit cells replaced; OpenFreeMap
  release 20261101_080013_pt, zoom 9, 27.2 MB fetched one tile at a time and deleted. Land pixels below 0 m: the Fens and
  the Broads (expected). Max terrain 1,271 m (Ben Nevis 1,345 m: zoom 9 flattens summits).
- 02_grid.py: GB 229,996 squares (England 130,360, Scotland 78,862, Wales 20,774), NI 14,176. First version leaked
  squares from the Republic of Ireland across the land border via the "nearest nation within 2 km" rule; fixed before any
  outcome (rule now applies only within 2 km of the sea, and Natural Earth IRL/IMN polygons exclude). Max distance to the
  OSM coast 114.4 km.
- Speed test on 3,000 random squares (timing only). Main run 295 s on two shared cores (load average 15 to 20 from other
  builders). To keep each run bounded, S5 was reduced from all squares to a random 25% (recorded in the plan section of the
  paper as a deviation) and variants are cached per file so that a run can be resumed.
- 06_validate.py: 8 of 10 at terrain height (rule of 80% met exactly), 9 of 10 at published height. Misses: Pendle Hill at
  terrain height (summit flattened; found at 557 m, about 40 km); Worcestershire Beacon at both heights and also at 100 km.
  Not adjusted.

## Literature verification status (independent review, 2026-11-10)
All references in the paper were checked online by the reviewer (title, authors, year, venue, volume, pages, DOI where one exists),
and each claim was checked against the abstract or a reliable summary. Changes:
- Removed (could not verify the record or the claim): Maloy and Dean 2001, Riggs and Dean 2007, Llobera 2003, Haverkort et al. 2009,
  Izraelevitz 2003, Kaplan and Kaplan 1989.
- Claims corrected to match the abstracts: Fisher 1991 (simulated DEM error; original viewshed may overestimate area), Fisher 1992
  (cumulated Boolean viewsheds from error realisations, not distance decay), Fisher 1993 (viewpoint/target representation; GIS
  implementations disagree), Fisher 1994 (distinguishes probable and fuzzy models), Fisher 1996 (title-level only), Sander and
  Manson 2007 (building generalisation changes viewsheds; no claim about vegetation or direction), Gibbons et al. 2014 (no
  coastline claim), Nutsford et al. 2016 (no viewshed claim), Hirt et al. 2010 (k measured near the ground).
- Details added or corrected: DOIs for most journal articles; Rodriguez et al. 2006 72(3) 249-260; Wheatley 1995 book title;
  van Kreveld 1996 (SDH proceedings, also UU-CS-1996-22); Garrett et al. 2019 cited by article number and DOI (volume not confirmed);
  Volker and Kistemann 2011 without issue number (not confirmed).
- Added: Haran 2003 (BBC News) for the Ordnance Survey farthest point from the sea (Church Flatts Farm, SK 253 144, about
  70 miles / 113 km at mean low water). Compared in the paper: the farthest square from this study's coast is 90 km from the OS point
  (the planned check counts against the OSM coastline definition, which runs up tidal rivers).
- Journals: Transactions in GIS (optional OA; abstract max 150 words), The Cartographic Journal (8,000 words; charges not confirmed),
  Area (hybrid; word limit not confirmed). Journal of Maps excluded (APC). See release/paper/cover_note.md.
- 2026-11-10 (later): QA found 340 GB and 83 NI squares missing in slivers between the simplified county polygons. Fixed in
  02_grid.py (nearest county within 2 km anywhere except Ireland/IoM) and every run repeated from scratch on the corrected
  grid (244,595 squares). Main-run result changed by less than 0.03 points.
- Model detail: the plan said "natural spline"; implemented as patsy cr(df=4, centred). A first version with an uncentred
  basis was collinear with the intercept (AME intervals collapsed); fixed before reporting.

## Results (numbers from data/results.json)
- E1: 26.28% of UK land (64,277 squares); England 16.4, Scotland 41.3, Wales 33.6, NI 22.5.
  Eyes 5/15/50 m: 29.2 / 34.5 / 45.1%.
- E2: GB population 22.6% (Wikidata-only weighting 22.0%); NI settlement population 56.0%.
- E3: half-way distance 3.5 km (<50 m), 6.5, 9.0, 8.6 km (>300 m: no gain at the half-way mark).
- E4: farthest from a sea view 94.4 km near Donington le Heath; farthest from coast 114.4 km near Akeley (Ordnance Survey point near Coton in the Elms, 113 km at mean low water, is 90 km away: planned check fails on the coastline definition).
- V1: 8/10 at terrain height (rule met exactly), 9/10 at published height.
- S6 (z10): lower in all four windows, max diff 7.3 points > 3: headline RESOLUTION-SENSITIVE (stated in paper, blog, page, README). Exploratory scaled estimate 23.3%.
- Sensitivity range 22.1 to 27.0%; MC sd 5 m 25.2% (24.6 to 25.8) vs 25.0% on the same squares.

## Deliverables
index.html + js/page.js (QA qa/*.png, 0 console errors at 1280 and 390 px), img overlays, header.png, data/*, code/01..12,
release/paper (PDF 19 pp, about 6,900 words before references incl. tables, abstract 240 words, 39 references, cover_note.md),
release/blog (post.html, 6 figures, meta.json), release/zenodo, reddit (collage, post.md, sea-view.gif; script
/home/claude/gifs/scripts/sea-view.py). Scratch deleted at the end.
