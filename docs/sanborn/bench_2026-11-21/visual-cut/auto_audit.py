"""Geometric audit of the lines the line editor would show for a plate (visual-cut, 21 Nov 2026). Reads only.

    python auto_audit.py N [N ...]        -> audit/N_audit.json, and a summary line per plate

Works on what Ben sees: clean(N_edges.json) (edit_server.clean, copied in vlib.py), not counting the sheet() lines.
Measured on every editor line / line end, no ground truth needed:
  open ends     a line end with no other editor-line end within 25 px and not touching another line's body (T), and more
                than 60 px in from the paper edge (ends at the paper edge are meant to stay open: Ben's rule).
    broken side    the open end faces a collinear editor line (angle < 4 deg, offset < 12 px) within 400 px: the gap
                   Ben joins with J. Gap = distance between the two ends.
    open corner    otherwise, another editor line not parallel (> 20 deg) whose infinite line meets this one within
                   200 px of this end and within 200 px of that line: Ben drags the end. Gap = distance to the meeting point.
    dangling       neither: a line end with nothing to meet within 200 px.
  street-side test   share of 'blank paper' in a band 12-40 px either side of the line (10-90 % of its length). A street
                   side has street (blank) on one side. 'both sides filled' -> candidate lot line / building wall / text;
                   'both sides blank' -> candidate line in open ground (pipe, rail, open land, bank).
  rail share     share of the line within 6 px of the rule bins railroad / streetcar (N_bins.png values 4, 5).
  line-net       mean P(line) under the line > 90/255 (outlines.py's dt).
  polygons       area (block mask piece), long line-network ridges inside the polygon (candidate merge), small ones.
Plate 44 only: every editor line is matched to Ben's street map (within 6 px and 10 deg, by share of length).
"""
import json, os, sys
import numpy as np
import cv2
from scipy.spatial import cKDTree
from vlib import load, SP, U, HERE

OUT = os.path.join(HERE, 'audit'); os.makedirs(OUT, exist_ok=True)


def samples(a, b, step=4.0, t0=0.1, t1=0.9):
    L = float(np.hypot(*(b - a))); n = max(3, int(L * (t1 - t0) / step)); t = np.linspace(t0, t1, n); return a + np.outer(t, b - a), L


def seg_point_dist(p, a, b):
    d = b - a; L2 = float(d @ d) or 1e-9; t = np.clip(((p - a) @ d) / L2, 0, 1); return float(np.hypot(*(p - (a + t * d)))), t


def intersect(a1, b1, a2, b2):
    d1, d2 = b1 - a1, b2 - a2; den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9: return None
    s = ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / den; return a1 + s * d1


