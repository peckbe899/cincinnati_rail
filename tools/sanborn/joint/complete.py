"""Every 1922 plate fitted by thin-plate spline on its complete control set, all 21 solved together (Ben, 6 November 2026;
docs/sanborn/RULES.md rule 12).

    cd data/sanborn
    python ../../tools/sanborn/joint/complete.py [--write]      (without --write: report only, no model files)

Controls, per plate: its hand picks as its current model uses them (fwd.pkl X -> O, 22-35N cuf/corr.pkl; the round-3
re-read corrections for 33, 34R, 37L, 37R and 38 as tools/sanborn/joint/local2.py applies them) plus the crossings read
for the complete set (data/sanborn/picks22_complete/<plate>/picks.json, each read for a known OSM crossing). Rule 4's
tests run on the union: a control more than 25 m off an affine fit, then more than 6 m off the tps1 spline, is dropped
one at a time (cufp/fit.py).

Model, per plate: world = A [1, u, v] + sum_j w_j phi(|x - c_j| / S), u, v = (x - c) / S, S = 1000 px, phi = r2 log r,
centres c_j the plate's control pixels, w in the null space of the affine terms (so the spline adds no affine part).
Nothing of the plate's current model is kept: the spline is fitted on the controls alone. Smoothing: a penalty
lam * bending energy (w' K w), lam per plate.

Joint solve: one weighted least-squares system over all 21 plates, E and N together (same design):
- controls, weight 1;
- ties: the crossings two plates share (tools/sanborn/seams.py matching over the hand picks and the complete picks,
  within 45 m under the current models; the re-read's wrong matches dropped), new_a(x_a) = new_b(x_b), Huber weights
  (k = 6 m, iterated); the 37L/37R shared crossings at weight 3, no Huber;
- the 37L/37R gutter pairs (cuf_cw/overlap_37L_37R.json: the same paper point on both halves) at weight 3, no Huber;
- the penalty rows sqrt(lam) * (eigen square root of the bending energy).
A control listed twice in a plate's own model (same pixel, same OSM point: 38, 69, 29) counts once.
Held-out error: exact leave-one-out over the plate's controls (each control's row taken out of the solved system, the
ties and penalty kept: r / (1 - h)). Smoothing chosen per plate by held-out error over LAMS, coordinate descent from
lam = 1 for all, two passes. The held-out error before is the current model's on the same control set: leave-one-out
for the controls it was fitted to (the plate's own model refitted without each), plain error for the new ones (it never
saw them); 22-35N's current model (Ben's georeference) was fitted to nothing, so plain error throughout.

Guard (Part 3 only if it holds): every plate's held-out error no worse than before; the seam median and 90% over all
plate-plate seams fall (seam report before and after both over the hand picks plus the complete picks); no plate corner
moves more than 10 m unless a control lies within 500 px of it.

Writes data/sanborn/reports/<date>_complete/ (README.md, plates.csv, controls.csv, ties.csv, solve.json) and, with
--write, each plate's model beside its old one (jointlib joint_path(pid, 'complete'), kind 'tps_px') and the two seam
reports. Nothing else.
"""
import csv, datetime, glob, json, os, pickle, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402
import local as LC  # noqa: E402
import local2 as L2  # noqa: E402

J, S, SV = LC.J, LC.S, LC.SV
SP = _ws.DATA
TAG = 'complete'
SC = 1000.0
LAMS = [1e-4, 1e-3, 3e-3, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 100.0]
LAM0 = 1.0
HUBER, W_GUT = 6.0, 3.0
CORNER_M, CORNER_PX = 10.0, 500.0
COMPLETE = 'picks22_complete'
ORIGIN = np.array([715000.0, 4335000.0])   # subtracted from the world targets inside the solve (conditioning)


# ------------------------------------------------------------------ data
def complete_picks(pid):
    f = SP + f'{COMPLETE}/{pid}/picks.json'
    return json.load(open(f, encoding='utf8'))['intersections'] if os.path.exists(f) else []


