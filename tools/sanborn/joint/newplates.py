"""New plates onto the applied 1922 layer (Ben, 8 November 2026: plates 25 and 28, batch 1; docs/sanborn/RULES.md rule 12).

    cd data/sanborn
    python ../../tools/sanborn/joint/newplates.py 22-25 22-28 [--write]

Each new plate is a thin-plate spline from plate pixel to world (tools/sanborn/joint/complete.py's model, kind
'tps_px') on its complete picks matched to OSM (cufp/<N>/fwd.pkl X -> O as cufp/fit.py matched them, rule 4's tests
applied there), the smoothing chosen by exact held-out error over complete.LAMS. The new plates are solved together:
- their controls, weight 1;
- ties to every plate already applied (the crossing on the new plate = the same crossing on the other plate, placed
  by its applied model, held fixed): tools/sanborn/seams.py matching over the hand picks (street names, within 45 m),
  Huber weights (k = 6 m, iterated);
- ties between the new plates themselves (both free), Huber as above.
Damping (complete2.py: the thin-plate part faded to the plate's affine over 300 px outside its controls' hull) only for
a plate whose image corner would otherwise move more than 10 m from its own name-seeded fit (cufp/<N>/fwd.pkl).

The applied models are the page's (data/sanborn/apply/apply.py TAGS: fwd_complete, fwd_local3 for 37L/37R).
Writes data/sanborn/reports/<date>_newplates/ (README.md, plates.csv, ties.csv, solve.json) and, with --write, each new
plate's model as cufp/<N>/fwd_complete.pkl (jointlib joint_path(pid, 'complete')) and the seam report over the applied
state with the new plates (reports/<date>_seams_newplates).
"""
import csv, datetime, json, os, pickle, sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import _ws  # noqa: E402

SP = _ws.DATA
sys.path.insert(0, SP + 'apply')
import apply as AP  # noqa: E402  (routing to the applied models)
import complete as CP  # noqa: E402
import complete2 as C2  # noqa: E402

J, S, SV = CP.J, CP.S, CP.SV
CORNER_M = 10.0
TAG = 'complete'


class Sys:
    def __init__(self, new, C, ties, damp):
        self.new, self.C, self.ties = new, C, ties
        self.M = {p: (C2.Plate(C[p]['X']) if damp.get(p) else CP.Plate(C[p]['X'])) for p in new}
        if not any(damp.values()):
            pass
        self.off = {}; o = 0
        for p in new:
            self.off[p] = o; o += self.M[p].k
        self.n = o
        A, Y, kind = [], [], []
        for p in new:
            D = self.M[p].design(C[p]['X'])
            for i in range(len(D)):
                r = np.zeros(self.n); r[self.off[p]:self.off[p] + D.shape[1]] = D[i]
                A.append(r); Y.append(C[p]['O'][i] - CP.ORIGIN); kind.append(('c', p, i))
        for t, T in enumerate(ties):
            r = np.zeros(self.n); y = np.zeros(2)
            ra = self.M[T['a']].design(np.array([T['xa']]))[0]; r[self.off[T['a']]:self.off[T['a']] + len(ra)] = ra
            if T['b'] in self.M:
                rb = self.M[T['b']].design(np.array([T['xb']]))[0]; r[self.off[T['b']]:self.off[T['b']] + len(rb)] -= rb
            else:
                y = np.asarray(T['Pb'], float) - CP.ORIGIN       # the applied plate's position, held fixed
            A.append(r); Y.append(y); kind.append(('t', t, False))
        self.A, self.Y, self.kind = np.array(A), np.array(Y), kind
        self.cidx = {p: [i for i, k in enumerate(kind) if k[0] == 'c' and k[1] == p] for p in new}
        self.tidx = [i for i, k in enumerate(kind) if k[0] == 't']
        self.plates = new
        self.Pen = {}
        for p in new:
            m = self.M[p]; Rm = np.zeros((m.R.shape[0], self.n)); Rm[:, self.off[p] + 3:self.off[p] + m.k] = m.R
            self.Pen[p] = Rm.T @ Rm

    weights = CP.System.weights
    solve = CP.System.solve
    heldout = CP.System.heldout
    world = CP.System.world

    def model_dict(self, sol, p):
        return (C2.System.model_dict if isinstance(self.M[p], C2.Plate) else CP.System.model_dict)(self, sol, p)


