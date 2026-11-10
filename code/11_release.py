"""Step 11: blog post and meta (release/blog), Zenodo files and metadata (release/zenodo).
10.5281/zenodo.24106076, https://doi.org/10.5281/zenodo.24106076 and https://blog.tristanhotham.com/2026/10/31/sea-view/ are left for the publisher to fill."""
import json as _json, shutil, zipfile
from PIL import Image
from common import *

R = jload(f"{DATA}/results.json")
NAME = "Hotham_Sea_View"
KEEP = {"DOI", "DOI_URL", "BLOG_URL"}
post = open(os.path.join(ROOT, "code", "blog_template.html"), encoding="utf-8").read()
post = re.sub(r"\{\{(?!IMG)([^}|]+)(\|(\w+))?\}\}", lambda m: m.group(0) if m.group(1) in KEEP else fmt(get(R, m.group(1)), m.group(3)), post)
used = re.findall(r"\{\{IMG\|([^|]+)\|", post)
assert 5 <= len(used) <= 8, len(used)
assert all(re.search(r"^\{\{IMG\|" + re.escape(u_), post, re.M) for u_ in used) and "wp:image" not in post
for img in used:
    assert Image.open(f"{REL}/blog/{img}").size[0] == 1800, img
for fn in os.listdir(f"{REL}/blog"):
    if fn.startswith("b_") and fn not in used:
        os.remove(f"{REL}/blog/{fn}")
assert set(re.findall(r"\{\{([^|}]+)\}\}", post)) <= KEEP
vis = re.sub(r"<!--.*?-->", "", post, flags=re.S)
for bad in ("\u2014", "\u2013", "--", "DSIT", "DCMS", "civil serv", "pre-registered"):
    assert bad not in vis, bad
assert AI in post
open(f"{REL}/blog/post.html", "w", encoding="utf-8").write(post)
words = len(re.sub(r"<[^>]+>|\{\{IMG\|[^}]*\}\}", " ", vis).split())
M = R["main"]
meta = {"title": "Can you see the sea?",
        "slug": "sea-view",
        "excerpt": f"I traced 360 sight lines from every 1 km square of the UK. Standing on the bare ground, {M['uk_pc']:.0f}% of the land has the sea in view; from an upstairs window, {R['eyes']['5']['uk_pc']:.0f}%. The farthest square from any sea view is near {R['farthest_seaview'][0]['near']['name']}.",
        "seo_description": f"From how much of the UK can you see the sea? Sight lines from every 1 km square: {M['uk_pc']:.0f}% of the land, standing on the ground.",
        "tags": ["maps", "data visualisation", "sea", "coast", "viewshed", "terrain", "United Kingdom", "geography"],
        "header_alt": "Title card on pale paper reading 'Can you see the sea?' beside a map of the UK with coastal areas in shades of blue by the distance to the nearest visible sea and inland areas in sand."}
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
_json.dump(meta, open(f"{REL}/blog/meta.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
Z = f"{REL}/zenodo"; os.makedirs(Z, exist_ok=True)
for fn in os.listdir(Z):
    os.remove(os.path.join(Z, fn))
shutil.copy(f"{REL}/paper/{NAME}.pdf", f"{Z}/{NAME}.pdf")
zp = f"{Z}/{SLUG}_data_and_code.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for fn in sorted(os.listdir(os.path.join(ROOT, "code"))):
        if fn.endswith((".pyc", ".png")) or fn == "__pycache__":
            continue
        z.write(os.path.join(ROOT, "code", fn), f"{SLUG}/code/{fn}")
    for fn in ("squares.csv.gz", "settlements_sea.csv", "seats_sea.csv", "counties_sea.csv", "profile.csv", "validation.csv", "results.json"):
        z.write(os.path.join(DATA, fn), f"{SLUG}/data/{fn}")
    for fn in ("README.md", "LICENSE", "NOTES.md"):
        z.write(os.path.join(ROOT, fn), f"{SLUG}/{fn}")
    z.write(os.path.join(REL, "paper", "cover_note.md"), f"{SLUG}/release/paper/cover_note.md")
    z.write(os.path.join(ROOT, "reddit", "collage.py"), f"{SLUG}/reddit/collage.py")
tex = open(f"{REL}/paper/{NAME}.tex", encoding="utf-8").read()
ab = re.search(r"\\begin\{center\}\\textbf\{Abstract\}\\end\{center\}\n(.*?)\n\n", tex, re.S).group(1)
ab = ab.replace("\\%", "%").replace("\\&", "&").replace("$", "").replace("``", "\"").replace("''", "\"").replace("~", " ")
zmeta = {"title": "Can You See the Sea? A Line-of-Sight Census of Sea Views from Every 1 km Square of the United Kingdom",
         "upload_type": "publication", "publication_type": "workingpaper",
         "description": f"<p>{ab}</p><p>Interactive version: <a href=\"{PAGE}\">{PAGE}</a>. Data and code: <a href=\"{REPO}\">{REPO}</a>. Blog post: {{https://blog.tristanhotham.com/2026/10/31/sea-view/}}.</p>"
                        "<p>Sources: AWS Terrain Tiles (Mapzen/Tilezen; SRTM, GMTED2010, ETOPO1 and others, see the Terrain Tiles attribution list); "
                        "sea from OpenStreetMap (ODbL) via OpenFreeMap vector tiles; Wikidata settlements (CC0); 2011 Census populations of the 2010 "
                        "Westminster constituencies (ONS, Open Government Licence v3.0); ONS-derived county boundaries (OGL v3.0); Natural Earth. "
                        "Text, figures and derived data CC BY 4.0, except data derived from OpenStreetMap (the sea mask and every distance to the sea), "
                        "shared under the ODbL; code MIT.</p>",
         "creators": [{"name": "Hotham, Tristan", "affiliation": "Independent researcher", "orcid": "0000-0003-4931-9349"}],
         "keywords": ["viewshed", "line of sight", "sea view", "coast", "terrain analysis", "visibility", "United Kingdom", "cartography"],
         "license": "cc-by-4.0", "language": "eng",
         "related_identifiers": [{"identifier": REPO, "relation": "isSupplementedBy", "resource_type": "software"},
                                 {"identifier": PAGE, "relation": "isSupplementedBy", "resource_type": "other"},
                                 {"identifier": "10.5281/zenodo.24055580", "relation": "references", "resource_type": "publication"},
                                 {"identifier": "10.5281/zenodo.24089892", "relation": "references", "resource_type": "publication"}],
         "files": sorted(os.listdir(Z))}
sj = _json.dumps(zmeta, ensure_ascii=False) + _json.dumps(meta, ensure_ascii=False)
assert "\u2014" not in sj and "\u2013" not in sj and "--" not in sj
_json.dump(zmeta, open(f"{Z}/metadata.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("blog words", words, "figures", len(used), "; zenodo", sorted(os.listdir(Z)), os.path.getsize(zp) // 1024, "KB zip")
