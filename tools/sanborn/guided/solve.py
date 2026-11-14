"""Feature-keyed placement of a guided plate (14 November 2026; Ben: strip the process to first principles).

    cd data/sanborn
    python ../../tools/sanborn/guided/solve.py N [--write]

A plate is one smooth warp, plate pixel -> world (affine + thin-plate spline, jointlib 'tps_px'). It is fitted to
every observation the guided reader made, each tied to a feature of today's map by identity, never by name:
- a crossing (picks22_guided/22-N/observations.json "crossings"): the plate point must land on today's crossing
  (two equations, east and north);
- a traced street point ("stations"): it must land on today's centre line of that street (one equation, across the
  street; along the street it is free).
No observation is cut at a threshold. Each gets a weight from how well it fits (Tukey biweight, iterated): a wrong
reading or a street realigned since 1922 fades out and is reported. Ben's decisions keep full weight.
The stiffness of the spline is chosen by the held-out test: a fifth of the crossings at a time is left out, the plate
is fitted without them, and the miss at the left-out crossings is measured. The same test is run for crossings alone,
so the report says what the street points add.
Seams: at today's crossings a neighbouring applied plate also has (its cufp/<M>/matches.json), the neighbour's position
of the crossing is compared with this plate's.
Writes picks22_guided/22-N/solve.json and, with --write, cufp/N/fwd_guided.pkl (jointlib tag 'guided').
"""
import json, os, pickle, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import streets as S  # noqa: E402
from shapely.geometry import Point  # noqa: E402
J = S.J
N = sys.argv[1]; WRITE = '--write' in sys.argv; SP = S.SP; D = SP + f'picks22_guided/22-{N}/'
P = S.Plate(N); BY = {s['sid']: s['geom'] for s in P.streets()}
OBS = json.load(open(D + 'observations.json', encoding='utf8'))
CR = [c for c in OBS['crossings'] if not c.get('same_point_as')]
ST = [s for s in OBS['stations'] if s['sid'] in BY]
SC, ORIGIN = 1000.0, np.array([715000.0, 4335000.0])
C_CROSS, C_LINE, W_LINE, LAMS, FOLDS, ITERS = 12.0, 8.0, 0.5, (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0), 5, 8

# dense observations from the U-net (unet/extract.py -> unet_obs.json): block-edge points against today's block edges
# (today/blocks_N.geojson), street centre points against today's centre lines. Each is matched to the nearest place on
# the reference under the current fit (re-matched every iteration) and pins the plate across that line.
from scipy.spatial import cKDTree  # noqa: E402
from shapely.geometry import shape  # noqa: E402
def sampler(lines):
    pts, nrm = [], []
    for l in lines:
        for t in np.arange(0, l.length, 1.0):
            a, b = l.interpolate(t), l.interpolate(min(l.length, t + 1.0)); d = np.array([b.x - a.x, b.y - a.y]); n = np.hypot(*d)
            if n > 0: pts.append([a.x, a.y]); nrm.append([-d[1] / n, d[0] / n])
    return cKDTree(np.array(pts)), np.array(pts), np.array(nrm)
DENSE = []          # (name, plate points, tree, reference points, normals, base weight, Tukey c in metres)
MAXD = 500
if os.path.exists(D + 'unet_obs.json') and '--no-unet' not in sys.argv:
    U = json.load(open(D + 'unet_obs.json', encoding='utf8')); r_ = np.random.default_rng(1)
    sub = lambda a: np.asarray(a, float)[r_.permutation(len(a))[:MAXD]]
    if os.path.exists(SP + f'today/blocks_{N}.geojson') and U['edges']:
        DENSE.append(('block_edges', sub(U['edges']), *sampler([shape(f['geometry']).exterior for f in json.load(open(SP + f'today/blocks_{N}.geojson', encoding='utf8'))['features']]), 0.3, 5.0))
    if U['centres']:
        DENSE.append(('centre_lines', sub(U['centres']), *sampler([l for g in BY.values() for l in getattr(g, 'geoms', [g])]), 0.3, 8.0))

