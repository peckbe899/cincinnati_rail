"""The complete-control fit again (Ben, 6 November 2026: one more pass, then apply), tools/sanborn/joint/complete.py with
three changes.

    cd data/sanborn
    python ../../tools/sanborn/joint/complete2.py [--write]

(a) Damping outside the controls. A plate's spline is world = A [1, u, v] + w(x) * sum_j w_j phi(|x - c_j| / S): the
    thin-plate part is multiplied by w(x) = 1 inside the convex hull of the plate's control pixels, falling to 0 over
    DAMP_PX outside it (a cosine taper on the distance to the hull, smooth at both ends). Beyond that a plate is its
    affine part only, so a corner cannot swing where no control checks it.
(b) 37L and 37R: the page-curl pre-correction (tools/sanborn/joint/curl.py: a monotone spline across the gutter, the
    fold lines and sides of data/sanborn/joint/curl_sides.json) under their splines: world = spline(x + c(x)). The curl
    is fitted by alternation with the linear solve: the spline solved with the curl held, then each half's curl (6
    spline coefficients, all of one sign, and the along-gutter factor k, |k| <= 0.9) by bounded Gauss-Newton on every
    row that touches the two halves (their controls, the gutter pairs at weight 3, their ties) with the spline held;
    both signs tried per half, the lower misfit kept; CURL_ROUNDS rounds. The two halves are one sheet for the
    smoothing and the guard: each half's smoothing is chosen by the held-out error over every control of both, and the
    sheet's held-out error is compared with the current models' over the same controls.
(c) Everything else as complete.py: the complete control set (hand picks plus picks22_complete, rule 4's tests on the
    union), all 21 solved together, the shared crossings as Huber-weighted ties, the gutter pairs at weight 3,
    smoothing per plate by exact leave-one-out (the curl held).

Guard: every plate's held-out error (37L + 37R as one sheet) no worse than its current model's on the same controls;
the seam median and 90% over all plate-plate seams fall; no image corner of any plate moves more than 10 m.

Writes data/sanborn/reports/<date>_complete2/ and, with --write, the models (jointlib joint_path(pid, 'complete2'),
kind 'tps_px' with 'damp' and, for 37L/37R, 'curl') and the seam reports before and after.
"""
import csv, datetime, json, os, pickle, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402
import complete as CP  # noqa: E402
import curl as CU  # noqa: E402

J, S, SV, LC, L2 = CP.J, CP.S, CP.SV, CP.LC, CP.L2
SP = _ws.DATA
TAG = 'complete2'
SC, ORIGIN = CP.SC, CP.ORIGIN
DAMP_PX = 300.0
SHEET = ('22-37L', '22-37R')
CURL_ROUNDS = 4
CORNER_M = 10.0


# ------------------------------------------------------------------ geometry
def hull_of(X):
    from scipy.spatial import ConvexHull
    h = ConvexHull(X)
    return X[h.vertices]                                   # counter-clockwise


def hull_dist(H, Q):
    """distance (px) from Q to the convex polygon H (0 inside)"""
    Q = np.asarray(Q, float)
    a = H; b = np.roll(H, -1, 0)
    e = b - a
    cross = e[None, :, 0] * (Q[:, None, 1] - a[None, :, 1]) - e[None, :, 1] * (Q[:, None, 0] - a[None, :, 0])
    inside = np.all(cross >= 0, 1)
    t = np.clip(((Q[:, None, 0] - a[None, :, 0]) * e[None, :, 0] + (Q[:, None, 1] - a[None, :, 1]) * e[None, :, 1]) / (e[:, 0] ** 2 + e[:, 1] ** 2)[None, :], 0, 1)
    px = a[None, :, 0] + t * e[None, :, 0]; py = a[None, :, 1] + t * e[None, :, 1]
    d = np.hypot(Q[:, None, 0] - px, Q[:, None, 1] - py).min(1)
    return np.where(inside, 0.0, d)


def damp(H, Q, width=DAMP_PX):
    d = hull_dist(H, Q)
    return np.where(d >= width, 0.0, 0.5 * (1 + np.cos(np.pi * np.clip(d / width, 0, 1))))


