"""sk_straight_ctx.py (skeptic): the straight-run proxy on SA-F1 with the real plate ink beyond the crop edge, instead of
cv2's default border (which treats everything outside the crop as ink). Inside the crop: truth-1 ink (as the gate);
outside (80 px ring): plate ink that finder3 does not call text (a lenient stand-in for non-text ink), or all plate ink.
    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_straight_ctx.py OUT.json
"""
import json, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
TR = 'bench_2026-11-26/text_fix/sealed_final'; G = 'bench_2026-11-26/text_fix/gate/out'


def kern(L, ang):
    k = np.zeros((L, L), np.uint8); c = L // 2; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
    p0 = np.round(c - d * c).astype(int); p1 = np.round(c + d * c).astype(int); cv2.line(k, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 1, 1); return k


K = [kern(61, a) for a in np.arange(0, 180, 7.5)]


def st(m):
    s = np.zeros(m.shape, bool); u = m.astype(np.uint8)
    for k in K: s |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k, borderType=cv2.BORDER_CONSTANT, borderValue=0) > 0
    return s


O = {}
for cid in ('SA-F1', 'SB-F1'):
    c = json.load(open(f'{TR}/crops.json'))[cid]; x0, y0, x1, y1 = c['win']; N = c['plate']
    T = cv2.imread(f'{TR}/{cid}_mask.png', 0)
    A = cv2.imread(f'{G}/finder3/{N}_text.png', cv2.IMREAD_UNCHANGED); B = cv2.imread(f'{G}/finder4/{N}_text.png', cv2.IMREAD_UNCHANGED)
    pad = 80; X0, Y0, X1, Y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    inkw = A[Y0:Y1, X0:X1] > 0; inner = (slice(pad, pad + y1 - y0), slice(pad, pad + x1 - x0))
    nt = np.zeros_like(inkw); nt[inner] = T == 1
    out = np.ones_like(inkw); out[inner] = False
    nt |= out & inkw & ~np.isin(A[Y0:Y1, X0:X1], (2, 3))
    ta = np.isin(A[y0:y1, x0:x1], (2, 3)); tb = np.isin(B[y0:y1, x0:x1], (2, 3)); r = {}
    for nm, s in (('nontext_ctx', st(nt)[inner]), ('allink_ctx', st(inkw)[inner] & (T == 1))):
        r[nm] = dict(straight_px=int(s.sum()), f3=int((s & ta).sum()), f4=int((s & tb).sum()), new=int((s & tb & ~ta).sum()))
    O[cid] = r; print(cid, r)
json.dump(O, open(sys.argv[1], 'w'), indent=1)
