"""The local fit with a page-curl option (Ben, 6 November 2026: the plates are bound-book scans; the distortion near a
spine is page curl).

    cd data/sanborn
    python ../../tools/sanborn/joint/local3.py [--write]

Part 2 of the ruling. The five plates (33, 34R, 37L, 37R, 38) fitted together, the other 16 fixed, as in local2.py (its
docstring: re-read picks in place of the old ones, wrong matches dropped, ties from the seam matching), with three
changes:
- each plate's correction is chosen by held-out error among affine, affine + curl and affine + thin plate (tps0.3 ...
  tps100, as before), for all five (37L and 37R included);
- affine + curl: new(px) = Q + d(Q), Q = F(px + c(px)), c the page curl of tools/sanborn/joint/curl.py on the plate's
  gutter edge (data/sanborn/joint/curl_sides.json), d affine. The curl's spline coefficients are all >= 0 or all <= 0
  (monotone; both signs tried, the lower misfit kept) and |k| <= 0.9; solved as bounded least squares (scipy lsq_linear),
  linearised in the curl (Gauss-Newton: F and its slope taken at the current curled pixel, repeated to convergence);
- the 37L/37R gutter pairs (206 paper points matched across the overlap) and their shared picks are ties at weight 3
  (an error of 1 m there counts as 1.7 m on a control), not 25, and not Huber-weighted; other ties Huber (k = 6 m).
Held-out error: each own control left out in turn, the plate's own model refitted without it (fwdlib.make), the joint
system solved again without that control (tie weights and the curl's linearisation held).

Then, read-only: the same choice (affine, affine + curl, thin plate) for every one of the 21 plates alone on its own
controls (the plate's fit picks, no ties), and which would pick curl and the held-out gain. No model files for that.

Writes reports/<date>_local3/ (README.md, plates.csv, ties.csv, controls.csv, curl21.csv, solve.json) and, with --write,
fwd_local3.pkl beside each of the five plates' old models and the seam report on them (reports/<date>_seams_local3).
"""
import csv, datetime, json, os, pickle, sys

import numpy as np
from scipy.optimize import lsq_linear

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402
import curl as CU  # noqa: E402
import local as LC  # noqa: E402
import local2 as L2  # noqa: E402

J, S, SV = LC.J, LC.S, LC.SV
SP = _ws.DATA
FIT, TAG = LC.FIT, 'local3'
SCALE, U, HUBER = LC.SCALE, LC.U, LC.HUBER
W_GUT = 3.0
KINDS = ['affine', 'curl'] + [k for k in LC.KINDS if k.startswith('tps')]
LIMIT = {'22-33': 0.3, '22-34R': 0.3, '22-38': 0.3, '22-37L': 0.5, '22-37R': 0.5}
GAP_MAX = 2.0
H_PX = 2.0


