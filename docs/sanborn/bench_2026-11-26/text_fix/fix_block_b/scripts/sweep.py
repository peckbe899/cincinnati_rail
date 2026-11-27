"""Choose blockfix's settings on ONE fold's dev crops (that fold's models: classifier, templates, number model), then
score the chosen settings on the OTHER fold with the same models.
    python -B .../scripts/sweep.py FOLD OUT.json
Objective on the tuning fold: pooled in-scope F1 of the dev block crops; within 0.001 of the best, the strictest
number model (fewer numbers kept where no block number was surveyed), then block recall. Every setting's numbers
are kept in OUT.json."""
import sys, os, json, subprocess, itertools
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import bfcommon as C

fold, outp = sys.argv[1], sys.argv[2]; other = 'B' if fold == 'A' else 'A'
S = os.path.join(C.ROOT, 'scripts'); M = os.path.join(C.ROOT, 'models')
grid = dict(pnum=[0.3, 0.4, 0.5, 0.6], core_pad=[0.0, 1.0])
res = []


def run(plates, opts, tag):
    od = os.path.join(C.ROOT, 'runs', 'sweep', tag)
    o = ','.join(f'{k}={v}' for k, v in opts.items())
    subprocess.run([sys.executable, '-B', os.path.join(S, 'run_fold.py'), od, fold, f'real_{fold}'] + plates + ['--opt', o], check=True, capture_output=True, cwd=C.DS)
    for N in C.FOLD['A'] + C.FOLD['B']:      # the scorer needs every dev plate: the other fold's plates stay finder3's
        if not os.path.exists(os.path.join(od, f'{N}_text.png')):
            import shutil; shutil.copy(C.f3_path(N), os.path.join(od, f'{N}_text.png'))
    js = os.path.join(od, 'score.json')
    subprocess.run([sys.executable, '-B', os.path.join(S, 'score_all.py'), od, js, '--quick'], check=True, capture_output=True, cwd=C.DS)
    return json.load(open(js))


for vals in itertools.product(*grid.values()):
    opts = dict(zip(grid.keys(), vals)); opts['num_model'] = os.path.join(M, f'num_{fold}.npz')
    tag = f'{fold}_' + '_'.join(f'{k}{v}' for k, v in zip(grid.keys(), vals))
    sc = run(C.FOLD[fold], opts, tag)[f'block{fold}']
    res.append(dict(opts={k: v for k, v in opts.items() if k != 'num_model'}, F1=sc['F1'], block=sc['block'], nontext=sc['nontext_called_text']))
    print(tag, sc['F1'], sc['block'], sc['nontext_called_text'], flush=True)
top = max(r['F1'] for r in res)   # within 0.001 of the best F1, take the strictest number model, then the higher recall
best = max([r for r in res if r['F1'] >= top - 0.001], key=lambda r: (r['opts']['pnum'], r['block']['recall']))
print('chosen on fold', fold, best)
opts = dict(best['opts']); opts['num_model'] = os.path.join(M, f'num_{fold}.npz')
full = run(C.FOLD[other], opts, f'{fold}_chosen_on_{other}')
json.dump(dict(fold=fold, grid=grid, results=res, chosen=best, scored_on=other, score_other=full[f'block{other}'], straight_runs=full['straight_runs_dev']), open(outp, 'w'), indent=1)
print('scored on fold', other, full[f'block{other}']['block'], 'F1', full[f'block{other}']['F1'], 'nontext', full[f'block{other}']['nontext_called_text'])