class Plate:
    """the plate's spline: affine + damped thin plate, in curled pixels if the plate carries a curl"""
    def __init__(self, X, curl=None):
        X = np.asarray(X, float)
        self.curl = curl
        self.H = hull_of(X)
        Xc = self.cq(X)
        self.c = Xc.mean(0)
        _, iu = np.unique(np.round(Xc * 2) / 2, axis=0, return_index=True)
        self.X = Xc[np.sort(iu)]                             # centres, in curled pixels
        P = np.c_[np.ones(len(self.X)), (self.X - self.c) / SC]
        U, s, Vt = np.linalg.svd(P, full_matrices=True)
        self.N = U[:, 3:]
        K = CP.kern(self.X, self.X)
        e, V = np.linalg.eigh(self.N.T @ K @ self.N)
        self.R = (V * np.sqrt(np.clip(e, 0, None))).T
        self.k = 3 + self.N.shape[1]

    def cq(self, Q):
        Q = np.asarray(Q, float)
        if self.curl is None:
            return Q
        return Q + CU.disp(self.curl['side'], self.curl['a'], self.curl['k'], Q)

    def design(self, Q):
        Q = np.asarray(Q, float); Qc = self.cq(Q)
        return np.c_[np.ones(len(Q)), (Qc - self.c) / SC, damp(self.H, Q)[:, None] * (CP.kern(Qc, self.X) @ self.N)]


class System(CP.System):
    def __init__(self, plates, C, ties, gut, curls):
        # as complete.System.__init__, with this module's Plate (damped, curled)
        self.curls = curls
        self.plates, self.C, self.ties, self.gut = plates, C, ties, gut
        self.M = {p: Plate(C[p]['X'], self.curls.get(p)) for p in plates}
        self.off = {}; o = 0
        for p in plates:
            self.off[p] = o; o += self.M[p].k
        self.n = o
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
        Da = self.M['22-37L'].design(pl); Db = self.M['22-37R'].design(pr)
        for g in range(len(pl)):
            r = np.zeros(self.n); r[self.off['22-37L']:self.off['22-37L'] + Da.shape[1]] = Da[g]; r[self.off['22-37R']:self.off['22-37R'] + Db.shape[1]] -= Db[g]
            A.append(r); Y.append(np.zeros(2)); kind.append(('g', g, True))
        self.A = np.array(A); self.Y = np.array(Y); self.kind = kind
        self.cidx = {p: [i for i, k in enumerate(kind) if k[0] == 'c' and k[1] == p] for p in plates}
        self.tidx = [i for i, k in enumerate(kind) if k[0] == 't']
        self.Pen = {}
        for p in plates:
            m = self.M[p]; Rm = np.zeros((m.R.shape[0], self.n)); Rm[:, self.off[p] + 3:self.off[p] + m.k] = m.R
            self.Pen[p] = Rm.T @ Rm

    def model_dict(self, sol, p):
        m = self.M[p]; th = sol['th'][self.off[p]:self.off[p] + m.k]
        w = m.N @ th[3:]; aff = th[:3].copy(); aff[0] += ORIGIN
        d = dict(kind='tps_px', scale_px=SC, center_px=m.c.tolist(), centers_px=m.X.tolist(), affine=aff.tolist(), w=w.tolist(),
                 lam=sol['lams'][p], damp=dict(hull_px=m.H.tolist(), width_px=DAMP_PX, taper='0.5 (1 + cos(pi d / width)), d the distance to the hull'),
                 formula='world = affine . [1, (q - center) / scale] + damp(x) sum_j w_j phi(|q - c_j| / scale), q = x + curl(x), phi(r) = r2 log r')
        if m.curl is not None:
            d['curl'] = dict(side=m.curl['side'], a=list(map(float, m.curl['a'])), k=float(m.curl['k']))
        return d


