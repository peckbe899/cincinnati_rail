"""gscore.py (final gate, 27 Nov 2026): my own scorer for the sealed truth, written apart from score_text.py and
target_recall.py, so the two can be checked against each other.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/gate/scripts/gscore.py OUT.npz NAME=PATTERN[:CODES] ... [--truth DIR]

PATTERN holds {plate} (a whole-plate code mask) and CODES the values that count as text (default 2,3).
For every crop of crops.json it keeps, per method:
  - pixel counts from one bincount of (truth class, called text): truth 1 = non-text ink, 2 = text ink, 3 = don't care,
    0 = paper. tp = text called text, fp = non-text called text, fn = text not called text.
  - one row per word: its text pixels (truth 2 inside its poly, filled with cv2.fillPoly on rounded vertices, the box
    rule of the truth README) and how many are called text. A word is found when found >= half its text pixels.
  - for the two full crops, one row per 100 x 100 px tile: tp, fp, fn, non-text px, street text px and found, and
    the straight-run proxy (non-text truth ink lying on a straight run of 61 px or more, called text).
  - the crop-sized cut of each method's codes (for the pictures).
Everything goes into OUT.npz (rows as json strings) for gboot.py and the pictures. Prints a short check table.
"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2

DEF_TRUTH = 'bench_2026-11-26/text_fix/sealed_final'
TILE = 100


def line_kernel(L, ang):
    k = np.zeros((L, L), np.uint8); c = L // 2; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
    p0 = np.round(c - d * c).astype(int); p1 = np.round(c + d * c).astype(int)
    cv2.line(k, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), 1, 1)
    return k


KERNELS = [line_kernel(61, a) for a in np.arange(0, 180, 7.5)]


def straight_runs(nontext):
    """non-text ink that a 61 px straight line fits inside (opening, every 7.5 degrees), the skeptic's stand-in."""
    u = nontext.astype(np.uint8); s = np.zeros(nontext.shape, bool)
    for k in KERNELS: s |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return s


def main():
    a = sys.argv[1:]; truth = DEF_TRUTH
    if '--truth' in a: i = a.index('--truth'); truth = a[i + 1]; a = a[:i] + a[i + 2:]
    outp = a[0]; meths = {}
    for s in a[1:]:
        n, v = s.split('=', 1)
        if ':' in v and v.rsplit(':', 1)[1].replace(',', '').isdigit(): pat, c = v.rsplit(':', 1)
        else: pat, c = v, '2,3'
        meths[n] = (pat, np.array([int(x) for x in c.split(',')]))
    crops = json.load(open(os.path.join(truth, 'crops.json'), encoding='utf8'))
    by_plate = {}
    for cid, c in crops.items():
        if os.path.exists(os.path.join(truth, f'{cid}_mask.png')): by_plate.setdefault(c['plate'], []).append(cid)
    pix, words, tiles, cuts = [], [], [], {}
    for plate in sorted(by_plate):
        codes = {}
        for n, (pat, tc) in meths.items():
            m = cv2.imread(pat.replace('{plate}', plate), cv2.IMREAD_UNCHANGED)
            if m is None: raise SystemExit(f'missing {pat} for {plate}')
            codes[n] = m if m.ndim == 2 else m[..., 0]
        for cid in sorted(by_plate[plate]):
            c = crops[cid]; x0, y0, x1, y1 = c['win']
            T = cv2.imread(os.path.join(truth, f'{cid}_mask.png'), cv2.IMREAD_UNCHANGED)
            assert T.shape == (y1 - y0, x1 - x0), cid
            W = json.load(open(os.path.join(truth, f'{cid}_words.json'), encoding='utf8'))['words']
            ctype = c.get('kind', 'full'); tgt = c.get('target', '')
            st = straight_runs(T == 1) if ctype == 'full' else None
            # word masks once (shared by every method)
            wm = []
            for w in W:
                if not w.get('poly'): continue
                pm = np.zeros(T.shape, np.uint8)
                cv2.fillPoly(pm, [np.round(np.asarray(w['poly'], float) - [x0, y0]).astype(np.int32)], 1)
                t = (pm > 0) & (T == 2)
                wm.append((w, t, int(t.sum())))
            street_px = np.zeros(T.shape, bool)
            for w, t, nn in wm:
                if w['kind'] == 'street': street_px |= t
            for n, (pat, tc) in meths.items():
                P = np.isin(codes[n][y0:y1, x0:x1], tc)
                cuts[f'{n}|{cid}'] = codes[n][y0:y1, x0:x1].copy()
                bc = np.bincount((T.astype(np.int64) * 2 + P).ravel(), minlength=8)
                pix.append(dict(method=n, crop=cid, plate=plate, ft=c['scale_ft_per_inch'], ctype=ctype, target=tgt,
                                paper=int(bc[0] + bc[1]), paper_called=int(bc[1]), t1=int(bc[2] + bc[3]), fp=int(bc[3]),
                                t2=int(bc[4] + bc[5]), tp=int(bc[5]), fn=int(bc[4]), t3=int(bc[6] + bc[7]), t3_called=int(bc[7])))
                for w, t, nn in wm:
                    if not nn: continue
                    words.append(dict(method=n, crop=cid, plate=plate, ft=c['scale_ft_per_inch'], ctype=ctype, target_crop=tgt,
                                      id=w['id'], kind=w['kind'], target=bool(w.get('target')), reading=w.get('reading', ''),
                                      aabb=w.get('aabb'), n=nn, f=int((t & P).sum())))
                if ctype == 'full':
                    H, Wd = T.shape
                    for ty in range(0, H, TILE):
                        for tx in range(0, Wd, TILE):
                            sl = (slice(ty, min(H, ty + TILE)), slice(tx, min(Wd, tx + TILE)))
                            Ts, Ps = T[sl], P[sl]
                            tiles.append(dict(method=n, crop=cid, tx=tx, ty=ty, tp=int(((Ts == 2) & Ps).sum()), fp=int(((Ts == 1) & Ps).sum()),
                                              fn=int(((Ts == 2) & ~Ps).sum()), t1=int((Ts == 1).sum()),
                                              sn=int(street_px[sl].sum()), sf=int((street_px[sl] & Ps).sum()),
                                              st=int(st[sl].sum()), stf=int((st[sl] & Ps).sum())))
        print('done plate', plate, flush=True)
    np.savez_compressed(outp, pix=json.dumps(pix), words=json.dumps(words), tiles=json.dumps(tiles),
                        meths=json.dumps({n: [p, tc.tolist()] for n, (p, tc) in meths.items()}), **{'cut|' + k: v for k, v in cuts.items()})
    # short check table
    for n in meths:
        R = [r for r in pix if r['method'] == n]
        tp = sum(r['tp'] for r in R); fp = sum(r['fp'] for r in R); fn = sum(r['fn'] for r in R)
        P_ = tp / max(1, tp + fp); R_ = tp / max(1, tp + fn)
        print(f'{n}: ALL crops tp {tp} fp {fp} fn {fn}  P {P_:.4f} R {R_:.4f} F1 {2 * P_ * R_ / max(1e-9, P_ + R_):.4f}')


if __name__ == '__main__':
    main()
