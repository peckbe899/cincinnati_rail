"""Rail benchmark scorer (bench_2026-11-21/rail, 21 Nov 2026). Read-only on the repo; writes only where told.

    cd data/sanborn
    python bench_2026-11-21/rail/score_rail_bench.py N RULE_TRACKS.json TRUTH.json OUT_PREFIX [--bins BINS.png] [--label NAME]

RULE_TRACKS.json: {tracks: [{kind, pts}]} (rail_tracks format).  TRUTH.json: Ben's rail_ben format.
Truth tracks with src:'rule' are NOT truth (unchecked): they are an ignore zone (rule length within 30 px of them is
neither right nor wrong). If TRUTH says complete:false, precision is only a lower bound (undrawn rail counts as false).

For each kind (railroad, streetcar), and tolerance 10 and 30 px:
  length recall    share of Ben's length (sampled every 2 px) within tol of a rule track of the same kind
  length precision share of rule track length within tol of a Ben track of the same kind
  cross-kind       rule length of this kind lying within tol of a Ben track of the OTHER kind
Track level (per tolerance):
  found / partial / missed   Ben tracks with coverage >= 80% / 20-80% / < 20%
  pieces                     rule tracks that each cover >= 40 px of the Ben track; 'broken' = 2 or more
  gaps                       uncovered runs of >= 40 px inside a Ben track (between covered stretches)
  false tracks               rule tracks with < 20% of their length near any Ben track of the same kind, and
  false length               all rule length beyond tol of Ben's same-kind tracks
Bin level (with --bins, as tools/sanborn/unet/score_rail.py): Ben length with rule BIN ink of the kind within 10 px
(railroad) / 30 px (streetcar), and rule bin ink more than 25 px from every Ben track of the kind.
Writes OUT_PREFIX.json (all numbers) and OUT_PREFIX.jpg (quarter size: found green/blue, missed red/magenta, rule false
orange/purple, ignore zone grey)."""
import sys, json, os
import numpy as np, cv2

KINDS = ('railroad', 'streetcar'); TOLS = (10, 30)


def plen(p):
    p = np.asarray(p, float); return float(np.hypot(*np.diff(p, axis=0).T).sum()) if len(p) > 1 else 0.0


def samples(p, step=2.0):
    p = np.asarray(p, float); S = []
    for q0, q1 in zip(p[:-1], p[1:]):
        L = np.hypot(*(q1 - q0)); n = max(2, int(np.ceil(L / step)) + 1); S.append(q0[None] + np.linspace(0, 1, n)[:-1, None] * (q1 - q0)[None])
    S.append(p[-1:]); return np.vstack(S)


def seglen_weights(S):
    """length each sample stands for (half the distance to each neighbour)"""
    d = np.hypot(*np.diff(S, axis=0).T); w = np.zeros(len(S)); w[:-1] += d / 2; w[1:] += d / 2; return w


def draw(tracks, H, W, wd=1, val=None):
    m = np.zeros((H, W), np.int32 if val else np.uint8)
    for i, p in enumerate(tracks):
        cv2.polylines(m, [np.round(np.asarray(p)).astype(np.int32)], False, (i + 1) if val else 1, wd)
    return m


def dist(m):
    return cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)


def clip(q, H, W):
    q = np.round(q).astype(int); q[:, 0] = np.clip(q[:, 0], 0, W - 1); q[:, 1] = np.clip(q[:, 1], 0, H - 1); return q