class Fit:
    def __init__(self, plates, C, basefn, ties=(), sheet=None, sides=None):
        self.plates, self.C, self.basefn, self.sides = plates, C, basefn, sides or {}
        pts = {p: [np.asarray(C[p]['X'], float)] for p in plates}
        cnt = {p: len(C[p]['X']) for p in plates}

        def add(p, q):
            pts[p].append(np.asarray(q, float)[None]); cnt[p] += 1; return cnt[p] - 1
        obs = []
        for p in plates:
            for i in range(len(C[p]['X'])):
                obs.append(dict(t='c', p=p, i=i, terms=[(1.0, p, i)], target=np.asarray(C[p]['O'][i], float), w=1.0))
        for k, t in enumerate(ties):
            terms = []
            for sg, sd in ((1.0, 'a'), (-1.0, 'b')):
                p = t[sd]
                terms.append((sg, p, add(p, t['x' + sd])) if p in plates else (sg, None, np.asarray(t['P' + sd], float)))
            obs.append(dict(t='g' if t['sheet'] else 't', k=k, terms=terms, target=np.zeros(2), w=W_GUT if t['sheet'] else 1.0))
        if sheet is not None:
            for k, (pl, pr) in enumerate(zip(*sheet)):
                obs.append(dict(t='s', k=k, terms=[(1.0, '22-37L', add('22-37L', pl)), (-1.0, '22-37R', add('22-37R', pr))],
                                target=np.zeros(2), w=W_GUT))
        self.obs = obs
        self.pts = {p: np.vstack(pts[p]) for p in plates}
        self.P = {p: np.asarray(basefn[p](self.pts[p]), float) for p in plates}
        self.center = {p: np.asarray(C[p]['O'], float).mean(0) for p in plates}
        # thin-plate centres: the plate's controls, its tie points and every third gutter pair (as local.py)
        self.cent, self.Nsp, self.Kcc = {}, {}, {}
        for p in plates:
            nC = len(C[p]['X']); use = list(range(nC))
            for o in obs:
                if o['t'] in ('t', 'g'):
                    use += [i for sg, q, i in o['terms'] if q == p]
                elif o['t'] == 's' and o['k'] % 3 == 0:
                    use += [i for sg, q, i in o['terms'] if q == p]
            keep = []
            for q in self.P[p][use]:
                if all(np.hypot(*(q - k)) > 1.0 for k in keep):
                    keep.append(q)
            c = np.array(keep); self.cent[p] = c
            Cm = np.c_[np.ones(len(c)), (c - self.center[p]) / SCALE]
            self.Nsp[p] = np.linalg.svd(Cm.T)[2][3:].T
            self.Kcc[p] = J.tps_kernel(c, c, U)
        self._cache = {}

    # ---------------------------------------------------------------- columns
    def ncol(self, p, kind):
        return 6 + (2 * self.Nsp[p].shape[1] if kind.startswith('tps') else 0) + (CU.NA + 1 if kind == 'curl' else 0)

    def corr_cols(self, p, Q, kind):
        """world correction columns at world points Q: (n, 2, ncol_without_curl)"""
        B = J.basis(Q, self.center[p], SCALE, 'affine'); n = len(Q)
        if kind.startswith('tps'):
            K = J.tps_kernel(Q, self.cent[p], U) @ self.Nsp[p]; z = np.zeros_like(K); zb = np.zeros_like(B)
            return np.stack([np.c_[B, zb, K, z], np.c_[zb, B, z, K]], 1)
        zb = np.zeros((n, 3))
        return np.stack([np.c_[B, zb], np.c_[zb, B]], 1)

    def curled(self, p, q, a, k):
        side = self.sides[p]
        return q + CU.disp(side, a, k, q)

    def evaluate(self, p, kind, st):
        """constant c (n, 2) and columns Bm (n, 2, ncol): the plate's world position of its points ~ c + Bm theta"""
        if kind != 'curl':
            if (p, kind) not in self._cache:
                P = self.P[p]; self._cache[(p, kind)] = (P, self.corr_cols(p, P, kind))
            return self._cache[(p, kind)]
        a0, k0 = st; q = self.pts[p]; side = self.sides[p]; e = CU.axis_vec(side)
        q1 = self.curled(p, q, a0, k0)
        Q0 = self.basefn[p](q1)
        Je = (self.basefn[p](q1 + H_PX * e) - self.basefn[p](q1 - H_PX * e)) / (2 * H_PX)   # world per pixel along the curl axis
        u, v = CU.uv(side, q); Phi = CU.phi(u); s0 = Phi @ a0; g0 = 1.0 + k0 * v
        d0 = s0 * g0
        c = Q0 - Je * d0[:, None] - Je * (s0 * v * k0)[:, None]
        base = self.corr_cols(p, Q0, 'affine')
        cc = np.concatenate([Je[:, :, None] * (Phi * g0[:, None])[:, None, :], (Je * (s0 * v)[:, None])[:, :, None]], 2)
        return c, np.concatenate([base, cc], 2)

    # ---------------------------------------------------------------- solve
    def layout(self, kinds):
        off, m = {}, 0
        for p in self.plates:
            off[p] = m; m += self.ncol(p, kinds[p])
        return off, m

    def penalty(self, kinds, off, m):
        R = []
        for p in self.plates:
            if kinds[p].startswith('tps'):
                lam = float(kinds[p][3:]); N_ = self.Nsp[p]; S_ = lam * N_.T @ self.Kcc[p] @ N_
                ev, V = np.linalg.eigh((S_ + S_.T) / 2); r = np.sqrt(np.clip(ev, 0, None))[:, None] * V.T
                ns = N_.shape[1]
                for o in (off[p] + 6, off[p] + 6 + ns):
                    blk = np.zeros((ns, m)); blk[:, o:o + ns] = r; R.append(blk)
        return np.vstack(R) if R else np.zeros((0, m))

    def build(self, kinds, states, off, m):
        E = {p: self.evaluate(p, kinds[p], states.get(p)) for p in self.plates}
        A = np.zeros((2 * len(self.obs), m)); y = np.zeros(2 * len(self.obs))
        for j, o in enumerate(self.obs):
            yv = o['target'].copy()
            for sg, p, i in o['terms']:
                if p is None:
                    yv -= sg * i
                else:
                    c, Bm = E[p]; yv -= sg * c[i]; nc = Bm.shape[2]
                    A[2 * j, off[p]:off[p] + nc] += sg * Bm[i, 0]; A[2 * j + 1, off[p]:off[p] + nc] += sg * Bm[i, 1]
            y[2 * j:2 * j + 2] = yv
        return A, y

    def bounds(self, kinds, signs, states, off, m):
        lb, ub = np.full(m, -np.inf), np.full(m, np.inf); any_b = False
        for p in self.plates:
            if kinds[p] == 'curl':
                any_b = True; o = off[p] + 6
                if signs[p] > 0:
                    lb[o:o + CU.NA] = 0.0
                else:
                    ub[o:o + CU.NA] = 0.0
                a0 = states[p][0]
                if np.abs(a0).max() < 1e-9:      # no curl yet: k has nothing to scale
                    lb[o + CU.NA], ub[o + CU.NA] = -1e-12, 1e-12
                else:
                    lb[o + CU.NA], ub[o + CU.NA] = -CU.K_MAX, CU.K_MAX
        return lb, ub, any_b

    @staticmethod
    def lsq(Aw, yw, lb, ub, any_b):
        if not any_b:
            return np.linalg.lstsq(Aw, yw, rcond=None)[0]
        return lsq_linear(Aw, yw, bounds=(lb, ub), method='bvls', tol=1e-12, max_iter=2000).x

    def solve(self, kinds, signs=None, iters=60):
        signs = signs or {}
        off, m = self.layout(kinds)
        states = {p: (np.zeros(CU.NA), 0.0) for p in self.plates if kinds[p] == 'curl'}
        Rp = self.penalty(kinds, off, m)
        tidx = [j for j, o in enumerate(self.obs) if o['t'] == 't']
        tw = np.ones(len(tidx))
        for it in range(iters):
            A, y = self.build(kinds, states, off, m)
            wo = np.array([o['w'] for o in self.obs]); wo[tidx] = tw
            w = np.repeat(wo, 2)
            lb, ub, any_b = self.bounds(kinds, signs, states, off, m)
            Aw = np.vstack([A * np.sqrt(w)[:, None], Rp]); yw = np.r_[y * np.sqrt(w), np.zeros(len(Rp))]
            th = self.lsq(Aw, yw, lb, ub, any_b)
            R = y - A @ th
            new_states = {p: (th[off[p] + 6:off[p] + 6 + CU.NA].copy(), float(th[off[p] + 6 + CU.NA])) for p in states}
            rt = np.array([np.hypot(R[2 * j], R[2 * j + 1]) for j in tidx])
            new_tw = np.where(rt <= HUBER, 1.0, HUBER / np.maximum(rt, 1e-9))
            dmax = max([np.abs(new_states[p][0] - states[p][0]).max() for p in states] + [0.0])
            kmax = max([abs(new_states[p][1] - states[p][1]) for p in states] + [0.0])
            first = any(np.abs(states[p][0]).max() < 1e-9 for p in states)
            states = new_states
            if np.allclose(new_tw, tw, atol=1e-4) and dmax < 0.01 and kmax < 1e-4 and not first:
                break
            tw = new_tw
        A, y = self.build(kinds, states, off, m)       # linearised at the final curl
        wo = np.array([o['w'] for o in self.obs]); wo[tidx] = tw; w = np.repeat(wo, 2)
        lb, ub, any_b = self.bounds(kinds, signs, states, off, m)
        Aw = np.vstack([A * np.sqrt(w)[:, None], Rp]); yw = np.r_[y * np.sqrt(w), np.zeros(len(Rp))]
        th = self.lsq(Aw, yw, lb, ub, any_b)
        cost = float(np.sum((Aw @ th - yw) ** 2))
        return dict(kinds=dict(kinds), signs=dict(signs), off=off, m=m, A=A, y=y, w=w, Rp=Rp, lb=lb, ub=ub, any_b=any_b,
                    th=th, states=states, tw=tw, tidx=tidx, cost=cost, iters=it + 1)

    def solve_best(self, kinds, signs):
        """curl plates whose sign is not yet set: try both, keep the lower misfit"""
        free = [p for p in self.plates if kinds[p] == 'curl' and p not in signs]
        best = None
        for combo in np.array(np.meshgrid(*[[1, -1]] * len(free))).T.reshape(-1, len(free)) if free else [[]]:
            sg = dict(signs); sg.update({p: int(s) for p, s in zip(free, combo)})
            s = self.solve(kinds, sg)
            if best is None or s['cost'] < best['cost']:
                best = s
        return best

    def heldout(self, sol, p, details=False):
        A, y, w, th = sol['A'], sol['y'], sol['w'], sol['th']
        c = self.C[p]; errs = []
        for j, o in enumerate(self.obs):
            if o['t'] != 'c' or o['p'] != p:
                continue
            w2 = w.copy(); w2[2 * j:2 * j + 2] = 0.0
            Aw = np.vstack([A * np.sqrt(w2)[:, None], sol['Rp']]); yw = np.r_[y * np.sqrt(w2), np.zeros(len(sol['Rp']))]
            t2 = self.lsq(Aw, yw, sol['lb'], sol['ub'], sol['any_b'])
            i = o['i']
            r = (c['Pl'][i] - c['P'][i]) - y[2 * j:2 * j + 2] + A[2 * j:2 * j + 2] @ t2
            errs.append(float(np.hypot(*r)))
        rms = float(np.sqrt(np.mean(np.square(errs))))
        return (rms, errs) if details else rms

    # ---------------------------------------------------------------- exact positions and the model file
    def theta(self, sol, p):
        o = sol['off'][p]; return sol['th'][o:o + self.ncol(p, sol['kinds'][p])]

    def world(self, sol, p, q):
        q = np.atleast_2d(np.asarray(q, float)); kind = sol['kinds'][p]; th = self.theta(sol, p)
        if kind == 'curl':
            a, k = sol['states'][p]; a = th[6:6 + CU.NA]; k = th[6 + CU.NA]
            Q = self.basefn[p](self.curled(p, q, a, k))
        else:
            Q = self.basefn[p](q)
        Bm = self.corr_cols(p, Q, 'affine' if kind == 'curl' else kind)
        return Q + np.einsum('nij,j->ni', Bm, th[:Bm.shape[2]])

    def model_dict(self, sol, p):
        th = self.theta(sol, p); kind = sol['kinds'][p]
        d = dict(model='local', kind=kind, plate=p, center=[float(v) for v in self.center[p]], scale=SCALE, U=U,
                 coefE=th[0:3].tolist(), coefN=th[3:6].tolist(), centers=None, wE=None, wN=None, curl=None)
        if kind.startswith('tps'):
            ns = self.Nsp[p].shape[1]
            d.update(centers=self.cent[p].tolist(), wE=(self.Nsp[p] @ th[6:6 + ns]).tolist(), wN=(self.Nsp[p] @ th[6 + ns:6 + 2 * ns]).tolist())
        if kind == 'curl':
            side = self.sides[p]; half = (side['size'][1] if side['axis'] == 'x' else side['size'][0]) / 2.0
            d['curl'] = dict(side=side, a=th[6:6 + CU.NA].tolist(), k=float(th[6 + CU.NA]), sign=sol['signs'][p],
                             k_per_px=float(th[6 + CU.NA]) / half, knots=list(CU.KNOTS))
        return d


