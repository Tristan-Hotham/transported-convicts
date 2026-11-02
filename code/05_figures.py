"""Step 5. Header card, blog figures (release/blog/b_*.png, 1800 px wide) and paper figures (release/paper/f_*.png).
Numbers from data/results.json; voyages from data/voyages.csv."""
import pandas as pd
import matplotlib.patheffects as pe
from matplotlib.patches import Patch, Circle
from matplotlib.lines import Line2D
from figstyle import *

R = jload(f"{DATA}/results.json")
V = pd.read_csv(f"{DATA}/voyages.csv", keep_default_na=False, na_values={"convicts": "", "voyage_days": "", "year": ""})
V["convicts"] = pd.to_numeric(V.convicts, errors="coerce")
M = V[V.counted_overseas_voyage == 1].copy()
BL = os.path.join(ROOT, "release", "blog"); PA = os.path.join(ROOT, "release", "paper")
os.makedirs(BL, exist_ok=True); os.makedirs(PA, exist_ok=True)
Y = pd.DataFrame(R["years"]).set_index("y")
HALO = [pe.withStroke(linewidth=3.5, foreground=SEA)]
HALOB = [pe.withStroke(linewidth=3.5, foreground=BG)]
RC = dict(REGIONS)


def both(fig, name, blog=True):
    w = fig.get_figwidth()
    fig.savefig(os.path.join(PA, "f_" + name + ".png"), dpi=200 * 12 / w, facecolor=fig.get_facecolor())
    if blog:
        fig.savefig(os.path.join(BL, "b_" + name + ".png"), dpi=1800 / w, facecolor=fig.get_facecolor())   # 1800 px wide
    plt.close(fig)


def colony_legend(fig, **kw):
    return fig.legend(handles=[Patch(color=COL[k]["c"], label=COL[k]["name"]) for k in CK], frameon=False, **kw)


# ---------- the map of voyages ----------
MS = M.sample(frac=1, random_state=3)          # draw order shuffled so that no colony's colour hides the others on shared routes


def voyage_map(ax, alpha=.06, size=1.0, jitter=1.1e5):
    ax.set_facecolor(SEA)
    world(ax, ec=BG)
    routes(ax, MS, alpha=alpha, jitter=jitter)
    P = [p for p in R["ports"] if p["region"] != "Within Australia"]
    for p in sorted(P, key=lambda r: -r["n"]):
        x, y = proj(p["lon"], p["lat"]); ax.add_patch(Circle((float(x), float(y)), size * 3.4e4 * np.sqrt(p["n"]), fc=RC[p["region"]], ec="#FFFFFF", lw=.6, alpha=.92, zorder=5))
    for k in CK:
        lat, lon = COL[k]["ll"]; x, y = proj(lon, lat); n = R["col"][k]["n"]
        ax.add_patch(Circle((float(x), float(y)), size * 2.6e4 * np.sqrt(n), fc=COL[k]["c"], ec="#FFFFFF", lw=.9, zorder=6))
    return P


PT = {p["key"]: p for p in R["ports"]}
cn = R["col"]
fig = plt.figure(figsize=(12, 7.8), facecolor=BG); ax = fig.add_axes([0, .18, 1, .71])
P = voyage_map(ax, alpha=.09)
CIRC = []
for p in P:
    x, y = proj(p["lon"], p["lat"]); CIRC.append((float(x), float(y), 3.4e4 * np.sqrt(p["n"])))
for k in CK:
    lat, lon = COL[k]["ll"]; x, y = proj(lon, lat); CIRC.append((float(x), float(y), 2.6e4 * np.sqrt(R["col"][k]["n"])))
