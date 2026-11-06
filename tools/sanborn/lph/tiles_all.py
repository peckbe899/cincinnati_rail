"""TILES_ALL (2026-10-20, later): the full tiles_n renderer. The 1922 underlay halves (POLY22) are no longer drawn here:
Ben asked for 1922 on its own layer (tiles_22, cuf/tiles22.py). REDO=frame,frame re-renders the tiles those frames touch
(REDO=22 means the POLY22 halves); old files renamed *.<BAK> (env BAK, default pre_all).
VOLUME 3 REST (2026-10-20): adds lph/tf_ext3.json (REDO defaults to all its frames) and lph/panels_ext3.json.
SHEET 168 REFIT (2026-10-19): re-renders only the tiles that frame 168 touches (old and new placement); renamed copies *.pre168.
EXTENSION (2026-10-18): adds the frames of lph/tf_ext.json and re-renders only the tiles they touch.
Deck + north Sanborn tiles for the Mill Creek Deck page: every frame of lph/tf_all.json (Lower Price Hill frames bent onto
the 1922 plates by lph/tps.pkl), 512 m webp tiles at 0.25 m with alpha, plus a 2 m overview. Each pixel goes to the frame
it lies deepest inside (paper mask; panel frames keep their own panel). Writes deckpage/tiles_n/ and lph/sheets_n.json.
  python3 tiles_n.py [start_index]   (resumable: existing tiles are skipped)"""
try: import _ws  # Sanborn paths: tools/sanborn/_ws.py, configs/sanborn_paths.json (was the Topography workspace scratchpad and the chat uploads)
except ImportError: import os as _o, sys as _s; _s.path.append(_o.path.normpath(_o.path.join(_o.path.dirname(_o.path.abspath(__file__)), '..'))); import _ws
import json, os, sys, pickle, collections, numpy as np, cv2
from PIL import Image
SP = _ws.DATA
sys.path.insert(0, _ws.CODE + 'lph'); sys.path.insert(0, _ws.CODE + 'sbg')
import mosn, tps
from sb import find
from shapely.geometry import MultiPoint, Point, box, Polygon
from matplotlib.path import Path
Image.MAX_IMAGE_PIXELS = None
OUT = SP + 'deckpage/tiles_n/'; os.makedirs(OUT, exist_ok=True)
RES, T, CG = 0.25, 512, 8                  # tile size m, coarse warp grid every 8 px (2 m)
NP = int(T / RES)
TF = json.load(open(SP + 'lph/tf_all.json')); TF.update(json.load(open(SP + 'lph/tf_ext.json'))); TFX = json.load(open(SP + 'lph/tf_ext2.json')); TF.update(TFX); TFX3 = json.load(open(SP + 'lph/tf_ext3.json')); TF.update(TFX3); MOD = pickle.load(open(SP + 'lph/tps.pkl', 'rb'))
WARP = tps.warpfn_factory(TF, MOD)
R = pickle.load(open(SP + 'lph/obs_all.pkl', 'rb'))['R']
PX = json.load(open(SP + 'lph/panels_ext.json')); PX.update(json.load(open(SP + 'lph/panels_ext2.json'))); PX.update(json.load(open(SP + 'lph/panels_ext3.json')))   # extension panel frames: page-px polygons each keeps
FP = collections.defaultdict(list)
for r in R: FP[r['fr']].append((r['x'], r['y']))
# panels: boxes from the pick notes; inset frames of 627 / 628 keep the hull of their own picks (buffered 800 px), and
# the main frames drop it
KEEP = {k: [Polygon([(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])])] for k, v in mosn.PANEL_KEEP.items() for b in v}
DROP = {k: [Polygon([(b[0], b[1]), (b[2], b[1]), (b[2], b[3]), (b[0], b[3])])] for k, v in mosn.PANEL_DROP.items() for b in v}
# panel lines read off the sheets: 627, heavy line from the top edge at x 4480 to (5550, 3950), then east (inset upper right);
# 628, heavy diagonal from (430, 7680) to the right edge at y 3910 (inset below it)
INSET = {627: Polygon([(4480, -10), (5550, 3950), (6700, 4030), (6700, -10)]),
         628: Polygon([(300, 7900), (300, 7760), (6700, 3870), (6700, 7900)])}
