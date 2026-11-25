"""Q1b (ben-labels, 25 Nov 2026): Ben's deleted network lines split into DUPLICATES (lying on one of his final lines:
the network drew the street side twice, or a piece of it, and he removed the spare) and FALSE lines (away from every
final line: a line where there is no street side). Then how the current labels teach each kind, and what ink lies under
the false ones (ink_bins bins). Also the added lines split by ink support.
    cd data/sanborn; python -B bench_2026-11-25/diag/ben-labels/scripts/deleted_split.py
dup share of a line = share of its points (every 2 px) within DUP_PX (6) px of a final line (his street map: every kind).
duplicate >= 0.6, false <= 0.2, partial between. Ink support of a line = share of its points with edgenet ink within 2 px.
Bins: 44 unet_data/44_bins.png (from his street map); 5 and 1A re-run today with his edits (diag bins_N_now.png).
"""
import sys, os, json
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *  # noqa
DUP_PX = 6
NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
SETS = {
    '1A': dict(sm=SP + 'train_v2/1A/streetmap.json', bins=DIAG + '/bins_1A_now.png', labels=[('train_v2 map (V1,V2)', SP + 'train_v2/1A/label.png', SP + 'train_v2/1A/lines.png')]),
    '5': dict(sm=DIAG + '/map_now/5_streetmap.json', bins=DIAG + '/bins_5_now.png', labels=[('train_v2 pseudo (V2)', SP + 'train_v2/5/label.png', SP + 'train_v2/5/lines.png'), ('map recipe now (not trained)', DIAG + '/map_now/5_label.png', DIAG + '/map_now/5_lines.png')]),
    '44': dict(sm=SP + 'streetmap/22-44.json', bins=SP + 'unet_data/44_bins.png', labels=[('map recipe (hypothetical)', DIAG + '/map_now/44_label.png', DIAG + '/map_now/44_lines.png')]),
}
def pts(a, b, step=2.0):
    a, b = np.asarray(a, float), np.asarray(b, float); L = np.hypot(*(b - a)); n = max(2, int(L / step) + 1)
    return a + np.linspace(0, 1, n)[:, None] * (b - a)
