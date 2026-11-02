"""Step 8. Blog post and meta (release/blog), Zenodo files and metadata (release/zenodo).
10.5281/zenodo.23873537, https://doi.org/10.5281/zenodo.23873537 and https://blog.tristanhotham.com/2026/10/31/transported-convicts/ stay as placeholders for the publisher. Reads data/ and release/ only, so it runs
without raw/."""
import json as _json, shutil, zipfile, importlib.util
from common import *

R = jload(f"{DATA}/results.json")
REL = os.path.join(ROOT, "release"); NAME = "Hotham_Transported"

# the page build checks the shared facts; these are statements in words or alt text in the blog and collage
spec = importlib.util.spec_from_file_location("b", os.path.join(ROOT, "code", "04_build_site.py")); spec.loader.exec_module(importlib.util.module_from_spec(spec))
pk, PT = R["peak"], {p["key"]: p for p in R["ports"]}
assert pk["n_1830s"] / 10 > 365 / 14                                                          # "more than one a fortnight"
assert [PT[k]["n"] for k in ("cork", "portsmouth", "london", "england", "dublin", "sheerness", "calcutta", "downs", "plymouth", "mauritius")] == [101, 100, 92, 62, 51, 45, 42, 41, 36, 33]   # b_ports alt text
assert [p["key"] for p in R["ports"][:3]] == ["cork", "portsmouth", "london"]
assert (pk["year"], pk["n"]) == (1833, 35) and round(R["irish"]["pct"]) == 26 and round(R["irish"]["nsw_pct"]) == 34 and round(R["irish"]["vdl_pct"]) == 6
assert [e["median"] for e in R["days"]["eras"]] == [190, 164, 115, 90] and R["days"]["slow"]["days"] == 309
D = sorted(R["deaths"]["tf_ships"], key=lambda s: -s["pct"])
assert (round(D[0]["pct"]), D[0]["ship"], round(D[-1]["pct"])) == (14, "Britannia", 3) and R["deaths"]["art_n"] == 24 and R["deaths"]["sf_pct"] == 26
P = {p["year"]: round(p["fpct"]) for p in R["women"]["pop"]}
assert (P[1788], P[1819], P[1828], P[1836], P[1841]) == (26, 11, 9, 9, 12) and max(p["total"] for p in R["women"]["pop"]) == 27831
assert R["col"]["nsw"]["first"] == 1788 and R["col"]["wa"]["last"] == 1868

post = open(os.path.join(ROOT, "code", "blog_template.html"), encoding="utf-8").read()
post = fill(post, R)
used = re.findall(r"\{\{IMG\|([^|]+)\|", post)
assert 5 <= len(used) <= 8, len(used)
assert all(re.search(r"^\{\{IMG\|" + re.escape(u), post, re.M) for u in used) and "wp:image" not in post
for img in used:
    assert os.path.exists(f"{REL}/blog/{img}"), img
for fn in os.listdir(f"{REL}/blog"):
    if fn.startswith("b_") and fn not in used:
        os.remove(f"{REL}/blog/{fn}")
assert set(re.findall(r"\{\{[^|}]+\}\}", post)) <= {"https://doi.org/10.5281/zenodo.23873537"}
vis = re.sub(r"<!--.*?-->", "", post, flags=re.S)
visible_text_ok(vis, "blog")
open(f"{REL}/blog/post.html", "w", encoding="utf-8").write(post)
words = len(re.sub(r"<[^>]+>|\{\{IMG\|[^}]*\}\}", " ", vis).split())
s = R["source"]
meta = {"title": "Transported: every convict ship to Australia, mapped",
        "slug": "transported-convicts",
        "excerpt": f"Britain shipped about {R['stated']['conv_162']:,} convicts to Australia. I mapped all {s['n_main']} voyages in Wikipedia's ship lists: the busiest port was Cork, the busiest year {pk['year']}, and the Second Fleet lost a quarter of its convicts at sea.",
        "seo_description": f"A map of {s['n_main']} convict voyages to Australia, 1788 to 1868: ports, passage times, deaths at sea, and penal transportation worldwide.",
        "tags": ["history", "maps", "data visualisation", "convicts", "Australia", "penal transportation", "maritime history", "Wikipedia"],
        "header_alt": f"Title card reading 'Transported' in black and red on pale paper, beside a world map with a thick braid of coloured lines running from the British Isles south through the Atlantic, round the Cape of Good Hope and across the Southern Ocean to Fremantle, Hobart, Sydney and Norfolk Island, and thinner lines from India and Mauritius. Below, a bar chart of ships arriving each year, rising to {pk['n']} in {pk['year']}. Text: every convict voyage to Australia in Wikipedia's lists, {s['n_main']} ships, 1788 to 1868."}
