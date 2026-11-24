"""review-labels, 24 Nov 2026: score pseudo labels against Ben's own street map, with code written apart from
make_labels_v2.py (it does not use the map labels' street rays; it reads Ben's blocks and lines directly).

    python -B score_pseudo.py PSEUDO_DIR N STREETMAP.json OUT.json [--val-x X]

Truth, at half size (the area label's grid):
  B  block: inside one of Ben's closed faces at least NARROW (60) full px across (street_map.py's faces; a narrower face,
     an alley closed at both ends, is street).
  S  street: on the paper, not B, and between two of Ben's lines (1 px) met by a scan in one of four directions (0, 45, 90,
     135 deg) when the two lines run within PAR (15) deg of parallel, the scan is within 50 deg of their normal, and the
     width across them is at most WMAX_FT (130 ft): the ground between two facing block sides. A narrow face is S.
     S at most NARROW_FT (40 ft) wide (and every narrow face) is reported apart: alleys and narrow streets.
  O  open: on the paper, neither (ground Ben's map does not decide: open land, rail yards, unclosed blocks).
  A 2 half-px band either side of every B edge is not scored.
Area: pseudo block px and pseudo street px by truth class; precision = right / (right + wrong) over B and S only.
Merges: each 8-connected piece of pseudo block, and which of Ben's blocks it overlaps (>= 200 half px or 5% of the block).
Lines (full size): pseudo positives within 3 and 6 px of Ben's printed/drawn lines (and of all his lines); Ben's printed and
drawn lines sampled every px: taught 1, 0 or 255 at the centre, and 'touched': a negative within 2 px of the centre.
Each of Ben's lines with >= 25% of its length touched by a negative is listed (a block line taught as 'not a line').
"""
import json, sys
import numpy as np
import cv2

SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
NARROW, WMAX_FT, BAND, PAR, NARROW_FT = 60.0, 130.0, 2, 15.0, 40.0


def paper(N, w, h):
    return cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5


def first_hit(ids):
    """for each pixel, the distance to and the id of the first line pixel to the left, right, up and down (ids: float32, 0 = none)"""
    h, w = ids.shape; wall = ids > 0; out = {}
    ix = np.arange(w, dtype=np.int64)[None, :].repeat(h, 0); iy = np.arange(h, dtype=np.int64)[:, None].repeat(w, 1); rows, cols = iy, ix
    last = np.maximum.accumulate(np.where(wall, ix, -1), 1); out['L'] = (np.where(last >= 0, ix - last, 10 ** 6), np.where(last >= 0, ids[rows, np.maximum(last, 0)], 0))
    nxt = np.minimum.accumulate(np.where(wall, ix, w)[:, ::-1], 1)[:, ::-1]; out['R'] = (np.where(nxt < w, nxt - ix, 10 ** 6), np.where(nxt < w, ids[rows, np.minimum(nxt, w - 1)], 0))
    last = np.maximum.accumulate(np.where(wall, iy, -1), 0); out['U'] = (np.where(last >= 0, iy - last, 10 ** 6), np.where(last >= 0, ids[np.maximum(last, 0), cols], 0))
    nxt = np.minimum.accumulate(np.where(wall, iy, h)[::-1], 0)[::-1]; out['D'] = (np.where(nxt < h, nxt - iy, 10 ** 6), np.where(nxt < h, ids[np.minimum(nxt, h - 1), cols], 0))
    return out


def between(ids, dirs, wmax, rot):
    """pixels between two of Ben's lines that run within PAR deg of parallel, the scan within 50 deg of their normal, and
    the street's width across them (the scan length times the cosine) at most wmax. Scans along x and y of ids (which is
    the plate turned by rot deg)."""
    d = first_hit(ids); res = np.full(ids.shape, np.inf, np.float32)
    for (k1, k2), sv in ((('L', 'R'), (1.0, 0.0)), (('U', 'D'), (0.0, 1.0))):
        (d1, i1), (d2, i2) = d[k1], d[k2]; i1 = i1.astype(np.int64); i2 = i2.astype(np.int64)
        u1, u2 = dirs[i1], dirs[i2]                                         # unit directions in the turned frame
        par = np.abs((u1 * u2).sum(-1)) >= np.cos(np.radians(PAR))
        cs = np.abs(u1[..., 0] * sv[1] - u1[..., 1] * sv[0])               # |cos| between the scan and the line's normal
        wd = (d1 + d2) * cs; ok = (i1 > 0) & (i2 > 0) & (d1 > 0) & (d2 > 0) & par & (cs >= np.cos(np.radians(50))) & (wd <= wmax)   # d > 0: not the line's own pixels
        res = np.where(ok, np.minimum(res, wd), res)
    return res                                                               # the street's width there (half px), inf: not between


