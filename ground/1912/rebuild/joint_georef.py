"""Stage registration, step 2: joint solve of the sheets' correction.

ground = start(p) + D(start(p)), D a smoothing thin-plate spline in ground metres, fitted robustly (changed streets
drop out) to the street controls of all 48 sheets at once. Default: one D shared by every sheet (solve_global), which
keeps the start model's exact agreement along shared neatlines. --per-sheet: a D per sheet tied together by seam
points re-targeted each round (solve); it fits held-out controls no better and opens seams up to 0.3 m.
Writes georef/<sid>.json; seam rms is measured on the shared neatlines every 50 ft.
"""
import json, sys
from pathlib import Path
import numpy as np

from common import load_paths, load_all, frame_px, neighbours
from georef_model import TPS, Sheet

LAM = 0.05          # TPS smoothing (relative to the r^2 log r kernel at 1 km scale)
W_SEAM = 4.0        # weight of a seam tie relative to one control
TIE_FT = 200.0      # tie spacing along a shared edge
CHECK_FT = 50.0     # seam-check spacing
ROUNDS = 25
DROP_M = 8.0        # controls further than this from the fit are dropped outright


def edge_points(kind, fixed, lo, hi, step):
    t = np.arange(lo + step / 2, hi, step)
    return (np.full(len(t), fixed), t) if kind == 'x' else (t, np.full(len(t), fixed))


def load_controls(P, ids):
    W = Path(P['work']) / 'controls'
    pk = json.load(open(W / 'picks12.json')) if (W / 'picks12.json').exists() else {}
    C = {}
    for sid in ids:
        d = json.load(open(W / f'{sid}.json'))
        c = [x for x in d['candidates'] if x['ok']] + pk.get(sid, [])
        C[sid] = c
    return C


def solve(P, ids, C, lam=LAM, rounds=ROUNDS, verbose=True):
    nb = neighbours(ids)
    # control base positions under the start model
    base = {}; tgt = {}; w = {}
    for sid in ids:
        c = C[sid]
        if c:
            px = np.array([x['px'] for x in c]); E, N = ids[sid]['start'].p2utm(px[:, 0], px[:, 1])
            base[sid] = np.c_[E, N]; tgt[sid] = np.array([x['xy'] for x in c], float)
        else:
            base[sid] = np.zeros((0, 2)); tgt[sid] = np.zeros((0, 2))
        w[sid] = np.where(np.array([x['source'] == 'picks12' for x in c], bool), 2.0, 1.0) if c else np.zeros(0)
    # seam ties: ground position of each tie under each sheet's start model
    ties = []   # (a, b, Ga, Gb)
    for a, b, kind, fixed, lo, hi in nb:
        gx, gy = edge_points(kind, fixed, lo, hi, TIE_FT)
        ua, va = ids[a]['start'].g2p(gx, gy); ub, vb = ids[b]['start'].g2p(gx, gy)
        Ga = np.c_[ids[a]['start'].p2utm(ua, va)]; Gb = np.c_[ids[b]['start'].p2utm(ub, vb)]
        ties.append((a, b, Ga, Gb))
    D = {sid: TPS() for sid in ids}
    rw = {sid: w[sid].copy() for sid in ids}
    for it in range(rounds):
        # seam targets from the current fit
        tie_pts = {sid: [] for sid in ids}; tie_tgt = {sid: [] for sid in ids}
        for a, b, Ga, Gb in ties:
            Fa = Ga + D[a](Ga); Fb = Gb + D[b](Gb); mid = (Fa + Fb) / 2
            tie_pts[a].append(Ga); tie_tgt[a].append(mid - Ga)
            tie_pts[b].append(Gb); tie_tgt[b].append(mid - Gb)
        newD = {}
        for sid in ids:
            xy = [base[sid]]; dd = [tgt[sid] - base[sid]]; ww = [rw[sid]]
            if tie_pts[sid]:
                xy += tie_pts[sid]; dd += tie_tgt[sid]; ww += [np.full(len(x), W_SEAM) for x in tie_pts[sid]]
            xy = np.vstack(xy); dd = np.vstack(dd); ww = np.concatenate(ww)
            keep = ww > 0
            newD[sid] = TPS.fit(xy[keep], dd[keep], ww[keep], lam)
        D = newD
        # robust re-weighting of controls
        tot = []
        for sid in ids:
            if not len(base[sid]):
                continue
            r = np.hypot(*(base[sid] + D[sid](base[sid]) - tgt[sid]).T)
            s = max(1.4826 * np.median(r), 1.0)
            c = 4.685 * s
            rw[sid] = np.where(r < min(c, DROP_M), w[sid] * (1 - (r / c) ** 2) ** 2, 0.0)
            tot.append(r[rw[sid] > 0])
        if verbose and (it % 5 == 4 or it == rounds - 1):
            sr = seam_stats(ids, D, nb)
            allr = np.concatenate(tot)
            print(f'round {it + 1}: control rms {np.sqrt(np.mean(allr ** 2)):.2f} m (n {len(allr)}), '
                  f'seam rms worst {max(v["rms_m"] for v in sr):.2f} m, median {np.median([v["rms_m"] for v in sr]):.2f} m', flush=True)
    return D, rw, base, tgt, nb


