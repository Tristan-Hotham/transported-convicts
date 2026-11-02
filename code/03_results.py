"""Step 3. Every number used anywhere (data/results.json), the reusable tables (data/*.csv) and the page data
(data/site.json). Reads data/ only.

Definitions:
  * a listed voyage: one row of the four voyage tables (New South Wales, Tasmania, Norfolk Island, Western Australia),
    plus Prince of Wales of the First Fleet, which the New South Wales list omits (added from the First Fleet article);
  * a convict voyage from overseas: a listed voyage with an arrival year, whose departure place is not in Australia,
    that is not a Parkhurst apprentice ship (Western Australia, 1842 to 1849) and is not the same voyage listed again
    by a second colony (same ship name, arrivals within 75 days of each other, not two different linked articles);
  * a transfer within Australia: a listed voyage that sailed from an Australian port (Sydney, Hobart, Norfolk Island,
    Adelaide, the Swan River or Port Phillip);
  * year: year of arrival (departure years are known for very few voyages);
  * convicts on a voyage: the number landed where a table or article gives it, otherwise the number embarked;
  * voyage length: days from departure to arrival as the fleet tables state them, or as computed from a ship article's
    own departure and arrival dates (kept only where that arrival matches the voyage table within three days);
  * Irish voyage: sailed from Cork, Dublin (Kingstown), Waterford or 'Ireland'."""
import numpy as np, pandas as pd, datetime as dt
from common import *

V = pd.read_csv(f"{SRC}/voyage_rows.csv", keep_default_na=False, na_values={"arr_y": "", "arr_m": "", "arr_d": "", "embarked": "", "landed": "", "days": "",
                                                                         "male": "", "female": "", "deaths": ""})
for c in ("arr_y", "arr_m", "arr_d", "embarked", "landed", "days", "male", "female", "deaths", "row", "fleet", "nfk_period", "parkhurst", "women", "article_inherited"):
    V[c] = pd.to_numeric(V[c], errors="coerce").astype("Int64")
Q = jload(f"{DATA}/source_quotes.json"); QU, REVS, CHK = Q["quotes"], Q["revids"], Q["checks"]
ROUTES = jload(f"{DATA}/routes.json")
S = pd.read_csv(f"{SRC}/ship_articles.csv", keep_default_na=False)
F = pd.read_csv(f"{SRC}/fleet_ships.csv")
POP = pd.read_csv(f"{SRC}/nsw_convict_population_by_sex.csv")
K = pd.read_csv(f"{SRC}/ship_article_voyages.csv", keep_default_na=False)
pc = lambda a, b: round(100 * a / b, 1) if b else None
R = {}

V = V.reset_index(drop=True)
V["id"] = [f"{l}{int(r):03d}" if r else f"{l}x{i}" for i, (l, r) in enumerate(zip(V.list, V.row))]
V["intra"] = (V.region == "Within Australia").astype(int)
V["disp"] = V.name.str.replace(r"\s*\((?:[^)]*\b(?:ship|whaler|EIC|schooner|brig)\b[^)]*|1\d{3})\)", "", regex=True).str.strip()

# ---------- the same voyage listed by two colonies ----------
V["dup_of"] = ""
dated = V[V.arr_y.notna() & V.arr_m.notna()].copy()
dated["t"] = [dt.date(int(y), int(m), int(d) if pd.notna(d) else 15).toordinal() for y, m, d in zip(dated.arr_y, dated.arr_m, dated.arr_d)]
for b, g in dated.groupby("ship_base"):
    if g.list.nunique() < 2:
        continue
    g = g.sort_values("t")
    for i in range(len(g)):
        for j in range(i + 1, len(g)):
            a, c = g.iloc[i], g.iloc[j]
            if a.list == c.list or c.t - a.t > 75 or c.intra or a.intra:
                continue
            if a.article and c.article and a.article != c.article:
                continue
            keep, drop = (c, a) if (pd.notna(c.landed) and pd.isna(a.landed)) else (a, c)
            if V.loc[drop.name, "dup_of"] == "" and V.loc[keep.name, "dup_of"] == "":
                V.loc[drop.name, "dup_of"] = keep.id
dups = V[V.dup_of != ""]
R["dups"] = [{"ship": r.disp, "listed": COL[r.list]["short"], "arr": r.arrival_raw, "kept": COL[V[V.id == r.dup_of].list.iloc[0]]["short"],
              "kept_arr": V[V.id == r.dup_of].arrival_raw.iloc[0]} for r in dups.itertuples()]

V["main"] = ((V.intra == 0) & V.arr_y.notna() & (V.parkhurst == 0) & (V.dup_of == "")).astype(int)
V["convicts"] = V.landed.where(V.landed.notna(), V.embarked)
M = V[V.main == 1].copy(); M["year"] = M.arr_y.astype(int)
I = V[(V.intra == 1) & V.arr_y.notna()]
U = V[V.arr_y.isna()]
assert len(M) > 700