def truth(N, sm, h, w, ftpi):
    pxh = 300.0 / ftpi / 2.0                                    # half px per foot
    Bi = np.zeros((h, w), np.int32); NF = np.zeros((h, w), np.uint8)
    for b in sorted(sm['blocks'], key=lambda b: -b['area_px']):
        r = np.round(np.array(b['ring'], float) / 2.0).astype(np.int32)
        if b['narrow_px'] < NARROW: cv2.fillPoly(NF, [r], 1)
        else: cv2.fillPoly(Bi, [r], b['id'])
    Bi[NF > 0] = 0; B = Bi > 0
    ids = np.zeros((h, w), np.float32); U0 = [(0.0, 0.0)]
    for i, l in enumerate(sm['lines']):
        a, b = np.array(l['a'], float) / 2, np.array(l['b'], float) / 2; L = np.hypot(*(b - a))
        U0.append(tuple((b - a) / max(L, 1e-6)))
        cv2.line(ids, tuple(np.round(a).astype(int)), tuple(np.round(b).astype(int)), float(i + 1), 1)
    U0 = np.array(U0)
    ah = paper(N, w, h); Wd = between(ids, U0, WMAX_FT * pxh, 0)
    c = (w / 2.0, h / 2.0); D = int(np.ceil(np.hypot(w, h))); M = cv2.getRotationMatrix2D(c, 45, 1.0); M[:, 2] += (D / 2.0 - c[0], D / 2.0 - c[1])
    idr = cv2.warpAffine(ids, M, (D, D), flags=cv2.INTER_NEAREST, borderValue=0)
    idr = cv2.dilate(idr, np.ones((2, 2), np.uint8))                        # a 1 px line can fall apart when turned
    R = M[:, :2]; Ur = U0 @ R.T                                             # the lines' directions in the turned frame
    Wr = between(idr, Ur, WMAX_FT * pxh, 45).astype(np.float32); Wr[~np.isfinite(Wr)] = 1e6   # float32: cv2 4.13's warpAffine gave wrong values on this float64 map
    Wd = np.minimum(Wd, cv2.warpAffine(Wr, cv2.invertAffineTransform(M), (w, h), flags=cv2.INTER_NEAREST, borderValue=1e6))
    S = (Wd <= WMAX_FT * pxh) & ah & ~B; S |= (NF > 0) & ah
    Wd[NF > 0] = 0.0; NAR = S & (Wd <= NARROW_FT * pxh)                    # alleys and narrow streets (a narrow face counts as one)
    edge = cv2.morphologyEx(B.astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8)) > 0
    band = cv2.dilate(edge.astype(np.uint8), np.ones((2 * BAND + 1, 2 * BAND + 1), np.uint8)) > 0
    O = ah & ~B & ~S
    return dict(B=B, Bi=Bi, S=S, O=O, band=band, ah=ah, NF=NF > 0, NAR=NAR)


def area_scores(lab, T, roi):
    r = {}
    sc = roi & ~T['band']
    for nm, v in (('block', 1), ('street', 0)):
        p = (lab == v) & roi; ps = p & sc
        inB, inS, inO = int((ps & T['B']).sum()), int((ps & T['S']).sum()), int((ps & T['O']).sum())
        right, wrong = (inB, inS) if v == 1 else (inS, inB)
        r[nm] = dict(px=int(p.sum()), in_band=int((p & T['band']).sum()), in_block=inB, in_street=inS, in_open=inO,
                     precision=round(right / max(1, right + wrong), 4), share_in_open=round(inO / max(1, inB + inS + inO), 4),
                     in_narrow_face=int((ps & T['NF']).sum()))
    r['coverage'] = dict(ben_block_taught_block=round(float(((lab == 1) & T['B'] & roi).sum() / max(1, (T['B'] & roi).sum())), 4),
                         ben_street_taught_street=round(float(((lab == 0) & T['S'] & roi).sum() / max(1, (T['S'] & roi).sum())), 4),
                         ben_open_taught=round(float(((lab != 255) & T['O'] & roi).sum() / max(1, (T['O'] & roi).sum())), 4),
                         ben_narrow_street=dict(px=int((T['NAR'] & roi & ~T['band']).sum()), taught_block=round(float(((lab == 1) & T['NAR'] & roi & ~T['band']).sum() / max(1, (T['NAR'] & roi & ~T['band']).sum())), 4),
                                                taught_street=round(float(((lab == 0) & T['NAR'] & roi & ~T['band']).sum() / max(1, (T['NAR'] & roi & ~T['band']).sum())), 4)),
                         ben_wide_street=dict(px=int((T['S'] & ~T['NAR'] & roi & ~T['band']).sum()), taught_block=round(float(((lab == 1) & T['S'] & ~T['NAR'] & roi & ~T['band']).sum() / max(1, (T['S'] & ~T['NAR'] & roi & ~T['band']).sum())), 4),
                                              taught_street=round(float(((lab == 0) & T['S'] & ~T['NAR'] & roi & ~T['band']).sum() / max(1, (T['S'] & ~T['NAR'] & roi & ~T['band']).sum())), 4)),
                         truth_px=dict(block=int((T['B'] & roi).sum()), street=int((T['S'] & roi).sum()), open=int((T['O'] & roi).sum())))
    return r