def solve_global(P, ids, C, lam=LAM, rounds=8):
    """One smoothing TPS for the whole survey, fitted robustly to every sheet's controls. The start model is already
    seamless along shared neatlines, and one shared correction keeps it so; held-out error 2.52 m against 2.58 m for
    per-sheet corrections (5-fold, 6 November)."""
    nb = neighbours(ids)
    base = {}; tgt = {}; w = {}
    for sid in ids:
        c = C[sid]
        if c:
            px = np.array([x['px'] for x in c]); E, N = ids[sid]['start'].p2utm(px[:, 0], px[:, 1])
            base[sid] = np.c_[E, N]; tgt[sid] = np.array([x['xy'] for x in c], float)
            w[sid] = np.where(np.array([x['source'] == 'picks12' for x in c], bool), 2.0, 1.0)
        else:
            base[sid] = np.zeros((0, 2)); tgt[sid] = np.zeros((0, 2)); w[sid] = np.zeros(0)
    keys = [s for s in sorted(ids) if len(base[s])]
    B = np.vstack([base[s] for s in keys]); T = np.vstack([tgt[s] for s in keys]); W0 = np.concatenate([w[s] for s in keys])
    Wt = W0.copy()
    for it in range(rounds):
        k = Wt > 0
        t = TPS.fit(B[k], T[k] - B[k], Wt[k], lam)
        r = np.hypot(*(B + t(B) - T).T); c = 4.685 * max(1.4826 * np.median(r), 1.0)
        Wt = np.where(r < min(c, DROP_M), W0 * (1 - (r / c) ** 2) ** 2, 0.0)
        print(f'round {it + 1}: control rms {np.sqrt(np.mean(r[Wt > 0] ** 2)):.2f} m (n {(Wt > 0).sum()} of {len(r)})', flush=True)
    D = {sid: t for sid in ids}
    rw = {}; i = 0
    for s in sorted(ids):
        n = len(base[s]); rw[s] = Wt[i:i + n] if s in keys else np.zeros(0); i += n if s in keys else 0
    return D, rw, base, tgt, nb


def seam_stats(ids, D, nb):
    out = []
    for a, b, kind, fixed, lo, hi in nb:
        gx, gy = edge_points(kind, fixed, lo, hi, CHECK_FT)
        ua, va = ids[a]['start'].g2p(gx, gy); ub, vb = ids[b]['start'].g2p(gx, gy)
        Ga = np.c_[ids[a]['start'].p2utm(ua, va)]; Gb = np.c_[ids[b]['start'].p2utm(ub, vb)]
        e = np.hypot(*((Ga + D[a](Ga)) - (Gb + D[b](Gb))).T)
        e0 = np.hypot(*(Ga - Gb).T)
        out.append(dict(a=a, b=b, rms_m=float(np.sqrt(np.mean(e ** 2))), max_m=float(e.max()), start_rms_m=float(np.sqrt(np.mean(e0 ** 2))), n=len(e)))
    return out


