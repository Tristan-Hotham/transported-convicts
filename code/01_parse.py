"""Step 1. Parse the Wikipedia voyage tables and context articles in raw/ into clean tables in data/source_tables/
(CC BY-SA 4.0, derived from Wikipedia) and the quoted facts in data/source_quotes.json. This is the only step that reads
raw/; every later step reads data/ only.

Voyage tables (one row per listed voyage):
  * New South Wales and Tasmania: Name, Date of arrival, Sailed from, Notes. The ship's Wikipedia article is taken from
    the link in the Name cell; a later row for the same name without a link (a ship's second or third voyage, listed
    straight after the first) inherits it. No convict numbers, departure dates or deaths are given in these tables.
  * Norfolk Island: two arrival tables (1788 to 1804 from Sydney; 1840 to 1850 direct from Britain and Ireland), with
    convicts embarked and landed; a third table of removals from the island (1807 to 1813) is kept as a source table.
  * Western Australia: Parkhurst apprentices (1842 to 1849) and convict voyages (1850 to 1868), with numbers.
  * First, Second and Third Fleet articles: departure and arrival dates, voyage length and convicts per ship (and, for
    the Third Fleet, deaths), matched to the New South Wales rows by ship and year.
Ship articles: the infobox (launched, tons burthen, builder, fate) and lead of 305 ship articles; and, for the convict
ships whose full article is in the search dump, sentences giving a departure date, an arrival date, convicts embarked
and convict deaths. These are kept only where the article's arrival date is within three days of a table row for the
same ship, and the sentence is stored with each value.
Quoted facts: each is an exact phrase that must appear in the named article's text; the sentence and revision id are
stored."""
import html as _html
import pandas as pd
from bs4 import BeautifulSoup
from common import *

L = jload(f"{RAW}/convicts_lists.json")
W = jload(f"{RAW}/convicts_wiki.json")
REV = {k[6:]: v["revid"] for k, v in L.items() if k.startswith("parse:")}


def soup(title):
    s = BeautifulSoup(L["parse:" + title]["html"], "lxml")
    for x in s.select("sup.reference, style, .mw-editsection"):
        x.decompose()
    return s


def ctext(c):
    return re.sub(r"\s+", " ", c.get_text(" ", strip=True).replace("\xa0", " ")).strip()


def ptext(title):
    s = soup(title)
    for x in s.select("table.navbox, .navbox, .reflist, .references, .mw-references-wrap"):
        x.decompose()
    return re.sub(r"\s+", " ", s.get_text(" ").replace("\xa0", " "))


def wikitext(title):
    for p in W[title]["pages"].values():
        return p["revisions"][0]["slots"]["main"]["*"]


def wclean(w):
    w = re.sub(r"<ref[^>]*/>", "", w); w = re.sub(r"<ref.*?</ref>", "", w, flags=re.S)
    w = re.sub(r"\{\{sfnp?\|[^{}]*\}\}", "", w)
    w = re.sub(r"\{\{(?:ship|HMS|Ship|HMAT|HMT)\|([^{}|]*)\|([^{}|]*)(?:\|[^{}]*)?\}\}", r"\1 \2", w)
    w = re.sub(r"\{\{convert\|([\d.]+)\|(\w+)[^{}]*\}\}", r"\1 \2", w)
    w = re.sub(r"\{\{frac\|(\d+)\|(\d+)\}\}", r" \1/\2", w)
    for _ in range(5):
        w = re.sub(r"\{\{[^{}]*\}\}", "", w)
    w = re.sub(r"\[\[(?:File|Image):[^\]]*\]\]", "", w)
    w = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", w); w = re.sub(r"'{2,}", "", w)
    w = _html.unescape(w).replace("&nbsp;", " ")
    return re.sub(r"\s+", " ", w)


def first_int(s):
    m = re.search(r"\d[\d,]*", s or "")
    return int(m.group(0).replace(",", "")) if m else None


def base(name):
    """Ship name without the disambiguation in brackets and without HMS: 'Atlas (1801 Quebec City ship)' -> 'atlas'."""
    n = re.sub(r"\s*\(.*?\)\s*", " ", name)
    n = re.sub(r"^(HMS|HMAT|HM Colonial brig|HM)\s+", "", n.strip())
    return norm(n).replace("st ", "saint ").strip()


chk = {}

# ---------------- New South Wales and Tasmania ----------------
rows = []
for ck in ("nsw", "vdl"):
    s = soup(COL[ck]["list"]); i = 0
    for tb in s.find_all("table", class_="wikitable"):
        hdr = [ctext(c) for c in tb.find_all("tr")[0].find_all(["th", "td"])]
        assert hdr == ["Name", "Date of arrival", "Sailed from", "Notes"], hdr
        prev = None
        for r in tb.find_all("tr")[1:]:
            cs = r.find_all(["td", "th"])
            assert not any(c.get("rowspan") or c.get("colspan") for c in cs)
            t = [ctext(c) for c in cs] + [""] * (4 - len(cs))
            a = cs[0].find("a"); link = None
            if a is not None and "new" not in (a.get("class") or []) and a.get("title"):
                link = a["title"]
            nm = t[0]; b = base(nm)
            if link is None and prev is not None and prev[0] == b and prev[1]:
                link = prev[1]; inh = 1
            else:
                inh = 0
            prev = (b, link)
            i += 1
            rows.append({"list": ck, "row": i, "name": nm, "ship_base": b, "article": link, "article_inherited": inh,
                         "arrival_raw": t[1], "sailed_raw": t[2], "notes": t[3], "master": "", "embarked": None, "landed": None})
    chk[f"rows_{ck}"] = i