PL = Placer(fig, ax, obstacles(MS, circles=CIRC, route_buf=1.3e5, min_voyages=3))
kw = lambda c=FG, fs=9.5, w="normal", ha="center": dict(ha=ha, va="center", fontsize=fs, color=c, path_effects=HALO, fontweight=w, linespacing=1.25)
EI = sum(p["n"] for p in P if p["region"] in ("England", "Ireland"))
PL.place("british", f"from British\nand Irish\nports: {EI}", (-30, 42), window=20, **kw(fs=9))
PL.place("route1", "the usual route:\nsouth past Madeira,\nwest towards Brazil,\neast to the Cape", (-9, -12), **kw(MUT, fs=8.5))
PL.place("route2", "then east through the Southern Ocean", (28, -46.5), **kw(MUT, fs=8.5))
PL.check()
fig.text(.02, .968, f"{R['source']['n_main']} convict voyages from overseas to Australia in Wikipedia's lists, {R['source']['first_year']} to {R['source']['last_year']}", fontsize=12, color=FG, fontweight="medium")
fig.text(.02, .905, f"Line colour: the colony the ship arrived in, on a stylised sailing route. Circles: voyages from each port (Cork {PT['cork']['n']}, Portsmouth {PT['portsmouth']['n']},\nLondon {PT['london']['n']}, Dublin {PT['dublin']['n']}; {R['indian']['n']} from India, Ceylon, Mauritius and Singapore, Calcutta {PT['calcutta']['n']} the busiest) and arrivals in each colony", fontsize=9.5, color=MUT, linespacing=1.4)
leg = [Patch(color=COL[k]["c"], label=f"{COL[k]['name'].replace(' (Tasmania)', '')} ({COL[k]['place'].replace(' (Port Jackson)', '')}): {cn[k]['n']} voyages") for k in CK] + \
      [Line2D([], [], ls="", marker="o", ms=8, mfc=RC[r], mec="#fff", label=f"port: {r}") for r in ("England", "Ireland", "India and the Indian Ocean", "Other colonies")]
fig.legend(handles=leg, loc="lower center", ncol=2, frameon=False, fontsize=9, bbox_to_anchor=(.5, .0), columnspacing=3)
both(fig, "map")

# ---------- voyages per year ----------
fig = plt.figure(figsize=(12, 5.4), facecolor=BG); ax = fig.add_axes([.06, .11, .92, .74]); ax.set_facecolor(BG)
base = np.zeros(len(Y))
for k in CK:
    ax.bar(Y.index, Y[k].values, bottom=base, color=COL[k]["c"], width=.86, label=COL[k]["name"]); base += Y[k].values
spines(ax); ax.set_xlim(Y0 - .8, Y1 + .8); ax.set_ylim(0, 40); ax.grid(axis="y", color=RULE); ax.set_axisbelow(True); ax.set_ylabel("ships arriving")
pk = R["peak"]
ax.text(pk["year"], pk["n"] + .8, f"{pk['year']}: {pk['n']}", ha="center", fontsize=10)
for x, y0, t in ((1788, 12.5, "First Fleet"), (1840, 21, "New South Wales\nstops taking convicts"), (1850, 9, "Western Australia\nbegins")):
    ax.plot([x, x], [y0, y0 + 2.5], color=MUT, lw=.8); ax.text(x + .4, y0 + 3, t, fontsize=9, color=MUT, va="bottom", path_effects=HALOB)
colony_legend(fig, loc="upper left", bbox_to_anchor=(.055, .99), ncol=4, fontsize=10)
both(fig, "years")

# ---------- ports ----------
PP = [p for p in R["ports"] if p["region"] != "Within Australia"][:16]
fig = plt.figure(figsize=(12, 6.2), facecolor=BG); ax = fig.add_axes([.23, .05, .72, .86]); ax.set_facecolor(BG)
nm = [p["name"].replace(" (Cove of Cork)", "").replace(" (Kingstown)", "") for p in PP][::-1]
ax.barh(nm, [p["n"] for p in PP][::-1], color=[RC[p["region"]] for p in PP][::-1], height=.7)
for i, p in enumerate(PP[::-1]):
    ax.text(p["n"] + 1, i, str(p["n"]), va="center", fontsize=10)