def merges(lab, T, roi, sm):
    n, cc, st, _ = cv2.connectedComponentsWithStats(((lab == 1) & roi).astype(np.uint8), connectivity=8)
    area = {b['id']: 0 for b in sm['blocks']}; ids, cnt = np.unique(T['Bi'][T['Bi'] > 0], return_counts=True); area.update(dict(zip(ids.tolist(), cnt.tolist())))
    out = []
    for k in range(1, n):
        if st[k, cv2.CC_STAT_AREA] < 200: continue
        m = cc == k; ov = T['Bi'][m]; u, c = np.unique(ov[ov > 0], return_counts=True)
        hit = [int(i) for i, cn in zip(u, c) if cn >= 200 or cn >= 0.05 * area.get(int(i), 1)]
        if len(hit) >= 2:
            out.append(dict(piece=k, px=int(st[k, cv2.CC_STAT_AREA]), ben_blocks=hit, px_on_ben_street=int((m & T['S']).sum()), px_on_open=int((m & T['O']).sum()),
                            bbox_half=[int(st[k, 0]), int(st[k, 1]), int(st[k, 0] + st[k, 2]), int(st[k, 1] + st[k, 3])]))
    pieces = int(sum(1 for k in range(1, n) if st[k, cv2.CC_STAT_AREA] >= 200))
    return dict(pieces=pieces, merged_pieces=len(out), ben_blocks_in_merges=len({i for o in out for i in o['ben_blocks']}), ben_blocks=len([b for b in sm['blocks'] if b['narrow_px'] >= NARROW]),
                ben_blocks_in_roi=int(len(np.unique(T['Bi'][(T['Bi'] > 0) & roi]))), merges=out)


def line_scores(t, sm, roif, N):
    H, W = t.shape
    def rast(kinds):
        m = np.zeros((H, W), np.uint8)
        for l in sm['lines']:
            if l['kind'] in kinds: cv2.line(m, tuple(np.round(l['a']).astype(int)), tuple(np.round(l['b']).astype(int)), 1, 1)
        return m
    P = rast(('printed', 'drawn')); A = rast(('printed', 'drawn', 'sheet_edge', 'no_printed_line'))
    dP = cv2.distanceTransform((P == 0).astype(np.uint8), cv2.DIST_L2, 5); dA = cv2.distanceTransform((A == 0).astype(np.uint8), cv2.DIST_L2, 5)
    pp = (t == 1) & roif; pn = (t == 0) & roif
    r = dict(pos_px=int(pp.sum()), neg_px=int(pn.sum()))
    for tol in (3, 6):
        r[f'pos_precision_tol{tol}'] = round(float((dP[pp] <= tol).mean()), 4) if pp.any() else None
        r[f'pos_precision_tol{tol}_incl_sheet_edge'] = round(float((dA[pp] <= tol).mean()), 4) if pp.any() else None
    r['neg_within_3px_of_ben_line'] = round(float((dA[pn] <= 3).mean()), 5) if pn.any() else None
    negnear = cv2.dilate(pn.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    per = []; agg = {}
    for i, l in enumerate(sm['lines']):
        if l['kind'] not in ('printed', 'drawn'): continue
        a, b = np.array(l['a'], float), np.array(l['b'], float); n = max(2, int(np.hypot(*(b - a))) + 1); q = a + np.outer(np.linspace(0, 1, n), b - a)
        x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); k = roif[y, x]
        if not k.any(): continue
        v = t[y[k], x[k]]; tn = negnear[y[k], x[k]]
        for nm in (l['kind'], 'all'):
            g = agg.setdefault(nm, dict(len=0, pos=0, neg=0, unscored=0, touched=0))
            g['len'] += len(v); g['pos'] += int((v == 1).sum()); g['neg'] += int((v == 0).sum()); g['unscored'] += int((v == 255).sum()); g['touched'] += int(tn.sum())
        if tn.mean() >= 0.25 and len(v) >= 30: per.append(dict(line=i, kind=l['kind'], a=l['a'], b=l['b'], len_px=int(len(v)), touched_share=round(float(tn.mean()), 3), pos_share=round(float((v == 1).mean()), 3)))
    r['ben_lines'] = {k: dict(length_px=g['len'], taught_positive=round(g['pos'] / max(1, g['len']), 4), negative_at_centre=round(g['neg'] / max(1, g['len']), 4),
                              left_255=round(g['unscored'] / max(1, g['len']), 4), negative_within_2px=round(g['touched'] / max(1, g['len']), 4)) for k, g in agg.items()}
    r['ben_lines_touched_by_negatives'] = sorted(per, key=lambda d: -d['len_px'] * d['touched_share'])
    far = pp & (dA > 6)                                   # positives not near any of Ben's lines
    return r, far