# ---------------- Norfolk Island ----------------
s = soup(COL["nfk"]["list"]); tabs = [tb for tb in s.find_all("table") if "wikitable" in (tb.get("class") or [])]
assert len(tabs) == 3
nfk_n = 0
for k, tb in enumerate(tabs):
    tr = tb.find_all("tr"); hdr = [ctext(c) for c in tr[0].find_all(["th", "td"])]
    if k == 1:
        assert hdr[:3] == ["Vessel", "Master", "Date of departure from Norfolk Island"], hdr
        rem = [[ctext(c) for c in r.find_all(["td", "th"])] for r in tr[1:]]
        pd.DataFrame(rem, columns=["vessel", "master", "departed_norfolk", "arrived", "destination", "passengers"]).to_csv(f"{SRC}/norfolk_removals_1807_1813.csv", index=False)
        continue
    assert [h.split(" [")[0] for h in hdr] == ["Vessel", "Master", "Date of arrival", "Sailed from", "Convicts embarked", "Convicts landed"], hdr
    for r in tr[1:]:
        t = [ctext(c) for c in r.find_all(["td", "th"])]
        a = r.find_all(["td", "th"])[0].find("a"); link = a["title"] if a is not None and a.get("title") and "new" not in (a.get("class") or []) else None
        nfk_n += 1
        rows.append({"list": "nfk", "row": nfk_n, "name": t[0], "ship_base": base(t[0]), "article": link, "article_inherited": 0, "arrival_raw": t[2],
                     "sailed_raw": t[3], "notes": ("landed " + t[5] if "+" in t[5] else ""), "master": t[1],
                     "embarked": first_int(t[4]), "landed": first_int(t[5]), "nfk_period": 1 if k == 0 else 2})
chk["rows_nfk"] = nfk_n

# ---------------- Western Australia ----------------
s = soup(COL["wa"]["list"]); tabs = [tb for tb in s.find_all("table") if "wikitable" not in (tb.get("class") or []) and tb.find("th") and ctext(tb.find("th")) == "Ship"]
assert len(tabs) == 2
wa_n = 0
for k, tb in enumerate(tabs):
    tr = tb.find_all("tr"); hdr = [ctext(c) for c in tr[0].find_all(["th", "td"])]
    assert hdr == (["Ship", "Arrival", "Number of Parkhurst apprentices"] if k == 0 else ["Ship", "Origin", "Arrival", "Number of convicts"]), hdr
    for r in tr[1:]:
        cs = r.find_all(["td", "th"]); t = [ctext(c) for c in cs]
        a = cs[0].find("a"); link = a["title"] if a is not None and a.get("title") and "new" not in (a.get("class") or []) else None
        wa_n += 1
        if k == 0:
            rows.append({"list": "wa", "row": wa_n, "name": t[0], "ship_base": base(t[0]), "article": link, "article_inherited": 0, "arrival_raw": t[1], "sailed_raw": "England",
                         "notes": "Parkhurst apprentices (juvenile prisoners, pardoned on arrival and apprenticed)", "master": "", "embarked": None, "landed": first_int(t[2]), "parkhurst": 1})
        else:
            rows.append({"list": "wa", "row": wa_n, "name": t[0], "ship_base": base(t[0]), "article": link, "article_inherited": 0, "arrival_raw": t[2], "sailed_raw": t[1],
                         "notes": "", "master": "", "embarked": None, "landed": first_int(t[3]), "parkhurst": 0})
chk["rows_wa"] = wa_n

V = pd.DataFrame(rows)
for c in ("nfk_period", "parkhurst"):
    V[c] = V[c].fillna(0).astype(int)
for c in ("embarked", "landed"):
    V[c] = V[c].astype("Int64")
dd = V.arrival_raw.map(parse_date)
V["arr_y"] = dd.map(lambda x: x[0]).astype("Int64"); V["arr_m"] = dd.map(lambda x: x[1]).astype("Int64"); V["arr_d"] = dd.map(lambda x: x[2]).astype("Int64")
# Pyramus: '14 December' with no year in the NSW table; its Wikipedia article is not linked, so it stays undated.


# departure place
def sailed(s):
    s0 = s.replace("[ 1 ]", "").replace("[ 2 ]", "").strip()
    if not s0:
        return None, ""
    parts = re.split(r"\s*(?:,\s*via|\bvia\b|&|\band\b|,)\s*", s0)
    key = SAILED.get(norm(parts[0]))
    if key is None:
        key = SAILED.get(norm(s0))
    assert key is not None, s
    return key, ", ".join(p for p in parts[1:] if p)