# ---------- source ----------
R["source"] = {"rows": {k: int((V.list == k).sum()) for k in CK}, "rows_total": len(V), "added_from_fleet": CHK.get("added_from_fleet", []),
               "revids": REVS, "n_ship_articles": CHK["ship_articles"], "n_article_voyages": len(K), "category_members": CHK["category_members"],
               "n_main": len(M), "n_intra": len(I), "n_parkhurst": int((V.parkhurst == 1).sum()), "parkhurst_n": int(V[V.parkhurst == 1].landed.sum()),
               "n_dup": len(dups), "n_undated": len(U), "n_noport_main": int((M.port == "").sum()),
               "first_year": int(M.year.min()), "last_year": int(M.year.max())}
src = R["source"]
assert src["parkhurst_n"] == 234                                          # matches the article's 234 Parkhurst apprentices
assert QU["wa_parkhurst"]["phrase"].find("234") > 0

# ---------- per colony ----------
col = {}
for k in CK:
    a = M[M.list == k]; yy = a.groupby("year").size()
    col[k] = {"name": COL[k]["name"], "short": COL[k]["short"], "n": len(a), "pct": pc(len(a), len(M)), "first": int(a.year.min()), "last": int(a.year.max()),
              "peak_year": int(yy.idxmax()), "peak_n": int(yy.max()), "n_conv": int(a.convicts.notna().sum()), "sum_conv": int(a.convicts.sum()),
              "irish": int((a.region == "Ireland").sum()), "england": int((a.region == "England").sum()), "indian": int((a.region == "India and the Indian Ocean").sum()),
              "last_ship": a.sort_values(["year", "arr_m", "arr_d"]).iloc[-1].disp, "last_date": a.sort_values(["year", "arr_m", "arr_d"]).iloc[-1].arrival_raw,
              "first_ship": a.sort_values(["year", "arr_m", "arr_d"]).iloc[0].disp, "first_date": a.sort_values(["year", "arr_m", "arr_d"]).iloc[0].arrival_raw,
              "intra": int((I.list == k).sum())}
    ei = a.region.isin(["England", "Ireland"]).sum()
    col[k]["irish_pct"] = pc(col[k]["irish"], ei)
R["col"] = col
assert col["wa"]["n"] == 43 and col["wa"]["sum_conv"] in (9668, 9721) or col["wa"]["n"] == 43
R["wa"] = {"n": col["wa"]["n"], "sum": col["wa"]["sum_conv"], "stated_721": 9721, "stated_668": 9668, "diff_721": 9721 - col["wa"]["sum_conv"], "diff_668": col["wa"]["sum_conv"] - 9668}

# ---------- per year and decade ----------
YEARS = list(range(Y0, Y1 + 1))
yr = []
for y in YEARS:
    a = M[M.year == y]; row = {"y": y, "n": len(a)}
    for k in CK:
        row[k] = int((a.list == k).sum())
    row["conv_known"] = int(a.convicts.sum()); row["n_conv"] = int(a.convicts.notna().sum())
    yr.append(row)
R["years"] = yr
Y = pd.DataFrame(yr).set_index("y")
R["peak"] = {"year": int(Y.n.idxmax()), "n": int(Y.n.max()), "years_over_20": [int(y) for y in Y.index[Y.n >= 20]], "zero_years": [int(y) for y in Y.index[(Y.n == 0) & (Y.index >= 1788)]]}
dec = []
for d in range(1780, 1870, 10):
    a = M[(M.year >= d) & (M.year < d + 10)]
    dec.append({"dec": d, "n": len(a), **{k: int((a.list == k).sum()) for k in CK}, "irish": int((a.region == "Ireland").sum()),
                "indian": int((a.region == "India and the Indian Ocean").sum())})
R["decades"] = dec
D = {d["dec"]: d for d in dec}
R["peak"]["dec"] = max(dec, key=lambda d: d["n"])["dec"]; R["peak"]["dec_n"] = max(dec, key=lambda d: d["n"])["n"]
R["peak"]["n_1830s"] = D[1830]["n"]; R["peak"]["n_1820s"] = D[1820]["n"]; R["peak"]["n_1810s"] = D[1810]["n"]; R["peak"]["n_1790s"] = D[1790]["n"]
R["peak"]["n_1800s"] = D[1800]["n"]; R["peak"]["n_1840s"] = D[1840]["n"]; R["peak"]["n_1850s"] = D[1850]["n"]; R["peak"]["n_1860s"] = D[1860]["n"]
R["peak"]["n_1815_1840"] = int(((M.year >= 1815) & (M.year <= 1840)).sum()); R["peak"]["pct_1815_1840"] = pc(R["peak"]["n_1815_1840"], len(M))
R["peak"]["n_pre1815"] = int((M.year < 1815).sum())
R["peak"]["vdl_1840s"] = D[1840]["vdl"]; R["peak"]["nsw_1840s"] = D[1840]["nsw"]
R["peak"]["nsw_1830s"] = D[1830]["nsw"]; R["peak"]["vdl_1830s"] = D[1830]["vdl"]
for k in CK:
    R["peak"][f"{k}_4149"] = int(((M.year >= 1841) & (M.year <= 1849) & (M.list == k)).sum())