def tps1_drop(X, O):
    """rule 4 (cufp/fit.py): drop, one at a time, a control more than 25 m off an affine fit, then more than 6 m off
    the tps1 spline (affine + RBF thin-plate, smoothing 1, on pixels / 1000)"""
    from scipy.interpolate import RBFInterpolator
    keep = np.ones(len(X), bool); dropped = []

    def aff(Xs, Os):
        A = np.c_[np.ones(len(Xs)), Xs / 10000]; c, *_ = np.linalg.lstsq(A, Os, rcond=None)
        return lambda q: np.c_[np.ones(len(q)), q / 10000] @ c

    def tps1(Xs, Os):
        b = aff(Xs, Os); rb = RBFInterpolator(Xs / 1000, Os - b(Xs), kernel='thin_plate_spline', smoothing=1, degree=1)
        return lambda q: b(q) + rb(q / 1000)
    for fit, lim, tag in ((aff, 25.0, 'affine'), (tps1, 6.0, 'tps1')):
        for _ in range(80):
            if keep.sum() < 6:
                break
            f = fit(X[keep], O[keep]); r = np.hypot(*(f(X) - O).T); w = int(np.argmax(np.where(keep, r, -1)))
            if r[w] > lim:
                keep[w] = False; dropped.append((w, tag, round(float(r[w]), 2)))
            else:
                break
    return keep, dropped


def setup():
    latest, ctl, drop = L2.reread_state()
    C5, basefn5, info5 = L2.setup(latest, ctl)
    C = {}
    for p in S.plate_ids():
        if p in C5:
            c = C5[p]; X, O, Pl = c['X'], c['O'], c['Pl']; model = c['model']
            cur = basefn5[p]
        else:
            X, O, P, Pl, names, model = SV.controls(p)
            cur = (lambda pid: lambda q: J.base_many(pid, np.asarray(q, float)))(p)
        new = complete_picks(p)
        Xn = np.array([[q['x'], q['y']] for q in new], float).reshape(-1, 2)
        On = np.array([q['osm'] for q in new], float).reshape(-1, 2)
        Xa = np.vstack([X, Xn]); Oa = np.vstack([O, On])
        src = ['hand'] * len(X) + ['complete'] * len(Xn)
        names = [''] * len(X) + [f"{q['a']} & {q['b']}" for q in new]
        before = np.vstack([Pl if p != '22-35N' else J.base_many(p, X), J.base_many(p, Xn) if len(Xn) else np.zeros((0, 2))])
        uniq = np.ones(len(Xa), bool)            # a control listed twice (same pixel within 1 px, same OSM point within 1 m)
        for i in range(len(Xa)):
            if uniq[i]:
                same = (np.hypot(*(Xa - Xa[i]).T) < 1.0) & (np.hypot(*(Oa - Oa[i]).T) < 1.0); same[:i + 1] = False
                uniq[same] = False
        n_dup = int((~uniq).sum())
        Xa, Oa, before = Xa[uniq], Oa[uniq], before[uniq]
        src = [s_ for s_, u in zip(src, uniq) if u]; names = [n_ for n_, u in zip(names, uniq) if u]
        keep, dropped = tps1_drop(Xa, Oa)
        C[p] = dict(X=Xa[keep], O=Oa[keep], src=[s for s, k in zip(src, keep) if k], names=[n for n, k in zip(names, keep) if k],
                    before=before[keep], model=model, cur=cur,
                    dropped=[dict(src=src[i], x=round(float(Xa[i, 0]), 1), y=round(float(Xa[i, 1]), 1), names=names[i], test=t, off_m=r) for i, t, r in dropped],
                    n_hand=len(X), n_new=len(Xn), n_dup=n_dup)
    return C, latest, drop


def patched_crossings(latest):
    """plate crossings for the ties and the seam report: the hand picks (re-read corrections applied) plus the
    complete picks"""
    pc0 = L2.patched_crossings(latest)

    def pc(pid):
        recs, nf = pc0(pid)
        w = S.plate_world(pid)
        for q in complete_picks(pid):
            E, N = w(q['x'], q['y'])
            recs.append(dict(src=pid, kind='plate', k=S.k2(q['a'], q['b']), a=q['a'], b=q['b'], x=q['x'], y=q['y'], E=E, N=N,
                             readers=2, complete=True))
        return recs, nf
    return pc


# ------------------------------------------------------------------ model
def kern(P, Cc):
    d = np.hypot(P[:, None, 0] - Cc[None, :, 0], P[:, None, 1] - Cc[None, :, 1]) / SC
    with np.errstate(divide='ignore', invalid='ignore'):
        return np.where(d > 0, d * d * np.log(d), 0.0)


