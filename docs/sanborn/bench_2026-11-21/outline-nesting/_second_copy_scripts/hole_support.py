"""Line-network support of each hole's whole ring (all its sides, short pieces too): the share of the ring's length where
the blurred line map (outlines.py's lp) is > 90 within +-3 px. A street hole should be traced by the line network all
round; a pocket of unsure ground in open land should not. Also the parent-size ratio is not needed here.

    python hole_support.py   -> hole_support.json; prints the support of 44's holes (good = on Ben's lines) and of the
                                holes of the eye-judged PDF sample (sample_holes/verdicts.json)
"""
import json, os
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'


def support(ring, lp):
    H, W = lp.shape; ok = tot = 0.0
    for k in range(len(ring)):
        a, b = np.array(ring[k], float), np.array(ring[(k + 1) % len(ring)], float); L = np.hypot(*(b - a))
        if L < 1: continue
        t = np.linspace(0, 1, max(2, int(L))); q = a + np.outer(t, b - a); u = (b - a) / L; nrm = np.array([-u[1], u[0]])
        best = np.zeros(len(q))
        for o in (-3, -1.5, 0, 1.5, 3):
            x = np.clip((q[:, 0] + nrm[0] * o).round().astype(int), 0, W - 1); y = np.clip((q[:, 1] + nrm[1] * o).round().astype(int), 0, H - 1)
            best = np.maximum(best, lp[y, x])
        ok += L * float((best > 90).mean()); tot += L
    return ok / max(1.0, tot)


def lpmap(n): return cv2.GaussianBlur(cv2.imread(U + f'{n}_lines_lines_ng1.png', 0), (5, 5), 0)


if __name__ == '__main__':
    out = {}
    P = json.load(open(HERE + 'runs/nest/outlines.json', encoding='utf8')); H44 = json.load(open(HERE + 'runs/nest/holes44.json'))['holes']; lp = lpmap('44')
    r44 = []
    for r in H44:
        ring = [s['a'] for s in P[r['poly']]]
        r44.append(dict(hole=r['poly'], len=r.get('len'), on_ben=r.get('on_ben'), support=round(support(ring, lp), 3)))
        print('44 hole', r['poly'], 'exported', r.get('len'), 'on Ben', r.get('on_ben'), 'ring support', r44[-1]['support'])
    out['44'] = r44
    S = json.load(open(HERE + 'sample_holes/sample.json'))['sample']; V = json.load(open(HERE + 'sample_holes/verdicts.json'))
    cache = {}; rows = []
    for o in S:
        n = o['plate']
        if n not in cache: cache = {n: (json.load(open(HERE + f'runs_plates/new/{n}/outlines.json', encoding='utf8')), lpmap(n))}
        polys, lpn = cache[n]
        rows.append(dict(k=o['k'], plate=n, verdict=V[str(o['k'])], support=round(support([s['a'] for s in polys[o['hole']]], lpn), 3)))
    for v in ('yes', 'no', 'unsure'):
        s = sorted(x['support'] for x in rows if x['verdict'] == v); print('PDF sample', v, len(s), s)
    out['pdf_sample'] = rows
    json.dump(out, open(HERE + 'hole_support.json', 'w'), indent=1)