def phi(d):
    with np.errstate(divide='ignore', invalid='ignore'): return np.where(d > 0, d * d * np.log(d), 0.0)

class Warp:
    """affine + thin-plate spline on given centres; theta per coordinate = [affine (3), spline in the null space of the affine]"""
    def __init__(self, centres):
        self.X = np.asarray(centres, float); self.c = self.X.mean(0); n = len(self.X)
        B = np.c_[np.ones(n), (self.X - self.c) / SC]
        q, _ = np.linalg.qr(B, mode='complete'); self.Z = q[:, 3:]              # B' Z = 0
        K = phi(np.hypot(self.X[:, None, 0] - self.X[None, :, 0], self.X[:, None, 1] - self.X[None, :, 1]) / SC)
        self.R = self.Z.T @ K @ self.Z; self.k = n
    def rows(self, q):
        q = np.asarray(q, float)
        K = phi(np.hypot(q[:, None, 0] - self.X[None, :, 0], q[:, None, 1] - self.X[None, :, 1]) / SC)
        return np.c_[np.ones(len(q)), (q - self.c) / SC, K @ self.Z]
    def world(self, th, q): return self.rows(q) @ th + ORIGIN
    def model(self, th, lam):
        aff = th[:3].copy(); aff[0] += ORIGIN
        return dict(kind='tps_px', scale_px=SC, center_px=self.c.tolist(), centers_px=self.X.tolist(), affine=aff.tolist(), w=(self.Z @ th[3:]).tolist(), lam=lam,
                    formula='world = affine . [1, (x - center) / scale] + sum_j w_j phi(|x - c_j| / scale), phi(r) = r2 log r')

def tukey(r, c): return np.where(r < c, (1 - (r / c) ** 2) ** 2, 0.0)

def project(sid, W):
    """foot of each world point on today's street, the unit normal there, and whether the foot is inside the street's length"""
    g = BY[sid]; F, Nm, ok = [], [], []
    for w in W:
        t = g.project(Point(*w)); a, b = g.interpolate(max(0, t - 1)), g.interpolate(min(g.length, t + 1)); f = g.interpolate(t)
        d = np.array([b.x - a.x, b.y - a.y]); d /= (np.hypot(*d) or 1)
        F.append([f.x, f.y]); Nm.append([-d[1], d[0]]); ok.append(1.0 < t < g.length - 1.0)
    return np.array(F), np.array(Nm), np.array(ok)

