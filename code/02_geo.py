"""Step 2. Geography: a light world outline file for the page and figures (Natural Earth 1:50m countries), a land mask
for checks, and a stylised sailing route for every departure place and colony pair used in the voyage tables.

Routes are drawn, not recorded. The tables give only a departure place and an arrival colony, so each route follows the
usual sailing pattern of the period as a smooth line through a few open-sea waypoints of my choosing: from the British
Isles south past Madeira and the Cape Verde islands, west towards Brazil, east across the South Atlantic, south of the
Cape of Good Hope and along the westerly winds of the Southern Ocean, then to Fremantle, round the south of Van
Diemen's Land to Hobart, or on up the east coast to Sydney and Norfolk Island. Ships from India, Mauritius and
Singapore cross the Indian Ocean and pass south of Australia through Bass Strait. Short transfers within Australia
follow the coast. Every route is checked: apart from the few kilometres at each end, no route may cross land."""
import numpy as np, pandas as pd
from shapely.geometry import shape, mapping, LineString, Point
from shapely.ops import unary_union
from shapely.prepared import prep
from common import *

iso_of = lambda p: p["ISO_A3_EH"] if p.get("ISO_A3_EH") not in ("-99", None) else p["ADM0_A3"]


def rnd(c, k=2):
    if isinstance(c, (list, tuple)) and c and isinstance(c[0], (int, float)):
        return [round(c[0], k), round(c[1], k)]
    return [rnd(x, k) for x in c]


W50 = jload(f"{GEO}/ne_50m_admin_0_countries.geojson")
feats = []
for f in W50["features"]:
    p = f["properties"]; iso = iso_of(p)
    gs = shape(f["geometry"]).simplify(0.04, preserve_topology=True)
    if gs.is_empty:
        continue
    gm = mapping(gs)
    nm = (p.get("NAME_EN") or p["NAME"]).replace("United States of America", "United States")
    feats.append({"type": "Feature", "properties": {"iso": iso, "n": nm, "lx": round(p["LABEL_X"], 2), "ly": round(p["LABEL_Y"], 2), "pop": float(p.get("POP_EST") or 0)},
                  "geometry": {"type": gm["type"], "coordinates": rnd(gm["coordinates"])}})
jsave({"type": "FeatureCollection", "features": feats}, f"{DATA}/world.json")

LANDG = unary_union([shape(f["geometry"]) for f in jload(f"{GEO}/ne_50m_land.geojson")["features"]])
LAND = prep(LANDG)

# open-sea waypoints (lon, lat)
CH = [(-2.0, 50.2), (-6.0, 49.2)]                            # down the English Channel
THAMES = [(1.6, 51.35), (1.45, 51.0), (0.4, 50.55)]           # from the Thames and the Downs, through the Strait of Dover
ATL = [(-12.5, 44.0), (-18.0, 31.0), (-24.5, 15.0), (-27.0, 1.0), (-31.0, -14.0), (-24.0, -30.0), (-5.0, -38.0), (19.0, -41.0),
       (45.0, -41.5), (75.0, -42.0), (100.0, -41.0)]           # Madeira, Cape Verde, towards Brazil, across to the Cape, the westerlies