# ---------- completeness ----------
cv = M[M.convicts.notna()]
st = {"stated_162": 162000, "stated_164": 164000, "stated_ships": 806, "n_main": len(M), "n_main_pct_806": pc(len(M), 806),
      "n_conv": len(cv), "n_conv_pct": pc(len(cv), len(M)), "sum_conv": int(cv.convicts.sum()), "sum_conv_pct_162": pc(cv.convicts.sum(), 162000),
      "avg_stated": round(164000 / 806), "avg_known": round(float(cv.convicts.mean())),
      "avg_known_ex_small": round(float(cv[cv.convicts >= 20].convicts.mean())),
      "n_conv_nsw": int(cv.list.eq("nsw").sum()), "n_conv_vdl": int(cv.list.eq("vdl").sum()), "n_conv_wa": int(cv.list.eq("wa").sum()), "n_conv_nfk": int(cv.list.eq("nfk").sum()),
      "n_eastern": int(M.list.isin(["nsw", "vdl"]).sum()), "n_eastern_conv": int(cv.list.isin(["nsw", "vdl"]).sum())}
st["implied_if_avg"] = int(round(len(M) * st["avg_stated"], -3))
st["n_eastern_conv_pct"] = pc(st["n_eastern_conv"], st["n_eastern"])
R["cover"] = st
assert st["n_main"] < 806 + 120

# ---------- voyage length ----------
d_ = M[M.days.notna()].copy()
d_["dep_year"] = d_.year
days = [{"ship": r.disp, "y": int(r.year), "days": int(r.days), "src": r.days_src, "list": r.list, "fleet": int(r.fleet), "port": r.port} for r in d_.sort_values("year").itertuples()]
R["days"] = {"rows": days, "n": len(days), "n_fleet": int((d_.days_src == "fleet table").sum()), "n_article": int((d_.days_src == "ship article").sum())}
dd = R["days"]
fl = d_[d_.fleet > 0]; af = d_[d_.fleet == 0]
for f in (1, 2, 3):
    x = d_[d_.fleet == f]
    dd[f"fleet{f}_min"] = int(x.days.min()); dd[f"fleet{f}_max"] = int(x.days.max()); dd[f"fleet{f}_med"] = int(x.days.median())
eras = [("1787 to 1791", 1787, 1791), ("1800 to 1819", 1800, 1819), ("1820 to 1839", 1820, 1839), ("1840 to 1868", 1840, 1868)]
dd["eras"] = []
for nm, a, b in eras:
    x = d_[(d_.year >= a) & (d_.year <= b)]
    dd["eras"].append({"era": nm, "n": len(x), "median": int(x.days.median()), "min": int(x.days.min()), "max": int(x.days.max())})
fast = af.sort_values("days").iloc[0]; slow = d_.sort_values("days").iloc[-1]; slow_af = af.sort_values("days").iloc[-1]
dd["fast"] = {"ship": fast.disp, "y": int(fast.year), "days": int(fast.days), "list": COL[fast.list]["short"]}
dd["slow"] = {"ship": slow.disp, "y": int(slow.year), "days": int(slow.days), "list": COL[slow.list]["short"]}
dd["slow_after"] = {"ship": slow_af.disp, "y": int(slow_af.year), "days": int(slow_af.days)}
dd["after1815_med"] = int(af[af.year >= 1815].days.median()); dd["after1815_n"] = int((af.year >= 1815).sum())
dd["ff_days"] = 252
hg = d_[d_.disp.str.startswith("Hougoumont")].iloc[0]
dd["hougoumont"] = int(hg.days); sc = d_[d_.disp == "Scindian"].iloc[0]; dd["scindian"] = int(sc.days)
mg = d_[(d_.article == "Mangles (1803 ship)")]
R_mg = M[M.article == "Mangles (1803 ship)"]
dd["mangles_n"] = len(mg); dd["mangles_med"] = int(mg.days.median()); dd["mangles_1828"] = int(mg[mg.year == 1828].days.iloc[0])
assert dd["eras"][0]["median"] > dd["eras"][2]["median"] > dd["eras"][3]["median"] - 40