class Plate:
    def __init__(self, X):
        X = np.asarray(X, float); self.c = X.mean(0)
        _, iu = np.unique(np.round(X * 2) / 2, axis=0, return_index=True)     # centres: each control pixel once
        self.X = X[np.sort(iu)]
        P = self.basis(self.X)
        U, s, Vt = np.linalg.svd(P, full_matrices=True)
        self.N = U[:, 3:]                                  # null space of P': w = N z
        K = kern(self.X, self.X)
        e, V = np.linalg.eigh(self.N.T @ K @ self.N)
        self.R = (V * np.sqrt(np.clip(e, 0, None))).T      # R' R = N' K N
        self.k = 3 + self.N.shape[1]

    def basis(self, Q):
        Q = np.asarray(Q, float)
        return np.c_[np.ones(len(Q)), (Q - self.c) / SC]

    def design(self, Q):
        """rows mapping the plate's parameters (affine 3, then z) to world at pixels Q"""
        Q = np.asarray(Q, float)
        return np.c_[self.basis(Q), kern(Q, self.X) @ self.N]


class System:
    def __init__(self, plates, C, ties, gut):
        self.plates, self.C, self.ties, self.gut = plates, C, ties, gut
        self.M = {p: Plate(C[p]['X']) for p in plates}
        self.off = {}; o = 0
        for p in plates:
            self.off[p] = o; o += self.M[p].k
        self.n = o
        rows = []        # (A row block list, target (2,), kind, ident)
        A, Y, kind = [], [], []
        for p in plates:
            D = self.M[p].design(C[p]['X'])
            for i in range(len(D)):
                r = np.zeros(self.n); r[self.off[p]:self.off[p] + D.shape[1]] = D[i]
                A.append(r); Y.append(C[p]['O'][i] - ORIGIN); kind.append(('c', p, i))
        for t, T in enumerate(ties):
            ra = self.M[T['a']].design(np.array([T['xa']]))[0]; rb = self.M[T['b']].design(np.array([T['xb']]))[0]
            r = np.zeros(self.n); r[self.off[T['a']]:self.off[T['a']] + len(ra)] = ra; r[self.off[T['b']]:self.off[T['b']] + len(rb)] -= rb
            A.append(r); Y.append(np.zeros(2)); kind.append(('t', t, T['sheet']))
        pl, pr = gut
        for g in range(len(pl)):
            ra = self.M['22-37L'].design(pl[g:g + 1])[0]; rb = self.M['22-37R'].design(pr[g:g + 1])[0]
            r = np.zeros(self.n); r[self.off['22-37L']:self.off['22-37L'] + len(ra)] = ra; r[self.off['22-37R']:self.off['22-37R'] + len(rb)] -= rb
            A.append(r); Y.append(np.zeros(2)); kind.append(('g', g, True))
        self.A = np.array(A); self.Y = np.array(Y); self.kind = kind
        self.cidx = {p: [i for i, k in enumerate(kind) if k[0] == 'c' and k[1] == p] for p in plates}
        self.tidx = [i for i, k in enumerate(kind) if k[0] == 't']
        self.Pen = {}
        for p in plates:
            m = self.M[p]; Rm = np.zeros((m.R.shape[0], self.n)); Rm[:, self.off[p] + 3:self.off[p] + m.k] = m.R
            self.Pen[p] = Rm.T @ Rm
        self.AtA_parts = None

    def weights(self, tw):
        W = np.ones(len(self.kind))
        for j, i in enumerate(self.tidx):
            W[i] = W_GUT if self.kind[i][2] else tw[j]
        for i, k in enumerate(self.kind):
            if k[0] == 'g':
                W[i] = W_GUT
        return W

    def solve(self, lams, tw=None, iterate=True):
        """normal equations, scaled to unit diagonal and solved by Cholesky (an explicit inverse loses the fit)"""
        import scipy.linalg as sl
        tw = np.ones(len(self.tidx)) if tw is None else tw.copy()
        for it in range(10 if iterate else 1):
            W = self.weights(tw)
            Nm = (self.A * W[:, None]).T @ self.A
            for p in self.plates:
                Nm += lams[p] * self.Pen[p]
            dg = np.sqrt(np.diag(Nm)); Ns = Nm / dg[:, None] / dg[None, :] + 1e-12 * np.eye(self.n)
            cf = sl.cho_factor(Ns)
            th = sl.cho_solve(cf, ((self.A * W[:, None]).T @ self.Y) / dg[:, None]) / dg[:, None]
            R = self.Y - self.A @ th
            if not iterate:
                break
            rt = np.hypot(*R[self.tidx].T) if self.tidx else np.zeros(0)
            new = np.where(rt <= HUBER, 1.0, HUBER / np.maximum(rt, 1e-9))
            if np.allclose(new, tw, atol=1e-4):
                break
            tw = new
        return dict(th=th, R=R, cf=cf, dg=dg, W=W, tw=tw, lams=dict(lams))

    def heldout(self, sol, p):
        import scipy.linalg as sl
        idx = self.cidx[p]
        a = self.A[idx] / sol['dg'][None, :]
        h = np.einsum('ij,ji->i', a, sl.cho_solve(sol['cf'], a.T)) * sol['W'][idx]
        e = sol['R'][idx] / (1 - h)[:, None]
        return np.hypot(*e.T)

    def world(self, sol, p, Q):
        D = self.M[p].design(Q)
        return D @ sol['th'][self.off[p]:self.off[p] + self.M[p].k] + ORIGIN

    def model_dict(self, sol, p):
        m = self.M[p]; th = sol['th'][self.off[p]:self.off[p] + m.k]
        w = m.N @ th[3:]; aff = th[:3].copy(); aff[0] += ORIGIN
        return dict(kind='tps_px', scale_px=SC, center_px=m.c.tolist(), centers_px=m.X.tolist(), affine=aff.tolist(),
                    w=w.tolist(), lam=sol['lams'][p],
                    formula='world = affine . [1, (x - center) / scale] + sum_j w_j phi(|x - c_j| / scale), phi(r) = r2 log r')