def score(N, rule, truth_json, H, W, bins=None):
    T = truth_json['tracks']; complete = bool(truth_json.get('complete'))
    ben = {k: [np.asarray(t['pts'], float) for t in T if t['kind'] == k and t.get('src') != 'rule'] for k in KINDS}
    unk = [np.asarray(t['pts'], float) for t in T if t.get('src') == 'rule']
    ign = dist(draw(unk, H, W)) <= 30 if unk else np.zeros((H, W), bool)
    rk = {k: [np.asarray(t['pts'], float) for t in rule if t['kind'] == k] for k in KINDS}
    Db = {k: dist(draw(ben[k], H, W)) for k in KINDS}
    Dr = {k: dist(draw(rk[k], H, W)) for k in KINDS}
    out = dict(plate=N, complete=complete, n_truth={k: len(ben[k]) for k in KINDS}, truth_px={k: round(sum(plen(p) for p in ben[k])) for k in KINDS},
               n_rule={k: len(rk[k]) for k in KINDS}, rule_px={k: round(sum(plen(p) for p in rk[k])) for k in KINDS}, n_ignored_truth=len(unk), kinds={})
    for k in KINDS:
        o = out['kinds'][k] = {}
        other = 'streetcar' if k == 'railroad' else 'railroad'
        lab = draw(rk[k], H, W, 1, val=True)
        # per-rule-track samples
        RS = [samples(p) for p in rk[k]]; RW = [seglen_weights(s) for s in RS]
        for tol in TOLS:
            r = o[f'tol{tol}'] = {}
            # recall by length
            tot = got = 0.0; tracks = []
            # which rule track lies near each Ben sample: dilate labels by tol (approximate: nearest-label via distance transform with labels)
            lab_near = None
            if rk[k]:
                _, L = cv2.distanceTransformWithLabels((lab == 0).astype(np.uint8), cv2.DIST_L2, 5, labelType=cv2.DIST_LABEL_PIXEL)
                # map each labelled seed pixel to its track id
                ys, xs = np.nonzero(lab); seedid = np.zeros(L.max() + 1, np.int32); seedid[L[ys, xs]] = lab[ys, xs]; lab_near = seedid[L]
            for ti, p in enumerate(ben[k]):
                S = samples(p); w = seglen_weights(S); q = clip(S, H, W)
                ok = Dr[k][q[:, 1], q[:, 0]] <= tol; ok &= True
                Lp = w.sum(); cov = float((w * ok).sum() / max(Lp, 1e-6)); tot += Lp; got += (w * ok).sum()
                pieces = {}
                if lab_near is not None:
                    ids = np.where(ok, lab_near[q[:, 1], q[:, 0]], 0)
                    for i_, ww in zip(ids, w):
                        if i_: pieces[int(i_)] = pieces.get(int(i_), 0) + ww
                npieces = sum(1 for v in pieces.values() if v >= 40)
                # the same, on the track's interior only (100 px in from each end): Ben splits his tracks at switches,
                # where the other branch's rule track also runs within tol for a few dozen px
                cum = np.cumsum(w); inner = (cum > 100) & (cum < Lp - 100); pin = {}
                if lab_near is not None and inner.any():
                    for i_, ww in zip(ids[inner], w[inner]):
                        if i_: pin[int(i_)] = pin.get(int(i_), 0) + ww
                npieces_in = sum(1 for v in pin.values() if v >= 60)
                # gaps: uncovered runs of >= 40 px between covered stretches
                gaps = 0; run = 0.0; seen_cov = False; pend = 0
                for f, ww in zip(ok, w):
                    if f:
                        if seen_cov and run >= 40: gaps += 1
                        run = 0.0; seen_cov = True
                    else: run += ww
                tracks.append(dict(i=ti, len=round(Lp), cov=round(cov, 3), pieces=npieces, pieces_interior=npieces_in, gaps=gaps, a=[round(float(v)) for v in p[0]], b=[round(float(v)) for v in p[-1]]))
            r['recall'] = round(got / max(tot, 1e-6), 4)
            # precision by length (excluding the ignore zone)
            rt = rf = rc = ri = 0.0; false_tracks = []
            for j, (S, w) in enumerate(zip(RS, RW)):
                q = clip(S, H, W); ig = ign[q[:, 1], q[:, 0]]; near = Db[k][q[:, 1], q[:, 0]] <= tol; cross = (~near) & (Db[other][q[:, 1], q[:, 0]] <= tol)
                ww = w * ~ig; rt += ww.sum(); rf += (ww * near).sum(); rc += (ww * cross).sum(); ri += (w * ig).sum()
                if ww.sum() > 0 and (ww * near).sum() / ww.sum() < 0.2:
                    false_tracks.append(dict(j=j, len=round(float(ww.sum())), cross=round(float((ww * cross).sum())), a=[round(float(v)) for v in S[0]], b=[round(float(v)) for v in S[-1]]))
            r['precision'] = round(rf / rt, 4) if rt else None
            r['rule_len_scored'] = round(rt); r['false_len'] = round(rt - rf); r['cross_kind_len'] = round(rc); r['ignored_len'] = round(ri)
            r['found'] = sum(t['cov'] >= 0.8 for t in tracks); r['partial'] = sum(0.2 <= t['cov'] < 0.8 for t in tracks); r['missed'] = sum(t['cov'] < 0.2 for t in tracks)
            r['broken'] = sum(t['pieces'] >= 2 for t in tracks); r['broken_interior'] = sum(t['pieces_interior'] >= 2 for t in tracks); r['gaps'] = int(sum(t['gaps'] for t in tracks))
            r['false_tracks'] = len(false_tracks); r['false_tracks_len'] = int(sum(t['len'] for t in false_tracks))
            r['tracks'] = tracks; r['false_track_list'] = sorted(false_tracks, key=lambda t: -t['len'])
        o['rule_track_lengths'] = sorted(round(plen(p)) for p in rk[k])
        if bins is not None:
            code = 4 if k == 'railroad' else 5; Dbin = dist((bins == code).astype(np.uint8)); tolb = 10 if k == 'railroad' else 30
            tot = got = 0.0
            for p in ben[k]:
                S = samples(p); w = seglen_weights(S); q = clip(S, H, W); ok = Dbin[q[:, 1], q[:, 0]] <= tolb; tot += w.sum(); got += (w * ok).sum()
            far = (bins == code) & (Db[k] > 25) & ~ign
            o['bin'] = dict(tol=tolb, recall=round(got / max(tot, 1e-6), 4), bin_px=int((bins == code).sum()), far_px=int(far.sum()))
    return out