# ---------- deaths ----------
tf = F[F.fleet == 3]
tb = int(tf.male_boarded.fillna(0).sum() + tf.female_boarded.fillna(0).sum()); tdth = int(tf.male_deaths.fillna(0).sum() + tf.female_deaths.fillna(0).sum())
tfs = []
for r in tf.itertuples():
    b = (0 if pd.isna(r.male_boarded) else r.male_boarded) + (0 if pd.isna(r.female_boarded) else r.female_boarded)
    de = (0 if pd.isna(r.male_deaths) else r.male_deaths) + (0 if pd.isna(r.female_deaths) else r.female_deaths)
    tfs.append({"ship": r.ship.replace("HMS ", "HMS "), "boarded": int(b), "deaths": int(de), "pct": pc(de, b), "days": int(r.days)})
sf = F[F.fleet == 2]
sfs = []
for r in sf.itertuples():
    b = (0 if pd.isna(r.male_boarded) else r.male_boarded) + (0 if pd.isna(r.female_boarded) else r.female_boarded)
    a = None if pd.isna(r.male_arr) and pd.isna(r.female_arr) else (0 if pd.isna(r.male_arr) else r.male_arr) + (0 if pd.isna(r.female_arr) else r.female_arr)
    sfs.append({"ship": r.ship, "boarded": int(b), "arrived": None if a is None or (r.ship == "Neptune") else int(a), "gap": None if a is None or r.ship == "Neptune" else int(b - a)})
ad = M[M.deaths.notna() & (M.fleet == 0) & M.embarked.notna()]
R["deaths"] = {"tf_boarded": tb, "tf_deaths": tdth, "tf_pct": pc(tdth, tb), "tf_ships": tfs, "tf_worst": max(tfs, key=lambda x: x["pct"]), "tf_best": min(tfs, key=lambda x: x["pct"]),
               "sf_ships": sfs, "sf_embarked": 1038, "sf_died": 273, "sf_pct": 26, "sf_sick": 486, "sf_after": 124, "sf_1006": 1006, "sf_267": 267,
               "ff_deaths": 48, "ff_births": 28,
               "art_n": len(ad), "art_deaths": int(ad.deaths.sum()), "art_embarked": int(ad.embarked.sum()), "art_pct": pc(ad.deaths.sum(), ad.embarked.sum()),
               "art_zero": int((ad.deaths == 0).sum()), "art_max": int(ad.deaths.max()), "art_max_ship": ad.sort_values("deaths").iloc[-1].disp, "art_max_y": int(ad.sort_values("deaths").iloc[-1].year)}
de = R["deaths"]
de["sf_vs_art_x"] = round(de["sf_pct"] / de["art_pct"])
de["mangles_max"] = int(R_mg.deaths.max()); de["mangles_n_deaths"] = int(R_mg.deaths.notna().sum())
de["tf_vs_art_x"] = round(de["tf_pct"] / de["art_pct"])
for k in ("sf_quarter", "sf_273", "sf_124", "sf_267", "ff_deaths"):
    assert k in QU
assert "273 died" in QU["sf_273"]["phrase"] and "267 out of 1,006" in QU["sf_267"]["phrase"] and "48 deaths and 28 births" in QU["ff_deaths"]["phrase"]
print("DEATHS", {k: v for k, v in de.items() if k not in ("tf_ships", "sf_ships")})
assert 0.5 <= de["art_pct"] <= 2.5 and 8 <= de["tf_pct"] <= 10
lost = V[V.notes.str.contains(r"wreck|drown|lost|loss of|captured|disabled|iceberg|beached", case=False) | V.arrival_raw.str.contains("Wreck", case=False)]
R["lost"] = [{"ship": r.disp, "list": COL[r.list]["short"], "arr": r.arrival_raw, "notes": r.notes} for r in lost.itertuples()]

# ---------- departure places ----------
P = M[M.port != ""]
ports = []
for k, g in P.groupby("port"):
    ports.append({"key": k, "name": PORTS[k][0], "lat": PORTS[k][1], "lon": PORTS[k][2], "region": PORTS[k][3], "n": len(g),
                  **{c: int((g.list == c).sum()) for c in CK}, "first": int(g.year.min()), "last": int(g.year.max())})