for s, ins in INSET.items(): KEEP[f'{s}i'] = [ins]; DROP[f'{s}m'] = [ins]
for f, poly in PX.items(): KEEP[f] = [Polygon(poly)]
# 1922 atlas underlay (Ben, 2026-10-13: fill between sheets 522 and 608; the Camp Washington strip east of the canal bed;
# the crossings): vol. 1 plate halves fitted in lph/tf22_cw.json, drawn only where no 1904 sheet reaches. Each keeps a
# polygon of its mapped area in page px (key boxes, title blocks, margins and other plates' blank areas left out).
TF22 = json.load(open(SP + 'lph/tf22_cw.json'))
POLY22 = {
    '22-34L': [(90, 90), (6175, 90), (6175, 6000), (4400, 6000), (4400, 6750), (90, 6750)],
    '22-37L': [(100, 60), (6272, 60), (6272, 7470), (100, 7470)],
    '22-37R': [(0, 60), (3500, 60), (3500, 2200), (5400, 2200), (5400, 4100), (3300, 4100), (3300, 7470), (0, 7470)],
    '22-34R': [(0, 90), (4800, 90), (4800, 700), (6009, 700), (6009, 7700), (1000, 7700), (1000, 6000), (0, 6000)],
    '22-16R': [(0, 0), (5050, 0), (5039, 356), (4890, 1273), (4750, 2128), (4514, 3494), (4429, 4081), (4285, 5076), (4065, 6636), (3950, 7796), (0, 7796)],
}
for _h in POLY22: TF[_h] = TF22[_h[3:]]
SCALE = {f: float(np.hypot(p[0], p[2]) if len(p) == 6 else np.hypot(p[0], p[1])) for f, p in TF.items()}   # m per px
class Cache:
    def __init__(self, n=7): self.n = n; self.d = collections.OrderedDict()
    def get(self, s):
        if s in self.d: self.d.move_to_end(s); return self.d[s]
        im = cv2.imread(find(s), cv2.IMREAD_COLOR)
        if len(self.d) >= self.n: self.d.popitem(last=False)
        self.d[s] = im; return im