def setup(new):
    C = {}
    for p in new:
        d = pickle.load(open(SP + J.base_path(p), 'rb'))
        X, O = np.asarray(d['X'], float), np.asarray(d['O'], float)
        uniq = np.ones(len(X), bool)
        for i in range(len(X)):
            if uniq[i]:
                same = (np.hypot(*(X - X[i]).T) < 1.0) & (np.hypot(*(O - O[i]).T) < 1.0); same[:i + 1] = False; uniq[same] = False
        C[p] = dict(X=X[uniq], O=O[uniq], own=lambda q, pid=p: J.base_many(pid, q), fit=d['model'])
    return C


def ties_for(new, own):
    """crossings a new plate shares with another plate (seams.py matching over the hand picks), the other plate placed by
    its applied model; new-new pairs both free"""
    AP.install()
    import seams as S2
    recs = []
    for p in S2.plate_ids():
        if p in new:
            continue
        recs += S2.plate_crossings(p)[0]
    for p in new:                         # the new plates' crossings placed by their own (name-seeded) fit, for the matching
        r, _ = S2.plate_crossings(p)
        for q in r:
            E, N = own[p](np.array([[q['x'], q['y']]]))[0]; q.update(E=float(E), N=float(N))
        recs += r
    near, _ = S2.pairs(recs)
    ties = []
    for i, j, d in near:
        a, b = recs[i], recs[j]
        if b['kind'] != 'plate' or not (a['src'] in new or b['src'] in new):
            continue
        if a['src'] not in new:
            a, b = b, a
        ties.append(dict(a=a['src'], b=b['src'], xa=[a['x'], a['y']], xb=[b['x'], b['y']], Pb=[b['E'], b['N']],
                         street_1=a['a'], street_2=a['b'], before_m=round(float(d), 2)))
    return ties


def choose(F, log):
    lams = {p: CP.LAM0 for p in F.plates}
    sol = F.solve(lams); tw = sol['tw']
    for ps in range(2):
        for p in F.plates:
            best = min(((CP.rms(F.heldout(F.solve(dict(lams, **{p: lam}), tw, iterate=False), p)), lam) for lam in CP.LAMS))
            lams[p] = best[1]; log(f'pass {ps + 1} {p}: lam {best[1]} held-out {best[0]:.2f}')
        sol = F.solve(lams, tw); tw = sol['tw']
    return lams, F.solve(lams, tw)


