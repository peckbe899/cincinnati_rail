"""Skeptic (26 Nov 2026): where does a mask call straight-run line ink text on the held-out crops? Lists the spots
(8-connected groups of truth-1 ink on a straight run >= 61 px that the mask calls text) and draws zooms:
scan | mask over a faded scan (red = straight-run line ink called text, magenta = other text call, grey = truth 1).
    cd data/sanborn; python -B .../sk_linepics.py METHOD [TRUTH] [--top 12]
Writes skeptic/pics/lineproxy_<METHOD>_<crop>_<i>.png and skeptic/out/lineproxy_<METHOD>_<H|T>.json."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
B = 'bench_2026-11-25/text_v1'
M = {'v2': (f'{B}/finder2/out/final/{{plate}}_text.png', (2, 3)), 'v3': (f'{B}/classifier/out/finder3/{{plate}}_text.png', (2, 3)),
     'v1': ('bench_2026-11-25/text/finder/out/{plate}_finder.png', (2, 3, 4))}
a = sys.argv[1:]; meth = a[0]; TD = a[1] if len(a) > 1 and not a[1].startswith('--') else f'{B}/truth-check/heldout_fixed'
top = int(a[a.index('--top') + 1]) if '--top' in a else 12
crops = json.load(open(os.path.join(TD, 'crops.json'))); ids = sorted(k for k in crops if os.path.exists(os.path.join(TD, f'{k}_mask.png')))


def straight_of(t1):
    u = t1.astype(np.uint8); s = np.zeros_like(t1); L = 61
    for ang in np.arange(0, 180, 7.5):
        k = np.zeros((L, L), np.uint8); c = L // 2; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
        cv2.line(k, tuple(np.round(c - d * c).astype(int)), tuple(np.round(c + d * c).astype(int)), 1, 1)
        s |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return s


rec = {}
os.makedirs(f'{B}/skeptic/pics', exist_ok=True)
for tid in ids:
    c = crops[tid]; x0, y0, x1, y1 = c['win']; truth = cv2.imread(os.path.join(TD, f'{tid}_mask.png'), 0)
    pat, codes = M[meth]; code = cv2.imread(pat.replace('{plate}', c['plate']), cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1]
    p = np.isin(code, codes); st = straight_of(truth == 1); bad = st & p
    n, lb, sts, _ = cv2.connectedComponentsWithStats(cv2.dilate(bad.astype(np.uint8), np.ones((9, 9), np.uint8)), connectivity=8)
    cnt = np.bincount(lb[bad], minlength=n); order = [i for i in np.argsort(-cnt) if i > 0 and cnt[i] > 0]
    spots = [dict(x=int(x0 + sts[i, 0] + sts[i, 2] // 2), y=int(y0 + sts[i, 1] + sts[i, 3] // 2), px=int(cnt[i]),
                  codes={str(int(v)): int(((lb == i) & bad & (code == v)).sum()) for v in codes}) for i in order]
    rec[tid] = dict(total=int(bad.sum()), of=int(st.sum()), spots=spots)
    im = cv2.imread(f'cufp/22-{c["plate"]}.jpg')[y0:y1, x0:x1]
    for j, i in enumerate(order[:top]):
        cx, cy = sts[i, 0] + sts[i, 2] // 2, sts[i, 1] + sts[i, 3] // 2; s = 45
        X0, Y0, X1, Y1 = max(0, cx - s), max(0, cy - s), min(im.shape[1], cx + s), min(im.shape[0], cy + s)
        o = (im[Y0:Y1, X0:X1] * 0.35 + 255 * 0.65).astype(np.uint8); tt = truth[Y0:Y1, X0:X1]
        o[tt == 1] = (150, 150, 150); o[tt == 2] = (60, 60, 60); o[p[Y0:Y1, X0:X1]] = (220, 0, 220); o[bad[Y0:Y1, X0:X1]] = (0, 0, 255)
        pic = np.concatenate([im[Y0:Y1, X0:X1], np.zeros((Y1 - Y0, 3, 3), np.uint8), o], 1); pic = cv2.resize(pic, None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
        cv2.putText(pic, f'{tid} {x0 + cx},{y0 + cy} {int(cnt[i])}px', (4, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.imwrite(f'{B}/skeptic/pics/lineproxy_{meth}_{tid}_{j}.png', pic)
    print(tid, 'straight-run truth-1 ink', int(st.sum()), 'called text', int(bad.sum()), 'top spots', [(s_['x'], s_['y'], s_['px']) for s_ in spots[:top]])
tag = 'T' if os.path.basename(os.path.normpath(TD)) == 'truth' else 'H'
json.dump(rec, open(f'{B}/skeptic/out/lineproxy_{meth}_{tag}.json', 'w'), indent=1)