IMG = Cache()
MASK = {}
def pmask(s):
    if isinstance(s, str) and s.startswith('22-') and s not in MASK:
        im = IMG.get(s); H, W = im.shape[:2]; m = np.zeros((H // 8 + 1, W // 8 + 1), np.uint8)
        cv2.fillPoly(m, [np.array([(x / 8, y / 8) for x, y in POLY22[s]], np.int32)], 1); m = m.astype(bool)
        from scipy import ndimage as _ndi
        MASK[s] = (m, _ndi.distance_transform_edt(m))
    if s not in MASK:
        im = IMG.get(s)[:, :, ::-1]; m, d = mosn.page_mask(s, im); MASK[s] = (m, d)
    return MASK[s]
def sheet(f): return f if str(f).startswith('22-') else mosn.sheet_of(f)
def footprint(f):
    s = sheet(f); m, _ = pmask(s); ys, xs = np.nonzero(m[::4, ::4]); xs = xs * 32.0; ys = ys * 32.0
    pts = np.c_[xs, ys]
    for poly in KEEP.get(f, []): pts = pts[Path(np.array(poly.exterior.coords)).contains_points(pts)]
    for poly in DROP.get(f, []): pts = pts[~Path(np.array(poly.exterior.coords)).contains_points(pts)]
    E, N = mosn.ap(TF[f], pts[:, 0], pts[:, 1])
    if f in MOD: dE, dN = tps.disp(f, E, N, MOD); E = E + dE; N = N + dN
    return np.c_[E, N]
def main(start=0):
    FB = {}; HULL = {}
    for f in TF:
        p = footprint(f)
        if len(p) < 3: continue
        h = MultiPoint(p).convex_hull; HULL[f] = h; FB[f] = h.bounds
        print('frame', f, [round(v) for v in h.bounds], flush=True)
    x0 = min(b[0] for b in FB.values()); y0 = min(b[1] for b in FB.values()); x1 = max(b[2] for b in FB.values()); y1 = max(b[3] for b in FB.values())
    X0 = int(np.floor(x0 / T) * T); Y0 = int(np.floor(y0 / T) * T)
    tiles = [(tx, ty) for ty in range(Y0, int(y1) + 1, T) for tx in range(X0, int(x1) + 1, T)
             if any(HULL[f].intersects(box(tx, ty, tx + T, ty + T)) for f in HULL)]
    # serpentine order so neighbouring tiles share sheets in the cache
    rows = collections.defaultdict(list)
    for t in tiles: rows[t[1]].append(t)
    order = []
    for i, ty in enumerate(sorted(rows)): order += sorted(rows[ty], reverse=bool(i % 2))
    json.dump(dict(size=T, res=RES, tiles=[list(t) for t in order]), open(OUT + 'index.json', 'w'))
    print('tiles', len(order), flush=True)
    RF = os.environ['REDO'].split(',') if os.environ.get('REDO') else list(TFX3)          # frames whose tiles are re-rendered (2026-10-19: 168 refit, then 159 bent)
    if RF == ['22']: RF = list(POLY22)
    redo = [t for t in order if any(HULL[f].intersects(box(t[0], t[1], t[0] + T, t[1] + T)) for f in RF)]
    for t in redo:
        fn = OUT + f'{t[0]}_{t[1]}.webp'
        if os.path.exists(fn): os.replace(fn, fn + '.' + os.environ.get('BAK', 'pre_all'))
    print('re-render', len(redo), flush=True)
    nc = NP // CG + 1
    for k, (tx, ty) in enumerate(order):
        if k < start or os.path.exists(OUT + f'{tx}_{ty}.webp'): continue
        tb = box(tx, ty, tx + T, ty + T); frs = [f for f in HULL if HULL[f].intersects(tb) and f not in POLY22]      # 1922 halves: own layer now
        jj, ii = np.meshgrid(np.arange(nc) * CG, np.arange(nc) * CG)
        Ec = tx + (jj + 0.5) * RES; Nc = ty + T - (ii + 0.5) * RES
        acc = np.zeros((NP, NP, 3), np.uint8); best = np.zeros((NP, NP), np.float32); al = np.zeros((NP, NP), np.uint8)
        for f in frs:
            s = sheet(f)
            xc, yc = WARP(f, Ec, Nc)
            mx = cv2.resize(xc.astype(np.float32), (NP + CG, NP + CG), interpolation=cv2.INTER_LINEAR)[:NP, :NP]
            my = cv2.resize(yc.astype(np.float32), (NP + CG, NP + CG), interpolation=cv2.INTER_LINEAR)[:NP, :NP]
            m, d = pmask(s)
            xi = np.clip((mx / 8).astype(np.int32), 0, m.shape[1] - 1); yi = np.clip((my / 8).astype(np.int32), 0, m.shape[0] - 1)
            im = IMG.get(s)
            ok = (mx >= 0) & (my >= 0) & (mx < im.shape[1] - 1) & (my < im.shape[0] - 1) & m[yi, xi]
            if f in KEEP or f in DROP:
                q = np.c_[mx[::4, ::4].ravel(), my[::4, ::4].ravel()]; sel = np.ones(len(q), bool)
                for poly in KEEP.get(f, []): sel &= Path(np.array(poly.exterior.coords)).contains_points(q)
                for poly in DROP.get(f, []): sel &= ~Path(np.array(poly.exterior.coords)).contains_points(q)
                sel = sel.reshape(mx[::4, ::4].shape)
                ok &= cv2.resize(sel.astype(np.uint8), (NP, NP), interpolation=cv2.INTER_NEAREST).astype(bool)
            dep = d[yi, xi] * 8 * SCALE[f] + (0.0 if f in POLY22 else 1e6)     # any 1904 sheet wins over the 1922 underlay
            take = ok & (dep > best)
            if not take.any(): continue
            rgb = cv2.remap(im, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            acc[take] = rgb[take]; best[take] = dep[take]; al[take] = 255
        if not al.any(): continue
        rgba = np.dstack([acc[:, :, ::-1], al])
        Image.fromarray(rgba, 'RGBA').save(OUT + f'{tx}_{ty}.webp', quality=72, method=4)
        print('tile', k, tx, ty, len(frs), flush=True)
    # index lists only the tiles that were written (empty slots would be requested again and again)
    json.dump(dict(size=T, res=RES, tiles=[list(t) for t in order if os.path.exists(OUT + f'{t[0]}_{t[1]}.webp')]), open(OUT + 'index.json', 'w'))
    # overview (2 m) from the tiles
    ex = [min(t[0] for t in order), min(t[1] for t in order), max(t[0] for t in order) + T, max(t[1] for t in order) + T]
    sc = int(2.0 / RES); W, H = int((ex[2] - ex[0]) / 2.0), int((ex[3] - ex[1]) / 2.0)
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    for tx, ty in order:
        fn = OUT + f'{tx}_{ty}.webp'
        if not os.path.exists(fn): continue
        t = Image.open(fn).convert('RGBA').resize((NP // sc, NP // sc), Image.LANCZOS)
        ov.paste(t, (int((tx - ex[0]) / 2.0), int((ex[3] - ty - T) / 2.0)), t)
    ov.save(OUT + 'overview.webp', quality=70, method=4)
    json.dump(dict(E0=ex[0], N0=ex[1], E1=ex[2], N1=ex[3], res=2), open(OUT + 'overview.json', 'w'))
    # sheet index outlines (hull of each frame's paper footprint)
    sh = []
    for f, h in HULL.items():
        if f in POLY22:
            mr = h.minimum_rotated_rectangle
            sh.append(dict(sheet='1922 pl. ' + f[3:], vol='1922 vol. 1', poly=[[round(x, 1), round(y, 1)] for x, y in list(mr.exterior.coords)[:4]])); continue
        s = mosn.sheet_of(f); vol = '1904 vol. ' + ('1' if s < 100 else '2' if s <= 200 else '3' if s < 311 else '4' if s < 450 else '5' if s < 600 else '6')
        mr = h.minimum_rotated_rectangle
        sh.append(dict(sheet=f, vol=vol, poly=[[round(x, 1), round(y, 1)] for x, y in list(mr.exterior.coords)[:4]]))
    json.dump(sh, open(SP + 'lph/sheets_ext3.json', 'w'))
    print('done', flush=True)
if __name__ == '__main__': main(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
