"""Independent scorer (vector geometry, not raster) of an outlines polys json against Ben's street map of 44.
python score.py polys.json [lp.png] [tol]"""
import json, sys
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
polys = json.load(open(sys.argv[1]))
lp = cv2.imread(sys.argv[2], 0).astype(np.float32) if len(sys.argv) > 2 and sys.argv[2] != '-' else None
TOL = float(sys.argv[3]) if len(sys.argv) > 3 else 6.0
sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
BA = np.array([l['a'] for l in sm['lines']], float); BB = np.array([l['b'] for l in sm['lines']], float); BK = np.array([l['kind'] for l in sm['lines']])
H, W = 7219, 10768

def pts(a, b, step=2.0):
    L = np.hypot(*(b - a)); n = max(2, int(L / step) + 1); return a + np.outer(np.linspace(0, 1, n), b - a), L

def segdist(P, A, B):
    """distance of each point P (n,2) to each segment (m) -> (n,m), and unit dirs of segments"""
    d = B - A; L2 = (d ** 2).sum(1); t = np.clip(((P[:, None, :] - A[None]) * d[None]).sum(2) / np.maximum(L2, 1e-9), 0, 1)
    q = A[None] + t[..., None] * d[None]; return np.hypot(*(P[:, None, :] - q).transpose(2, 0, 1))

def hit(P, dirv, A, B, ang=None):
    D = segdist(P, A, B)
    if ang is not None:
        d = (B - A) / np.hypot(*(B - A).T)[:, None]; c = np.abs(d @ dirv)
        D = np.where(c[None] >= np.cos(np.radians(ang)), D, 1e9)
    return D.min(1) <= TOL

def along(img, a, b):
    d = b - a; L = np.hypot(*d); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d)
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); return img[y, x]

kept = [(np.array(s['a']), np.array(s['b']), s['state']) for p in polys for s in p if s['state'] != 'short' and not s.get('paper_edge')]
res = {}
for ang in (None, 10):
    tag = 'dist' if ang is None else f'dist+ang{ang}'
    by = {}
    for a, b, st in kept:
        P, L = pts(a, b); dv = (b - a) / L; h = hit(P, dv, BA, BB, ang).mean()
        k = st
        if st == 'on print' and lp is not None: k = 'green+dt' if along(lp, a, b).mean() > 90 else 'green-nodt'
        e = by.setdefault(k, [0, 0.0, 0.0]); e[0] += 1; e[1] += L; e[2] += L * h
        if st == 'on print':
            e = by.setdefault('GREEN', [0, 0.0, 0.0]); e[0] += 1; e[1] += L; e[2] += L * h
        e = by.setdefault('ALL', [0, 0.0, 0.0]); e[0] += 1; e[1] += L; e[2] += L * h
    # recall of Ben's printed lines by exported / green
    KA = np.array([a for a, b, s in kept]); KB = np.array([b for a, b, s in kept]); G = np.array([s == 'on print' for a, b, s in kept])
    rec = {}
    for kind in ('printed', 'drawn', 'sheet_edge'):
        tot = gA = gG = 0.0
        for i in np.nonzero(BK == kind)[0]:
            P, L = pts(BA[i], BB[i]); dv = (BB[i] - BA[i]) / L
            tot += L; gA += L * hit(P, dv, KA, KB, ang).mean(); gG += L * hit(P, dv, KA[G], KB[G], ang).mean()
        rec[kind] = dict(len=round(tot), by_exported=round(gA / tot, 3), by_green=round(gG / tot, 3))
    res[tag] = dict(precision={k: dict(n=v[0], len=round(v[1]), on_ben=round(v[2] / v[1], 3)) for k, v in by.items()}, recall=rec)
print(json.dumps(res, indent=1))