def audit(n):
    D = load(n); W, H = D['W'], D['H']; full = D['full']
    a4 = np.load(SP + f'cufp/{n}/png_alpha_s4.npy').astype(np.uint8); dist4 = cv2.distanceTransform(np.pad(a4, 1), cv2.DIST_L2, 3)[1:-1, 1:-1] * (W / a4.shape[1])
    edge_d = lambda q: float(dist4[min(a4.shape[0] - 1, max(0, int(q[1] * a4.shape[0] / H))), min(a4.shape[1] - 1, max(0, int(q[0] * a4.shape[1] / W)))])
    hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV)
    ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))
    # paper colour: bright, low-saturation pixels on the paper
    al = D['alpha']; v = hsv[:, :, 2][al]; s_ = hsv[:, :, 1][al]
    sel = (v > np.percentile(v, 60)) & (s_ < np.percentile(s_, 50)); paper = np.median(full[al][sel], 0).astype(np.float32)
    blank = (~ink) & (np.abs(full.astype(np.int16) - paper.astype(np.int16)).max(2) < 28) & al
    del hsv
    bins = cv2.imread(U + f'{n}_bins.png', cv2.IMREAD_UNCHANGED)
    rail = np.isin(bins, (4, 5)).astype(np.uint8) if bins is not None else np.zeros((H, W), np.uint8)
    rail = cv2.dilate(rail, np.ones((13, 13), np.uint8)) > 0
    lp = cv2.GaussianBlur(D['pl'], (5, 5), 0)
    E = [dict(a=np.array(s['a'], float), b=np.array(s['b'], float), state=s['state'], polys=s.get('polys', [])) for s in D['shown']]
    ben = None
    if n == '44':
        sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
        ben = [(np.array(l['a'], float), np.array(l['b'], float), l['kind']) for l in sm['lines']]
    look = lambda img, q: img[np.clip(q[:, 1].round().astype(int), 0, H - 1), np.clip(q[:, 0].round().astype(int), 0, W - 1)]
    for e in E:
        a, b = e['a'], e['b']; q, L = samples(a, b); d = (b - a) / L; nrm = np.array([-d[1], d[0]])
        e['L'] = L
        sides = []
        for sg in (1, -1):
            pts = np.concatenate([q + nrm * sg * o for o in range(12, 41, 4)]); sides.append(float(look(blank, pts).mean()))
        e['blank_l'], e['blank_r'] = sides
        e['rail'] = float(look(rail, q).mean()); e['dt'] = bool(look(lp, samples(a, b, 2.0, 0.06, 0.94)[0]).mean() > 90)
        e['edge_d'] = edge_d((a + b) / 2)
        if ben is not None:
            hit = np.zeros(len(q), bool)
            for ba, bb, k in ben:
                bd = (bb - ba); bl = np.hypot(*bd)
                if bl < 1 or abs((bd / bl) @ d) < np.cos(np.radians(10)): continue
                t = np.clip(((q - ba) @ bd) / bl ** 2, 0, 1); dd = np.hypot(*(q - (ba + t[:, None] * bd)).T); hit |= dd <= 6
            e['on_ben'] = float(hit.mean())
    # open ends
    ends = [(i, k) for i in range(len(E)) for k in ('a', 'b')]
    P = np.array([E[i][k] for i, k in ends]); tree = cKDTree(P)
    res_ends = []
    for j, (i, k) in enumerate(ends):
        p = E[i][k]; other = E[i]['b' if k == 'a' else 'a']
        if edge_d(p) < 60: continue
        near = [m for m in tree.query_ball_point(p, 25.0) if ends[m][0] != i]
        if near: continue
        touch = any(seg_point_dist(p, E[m]['a'], E[m]['b'])[0] < 15 for m in range(len(E)) if m != i)
        if touch: continue
        d = (p - other); d /= np.hypot(*d); nd = np.array([-d[1], d[0]]); brk, cor = [], []
        for m in range(len(E)):
            if m == i: continue
            a2, b2 = E[m]['a'], E[m]['b']; d2 = (b2 - a2) / E[m]['L']; c = abs(d @ d2)
            if c > np.cos(np.radians(4)):   # collinear: same street side, broken
                if max(abs((a2 - p) @ nd), abs((b2 - p) @ nd)) > 12: continue
                for qq in (a2, b2):
                    if 0 < (qq - p) @ d < 400: brk.append(float(np.hypot(*(qq - p))))
            elif c < np.cos(np.radians(20)):  # another side: the corner is where the two meet
                x = intersect(other, p, a2, b2)
                if x is None: continue
                g = float(np.hypot(*(x - p))); dm = seg_point_dist(x, a2, b2)[0]
                if g < 200 and dm < 200 and (x - p) @ d > -30: cor.append(g + dm)   # Ben drags this end (and maybe the other line's end) to the meeting point
        kind, gap = ('broken', min(brk)) if brk else (('corner', min(cor)) if cor else ('dangling', None))
        res_ends.append(dict(line=i, end=k, at=p.round(1).tolist(), kind=kind, gap=None if gap is None else round(gap, 1), polys=E[i]['polys']))
    # polygons: area and line-network ridges inside
    bm = cv2.resize(D['bm'], (W, H), interpolation=cv2.INTER_NEAREST) > 127
    ncc, cc, st, cen = cv2.connectedComponentsWithStats(bm.astype(np.uint8), connectivity=4)
    pl_bin = (D['pl'] > 127).astype(np.uint8)
    polys = []
    for i in range(1, ncc):
        x, y, w, h, A = st[i]
        if A < 6000: continue
        m = (cc[y:y + h, x:x + w] == i).astype(np.uint8)
        inner = cv2.erode(m, np.ones((61, 61), np.uint8))
        r = pl_bin[y:y + h, x:x + w] & inner
        nr, rc, rst, _ = cv2.connectedComponentsWithStats(r, connectivity=8)
        long_r = [int(max(rst[j, 2], rst[j, 3])) for j in range(1, nr) if max(rst[j, 2], rst[j, 3]) >= 250]
        pa = cv2.resize(D['pa'], (W, H), interpolation=cv2.INTER_LINEAR)[y:y + h, x:x + w] if False else None
        polys.append(dict(cc=i, bbox=[int(x), int(y), int(w), int(h)], area=int(A), centre=[round(float(c), 1) for c in cen[i]], ridges_ge250=len(long_r), ridge_len=int(sum(long_r)), paper_share=round(A / float(D['alpha'].sum()), 4)))
    out = dict(plate=n, W=W, H=H, paper=paper.tolist(), lines=[dict(a=e['a'].round(1).tolist(), b=e['b'].round(1).tolist(), state=e['state'], L=round(e['L'], 1), polys=e['polys'],
                                                                        blank_l=round(e['blank_l'], 3), blank_r=round(e['blank_r'], 3), rail=round(e['rail'], 3), dt=e['dt'], edge_d=round(e['edge_d'], 1),
                                                                        **({'on_ben': round(e['on_ben'], 3)} if 'on_ben' in e else {})) for e in E], ends=res_ends, polys=polys)
    json.dump(out, open(os.path.join(OUT, f'{n}_audit.json'), 'w'), indent=0)
    # summary
    Ls = np.array([e['L'] for e in E]); bl = np.array([max(e['blank_l'], e['blank_r']) for e in E]); bmn = np.array([min(e['blank_l'], e['blank_r']) for e in E])
    rl = np.array([e['rail'] for e in E])
    k = lambda kind: [x for x in res_ends if x['kind'] == kind]
    gsum = lambda xs: round(sum(x['gap'] for x in xs if x['gap'] is not None))
    areas = sorted(p['area'] for p in polys)
    s = dict(plate=n, editor_lines=len(E), editor_len=int(Ls.sum()), green=sum(e['state'] == 'green' for e in E), orange=sum(e['state'] == 'orange' for e in E),
             open_ends=len(res_ends), broken=len(k('broken')), broken_gap=gsum(k('broken')), corner=len(k('corner')), corner_gap=gsum(k('corner')), dangling=len(k('dangling')),
             filled_both_sides=int((bl < 0.5).sum()), filled_both_len=int(Ls[bl < 0.5].sum()), blank_both_sides=int((bmn > 0.8).sum()), blank_both_len=int(Ls[bmn > 0.8].sum()),
             rail_lines=int((rl > 0.5).sum()), rail_len=int(Ls[rl > 0.5].sum()),
             polys=len(polys), median_area=int(np.median(areas)) if areas else 0, small_polys=sum(a < 0.2 * np.median(areas) for a in areas) if areas else 0,
             largest_share=max((p['paper_share'] for p in polys), default=0), polys_with_ridge=sum(p['ridges_ge250'] > 0 for p in polys), ridge_len=sum(p['ridge_len'] for p in polys))
    if ben is not None:
        ob = np.array([e['on_ben'] for e in E]); s.update(on_ben_len=int((Ls * ob).sum()), precision=round(float((Ls * ob).sum() / Ls.sum()), 3))
    return s


if __name__ == '__main__':
    rows = []
    for n in sys.argv[1:]:
        s = audit(n); s = json.loads(json.dumps(s, default=lambda o: o.item() if hasattr(o, 'item') else str(o))); rows.append(s); print(json.dumps(s), flush=True)
    f = os.path.join(OUT, 'summary.json'); old = json.load(open(f)) if os.path.exists(f) else {}
    old.update({r['plate']: r for r in rows}); json.dump(old, open(f, 'w'), indent=1)