def main():
    pdir, N, smf, out = sys.argv[1:5]; vx = int(sys.argv[sys.argv.index('--val-x') + 1]) if '--val-x' in sys.argv else None
    sm = json.load(open(smf, encoding='utf8')); lab = cv2.imread(f'{pdir}/{N}/label.png', cv2.IMREAD_UNCHANGED); t = cv2.imread(f'{pdir}/{N}/lines.png', cv2.IMREAD_UNCHANGED)
    meta = json.load(open(f'{pdir}/{N}/meta.json', encoding='utf8')); ftpi = meta.get('ft_per_inch') or 100
    h, w = lab.shape; H, W = t.shape; T = truth(N, sm, h, w, ftpi)
    parts = [('whole', np.ones((h, w), bool))]
    if vx is not None:
        v = np.zeros((h, w), bool); v[:, vx:] = True; parts += [('train_part', ~v), ('val_part', v)]
    res = dict(plate=N, pseudo=pdir, streetmap=smf, label_sha=meta['files']['label.png']['sha256'], lines_sha=meta['files']['lines.png']['sha256'], ft_per_inch=ftpi,
               truth_rule=dict(narrow_px=NARROW, wmax_ft=WMAX_FT, band_half_px=BAND, par_deg=PAR, narrow_street_ft=NARROW_FT), counts=meta.get('counts'), parts={})
    Bf = cv2.resize(T['B'].astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0; Sf = cv2.resize(T['S'].astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    for nm, roi in parts:
        roif = cv2.resize(roi.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
        ls, far = line_scores(t, sm, roif, N)
        ls['pos_far_from_ben_lines'] = dict(px=int(far.sum()), in_ben_block=int((far & Bf).sum()), in_ben_street=int((far & Sf).sum()), elsewhere=int((far & ~Bf & ~Sf).sum()))
        res['parts'][nm] = dict(area=area_scores(lab, T, roi), merges=merges(lab, T, roi, sm), lines=ls)
        if nm == 'whole':
            cv2.imwrite(out.replace('.json', '_far_pos.png'), (cv2.dilate(far.astype(np.uint8), np.ones((3, 3), np.uint8)) * 255)[::2, ::2])
    vis = np.zeros((h, w, 3), np.uint8); vis[T['B']] = (90, 160, 90); vis[T['S']] = (200, 160, 90); vis[T['O']] = (140, 140, 140); vis[T['band']] = (0, 0, 0)
    cv2.imwrite(out.replace('.json', '_truth.jpg'), cv2.resize(vis, (w // 2, h // 2), interpolation=cv2.INTER_NEAREST))
    json.dump(res, open(out, 'w', encoding='utf8', newline='\n'), indent=1)
    for nm, p in res['parts'].items():
        a, m, l = p['area'], p['merges'], p['lines']
        print(N, nm, 'block prec', a['block']['precision'], 'open', a['block']['share_in_open'], '| street prec', a['street']['precision'], 'open', a['street']['share_in_open'],
              '| cov', a['coverage'], '| merges', m['merged_pieces'], 'of', m['pieces'], 'pieces; Ben blocks merged', m['ben_blocks_in_merges'], '/', m['ben_blocks_in_roi'],
              '| pos prec3', l['pos_precision_tol3'], 'prec6', l['pos_precision_tol6'], 'incl edge6', l['pos_precision_tol6_incl_sheet_edge'], '| ben', l['ben_lines'].get('all'), '| touched lines', len(l['ben_lines_touched_by_negatives']), flush=True)


if __name__ == '__main__':
    main()