TO = {
    "wa": [(110.0, -36.0), (114.2, -32.4)],
    "vdl": [(122.0, -42.8), (138.0, -44.6), (146.5, -44.3), (147.7, -43.4), (147.45, -43.05)],
    "nsw": [(122.0, -42.8), (138.0, -44.6), (146.5, -44.3), (148.6, -42.9), (149.4, -40.0), (150.4, -37.6), (151.4, -35.2), (151.35, -33.84)],
    "nfk": [(122.0, -42.8), (138.0, -44.6), (146.5, -44.3), (149.0, -42.5), (156.0, -38.0), (164.5, -31.0), (167.9, -29.15)],
}
# Indian Ocean and south of Australia, through Bass Strait
SOUTH = [(108.0, -37.5), (117.0, -37.2), (127.0, -36.6), (136.0, -37.6), (141.0, -39.3), (143.7, -39.25)]
BASS = [(145.6, -39.5), (147.0, -38.95), (148.9, -38.7), (150.4, -37.6), (151.4, -35.2), (151.35, -33.84)]
TOI = {
    "nsw": SOUTH + BASS,
    "vdl": [(108.0, -37.5), (117.0, -37.2), (127.0, -36.6), (136.0, -38.5), (143.0, -42.0), (145.8, -43.9), (147.0, -43.9), (147.7, -43.4), (147.45, -43.05)],
    "wa": [(110.0, -33.5), (114.3, -32.3)],
    "nfk": SOUTH + BASS + [(156.0, -32.5), (167.9, -29.15)],
}
FROM_IND = {
    "calcutta": [(88.05, 21.6), (88.1, 21.0), (88.5, 15.0), (87.5, 5.0), (90.0, -10.0), (98.0, -25.0)],
    "india": [(88.1, 21.0), (88.5, 15.0), (87.5, 5.0), (90.0, -10.0), (98.0, -25.0)],
    "madras": [(81.5, 12.0), (85.0, 4.0), (90.0, -10.0), (98.0, -25.0)],
    "bombay": [(71.5, 17.0), (70.5, 8.0), (76.0, -4.0), (86.0, -16.0), (98.0, -27.0)],
    "ceylon": [(79.6, 6.6), (80.0, 5.4), (84.0, 0.0), (90.0, -10.0), (98.0, -25.0)],
    "mauritius": [(59.0, -22.0), (70.0, -29.0), (88.0, -34.5), (100.0, -36.5)],
    "singapore": [(104.1, 1.22), (104.35, 1.3), (104.8, 1.2), (105.2, 0.6), (105.6, 0.2), (106.6, -1.4), (107.15, -2.6), (106.9, -4.6), (105.85, -5.95), (104.8, -7.3), (104.5, -12.0), (105.0, -22.0), (107.0, -30.0)],
}
FROM_OTHER = {
    "bermuda": [(-62.0, 30.0), (-45.0, 18.0), (-30.0, 3.0), (-31.0, -14.0)],
    "quebec": [(-70.3, 47.3), (-69.0, 48.3), (-66.5, 49.25), (-63.8, 49.05), (-60.5, 47.4), (-57.0, 46.0), (-50.0, 42.0), (-38.0, 25.0), (-28.0, 5.0), (-31.0, -14.0)],
    "cape": [(18.0, -36.0), (25.0, -40.0)],
}
OUT = {"london": THAMES, "downs": THAMES[1:], "sheerness": THAMES, "woolwich": THAMES, "deptford": THAMES, "gravesend": THAMES, "yarmouth": [(2.2, 52.4), (2.0, 51.4)] + THAMES[1:]}
IRISH = {"cork": [(-8.25, 51.7), (-9.5, 50.0)], "ireland": [(-8.25, 51.7), (-9.5, 50.0)], "waterford": [(-7.0, 52.0), (-8.5, 50.6)],
         "dublin": [(-5.8, 53.25), (-5.6, 52.3), (-6.3, 51.6), (-8.0, 50.3)]}