res = {}
for N, S in SETS.items():
    full = scan(N); H, W = full.shape[:2]; ink = ink_edgenet(full); del full; af = alpha_full(N, W, H); h, w = H // K, W // K; ah = alpha_half(N, w, h)
    sm = json.load(open(S['sm'], encoding='utf8')); fin = raster([(l['a'], l['b']) for l in sm['lines']], (H, W), 1.0, 1)
    dfin = cv2.distanceTransform((fin == 0).astype(np.uint8), cv2.DIST_L2, 5)
    dink = cv2.distanceTransform((~ink).astype(np.uint8), cv2.DIST_L2, 5)
    bins = cv2.imread(S['bins'], 0); assert bins.shape == (H, W)
    B = ben(N)['lines']; dels = [(s['a0'], s['b0']) for s in B if s.get('verdict') == 'wrong' and s.get('src') != 'sheet']
    adds = [(s['a'], s['b']) for s in B if s.get('added') and s.get('verdict') != 'wrong']
    cls = []; inks = []
    for a, b in dels:
        p = pts(a, b); x = np.clip(p[:, 0].round().astype(int), 0, W - 1); y = np.clip(p[:, 1].round().astype(int), 0, H - 1)
        ds = float((dfin[y, x] <= DUP_PX).mean()); cls.append('duplicate' if ds >= 0.6 else 'false' if ds <= 0.2 else 'partial'); inks.append(float((dink[y, x] <= 2).mean()))
    asup = []
    for a, b in adds:
        p = pts(a, b); x = np.clip(p[:, 0].round().astype(int), 0, W - 1); y = np.clip(p[:, 1].round().astype(int), 0, H - 1); asup.append(float((dink[y, x] <= 2).mean()))
    r = dict(deleted_net=len(dels), by_kind={k: cls.count(k) for k in ('duplicate', 'partial', 'false')},
             length_by_kind={k: round(sum(float(np.hypot(b[0] - a[0], b[1] - a[1])) for (a, b), c in zip(dels, cls) if c == k)) for k in ('duplicate', 'partial', 'false')},
             false_ink_support_median=round(float(np.median([i for i, c in zip(inks, cls) if c == 'false'] or [0])), 3),
             added=len(adds), added_ink_support={'<0.3': sum(v < 0.3 for v in asup), '0.3-0.7': sum(0.3 <= v < 0.7 for v in asup), '>=0.7': sum(v >= 0.7 for v in asup)},
             added_length_inkless_px=round(sum(float(np.hypot(b[0] - a[0], b[1] - a[1])) for (a, b), v in zip(adds, asup) if v < 0.3)))
    # what ink lies under the false lines: bins of the ink within 5 px of each false line (WRONG_PX strip)
    fl = [l for l, c in zip(dels, cls) if c == 'false']; fm = (raster(fl, (H, W), 1.0, WRONG_PX) > 0) & af
    fi = fm & (bins > 0); tot = int(fi.sum())
    r['false_lines_ink_by_bin'] = {NAMES[k]: round(float(((bins == k) & fm).sum()) / max(1, tot), 3) for k in range(1, 10)} | {'ink_px': tot}
    # each false line's main ink bin (most of its strip's ink)
    main = []
    for (a, b) in fl:
        m = (raster([(a, b)], (H, W), 1.0, WRONG_PX) > 0) & (bins > 0)
        main.append(NAMES[int(np.bincount(bins[m], minlength=10)[1:].argmax()) + 1] if m.any() else 'no ink')
    r['false_lines_main_bin'] = {k: main.count(k) for k in sorted(set(main))}
    # how the labels teach each kind
    for name, lf, tf in S['labels']:
        lab = cv2.imread(lf, 0); t = cv2.imread(tf, 0); out = {}
        for kind in ('duplicate', 'partial', 'false'):
            L = [l for l, c in zip(dels, cls) if c == kind]
            if not L: continue
            m = (raster(L, (H, W), 1.0, LINE) > 0) & af; mi = (raster(L, (H, W), 1.0, WRONG_PX) > 0) & af & ink
            under = (raster(L, (h, w), 1.0 / K, 1) > 0) & ah; besid = (raster(L, (h, w), 1.0 / K, 17) > 0) & ~(raster(L, (h, w), 1.0 / K, 3) > 0) & ah
            per = []
            for l in L:
                mm = (raster([l], (H, W), 1.0, LINE) > 0) & af; v = t[mm]
                per.append('positive' if (v == 1).mean() > 0.5 else 'negative' if (v == 0).mean() > 0.5 else 'unscored' if (v == 255).mean() > 0.5 else 'mixed')
            out[kind] = dict(lines=len(L), line_px=share(m, t, (1, 0, 255)), ink11=share(mi, t, (1, 0, 255)), majority={k: per.count(k) for k in ('positive', 'negative', 'unscored', 'mixed')},
                             area_under=share(under, lab, (0, 1, 255)), area_beside=share(besid, lab, (0, 1, 255)))
        # added lines with no ink under them (support < 0.3)
        La = [l for l, v in zip(adds, asup) if v < 0.3]
        if La:
            m = (raster(La, (H, W), 1.0, LINE) > 0) & af; out['added_inkless'] = dict(lines=len(La), line_px=share(m, t, (1, 0, 255)), on_ink=round(float((m & ink).mean() if False else (m & ink).sum() / max(1, m.sum())), 4))
        r[name] = out
    res[N] = r; print(N, json.dumps(r), flush=True)
    json.dump(dict(dels=[dict(a=a, b=b, kind=c, ink=round(i, 3)) for (a, b), c, i in zip(dels, cls, inks)], adds=[dict(a=a, b=b, ink=round(v, 3)) for (a, b), v in zip(adds, asup)]), open(os.path.join(DIAG, f'lines_{N}.json'), 'w'), indent=0)
wj(os.path.join(DIAG, 'deleted_split.json'), res)