def fit(cr, st, lam, lines=True, dense=False):
    """IRLS fit. Returns warp, theta (k x 2), crossing weights and misses, station weights and across-street misses."""
    Xc = np.array([[c['x'], c['y']] for c in cr]); Oc = np.array([[c['E'], c['N']] for c in cr]) - ORIGIN
    ben = np.array([bool(c.get('ben')) for c in cr]); Xs = np.array([[s['x'], s['y']] for s in st]).reshape(-1, 2)
    Wp = Warp(np.r_[Xc, Xs] if lines and len(Xs) else Xc); Rc = Wp.rows(Xc); Rs = Wp.rows(Xs) if lines and len(Xs) else np.zeros((0, Wp.k))
    Rd = [Wp.rows(g[1]) for g in DENSE] if dense else []; wd = [np.zeros(len(r)) for r in Rd]; pd = [np.zeros(len(r)) for r in Rd]
    k = Wp.k; wc = np.where([c['low'] for c in cr], 0.5, 1.0); ws = np.zeros(len(Rs)); th = None
    Pen = np.zeros((2 * k, 2 * k)); Pen[3:k, 3:k] = Wp.R; Pen[k + 3:, k + 3:] = Wp.R
    sids = sorted({s['sid'] for s in st})
    for it in range(ITERS):
        A = np.zeros((2 * len(Rc), 2 * k)); A[:len(Rc), :k] = Rc; A[len(Rc):, k:] = Rc
        y = np.r_[Oc[:, 0], Oc[:, 1]]; w = np.r_[wc, wc]
        if th is not None and len(Rs):
            Ws = Rs @ th + ORIGIN; F = np.zeros_like(Ws); Nm = np.zeros_like(Ws); ok = np.zeros(len(Ws), bool)
            for sid in sids:
                m = np.array([s['sid'] == sid for s in st]); F[m], Nm[m], ok[m] = project(sid, Ws[m])
            perp = np.abs(((Ws - F) * Nm).sum(1)); c = C_LINE * (2 if it < 3 else 1)
            ws = W_LINE * tukey(perp, c) * ok
            A = np.r_[A, np.c_[Rs * Nm[:, :1], Rs * Nm[:, 1:]]]; y = np.r_[y, ((F - ORIGIN) * Nm).sum(1)]; w = np.r_[w, ws]
        if th is not None:
            for j, (g, R) in enumerate(zip(DENSE, Rd)):
                Wq = R @ th + ORIGIN; dist, i = g[2].query(Wq); F, Nm = g[3][i], g[4][i]
                pd[j] = np.abs(((Wq - F) * Nm).sum(1)); c = g[6] * (2 if it < 3 else 1)
                wd[j] = g[5] * tukey(pd[j], c) * (dist < 3 * g[6])
                A = np.r_[A, np.c_[R * Nm[:, :1], R * Nm[:, 1:]]]; y = np.r_[y, ((F - ORIGIN) * Nm).sum(1)]; w = np.r_[w, wd[j]]
        sw = np.sqrt(w)[:, None]
        sol = np.linalg.solve((A * sw).T @ (A * sw) + lam * Pen + 1e-9 * np.eye(2 * k), (A * sw).T @ (y * sw[:, 0]))
        th = np.c_[sol[:k], sol[k:]]
        miss = np.hypot(*(Rc @ th - Oc).T); c = C_CROSS * (2 if it < 3 else 1)
        wc = np.where(ben, 1.0, tukey(miss, c) * np.where([c_['low'] for c_ in cr], 0.5, 1.0))
    perp = np.zeros(0)
    if len(Rs):
        Ws = Rs @ th + ORIGIN; perp = np.zeros(len(Ws))
        for sid in sids:
            m = np.array([s['sid'] == sid for s in st]); F, Nm, ok = project(sid, Ws[m]); perp[m] = np.abs(((Ws[m] - F) * Nm).sum(1))
    fit.dense = [(g[0], wd[j], pd[j]) for j, g in enumerate(DENSE)] if dense else []
    return Wp, th, wc, miss, ws, perp

rms = lambda e: float(np.sqrt(np.mean(np.square(e)))) if len(e) else float('nan')
# evaluation set: crossings a crossings-only fit trusts (independent of the street points), in FOLDS random folds
_, _, w0, m0, _, _ = fit(CR, [], 0.3, lines=False)
EV = np.where(w0 >= 0.8)[0]; rng = np.random.default_rng(0); fold = rng.permutation(len(EV)) % FOLDS
def cv(lam, lines, dense=False):
    e = np.zeros(len(EV))
    for f in range(FOLDS):
        out = set(EV[fold == f].tolist()); tr = [c for i, c in enumerate(CR) if i not in out]
        Wp, th, *_ = fit(tr, ST, lam, lines, dense)
        for j in np.where(fold == f)[0]:
            c = CR[EV[j]]; e[j] = np.hypot(*(Wp.world(th, [[c['x'], c['y']]])[0] - [c['E'], c['N']]))
    return e
rep = dict(plate=N, crossings=len(CR), stations=len(ST), eval_crossings=int(len(EV)), folds=FOLDS, heldout={})
best = {}
VAR = [('crossings_only', False, False), ('with_street_points', True, False)] + ([('with_unet', True, True)] if DENSE else [])
for name, lines, dense in VAR:
    tab = {lam: cv(lam, lines, dense) for lam in LAMS}; lam = min(tab, key=lambda l: rms(tab[l])); best[name] = lam
    rep['heldout'][name] = dict(lam=lam, rms=round(rms(tab[lam]), 2), median=round(float(np.median(tab[lam])), 2), p90=round(float(np.percentile(tab[lam], 90)), 2),
        max=round(float(tab[lam].max()), 2), by_lam={str(l): round(rms(e), 2) for l, e in tab.items()})
    print('held-out', name, rep['heldout'][name], flush=True)
