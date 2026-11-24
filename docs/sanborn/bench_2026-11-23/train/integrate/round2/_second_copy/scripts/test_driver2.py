"""Integrator, round 2 (24 Nov 2026): the staged driver train_v2.py after the review fixes, on made-up files in
integrate/round2/driver_test/. Nothing is trained or evaluated: the driver's runner is replaced by stubs.
Checks review-code 2 (a failed step does not end the run), 3 (a cut-off json), 4 (seed, plates, weights,
--area-blank), 5 (1A truth and region pinned), 8 (summary with missing values), the V2 commands (--area-blank pseudo
on the line network only, weights 5/11) and the shipping rule (decide()).
    python -B test_driver2.py
"""
import importlib.util, json, os, shutil, sys
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
STAGED = REPO + 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/'
W2 = REPO + 'data/sanborn/bench_2026-11-23/train/integrate/round2/'
T = W2 + 'driver_test/'
spec = importlib.util.spec_from_file_location('train_v2', STAGED + 'train_v2.py'); D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
MAN = D.sha(D.SP + '/train_v2/manifest.json')
res = {}
V1 = list(D.LABELLED); V2 = D.LABELLED + D.PSEUDO; W = ','.join(f'{p}={D.PSEUDO_W}' for p in D.PSEUDO)


def fresh():
    if os.path.isdir(T): shutil.rmtree(T)
    os.makedirs(T + 'models')


def fake_model(name, iters=4000, man=MAN, seed=1, plates=V1, weights=None, blank=None, raw=None, last=True):
    j = T + 'models/' + name + '.json'
    if raw is not None: open(j, 'w').write(raw)
    else:
        wd = {p: float(v) for p, v in (kv.split('=') for kv in weights.split(','))} if weights else {}
        d = dict(history=[dict(iter=iters)], manifest_sha256=man, seed=seed, plates=[dict(plate=p, spec=p, weight=wd.get(p, 1.0)) for p in plates])
        if name.startswith('lines'): d['area_blank'] = [blank.upper()] if blank else []
        json.dump(d, open(j, 'w'))
    if last: open(T + 'models/' + name + '_last.pt', 'wb').write(b'x')
    open(T + 'models/' + name + '.pt', 'wb').write(b'y')


def call(f, *a):
    try: return f(*a)
    except SystemExit as e: return 'SystemExit: ' + str(e.code)[:200]
    except Exception as e: return f'{type(e).__name__}: {str(e)[:200]}'


M = T + 'models'
fresh(); fake_model('area_v2a_s1'); res['v1_area_complete'] = call(D.model_done, M, 'area_v2a_s1', 4000, MAN, 1, V1, None, None)
fresh(); fake_model('lines_v2b_s1', plates=V2, weights=W, blank='pseudo'); res['v2_lines_complete'] = call(D.model_done, M, 'lines_v2b_s1', 4000, MAN, 1, V2, W, 'pseudo')
fresh(); fake_model('lines_v2b_s1', plates=V2, weights=W, blank=None); res['v2_lines_without_area_blank'] = call(D.model_done, M, 'lines_v2b_s1', 4000, MAN, 1, V2, W, 'pseudo')
fresh(); fake_model('area_v2a_s1', iters=3000); res['cut_off_history'] = call(D.model_done, M, 'area_v2a_s1', 4000, MAN, 1, V1, None, None)
fresh(); fake_model('area_v2a_s1', last=False); res['no_last_pt'] = call(D.model_done, M, 'area_v2a_s1', 4000, MAN, 1, V1, None, None)
fresh(); fake_model('area_v2a_s1', raw='{"name": "m", "history": [{"iter": 250'); res['truncated_json'] = call(D.model_done, M, 'area_v2a_s1', 4000, MAN, 1, V1, None, None)
fresh(); fake_model('area_v2a_s1', man='0' * 64); res['other_manifest'] = call(D.model_done, M, 'area_v2a_s1', 4000, MAN, 1, V1, None, None)
fresh(); fake_model('area_v2a_s1', seed=9); res['other_seed'] = call(D.model_done, M, 'area_v2a_s1', 4000, MAN, 1, V1, None, None)
fresh(); fake_model('area_v2b_s1', plates=V2[:-1], weights=W.rsplit(',', 1)[0]); res['other_plates'] = call(D.model_done, M, 'area_v2b_s1', 4000, MAN, 1, V2, W, None)
fresh(); fake_model('area_v2b_s1', plates=V2, weights=W.replace(f'={D.PSEUDO_W}', '=0.5')); res['other_weights'] = call(D.model_done, M, 'area_v2b_s1', 4000, MAN, 1, V2, W, None)
# eval_done
fresh(); a, l = T + 'models/a.pt', T + 'models/l.pt'; open(a, 'wb').write(b'a'); open(l, 'wb').write(b'l'); os.makedirs(T + 'eval/S')
json.dump(dict(models=dict(area=dict(sha256=D.sha(a)), lines=dict(sha256=D.sha(l)))), open(T + 'eval/S/eval_v2.json', 'w'))
res['eval_same_models'] = call(D.eval_done, T + 'eval/S', a, l)
open(l, 'wb').write(b'l2'); res['eval_lines_retrained'] = call(D.eval_done, T + 'eval/S', a, l)
open(T + 'eval/S/eval_v2.json', 'w').write('{"models": {"area"'); res['eval_truncated_json'] = call(D.eval_done, T + 'eval/S', a, l)
# summary with missing values (review-code 8)
fresh(); os.makedirs(T + 'eval/V1S1')
json.dump(dict(bench44=dict(v2=dict(all=dict(PQ=dict(mean=0.5))), paired=None, grids=['grid0']), bench1A=dict(v2=dict(region=dict(PQ=0.1)), region_blocks=9)), open(T + 'eval/V1S1/eval_v2.json', 'w'))
res['summary_without_paired'] = call(lambda: D.summary(T.rstrip('/'), 4000) and 'ok')
open(T + 'eval/V1S1/eval_v2.json', 'w').write('{"bench44": ')
res['summary_with_cut_eval'] = call(lambda: D.summary(T.rstrip('/'), 4000) and 'ok')


