"""sk_straight.py (skeptic): why my straight-run proxy (297 -> 306) differs from the gate's (474 -> 504) on the full crops.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_straight.py OUT.json

The proxy: truth-1 (non-text) ink lying on a straight run of 61 px or more (opening with 61 px lines every 7.5 deg),
called text. The gate (gscore.py) and integrate (straight.py) open with cv2.morphologyEx, whose default border for
erosion counts the outside of the crop as ink. scipy's binary_opening counts it as paper. Here both, on the same
kernels (cv2.line, as the gate), plus where the finder4-only pixels lie (distance to the crop edge).
"""
import json, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
from scipy import ndimage as ndi
TR = 'bench_2026-11-26/text_fix/sealed_final'; G = 'bench_2026-11-26/text_fix/gate/out'


def kern(L, ang):
    k = np.zeros((L, L), np.uint8); c = L // 2; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
    p0 = np.round(c - d * c).astype(int); p1 = np.round(c + d * c).astype(int); cv2.line(k, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 1, 1)
    return k


K = [kern(61, a) for a in np.arange(0, 180, 7.5)]


def st_cv(m):
    s = np.zeros(m.shape, bool); u = m.astype(np.uint8)
    for k in K: s |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return s


def st_sp(m, border):
    s = np.zeros(m.shape, bool)
    for k in K:
        e = ndi.binary_erosion(m, structure=k > 0, border_value=border)
        s |= ndi.binary_dilation(e, structure=k > 0) & m
    return s


crops = json.load(open(f'{TR}/crops.json')); O = {}
for cid in ('SA-F1', 'SB-F1'):
    c = crops[cid]; x0, y0, x1, y1 = c['win']; T = cv2.imread(f'{TR}/{cid}_mask.png', 0); t1 = T == 1
    P = {m: np.isin(cv2.imread(f'{G}/{m}/{c["plate"]}_text.png', cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1], (2, 3)) for m in ('finder3', 'finder4')}
    H, W = T.shape; yy, xx = np.mgrid[0:H, 0:W]; edge = np.minimum.reduce([xx, yy, W - 1 - xx, H - 1 - yy])
    r = {}
    for nm, s in (('cv2_default', st_cv(t1)), ('scipy_border_paper', st_sp(t1, 0)), ('scipy_border_ink', st_sp(t1, 1))):
        new = s & P['finder4'] & ~P['finder3']
        lab, nl = ndi.label(new, structure=np.ones((3, 3)))
        spots = []
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            mm = lab[sl] == i; ys, xs = np.nonzero(mm)
            spots.append(dict(px=int(mm.sum()), x=int(x0 + sl[1].start + xs.mean()), y=int(y0 + sl[0].start + ys.mean()), min_edge_dist=int(edge[sl][mm].min())))
        r[nm] = dict(straight_px=int(s.sum()), f3=int((s & P['finder3']).sum()), f4=int((s & P['finder4']).sum()), new_f4_only=int(new.sum()),
                     new_within_30px_of_edge=int((new & (edge < 30)).sum()), spots=spots)
    O[cid] = r
    print(cid, json.dumps(r))
json.dump(O, open(sys.argv[1], 'w'), indent=1)
