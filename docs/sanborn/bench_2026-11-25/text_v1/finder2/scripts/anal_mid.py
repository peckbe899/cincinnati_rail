"""Analysis (finder2, 25 Nov 2026): MID line ink pieces (v1 line ink that a 121 px line does not fit, 8-connected) on the
truth v2 crops, with features and the share of their ink the truth calls text. Development only.

    cd data/sanborn; python -B bench_2026-11-25/text_v1/finder2/scripts/anal_mid.py [T1 ...]"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
TRUTH = os.path.normpath(os.path.join(HERE, '..', '..', 'truth'))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'code')))
import finder2 as F


def mid_features(ink, line, lng):
    """features of each 8-connected piece of mid line ink (line & ~lng)"""
    H, W = ink.shape
    mid = ((line > 0) & (lng == 0)).astype(np.uint8)
    n, lb, st, _ = cv2.connectedComponentsWithStats(mid, connectivity=8)
    A, lg, th, mx, my, an = F.shape(lb, n)
    dt = cv2.distanceTransform(ink, cv2.DIST_L2, 5)
    ridge = (dt > 0) & (dt >= cv2.dilate(dt, np.ones((3, 3), np.uint8))) & (mid > 0)
    rl = lb[ridge]; sw = 2 * np.bincount(rl, dt[ridge], n) / np.maximum(np.bincount(rl, minlength=n), 1)
    other_line = (line > 0) & (mid == 0)
    R = {}
    for j in range(1, n):
        x, y, w, h, a = st[j]
        if a < 15: continue
        g = 12; X0, Y0, X1, Y1 = max(0, x - g), max(0, y - g), min(W, x + w + g), min(H, y + h + g)
        sub = (lb[Y0:Y1, X0:X1] == j).astype(np.uint8)
        # contacts with other line ink (long ink or other mid pieces) within 2 px
        z = cv2.dilate(sub, np.ones((5, 5), np.uint8)) > 0
        ol = ((line[Y0:Y1, X0:X1] > 0) & (sub == 0) & z).astype(np.uint8)
        nc = cv2.connectedComponents(cv2.dilate(ol, np.ones((3, 3), np.uint8)), connectivity=8)[0] - 1
        # side clutter: ink (not this piece, not line ink) in the band 3..10 px from the piece, as a share of the band
        d = cv2.distanceTransform((sub == 0).astype(np.uint8), cv2.DIST_L2, 5)
        band = (d >= 3) & (d <= 10)
        inkb = (ink[Y0:Y1, X0:X1] > 0) & (line[Y0:Y1, X0:X1] == 0)
        clut = float((band & inkb).sum()) / max(1, band.sum())
        R[j] = dict(A=int(a), lg=round(float(lg[j]), 1), th=round(float(th[j]), 1), sw=round(float(sw[j]), 2), contacts=int(nc),
                    clutter=round(clut, 3), ang=round(float(np.degrees(an[j])), 1), box=[int(x), int(y), int(w), int(h)])
    return n, lb, R


if __name__ == '__main__':
    M = 200
    crops = json.load(open(os.path.join(TRUTH, 'crops.json')))
    ids = sys.argv[1:] or ['T1', 'T2', 'T3', 'T4', 'T6', 'T7']
    rows = []
    for tid in ids:
        c = crops[tid]; x0, y0, x1, y1 = c['win']
        im, ink, paper, _ = F.load(c['plate'], (x0 - M, y0 - M, x1 + M, y1 + M))
        P0 = dict(F.P); F.P['clus_r'] = 0; line, ori = F.line_ink(ink); F.P.update(P0)
        fat = cv2.dilate(ink, np.ones((3, 3), np.uint8)); lng = F.long_ink(fat, line, 121)
        n, lb, R = mid_features(ink, line, lng)
        tr = np.zeros(ink.shape, np.uint8); tr[M:M + y1 - y0, M:M + x1 - x0] = cv2.imread(os.path.join(TRUTH, f'{tid}_mask.png'), 0) + 10
        tt = np.bincount(lb[tr == 12], minlength=n); tn = np.bincount(lb[tr == 11], minlength=n)
        for j, r in R.items():
            if tt[j] + tn[j] < 10: continue
            r.update(tid=tid, x=r['box'][0] + x0 - M, y=r['box'][1] + y0 - M, tpx=int(tt[j]), npx=int(tn[j]), text=round(tt[j] / (tt[j] + tn[j]), 3)); rows.append(r)
    json.dump(rows, open(os.path.join(HERE, '..', 'out', 'anal_mid.json'), 'w'), indent=0)
    print(len(rows), 'mid pieces; text px', sum(r['tpx'] for r in rows), 'non-text', sum(r['npx'] for r in rows))
    import collections
    for key, bins in (('contacts', [(0, 0), (1, 1), (2, 2), (3, 99)]), ('clutter', [(0, .05), (.05, .1), (.1, .2), (.2, .3), (.3, 1)]),
                      ('sw', [(0, 3), (3, 4.5), (4.5, 6), (6, 99)]), ('lg', [(0, 40), (40, 61), (61, 81), (81, 101), (101, 999)])):
        print(key, '  '.join(f"{lo}-{hi}: text {sum(r['tpx'] for r in rows if lo <= r[key] <= hi)} / non {sum(r['npx'] for r in rows if lo <= r[key] <= hi)}" for lo, hi in bins))
    print('contacts x clutter (text / non):')
    for c0 in (0, 1, 2):
        print(' contacts', c0 if c0 < 2 else '2+', '  '.join(f"cl {lo}-{hi}: {sum(r['tpx'] for r in rows if (r['contacts'] == c0 if c0 < 2 else r['contacts'] >= 2) and lo <= r['clutter'] < hi)}/{sum(r['npx'] for r in rows if (r['contacts'] == c0 if c0 < 2 else r['contacts'] >= 2) and lo <= r['clutter'] < hi)}" for lo, hi in ((0, .05), (.05, .1), (.1, .2), (.2, .3), (.3, 1))))
