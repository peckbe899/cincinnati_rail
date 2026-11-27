"""Two-fold check of dittofix's thresholds (26 Nov 2026). DEV ONLY (reads the dev truth through harness.py).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/fix_ditto/code/folds.py [OUT.json]

The dev windows are split by plate into fold A and fold B (devdata.FOLD_A / FOLD_B, balanced by scale and by ditto
words). For each fold, a grid of thresholds is scored on that fold only, and the best setting is then scored on the
other fold. The objective is the pooled pixel F1 over the fold's windows: the ditto crops' scopes, the T1-T7 crops of
the fold's plates and the negative windows (so a change that calls non-text ink text costs precision there).
The rules themselves (which features, which routes) were designed by looking at all dev plates and at whole-plate samples
(see the report); only the numbers below are tuned per fold.
"""
import os, sys, json, itertools, time
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import harness as H, dittofix as DF, devdata as D

GRID = dict(fig_m=(0.0, 0.75, 1.0, 1.25), sp_on=(False, True), s_Amin_d=(-2, 0, 4), s_ppair=(0, 1), min_paper=(1.9, 2.3, 2.9), L_dark=(80, 90, 100))


def params(g, ft):
    base = dict(DF.COMMON, **DF.P[ft])
    p = dict(Rfig=(base['Rfig'] or DF.P[200]['Rfig'] * {100: 60 / 45, 400: 40 / 45}[ft]) * g['fig_m'], s_ppair=g['s_ppair'], min_paper=g['min_paper'], L_dark=g['L_dark'],
             s_Amin=base['s_Amin'] + g['s_Amin_d'])
    p['sp_on'] = g['sp_on'] if ft != 400 else False
    return p


def pooled(res, fold):
    tp = fp = fn = 0
    for r in res.values():
        if r['fold'] != fold: continue
        tp += r['tp']; fp += r['fp']; fn += r['fn']
    P = tp / max(1, tp + fp); R = tp / max(1, tp + fn); return 2 * P * R / max(1e-9, P + R)


def run_grid(data, fold):
    keys = list(GRID); best = None; rows = []
    for vals in itertools.product(*(GRID[k] for k in keys)):
        g = dict(zip(keys, vals))
        acc = {N: DF.decide(d['M'], d['ft'], params(g, d['ft'])) for N, d in data.items() if D.fold(N) == fold}
        res = H.evaluate(data, acc, plates=set(acc))
        f = pooled(res, fold); rows.append((f, g))
        if best is None or f > best[0] + 1e-12: best = (f, g)
    return best, rows


if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'scores', 'folds.json')
    data = H.load_all(); t0 = time.time()
    default = {k: None for k in GRID}
    R = {}
    for fold, other in (('A', 'B'), ('B', 'A')):
        best, rows = run_grid(data, fold)
        g = best[1]
        acc = {N: DF.decide(d['M'], d['ft'], params(g, d['ft'])) for N, d in data.items()}
        res = H.evaluate(data, acc)
        R[f'tuned_on_{fold}'] = dict(grid_best=g, objective_own=round(best[0], 4), objective_other=round(pooled(res, other), 4),
                                     own=H.summary(res, fold), other=H.summary(res, other), n_grid=len(rows))
        print(f'tuned on {fold}: {g}  own F1 {best[0]:.4f}  other ({other}) F1 {pooled(res, other):.4f}', flush=True)
    acc = {N: DF.decide(d['M'], d['ft']) for N, d in data.items()}; res = H.evaluate(data, acc)
    R['hand_set'] = dict(A=H.summary(res, 'A'), B=H.summary(res, 'B'), objective_A=round(pooled(res, 'A'), 4), objective_B=round(pooled(res, 'B'), 4))
    base = H.evaluate(data, {})
    R['finder3'] = dict(A=H.summary(base, 'A'), B=H.summary(base, 'B'), objective_A=round(pooled(base, 'A'), 4), objective_B=round(pooled(base, 'B'), 4))
    print('hand-set: A', R['hand_set']['objective_A'], 'B', R['hand_set']['objective_B'], '| finder3: A', R['finder3']['objective_A'], 'B', R['finder3']['objective_B'])
    print(f'{time.time() - t0:.0f} s')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    json.dump(R, open(out, 'w', encoding='utf8', newline='\n'), indent=1, default=str)
