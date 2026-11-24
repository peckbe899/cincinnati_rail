"""Integrator, round 2 (24 Nov 2026): the staged unet.py / edgenet.py command lines after the review fixes, parsed by
their __main__ blocks with train / predict / train_data replaced by stubs (nothing is trained). review-code's
test_cli.py cases plus --val-every 0, --out inside unet_data, the default --out, and --area-blank.
    VENV -B test_cli2.py
"""
import json, os, sys, importlib
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
STAGED = REPO + 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/'
sys.path.insert(0, REPO + 'tools/sanborn'); sys.path.insert(0, STAGED)
SP = REPO + 'data/sanborn/'


def run(fname, argv):
    for m in ('unet', 'edgenet'): sys.modules.pop(m, None)
    sys.argv = [STAGED + fname] + argv
    mod = importlib.import_module(fname[:-3])
    calls = []
    mod.train = lambda *a: calls.append(('train',) + a)
    mod.predict = lambda *a: calls.append(('predict',) + a)
    mod.train_data = lambda *a: calls.append(('train_data',) + a)
    src = open(STAGED + fname, encoding='utf8').read(); k = src.index("if __name__ == '__main__':")
    try:
        exec(compile("if True:" + src[k + len("if __name__ == '__main__':"):], fname, 'exec'), mod.__dict__)
        return dict(calls=[[str(c) for c in x] for x in calls])
    except SystemExit as e:
        return dict(exit=str(e.code)[:200])


cases = [
    ('unet.py', ['train', 'area_ng1', '82A:all', '80:all', '43:all', '45:all', '44:val', '--no-guide', '--iters', '4000']),
    ('unet.py', ['predict', 'area_ng1', '43', '--no-guide']),
    ('edgenet.py', ['train', 'lines_ng1', '82A', '80', '43', '45', '44:val', '--no-guide', '--area', 'area_ng1', '--iters', '4000']),
    ('edgenet.py', ['predict', 'lines_ng1', '43', '--no-guide', '--area', 'area_ng1']),
    ('unet.py', ['train', 'x', '--data', 'D', '43', '1A', '--seed', '1', '--iters', '20', '--out', 'O', '--weights', '5=0.5,54a=0.5']),
    ('edgenet.py', ['train', 'x', '--data', 'D', '43', '1A', '--seed', '1', '--iters', '20', '--out', 'O', '--area-blank', 'pseudo']),
    ('edgenet.py', ['train', 'x', '--data', 'D', '43', '--area-blank', 'pseudo,58']),
    ('unet.py', ['train', 'x', '--data', 'D', '43']),                                     # default --out
    ('unet.py', ['train', 'x', '--data', 'D', '43', '--out', SP + 'unet_data/models']),   # refused
    ('edgenet.py', ['train', 'x', '--data', 'D', '43', '--out', SP + 'unet_data']),       # refused
    ('unet.py', ['train', 'x', '--data', 'D', '--val-every', '0']),                       # refused
    ('edgenet.py', ['train', 'x', '--data', 'D', '--val-every', '-5']),                   # refused
    ('edgenet.py', ['train', 'x', '43', '--area-blank', 'pseudo']),                      # refused: not for the unet_data plates
    ('unet.py', ['train', 'x', '43', '--seed', '1']),
    ('unet.py', ['train', 'x', '43', '--iters=20']),
    ('edgenet.py', ['train', 'x', '--data', 'D', '--legacy-noguide']),
]
out = []
for f, argv in cases:
    r = run(f, argv); r.update(file=f, argv=argv); out.append(r); print(json.dumps(r)[:400])
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_cli2.json'), 'w'), indent=1)
