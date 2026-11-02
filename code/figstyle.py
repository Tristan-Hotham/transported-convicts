"""House style for static figures: fonts (static instances cut from the variable Fraunces in /home/claude/ref/fonts,
written to WORK), the palette, Natural Earth outlines in the Equal Earth projection, and the voyage routes."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Polygon as MPoly
from matplotlib.collections import LineCollection
import numpy as np
from pyproj import Transformer
from common import *

FD = os.path.join(WORK, "fonts"); os.makedirs(FD, exist_ok=True)
if not os.path.exists(f"{FD}/Fraunces-Black.ttf"):
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer
    for w, nm in ((900, "Black"), (700, "Bold")):
        instancer.instantiateVariableFont(TTFont(f"{FONTS}/FrauncesVar.ttf"), {"wght": w, "opsz": 144, "SOFT": 0, "WONK": 0}).save(f"{FD}/Fraunces-{nm}.ttf")
DISP = fm.FontProperties(fname=f"{FD}/Fraunces-Black.ttf")
DISPB = fm.FontProperties(fname=f"{FD}/Fraunces-Bold.ttf")
SERP = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-Regular.ttf")
SERB = fm.FontProperties(fname=f"{FONTS}/SourceSerif4-Semibold.ttf")
for f in ("IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf"):
    fm.fontManager.addfont(f"{FONTS}/{f}")
MONO = "IBM Plex Mono"
plt.rcParams.update({"font.family": MONO, "font.size": 12, "axes.edgecolor": "#646A70", "axes.labelcolor": "#1E2126",
                     "xtick.color": "#646A70", "ytick.color": "#646A70"})
BG, FG, MUT, LAND, RULE, SEA = "#F6F3EC", "#1E2126", "#646A70", "#E2DCCD", "#DED7C9", "#EBEFF0"
INK, WORLDC = "#1F2F4D", "#6E4C9A"
CCOL = {k: COL[k]["c"] for k in CK}

EE = Transformer.from_crs(4326, 8857, always_xy=True)
W = jload(f"{DATA}/world.json")
ROUTES = jload(f"{DATA}/routes.json")


def rings(geom):
    cs = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    for poly in cs:
        yield np.array(poly[0])


SHAPES = []
for f in W["features"]:
    for ring in rings(f["geometry"]):
        x, y = EE.transform(np.clip(ring[:, 0], -179.9, 179.9), np.clip(ring[:, 1], -89.5, 89.5))
        SHAPES.append((f["properties"]["iso"], np.column_stack([x, y]), ring))


def proj(lon, lat):
    return EE.transform(np.asarray(lon), np.asarray(lat))


def ext(lon0, lon1, lat0, lat1):
    x0, _ = proj(lon0, 0); x1, _ = proj(lon1, 0); _, y0 = proj(0, lat0); _, y1 = proj(0, lat1)
    return (float(x0), float(x1), float(y0), float(y1))


EXT_VOY = ext(-75, 180, -50, 61)


def world(ax, lw=.3, ext=EXT_VOY, ec="#FFFFFF", land=LAND, z=1, skip_ata=True):
    for iso, p, _ in SHAPES:
        if skip_ata and iso == "ATA":
            continue
        ax.add_patch(MPoly(p, closed=True, fc=land, ec=ec, lw=lw, zorder=z))
    ax.set_xlim(ext[0], ext[1]); ax.set_ylim(ext[2], ext[3]); ax.set_aspect("equal"); ax.axis("off")


def route_xy(key):
    c = np.array(ROUTES[key]["coords"]); x, y = proj(c[:, 0], c[:, 1]); return np.column_stack([x, y])


def routes(ax, V, alpha=.07, lw_unknown=.7, lw_scale=.075, z=3, jitter=0.0):
    """Every voyage as a line on its route, coloured by colony; width by convicts where given."""
    segs, cols, lws = [], [], []
    rng = np.random.default_rng(7)
    for r in V.itertuples():
        if not r.route:
            continue
        xy = route_xy(r.route)
        if jitter:
            n = len(xy); t = np.sin(np.linspace(0, np.pi, n))[:, None]; xy = xy + rng.normal(0, jitter, 2)[None, :] * t
        segs.append(xy); cols.append(CCOL[r.colony])
        lws.append(lw_unknown if np.isnan(r.convicts) else .9 + lw_scale * np.sqrt(r.convicts))
    ax.add_collection(LineCollection(segs, colors=cols, linewidths=lws, alpha=alpha, zorder=z, capstyle="round"))


def spines(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


# ---------- automatic label placement: labels go on open sea (or paper), never over land, routes, circles or labels ----------
from shapely.geometry import shape as _shape, box as _box, Point as _Pt, LineString as _LS, Polygon as _Poly
from shapely.ops import unary_union as _union
from shapely.prepared import prep as _prep
_LAND = None


def land_proj(margin=2.5e4, min_km2=1500):
    """Natural Earth 1:50m land in Equal Earth metres, buffered by margin. Islands under min_km2 (specks of a pixel or
    less at these scales, such as the Cocos and Chagos islands) are not treated as land for label placement."""
    global _LAND
    if _LAND is None:
        polys = []
        for f in jload(f"{GEO}/ne_50m_land.geojson")["features"]:
            g = _shape(f["geometry"]); gs = g.geoms if g.geom_type == "MultiPolygon" else [g]
            for q in gs:
                xy = np.array(q.exterior.coords); x, y = EE.transform(np.clip(xy[:, 0], -179.99, 179.99), np.clip(xy[:, 1], -89.9, 89.9))
                pg = _Poly(np.column_stack([x, y])).buffer(0)
                if pg.area >= min_km2 * 1e6:
                    polys.append(pg)
        _LAND = _union(polys)
    return _LAND.buffer(margin) if margin else _LAND


class Placer:
    """Place text labels on a map axis without touching land, drawn data or each other."""
    def __init__(self, fig, ax, obstacles, margin=2.5e4, inset=1.5e5, markers=()):
        self.fig, self.ax, self.placed, self.failed, self.lines = fig, ax, [], [], []
        self.markers = [_Pt(x, y).buffer(r) for x, y, r in markers]          # leaders may not cross these
        self.land = _prep(land_proj(margin)); self.obs = _prep(obstacles) if obstacles is not None else None
        x0, x1 = ax.get_xlim(); y0, y1 = ax.get_ylim(); self.frame = _box(x0 + inset, y0 + inset, x1 - inset, y1 - inset)
        fig.canvas.draw(); self.ren = fig.canvas.get_renderer()

    def bbox(self, t, pad=3):
        bb = t.get_window_extent(self.ren)
        (x0, y0), (x1, y1) = self.ax.transData.inverted().transform([[bb.x0 - pad, bb.y0 - pad], [bb.x1 + pad, bb.y1 + pad]])
        return _box(x0, y0, x1, y1)

    def bad(self, b, allow_paper=False):
        if not self.frame.contains(b):
            return True
        return self.land.intersects(b) or (self.obs is not None and self.obs.intersects(b)) or any(b.intersects(o) for _, o in self.placed)

    def place(self, name, s, pref, window=16, step=1.0, target=None, lead_gap=2.5e5, lead_c=None, **kw):
        """Try positions on a grid around pref (nearest first). target=(lon, lat, r): the marker the label belongs to;
        if the label ends up more than lead_gap from the marker's edge, a thin leader is drawn, and the leader may not
        cross another label."""
        from shapely.ops import nearest_points
        lon0, lat0 = pref
        t = self.ax.text(0, 0, s, zorder=10, **kw)
        cands = sorted([(lon0 + dx * step, lat0 + dy * step) for dx in range(-window, window + 1) for dy in range(-window, window + 1)],
                       key=lambda q: (q[0] - lon0) ** 2 + (q[1] - lat0) ** 2)
        for lon, lat in cands:
            if abs(lat) > 85 or abs(lon) > 180: continue
            x, y = proj(lon, lat); t.set_position((float(x), float(y))); b = self.bbox(t)
            if self.bad(b):
                continue
            ln = None
            if target is not None:
                tx, ty = proj(target[0], target[1]); c = _Pt(float(tx), float(ty))
                if b.distance(c) - target[2] > lead_gap:
                    pb, _ = nearest_points(b, c); d = np.hypot(pb.x - c.x, pb.y - c.y)
                    ln = _LS([(pb.x, pb.y), (c.x + (pb.x - c.x) * target[2] / d, c.y + (pb.y - c.y) * target[2] / d)])
                    if any(ln.intersects(o) for _, o in self.placed) or any(ln.intersects(l) for _, l in self.lines) or \
                            any(m.intersects(ln) and not m.contains(c) for m in self.markers):
                        continue
            self.placed.append((name, b))
            if ln is not None:
                self.lines.append((name, ln)); self.ax.plot(*ln.xy, color=lead_c or kw.get("color", "#1E2126"), lw=.8, zorder=9)
            return t
        x, y = proj(lon0, lat0); t.set_position((float(x), float(y))); t.set_color("#FF00FF")   # visible in a debug render
        self.failed.append(name); self.placed.append((name, self.bbox(t))); return t

    def check(self):
        assert not self.failed, ("no clean spot for", self.failed)
        for nm, b in self.placed:
            assert not self.land.intersects(b), nm
            assert self.obs is None or not self.obs.intersects(b), nm
            assert not any(b.intersects(o) for n2, o in self.placed if n2 != nm), nm
        for nm, l in self.lines:
            assert not any(l.intersects(o) for n2, o in self.placed if n2 != nm), ("leader crosses a label", nm)


def obstacles(V, route_buf=1.6e5, circles=(), min_voyages=1):
    """Shapely geometry of every drawn route (buffered) and circle, in projected metres. min_voyages > 1 ignores routes
    drawn so faintly (one or two voyages) that a label's halo hides nothing."""
    cnt = V.route.value_counts()
    gs = [_LS(route_xy(k)).buffer(route_buf) for k in sorted(set(V.route)) if k and cnt[k] >= min_voyages]
    gs += [_Pt(x, y).buffer(r) for x, y, r in circles]
    return _union(gs)