# ------------------------------------------------------------------ curl
def fit_curls(F, sol, curls, C, ties, gut):
    """bounded Gauss-Newton on the two halves' curls, the spline (sol['th']) and the centres held"""
    from scipy.optimize import lsq_linear
    pl, pr = gut
    th = sol['th']
    rows = []                                          # (plate a, pixels a, plate b or None, pixels b, target, weight)
    for p in SHEET:
        rows.append((p, C[p]['X'], None, None, C[p]['O'] - ORIGIN, np.ones(len(C[p]['X']))))
    rows.append(('22-37L', pl, '22-37R', pr, np.zeros((len(pl), 2)), np.full(len(pl), CP.W_GUT)))
    for j, (t, T) in enumerate(zip(F.tidx, ties)):
        if T['a'] in SHEET or T['b'] in SHEET:
            w = CP.W_GUT if T['sheet'] else sol['tw'][j]
            rows.append((T['a'], np.array([T['xa']]), T['b'], np.array([T['xb']]), np.zeros((1, 2)), np.array([w])))

    def world(p, Q, cv):
        m = F.M[p]; saved = m.curl; m.curl = cv.get(p, saved) if p in SHEET else saved
        out = m.design(Q) @ th[F.off[p]:F.off[p] + m.k]
        m.curl = saved
        return out

    def resid(cv):
        R, Wt = [], []
        for pa, Qa, pb, Qb, tgt, w in rows:
            v = world(pa, Qa, cv) - (world(pb, Qb, cv) if pb else 0) - tgt
            R.append(v); Wt.append(w)
        R = np.vstack(R); Wt = np.concatenate(Wt)
        return (R * np.sqrt(Wt)[:, None]).ravel()

    def pack(cv):
        return np.concatenate([np.r_[cv[p]['a'], cv[p]['k']] for p in SHEET])

    def unpack(v):
        return {p: dict(side=curls[p]['side'], a=v[i * 7:i * 7 + 6], k=v[i * 7 + 6]) for i, p in enumerate(SHEET)}
    best = None
    for sL in (1, -1):
        for sR in (1, -1):
            v = pack(curls).astype(float)
            v[0:6] = np.abs(v[0:6]) * sL; v[7:13] = np.abs(v[7:13]) * sR
            lo = np.r_[[0 if sL > 0 else -np.inf] * 6, -CU.K_MAX, [0 if sR > 0 else -np.inf] * 6, -CU.K_MAX]
            hi = np.r_[[np.inf if sL > 0 else 0] * 6, CU.K_MAX, [np.inf if sR > 0 else 0] * 6, CU.K_MAX]
            for it in range(6):
                r0 = resid(unpack(v))
                Jm = np.zeros((len(r0), len(v)))
                for i in range(len(v)):
                    h = 1e-3 if i % 7 == 6 else 0.5
                    vp = v.copy(); vp[i] += h; vm = v.copy(); vm[i] -= h
                    Jm[:, i] = (resid(unpack(vp)) - resid(unpack(vm))) / (2 * h)
                res = lsq_linear(Jm, -r0, bounds=(lo - v, hi - v), method='bvls')
                v = np.clip(v + res.x, lo, hi)
                if np.abs(res.x).max() < 1e-3:
                    break
            cost = float(np.sum(resid(unpack(v)) ** 2))
            if best is None or cost < best[0]:
                best = (cost, v.copy(), (sL, sR))
    return unpack(best[1]), best[2], best[0]


# ------------------------------------------------------------------ choice
def sheet_rms(F, sol):
    return CP.rms(np.concatenate([F.heldout(sol, p) for p in SHEET]))


def choose(F, passes=2, log=print, lams=None):
    lams = dict(lams) if lams else {p: CP.LAM0 for p in F.plates}
    sol = F.solve(lams); tw = sol['tw']
    for ps in range(passes):
        changed = False
        for p in F.plates:
            best = None
            for lam in CP.LAMS:
                L_ = dict(lams); L_[p] = lam
                s = F.solve(L_, tw, iterate=False)
                h = sheet_rms(F, s) if p in SHEET else CP.rms(F.heldout(s, p))
                if best is None or h < best[0] - 1e-6:
                    best = (h, lam)
            changed |= best[1] != lams[p]; lams[p] = best[1]
            log(f'pass {ps + 1} {p}: lam {best[1]} held-out {best[0]:.2f}' + (' (37L+37R sheet)' if p in SHEET else ''))
        sol = F.solve(lams, tw); tw = sol['tw']
        if not changed:
            break
    return lams, F.solve(lams, tw)


