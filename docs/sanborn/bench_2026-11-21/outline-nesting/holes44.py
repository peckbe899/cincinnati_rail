"""Plate 44: what the hole sides added by RETR_TREE are, scored against Ben's lines (bench44 scorer, imported).

    python holes44.py RUN_TAG        (default: nest)  -> runs/RUN_TAG/holes44.json, prints a table

Per hole polygon: area, exported sides (step 4: not short, not paper_edge), length, share of that length on Ben's lines
(5 px, 20 degrees, against all his lines), split by green/orange and by line-network support (the side's mean P(line) on
the blurred line map > 90, outlines.py's 'on detected line'), and where the hole is (decided ground or not).
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.path.insert(0, HERE)
import bench44_copy as B  # noqa: E402

tag = sys.argv[1] if len(sys.argv) > 1 else 'nest'
run = HERE + f'runs/{tag}/'
polys = json.load(open(run + 'outlines.json', encoding='utf8'))
T = B.load_truth(); ben = B.LineSet(T['lines'], 20.0)
pl = cv2.imread(B.U + '44_lines_lines_ng1.png', 0); lp = cv2.GaussianBlur(pl, (5, 5), 0).astype(np.float32)
H, W = pl.shape


def det(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float); L = np.hypot(*(b - a)); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, b - a)
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); return float(lp[y, x].mean())


rows = []; tot = dict(len=0.0, on=0.0)
for k, p in enumerate(polys):
    if not (p and p[0].get('hole')): continue
    ring = np.array([s['a'] for s in p], float); area = abs(cv2.contourArea(ring.astype(np.float32)))
    ex = [s for s in p if s['state'] != 'short' and not s.get('paper_edge')]
    if not ex: rows.append(dict(poly=k, area=round(area), sides=0)); continue
    items = [(s['a'], s['b'], 'green' if s['state'] == 'on print' else 'orange') for s in ex]
    ls = B.LineSet(items, 20.0); d = ls.dist_to(ben); ok = d <= 5.0
    per = []
    for j, s in enumerate(ex):
        sel = ls.ix == j; L = float(np.hypot(*(np.subtract(s['b'], s['a']))))
        per.append(dict(len=round(L), on_ben=round(float(ok[sel].mean()), 3) if sel.any() else None, green=s['state'] == 'on print', det=round(det(s['a'], s['b']), 1)))
    cx, cy = ring.mean(0); dec = bool(T['decided'][min(int(cy * 0.5), T['decided'].shape[0] - 1), min(int(cx * 0.5), T['decided'].shape[1] - 1)])
    Lx = sum(q['len'] for q in per); on = sum(q['len'] * (q['on_ben'] or 0) for q in per)
    rows.append(dict(poly=k, area=round(area), centre=[round(cx), round(cy)], centre_on_decided=dec, sides=len(ex), len=round(Lx), on_ben=round(on / max(1, Lx), 3), per_side=per))
    tot['len'] += Lx; tot['on'] += on
allsides = [q for r in rows for q in r.get('per_side', [])]
def grp(f):
    s = [q for q in allsides if f(q)]; L = sum(q['len'] for q in s); return dict(n=len(s), len=round(L), on_ben=round(sum(q['len'] * (q['on_ben'] or 0) for q in s) / max(1, L), 3))
summary = dict(holes=len(rows), hole_sides_len=round(tot['len']), hole_sides_on_ben=round(tot['on'] / max(1, tot['len']), 3),
               green=grp(lambda q: q['green']), orange=grp(lambda q: not q['green']),
               green_det=grp(lambda q: q['green'] and q['det'] > 90), green_nodet=grp(lambda q: q['green'] and q['det'] <= 90),
               det=grp(lambda q: q['det'] > 90), nodet=grp(lambda q: q['det'] <= 90))
json.dump(dict(summary=summary, holes=rows), open(run + 'holes44.json', 'w'), indent=1)
print(json.dumps(summary, indent=1))
for r in rows: print(r['poly'], r['area'], r.get('centre'), r.get('centre_on_decided'), r['sides'], r.get('len'), r.get('on_ben'))