def rms(e):
    e = np.asarray(e, float)
    return float(np.sqrt(np.mean(e ** 2))) if len(e) else float('nan')


def choose(F, passes=2, log=print):
    lams = {p: LAM0 for p in F.plates}
    sol = F.solve(lams); tw = sol['tw']
    trail = []
    for ps in range(passes):
        changed = False
        for p in F.plates:
            best = None
            for lam in LAMS:
                L_ = dict(lams); L_[p] = lam
                s = F.solve(L_, tw, iterate=False)
                h = rms(F.heldout(s, p))
                if best is None or h < best[0] - 1e-6:
                    best = (h, lam)
            if best[1] != lams[p]:
                changed = True
            lams[p] = best[1]; trail.append((ps, p, best[1], round(best[0], 3)))
            log(f'pass {ps + 1} {p}: lam {best[1]} held-out {best[0]:.2f}')
        sol = F.solve(lams, tw); tw = sol['tw']
        if not changed:
            break
    return lams, F.solve(lams, tw), trail


# ------------------------------------------------------------------ main
def main():
    write = '--write' in sys.argv
    today = datetime.date.today().isoformat()
    out = SP + f'reports/{today}_complete'; os.makedirs(out, exist_ok=True)
    log = lambda s: print(s, flush=True)
    plates = S.plate_ids()
    C, latest, drop = setup()
    for p in plates:
        log(f"{p}: hand {C[p]['n_hand']} new {C[p]['n_new']} listed twice {C[p]['n_dup']} kept {len(C[p]['X'])} dropped {len(C[p]['dropped'])}")
    pc = patched_crossings(latest)
    S.plate_crossings = pc; S.pairs = L2.patched_pairs(drop)
    recs = []
    for p in plates:
        recs += S.plate_crossings(p)[0]
    near, _ = S.pairs(recs)
    ties = []
    for i, j, d in near:
        a, b = recs[i], recs[j]
        if b['kind'] != 'plate':
            continue
        sheet = {a['src'], b['src']} == {'22-37L', '22-37R'}
        ties.append(dict(a=a['src'], b=b['src'], xa=[a['x'], a['y']], xb=[b['x'], b['y']], street_1=a['a'], street_2=a['b'],
                         before_m=round(float(d), 2), sheet=sheet, complete=bool(a.get('complete') or b.get('complete'))))
    ov = LC.overlap_pairs()
    pr = np.array([q[:2] for q in ov['pairs']], float); pl = np.array([q[2:] for q in ov['pairs']], float)
    gap0 = np.hypot(*(C['22-37L']['cur'](pl) - C['22-37R']['cur'](pr)).T)
    F = System(plates, C, ties, (pl, pr))
    log(f'unknowns {F.n}, rows {len(F.kind)}, ties {len(ties)}, gutter pairs {len(pl)}')
    lams, sol, trail = choose(F, log=log)
    rows, ctl_rows, guard_fail = [], [], []
    for p in plates:
        c = C[p]; new = F.world(sol, p, c['X']); own = np.hypot(*(new - c['O']).T)
        ho = F.heldout(sol, p); hb = np.hypot(*(c['before'] - c['O']).T)
        w, h = SV.plate_size(p); corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
        mv = np.hypot(*(F.world(sol, p, corners) - c['cur'](corners)).T)
        dmin = np.array([np.hypot(*(c['X'] - q).T).min() for q in corners])
        bad_corner = [int(k) for k in range(4) if mv[k] > CORNER_M and dmin[k] > CORNER_PX]
        r = dict(plate=p, controls=len(c['X']), hand=sum(s == 'hand' for s in c['src']), new=sum(s == 'complete' for s in c['src']),
                 dropped=len(c['dropped']), lam=lams[p], own_rms=round(rms(own), 2), heldout_before=round(rms(hb), 2),
                 heldout_after=round(rms(ho), 2), heldout_change=round(rms(ho) - rms(hb), 2),
                 max_corner_move_m=round(float(mv.max()), 2), corner_moves_m=[round(float(v), 1) for v in mv],
                 corner_nearest_control_px=[round(float(v)) for v in dmin], corners_failing=bad_corner,
                 ties=sum(1 for t in ties if p in (t['a'], t['b'])))
        rows.append(r)
        if rms(ho) > rms(hb) + 1e-9:
            guard_fail.append((p, f"held-out {rms(ho):.2f} m against {rms(hb):.2f} m before"))
        if bad_corner:
            guard_fail.append((p, f"corner(s) {bad_corner} move {', '.join(f'{mv[k]:.1f}' for k in bad_corner)} m with no control within {CORNER_PX:.0f} px"))
        for i in range(len(c['X'])):
            ctl_rows.append(dict(plate=p, src=c['src'][i], names=c['names'][i], x=round(float(c['X'][i, 0]), 1), y=round(float(c['X'][i, 1]), 1),
                                 E=round(float(c['O'][i, 0]), 2), N=round(float(c['O'][i, 1]), 2), before_m=round(float(hb[i]), 2),
                                 own_m=round(float(own[i]), 2), heldout_m=round(float(ho[i]), 2)))
    tinfo = []
    for k, t in enumerate(ties):
        na = F.world(sol, t['a'], np.array([t['xa']]))[0]; nb = F.world(sol, t['b'], np.array([t['xb']]))[0]
        tinfo.append(dict(a=t['a'], b=t['b'], street_1=t['street_1'], street_2=t['street_2'], before_m=t['before_m'],
                          after_m=round(float(np.hypot(*(nb - na))), 2), weight=round(float(W_GUT if t['sheet'] else sol['tw'][k]), 3),
                          sheet=t['sheet'], complete=t['complete']))
    gap1 = np.hypot(*(F.world(sol, '22-37L', pl) - F.world(sol, '22-37R', pr)).T)
    summary = dict(lams=lams, ties=len(ties), gutter_pairs=len(pl), gutter_weight=W_GUT,
                   gutter_gap_before=dict(median=round(float(np.median(gap0)), 2), p90=round(float(np.percentile(gap0, 90)), 2), max=round(float(gap0.max()), 2)),
                   gutter_gap_after=dict(median=round(float(np.median(gap1)), 2), p90=round(float(np.percentile(gap1, 90)), 2), max=round(float(gap1.max()), 2)),
                   guard_fail=guard_fail, controls=sum(len(C[p]['X']) for p in plates),
                   dropped={p: C[p]['dropped'] for p in plates if C[p]['dropped']})
    import scipy
    meta = dict(made=datetime.datetime.now().isoformat(timespec='seconds'), by='tools/sanborn/joint/complete.py', lams_tried=LAMS, huber_m=HUBER,
                corner_m=CORNER_M, corner_px=CORNER_PX, scale_px=SC, choice_trail=trail, versions=dict(numpy=np.__version__, scipy=scipy.__version__),
                picks=COMPLETE, overlap=LC.OVERLAP)
    if write:
        for p in plates:
            jp = J.joint_path(p, TAG); assert jp != J.base_path(p)
            d = F.model_dict(sol, p)
            d.update(controls_X=C[p]['X'].tolist(), controls_O=C[p]['O'].tolist(), base=J.base_path(p),
                     solve=os.path.relpath(out, SP).replace('\\', '/'), made=meta['made'])
            pickle.dump(d, open(SP + jp, 'wb'))
        J._J.clear()
        chk = max(float(np.abs(J.world_many(p, C[p]['X'], TAG) - F.world(sol, p, C[p]['X'])).max()) for p in plates)
        assert chk < 1e-6, chk
        sd = {}
        for tag, models in (('before', None), ('after', TAG)):
            S.READ.clear(); S.MODELS = None; S.JOINT = False
            d_ = SP + f'reports/{today}_seams_complete' + ('_before' if tag == 'before' else '')
            S.main((['--models', models] if models else []) + [d_]); S.MODELS = None
            sd[tag] = LC.seam_stats(json.load(open(d_ + '/seams.json', encoding='utf8'))['seams'], plates)['all']
            sd[tag + '_dir'] = os.path.relpath(d_, SP).replace('\\', '/')
        summary['seams'] = sd
        if not sd['after']['median'] < sd['before']['median']:
            guard_fail.append(('all', f"seam median {sd['after']['median']} m, not below {sd['before']['median']} m"))
        if not sd['after']['p90'] < sd['before']['p90']:
            guard_fail.append(('all', f"seam 90% {sd['after']['p90']} m, not below {sd['before']['p90']} m"))
        summary['guard_fail'] = guard_fail; summary['apply'] = not guard_fail
    json.dump(dict(meta=meta, summary=summary, plates=rows, ties=tinfo), open(out + '/solve.json', 'w', encoding='utf8', newline='\n'), indent=1, default=str)
    for name, data in (('plates.csv', rows), ('ties.csv', tinfo), ('controls.csv', ctl_rows)):
        with open(out + '/' + name, 'w', newline='', encoding='utf8') as f:
            wr = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n'); wr.writeheader(); wr.writerows(data)
    if write:
        write_readme(out, meta, summary, rows, tinfo)
    print(json.dumps({k: v for k, v in summary.items() if k != 'dropped'}, indent=1, default=str))
    for r in rows:
        print({k: v for k, v in r.items() if k not in ('corner_moves_m', 'corner_nearest_control_px')})


