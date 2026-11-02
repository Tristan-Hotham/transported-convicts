"""Step 4. Build index.html from code/page_template.html. Every number in the text is a {{path|format}} token filled
from data/results.json; the page data (results, site.json, world.json) is embedded. Facts stated in words on the page,
blog, paper and collage are checked here against the data. The full-screen map snippet (code/fullscreen_snippet.html)
is pasted before </body>. 10.5281/zenodo.23873537 and https://blog.tristanhotham.com/2026/10/31/transported-convicts/ stay as placeholders for the publisher."""
import json
from common import *

R = jload(f"{DATA}/results.json")
SITE = jload(f"{DATA}/site.json")
Q = jload(f"{DATA}/source_quotes.json")["quotes"]
col, pk, dd, de, ir, sh, wo, cv = R["col"], R["peak"], R["days"], R["deaths"], R["irish"], R["ships"], R["women"], R["cover"]

# facts stated in words (page, blog, paper, collage)
assert col["wa"]["last_ship"] == "Hougoumont" and col["wa"]["last_date"] == "9 January 1868" and col["wa"]["first_ship"] == "Scindian"
assert col["nsw"]["first"] == 1788 and col["wa"]["first"] == 1850 and col["wa"]["last"] == 1868
assert pk["n"] > 30 and 1830 <= pk["year"] <= 1839 and pk["dec"] == 1830                    # "more than thirty in the 1830s"
assert pk["vdl_4149"] > pk["nsw_4149"] and pk["nfk_4149"] > pk["nsw_4149"]                    # "move from Sydney to Hobart and Norfolk Island"
assert pk["n_1790s"] < 40 and pk["n_1800s"] < 40 and pk["n_1815_1840"] > len(R["years"]) * 5
assert cv["avg_known"] == cv["avg_stated"] and cv["n_main_pct_806"] > 90                       # "the same as", "most of the ships are there"
assert col["wa"]["n"] == 43 and "43 convict ship voyages" in Q["wa_9721"]["phrase"]            # "the one list that is complete"
assert R["source"]["n_main"] > 700
assert dd["slow"]["ship"] == "Lady Juliana" and dd["fast"]["ship"] == "Scindian" and dd["eras"][0]["median"] > dd["eras"][2]["median"]
assert sh["top"][0]["name"] == "Mangles" and sh["top"][0]["voyages"] > sh["top"][1]["voyages"] and sh["top"][0]["lead"] == sh["top"][0]["voyages"]
assert de["tf_best"]["ship"] == "Salamander" and de["tf_worst"]["ship"] == "Britannia" and de["art_pct"] < 1
assert de["mangles_max"] == 3 and de["mangles_n_deaths"] >= 4
assert ir["cork_rank"] == 1 and ir["thames"] + ir["solent"] > ir["n_ei"] / 2 and ir["nsw_n"] / ir["n"] > .9   # "most ... Thames or Solent", "nearly all"
assert ir["wa_irish"] == 1 and ir["portland_wa"] > ir["plymouth_wa"] > 0
assert R["indian"]["wa_conv"] < 50 and R["indian"]["wa"] == 6
assert sh["lead_agree"] / sh["lead_checked"] > .8                                             # "agree well"
assert wo["pop_first_pct"] > wo["pop_last_pct"] and {"Lady Penrhyn", "Lady Juliana"} <= {s["ship"] for s in wo["ships_flagged"]}
assert R["stated"]["sites"] == 11                                                             # "Eleven convict sites"
assert sum(1 for w in R["world"]) == 8


def build():
    tpl = open(os.path.join(ROOT, "code", "page_template.html"), encoding="utf-8").read()
    html = fill(tpl, R)
    left = re.findall(r"\{\{[^}]*\}\}", html)
    assert set(left) <= {"10.5281/zenodo.23873537", "https://blog.tristanhotham.com/2026/10/31/transported-convicts/"}, left[:5]
    J = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":"))
    html = html.replace("/*RESULTS*/", J(R)).replace("/*SITE*/", J(SITE))
    html = html.replace("/*WORLD*/", open(f"{DATA}/world.json", encoding="utf-8").read())
    html = html.replace("/*FULLSCREEN*/", open(os.path.join(ROOT, "code", "fullscreen_snippet.html"), encoding="utf-8").read())
    vis = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", html, flags=re.S)
    vis = re.sub(r"<[^>]+>", " ", vis)
    visible_text_ok(vis, "index.html")
    for scr in re.findall(r"<script>(.*?)</script>", html, flags=re.S):
        for bad in ("—", "–"):
            assert bad not in scr, bad
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(html)
    print("index.html", len(html.encode()) // 1024, "KB")


if __name__ == "__main__":
    build()