# ------------------------------------------------------------------ main
def main():
    write = '--write' in sys.argv
    today = datetime.date.today().isoformat()
    out = SP + f'reports/{today}_{TAG}'; os.makedirs(out, exist_ok=True)
    log = lambda s: print(s, flush=True)
    plates = S.plate_ids()
    C, latest, drop = CP.setup()
    S.plate_crossings = CP.patched_crossings(latest); S.pairs = L2.patched_pairs(drop)
    recs = []
    for p in plates:
        recs += S.plate_crossings(p)[0]
    near, _ = S.pairs(recs)
    ties = []
    for i, j, d in near:
        a, b = recs[i], recs[j]
        if b['kind'] != 'plate':
            continue
        ties.append(dict(a=a['src'], b=b['src'], xa=[a['x'], a['y']], xb=[b['x'], b['y']], street_1=a['a'], street_2=a['b'],
                         before_m=round(float(d), 2), sheet={a['src'], b['src']} == set(SHEET), complete=bool(a.get('complete') or b.get('complete'))))
    ov = LC.overlap_pairs()
    pr = np.array([q[:2] for q in ov['pairs']], float); pl = np.array([q[2:] for q in ov['pairs']], float)
    gap0 = np.hypot(*(C['22-37L']['cur'](pl) - C['22-37R']['cur'](pr)).T)
    curls = {p: dict(side=CU.side_of(p), a=np.zeros(CU.NA), k=0.0) for p in SHEET}
    lams = None; trail = []
    for rnd in range(CURL_ROUNDS):
        F = System(plates, C, ties, (pl, pr), curls)
        lams, sol = choose(F, log=log, lams=lams)
        if rnd == CURL_ROUNDS - 1:
            break
        curls, signs, cost = fit_curls(F, sol, curls, C, ties, (pl, pr))
        sh = {p: dict(s0_px=round(float(CU.s_of_u(curls[p]['a'], 0)[0]), 1), s500_px=round(float(CU.s_of_u(curls[p]['a'], 500)[0]), 1),
                      s2000_px=round(float(CU.s_of_u(curls[p]['a'], 2000)[0]), 1), k=round(float(curls[p]['k']), 3)) for p in SHEET}
        trail.append(dict(round=rnd + 1, sheet_heldout=round(sheet_rms(F, sol), 3), curl=sh, signs=signs))
        log(f'curl round {rnd + 1}: sheet held-out {sheet_rms(F, sol):.2f} curl {sh}')
    trail.append(dict(round=CURL_ROUNDS, sheet_heldout=round(sheet_rms(F, sol), 3)))
    rows, ctl_rows, guard_fail = [], [], []
    sheet_e = {'before': [], 'after': []}
    for p in plates:
        c = C[p]; new = F.world(sol, p, c['X']); own = np.hypot(*(new - c['O']).T)
        ho = F.heldout(sol, p); hb = np.hypot(*(c['before'] - c['O']).T)
        w, h = SV.plate_size(p); corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
        mv = np.hypot(*(F.world(sol, p, corners) - c['cur'](corners)).T)
        r = dict(plate=p, controls=len(c['X']), hand=sum(s == 'hand' for s in c['src']), new=sum(s == 'complete' for s in c['src']),
                 dropped=len(c['dropped']), lam=sol['lams'][p], own_rms=round(CP.rms(own), 2), heldout_before=round(CP.rms(hb), 2),
                 heldout_after=round(CP.rms(ho), 2), heldout_change=round(CP.rms(ho) - CP.rms(hb), 2),
                 max_corner_move_m=round(float(mv.max()), 2), corner_moves_m=[round(float(v), 1) for v in mv],
                 ties=sum(1 for t in ties if p in (t['a'], t['b'])), curl='' if p not in SHEET else json.dumps({k: (list(np.round(v, 3)) if isinstance(v, np.ndarray) else v) for k, v in curls[p].items() if k != 'side'}))
        rows.append(r)
        if p in SHEET:
            sheet_e['before'].append(hb); sheet_e['after'].append(ho)
        elif CP.rms(ho) > CP.rms(hb) + 1e-9:
            guard_fail.append((p, f"held-out {CP.rms(ho):.2f} m against {CP.rms(hb):.2f} m before"))
        if mv.max() > CORNER_M:
            guard_fail.append((p, f"corner(s) {[int(k) for k in np.where(mv > CORNER_M)[0]]} move {', '.join(f'{v:.1f}' for v in mv[mv > CORNER_M])} m"))
        for i in range(len(c['X'])):
            ctl_rows.append(dict(plate=p, src=c['src'][i], names=c['names'][i], x=round(float(c['X'][i, 0]), 1), y=round(float(c['X'][i, 1]), 1),
                                 E=round(float(c['O'][i, 0]), 2), N=round(float(c['O'][i, 1]), 2), before_m=round(float(hb[i]), 2),
                                 own_m=round(float(own[i]), 2), heldout_m=round(float(ho[i]), 2)))
    sb, sa = CP.rms(np.concatenate(sheet_e['before'])), CP.rms(np.concatenate(sheet_e['after']))
    if sa > sb + 1e-9:
        guard_fail.insert(0, ('22-37L + 22-37R', f'sheet held-out {sa:.2f} m against {sb:.2f} m before'))
    tinfo = []
    for k, t in enumerate(ties):
        na = F.world(sol, t['a'], np.array([t['xa']]))[0]; nb = F.world(sol, t['b'], np.array([t['xb']]))[0]
        tinfo.append(dict(a=t['a'], b=t['b'], street_1=t['street_1'], street_2=t['street_2'], before_m=t['before_m'],
                          after_m=round(float(np.hypot(*(nb - na))), 2), weight=round(float(CP.W_GUT if t['sheet'] else sol['tw'][k]), 3),
                          sheet=t['sheet'], complete=t['complete']))
    gap1 = np.hypot(*(F.world(sol, '22-37L', pl) - F.world(sol, '22-37R', pr)).T)
    curl_out = {p: dict(side=curls[p]['side']['side'], fold=curls[p]['side'].get('fold'), a=[round(float(v), 3) for v in curls[p]['a']], k=round(float(curls[p]['k']), 4),
                        s_px={str(u): round(float(CU.s_of_u(curls[p]['a'], u)[0]), 1) for u in (0, 200, 500, 1000, 2000, 4000)}) for p in SHEET}
    summary = dict(lams=sol['lams'], ties=len(ties), gutter_pairs=len(pl), gutter_weight=CP.W_GUT, damp_px=DAMP_PX,
                   sheet_heldout=dict(before=round(sb, 2), after=round(sa, 2)), curl=curl_out, curl_rounds=trail,
                   gutter_gap_before=dict(median=round(float(np.median(gap0)), 2), p90=round(float(np.percentile(gap0, 90)), 2), max=round(float(gap0.max()), 2)),
                   gutter_gap_after=dict(median=round(float(np.median(gap1)), 2), p90=round(float(np.percentile(gap1, 90)), 2), max=round(float(gap1.max()), 2)),
                   guard_fail=guard_fail, controls=sum(len(C[p]['X']) for p in plates))
    import scipy
    meta = dict(made=datetime.datetime.now().isoformat(timespec='seconds'), by='tools/sanborn/joint/complete2.py', lams_tried=CP.LAMS, huber_m=CP.HUBER,
                corner_m=CORNER_M, damp_px=DAMP_PX, scale_px=SC, versions=dict(numpy=np.__version__, scipy=scipy.__version__), picks=CP.COMPLETE,
                overlap=LC.OVERLAP, sides=CU.SIDES)
    if write:
        for p in plates:
            jp = J.joint_path(p, TAG); assert jp != J.base_path(p)
            d = F.model_dict(sol, p)
            d.update(controls_X=C[p]['X'].tolist(), controls_O=C[p]['O'].tolist(), base=J.base_path(p),
                     solve=os.path.relpath(out, SP).replace('\\', '/'), made=meta['made'])
            pickle.dump(d, open(SP + jp, 'wb'))
        J._J.clear()
        chk = max(float(np.abs(J.world_many(p, C[p]['X'], TAG) - F.world(sol, p, C[p]['X'])).max()) for p in plates)
        w, h = SV.plate_size('22-37L')
        chk2 = float(np.abs(J.world_many('22-37L', np.array([[0, 0], [w, h]], float), TAG) - F.world(sol, '22-37L', np.array([[0, 0], [w, h]], float))).max())
        assert chk < 1e-6 and chk2 < 1e-6, (chk, chk2)
        sd = {}
        for tag, models in (('before', None), ('after', TAG)):
            S.READ.clear(); S.MODELS = None; S.JOINT = False
            d_ = SP + f'reports/{today}_seams_{TAG}' + ('_before' if tag == 'before' else '')
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
    print(json.dumps({k: v for k, v in summary.items() if k not in ('curl_rounds',)}, indent=1, default=str))
    for r in rows:
        print({k: v for k, v in r.items() if k not in ('corner_moves_m', 'curl')})