spines(ax); ax.spines["bottom"].set_visible(False); ax.set_xticks([]); ax.tick_params(axis="y", length=0, labelsize=10.5)
ir = R["irish"]
ax.text(.98, .30, f"Irish ports: {ir['n']} of the {ir['n_ei']} voyages\nfrom Britain and Ireland ({ir['pct']:.0f}%)\nNew South Wales: {ir['nsw_pct']:.0f}% Irish\nVan Diemen's Land: {ir['vdl_pct']:.0f}% Irish", transform=ax.transAxes, ha="right", va="bottom", fontsize=10.5, color=FG, linespacing=1.5)
fig.legend(handles=[Patch(color=RC[r], label=r) for r in ("England", "Ireland", "India and the Indian Ocean")], loc="upper left", bbox_to_anchor=(.22, 1.0), ncol=3, frameon=False, fontsize=10)
both(fig, "ports")

# ---------- voyage length ----------
D = pd.DataFrame(R["days"]["rows"])
fig = plt.figure(figsize=(12, 5.6), facecolor=BG); ax = fig.add_axes([.07, .11, .9, .74]); ax.set_facecolor(BG)
for k in CK:
    a = D[(D.list == k) & (D.fleet > 0)]; b = D[(D.list == k) & (D.fleet == 0)]
    ax.scatter(a.y, a.days, marker="s", s=46, c=COL[k]["c"], ec=BG, lw=.8, zorder=4)
    ax.scatter(b.y, b.days, marker="o", s=52, c=COL[k]["c"], ec=BG, lw=.8, zorder=4)
for (a_, b_), e in zip(((1787, 1791), (1800, 1819), (1820, 1839), (1840, 1868)), R["days"]["eras"]):
    ax.plot([a_, b_], [e["median"], e["median"]], color=FG, lw=2, alpha=.55, zorder=3)
    ax.text(a_, 70, f"median {e['median']}\n({e['n']} voyages)", fontsize=9, color=FG, va="center", path_effects=HALOB, zorder=5)
    ax.plot([a_, a_], [78, e["median"]], color=FG, lw=.6, ls=":", alpha=.5, zorder=2)
sl, fa = R["days"]["slow"], R["days"]["fast"]
ax.text(sl["y"] + 1, sl["days"], f"{sl['ship']}, {sl['days']} days", fontsize=9.5, va="center", path_effects=HALOB)
ax.text(fa["y"], fa["days"] + 12, f"{fa['ship']}, {fa['days']} days", fontsize=9.5, ha="center", path_effects=HALOB)
ax.text(1869, R["days"]["hougoumont"] + 12, f"Hougoumont, {R['days']['hougoumont']}", fontsize=9.5, ha="right", path_effects=HALOB)
spines(ax); ax.set_xlim(1784, 1871); ax.set_ylim(58, 330); ax.set_ylabel("days at sea"); ax.grid(axis="y", color=RULE); ax.set_axisbelow(True)
leg = [Line2D([], [], ls="", marker="s", ms=7, mfc=MUT, mec=BG, label="fleet tables (1788 to 1791)"), Line2D([], [], ls="", marker="o", ms=7, mfc=MUT, mec=BG, label="ship articles")] + \
      [Patch(color=COL[k]["c"], label=COL[k]["short"]) for k in CK]
fig.legend(handles=leg, loc="upper left", bbox_to_anchor=(.065, .99), ncol=6, frameon=False, fontsize=9.5)
both(fig, "days")

# ---------- deaths ----------
de = R["deaths"]; T = sorted(de["tf_ships"], key=lambda s: -s["pct"])
rows = [("Second Fleet, 1790 (all ships)", de["sf_pct"], COL["vdl"]["c"])] + [(s["ship"], s["pct"], INK) for s in T] + [(f"Later voyages ({de['art_n']})", de["art_pct"], COL["nfk"]["c"])]
fig = plt.figure(figsize=(12, 6.8), facecolor=BG); ax = fig.add_axes([.27, .12, .68, .84]); ax.set_facecolor(BG)
ypos = [0] + [i + 1.6 for i in range(1, len(T) + 1)] + [len(T) + 3.2]
ax.barh(ypos, [r[1] for r in rows], color=[r[2] for r in rows], height=.72)
for y_, r in zip(ypos, rows):
    ax.text(r[1] + .3, y_, f"{r[1]:.1f}%" if r[1] < 2 else f"{r[1]:.0f}%", va="center", fontsize=10)