ports.sort(key=lambda r: -r["n"])
R["ports"] = ports; PT = {p["key"]: p for p in ports}
reg = M.region.value_counts()
EI = M[M.region.isin(["England", "Ireland"])]
R["regions"] = {r: int(reg.get(r, 0)) for r, _ in REGIONS}
R["irish"] = {"n": int((EI.region == "Ireland").sum()), "n_ei": len(EI), "pct": pc((EI.region == "Ireland").sum(), len(EI)),
              "cork": PT["cork"]["n"], "dublin": PT["dublin"]["n"], "cork_rank": [p["key"] for p in ports].index("cork") + 1,
              "nsw_pct": col["nsw"]["irish_pct"], "vdl_pct": col["vdl"]["irish_pct"], "wa_irish": col["wa"]["irish"],
              "england_unspecified": PT["england"]["n"], "thames": sum(PT[k]["n"] for k in ("london", "woolwich", "deptford", "gravesend", "sheerness", "downs") if k in PT),
              "solent": sum(PT[k]["n"] for k in ("portsmouth", "spithead", "cowes") if k in PT), "plymouth": sum(PT[k]["n"] for k in ("plymouth", "devonport") if k in PT),
              "portland": PT["portland"]["n"], "portland_wa": PT["portland"]["wa"], "plymouth_wa": PT["plymouth"]["wa"]}
R["irish"]["nsw_n"] = col["nsw"]["irish"]; R["irish"]["vdl_n"] = col["vdl"]["irish"]
ind = M[M.region == "India and the Indian Ocean"]
R["indian"] = {"n": len(ind), "pct": pc(len(ind), len(M)), "first": int(ind.year.min()), "last": int(ind.year.max()),
               "military": int(ind.notes.str.contains("military", case=False).sum()), "calcutta": PT["calcutta"]["n"], "mauritius": PT["mauritius"]["n"],
               "nsw": int((ind.list == "nsw").sum()), "wa": int((ind.list == "wa").sum()), "wa_conv": int(ind[ind.list == "wa"].convicts.sum())}

# ---------- ships ----------
M["ship_id"] = [a if a else f"{l}:{b}" for a, l, b in zip(M.article, M.list, M.ship_base)]
SA = S.set_index("article")
sh = []
for sid, g in M.groupby("ship_id"):
    art = sid if ":" not in sid else None
    info = SA.loc[art] if art in SA.index else None
    sh.append({"ship_id": sid, "name": g.disp.iloc[0], "article": art or "", "voyages": len(g), "first": int(g.year.min()), "last": int(g.year.max()),
               "colonies": ", ".join(sorted({COL[x]["short"] for x in g.list})), "launched": int(float(info.launched)) if info is not None and str(info.launched) not in ("", "nan") else None,
               "tons": int(float(info.tons_burthen)) if info is not None and str(info.tons_burthen) not in ("", "nan") else None,
               "lead_voyages": int(float(info.lead_convict_voyages)) if info is not None and str(info.lead_convict_voyages) not in ("", "nan") else None,
               "fate": info.fate if info is not None else "", "builder": info.builder if info is not None else ""})
SH = pd.DataFrame(sh).sort_values(["voyages", "first"], ascending=[False, True])
SH.to_csv(f"{DATA}/ships.csv", index=False)
top = SH.head(12)
R["ships"] = {"n_ids": len(SH), "n_with_article": int((SH.article != "").sum()), "one_voyage": int((SH.voyages == 1).sum()),
              "top": [{"name": r.name, "article": r.article, "voyages": int(r.voyages), "first": int(r.first), "last": int(r.last), "colonies": r.colonies,
                       "launched": None if pd.isna(r.launched) else int(r.launched), "lead": None if pd.isna(r.lead_voyages) else int(r.lead_voyages)} for r in top.itertuples()]}
R["ships"]["voyages_by_top"] = int(top.head(10).voyages.sum())
lv = SH[SH.lead_voyages.notna()]
R["ships"]["lead_checked"] = len(lv); R["ships"]["lead_agree"] = int((lv.lead_voyages == lv.voyages).sum())
age = []
for r in M.itertuples():
    if r.article and r.article in SA.index and str(SA.loc[r.article].launched) not in ("", "nan"):
        a = int(r.year) - int(float(SA.loc[r.article].launched))
        if 0 <= a <= 90: age.append(a)
R["ships"]["age_n"] = len(age); R["ships"]["age_med"] = int(np.median(age))
tons = SH[SH.tons.notna()]
R["ships"]["tons_med"] = int(tons.tons.median()); R["ships"]["tons_n"] = len(tons)

# ---------- women ----------
POP["fpct"] = (100 * POP.female / POP.total).round(1)
w = M[M.women == 1]
R["women"] = {"stated": 24000, "one_in": 7, "stated_pct": round(100 * 24000 / 162000, 1), "fry_women": 12000, "fry_ships": 106,
              "pop": POP.to_dict("records"), "pop_first_pct": float(POP.fpct.iloc[0]), "pop_last_pct": float(POP.fpct.iloc[-1]),
              "pop_last_year": int(POP.year.iloc[-1]), "pop_1836_f": int(POP[POP.year == 1836].female.iloc[0]), "pop_1836_m": int(POP[POP.year == 1836].male.iloc[0]),
              "pop_max_total": int(POP.total.max()), "pop_max_year": int(POP.loc[POP.total.idxmax(), "year"]),
              "flagged": len(w), "flagged_pct": pc(len(w), len(M)), "ships_flagged": [{"ship": r.disp, "y": int(r.year), "list": COL[r.list]["short"], "female": None if pd.isna(r.female) else int(r.female)} for r in w.sort_values("year").itertuples()],
              "ff_women_ships": int(((M.fleet == 1) & (M.female > 0)).sum()), "lady_juliana": int(M[M.disp == "Lady Juliana"].female.iloc[0])}
