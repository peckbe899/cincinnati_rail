"""sk_score.py (skeptic, 27 Nov 2026): my own scorer for the sealed truth (sealed_final), written apart from
score_text.py, target_recall.py and the gate's gscore.py, so all of them can be checked against each other.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_score.py OUT.json NAME=PATTERN[:CODES] ... [--truth DIR]

PATTERN holds {plate} (a whole-plate code mask); CODES the values that count as text (default 2,3).

How it differs from the others (on purpose):
  - Pixel tallies are counted with np.count_nonzero on each class, not one bincount.
  - Every word is filled twice: (a) cv2.fillPoly on rounded vertices (the truth README's rule, which the builder used
    for text_px_final) and (b) a pixel-centre test with shapely.contains_xy on the unrounded polygon (pixel (x, y) is in
    when its centre (x, y) lies inside or on the edge). (a) gives the numbers; (a) is
    checked against the builder's own text_px_final; (b) shows how much the numbers hang on the fill rule.
  - For each word it keeps the codes of the missed text pixels (which code finder left them in).
  - Full crops: 100 px tiles, and the straight-run proxy made with my own line footprints (a DDA line, scipy
    binary_opening), a different kernel maker and opening than the cv2.line / cv2.morphologyEx ones of the gate and integrate.
(skimage is not importable on the system python: lazy_loader is missing; no installs.)
Writes OUT.json: {meths, crops: [...], words: [...], tiles: [...]}.
"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
import shapely
from scipy import ndimage as ndi

DEF_TRUTH = 'bench_2026-11-26/text_fix/sealed_final'
TILE = 100


def footprints(L=61, step=7.5):
    out = []
    c = L // 2
    for a in np.arange(0, 180, step):
        d = np.array([np.cos(np.radians(a)), np.sin(np.radians(a))])
        p0 = np.round(c - d * c).astype(int); p1 = np.round(c + d * c).astype(int)
        k = np.zeros((L, L), bool); nstep = int(max(abs(p1 - p0))) + 1
        for t in np.linspace(0, 1, nstep):
            x, y = np.floor(p0 + t * (p1 - p0) + 0.5).astype(int); k[y, x] = True
        out.append(k)
    return out


FP = footprints()


def straight(mask):
    s = np.zeros(mask.shape, bool)
    for k in FP:
        s |= ndi.binary_opening(mask, structure=k)
    return s


def main():
    a = sys.argv[1:]; truth = DEF_TRUTH
    if '--truth' in a: i = a.index('--truth'); truth = a[i + 1]; a = a[:i] + a[i + 2:]
    outp = a[0]; meths = {}
    for s in a[1:]:
        n, v = s.split('=', 1)
        if ':' in v and v.rsplit(':', 1)[1].replace(',', '').isdigit(): pat, c = v.rsplit(':', 1)
        else: pat, c = v, '2,3'
        meths[n] = (pat, [int(x) for x in c.split(',')])
    crops = json.load(open(os.path.join(truth, 'crops.json'), encoding='utf8'))
    plates = sorted({c['plate'] for c in crops.values()}, key=lambda s: (len(s), s))
    CR, WR, TR = [], [], []
    for plate in plates:
        codes = {}
        for n, (pat, tc) in meths.items():
            m = cv2.imread(pat.replace('{plate}', plate), cv2.IMREAD_UNCHANGED)
            if m is None: raise SystemExit(f'missing {pat} for plate {plate}')
            codes[n] = m if m.ndim == 2 else m[..., 0]
        for cid in sorted(k for k, c in crops.items() if c['plate'] == plate):
            c = crops[cid]; x0, y0, x1, y1 = c['win']
            T = cv2.imread(os.path.join(truth, f'{cid}_mask.png'), cv2.IMREAD_UNCHANGED)
            assert T.shape == (y1 - y0, x1 - x0), cid
            H, Wd = T.shape
            words = json.load(open(os.path.join(truth, f'{cid}_words.json'), encoding='utf8'))['words']
            t2 = T == 2; t1 = T == 1; t3 = T == 3; t0 = T == 0
            ctype = c.get('kind', 'full'); tgt = c.get('target', '')
            st = straight(t1) if ctype == 'full' else None
            preds = {n: np.isin(codes[n][y0:y1, x0:x1], tc) for n, (pat, tc) in meths.items()}
            raw = {n: codes[n][y0:y1, x0:x1] for n in meths}
            for n, P in preds.items():
                CR.append(dict(method=n, crop=cid, plate=plate, ft=c['scale_ft_per_inch'], ctype=ctype, target=tgt,
                               tp=int(np.count_nonzero(P & t2)), fp=int(np.count_nonzero(P & t1)), fn=int(np.count_nonzero(~P & t2)),
                               t1=int(np.count_nonzero(t1)), t2=int(np.count_nonzero(t2)), t3=int(np.count_nonzero(t3)),
                               t3_called=int(np.count_nonzero(P & t3)), paper_called=int(np.count_nonzero(P & t0)),
                               straight_px=int(st.sum()) if st is not None else None,
                               straight_called=int(np.count_nonzero(st & P)) if st is not None else None))
            street = np.zeros(T.shape, bool)
            for w in words:
                p = w.get('poly')
                if not p: continue
                pa = np.round(np.asarray(p, float) - [x0, y0]).astype(np.int32)
                m_cv = np.zeros(T.shape, np.uint8); cv2.fillPoly(m_cv, [pa], 1); m_cv = (m_cv > 0) & t2
                q = np.asarray(p, float) - [x0, y0]
                m_sk = np.zeros(T.shape, bool)
                qx0, qy0 = np.maximum(0, np.floor(q.min(0)).astype(int)); qx1, qy1 = np.minimum([Wd - 1, H - 1], np.ceil(q.max(0)).astype(int))
                if qx1 >= qx0 and qy1 >= qy0:
                    yy, xx = np.mgrid[qy0:qy1 + 1, qx0:qx1 + 1]
                    poly = shapely.Polygon(q)
                    ins = shapely.contains_xy(poly, xx.ravel().astype(float), yy.ravel().astype(float)) | shapely.intersects_xy(poly.boundary, xx.ravel().astype(float), yy.ravel().astype(float))
                    m_sk[yy.ravel()[ins], xx.ravel()[ins]] = True
                m_sk &= t2
                if w['kind'] == 'street': street |= m_cv
                ncv = int(m_cv.sum()); nsk = int(m_sk.sum())
                box_ink = 0; box_nontext = 0
                ax0, ay0, ax1, ay1 = [int(v) for v in w['aabb']]
                bx0, by0 = max(0, ax0 - x0), max(0, ay0 - y0); bx1, by1 = min(Wd, ax1 - x0 + 1), min(H, ay1 - y0 + 1)
                if bx1 > bx0 and by1 > by0:
                    sub = T[by0:by1, bx0:bx1]; box_ink = int(np.isin(sub, (1, 2, 3)).sum()); box_nontext = int((sub == 1).sum())
                r = dict(crop=cid, plate=plate, ft=c['scale_ft_per_inch'], ctype=ctype, target_crop=tgt, id=w['id'], kind=w['kind'],
                         target=bool(w.get('target')), reading=w.get('reading', ''), flags=w.get('flags') or [], touches_line=w.get('touches_line'),
                         aabb=w['aabb'], height=w.get('height'), length=w.get('length'), ink_px=w.get('ink_px'),
                         text_px_final=w.get('text_px_final'), n=ncv, n_sk=nsk, box_ink=box_ink, box_nontext=box_nontext)
                if ncv:
                    lab, ncomp = ndi.label(m_cv, structure=np.ones((3, 3)))
                    r['text_components'] = int(ncomp)
                    dt = ndi.distance_transform_edt(m_cv)
                    r['stroke_w_median'] = float(2 * np.median(dt[m_cv]))
                for n, P in preds.items():
                    r[f'f_{n}'] = int(np.count_nonzero(m_cv & P)); r[f'fsk_{n}'] = int(np.count_nonzero(m_sk & P))
                    miss = m_cv & ~P
                    r[f'miss_codes_{n}'] = {str(int(k)): int(v) for k, v in zip(*np.unique(raw[n][miss], return_counts=True))}
                WR.append(r)
            if ctype == 'full':
                for ty in range(0, H, TILE):
                    for tx in range(0, Wd, TILE):
                        sl = (slice(ty, min(H, ty + TILE)), slice(tx, min(Wd, tx + TILE)))
                        row = dict(crop=cid, tx=tx, ty=ty, t1=int(t1[sl].sum()), sn=int(street[sl].sum()), st=int(st[sl].sum()))
                        for n, P in preds.items():
                            Ps = P[sl]
                            row[n] = dict(tp=int((t2[sl] & Ps).sum()), fp=int((t1[sl] & Ps).sum()), fn=int((t2[sl] & ~Ps).sum()),
                                          sf=int((street[sl] & Ps).sum()), stf=int((st[sl] & Ps).sum()))
                        TR.append(row)
        print('done plate', plate, flush=True)
    json.dump(dict(meths=meths, truth=truth, crops=CR, words=WR, tiles=TR), open(outp, 'w', encoding='utf8', newline='\n'))
    for n in meths:
        R = [r for r in CR if r['method'] == n]
        tp, fp, fn = (sum(r[k] for r in R) for k in ('tp', 'fp', 'fn'))
        P_ = tp / max(1, tp + fp); R_ = tp / max(1, tp + fn)
        print(f'{n}: all crops tp {tp} fp {fp} fn {fn}  P {P_:.4f} R {R_:.4f} F1 {2 * P_ * R_ / max(1e-9, P_ + R_):.4f}')
    bad = [(w['crop'], w['id'], w['n'], w['text_px_final']) for w in WR if w['text_px_final'] is not None and w['n'] != w['text_px_final']]
    print(f'words whose cv2 fill differs from the builder text_px_final: {len(bad)} of {len(WR)}', bad[:10])


if __name__ == '__main__':
    main()