def choose(F, plates, passes=3, log=None):
    kinds = {p: 'affine' for p in plates}; signs = {}
    sol = F.solve(kinds); ho = {p: F.heldout(sol, p) for p in plates}; trail = []; tried = {}
    for ps in range(passes):
        changed = False
        for p in plates:
            best = (ho[p], kinds[p], sol, signs)
            for k in KINDS:
                if k == kinds[p]:
                    continue
                alt = dict(kinds); alt[p] = k
                sg = {q: s for q, s in signs.items() if q != p and alt[q] == 'curl'}
                s2 = F.solve_best(alt, sg) if k == 'curl' else F.solve(alt, sg)
                h2 = F.heldout(s2, p); tried[(ps + 1, p, k)] = round(h2, 3)
                if h2 < best[0] - 1e-6:
                    best = (h2, k, s2, s2['signs'])
            if best[1] != kinds[p]:
                trail.append(dict(pass_=ps + 1, plate=p, frm=kinds[p], to=best[1], heldout=round(best[0], 3)))
                kinds = dict(kinds); kinds[p] = best[1]; sol = best[2]; signs = dict(best[3]); ho = {q: F.heldout(sol, q) for q in plates}
                changed = True
        if log:
            log(f'pass {ps + 1} {kinds} {signs} ' + str({p: round(v, 2) for p, v in ho.items()}))
        if not changed:
            break
    return kinds, signs, sol, ho, trail, tried