ax.set_yticks(ypos); ax.set_yticklabels([r[0] for r in rows], fontsize=10.5); ax.invert_yaxis()
ax.text(0, 1.75, "Third Fleet ships, 1791", fontsize=9.5, color=MUT, va="bottom")
spines(ax); ax.set_xlim(0, 30); ax.tick_params(axis="y", length=0); ax.set_xlabel("share of embarked convicts who died at sea")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%")); ax.grid(axis="x", color=RULE); ax.set_axisbelow(True)
both(fig, "deaths")

# ---------- women ----------
PO = pd.DataFrame(R["women"]["pop"])
fig = plt.figure(figsize=(12, 6.0), facecolor=BG)
a2 = fig.add_axes([.09, .66, .86, .22]); a2.set_facecolor(BG)
ax = fig.add_axes([.09, .09, .86, .52]); ax.set_facecolor(BG)
xs = np.arange(len(PO))
ax.bar(xs, PO.male, color=INK, alpha=.85, width=.62)
ax.bar(xs, PO.female, bottom=PO.male, color=COL["vdl"]["c"], width=.62)
ax.set_xticks(xs); ax.set_xticklabels(PO.year); spines(ax); ax.set_ylabel("convicts in NSW"); ax.grid(axis="y", color=RULE); ax.set_axisbelow(True)
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
a2.plot(xs, PO.fpct, "-o", color=COL["vdl"]["c"], lw=2.2, ms=5); a2.set_ylim(0, 34); a2.set_xlim(ax.get_xlim()); spines(a2); a2.set_xticks([])
a2.set_ylabel("women's share"); a2.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%")); a2.set_yticks([0, 10, 20, 30]); a2.grid(axis="y", color=RULE)
for x, v in zip(xs, PO.fpct):
    a2.text(x, v + 3, f"{v:.0f}%", ha="center", fontsize=9.5, color=COL["vdl"]["c"], path_effects=HALOB)
fig.legend(handles=[Patch(color=INK, alpha=.85, label="male convicts"), Patch(color=COL["vdl"]["c"], label="female convicts"), Line2D([], [], color=COL["vdl"]["c"], marker="o", label="women's share of convicts (top)")],
           loc="upper left", bbox_to_anchor=(.085, .995), ncol=3, frameon=False, fontsize=10)
both(fig, "women")

# ---------- the wider world ----------
EXT_W = ext(-105, 180, -50, 66)
fig = plt.figure(figsize=(14, 8.2), facecolor=BG); ax = fig.add_axes([0, .02, 1, .84]); ax.set_facecolor(SEA)
world(ax, ec=BG, ext=EXT_W)
RC_ = M.route.value_counts(); RK = sorted(r for r in RC_.index if r and RC_[r] >= 3)      # routes with three or more voyages
ax.add_collection(LineCollection([route_xy(k) for k in RK], colors="#9C9486", linewidths=.9, alpha=.55, zorder=3))
CIRW = []
for w in R["world"]:
    x, y = proj(w["lon"], w["lat"]); r = 1.1e3 * np.sqrt(w["pn"]) if w["pn"] else 1.5e5
    ax.add_patch(Circle((float(x), float(y)), r, fc=WORLDC if w["pn"] else "none", alpha=.85 if w["pn"] else 1, ec=WORLDC, lw=2 if not w["pn"] else .8, zorder=6))
    CIRW.append((float(x), float(y), r + 1.2e5))
PLW = Placer(fig, ax, obstacles(M, route_buf=1.0e5, circles=CIRW, min_voyages=3), markers=CIRW)
kww = lambda c=WORLDC: dict(ha="center", va="center", fontsize=8.8, color=c, path_effects=HALO, fontweight="medium", linespacing=1.25)
WP = {w["key"]: w for w in R["world"]}
def tg(k):
    w = WP[k]; x, y = proj(w["lon"], w["lat"]); return (w["lon"], w["lat"], (1.1e3 * np.sqrt(w["pn"]) if w["pn"] else 1.5e5) + 6e4)
