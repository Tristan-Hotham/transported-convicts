"""Step 6. Build the paper: fill code/paper_template.tex from data/results.json, add tables, compile with xelatex.
Output: release/paper/<NAME>.pdf and .tex (figures f_*.png sit beside them). The DOI stays as the 10.5281/zenodo.23873537 placeholder."""
import subprocess
from common import *

R = jload(f"{DATA}/results.json")
OUT = os.path.join(ROOT, "release", "paper"); NAME = "Hotham_Transported"
tex = lambda s: str(s).replace("\\", "").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_").replace("#", "\\#").replace("$", "\\$")

# statements made in words in the paper only
assert R["cover"]["n_conv_pct"] < 100 / 6                                       # "under a sixth of the voyages"
assert R["decades"][0]["dec"] == 1780 and R["decades"][0]["n"] == 6            # "The First Fleet's 6 transports arrived in 1788"
assert R["irish"]["nsw_n"] / R["irish"]["n"] > .9                              # "almost all went to New South Wales"
assert R["indian"]["nsw"] / R["indian"]["n"] > .9
assert R["days"]["slow_after"]["ship"] == "Friends" and R["deaths"]["art_max_ship"] == "Tellicherry"
assert R["days"]["eras"][3]["n"] <= 5 and R["days"]["eras"][1]["n"] <= 6            # "very small", "nearly as small"
assert R["meta"]["dup_days"] == 75 and R["meta"]["match_days"] == 3


def tfmt(v, f):
    if f == "int": return f"{int(round(float(v))):,}"
    if f == "pc": return f"{round(float(v))}\\%"
    if f == "pc1": return f"{float(v):.1f}\\%"
    if f == "f1": return f"{float(v):.1f}"
    return tex(str(v))


rows = "".join(f"{tex(c['name'].replace(' (Tasmania)', ''))} & {c['n']} & {c['first']} & {c['last']} & {c['peak_year']} ({c['peak_n']}) & {c['n_conv']} & {c['sum_conv']:,} & {c['irish']} & {c['indian']} & {c['intra']}\\\\\n"
               for c in R["col"].values())
TC = ("\\begin{table}[tbp]\\centering\\footnotesize\\setlength{\\tabcolsep}{4pt}\\caption{Listed voyages from overseas by colony: first and last arrival, busiest year, voyages with a number of convicts and the convicts they carried, voyages from Ireland and from India and the Indian Ocean, and (not counted) transfers within Australia.}\\label{tab:colonies}"
      "\\begin{tabular}{lrrrrrrrrr}\\toprule Colony & Voyages & First & Last & Busiest & With no. & Convicts & Ireland & India etc. & Transfers\\\\\\midrule\n" + rows +
      f"\\midrule All & {R['source']['n_main']} & {R['source']['first_year']} & {R['source']['last_year']} & {R['peak']['year']} ({R['peak']['n']}) & {R['cover']['n_conv']} & {R['cover']['sum_conv']:,} & {R['irish']['n']} & {R['indian']['n']} & {R['source']['n_intra']}\\\\\n\\bottomrule\\end{{tabular}}\\end{{table}}")
rows = "".join(f"{tex(s['name'])} & {s['voyages']} & {s['first']} to {s['last']} & {tex(s['colonies'])} & {s['launched'] or ''} & {s['lead'] or ''}\\\\\n" for s in R["ships"]["top"])
TSH = ("\\begin{table}[tbp]\\centering\\small\\caption{Ships with the most listed convict voyages from overseas, with the launch year and the number of convict voyages stated in the ship's own article where given.}\\label{tab:ships}"
       "\\begin{tabular}{lrllrr}\\toprule Ship & Voyages & Years & Colonies & Launched & Article says\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = "".join(f"{tex(w['name'])} & {tex(w['by'])} & {tex(w['years'])} & {tex(w['people'])} & {tex('; '.join(w['articles']))}\\\\\n" for w in R["world"])
TW = ("\\begin{table}[tbp]\\centering\\footnotesize\\setlength{\\tabcolsep}{4pt}\\caption{Penal transportation systems in the articles, with the numbers they state. For Sakhalin and Siberia the articles used give a start but no end.}\\label{tab:world}"
      "\\begin{tabular}{p{2.4cm}p{1.9cm}p{2.3cm}p{4.0cm}p{4.0cm}}\\toprule Destination & From & Years & Convicts, as stated & Articles\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
rows = "".join(f"{tex(t)} & {r}\\\\\n" for t, r in sorted(R["source"]["revids"].items()) if t not in ("List of convict ships to Western Australia", "Convict ships to Australia"))
TS = ("\\begin{table}[tbp]\\centering\\small\\caption{English Wikipedia articles used, with the revision read (CC BY-SA 4.0). Also used, from a search dump without revision ids: Convict ship, Devil's Island, Penal colony, Port Blair, Sakhalin, Gulag, Andaman Islands, Hulk (ship type), and the full text of the convict ship articles named in the data.}\\label{tab:revs}"
      "\\begin{tabular}{lr}\\toprule Article & Revision\\\\\\midrule\n" + rows + "\\bottomrule\\end{tabular}\\end{table}")
t = open(os.path.join(ROOT, "code", "paper_template.tex"), encoding="utf-8").read()
for k in ("page", "repo"):
    t = t.replace("\\url{{{meta.%s}}}" % k, "\\url{%s}" % R["meta"][k])
t = re.sub(r"\{\{(?!TABLE_)([^}|]+)(\|(\w+))?\}\}", lambda m: tfmt(get(R, m.group(1)), m.group(3) or "raw"), t)
for k, v in (("COLONIES", TC), ("SHIPS", TSH), ("WORLD", TW), ("REVS", TS)):
    t = t.replace("{{TABLE_%s}}" % k, v)
t = t.replace("@@DOILINK@@", "https://doi.org/\\{\\{DOI\\}\\}")
assert "{{" not in t and "--" not in t and "—" not in t and "–" not in t, re.findall(r"\{\{[^}]*\}\}", t)[:4]
for bad in ("DSIT", "DCMS", "civil serv"):
    assert bad not in t
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, NAME + ".tex"), "w", encoding="utf-8").write(t)
for _ in range(2):
    r = subprocess.run(["xelatex", "-interaction=nonstopmode", NAME + ".tex"], cwd=OUT, capture_output=True, text=True)
log = open(os.path.join(OUT, NAME + ".log"), encoding="utf-8", errors="ignore").read()
print([l for l in log.splitlines() if "Missing character" in l or "undefined" in l.lower() or "Overfull" in l][:12])
for ext in (".aux", ".log", ".out"):
    q = os.path.join(OUT, NAME + ext)
    if os.path.exists(q): os.remove(q)
txt = subprocess.run(["pdftotext", os.path.join(OUT, NAME + ".pdf"), "-"], capture_output=True, text=True).stdout
pages = subprocess.run(["pdfinfo", os.path.join(OUT, NAME + ".pdf")], capture_output=True, text=True).stdout
print("paper", r.returncode, len(txt.split()), "words;", [l for l in pages.splitlines() if l.startswith("Pages")], "dashes:", txt.count("—") + txt.count("–") + txt.count("--"))
