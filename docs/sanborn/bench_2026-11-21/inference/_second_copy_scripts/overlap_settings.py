"""How much of the exported side length two settings share (within 8 px, directions within 20 degrees), per plate.

    python overlap_settings.py SETTING_A SETTING_B N[,N...] [--eye EYE.json]

From qa/SETTING/N/N_edges.json. Each side is sampled every 2 px. Prints and writes overlap/A_vs_B.json: per plate and in
all, A's length, the part of it B also exports ('shared'), the part only A exports, and the same for B.
--eye: a json of by-eye precisions {"A_only": p, "B_only": p, "shared": p} (from sample_sides.py montages) to turn the
lengths into an estimate of right length for each setting (ESTIMATE, not a measurement).
"""
import json, os, sys
import numpy as np
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
a = sys.argv[1:]
A, B, plates = a[0], a[1], a[2].split(','); eye = json.load(open(a[a.index('--eye') + 1])) if '--eye' in a else None


def samp(edges):
    P, D = [], []
    for e in edges:
        p0, p1 = np.array(e['a'], float), np.array(e['b'], float); L = np.hypot(*(p1 - p0))
        if L < 1: continue
        m = int(np.ceil(L / 2)); t = (np.arange(m) + 0.5) / m; P.append(p0 + np.outer(t, p1 - p0)); D.append(np.repeat(((p1 - p0) / L)[None], m, 0))
    return (np.vstack(P), np.vstack(D)) if P else (np.zeros((0, 2)), np.zeros((0, 2)))


def cov(P, Pd, Q, Qd, r=8.0, ang=20):
    if not len(P) or not len(Q): return np.zeros(len(P), bool)
    d, j = cKDTree(Q).query(P, k=min(16, len(Q)), distance_upper_bound=r)
    if d.ndim == 1: d, j = d[:, None], j[:, None]
    ok = np.isfinite(d); jj = np.where(ok, j, 0); ok &= np.abs((Qd[jj] * Pd[:, None, :]).sum(2)) >= np.cos(np.radians(ang))
    return ok.any(1)


res = {}; tot = dict(A_len=0.0, A_shared=0.0, B_len=0.0, B_shared=0.0)
for n in plates:
    ea = json.load(open(HERE + f'qa/{A}/{n}/{n}_edges.json')); eb = json.load(open(HERE + f'qa/{B}/{n}/{n}_edges.json'))
    (Pa, Da), (Pb, Db) = samp(ea), samp(eb); ca, cb = cov(Pa, Da, Pb, Db), cov(Pb, Db, Pa, Da)
    r = dict(A_len=2.0 * len(Pa), A_shared=2.0 * ca.sum(), B_len=2.0 * len(Pb), B_shared=2.0 * cb.sum())
    for k in tot: tot[k] += r[k]
    res[n] = {k: round(v) for k, v in r.items()}
res['all'] = {k: round(v) for k, v in tot.items()}
t = res['all']; out = dict(A=A, B=B, per_plate=res, note='lengths in full-size px; shared = within 8 px and 20 degrees of the other setting\'s sides')
out['shares'] = dict(A_shared_share=round(t['A_shared'] / max(1, t['A_len']), 3), B_shared_share=round(t['B_shared'] / max(1, t['B_len']), 3))
if eye:
    ra = t['A_shared'] * eye['shared'] + (t['A_len'] - t['A_shared']) * eye['A_only']; rb = t['B_shared'] * eye['shared'] + (t['B_len'] - t['B_shared']) * eye['B_only']
    out['estimate_right_len'] = dict(A=round(ra), B=round(rb), A_precision=round(ra / t['A_len'], 3), B_precision=round(rb / t['B_len'], 3), eye=eye, note='ESTIMATE from by-eye samples of 24 points per part')
os.makedirs(HERE + 'overlap', exist_ok=True); json.dump(out, open(HERE + f'overlap/{A}_vs_{B}.json', 'w'), indent=1); print(json.dumps(out, indent=1))
