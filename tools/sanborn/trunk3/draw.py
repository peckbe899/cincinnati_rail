try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import sys, json, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
from shapely.geometry import LineString, Point, box, shape, Polygon
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'trunk3'); sys.path.insert(0, _ws.CODE + 'trunk2')
import build as B, north as N, ctx
from creek_up import WAT_UP as WAT
import geo4 as Q
FR = N.FR
COL = {'X2': '#c2185b', 'ORR': '#c2185b', 'B': '#ef6c00', 'Dayton': '#111111', 'Norwood': '#555555', 'TV': '#6a1b9a'}
def col(k): return next(v for a, v in COL.items() if k.startswith(a))
def base(ax, Bx):
    for f in ctx.BJ['features']:
        p = f['properties']; g = shape(f['geometry'])
        if not g.intersects(Bx): continue
        if p.get('layer') == 'block' and g.geom_type == 'Polygon': ax.fill(*g.exterior.xy, color='#eeeeee', lw=0)
        if p.get('layer') == 'street' and g.geom_type == 'LineString':
            gg = g.buffer(p.get('width_m', 12) / 2, cap_style=2)
            for qq in getattr(gg, 'geoms', [gg]): ax.fill(*qq.exterior.xy, color='#d6d6d6', lw=0)
    for f in ctx.H['features']:
        if f['properties'].get('layer') == 'hw_piece':
            g = shape(f['geometry'])
            if g.intersects(Bx):
                gg = g.buffer(f['properties']['w'] / 2, cap_style=2)
                for qq in getattr(gg, 'geoms', [gg]): ax.fill(*qq.exterior.xy, color='#f6d5e4', lw=0)
    HW = json.load(open(SP + 'hwy/data.json')); HO = HW['origin']
    for q in HW['segs']:
        if q['t'] in ('Parkway hybrid', 'Boulevard'):
            c = np.array(q['c']) + HO
            if LineString(c).intersects(Bx): ax.plot(c[:, 0], c[:, 1], color='#e8a0c0', lw=0.8, ls='--')
    for qq in getattr(WAT, 'geoms', [WAT]):
        if qq.intersects(Bx): ax.fill(*qq.exterior.xy, color='#9ecae1', lw=0)
    # existing tracks south of the split (installed), and Norwood Central
    for f in ctx.T['features']:
        g = f['geometry']; p = f['properties']
        if g['type'] != 'LineString': continue
        nm = p.get('name') or ''
        if nm.startswith(('APEx Southwest Chief', 'APEx Transcontinental')):
            c = np.array(g['coordinates'])[:, :2]
            if LineString(c).intersects(Bx): ax.plot(c[:, 0], c[:, 1], color='#999', lw=0.5, ls=':')
            continue
        if nm.startswith(('APEx Dayton', 'APEx Norwood', 'Lower-level pair')):
            c = np.array(g['coordinates'])[:, :2]; s = np.array([Q.TR.proj(q) for q in c]); c = c[s <= N.S0 + 1]
            col_ = '#111' if nm.startswith('APEx') else '#c2185b'
            if len(c) > 1: ax.plot(c[:, 0], c[:, 1], color=col_, lw=0.7)
    for t in ctx.C['tracks']:
        if t.get('pid') == 'R-B-715612-4338596':
            c = np.array(t['c']); s = np.array([Q.TR.proj(q) for q in c]); c = c[s <= N.S0 + 1]; ax.plot(c[:, 0], c[:, 1], color='#ef6c00', lw=0.7)
    for f in ctx.NW['features']:
        g = f['geometry']
        if g['type'] == 'LineString': c = np.array(g['coordinates']); ax.plot(c[:, 0], c[:, 1], color='#1565c0', lw=0.6)
def plats(L):
    out = {}
    for st, s0, s1 in (('Ivorydale', N.S_IV0, N.S_IV1), ('Elmwood Place', N.S_EP0, N.S_EP1)):
        ss = np.arange(s0, s1 + 0.1, 2.0); lo = N.o_b(0)(ss) + 1.75; hi = N.o_b(1)(ss) - 1.75
        out[st] = np.vstack([N.FD.at(ss, lo), N.FD.at(ss, hi)[::-1]])
    return out
def plan(L, x0, x1, y0, y1, fn, title, notes=(), w=15):
    Bx = box(x0, y0, x1, y1); fig, ax = plt.subplots(figsize=(w, w * (y1 - y0) / (x1 - x0)))
    base(ax, Bx)
    for st, ring in plats(L).items(): ax.add_patch(MPoly(ring, closed=True, color='#ffcc80', lw=0))
    for k, v in L.items():
        if k.startswith('_') or v['kind'] == 'ref': continue
        c = v['c']; ax.plot(c[:, 0], c[:, 1], color=col(k), lw=0.9)
    for xy, txt, ha in notes:
        if Bx.contains(Point(xy)): ax.annotate(txt, xy, fontsize=7, ha=ha, va='center', bbox=dict(fc='white', ec='none', alpha=0.8, pad=1))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal'); ax.set_title(title, fontsize=10); ax.tick_params(labelsize=6)
    fig.savefig(fn, dpi=150, bbox_inches='tight'); plt.close(fig)
def strip(L, opt, ax, s0=2900, s1=4200, prof=None):
    """the Norwood approach in its own frame: s along, o across (exaggerated 4x)"""
    for k, v in L.items():
        if k.startswith('_') or v['kind'] == 'ref': continue
        so = np.array([FR.nw_so(q) for q in v['c']]); sel = (so[:, 0] >= s0 - 5) & (so[:, 0] <= s1 + 5)
        if sel.any(): ax.plot(so[sel, 0], so[sel, 1], color=col(k), lw=1.0)
    for f in ctx.NW['features']:
        g = f['geometry']
        if g['type'] == 'LineString':
            so = np.array([FR.nw_so(q) for q in g['coordinates']]); sel = so[:, 0] <= s1 + 5; ax.plot(so[sel, 0], so[sel, 1], color='#1565c0', lw=0.6)
    for snw, nm in ((3023, 'Reading Rd'), (3939, 'Section Ave')): ax.axvspan(snw - 8, snw + 8, color='#ddd'); ax.text(snw, 26, nm, fontsize=6, ha='center')
    ax.set_xlim(s0, s1); ax.set_ylim(-32, 30); ax.set_ylabel('across (m, north +)', fontsize=7); ax.tick_params(labelsize=6); ax.grid(lw=0.2)
