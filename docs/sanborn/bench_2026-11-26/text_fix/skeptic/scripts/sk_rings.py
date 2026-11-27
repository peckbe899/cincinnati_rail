"""sk_rings.py (skeptic): is false text hiding just outside the 25 px scopes? Text called in rings 25-60 px round the
target words, on the whole sealed plates, finder3 against finder4 (the gate's masks).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_rings.py OUT.json PIECES.json

Ring of a target word: its box grown by 60 px minus its box grown by 25 px (square, like the scope). Rings of one plate
are joined (no pixel counted twice). Pixels inside any labelled sealed area (a scope box or a full crop) are left out of
the ring and counted apart (the truth already scores them). In the ring, for each method: ink px, text px; and the
pixels finder4 calls text that finder3 did not ('new'), split by finder3's code (1 line ink, 4 shared, 5 other ink) and
by whether they lie on a straight run of ink of 61 px or more (all ink, opening with 61 px lines every 7.5 deg; a
line-like sign). The same is counted inside the scopes for comparison (there the truth splits right from wrong).
Also checks on every sealed plate: same ink in both masks; no finder3 text pixel lost by finder4.
PIECES.json: every 8-connected piece of new text in the rings (plate, box, px, finder3 codes, straight px), for the
eye check (sk_pic.py).
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


def straight(ink):
    u = ink.astype(np.uint8); s = np.zeros(ink.shape, bool)
    for k in K: s |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k, borderType=cv2.BORDER_CONSTANT, borderValue=0) > 0
    return s


def main():
    crops = json.load(open(f'{TR}/crops.json')); O = dict(plates={}, checks={}); pieces = []
    plates = sorted({c['plate'] for c in crops.values()}, key=lambda s: (len(s), s))
    for N in plates:
        a = cv2.imread(f'{G}/finder3/{N}_text.png', cv2.IMREAD_UNCHANGED); b = cv2.imread(f'{G}/finder4/{N}_text.png', cv2.IMREAD_UNCHANGED)
        H, W = a.shape
        ta = np.isin(a, (2, 3)); tb = np.isin(b, (2, 3))
        O['checks'][N] = dict(same_ink=bool(np.array_equal(a > 0, b > 0)), f3_text_lost=int((ta & ~tb).sum()), f4_new_text_plate=int((tb & ~ta).sum()))
        labelled = np.zeros((H, W), bool); scope = {'block': np.zeros((H, W), bool), 'ditto': np.zeros((H, W), bool)}
        ring = {'block': np.zeros((H, W), bool), 'ditto': np.zeros((H, W), bool)}
        for cid, c in crops.items():
            if c['plate'] != N: continue
            if c.get('kind') == 'full':
                x0, y0, x1, y1 = c['win']; labelled[y0:y1, x0:x1] = True; continue
            for s in c['scope']:
                x0, y0, x1, y1 = s; labelled[y0:y1 + 1, x0:x1 + 1] = True; scope[c['target']][y0:y1 + 1, x0:x1 + 1] = True
            for w in json.load(open(f'{TR}/{cid}_words.json', encoding='utf8'))['words']:
                if not w.get('target'): continue
                x0, y0, x1, y1 = w['aabb']
                g = lambda p: (max(0, x0 - p), max(0, y0 - p), min(W, x1 + p + 1), min(H, y1 + p + 1))
                o = g(60); i = g(25)
                r = np.zeros((o[3] - o[1], o[2] - o[0]), bool); r[:] = True; r[i[1] - o[1]:i[3] - o[1], i[0] - o[0]:i[2] - o[0]] = False
                ring[c['target']][o[1]:o[3], o[0]:o[2]] |= r
        ink = a > 0
        rec = {}
        for kind in ('block', 'ditto'):
            R = ring[kind] & ~labelled
            if not R.any(): continue
            ys, xs = np.nonzero(R | scope[kind]); bx0, by0, bx1, by1 = max(0, xs.min() - 40), max(0, ys.min() - 40), min(W, xs.max() + 41), min(H, ys.max() + 41)
            # straight runs only where needed: per ring/scope bounding windows of each target region (cheaper: per component box)
            region = (R | scope[kind])
            lab, nl = ndi.label(region); st_all = np.zeros((H, W), bool)
            for sl in ndi.find_objects(lab):
                y0, y1 = max(0, sl[0].start - 70), min(H, sl[0].stop + 70); x0, x1 = max(0, sl[1].start - 70), min(W, sl[1].stop + 70)
                st_all[y0:y1, x0:x1] |= straight(ink[y0:y1, x0:x1])
            new = tb & ~ta
            for nm, M in (('ring', R), ('scope', scope[kind])):
                nn = new & M
                rec[f'{kind}_{nm}'] = dict(px=int(M.sum()), ink=int((ink & M).sum()), f3_text=int((ta & M).sum()), f4_text=int((tb & M).sum()), new=int(nn.sum()),
                                           new_from_code={str(k): int(((a == k) & nn).sum()) for k in (1, 4, 5)}, new_on_straight=int((nn & st_all).sum()),
                                           f3_text_on_straight=int((ta & M & st_all).sum()), f4_text_on_straight=int((tb & M & st_all).sum()))
            nn = new & R
            lab2, n2 = ndi.label(nn, structure=np.ones((3, 3)))
            for j, sl in enumerate(ndi.find_objects(lab2), 1):
                m = lab2[sl] == j; sub = a[sl]
                pieces.append(dict(plate=N, kind=kind, box=[int(sl[1].start), int(sl[0].start), int(sl[1].stop), int(sl[0].stop)], px=int(m.sum()),
                                   f3_codes={str(int(k)): int(v) for k, v in zip(*np.unique(sub[m], return_counts=True))}, straight=int((st_all[sl] & m).sum())))
        O['plates'][N] = rec
        print(N, json.dumps(O['checks'][N]), {k: (v['new'], v['ink']) for k, v in rec.items()}, flush=True)
    tot = {}
    for N, rec in O['plates'].items():
        for k, v in rec.items():
            t = tot.setdefault(k, {})
            for q, x in v.items():
                if isinstance(x, dict):
                    tq = t.setdefault(q, {})
                    for kk, vv in x.items(): tq[kk] = tq.get(kk, 0) + vv
                else: t[q] = t.get(q, 0) + x
    O['total'] = tot
    json.dump(O, open(sys.argv[1], 'w'), indent=1); json.dump(pieces, open(sys.argv[2], 'w'), indent=0)
    for k, v in tot.items(): print(k, v)
    print('pieces of new text in the rings:', len(pieces), 'px', sum(p['px'] for p in pieces))


if __name__ == '__main__':
    main()