def loo_cv(P, ids, C, lams, folds=5):
    """K-fold check of the smoothing: hold out a fifth of each sheet's controls, refit, measure."""
    rng = np.random.default_rng(12)
    for lam in lams:
        errs = []
        for k in range(folds):
            Ck = {}; held = {}
            for sid, c in C.items():
                f = rng.integers(0, folds, len(c)) if k == 0 or sid not in held else None
                f = np.arange(len(c)) % folds
                Ck[sid] = [x for x, ff in zip(c, f) if ff != k]; held[sid] = [x for x, ff in zip(c, f) if ff == k]
            D, rw, *_ = solve(P, ids, Ck, lam=lam, rounds=10, verbose=False)
            for sid, h in held.items():
                if not h:
                    continue
                px = np.array([x['px'] for x in h]); E, N = ids[sid]['start'].p2utm(px[:, 0], px[:, 1]); b = np.c_[E, N]
                errs.append(np.hypot(*(b + D[sid](b) - np.array([x['xy'] for x in h])).T))
        e = np.concatenate(errs)
        print(f'lam {lam}: held-out median {np.median(e):.2f} m, p75 {np.percentile(e, 75):.2f} m', flush=True)


def write(P, ids, meta, C, D, rw, base, tgt, nb, outdir):
    out = Path(outdir); (out / 'georef').mkdir(parents=True, exist_ok=True)
    seams = seam_stats(ids, D, nb)
    start_json = json.load(open(P['georef_start']))
    report = {}
    for sid, d in ids.items():
        c = C[sid]; res = np.hypot(*(base[sid] + D[sid](base[sid]) - tgt[sid]).T) if c else np.zeros(0)
        used = rw[sid] > 0
        ctrl = [dict(px=[round(x['px'][0], 2), round(x['px'][1], 2)], xy=[round(x['xy'][0], 2), round(x['xy'][1], 2)],
                     name=x['name'], source=x['source'], residual_m=round(float(r), 3))
                for x, r, u in zip(c, res, used) if u]
        rms = float(np.sqrt(np.average(res[used] ** 2))) if used.any() else None
        m = start_json[d['num']]
        fwd = {'start': {'description': 'I4 joint transform (georef_1912.json), unchanged: grid g0 = CoonsInverse(p); '
                                         'q = p + 2*(J.F(g0) + S(p/2 - (u0, v0))); grid = CoonsInverse(q) (feet); '
                                         'ground = AEQD(origin, WGS84) -> EPSG:26916',
                         'origin_lat': meta['origin_lat'], 'origin_lon': meta['origin_lon'], 'foot_m': meta['foot_m'],
                         'F': meta['F'], 'shape_basis': meta['shape_basis'],
                         **{k: m[k] for k in ('x_w', 'x_e', 'y_n', 'y_s', 'corners', 'H_grid_to_px', 'neatline_offsets_px',
                                              'neatline_normals', 'J', 'u0', 'v0', 'W', 'H', 'shape_x', 'shape_y')},
                         'neatline_t': 'neatline offsets sampled at t = linspace(0, 1, 401) along each edge'},
               'correction': {'description': 'ground = start(p) + D(start(p)); D is this thin-plate spline (metres)',
                              **D[sid].to_json()}}
        sr = {s['b'] if s['a'] == sid else s['a']: round(s['rms_m'], 3) for s in seams if sid in (s['a'], s['b'])}
        g = dict(sheet=sid, file=d['file'], survey_sheet=int(d['num']), model='tps', controls=ctrl, forward=fwd,
                 rms_m=None if rms is None else round(rms, 3), seam_rms_m=sr,
                 controls_rejected=int((~used).sum()), lambda_=LAM)
        json.dump(g, open(out / 'georef' / f'{sid}.json', 'w'), indent=0)
        report[sid] = dict(controls=int(used.sum()), rms_m=None if rms is None else round(rms, 3))
    json.dump(dict(sheets=report, seams=seams), open(Path(P['work']) / 'registration_report.json', 'w'), indent=1)
    return report, seams


if __name__ == '__main__':
    paths = sys.argv[1] if len(sys.argv) > 1 else 'configs/ground_paths.json'
    outdir = sys.argv[2] if len(sys.argv) > 2 else 'ground/1912'
    P = load_paths(paths); ids, meta = load_all(P); C = load_controls(P, ids)
    print('controls per sheet:', {s: len(c) for s, c in C.items()})
    if '--cv' in sys.argv:
        loo_cv(P, ids, C, [0.005, 0.05, 0.5, 5.0]); sys.exit()
    D, rw, base, tgt, nb = solve(P, ids, C) if '--per-sheet' in sys.argv else solve_global(P, ids, C)
    report, seams = write(P, ids, meta, C, D, rw, base, tgt, nb, outdir)
    print('worst seams:', sorted(((round(s['rms_m'], 2), s['a'], s['b']) for s in seams), reverse=True)[:8])
