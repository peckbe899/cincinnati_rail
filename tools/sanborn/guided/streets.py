"""Shared by the guided-reading tools (14 November 2026): today's streets on a 1922 plate, and the plate's current model.

Today's streets are the named OSM ways (primary to residential) that fall on the plate. A street is one connected run of
ways with exactly the same name: two runs of one name that do not touch are two streets, and two names the old name key
runs together (Rose Hill Avenue and Rose Hill Lane on plate 80) stay two streets. Each gets a street id (sid), which the
crossings, the traced points and the street set all carry, so a street is never grouped by its name alone.
"""
import json, os, re, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..')).replace(os.sep, '/') + '/'
for d in ('tools/sanborn/joint', 'tools/sanborn', 'tools/sanborn/sbg'): sys.path.insert(0, ROOT + d)
import _ws, jointlib as J  # noqa: E402
from scipy.interpolate import LinearNDInterpolator  # noqa: E402
from shapely.geometry import shape, box, Point, LineString  # noqa: E402
from shapely.ops import linemerge, unary_union  # noqa: E402
SP = _ws.DATA
KEEP = {'primary', 'secondary', 'tertiary', 'residential', 'unclassified', 'living_street', 'trunk'}
OSM = ('lph/osm_north.geojson', 'basin/osm_basin.geojson', 'lph/osm_east.geojson', 'lph/osm_norwood.geojson', 'lph/osm_west.geojson')

def slug(name): return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')

class Plate:
    def __init__(self, N):
        self.N = N; self.pid = f'22-{N}'
        self.A = np.load(SP + f'cufp/{N}/png_alpha_s4.npy'); self.H, self.W = self.A.shape[0] * 4, self.A.shape[1] * 4
        gx, gy = np.meshgrid(np.linspace(-300, self.W + 300, 140), np.linspace(-300, self.H + 300, 110)); P = np.c_[gx.ravel(), gy.ravel()]
        Wd = J.world_many(self.pid, P, 'complete'); self._inv = LinearNDInterpolator(Wd, P); self.box = box(*Wd.min(0), *Wd.max(0))
    def px(self, E, Nn): return self._inv(np.array([[E, Nn]]))[0]
    def px_many(self, EN): return self._inv(np.asarray(EN, float))
    def world(self, xy): return J.world_many(self.pid, np.asarray(xy, float), 'complete')
    def on_plate(self, c, margin_px=60):
        if np.isnan(c).any() or not (0 <= c[0] < self.W and 0 <= c[1] < self.H): return False
        yy, xx = int(c[1]) // 4, int(c[0]) // 4; m = margin_px // 4
        return self.A[max(0, yy - m):yy + m, max(0, xx - m):xx + m].max() > 0
    def inside(self, c):
        if np.isnan(c).any() or not (0 <= c[0] < self.W and 0 <= c[1] < self.H): return False
        return self.A[int(c[1]) // 4, int(c[0]) // 4] > 0
    def way(self, l, pt):              # direction of a street on the plate at a point, in words
        t = l.project(pt); a = l.interpolate(max(0, t - 15)); b = l.interpolate(min(l.length, t + 15))
        d = self.px(b.x, b.y) - self.px(a.x, a.y); ang = np.degrees(np.arctan2(-d[1], d[0])) % 180
        return 'left-right' if ang < 22.5 or ang >= 157.5 else ('lower-left to upper-right' if ang < 67.5 else ('up-down' if ang < 112.5 else 'upper-left to lower-right'))
    def streets(self):
        """[{sid, name, geom}] for today's streets on and near the plate"""
        by = {}
        B = self.box.buffer(200)
        for f in OSM:
            for ft in json.load(open(SP + f, encoding='utf8'))['features']:
                p, g = ft['properties'], ft['geometry']
                if not g or 'Line' not in g['type'] or p.get('highway') not in KEEP or not p.get('name'): continue
                s = shape(g)
                if s.intersects(B): by.setdefault(' '.join(p['name'].split()), []).append(s)
        out = []
        for name, gs in sorted(by.items()):
            u = unary_union(gs); m = linemerge(u) if u.geom_type != 'LineString' else u
            parts = list(getattr(m, 'geoms', [m]))
            groups = []                                   # connected runs: parts within 3 m of each other
            for q in parts:
                hit = [g for g in groups if any(q.distance(r) < 3 for r in g)]
                for g in hit: groups.remove(g)
                groups.append(sum(hit, []) + [q])
            groups.sort(key=lambda g: (-sum(r.length for r in g)))
            for i, g in enumerate(groups):
                geom = linemerge(g) if len(g) > 1 else g[0]
                out.append(dict(sid=slug(name) + (f'#{i + 1}' if len(groups) > 1 else ''), name=name, geom=geom))
        return out
    def sid_at(self, streets, name, E, Nn, within=25.0):
        """the street id of the street of this name nearest a world point"""
        c = [(s['geom'].distance(Point(E, Nn)), s['sid']) for s in streets if s['name'] == ' '.join(name.split())]
        c = [t for t in c if t[0] < within]
        return min(c)[1] if c else None

def render_crop(N, box_, out, marks=()):
    """a plate crop with the reading grid (tools/sanborn/sbg/sb.py render), and red crosses at plate points"""
    import sb
    from PIL import Image, ImageDraw
    sb.render(f'22-{N}', tuple(box_), out)
    if marks:
        im = Image.open(out); s = im.size[0] / (box_[2] - box_[0]); d = ImageDraw.Draw(im)
        for x, y in marks:
            X, Y = (x - box_[0]) * s, (y - box_[1]) * s
            d.line([(X - 14, Y), (X - 5, Y)], fill=(230, 0, 0), width=3); d.line([(X + 5, Y), (X + 14, Y)], fill=(230, 0, 0), width=3)
            d.line([(X, Y - 14), (X, Y - 5)], fill=(230, 0, 0), width=3); d.line([(X, Y + 5), (X, Y + 14)], fill=(230, 0, 0), width=3)
        im.save(out, quality=90)
