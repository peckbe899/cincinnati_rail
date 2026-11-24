"""review-code: the staged driver train_v2.py's resume logic and summary, on made-up files in review-code/driver_test/.
Nothing is trained or evaluated; the driver's subprocess runner is replaced by a stub that only records the commands.

    python -B test_driver.py
"""
import importlib.util, json, os, shutil, sys
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
STAGED = REPO + 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/'
RC = REPO + 'data/sanborn/bench_2026-11-23/train/review-code/'
T = RC + 'driver_test/'
spec = importlib.util.spec_from_file_location('train_v2', STAGED + 'train_v2.py'); D = importlib.util.module_from_spec(spec); spec.loader.exec_module(D)
MAN = D.sha(D.SP + '/train_v2/manifest.json')
res = {}


def fresh():
    if os.path.isdir(T): shutil.rmtree(T)
    os.makedirs(T + 'models')


def fake_model(name, iters, man=MAN, last=True, best=True, extra=None, raw=None):
    j = T + 'models/' + name + '.json'
    if raw is not None: open(j, 'w').write(raw)
    else: json.dump(dict(dict(history=[dict(iter=iters)], manifest_sha256=man, seed=1), **(extra or {})), open(j, 'w'))
    if last: open(T + 'models/' + name + '_last.pt', 'wb').write(b'x')
    if best: open(T + 'models/' + name + '.pt', 'wb').write(b'y')


def call(f, *a):
    try: return f(*a)
    except SystemExit as e: return 'SystemExit: ' + str(e.code)[:160]
    except Exception as e: return f'{type(e).__name__}: {str(e)[:160]}'


# model_done cases
fresh(); fake_model('m', 4000); res['complete'] = call(D.model_done, T + 'models', 'm', 4000, MAN)
fresh(); fake_model('m', 3000); res['cut_off_json'] = call(D.model_done, T + 'models', 'm', 4000, MAN)
fresh(); fake_model('m', 4000, last=False); res['no_last_pt'] = call(D.model_done, T + 'models', 'm', 4000, MAN)
fresh(); fake_model('m', 4000, man='0' * 64); res['other_manifest'] = call(D.model_done, T + 'models', 'm', 4000, MAN)
fresh(); fake_model('m', 0, raw='{"name": "m", "history": [{"iter": 250'); res['truncated_json'] = call(D.model_done, T + 'models', 'm', 4000, MAN)
fresh(); fake_model('m', 4000, extra=dict(argv=['train', 'm', '--data', 'X', '43', '--seed', '9'], seed=9)); res['other_seed_or_plates_in_json'] = call(D.model_done, T + 'models', 'm', 4000, MAN)
# eval_done
fresh(); a, l = T + 'models/a.pt', T + 'models/l.pt'; open(a, 'wb').write(b'a'); open(l, 'wb').write(b'l'); os.makedirs(T + 'eval/S')
json.dump(dict(models=dict(area=dict(sha256=D.sha(a)), lines=dict(sha256=D.sha(l)))), open(T + 'eval/S/eval_v2.json', 'w'))
res['eval_same_models'] = call(D.eval_done, T + 'eval/S', a, l)
open(l, 'wb').write(b'l2'); res['eval_lines_retrained'] = call(D.eval_done, T + 'eval/S', a, l)
open(T + 'eval/S/eval_v2.json', 'w').write('{"models": {"area"'); res['eval_truncated_json'] = call(D.eval_done, T + 'eval/S', a, l)
# summary with one V row whose eval lacks the paired gains (bench44 --paired missing)
fresh(); os.makedirs(T + 'eval/V1S1')
json.dump(dict(bench44=dict(v2=dict(all=dict(PQ=dict(mean=0.5))), paired=None, grids=['grid0']), bench1A=dict(v2=dict(region=dict(PQ=0.1)), region_blocks=9)), open(T + 'eval/V1S1/eval_v2.json', 'w'))
res['summary_without_paired'] = call(lambda: D.summary(T.rstrip('/'), 4000) and 'ok')
json.dump(dict(bench44=dict(v2=dict(all=dict(PQ=dict(mean=0.5))), paired=dict(all=dict(PQ=dict(mean=0.01, gains=4, of=6))), grids=['grid0']), bench1A=None), open(T + 'eval/V1S1/eval_v2.json', 'w'))
res['summary_with_no_1A'] = call(lambda: D.summary(T.rstrip('/'), 4000) and 'ok')
# the driver end to end with the runner stubbed: what it would run on a fresh OUT, then after "V1S1 area" finished
CMDS = []
def stub(cmd, logfile, log, dry):
    CMDS.append(cmd); return 0.0
D.run = stub
fresh()
def main(argv):
    CMDS.clear(); sys.argv = ['train_v2.py'] + argv
    r = call(D.main); return dict(ret=str(r), cmds=[' '.join(os.path.basename(c) if os.path.isabs(c) and i < 3 else c for i, c in enumerate(cm))[:300] for cm in CMDS])
res['driver_fresh'] = main(['--out', T, '--only', 'V1S1'])
json.dump(res, open(RC + 'test_driver.json', 'w'), indent=1); print(json.dumps(res, indent=1))