ss = V.sailed_raw.map(sailed)
V["port"] = ss.map(lambda x: x[0]); V["via"] = ss.map(lambda x: x[1])
V["port"] = V.port.where(V.port.notna(), "")
V["region"] = V.port.map(lambda k: PORTS[k][3] if k else "Not given")
chk["sailed_values"] = V.sailed_raw.value_counts().to_dict()

# ---------------- the three fleets ----------------
FL = []
s = soup("First Fleet"); ff = [tb for tb in s.find_all("table") if "wikitable" in (tb.get("class") or [])]
tr = ff[1].find_all("tr")
assert [ctext(c) for c in tr[1].find_all(["th", "td"])] == ["Males", "Females"]
for r in tr[2:]:
    t = [ctext(c) for c in r.find_all(["td", "th"])]
    FL.append({"fleet": 1, "ship": t[0], "dep": "13 May 1787", "arr": t[5], "days": first_int(t[6]), "male_arr": first_int(t[7]), "female_arr": first_int(t[8]),
               "male_boarded": None, "female_boarded": None, "male_deaths": None, "female_deaths": None, "note": t[7] + " | " + t[8]})
s = soup("Second Fleet (Australia)"); tb = [tb for tb in s.find_all("table") if "wikitable" in (tb.get("class") or [])][0]
for r in tb.find_all("tr")[1:]:
    t = [ctext(c) for c in r.find_all(["td", "th"])]
    if t[0] == "TOTAL":
        continue
    def ab(x):
        m = re.match(r"\s*(\?|\d+|n/a)?\s*\((\d+)\)", x)
        if not m: return None, None
        return (int(m.group(1)) if m.group(1) and m.group(1).isdigit() else None), int(m.group(2))
    ma, mb = ab(t[8]); fa, fb = ab(t[9])
    FL.append({"fleet": 2, "ship": t[0], "dep": t[5], "arr": t[6], "days": first_int(t[7]), "male_arr": ma, "female_arr": fa, "male_boarded": mb, "female_boarded": fb,
               "male_deaths": None, "female_deaths": None, "note": t[8] + " | " + t[9]})
s = soup("Third Fleet (Australia)"); tb = [tb for tb in s.find_all("table") if "wikitable" in (tb.get("class") or [])][0]
for r in tb.find_all("tr")[1:]:
    t = [ctext(c) for c in r.find_all(["td", "th"])]
    if t[0] == "TOTAL":
        continue
    def adb(x):
        m = re.match(r"\s*(\d+)\s*\[(\d+|-)\]\s*\((\d+)\)", x)
        if not m: return None, None, None
        return int(m.group(1)), (0 if m.group(2) == "-" else int(m.group(2))), int(m.group(3))
    ma, md, mb = adb(t[5]); fa, fd, fb = adb(t[6])
    FL.append({"fleet": 3, "ship": re.sub(r"\s*\(.*", "", t[0]), "dep": t[2], "arr": t[3], "days": first_int(t[4]), "male_arr": ma, "female_arr": fa, "male_boarded": mb,
               "female_boarded": fb, "male_deaths": md, "female_deaths": fd, "note": t[5] + " | " + t[6]})
F = pd.DataFrame(FL)
F.to_csv(f"{SRC}/fleet_ships.csv", index=False)
assert len(F) == 6 + 6 + 11, len(F)
# match to the NSW rows: same ship name, arrival in the fleet's year
FY = {1: 1788, 2: 1790, 3: 1791}
V["fleet"] = 0
for c in ("dep_raw", "days_src", "src_sentence"):
    V[c] = ""
V["days"] = pd.Series([None] * len(V), dtype="Int64")
for c in ("male", "female", "deaths", "boarded"):
    V[c] = pd.Series([None] * len(V), dtype="Int64")
