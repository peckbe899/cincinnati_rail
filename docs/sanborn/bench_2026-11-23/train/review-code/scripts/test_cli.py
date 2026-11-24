"""review-code: the staged unet.py / edgenet.py command lines, as train_noguide.py, blocks_noguide and the driver call
them, parsed by the staged __main__ blocks with train / predict / train_data replaced by stubs (nothing is trained).

    VENV -B test_cli.py
"""
import json, os, sys, importlib
sys.dont_write_bytecode = True
REPO = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
STAGED = REPO + 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/'
sys.path.insert(0, REPO + 'tools/sanborn'); sys.path.insert(0, STAGED)


def run(fname, argv):
    """import the staged module fresh with this argv (its flags are read at import), then run its __main__ block"""
    for m in ('unet', 'edgenet'): sys.modules.pop(m, None)
    sys.argv = [STAGED + fname] + argv
    mod = importlib.import_module(fname[:-3])
    calls = []
    mod.train = lambda *a: calls.append(('train',) + a)
    mod.predict = lambda *a: calls.append(('predict',) + a)
    mod.train_data = lambda *a: calls.append(('train_data',) + a)
    src = open(STAGED + fname, encoding='utf8').read(); k = src.index("if __name__ == '__main__':")
    flags = {f: getattr(mod, f, None) for f in ('NOGUIDE', 'LEGACY_NOGUIDE', 'AREA')}
    try:
        exec(compile("if True:" + src[k + len("if __name__ == '__main__':"):], fname, 'exec'), mod.__dict__)
        return dict(calls=[[str(c) for c in x] for x in calls], flags=flags)
    except SystemExit as e:
        return dict(exit=str(e.code)[:200], flags=flags)


cases = [
    ('unet.py', ['train', 'area_ng1', '82A:all', '80:all', '43:all', '45:all', '44:val', '--no-guide', '--iters', '4000']),
    ('unet.py', ['predict', 'area_ng1', '43', '--no-guide']),
    ('edgenet.py', ['train', 'lines_ng1', '82A', '80', '43', '45', '44:val', '--no-guide', '--area', 'area_ng1', '--iters', '4000']),
    ('edgenet.py', ['predict', 'lines_ng1', '43', '--no-guide', '--area', 'area_ng1']),
    ('unet.py', ['train', 'x', '--data', 'D', '43', '1A', '--seed', '1', '--iters', '20', '--out', 'O', '--weights', '5=0.5,54a=0.5']),
    ('edgenet.py', ['train', 'x', '--data', 'D', '43', '1A', '--seed', '1', '--iters', '20', '--out', 'O']),
    ('unet.py', ['train', 'x', '43', '--seed', '1']),               # --seed without --data
    ('unet.py', ['train', 'x', '43', '--iters=20']),                # = form
    ('unet.py', ['train', 'x', '--data', 'D', '--val-every', '0']),
    ('edgenet.py', ['train', 'x', '--data', 'D', '--legacy-noguide']),
]
out = []
for f, argv in cases:
    r = run(f, argv); r.update(file=f, argv=argv); out.append(r); print(json.dumps(r))
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'test_cli.json'), 'w'), indent=1)