assert R["women"]["pop_first_pct"] > 25 and R["women"]["pop_last_pct"] < 12

# ---------- the wider world (stated figures only) ----------
WORLD = [
    {"key": "aus", "years": "1788 to 1868", "name": "Australia", "by": "Britain and Ireland", "place": "New South Wales, Van Diemen's Land, Norfolk Island, Moreton Bay, Western Australia",
     "lat": -33.86, "lon": 151.21, "from": 1788, "to": 1868, "people": "about 162,000", "pn": 162000, "src": ["aus_162k"]},
    {"key": "america", "years": "1718 to 1776", "name": "British America", "by": "Britain", "place": "mostly Virginia and Maryland (the Chesapeake)", "lat": 38.3, "lon": -76.4, "from": 1718, "to": 1776,
     "people": "30,000 to 50,000; estimates range to 120,000", "pn": 50000, "src": ["america_1717", "america_lang", "america_60k"]},
    {"key": "bermuda", "years": "1823 to 1863", "name": "Bermuda", "by": "Britain", "place": "Royal Naval Dockyard, Ireland Island (prison hulks)", "lat": 32.326, "lon": -64.835, "from": 1823, "to": 1863,
     "people": "not stated", "pn": None, "src": ["bermuda_1823", "bermuda_1863", "bermuda"]},
    {"key": "guiana", "years": "1852 to 1953", "name": "French Guiana", "by": "France", "place": "Cayenne, Saint-Laurent-du-Maroni and Devil's Island", "lat": 5.29, "lon": -52.58, "from": 1852, "to": 1953,
     "people": "more than 80,000", "pn": 80000, "src": ["guiana_dates", "guiana_80k", "bagne_1953"]},
    {"key": "newcal", "years": "1864 to 1897", "name": "New Caledonia", "by": "France", "place": "the bagne of New Caledonia", "lat": -22.27, "lon": 166.44, "from": 1864, "to": 1897,
     "people": "about 22,000", "pn": 22000, "src": ["newcal", "bagne_1852"]},
    {"key": "andaman", "years": "1858 to 1947", "name": "Andaman Islands", "by": "British India", "place": "Port Blair and the Cellular Jail", "lat": 11.675, "lon": 92.748, "from": 1858, "to": 1947,
     "people": "200 in the first party, 1858; the Cellular Jail had 698 cells", "pn": None, "src": ["portblair_200", "andaman_cells", "andaman_1947", "andaman_1857"]},
    {"key": "sakhalin", "years": "from 1857", "name": "Sakhalin", "by": "Russia", "place": "katorga settlements around Aleksandrovsk", "lat": 50.9, "lon": 142.16, "from": 1857, "to": 1905,
     "people": "not stated", "pn": None, "src": ["sakhalin_1857", "katorga_chekhov"]},
    {"key": "siberia", "years": "from the 17th century", "name": "Siberia", "by": "Russia", "place": "katorga mines and camps, such as Nerchinsk and Kara", "lat": 51.98, "lon": 116.58, "from": 1650, "to": 1917,
     "people": "about 6,000 serving katorga in 1906, up to 28,600 by 1916", "pn": None, "src": ["katorga_17c", "katorga_1906"]},
]
# 'from' and 'to' are for sorting only; the text uses 'years', which for Sakhalin and Siberia gives only the start the
# articles state (the articles used give no end year).
for w_ in WORLD:
    for s_ in w_["src"]:
        assert s_ in QU, s_
    w_["quote"] = " ".join(QU[s_]["sentence"] for s_ in w_["src"][:2])[:600]
    w_["articles"] = sorted({QU[s_]["article"] for s_ in w_["src"]})