def curl_shape(F, sol, p):
    """s at the knots (pixels), the world size of 1 px across the gutter (m), and k"""
    th = F.theta(sol, p); a = th[6:6 + CU.NA]; k = float(th[6 + CU.NA])
    s = CU.s_of_u(a, np.array(CU.KNOTS[:-1]))
    side = F.sides[p]; e = CU.axis_vec(side); q = np.asarray(F.C[p]['X'], float)
    mpp = float(np.median(np.hypot(*((F.basefn[p](q + e) - F.basefn[p](q - e)) / 2).T)))
    return dict(s_px={int(u): round(float(v), 1) for u, v in zip(CU.KNOTS[:-1], s)}, s0_m=round(float(s[0]) * mpp, 2), m_per_px=round(mpp, 4),
                k=round(k, 3), sign=sol['signs'][p])


# -------------------------------------------------------------------- the 21 plates alone (read-only)
def per_plate_21(sides, log=None):
    rows = []
    for p in S.plate_ids():
        X, O, P, Pl, names, model = SV.controls(p)
        C = {p: dict(X=X, O=O, P=P, Pl=Pl, model=model)}
        bf = {p: (lambda pid: lambda q: J.base_many(pid, np.asarray(q, float)))(p)}
        F = Fit([p], C, bf, sides={p: sides[p]})
        res = {}
        for k in KINDS:
            s = F.solve_best({p: k}, {}) if k == 'curl' else F.solve({p: k})
            res[k] = (F.heldout(s, p), s)
        nc = min((k for k in KINDS if k != 'curl'), key=lambda k: res[k][0])
        pick = min(KINDS, key=lambda k: res[k][0])
        sh = curl_shape(F, res['curl'][1], p)
        own = SV.old_heldout(p, model)
        u = CU.uv(sides[p], X)[0]
        rows.append(dict(plate=p, own_model=model, own_heldout=None if own is None else round(own, 2), controls=len(X),
                         controls_within_500px=int((u < 500).sum()),
                         gutter_edge=sides[p]['side'], edge_from='page position' if sides[p]['how'].startswith('page position:') else 'worst held-out edge',
                         best_without_curl=nc, heldout_without_curl=round(res[nc][0], 2), heldout_curl=round(res['curl'][0], 2),
                         picks=pick, picks_curl=pick == 'curl', heldout_gain_m=round(res[nc][0] - res['curl'][0], 2),
                         curl_s0_px=sh['s_px'][0], curl_s0_m=sh['s0_m'], curl_k=sh['k'], heldout_affine=round(res['affine'][0], 2)))
        if log:
            log(str(rows[-1]))
    return rows