fm = 0
for f in FL:
    b = base(f["ship"].replace("HMS ", ""))
    m = V[(V.list == "nsw") & (V.ship_base == b) & (V.arr_y == FY[f["fleet"]])]
    if f["ship"] in ("Guardian", "Justinian"):
        continue   # Guardian was disabled on the way and is listed without an arrival; Justinian was a storeship
    if len(m) == 0:   # a fleet ship missing from the NSW list (Prince of Wales, First Fleet): added from the fleet article
        assert f["ship"] == "Prince of Wales", f["ship"]
        i = V.index.max() + 1
        V.loc[i] = {c: None for c in V.columns}
        V.loc[i, ["list", "row", "name", "ship_base", "article", "article_inherited", "arrival_raw", "sailed_raw", "notes", "master", "port", "via", "region", "nfk_period", "parkhurst"]] = \
            ["nsw", 0, "Prince of Wales", b, None, 0, "26 January 1788", "Portsmouth", "Part of First Fleet (not in the New South Wales list; added from the First Fleet article)", "", "portsmouth", "", "England", 0, 0]
        V.loc[i, ["arr_y", "arr_m", "arr_d"]] = [1788, 1, 26]
        V.loc[i, ["dep_raw", "days_src", "src_sentence", "fleet"]] = ["", "", "", 0]
        chk["added_from_fleet"] = [f["ship"]]
        m = V.loc[[i]]
    assert len(m) == 1, (f["ship"], len(m))
    i = m.index[0]; fm += 1
    V.loc[i, "fleet"] = f["fleet"]; V.loc[i, "dep_raw"] = f["dep"]; V.loc[i, "days"] = f["days"]; V.loc[i, "days_src"] = "fleet table"
    tot = lambda a, b: None if a is None and b is None else (a or 0) + (b or 0)
    if f["male_arr"] is not None or f["female_arr"] is not None:
        V.loc[i, "landed"] = tot(f["male_arr"], f["female_arr"])
    if f["male_boarded"] is not None or f["female_boarded"] is not None:
        V.loc[i, "boarded"] = tot(f["male_boarded"], f["female_boarded"])
    V.loc[i, "male"] = f["male_arr"] if f["male_arr"] is not None else f["male_boarded"]
    V.loc[i, "female"] = f["female_arr"] if f["female_arr"] is not None else f["female_boarded"]
    if f["male_deaths"] is not None or f["female_deaths"] is not None:
        V.loc[i, "deaths"] = tot(f["male_deaths"], f["female_deaths"])
chk["fleet_matched"] = fm
V["embarked"] = V.embarked.where(V.embarked.notna(), V.boarded)

# ---------------- convict population of New South Wales by sex ----------------
s = soup("Convict women in Australia"); tb = [tb for tb in s.find_all("table") if "wikitable" in (tb.get("class") or [])][0]
pop = []
for r in tb.find_all("tr")[1:]:
    t = [ctext(c) for c in r.find_all(["td", "th"])]
    pop.append({"year": first_int(t[0]), "male": first_int(t[1]), "female": first_int(t[2]), "total": first_int(t[3])})
pd.DataFrame(pop).to_csv(f"{SRC}/nsw_convict_population_by_sex.csv", index=False)
assert all(p["male"] + p["female"] == p["total"] for p in pop)

# ---------------- ship articles: infobox and lead ----------------
SI = L["__shipinfo"]
ships = []
for t, v in SI.items():
    w = v["w"]
    def ib(k):
        m = re.search(r"\|\s*" + k + r"\s*=\s*(.*?)\n\s*\|", w, re.S)
        return wclean(m.group(1)).strip(" ,;") if m else ""
    lead = wclean(w.split("}}\n}}")[-1] if "}}\n}}" in w else w)
    lau = ib("launched"); y = re.search(r"1[6-8]\d\d", lau)
    tons = ib("tons_burthen"); tn = re.search(r"\d[\d,]*", tons)
    nv = None
    m = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d+) (?:voyages?|trips?)[^.]{0,40}?(?:transport\w* convicts|as a convict transport|carrying convicts|convict voyages)", lead)
    if m:
        nv = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12}.get(m.group(1), None) or (int(m.group(1)) if m.group(1).isdigit() else None)
    ships.append({"article": t, "wikidata": v.get("wd"), "revid": v["revid"], "launched_raw": lau, "launched": int(y.group(0)) if y else None,
                  "builder": ib("builder"), "tons_burthen": int(tn.group(0).replace(",", "")) if tn else None, "fate": ib("fate"),
                  "lead_convict_voyages": nv, "lead_convict_voyages_text": m.group(0) if m else "", "lead": lead[:600]})
S = pd.DataFrame(ships)
S.to_csv(f"{SRC}/ship_articles.csv", index=False)
chk["ship_articles"] = len(S)
cats = pd.DataFrame(L["__catmembers"], columns=["category", "member"])
cats.to_csv(f"{SRC}/category_members.csv", index=False)
chk["category_members"] = cats.groupby("category").size().to_dict()

# ---------------- ship articles: voyage details from full articles ----------------
M_ = r"(?:January|February|March|April|May|June|July|August|September|October|November|December)"
DT = r"(\d{1,2} " + M_ + r"(?: \d{4})?|" + M_ + r" \d{1,2}(?:, \d{4})?)"
full = {}
for k, v in W.items():
    if k == "__titles":
        continue
    for p in v["pages"].values():
        try:
            w = p["revisions"][0]["slots"]["main"]["*"]
        except (KeyError, IndexError):
            continue
        if "Category:Convict ships" in w:
            full[p["title"]] = wclean(w)
for t, v in SI.items():
    if t not in full:
        full[t] = wclean(v["w"])
chk["ship_texts"] = len(full)


def pdt(s, y_ctx):
    y, m, d = parse_date(s)
    if y is None:
        mm = re.search(r"(\d{1,2}) (\w+)", s) or re.search(r"(\w+) (\d{1,2})", s)
        a, b = mm.group(1), mm.group(2)
        d, m = (int(a), MONTHS[b.lower()]) if a.isdigit() else (int(b), MONTHS[a.lower()])
        y = y_ctx
    return y, m, d