def main():
    new = [a for a in sys.argv[1:] if a.startswith('22-')]
    write = '--write' in sys.argv
    today = datetime.date.today().isoformat()
    out = SP + f'reports/{today}_newplates'; os.makedirs(out, exist_ok=True)
    log = lambda s: print(s, flush=True)
    C = setup(new)
    ties = ties_for(new, {p: C[p]['own'] for p in new})
    log(f"controls { {p: len(C[p]['X']) for p in new} }, ties {len(ties)}: " + str({p: sum(1 for t in ties if p in (t['a'], t['b'])) for p in new}))
    damp = {p: False for p in new}
    for rnd in range(2):
        F = Sys(new, C, ties, damp)
        lams, sol = choose(F, log)
        mv = {}
        for p in new:
            w, h = SV.plate_size(p); cn = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
            mv[p] = np.hypot(*(F.world(sol, p, cn) - C[p]['own'](cn)).T)
        more = [p for p in new if mv[p].max() > CORNER_M and not damp[p]]
        if not more:
            break
        for p in more:
            damp[p] = True
        log(f'corner over {CORNER_M} m on {more}: damped and solved again')
    rows, tinfo = [], []
    for p in new:
        c = C[p]; nw = F.world(sol, p, c['X']); own = np.hypot(*(nw - c['O']).T); ho = F.heldout(sol, p)
        rows.append(dict(plate=p, controls=len(c['X']), name_seeded_fit=c['fit'], lam=lams[p], damped=damp[p], own_rms=round(CP.rms(own), 2),
                         heldout=round(CP.rms(ho), 2), heldout_max=round(float(ho.max()), 2), max_corner_move_m=round(float(mv[p].max()), 2),
                         corner_moves_m=[round(float(v), 1) for v in mv[p]], ties=sum(1 for t in ties if p in (t['a'], t['b'])),
                         tie_partners=sorted({t['b'] if t['a'] == p else t['a'] for t in ties if p in (t['a'], t['b'])})))
    for k, t in enumerate(ties):
        na = F.world(sol, t['a'], np.array([t['xa']]))[0]
        nb = F.world(sol, t['b'], np.array([t['xb']]))[0] if t['b'] in new else np.asarray(t['Pb'])
        tinfo.append(dict(a=t['a'], b=t['b'], street_1=t['street_1'], street_2=t['street_2'], before_m=t['before_m'],
                          after_m=round(float(np.hypot(*(nb - na))), 2), weight=round(float(sol['tw'][k]), 3)))
    summary = dict(plates=rows, ties=len(ties))
    if write:
        for p in new:
            jp = J.joint_path(p, TAG); assert jp != J.base_path(p)
            d = F.model_dict(sol, p)
            d.update(controls_X=C[p]['X'].tolist(), controls_O=C[p]['O'].tolist(), base=J.base_path(p), solve=os.path.relpath(out, SP).replace('\\', '/'))
            pickle.dump(d, open(SP + jp, 'wb'))
        J._J.clear()
        chk = max(float(np.abs(J.world_many(p, C[p]['X'], TAG) - F.world(sol, p, C[p]['X'])).max()) for p in new)
        assert chk < 1e-6, chk
        import seams as S2
        S2.READ.clear()
        d_ = SP + f'reports/{today}_seams_newplates'
        S2.main([d_])
        rows_s = json.load(open(d_ + '/seams.json', encoding='utf8'))['seams']
        before = json.load(open(SP + 'reports/2026-11-07_seams_applied/seams.json', encoding='utf8'))['seams']
        nb = sorted({r['b_src'] if r['a_src'] in new else r['a_src'] for r in rows_s if r['within_45m'] and r['seam'] == 'plate-plate' and (r['a_src'] in new) != (r['b_src'] in new)})
        per = {}
        for q in nb:
            def st(R, q=q):
                dd = [r['dist_m'] for r in R if r['within_45m'] and r['seam'] == 'plate-plate' and q in (r['a_src'], r['b_src'])]
                return dict(n=len(dd), median=round(float(np.median(dd)), 2) if dd else None)
            per[q] = dict(before=st(before), after=st(rows_s),
                          with_new=[dict(new=p, **(lambda dd: dict(n=len(dd), median=round(float(np.median(dd)), 2) if dd else None, max=round(float(max(dd)), 2) if dd else None))(
                              [r['dist_m'] for r in rows_s if r['within_45m'] and {r['a_src'], r['b_src']} == {p, q}])) for p in new])
        newnew = [r['dist_m'] for r in rows_s if r['within_45m'] and {r['a_src'], r['b_src']} == set(new)]
        summary['seams'] = dict(dir=os.path.relpath(d_, SP).replace('\\', '/'), neighbours=per,
                                new_pair=dict(n=len(newnew), median=round(float(np.median(newnew)), 2) if newnew else None, max=round(float(max(newnew)), 2) if newnew else None))
        gate = dict(heldout_under_5m=all(r['heldout'] < 5.0 for r in rows),
                    neighbour_median_not_worse={q: (v['before']['median'] is None or v['after']['median'] is None or v['after']['median'] <= v['before']['median']) for q, v in per.items()})
        gate['build'] = gate['heldout_under_5m'] and all(gate['neighbour_median_not_worse'].values())
        summary['gate'] = gate
    json.dump(dict(made=datetime.datetime.now().isoformat(timespec='seconds'), summary=summary, ties=tinfo), open(out + '/solve.json', 'w', encoding='utf8', newline='\n'), indent=1, default=str)
    for name, data in (('plates.csv', rows), ('ties.csv', tinfo)):
        with open(out + '/' + name, 'w', newline='', encoding='utf8') as f:
            w = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator='\n'); w.writeheader(); w.writerows(data)
    print(json.dumps(summary, indent=1, default=str))


if __name__ == '__main__':
    main()