name, use_lines, use_dense = min(VAR, key=lambda v: rep['heldout'][v[0]]['rms'])
rep['chosen'] = name
Wp, th, wc, miss, ws, perp = fit(CR, ST, best[name], use_lines, use_dense)
rep['unet'] = [dict(kind=n_, points=int(len(w_)), used=int((w_ > 0.06).sum()), median_across_m=round(float(np.median(p_[w_ > 0.06])), 2) if (w_ > 0.06).any() else None) for n_, w_, p_ in fit.dense]
rep['crossing_weights'] = dict(full=int((wc >= 0.8).sum()), partial=int(((wc > 0.05) & (wc < 0.8)).sum()), out=int((wc <= 0.05).sum()))
rep['faded_crossings'] = sorted([dict(id=c['id'], a=c['a'], b=c['b'], miss_m=round(float(m), 1), weight=round(float(w), 2)) for c, m, w in zip(CR, miss, wc) if w < 0.5], key=lambda r: -r['miss_m'])
moved = []
if len(perp):
    for sid in sorted({s['sid'] for s in ST}):
        m = np.array([s['sid'] == sid for s in ST])
        if m.sum() >= 3 and (ws[m] < 0.2 * W_LINE).mean() > 0.6: moved.append(dict(sid=sid, stations=int(m.sum()), median_off_m=round(float(np.median(perp[m])), 1)))
    rep['street_points'] = dict(used=int((ws > 0.2 * W_LINE).sum()), faded=int((ws <= 0.2 * W_LINE).sum()), median_across_m=round(float(np.median(perp[ws > 0.2 * W_LINE])), 2) if (ws > 0.2 * W_LINE).any() else None)
rep['moved_streets'] = moved
# seams with applied neighbours, at today's crossings both plates have
def others():
    for d in sorted(os.listdir(SP + 'cufp')):
        f = SP + f'cufp/{d}/matches.json'
        if d != N and os.path.isfile(f) and J.has(f'22-{d}', 'complete'): yield d, json.load(open(f, encoding='utf8'))
models = {'new_solver': lambda q: Wp.world(th, q)}
bk = D + 'applied_backup/cufp82A/fwd_complete.pkl' if N == '82A' else None
if J.has(f'22-{N}', 'complete'): models['current_cufp_model'] = lambda q: J.world_many(f'22-{N}', q, 'complete')
if bk and os.path.exists(bk):
    jb = pickle.load(open(bk, 'rb')); models['applied_before_test'] = lambda q: J.tps_px_many(jb, q)
seams = {}
for d, M in others():
    rows = []
    for m in M:
        if not m.get('osm') or not m.get('used'): continue
        c = next((c for c in CR if np.hypot(c['E'] - m['osm'][0], c['N'] - m['osm'][1]) < 5.0), None)
        if c is None: continue
        nb = J.world_many(f'22-{d}', np.array([[m['x'], m['y']]]), 'complete')[0]
        rows.append({k: float(np.hypot(*(f(np.array([[c['x'], c['y']]]))[0] - nb))) for k, f in models.items()})
    if rows: seams[d] = dict(n=len(rows), **{k: dict(median=round(float(np.median([r[k] for r in rows])), 2), max=round(max(r[k] for r in rows), 2)) for k in models})
rep['seams'] = seams
json.dump(rep, open(D + 'solve.json', 'w', encoding='utf8', newline='\n'), indent=1)
if WRITE:
    pickle.dump(dict(Wp.model(th, best[name]), source='tools/sanborn/guided/solve.py'), open(SP + J.joint_path(f'22-{N}', 'guided'), 'wb'))
print(json.dumps({k: v for k, v in rep.items() if k != 'heldout'}, indent=1))