import datetime as _dt
ART = []
for t, txt in full.items():
    sents = re.split(r"(?<=[.])\s+(?=[A-Z=])", txt); yctx = None
    for i, sx in enumerate(sents):
        ym = re.findall(r"\b(1[78]\d\d)\b", sx)
        md = re.search(r"(?:sailed|left|departed)\b[^.]{0,70}?(?:\bfrom ([A-Z][\w' ]+?))?[^.]{0,40}? on " + DT, sx)
        if not md:
            if ym: yctx = int(ym[-1])
            continue
        mfrom = re.search(r"(?:sailed|left|departed)(?: \w+){0,3}? from (?:the )?([A-Z][\w' ]+?)(?: on|,| in| for| bound|$)", sx) or re.search(r"(?:left|departed) (?:the )?([A-Z][\w']+(?: [A-Z][\w']+)?)", sx)
        dy, dm, ddd = pdt(md.group(2), yctx)
        if not ym:
            pass
        yctx = dy
        win = " ".join(sents[i:i + 4])
        stop = re.search(r"(?<=\.)\s+[^.]*?(?:sailed|left|departed)\b[^.]{0,70}? on " + DT, win[len(sx):]) if len(win) > len(sx) else None
        if stop:
            win = win[:len(sx) + stop.start()]
        ma = re.search(r"(?:arrived|reached|docked|anchored)\b[^.]{0,80}? on " + DT, win[md.end():] if md.end() < len(sx) else win[len(sx):]) or re.search(r"(?:arrived|reached|docked|anchored)\b[^.]{0,80}? on " + DT, win)
        if not ma or dy is None:
            continue
        ay, am, ad = pdt(ma.group(1), dy)
        try:
            d0 = _dt.date(dy, dm, ddd); d1 = _dt.date(ay, am, ad)
        except (TypeError, ValueError):
            continue
        if d1 <= d0:
            d1 = _dt.date(ay + 1, am, ad)
        days = (d1 - d0).days
        if not 50 <= days <= 400:
            continue
        NUM = {"no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
               "eleven": 11, "twelve": 12}
        N_ = r"(no|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|\d+)"
        num = lambda g: NUM.get(g.lower(), int(g) if g.isdigit() else None)
        CV = r"(?:convicts|prisoners)"
        emb2 = re.search(r"embarked (\d+) male and (\d+) female " + CV, win)
        emb = re.search(r"(?:embarked|with|carried|carrying|transported) (\d+) (male |female )?" + CV + r"|(\d+) (male |female )" + CV, win)
        dv = None
        dq2 = re.search(N_ + r" male convicts? and " + N_ + r" female convicts? died", win, re.I)
        dq1 = re.search(N_ + r" (?:male |female )?convicts? (?:deaths?|died)|(?:suffered|with|and|had) " + N_ + r" convict deaths?|" + N_ + r" of whom died|during which time " + N_ + r" convicts? died|had " + N_ + r" deaths en route", win, re.I)
        if dq2:
            dv = num(dq2.group(1)) + num(dq2.group(2))
        elif dq1:
            dv = num(next(x for x in dq1.groups() if x))
        dis = re.search(r"disembarked (\d+)\b(?! at)|landed (\d+)\b(?! at)", win)
        lv = int(next(x for x in dis.groups() if x)) if dis else None
        if emb2:
            ev, mv, fv = int(emb2.group(1)) + int(emb2.group(2)), int(emb2.group(1)), int(emb2.group(2))
        elif emb:
            g = emb.groups(); ev = int(g[0] or g[2]); sx_ = (g[1] or g[3] or "").strip()
            mv = ev if sx_ == "male" else None; fv = ev if sx_ == "female" else None
        else:
            ev = mv = fv = None
        ART.append({"article": t, "dep_from": (mfrom.group(1).strip() if mfrom else ""), "dep": d0.isoformat(), "arr": d1.isoformat(), "days": days,
                    "embarked": ev, "landed": lv, "male": mv, "female": fv, "deaths": dv, "evidence": win[:600]})
