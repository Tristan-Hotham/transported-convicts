"""r/dataisbeautiful collage for transported-convicts: 2400 x 3200 px, light background. Numbers from data/results.json.
Map labels are placed automatically on open sea (never over land, routes, circles or other labels) and then checked;
the colony names and counts are carried by the legend under the map."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "code"))
from figstyle import *
import pandas as pd
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, Circle
from matplotlib.lines import Line2D

R = jload(f"{DATA}/results.json")
V = pd.read_csv(f"{DATA}/voyages.csv", keep_default_na=False, na_values={"convicts": "", "voyage_days": "", "year": ""})
V["convicts"] = pd.to_numeric(V.convicts, errors="coerce")
M = V[V.counted_overseas_voyage == 1].sample(frac=1, random_state=3)
BGc = "#F7F5F0"; SEAc = "#E9EFF2"; LANDc = "#E2DDD1"
HALO = [pe.withStroke(linewidth=4, foreground=SEAc)]
HALOP = [pe.withStroke(linewidth=4, foreground=BGc)]
RC = dict(REGIONS)
s, pk, cv, ir, dd, de, st, cl = R["source"], R["peak"], R["cover"], R["irish"], R["days"], R["deaths"], R["stated"], R["col"]
Y = pd.DataFrame(R["years"]).set_index("y")

fig = plt.figure(figsize=(12, 16.0), dpi=200, facecolor=BGc)
fig.text(.045, .985, "Every convict ship to Australia", fontproperties=DISP, fontsize=44, color=FG, va="top")
fig.text(.045, .938, f"Britain transported about {st['conv_162']:,} convicts to Australia. Wikipedia's ship lists hold {s['n_main']} of their voyages,\n"
         f"{s['first_year']} to {s['last_year']}, here on the usual sailing route: south through the Atlantic, past the Cape, across the Southern Ocean.",
         fontproperties=SERP, fontsize=14, color=FG, va="top", linespacing=1.45)

# ---- map
ax = fig.add_axes([0, .505, 1, .385]); ax.set_facecolor(SEAc)
world(ax, lw=.3, land=LANDc, ec=BGc)
routes(ax, M, alpha=.09, jitter=1.1e5)
P = [p for p in R["ports"] if p["region"] != "Within Australia"]
CIRC = []
for p in sorted(P, key=lambda r: -r["n"]):
    x, y = proj(p["lon"], p["lat"]); r = 3.4e4 * np.sqrt(p["n"]); CIRC.append((float(x), float(y), r))
    ax.add_patch(Circle((float(x), float(y)), r, fc=RC[p["region"]], ec="#FFFFFF", lw=.7, alpha=.92, zorder=5))
for k in CK:
    lat, lon = COL[k]["ll"]; x, y = proj(lon, lat); r = 2.6e4 * np.sqrt(cl[k]["n"]); CIRC.append((float(x), float(y), r))
    ax.add_patch(Circle((float(x), float(y)), r, fc=COL[k]["c"], ec="#FFFFFF", lw=1, zorder=6))
PL = Placer(fig, ax, obstacles(M, route_buf=1.4e5, circles=CIRC), markers=CIRC)
kw = lambda c=FG, fs=10, w="medium": dict(ha="center", va="center", fontsize=fs, color=c, path_effects=HALO, fontweight=w, family=MONO, linespacing=1.25)
EI = sum(p["n"] for p in P if p["region"] in ("England", "Ireland"))
PL.place("british", f"from British\nand Irish\nports: {EI}", (-30, 42), window=20, **kw())
PL.place("route1", "south past\nMadeira, west\ntowards Brazil,\neast to the Cape", (-9, -12), window=12, **kw(MUT, 9, "normal"))
PL.place("route2", "then east through the Southern Ocean", (28, -46.5), window=10, **kw(MUT, 9, "normal"))
PL.check()
print("labels ok:", [n for n, _ in PL.placed])

# ---- legend (full) under the map
LP = SERP.copy(); LP.set_size(11.5)
leg = [Patch(color=COL[k]["c"], label=f"{COL[k]['name'].replace(' (Tasmania)', ' (Tasmania), Hobart').replace('New South Wales', 'New South Wales, Sydney').replace('Western Australia', 'Western Australia, Fremantle').replace('Norfolk Island', 'Norfolk Island, Kingston')}: {cl[k]['n']} voyages") for k in CK] + \
      [Line2D([], [], ls="", marker="o", ms=10, mfc=RC[r], mec="#fff", label=f"port of departure: {r}") for r in ("England", "Ireland", "India and the Indian Ocean", "Other colonies")]
fig.text(.045, .497, "Lines: one per voyage, coloured by its colony; routes are stylised (the lists give only port and colony). Circles: area = voyages.", fontsize=9.4, color=MUT, va="top")
fig.legend(handles=leg, loc="upper left", bbox_to_anchor=(.035, .489), ncol=2, frameon=False, prop=LP, handletextpad=.5, columnspacing=1.6, labelspacing=.55)

# ---- numbers row
nums = [(f"{pk['n']}", COL["nsw"]["c"], f"ships arrived in {pk['year']},\nthe busiest year"),
        (f"{ir['cork']}", COL["nfk"]["c"], f"sailed from Cork, the\nbusiest single port"),
        (f"{dd['eras'][2]['median']}", COL["wa"]["c"], f"median days at sea in the\n1820s and 30s; first fleets {dd['eras'][0]['median']}"),
        (f"{de['sf_pct']}%", COL["vdl"]["c"], "of the Second Fleet's\nconvicts died at sea")]
for i, (big, col, small) in enumerate(nums):
    xx = .045 + i * .235
    fig.text(xx, .385, big, fontproperties=DISP, fontsize=34, color=col, va="top")
    fig.text(xx, .347, small, family=MONO, fontsize=10.5, color=FG, va="top", linespacing=1.4)

# ---- ships per year
a = fig.add_axes([.075, .155, .875, .135]); a.set_facecolor(BGc)
base = np.zeros(len(Y))
for k in CK:
    a.bar(Y.index, Y[k].values, bottom=base, color=COL[k]["c"], width=.86); base += Y[k].values
a.set_xlim(Y0 - .8, Y1 + .8); a.set_ylim(0, 40); spines(a); a.tick_params(labelsize=10); a.grid(axis="y", color=RULE, lw=.8); a.set_axisbelow(True)
a.set_title("Convict ships arriving from overseas, per year", family=MONO, fontsize=13, color=FG, loc="left", pad=10)
a.text(pk["year"], pk["n"] + 1.2, f"{pk['year']}: {pk['n']}", ha="center", fontsize=10, color=FG, path_effects=HALOP)
a.text(1788.5, 13, "First\nFleet", fontsize=9, color=MUT, va="bottom", path_effects=HALOP)
a.text(1840.6, 21, "New South Wales\nstops, 1840", fontsize=9, color=MUT, va="bottom", path_effects=HALOP)
a.text(1850.4, 9, "Western Australia\n1850 to 1868", fontsize=9, color=MUT, va="bottom", path_effects=HALOP)

# ---- small panels: deaths and ports
b2 = fig.add_axes([.235, .052, .30, .062]); b2.set_facecolor(BGc)
rows = [("Second Fleet, 1790", de["sf_pct"], COL["vdl"]["c"]), ("Third Fleet, 1791", de["tf_pct"], INK), (f"{de['art_n']} later voyages", de["art_pct"], COL["nfk"]["c"])]
b2.barh(range(3), [r[1] for r in rows], color=[r[2] for r in rows], height=.62); b2.invert_yaxis()
b2.set_yticks(range(3)); b2.set_yticklabels([r[0] for r in rows], fontsize=9.5); b2.tick_params(axis="y", length=0); b2.set_xticks([]); spines(b2); b2.spines["bottom"].set_visible(False)
for i, r in enumerate(rows):
    b2.text(r[1] + .5, i, f"{r[1]:.1f}%" if r[1] < 10 else f"{r[1]:.0f}%", va="center", fontsize=9.5)
b2.set_xlim(0, 32); b2.set_title("Convicts who died at sea", family=MONO, fontsize=11, color=FG, loc="left", pad=6)
b3 = fig.add_axes([.78, .052, .18, .062]); b3.set_facecolor(BGc)
TP = [p for p in R["ports"] if p["region"] != "Within Australia"][:4]
b3.barh(range(4), [p["n"] for p in TP], color=[RC[p["region"]] for p in TP], height=.62); b3.invert_yaxis()
b3.set_yticks(range(4)); b3.set_yticklabels([p["name"].replace(" (Cove of Cork)", "").replace(" (port not given)", ", port not given") for p in TP], fontsize=9.5); b3.tick_params(axis="y", length=0); b3.set_xticks([]); spines(b3); b3.spines["bottom"].set_visible(False)
for i, p in enumerate(TP):
    b3.text(p["n"] + 2, i, str(p["n"]), va="center", fontsize=9.5)
b3.set_xlim(0, 135); b3.set_title("Busiest ports of departure", family=MONO, fontsize=11, color=FG, loc="left", pad=6)

fig.text(.045, .006, f"Source: English Wikipedia (CC BY-SA 4.0): Convict ships to New South Wales, to Tasmania and to Norfolk Island; List of convict ship voyages to Western\n"
         f"Australia; First, Second and Third Fleet; ship articles. Voyages from overseas counted once by arrival year; the lists give convict numbers for only {cv['n_conv']}.\n"
         "Analysis and chart: Tristan Hotham, with Python and matplotlib  ·  maps.tristanhotham.com/transported-convicts", family=MONO, fontsize=8.3, color=MUT, linespacing=1.5, va="bottom")
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "every_convict_ship.png")
fig.savefig(out, facecolor=BGc, dpi=200)
print("ok", out)