# the rule (decide), on made-up 44 numbers
def rows(pq, gain, vq):
    return [dict(step=s, **{'44': dict(PQ=pq[s]), '44_paired_gain': dict(PQ=dict(mean=gain[s])), '1A_region': dict(PQ=vq[s])}) for s in pq]
S4 = ('V1S1', 'V1S2', 'V2S1', 'V2S2')
res['rule_v2_wins'] = D.decide(rows(dict(zip(S4, (0.53, 0.52, 0.58, 0.57))), dict(zip(S4, (0.02, 0.01, 0.07, 0.06))), dict(zip(S4, (0.1, 0.2, 0.2, 0.3)))))
res['rule_v2_within_noise'] = D.decide(rows(dict(zip(S4, (0.53, 0.50, 0.545, 0.52))), dict(zip(S4, (0.02, -0.01, 0.034, 0.009))), dict(zip(S4, (0.1, 0.2, 0.2, 0.3)))))
res['rule_nothing_ships'] = D.decide(rows(dict(zip(S4, (0.50, 0.51, 0.49, 0.50))), dict(zip(S4, (-0.01, 0.0, -0.02, -0.01))), dict(zip(S4, (0.1, 0.2, 0.2, 0.3)))))
res['rule_incomplete'] = D.decide(rows(dict(zip(S4, (0.5, None, 0.5, 0.5))), dict(zip(S4, (0.0, None, 0.0, 0.0))), dict(zip(S4, (0.1, 0.2, 0.2, 0.3)))))

# the driver end to end with the runner stubbed
CMDS = []; FAIL = set()
def stub(cmd, logfile, log, dry):
    CMDS.append(cmd); name = os.path.basename(cmd[3]) + ' ' + (cmd[5] if cmd[4] == 'train' else 'eval')
    return (not any(f in ' '.join(cmd) for f in FAIL)), 0.0
D.run = stub
def main(argv):
    CMDS.clear(); sys.argv = ['train_v2.py'] + argv
    r = call(D.main)
    return dict(ret=str(r), cmds=[' '.join((os.path.basename(c) if os.path.isabs(c) and i < 4 else (os.path.relpath(c, D.SP) if os.path.isabs(c) else c)) for i, c in enumerate(cm))[:700] for cm in CMDS])
fresh(); res['driver_V2S1'] = main(['--out', T, '--only', 'V2S1'])
fresh(); FAIL = {'area_v2a_s1'}; res['driver_area_fails'] = main(['--out', T, '--only', 'V1S1,V2S1'])
fresh(); FAIL = {'eval_v2.py'}; res['driver_eval_fails'] = main(['--out', T, '--only', 'baseline,V1S1'])
res['log_tail'] = open(T + 'train_v2.log', encoding='utf8').read().splitlines()[-4:]
json.dump(res, open(W2 + 'test_driver2.json', 'w'), indent=1); print(json.dumps(res, indent=1))