def main():
    write = '--write' in sys.argv
    today = datetime.date.today().isoformat()
    out = SP + f'reports/{today}_local3'; os.makedirs(out, exist_ok=True)
    log = lambda s: print(s, flush=True)
    sides = {p: CU.side_of(p) for p in S.plate_ids()}
    latest, ctl, drop = L2.reread_state()
    C, basefn, info = L2.setup(latest, ctl)
    S.plate_crossings = L2.patched_crossings(latest); S.pairs = L2.patched_pairs(drop)
    recs = []
    for p in S.plate_ids():
        recs += S.plate_crossings(p)[0]
    near, _ = S.pairs(recs)
    ties = []
    for i, j, d in near:
        a, b = recs[i], recs[j]
        if b['kind'] != 'plate' or not (a['src'] in FIT or b['src'] in FIT):
            continue
        Pa = basefn[a['src']]([[a['x'], a['y']]])[0] if a['src'] in FIT else np.array([a['E'], a['N']])
        Pb = basefn[b['src']]([[b['x'], b['y']]])[0] if b['src'] in FIT else np.array([b['E'], b['N']])
        sheet = {a['src'], b['src']} == {'22-37L', '22-37R'}
        ties.append(dict(a=a['src'], b=b['src'], xa=[a['x'], a['y']], xb=[b['x'], b['y']], Pa=np.asarray(Pa, float), Pb=np.asarray(Pb, float),
                         street_1=a['a'], street_2=a['b'], before_m=round(float(np.hypot(*(np.asarray(Pa) - np.asarray(Pb)))), 2), sheet=sheet,
                         reread=bool(a.get('reread') or b.get('reread'))))
    ov = LC.overlap_pairs()
    pr = np.array([q[:2] for q in ov['pairs']]); pl = np.array([q[2:] for q in ov['pairs']])
    PR, PL = basefn['22-37R'](pr), basefn['22-37L'](pl)
    gap0 = np.hypot(*(PL - PR).T)
    F = Fit(FIT, C, basefn, ties, (pl, pr), sides)
    log(f'ties {len(ties)} gutter pairs {len(pr)} gap before median {np.median(gap0):.2f}')
    kinds, signs, sol, ho, trail, tried = choose(F, FIT, log=log)
    rows, ctl_rows = [], []
    for p in FIT:
        c = C[p]; new = F.world(sol, p, c['X']); after = np.hypot(*(new - c['O']).T)
        w, h = SV.plate_size(p); corners = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
        mv = np.hypot(*(F.world(sol, p, corners) - J.base_many(p, corners)).T)
        ob = SV.old_heldout(p, c['model']); inf = info[p]
        before = J.base_many(p, c['X'])
        sh = curl_shape(F, sol, p) if kinds[p] == 'curl' else None
        rows.append(dict(plate=p, base_model=c['model'] + (' (rebuilt)' if inf['rebuilt'] else ''), gutter_edge=sides[p]['side'],
                         correction=kinds[p], curl_s0_px=sh['s_px'][0] if sh else '', curl_s0_m=sh['s0_m'] if sh else '', curl_k=sh['k'] if sh else '',
                         controls=len(c['O']), rms_before=round(inf['rms_before'], 2), rms_after=round(float(np.sqrt((after ** 2).mean())), 2),
                         limit=LIMIT[p], heldout_before=round(ob, 2), heldout_after=round(ho[p], 2), max_corner_move_m=round(float(mv.max()), 2),
                         median_control_move_m=round(float(np.median(np.hypot(*(new - c['P']).T))), 2),
                         ties=sum(1 for t in ties if p in (t['a'], t['b']))))
        rows[-1]['rms_change'] = round(rows[-1]['rms_after'] - rows[-1]['rms_before'], 2)
        mf = (os.path.dirname(J.base_path(p)) + '/matches.json') if p != '22-38' else 'cuf38/matches38.json'
        M = json.load(open(SP + mf, encoding='utf8')); M = [q for q in M if q.get('osm')] if isinstance(M, list) else []
        for i in range(len(c['X'])):
            q = min(M, key=lambda q: np.hypot(q['x'] - c['X'][i][0], q['y'] - c['X'][i][1])) if M else None
            ctl_rows.append(dict(plate=p, x=round(float(c['X'][i][0]), 1), y=round(float(c['X'][i][1]), 1), crossing=f"{q['a']} & {q['b']}" if q else '',
                                 before_m=round(float(np.hypot(*(before[i] - c['O'][i]))), 2), after_m=round(float(after[i]), 2),
                                 moved_m=round(float(np.hypot(*(new[i] - c['P'][i]))), 2)))
    tinfo = []
    for k, t in enumerate(ties):
        na = F.world(sol, t['a'], t['xa'])[0] if t['a'] in FIT else t['Pa']
        nb = F.world(sol, t['b'], t['xb'])[0] if t['b'] in FIT else t['Pb']
        j = next(j for j, o in enumerate(F.obs) if o['t'] in ('t', 'g') and o['k'] == k)
        wt = W_GUT if t['sheet'] else float(sol['tw'][sol['tidx'].index(j)])
        tinfo.append(dict(a=t['a'], b=t['b'], street_1=t['street_1'], street_2=t['street_2'], before_m=t['before_m'],
                          after_m=round(float(np.hypot(*(nb - na))), 2), weight=round(wt, 3), sheet=t['sheet'], reread=t['reread']))
    gap1 = np.hypot(*(F.world(sol, '22-37L', pl) - F.world(sol, '22-37R', pr)).T)
    worse = [r['plate'] for r in rows if r['rms_change'] > r['limit']]
    summary = dict(plates=FIT, kinds=kinds, signs=signs, ties=len(ties), gutter_pairs=len(pr), gutter_weight=W_GUT,
                   gutter_gap_before=dict(median=round(float(np.median(gap0)), 2), max=round(float(gap0.max()), 2)),
                   gutter_gap_after=dict(median=round(float(np.median(gap1)), 2), p90=round(float(np.percentile(gap1, 90)), 2), max=round(float(gap1.max()), 2)),
                   worse_than_limit=worse, curl={p: curl_shape(F, sol, p) for p in FIT if kinds[p] == 'curl'})
    # what each of the five would do with curl (the system with that plate on curl, the others as chosen)
    alt_curl = {}
    for p in FIT:
        if kinds[p] == 'curl':
            continue
        alt = dict(kinds); alt[p] = 'curl'
        s2 = F.solve_best(alt, {q: s for q, s in signs.items() if alt[q] == 'curl'})
        nw = F.world(s2, p, C[p]['X'])
        alt_curl[p] = dict(heldout=round(F.heldout(s2, p), 2), rms=round(float(np.sqrt(np.mean(np.sum((nw - C[p]['O']) ** 2, 1)))), 2),
                           gap_median=round(float(np.median(np.hypot(*(F.world(s2, '22-37L', pl) - F.world(s2, '22-37R', pr)).T))), 2),
                           **curl_shape(F, s2, p))
    summary['alt_curl'] = alt_curl
    import scipy
    meta = dict(made=datetime.datetime.now().isoformat(timespec='seconds'), by='tools/sanborn/joint/local3.py', kinds_tried=KINDS, limits=LIMIT,
                gap_max=GAP_MAX, choice_trail=trail, tried={f'{a}|{b}|{c}': v for (a, b, c), v in tried.items()},
                versions=dict(numpy=np.__version__, scipy=scipy.__version__), sides=CU.SIDES,
                bases={p: dict(path=J.base_path(p), sha256=SV.sha(J.base_path(p))) for p in FIT}, overlap=LC.OVERLAP)
    log('choice done; the 21 plates alone ...')
    c21 = per_plate_21(sides, log=log)
    if write:
        for p in FIT:
            jp = J.joint_path(p, TAG); assert jp != J.base_path(p)
            d = F.model_dict(sol, p)
            d.update(base=J.base_path(p), base_sha256=SV.sha(J.base_path(p)), base_override=info[p]['base_override'],
                     solve=os.path.relpath(out, SP).replace('\\', '/'), made=meta['made'])
            pickle.dump(d, open(SP + jp, 'wb'))
        J._J.clear()
        chk = max(float(np.abs(J.world_many(p, C[p]['X'], TAG) - F.world(sol, p, C[p]['X'])).max()) for p in FIT)
        assert chk < 1e-6, chk
        S.READ.clear(); d_ = SP + f'reports/{today}_seams_{TAG}'
        S.main(['--models', TAG, d_]); S.MODELS = None
        sa = LC.seam_stats(json.load(open(d_ + '/seams.json', encoding='utf8'))['seams'], FIT)
        sb = LC.seam_stats(json.load(open(SP + 'reports/2026-11-06_seams_reread3/seams.json', encoding='utf8'))['seams'], FIT)
        verdict = dict(worse_plates=worse, gap_ok=summary['gutter_gap_after']['median'] < GAP_MAX,
                       median_falls=sa['touching']['median'] < sb['touching']['median'], p90_falls=sa['touching']['p90'] < sb['touching']['p90'])
        verdict['apply'] = not worse and verdict['gap_ok'] and verdict['median_falls'] and verdict['p90_falls']
        summary.update(seams_before=sb, seams_after=sa, part3_check=verdict,
                       seam_reports=['reports/2026-11-06_seams_reread3', f'reports/{today}_seams_{TAG}'])
    json.dump(dict(meta=meta, summary=summary, plates=rows, ties=tinfo, curl21=c21), open(out + '/solve.json', 'w', encoding='utf8', newline='\n'), indent=1, default=str)
    for name, data in (('plates.csv', rows), ('ties.csv', tinfo), ('controls.csv', ctl_rows), ('curl21.csv', c21)):
        with open(out + '/' + name, 'w', newline='', encoding='utf8') as f:
            wr = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n'); wr.writeheader(); wr.writerows(data)
    if write:
        write_readme(out, meta, summary, rows, tinfo, ctl_rows, c21, sides)
    print(json.dumps({k: v for k, v in summary.items()}, indent=1, default=str))
    for r in rows:
        print(r)