L = [("america", (-50, 40), "British America\n1718 to 1776\n30,000 to 50,000*"), ("bermuda", (-50, 22), "Bermuda hulks\n1823 to 1863"),
     ("guiana", (-42, 12), "French Guiana\n1852 to 1953\nover 80,000"), ("newcal", (172, -14), "New Caledonia\n1864 to 1897\nabout 22,000"),
     ("andaman", (84, 3), "Andaman Islands\n1858 to 1947"), ("sakhalin", (156, 50), "Sakhalin\nfrom 1857"), ("siberia", (150, 57), "Siberia:\nkatorga")]
for k, pref, txt in L:
    PLW.place(k, txt, pref, window=22, target=tg(k), lead_gap=3e5, **kww(WORLDC))
fig.text(.02, .955, "Penal transportation around the world, with the numbers Wikipedia's articles state", fontsize=12, color=FG, fontweight="medium")
fig.text(.02, .9, f"Filled circles: area by people sent; the largest is Australia, 1788 to 1868, about {R['stated']['conv_162']:,}. Rings: no total stated.\n* Estimates range to {R['stated']['am_keneally']:,}. Grey lines: the main routes of the Australian convict voyages", fontsize=9.5, color=MUT, linespacing=1.45)
both(fig, "world")
PLW.check()

# ---------- completeness (paper only) ----------
fig = plt.figure(figsize=(12, 3.6), facecolor=BG); ax = fig.add_axes([.2, .18, .72, .74]); ax.set_facecolor(BG)
for i, k in enumerate(CK[::-1]):
    c = R["col"][k]; ax.barh(i, c["n_conv"], color=COL[k]["c"], height=.6); ax.barh(i, c["n"] - c["n_conv"], left=c["n_conv"], color=COL[k]["c"], alpha=.25, height=.6)
    ax.text(c["n"] + 6, i, f"{c['n_conv']} of {c['n']}", va="center", fontsize=10)
ax.set_yticks(range(len(CK))); ax.set_yticklabels([COL[k]["name"] for k in CK[::-1]]); spines(ax); ax.tick_params(axis="y", length=0); ax.set_xlabel("listed voyages from overseas (dark: number of convicts given)")
both(fig, "cover", blog=False)

# ---------- header card 1200 x 630 ----------
fig = plt.figure(figsize=(12, 6.3), dpi=100, facecolor=BG)
ax = fig.add_axes([.36, .14, .64, .82]); voyage_map(ax, alpha=.1, size=.8)
fig.text(.04, .80, "Trans-", fontproperties=DISP, fontsize=60, color=FG, va="top")
fig.text(.04, .62, "ported", fontproperties=DISP, fontsize=60, color=COL["vdl"]["c"], va="top")
fig.text(.04, .40, f"Every convict voyage to Australia in\nWikipedia's lists: {R['source']['n_main']} ships, {R['source']['first_year']} to {R['source']['last_year']}.\nWhere they sailed from, how long it took,\nand who did not survive the passage.", fontproperties=SERP, fontsize=14, color=FG, va="top", linespacing=1.35)
a2 = fig.add_axes([.42, .05, .55, .12]); a2.set_facecolor(BG); base = np.zeros(len(Y))
for k in CK:
    a2.bar(Y.index, Y[k].values, bottom=base, color=COL[k]["c"], width=.86); base += Y[k].values
a2.axis("off"); a2.set_xlim(Y0, Y1)
fig.text(.04, .04, "maps.tristanhotham.com/transported-convicts", fontsize=11, color=MUT)
fig.savefig(os.path.join(ROOT, "header.png"), dpi=100, facecolor=BG)
plt.close(fig)
print("figures done", sorted(os.listdir(BL)), sorted(x for x in os.listdir(PA) if x.endswith(".png")))