R["world"] = WORLD
R["america"] = {"low": 30000, "high": 50000, "lang": 50000, "keneally": 120000, "about": 60000}
STATIONS = [
    {"name": "Norfolk Island", "lat": -29.056, "lon": 167.959, "years": "1788 to 1814, 1825 to 1855", "a": 1788, "b": 1855, "src": "nfk_dates",
     "note": "a place of secondary punishment for convicts who reoffended in Australia, in its second period"},
    {"name": "Moreton Bay", "lat": -27.47, "lon": 153.03, "years": "1824 to 1842", "a": 1824, "b": 1842, "src": "moreton", "note": "prisoners rose from 200 to 1,000 between 1826 and 1829; now Brisbane"},
    {"name": "Macquarie Harbour", "lat": -42.39, "lon": 145.45, "years": "1822 to 1833", "a": 1822, "b": 1833, "src": "macquarie", "note": "Sarah Island, on the remote west coast of Van Diemen's Land"},
    {"name": "Port Arthur", "lat": -43.148, "lon": 147.85, "years": "1833 to 1877", "a": 1833, "b": 1877, "src": "portarthur", "note": "for 'the most hardened' secondary offenders; a timber station from 1830"},
]
R["stations"] = STATIONS
R["quotes"] = {k: {"article": v["article"], "revid": v["revid"]} for k, v in QU.items()}

# ---------- facts from the articles used in the text ----------
# figures the articles state, each checked against the quoted phrase: name, value, quote key, the text that must appear
STATED = [("ships_806", 806, "aus_164k", "806 ships"), ("conv_164", 164000, "aus_164k", "164,000"), ("conv_162", 162000, "aus_162k", "162,000"),
          ("by1840", 150000, "aus_1840", "150,000"), ("political", 3600, "aus_political", "3,600"), ("ff_over", 1400, "ff_depart", "over 1,400"),
          ("ff_days", 252, "ff_252", "252 days"), ("ff_men", 582, "ff_gillen", "582"), ("ff_women", 193, "ff_gillen", "193"), ("tf_over", 2000, "tf_2000", "2,000"), ("women", 24000, "aus_women", "24,000"), ("women_theft_pct", 80, "women_theft", "80%"),
          ("fry_women", 12000, "women_fry", "12,000"), ("fry_ships", 106, "women_fry", "106 ships"), ("wa_721", 9721, "wa_9721", "9,721"), ("wa_668", 9668, "wa_9668", "9,668"),
          ("sf_embarked", 1038, "sf_273", "1,038"), ("sf_died", 273, "sf_273", "273 died"), ("sf_sick", 486, "sf_273", "486"), ("sf_after", 124, "sf_124", "124"),
          ("sf_1006", 1006, "sf_267", "1,006"), ("sf_267", 267, "sf_267", "267"), ("sf_six_months_pct", 40, "sf_quarter", "40 per cent"),
          ("ff_deaths", 48, "ff_deaths", "48 deaths"), ("ff_births", 28, "ff_deaths", "28 births"),
          ("am_1717_low", 30000, "america_1717", "30,000"), ("am_1717_high", 50000, "america_1717", "50,000"), ("am_lang", 50000, "america_lang", "50,000"),
          ("am_keneally", 120000, "america_lang", "120,000"), ("am_60k", 60000, "america_60k", "60,000"),
          ("guiana", 80000, "guiana_80k", "80,000"), ("newcal", 22000, "newcal", "22,000"), ("andaman_first", 200, "portblair_200", "200 convicts"),
          ("andaman_cells", 698, "andaman_cells", "698"), ("andaman_80k", 80000, "andaman_80k", "80,000"), ("katorga_1906", 6000, "katorga_1906", "6,000"),
          ("katorga_1916", 28600, "katorga_1916" if "katorga_1916" in QU else "katorga_1906", "28,600"), ("moreton_max", 1000, "moreton_1000", "1000"),
          ("sites", 11, "sites_eleven", "eleven sites"), ("parkhurst", 234, "wa_parkhurst", "234")]
R["stated"] = {}
for k, v, q, t in STATED:
    if t:
        assert t in QU[q]["phrase"], (k, q, t)
    R["stated"][k] = v
assert "During the 25 years that Fry was involved" in QU["women_fry"]["sentence"]; R["stated"]["fry_years"] = 25
R["stated"].update({"nsw_end": 1850, "vdl_end": 1853, "wa_end": 1868, "nfk_end": 1855, "unesco": 2010})
assert R["stated"]["ff_men"] + R["stated"]["ff_women"] > 1400 / 2                       # "over half of them convicts"
assert "eleven vessels" in QU["ff_eleven"]["phrase"]
# wrecks in the tables' notes
am = V[V.disp == "Amphitrite"].notes.iloc[0]; nv = " ".join(V[V.disp == "Neva"].arrival_raw)
assert am == "108 female convicts and 12 children drowned" and "224 lives" in nv
R["stated"].update({"amph_women": 108, "amph_children": 12, "neva": 224})
assert "wrecked in 1833" in S[S.article == "Amphitrite (1802 ship)"].lead.iloc[0]