LOCAL = {   # transfers within Australia: (from, colony) -> waypoints
    ("hobart", "nsw"): [(147.45, -43.05), (147.6, -43.3), (148.1, -43.3), (148.5, -42.6), (148.9, -40.5), (150.4, -37.6), (151.4, -35.2), (151.35, -33.84)],
    ("sydney", "vdl"): [(151.35, -33.84), (151.4, -35.2), (150.4, -37.6), (148.9, -40.5), (148.5, -42.6), (148.1, -43.3), (147.6, -43.3), (147.45, -43.05)],
    ("sydney", "nfk"): [(151.35, -33.84), (152.5, -33.6), (158.0, -31.5), (167.9, -29.15)],
    ("norfolk", "vdl"): [(167.9, -29.15), (160.0, -36.0), (150.0, -42.0), (148.3, -43.3), (147.6, -43.3), (147.45, -43.05)],
    ("adelaide", "nsw"): [(138.3, -35.1), (138.15, -35.62), (138.6, -36.0), (140.5, -38.3), (141.0, -39.3), (143.7, -39.25)] + BASS,
    ("swan", "nsw"): [(114.3, -32.3), (114.0, -35.2), (117.0, -37.2), (127.0, -36.6), (136.0, -37.6), (141.0, -39.3), (143.7, -39.25)] + BASS,
    ("portphillip", "vdl"): [(144.6, -38.4), (145.0, -39.0), (147.2, -39.3), (148.6, -39.2), (149.0, -40.5), (148.5, -42.6), (148.1, -43.3), (147.6, -43.3), (147.45, -43.05)],
}


def waypoints(port, ck):
    lat, lon = PORTS[port][1], PORTS[port][2]; end = (COL[ck]["ll"][1], COL[ck]["ll"][0])
    reg = PORTS[port][3]
    if reg == "Within Australia":
        return [(lon, lat)] + LOCAL[(port, ck)] + [end]
    if reg == "India and the Indian Ocean":
        return [(lon, lat)] + FROM_IND[port] + TOI[ck] + [end]
    if reg == "Other colonies":
        tail = ATL[ATL.index((-31.0, -14.0)) + 1:] if port != "cape" else [(45.0, -41.5), (75.0, -42.0), (100.0, -41.0)]
        return [(lon, lat)] + FROM_OTHER[port] + tail + TO[ck] + [end]
    if reg == "Ireland":
        return [(lon, lat)] + IRISH[port] + ATL + TO[ck] + [end]
    start = OUT.get(port, [])
    return [(lon, lat)] + start + CH[(1 if port in ("plymouth", "devonport", "falmouth", "landsend", "dartmouth", "torbay") else 0):] + ATL + TO[ck] + [end]


def smooth(pts, n=10):
    """Centripetal Catmull-Rom through the waypoints, n points per segment."""
    P = np.array(pts, float); P = np.vstack([P[0], P, P[-1]]); out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return np.array(out)


def km(a, b):
    p1, p2, l1, l2 = map(np.radians, (a[1], b[1], a[0], b[0]))
    return 6371 * 2 * np.arcsin(np.sqrt(np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin((l2 - l1) / 2) ** 2))


V = pd.read_csv(f"{SRC}/voyage_rows.csv", keep_default_na=False)
pairs = sorted({(p, c) for p, c in zip(V.port, V.list) if p})
ROUTES = {}; bad = []
for p, c in pairs:
    if p == "swan" and c == "nsw" or True:
        pass
    wp = waypoints(p, c)
    line = smooth(wp, 6)
    # land check: ignore the first and last 60 km (harbours and estuaries)
    d = np.r_[0, np.cumsum([km(line[i], line[i + 1]) for i in range(len(line) - 1)])]
    lead = {"calcutta": 200, "quebec": 450, "london": 90, "woolwich": 90, "deptford": 90}.get(p, 60)
    mid = line[(d > lead) & (d < d[-1] - 60)]
    hits = [tuple(np.round(q, 2)) for q in mid if LAND.contains(Point(q[0], q[1]))]
    if hits:
        bad.append((p, c, hits[:5]))
    ROUTES[f"{p}|{c}"] = {"km": int(round(d[-1])), "coords": [[round(float(x), 3), round(float(y), 3)] for x, y in line]}
assert not bad, bad
jsave(ROUTES, f"{DATA}/routes.json")
print("countries", len(feats), "world", os.path.getsize(f"{DATA}/world.json") // 1024, "KB; routes", len(ROUTES), "longest", max((v["km"], k) for k, v in ROUTES.items()))
