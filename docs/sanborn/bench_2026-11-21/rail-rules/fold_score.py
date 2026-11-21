"""Rail scores per fold of plate 44 (rail-rules, 21 Nov 2026). Read-only; writes nothing by itself.

Wraps score_rail_bench.py (an unchanged copy of bench_2026-11-21/rail/score_rail_bench.py, the rail agent's scorer) and
adds a region restriction, using bench44's folds so that every agent cuts plate 44 the same way:
  fold A ('north-west grid + east'): (x < 2950 and y < 3560) or x >= 5400;   fold B: the rest.
Length scores (recall, precision, F1 at 10 and 30 px) count only samples inside the region: Ben's samples for recall,
rule samples for precision (a rule track outside the region still counts as 'near' a Ben sample inside it).
Track scores (found / partial / missed, broken in the interior, gaps, false tracks) count a Ben track, or a rule track,
in the region that holds the larger part of its length.
For region 'all' the numbers are score_rail_bench.score()'s own (checked in check_fold_score.py)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from score_rail_bench import score, samples, seglen_weights, draw, dist, clip, KINDS, TOLS

FX, FY, FX2 = 2950, 3560, 5400


def in_fold(q, reg):
    if reg == 'all': return np.ones(len(q), bool)
    a = ((q[:, 0] < FX) & (q[:, 1] < FY)) | (q[:, 0] >= FX2)
    return a if reg == 'A' else ~a


def major(p, reg):
    S = samples(p); w = seglen_weights(S); return (w * in_fold(S, reg)).sum() > 0.5 * w.sum()


def fscore(N, rule, TJ, H, W, regions=('all', 'A', 'B')):
    """{region: {kind: {tolN: {recall, precision, f1, rule_len, ben_len, found, partial, missed, broken_interior, gaps, false_tracks, false_tracks_len}}}}"""
    full = score(N, rule, TJ, H, W)
    T = TJ['tracks']
    ben = {k: [np.asarray(t['pts'], float) for t in T if t['kind'] == k and t.get('src') != 'rule'] for k in KINDS}
    unk = [np.asarray(t['pts'], float) for t in T if t.get('src') == 'rule']
    ign = dist(draw(unk, H, W)) <= 30 if unk else np.zeros((H, W), bool)
    rk = {k: [np.asarray(t['pts'], float) for t in rule if t['kind'] == k] for k in KINDS}
    Db = {k: dist(draw(ben[k], H, W)) for k in KINDS}; Dr = {k: dist(draw(rk[k], H, W)) for k in KINDS}
    out = {}
    for reg in regions:
        o = out[reg] = {}
        for k in KINDS:
            o[k] = {}
            bS = [samples(p) for p in ben[k]]; bW = [seglen_weights(s) for s in bS]; bq = [clip(s, H, W) for s in bS]
            rS = [samples(p) for p in rk[k]]; rW = [seglen_weights(s) for s in rS]; rq = [clip(s, H, W) for s in rS]
            bmaj = [major(p, reg) for p in ben[k]]; rmaj = [major(p, reg) for p in rk[k]]
            for tol in TOLS:
                tot = got = 0.0
                for S, w, q in zip(bS, bW, bq):
                    f = in_fold(S, reg); ok = Dr[k][q[:, 1], q[:, 0]] <= tol; tot += (w * f).sum(); got += (w * f * ok).sum()
                rt = rf = 0.0
                for S, w, q in zip(rS, rW, rq):
                    f = in_fold(S, reg) & ~ign[q[:, 1], q[:, 0]]; near = Db[k][q[:, 1], q[:, 0]] <= tol; rt += (w * f).sum(); rf += (w * f * near).sum()
                R = got / tot if tot else None; P = rf / rt if rt else None
                F = (2 * P * R / (P + R) if P is not None and R is not None and P + R > 0 else None)
                ft = full['kinds'][k][f'tol{tol}']; trk = [t for t in ft['tracks'] if bmaj[t['i']]]; fls = [t for t in ft['false_track_list'] if rmaj[t['j']]]
                o[k][f'tol{tol}'] = dict(recall=None if R is None else round(R, 4), precision=None if P is None else round(P, 4), f1=None if F is None else round(F, 4),
                                         ben_len=round(tot), rule_len=round(rt), false_len=round(rt - rf),
                                         n_ben=len(trk), found=sum(t['cov'] >= 0.8 for t in trk), partial=sum(0.2 <= t['cov'] < 0.8 for t in trk), missed=sum(t['cov'] < 0.2 for t in trk),
                                         broken_interior=sum(t['pieces_interior'] >= 2 for t in trk), gaps=int(sum(t['gaps'] for t in trk)),
                                         false_tracks=len(fls), false_tracks_len=int(sum(t['len'] for t in fls)), n_rule=int(sum(rmaj)))
    return out, full