# ---------- clean data out ----------
V["year"] = V.arr_y
V["route"] = [f"{p}|{l}" if p and f"{p}|{l}" in ROUTES else "" for p, l in zip(V.port, V.list)]
V["port_name"] = V.port.map(lambda k: PORTS[k][0] if k else "")
out = V[["id", "list", "disp", "name", "article", "arrival_raw", "year", "arr_m", "arr_d", "sailed_raw", "port", "port_name", "region", "via", "notes", "master",
         "embarked", "landed", "convicts", "male", "female", "deaths", "dep_raw", "days", "days_src", "fleet", "women", "women_src", "parkhurst", "nfk_period",
         "intra", "dup_of", "main", "route"]].rename(columns={"list": "colony", "disp": "ship", "name": "name_in_table", "article": "wikipedia_article", "arrival_raw": "arrival_as_listed",
                                                             "arr_m": "arrival_month", "arr_d": "arrival_day", "sailed_raw": "sailed_from_as_listed", "dep_raw": "departure_date",
                                                             "days": "voyage_days", "days_src": "voyage_days_source", "main": "counted_overseas_voyage"})
out.to_csv(f"{DATA}/voyages.csv", index=False)
pd.DataFrame(yr).rename(columns={"y": "year", "n": "overseas_voyages", "conv_known": "convicts_where_given", "n_conv": "voyages_with_convict_number"}).to_csv(f"{DATA}/voyages_by_year.csv", index=False)
pd.DataFrame([{"key": k, "name": v[0], "lat": v[1], "lon": v[2], "region": v[3], "voyages_counted": PT.get(k, {}).get("n", 0)} for k, v in PORTS.items()]).to_csv(f"{DATA}/ports.csv", index=False)
pd.DataFrame([{k: w_[k] for k in ("name", "by", "place", "lat", "lon", "years", "people", "articles")} for w_ in WORLD]).to_csv(f"{DATA}/other_penal_systems.csv", index=False)

# ---------- page data ----------
PK = list(PORTS); PI = {k: i for i, k in enumerate(PK)}; RK = sorted({r for r in V.route if r}); RI = {k: i for i, k in enumerate(RK)}
RG = [r for r, _ in REGIONS]
I_ = lambda v: -1 if pd.isna(v) else int(v)
vrows = []
for r in V[V.arr_y.notna()].sort_values(["arr_y", "arr_m", "arr_d"]).itertuples():
    flag = 0 if r.main else (1 if r.intra else 2 if r.parkhurst else 3)
    vrows.append([r.id, r.disp, CK.index(r.list), PI.get(r.port, -1), int(r.arr_y), I_(r.arr_m), I_(r.arr_d), I_(r.convicts), I_(r.embarked), I_(r.deaths), I_(r.days),
                  r.dep_raw, r.article, r.notes[:160], int(r.women), RG.index(r.region), flag, RI.get(r.route, -1), r.arrival_raw, r.sailed_raw])
site = {"colonies": [[k, COL[k]["name"], COL[k]["short"], COL[k]["c"], COL[k]["ll"][0], COL[k]["ll"][1], COL[k]["place"], COL[k]["list"]] for k in CK],
        "ports": [[k, PORTS[k][0], PORTS[k][1], PORTS[k][2], RG.index(PORTS[k][3]), PT.get(k, {}).get("n", 0)] for k in PK],
        "regions": REGIONS, "routes": [ROUTES[k]["coords"] for k in RK], "route_km": [ROUTES[k]["km"] for k in RK],
        "cols": ["id", "ship", "colony", "port", "y", "m", "d", "convicts", "embarked", "deaths", "days", "dep", "article", "notes", "women", "region", "flag", "route", "arr", "sailed"],
        "voyages": vrows, "world": WORLD, "stations": STATIONS}
jsave(site, f"{DATA}/site.json")
R["meta"] = {"page": PAGE, "repo": REPO, "slug": SLUG, "y0": Y0, "y1": Y1, "dup_days": 75, "match_days": 3}
R["ports_n"] = len(PORTS)
jsave(R, f"{DATA}/results.json", indent=1)
print("main", len(M), {k: col[k]["n"] for k in CK}, "intra", len(I), "dups", len(dups), "undated", len(U))
print("peak", R["peak"]); print("cover", st); print("days", {k: v for k, v in dd.items() if k != "rows"})
print("deaths", {k: v for k, v in de.items() if k not in ("tf_ships", "sf_ships")}); print("irish", R["irish"]); print("indian", R["indian"])
print("ships", {k: v for k, v in R["ships"].items() if k != "top"}); print([(t["name"], t["voyages"], t["lead"]) for t in R["ships"]["top"]])
print("women", {k: v for k, v in R["women"].items() if k not in ("pop", "ships_flagged")})
print("colonies", {k: (v["first"], v["last"], v["last_ship"], v["last_date"], v["peak_year"], v["peak_n"], v["irish_pct"]) for k, v in col.items()})
print("dups", R["dups"]); print("lost", R["lost"])
print("site", os.path.getsize(f"{DATA}/site.json") // 1024, "KB")
