**Title:** [OC] Can you see the sea? Standing on the bare ground, the sea is in view from 26% of the UK's land. From an upstairs window, 29%.

**Body:**

I traced 360 sight lines from the middle of every 1 km square of the UK (244,595 of them) over the terrain, out to 50 km, allowing for the curve of the Earth and refraction, and checked whether any of them reach the sea.

- Scotland 41% of land, Wales 34%, Northern Ireland 22%, England 16%.
- Eyes at 5 m: 29%. 15 m: 35%. 50 m: 45%.
- Where you can see it, the nearest visible sea is a median 6 km away.
- On low ground the sea is gone for half of squares about 3 km inland; on ground of 150 to 300 m, about 9 km.
- Farthest square from any sea view: near Donington le Heath, Leicestershire, 94 km from one.
- 9 of 10 hills with a documented sea view check out at their surveyed heights (8 of 10 at the coarser terrain's own heights), Pendle Hill included, as George Fox said in 1652.

Caveats: every figure is an upper bound (bare terrain, no buildings or trees), the most the land allows on a clear day. The headline is resolution-sensitive: finer terrain (about 88 m) lowers it by up to 7.3 points in test areas. "Sea" includes tidal estuaries and sea lochs.

Interactive map with an eye-height slider and search: https://maps.tristanhotham.com/sea-view/

**Source comment:**

Data: AWS Terrain Tiles (SRTM, GMTED2010, ETOPO1; zoom 9, about 175 m); sea from OpenStreetMap (ODbL) via OpenFreeMap; Wikidata settlements; 2011 Census. Method: line of sight with Earth curvature and refraction (k = 0.13), 360 rays per square to 50 km, every check pre-specified in a written plan. Tools: Python (numpy, numba, pandas, matplotlib), MapLibre. Paper and code: https://github.com/Tristan-Hotham/sea-view