assert len(meta["seo_description"]) < 160, len(meta["seo_description"])
visible_text_ok(_json.dumps(meta, ensure_ascii=False), "meta")
jsave(meta, f"{REL}/blog/meta.json", indent=2)

# Zenodo
Z = f"{REL}/zenodo"; os.makedirs(Z, exist_ok=True)
for fn in os.listdir(Z):
    os.remove(os.path.join(Z, fn))
shutil.copy(f"{REL}/paper/{NAME}.pdf", f"{Z}/{NAME}.pdf")
zp = f"{Z}/transported-convicts_data_and_code.zip"
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED) as z:
    for d in ("code", "data", "data/source_tables"):
        for fn in sorted(os.listdir(os.path.join(ROOT, d))):
            p = os.path.join(ROOT, d, fn)
            if fn.endswith(".pyc") or fn == "__pycache__" or os.path.isdir(p):
                continue
            z.write(p, f"transported-convicts/{d}/{fn}")
    for fn in ("README.md", "LICENSE"):
        z.write(os.path.join(ROOT, fn), f"transported-convicts/{fn}")
    z.write(os.path.join(ROOT, "reddit", "collage.py"), "transported-convicts/reddit/collage.py")
tex = open(f"{REL}/paper/{NAME}.tex", encoding="utf-8").read()
ab = re.search(r"\\begin\{center\}\\textbf\{Abstract\}\\end\{center\}\n(.*?)\n\n\\textbf\{Keywords", tex, re.S).group(1)
ab = ab.replace("\\%", "%").replace("\\&", "&")
zmeta = {"title": "Transported: The Convict Ships to Australia, 1788 to 1868, and the Wider World of Penal Transportation",
         "upload_type": "publication", "publication_type": "workingpaper",
         "description": f"<p>{ab}</p><p>Interactive version: <a href=\"{PAGE}\">{PAGE}</a>. Data and code: <a href=\"{REPO}\">{REPO}</a>. Blog post: {BLOG}.</p><p>Sources: English Wikipedia (CC BY-SA 4.0); the tables derived from it are released under CC BY-SA 4.0. Natural Earth (public domain).</p>",
         "creators": [{"name": "Hotham, Tristan", "affiliation": "Independent researcher", "orcid": "0000-0003-4931-9349"}],
         "keywords": ["penal transportation", "convicts", "convict ships", "Australia", "New South Wales", "Van Diemen's Land", "Western Australia", "maritime history", "colonial history", "Wikipedia", "open data", "maps"],
         "license": "cc-by-4.0", "language": "eng",
         "notes": "Code MIT; text and figures CC BY 4.0; data/voyages.csv, data/ships.csv, data/source_tables and data/source_quotes.json CC BY-SA 4.0 (derived from English Wikipedia).",
         "related_identifiers": [{"identifier": REPO, "relation": "isSupplementedBy", "resource_type": "software"},
                                 {"identifier": PAGE, "relation": "isSupplementedBy", "resource_type": "other"},
                                 {"identifier": WIKI_URL("Convict ships to New South Wales"), "relation": "isDerivedFrom", "resource_type": "other"},
                                 {"identifier": WIKI_URL("Convict ships to Tasmania"), "relation": "isDerivedFrom", "resource_type": "other"},
                                 {"identifier": WIKI_URL("Convict ships to Norfolk Island"), "relation": "isDerivedFrom", "resource_type": "other"},
                                 {"identifier": WIKI_URL("List of convict ship voyages to Western Australia"), "relation": "isDerivedFrom", "resource_type": "other"},
                                 {"identifier": "https://www.naturalearthdata.com/", "relation": "isDerivedFrom", "resource_type": "dataset"}],
         "files": sorted(os.listdir(Z))}
sj = _json.dumps(zmeta, ensure_ascii=False)
assert "\u2014" not in sj and "\u2013" not in sj and "--" not in sj
jsave(zmeta, f"{Z}/metadata.json", indent=2)
print("blog words", words, "figures", len(used), "; zenodo", sorted(os.listdir(Z)), os.path.getsize(zp) // 1024, "KB zip")