def picture(path, N, rule, truth_json, res, H, W):
    im = cv2.imread(f'cufp/22-{N}.jpg'); c = (im * 0.35 + 255 * 0.65).astype(np.uint8)
    unk = [np.asarray(t['pts'], float) for t in truth_json['tracks'] if t.get('src') == 'rule']
    for p in unk: cv2.polylines(c, [np.round(p).astype(np.int32)], False, (150, 150, 150), 61)
    for k in KINDS:
        tol = 10
        ben = [np.asarray(t['pts'], float) for t in truth_json['tracks'] if t['kind'] == k and t.get('src') != 'rule']
        rk = [np.asarray(t['pts'], float) for t in rule if t['kind'] == k]
        Dr = dist(draw(rk, H, W)); Db = dist(draw(ben, H, W))
        for p in ben:
            S = samples(p, 6); q = clip(S, H, W); ok = Dr[q[:, 1], q[:, 0]] <= tol
            for (x, y), f in zip(q, ok): cv2.circle(c, (int(x), int(y)), 7, ((0, 170, 0) if f else (0, 0, 255)) if k == 'railroad' else ((220, 120, 0) if f else (255, 0, 255)), -1)
        for p in rk:
            S = samples(p, 6); q = clip(S, H, W); bad = Db[q[:, 1], q[:, 0]] > tol
            for (x, y), f in zip(q, bad):
                if f: cv2.circle(c, (int(x), int(y)), 7, (0, 140, 255) if k == 'railroad' else (150, 0, 150), -1)
            cv2.polylines(c, [np.round(p).astype(np.int32)], False, (0, 0, 0), 3)
    cv2.imwrite(path, cv2.resize(c, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])


def summary_lines(res):
    L = []
    for k in KINDS:
        o = res['kinds'][k]
        L.append(f"{k}: Ben {res['n_truth'][k]} tracks {res['truth_px'][k]} px | rule {res['n_rule'][k]} tracks {res['rule_px'][k]} px" + (f" | bin recall {100 * o['bin']['recall']:.1f}% (within {o['bin']['tol']} px), bin far {o['bin']['far_px']} px" if 'bin' in o else ''))
        for tol in TOLS:
            r = o[f'tol{tol}']; pr = 'n/a' if r['precision'] is None else f"{100 * r['precision']:.1f}%"
            L.append(f"  within {tol:2d} px: recall {100 * r['recall']:.1f}%  precision {pr}{'' if res['complete'] else ' (lower bound)'}  false {r['false_len']} px (cross-kind {r['cross_kind_len']})"
                     f" | Ben tracks found {r['found']} partial {r['partial']} missed {r['missed']} | broken {r['broken']} (interior {r['broken_interior']}) gaps {r['gaps']} | false tracks {r['false_tracks']} ({r['false_tracks_len']} px)")
    return L


if __name__ == '__main__':
    N, rp, tp, outp = sys.argv[1:5]
    rule = json.load(open(rp, encoding='utf8'))['tracks']; TJ = json.load(open(tp, encoding='utf8'))
    H, W = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_GRAYSCALE).shape[:2]
    bins = cv2.imread(sys.argv[sys.argv.index('--bins') + 1], 0) if '--bins' in sys.argv else None
    res = score(N, rule, TJ, H, W, bins)
    res['rule_file'] = rp; res['truth_file'] = tp; res['label'] = sys.argv[sys.argv.index('--label') + 1] if '--label' in sys.argv else ''
    json.dump(res, open(outp + '.json', 'w'), indent=1)
    for l in summary_lines(res): print(l)
    if '--nopic' not in sys.argv: picture(outp + '.jpg', N, rule, TJ, res, H, W)