A = pd.DataFrame(ART).drop_duplicates(["article", "dep"]).sort_values(["article", "dep"])
chk["article_voyages_found"] = len(A)
# keep those whose arrival matches a table row of the same ship within three days
V["arr_date"] = [(_dt.date(int(y), int(m), int(d)).isoformat() if pd.notna(y) and pd.notna(m) and pd.notna(d) else "") for y, m, d in zip(V.arr_y, V.arr_m, V.arr_d)]
keep = []
for a in A.itertuples():
    ab_ = base(a.article)
    cand = V[((V.article == a.article) | (V.ship_base == ab_)) & (V.arr_date != "")]
    best = None
    for i, r in cand.iterrows():
        gap = abs((_dt.date.fromisoformat(r.arr_date) - _dt.date.fromisoformat(a.arr)).days)
        if gap <= 3 and (best is None or gap < best[1]):
            best = (i, gap)
    if best is None:
        continue
    i = best[0]
    if V.loc[i, "days_src"] in ("fleet table", "ship article"):
        continue   # the fleet table wins; for a second departure sentence (a call at Rio or Tenerife) the first is kept
    keep.append({**a._asdict(), "list": V.loc[i, "list"], "row": int(V.loc[i, "row"]), "table_arrival": V.loc[i, "arrival_raw"], "gap_days": best[1]})
    V.loc[i, "dep_raw"] = a.dep; V.loc[i, "days"] = a.days; V.loc[i, "days_src"] = "ship article"; V.loc[i, "src_sentence"] = a.evidence[:300]
    if pd.isna(V.loc[i, "landed"]) and a.landed is not None and not pd.isna(a.landed): V.loc[i, "landed"] = int(a.landed)
    if pd.isna(V.loc[i, "embarked"]) and a.embarked is not None and not pd.isna(a.embarked): V.loc[i, "embarked"] = int(a.embarked)
    if a.male is not None and not pd.isna(a.male): V.loc[i, "male"] = int(a.male)
    if a.female is not None and not pd.isna(a.female): V.loc[i, "female"] = int(a.female)
    if a.deaths is not None and not pd.isna(a.deaths) and pd.isna(V.loc[i, "deaths"]): V.loc[i, "deaths"] = int(a.deaths)
K = pd.DataFrame(keep).drop(columns=["Index"])
K.to_csv(f"{SRC}/ship_article_voyages.csv", index=False)
chk["article_voyages_matched"] = len(K)

# women: the tables' notes, the fleet tables and ship-article sentences that name female convicts in a given year
V["women_src"] = ""
V.loc[V.female.fillna(0) > 0, "women_src"] = "fleet table or ship article"
V.loc[V.notes.str.contains("female", case=False) & (V.women_src == ""), "women_src"] = "table notes"
fem = []
for t, txt in full.items():
    for sx in re.split(r"(?<=[.])\s+", txt):
        if re.search(r"\bfemale convicts|\bwomen convicts|\bconvict women", sx) and not re.search(r"(?<!fe)male convicts", sx):
            for y in set(int(x) for x in re.findall(r"\b(1[78]\d\d)\b", sx)):
                fem.append((t, y, sx[:300]))
nfem = 0
for t, y, sx in fem:
    c = V[(V.article == t) & (V.arr_y.isin([y, y + 1]))]
    if re.search(r"New South Wales|Port Jackson|Sydney", sx): c = c[c.list == "nsw"]
    if re.search(r"Van Diemen|Hobart|Tasmania", sx): c = c[c.list == "vdl"]
    if len(c) == 1 and V.loc[c.index[0], "women_src"] == "":
        V.loc[c.index[0], "women_src"] = "ship article: " + sx[:200]; nfem += 1
chk["women_from_articles"] = nfem
V["women"] = (V.women_src != "").astype(int)
V.loc[(V.female.notna()) & (V.female == 0), "women"] = 0
V.drop(columns=["boarded"]).to_csv(f"{SRC}/voyage_rows.csv", index=False)
V.drop(columns=["boarded"]).to_pickle(f"{WORK}/voyages.pkl")