def write_readme(out, meta, summary, rows, tinfo, ctl_rows, c21, sides):
    v = summary['part3_check']; sb, sa = summary['seams_before'], summary['seams_after']
    g0, g1 = summary['gutter_gap_before'], summary['gutter_gap_after']
    L = [f"# Local fit with a page-curl option, {meta['made'][:10]}", '',
         "Ben's ruling (6 November): the plates are bound-book scans, so the distortion near a spine is page curl. A page-curl "
         'correction (`tools/sanborn/joint/curl.py`) is offered beside affine and thin plate; the five plates (33, 34R, 37L, 37R, 38) '
         'are fitted together, the other 16 fixed, with the 37L/37R gutter pairs as ties at weight 3. Method: `tools/sanborn/joint/local3.py` '
         '(its docstring). Nothing is applied by this report: the new models sit beside the old ones (`fwd_local3.pkl`, `cuf38/fwd38_local3.pkl`).', '',
         f"{summary['ties']} ties, {summary['gutter_pairs']} gutter pairs (weight {summary['gutter_weight']:g}). Gutter gap (the same paper point on "
         f"both halves): median {g0['median']} m, max {g0['max']} m before; median {g1['median']} m, 90% {g1['p90']} m, max {g1['max']} m after.", '',
         '## Part 3 check', '',
         f"- 33, 34R, 38 own control rms within 0.3 m of before, 37L and 37R within 0.5 m: **{'yes' if not v['worse_plates'] else 'no'}**"
         + (f" (over: {', '.join(v['worse_plates'])})" if v['worse_plates'] else ''),
         f"- Gutter gap median under {meta['gap_max']:g} m: **{'yes' if v['gap_ok'] else 'no'}** ({g1['median']} m)",
         f"- Plate-plate seam median across the five falls: **{'yes' if v['median_falls'] else 'no'}** ({sb['touching']['median']} to {sa['touching']['median']} m)",
         f"- Plate-plate seam 90% across the five falls: **{'yes' if v['p90_falls'] else 'no'}** ({sb['touching']['p90']} to {sa['touching']['p90']} m)",
         f"- So Part 3 {'goes ahead' if v['apply'] else '**does not** go ahead (stop after Part 2)'}.", '',
         "\"Before\" is each plate's own model on the same controls (the round-3 re-read pixel positions). Seams before: "
         f"`{summary['seam_reports'][0]}` (own models, re-read picks, wrong matches dropped); after: `{summary['seam_reports'][1]}`.", '',
         '## Gutter edges', '',
         '| Plate | Gutter edge | From | Fold line (px) |', '|---|---|---|---|']
    for p in FIT:
        sd = sides[p]; f = sd.get('fold')
        L.append(f"| {p} | {sd['side']} | {sd['how']} | {'x = %.0f %+.4f y' % (f[0], f[1]) if f else 'image edge'} |")
    L += ['', 'All 21 plates: `data/sanborn/joint/curl_sides.json`.', '',
          '## Per plate', '',
          'Rms: own controls, m. Held-out: leave-one-out rms (before: the plate\'s fit report). Curl s(0): the curl\'s shift at the gutter, px and m.', '',
          '| Plate | Own model | Correction | Curl s(0) | Curl k | Controls | Rms before | Rms after | Change | Limit | Held-out before | Held-out after | Max corner move m | Median control move m | Ties |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        s0 = f"{r['curl_s0_px']} px ({r['curl_s0_m']} m)" if r['correction'] == 'curl' else ''
        L.append(f"| {r['plate']} | {r['base_model']} | {r['correction']} | {s0} | {r['curl_k']} | {r['controls']} | {r['rms_before']} | {r['rms_after']} | "
                 f"{r['rms_change']:+.2f}{' **over**' if r['rms_change'] > r['limit'] else ''} | {r['limit']} | {r['heldout_before']} | {r['heldout_after']} | "
                 f"{r['max_corner_move_m']} | {r['median_control_move_m']} | {r['ties']} |")
    if summary['curl']:
        L += ['', 'Curl shape of the plates that took it (s at the knots, px; m per px across the gutter):', '']
        for p, c in summary['curl'].items():
            L.append(f"- {p}: s = {c['s_px']}, {c['m_per_px']} m/px, k = {c['k']}")
    if summary['alt_curl']:
        L += ['', 'The plates that did not take curl, with curl forced (the others as chosen):', '',
              '| Plate | Held-out with curl | Own rms with curl | Gutter gap median | s(0) px |', '|---|---|---|---|---|']
        for p, c in summary['alt_curl'].items():
            L.append(f"| {p} | {c['heldout']} | {c['rms']} | {c['gap_median']} | {c['s_px'][0]} |")
    worse = v['worse_plates']
    if worse:
        L += ['', '## The controls of the plates over their limit', '', '| Plate | Crossing | Pixel | Before m | After m | Moved m |', '|---|---|---|---|---|---|']
        for c in sorted([c for c in ctl_rows if c['plate'] in worse], key=lambda c: (c['plate'], -c['after_m'])):
            L.append(f"| {c['plate']} | {c['crossing']} | ({c['x']:.0f}, {c['y']:.0f}) | {c['before_m']} | {c['after_m']} | {c['moved_m']} |")
    L += ['', '## Seams', '', '| Plate-plate seams | | Shared | Median m | 90% m | Max m | > 10 m | > 20 m |', '|---|---|---|---|---|---|---|---|']
    for key, lab in (('touching', 'touching the five'), ('within', 'among the five'), ('all', 'all plates')):
        for when, d in (('before', sb[key]), ('after', sa[key])):
            L.append(f"| {lab} | {when} | {d['n']} | {d.get('median', '')} | {d.get('p90', '')} | {d.get('max', '')} | {d.get('over_10m', '')} | {d.get('over_20m', '')} |")
    for when, d in (('before', sb['plate_1904_touching']), ('after', sa['plate_1904_touching'])):
        L.append(f"| plate-1904, the five | {when} | {d['n']} | {d.get('median', '')} | {d.get('p90', '')} | {d.get('max', '')} | {d.get('over_10m', '')} | {d.get('over_20m', '')} |")
    L += ['', '## Ties, widest after the fit', '', '| Plates | Crossing | Before m | After m | Weight |', '|---|---|---|---|---|']
    for t in sorted(tinfo, key=lambda t: -t['after_m'])[:15]:
        L.append(f"| {t['a']} / {t['b']} | {t['street_1']} & {t['street_2']} | {t['before_m']} | {t['after_m']} | {t['weight']}{' (gutter)' if t['sheet'] else ''} |")
    L += ['', '## Curl as an option for every plate alone (read-only)', '',
          'Each of the 21 plates on its own controls only (its fit picks, no ties), the correction chosen among affine, affine + curl and '
          'thin plate by held-out error. Gain: held-out of the best choice without curl minus held-out with curl (positive: curl is better). '
          'Nothing written but this table (`curl21.csv`).', '',
          '| Plate | Own model | Own held-out | Controls | Within 500 px of the gutter | Gutter edge | From | Best without curl | Held-out | With curl | Gain m | Would pick | s(0) px | k |',
          '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for r in c21:
        L.append(f"| {r['plate']} | {r['own_model']} | {r['own_heldout'] if r['own_heldout'] is not None else '-'} | {r['controls']} | {r['controls_within_500px']} | {r['gutter_edge']} | {r['edge_from']} | "
                 f"{r['best_without_curl']} | {r['heldout_without_curl']} | {r['heldout_curl']} | {r['heldout_gain_m']:+.2f} | "
                 f"{'**curl**' if r['picks_curl'] else r['picks']} | {r['curl_s0_px']} | {r['curl_k']} |")
    big = [r for r in c21 if abs(r['curl_s0_px']) > 500]
    if big:
        L += ['', 'Read the s(0) column with the "within 500 px" one: the value of the spline at the gutter is set only by the controls close to it, '
              'so where few or none lie there it can take sizes no page curls by (' + ', '.join(f"{r['plate']} {r['curl_s0_px']} px" for r in big)
              + '). A held-out gain from such a curl rests on a handful of controls near the edge.']
    pc = [r['plate'] for r in c21 if r['picks_curl']]
    L += ['', f"Would pick curl: {', '.join(pc) if pc else 'none'}"
          + (f" (held-out gain {', '.join(str(r['heldout_gain_m']) for r in c21 if r['picks_curl'])} m)." if pc else '.'), '',
          f"Choice trail (the five): {meta['choice_trail'] or 'affine kept'}. Computed with numpy {meta['versions']['numpy']}, scipy {meta['versions']['scipy']}.", '']
    open(out + '/README.md', 'w', encoding='utf8', newline='\n').write('\n'.join(L))


if __name__ == '__main__':
    main()