def write_readme(out, meta, summary, rows, tinfo):
    g0, g1 = summary['gutter_gap_before'], summary['gutter_gap_after']
    sd = summary.get('seams', {})
    L = [f"# Complete-control fit of the 1922 plates, {meta['made'][:10]}", '',
         'Every plate a thin-plate spline on its complete control set (hand picks plus the crossings read for the complete '
         'set), all 21 solved together; method in `tools/sanborn/joint/complete.py`. Models beside the old ones '
         '(`fwd_complete.pkl`); ' + ('**guard passed**' if summary.get('apply') else '**guard failed: not applied**') + '.', '',
         '| Plate | Controls | Hand | New | Dropped (rule 4) | Smoothing | Own rms m | Held-out before m | Held-out after m | Change | Max corner move m | Ties |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append(f"| {r['plate']} | {r['controls']} | {r['hand']} | {r['new']} | {r['dropped']} | {r['lam']} | {r['own_rms']} | {r['heldout_before']} | "
                 f"{r['heldout_after']} | {r['heldout_change']:+.2f} | {r['max_corner_move_m']} | {r['ties']} |")
    L += ['', f"Gutter gap (37L/37R, {summary['gutter_pairs']} pairs at weight {summary['gutter_weight']}): median {g0['median']} -> {g1['median']} m, "
          f"90% {g0['p90']} -> {g1['p90']} m, max {g0['max']} -> {g1['max']} m.", '']
    if sd:
        b, a = sd['before'], sd['after']
        L += [f"Seams, all plate-plate pairs (hand picks plus complete picks; `{sd['before_dir']}` -> `{sd['after_dir']}`): "
              f"n {b['n']} -> {a['n']}, median {b['median']} -> {a['median']} m, 90% {b['p90']} -> {a['p90']} m, max {b['max']} -> {a['max']} m, "
              f"over 10 m {b['over_10m']} -> {a['over_10m']}, over 20 m {b['over_20m']} -> {a['over_20m']}.", '']
    L += ['## Guard', '']
    if summary['guard_fail']:
        L += [f'- {p}: {why}' for p, why in summary['guard_fail']]
    else:
        L += ['Every check holds.']
    L += ['', f"Ties: {summary['ties']} ({sum(t['complete'] for t in tinfo)} involve a complete pick); `ties.csv` before and after each.", '']
    open(out + '/README.md', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