def write_readme(out, meta, summary, rows, tinfo):
    g0, g1 = summary['gutter_gap_before'], summary['gutter_gap_after']
    sd = summary.get('seams', {}); sh = summary['sheet_heldout']
    L = [f"# Complete-control fit, second pass, {meta['made'][:10]}", '',
         'As `reports/2026-11-06_complete` with three changes (`tools/sanborn/joint/complete2.py`): the thin-plate part of '
         f"each plate's spline damped to its affine part over {DAMP_PX:.0f} px outside the convex hull of its controls; 37L "
         'and 37R with the page-curl pre-correction under their splines, judged as one sheet; everything else as before. '
         'Models beside the old ones (`fwd_complete2.pkl`); ' + ('**guard passed**' if summary.get('apply') else '**guard failed: not applied**') + '.', '',
         '| Plate | Controls | Hand | New | Dropped (rule 4) | Smoothing | Own rms m | Held-out before m | Held-out after m | Change | Max corner move m | Ties |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        L.append(f"| {r['plate']} | {r['controls']} | {r['hand']} | {r['new']} | {r['dropped']} | {r['lam']} | {r['own_rms']} | {r['heldout_before']} | "
                 f"{r['heldout_after']} | {r['heldout_change']:+.2f} | {r['max_corner_move_m']} | {r['ties']} |")
    L += ['', f"37L + 37R as one sheet (every control of both): held-out {sh['before']} -> {sh['after']} m.", '']
    for p, c in summary['curl'].items():
        L.append(f"- {p} curl ({c['side']} edge): s(u) px at u = 0, 200, 500, 1000, 2000, 4000: "
                 f"{', '.join(str(v) for v in c['s_px'].values())}; k {c['k']}")
    L += ['', f"Gutter gap (37L/37R, {summary['gutter_pairs']} pairs at weight {summary['gutter_weight']}): median {g0['median']} -> {g1['median']} m, "
          f"90% {g0['p90']} -> {g1['p90']} m, max {g0['max']} -> {g1['max']} m.", '']
    if sd:
        b, a = sd['before'], sd['after']
        L += [f"Seams, all plate-plate pairs (hand picks plus complete picks; `{sd['before_dir']}` -> `{sd['after_dir']}`): "
              f"n {b['n']} -> {a['n']}, median {b['median']} -> {a['median']} m, 90% {b['p90']} -> {a['p90']} m, max {b['max']} -> {a['max']} m, "
              f"over 10 m {b['over_10m']} -> {a['over_10m']}, over 20 m {b['over_20m']} -> {a['over_20m']}.", '']
    L += ['## Guard', '']
    L += [f'- {p}: {why}' for p, why in summary['guard_fail']] if summary['guard_fail'] else ['Every check holds.']
    L += ['', f"Ties: {summary['ties']} ({sum(t['complete'] for t in tinfo)} involve a complete pick); `ties.csv` before and after each.", '']
    open(out + '/README.md', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