# ---------------- quoted facts ----------------
TXT = {t: ptext(t) for t in REV}
WT = {t: wclean(wikitext(t)) for t in ("Devil's Island", "Penal colony", "Port Blair", "Sakhalin", "Gulag", "Andaman Islands", "Hulk (ship type)", "Convict ship")}
Q = [  # key, article, exact phrase that must appear
    ("aus_162k", "Convicts in Australia", "transported about 162,000 convicts from Great Britain and Ireland"),
    ("aus_164k", "Convicts in Australia", "about 164,000 convicts were transported to the Australian colonies between 1788 and 1868 onboard 806 ships"),
    ("aus_women", "Convicts in Australia", "about 24,000 transportees (one in seven) were women"),
    ("aus_political", "Convicts in Australia", "Approximately 3,600 political prisoners were transported"),
    ("aus_1840", "Convicts in Australia", "by which time some 150,000 convicts had been sent to the colonies"),
    ("nsw_end", "Convicts in Australia", "The final transport of convicts to New South Wales occurred in 1850"),
    ("nsw_abolished", "Convict ships to New South Wales", "Transportation to the Colony of New South Wales was finally officially abolished on 1 October 1850"),
    ("vdl_end", "Convicts in Australia", "Transportation to Tasmania ended in 1853"),
    ("vdl_last", "Convict ships to Tasmania", "until 26 May 1853 when St Vincent became the last to arrive"),
    ("vdl_first", "Convict ships to Tasmania", "Indefatigable arrived at Hobart Town in 1812 and was the first vessel to transport convicts to Van Diemen's Land"),
    ("wa_9721", "Convict era of Western Australia", "Between 1850 and 1868, 9,721 convicts were transported to Western Australia on 43 convict ship voyages"),
    ("wa_9668", "Convicts in Australia", "9,668 convicts were transported on 43 convict ships"),
    ("wa_last", "Convicts in Australia", "In 1868, almost two decades after transportation to the eastern colonies had ceased, the last convict ship arrived in Western Australia"),
    ("wa_nowomen", "Convict era of Western Australia", "that no female convicts be transported"),
    ("wa_parkhurst", "List of convict ship voyages to Western Australia", "Between 1842 and 1849, Western Australia accepted 234 Parkhurst apprentices, all males aged between 10 and 21"),
    ("nfk_dates", "Norfolk Island", "The island served as a convict penal settlement from 6 March 1788 until 5 May 1855"),
    ("nfk_nocompil", "Convict ships to Norfolk Island", "There appear to be no compilations of which vessels brought how many convicts from New South Wales to Norfolk Island"),
    ("ff_depart", "First Fleet", "On 13 May 1787, the ships, with over 1,400 convicts , marines , sailors, colonial officials, and free settlers onboard, left Portsmouth"),
    ("ff_deaths", "First Fleet", "reported a total of 48 deaths and 28 births during the voyage"),
    ("ff_252", "First Fleet", "had travelled for 252 days for more than 15,000 miles"),
    ("ff_eora", "First Fleet", "they encountered the Eora people, including the Bidjigal clan"),
    ("sf_quarter", "Second Fleet (Australia)", "Of the 1,006 convicts transported aboard the Fleet, one quarter died during the voyage and around 40 per cent were dead within six months of arrival in Australia"),
    ("sf_273", "Second Fleet (Australia)", "Of the 1,038 convicts embarked, 273 died during the voyage (26%) and 486 (47% of those embarked) landed sick"),
    ("sf_124", "Second Fleet (Australia)", "Of these, 124 died shortly after they had landed"),
    ("sf_fee", "Second Fleet (Australia)", "per head, whether they landed alive or not"),
    ("sf_267", "Convict women in Australia", "in the Second Fleet , 267 out of 1,006 prisoners died at sea"),
    ("tf_2000", "Third Fleet (Australia)", "with more than 2,000 convicts aboard"),
    ("women_fry", "Convict women in Australia", "12,000 women were transported on 106 ships"),
    ("women_six", "Convict women in Australia", "male convicts outnumbered the female convicts six to one"),
    ("frontier", "Penal transportation", "Violent conflict on the Australian frontier between indigenous Australians and the colonists began only months after the First Fleet landed, lasting over a century"),
    ("myall", "Penal transportation", "convicts and ex-convicts also attacked indigenous people in some instances, such as the Myall Creek Massacre"),
    ("hawkesbury", "Penal transportation", "a group of Irish convicts joined the Aboriginal coalition of Eora , Gandangara , Dharug and Tharawal nations in their fight against the colonists"),
    ("america_lang", "Convicts in Australia", "it has been estimated to be 50,000 by John Dunmore Lang and 120,000 by Thomas Keneally"),
    ("america_60k", "Convicts in Australia", "About 60,000 convicts were transported to the British colonies in North America"),
    ("america_1717", "Transportation Act 1717", "It is commonly accepted that 30,000 convicts (women, men and children) may have been transported to the British American colonies, with some estimates going as high as 50,000"),
    ("america_range", "Penal transportation", "England transported an estimated 50,000 to 120,000 convicts and political prisoners"),
    ("america_1776", "Penal transportation", "early in the American Revolution in 1776"),
    ("bermuda", "Penal transportation", "From the 1820s until the 1860s, convicts were sent to the Imperial fortress colony of Bermuda"),
    ("bermuda_1823", "Royal Naval Dockyard, Bermuda", "the first arriving in 1823"),
    ("bermuda_1863", "Royal Naval Dockyard, Bermuda", "The last convicts were withdrawn in 1863"),
    ("andaman_1857", "Penal transportation", "A penal colony was established there in 1857 with prisoners from the Indian Rebellion of 1857"),
    ("andaman_80k", "Penal transportation", "An estimated 80,000 political prisoners were transported to the Cellular Jail"),
    ("andaman_cells", "Penal transportation", "was constructed between 1896 and 1906 as a high-security prison with 698 individual cells"),
    ("guiana_dates", "Penal transportation", "Devil's Island, a French penal colony in Guiana , was used for transportation from 1852 to 1953"),
    ("newcal", "Penal transportation", "New Caledonia became a French penal colony from the 1860s until the end of the transportations in 1897; about 22,000 criminals and political prisoners"),
    ("bagne_1852", "Bagne (penal establishment)", "The maritime bagnes were then transferred to Cayenne in 1852, and to New Caledonia in 1864"),
    ("bagne_1953", "Bagne (penal establishment)", "On August 1, 1953, the last convicts and their supervisors returned to France"),
    ("bagne_1938", "Bagne (penal establishment)", "a decree-law of June 17, 1938"),
    ("katorga_chekhov", "Katorga", "In 1891 Anton Chekhov , the Russian writer and playwright, visited the katorga settlements on Sakhalin island"),
    ("katorga_17c", "Katorga", "Katorga camps were established in the 17th century by Tsar Alexis of Russia"),
    ("moreton", "Moreton Bay Penal Settlement", "The Moreton Bay Penal Settlement operated from 1824 to 1842"),
    ("moreton_1000", "Moreton Bay Penal Settlement", "the number of prisoners in the settlement rose from 200 to 1000"),
    ("macquarie", "Macquarie Harbour Penal Station", "Opened 1822 Closed 1833"),
    ("portarthur", "Port Arthur, Tasmania", "From 1833 until 1877, it was the destination for those deemed the most hardened of transported convicts"),
    ("sites_unesco", "Australian Convict Sites", "Inscription 2010"),
    ("sites_eleven", "Australian Convict Sites", "one of the eleven sites that form the Australian Convict Sites"),
    ("sites_fremantle", "Australian Convict Sites", "Fremantle Prison was constructed during the 1850s"),
    ("women_theft", "Convicts in Australia", "Some 80% of women had been convicted of theft, usually petty"),
    ("women_prost", "Convicts in Australia", "no women were transported for prostitution, as it was not a transportable offence"),
    ("women_courtesans", "Convicts in Australia", "Although they were routinely referred to as courtesans"),
    ("women_fry_society", "Convict women in Australia", "British Ladies Society cared for women convicts"),
    ("ff_tenerife", "First Fleet", "the fleet anchored at Santa Cruz at Tenerife"),
    ("ff_rio", "First Fleet", "The Fleet reached Rio de Janeiro on 5 August and stayed for a month"),
    ("ff_eora_first", "First Fleet", "First contact was made with the local indigenous people, the Eora , who seemed curious but suspicious of the newcomers"),
    ("wa_request", "Convict era of Western Australia", "At the request of the colony, convicts were initially selected"),
    ("nsw_1840", "Convicts in Australia", "Transportation to New South Wales was temporarily ended in 1840"),
    ("cellular_political", "Cellular Jail", "Prison for political prisoners"),
    ("ff_gillen", "First Fleet", "Convicts (men) 582 543 Convicts (women) 193 189"),
    ("ff_eleven", "First Fleet", "eleven vessels carrying about 1,487 people"),
]
QW = [
    ("guiana_80k", "Devil's Island", "The vast majority of the more than 80,000 prisoners sent to the Devil's Island prison system never returned to France"),
    ("guiana_pc", "Penal colony", "Devil's Island in French Guiana received some 80,000 forgers and other criminals between 1852 and 1939"),
    ("sakhalin_1857", "Sakhalin", "In 1857, the Russians established a penal colony, or katorga, on Sakhalin"),
    ("sakhalin_1869", "Sakhalin", "which formed the legal basis for Sakhalin Island to be a penal colony"),
    ("katorga_1906", "Gulag", "approximately 6,000 katorga convicts were serving sentences in 1906, with up to 28,600 by 1916"),
    ("portblair_200", "Port Blair", "the first set of 200 convicts arrived at the island in March 1858"),
    ("andaman_1947", "Andaman Islands", "The penal colony was eventually closed on 15 August 1947"),
    ("hulks_1776", "Hulk (ship type)", "commencing in Britain in 1776 when the American Revolution prevented the sending of convicts to North America"),
    ("convict_ship", "Convict ship", "There was no ship specifically built as a convict vessel"),
    ("devils_never", "Devil's Island", "never returned to France"),
]
QU = {}
for k, t, ph in Q:
    T = TXT[t]
    assert ph in T, (k, t, ph)
    j = T.find(ph); a = T.rfind(". ", 0, j); b = T.find(". ", j + len(ph))
    QU[k] = {"article": t, "revid": REV[t], "phrase": ph, "sentence": T[a + 2 if a >= 0 else 0:(b + 1 if b >= 0 else len(T))].strip()[:600]}
for k, t, ph in QW:
    T = WT[t]
    assert ph in T, (k, t, ph)
    QU[k] = {"article": t, "revid": None, "phrase": ph, "sentence": ph}
hulks = []
s = soup("List of British prison hulks"); tb = [tb for tb in s.find_all("table") if "wikitable" in (tb.get("class") or [])][0]
for r in tb.find_all("tr")[1:]:
    t = [ctext(c) for c in r.find_all(["td", "th"])]
    hulks.append({"name": t[0], "years": t[1], "location": t[2], "comments": t[3][:300]})
pd.DataFrame(hulks).to_csv(f"{SRC}/prison_hulks.csv", index=False)
chk["hulks"] = len(hulks)
jsave({"quotes": QU, "revids": REV, "checks": chk}, f"{DATA}/source_quotes.json", indent=1)
print("rows", {k: int((V.list == k).sum()) for k in CK}, "fleet matched", fm, "article voyages", len(A), "matched", len(K), "women flagged", int(V.women.sum()))
print("quotes", len(QU), "hulks", len(hulks), "ships", len(S))
print(V.region.value_counts().to_dict())
