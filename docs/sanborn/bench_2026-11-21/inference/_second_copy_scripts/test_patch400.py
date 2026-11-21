"""Check the patched blocks_noguide.py run() (patched/ and patched_400/) without touching the repo.

    VENV_PYTHON test_patch400.py N [N ...] [--which patched_400|patched] [--cpu]

run() is cut out of the patched file with ast and executed with pred_only=True (it stops after the two networks), with
U pointed at test_run/WHICH/ in this folder, and A.predict_full / E.predict_full / E.ink_image taken from the patched
unet.py / edgenet.py (also cut out with ast, so _ws is never imported). The maps it writes are compared with the maps
made by infer_lib for the same setting:
  patched_400, a 400-ft plate -> maps_plates/up2thin/N_*.png        patched_400 or patched, other plate -> maps_plates/atta8/N_*.png
Writes logs/test_patch400_WHICH.json.
"""
import ast, json, os, sys, time, types, subprocess
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, torch, torch.nn.functional as F
import infer_lib as L


def cut(path, names):                       # as in test_patch.py (not imported: that file runs its test on import)
    src = open(path, encoding='utf8').read(); tree = ast.parse(src); keep = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.Assign)):
            nm = node.name if isinstance(node, ast.FunctionDef) else getattr(node.targets[0], 'id', None)
            if nm in names: keep.append(ast.get_source_segment(src, node))
    return chr(10).join(keep)


args = [a for a in sys.argv[1:] if not a.startswith('--')]
which = sys.argv[sys.argv.index('--which') + 1] if '--which' in sys.argv else 'patched_400'
args = [a for a in args if a != which]
ns_u = dict(np=np, cv2=cv2, torch=torch, F=F); exec(cut(L.HERE + 'patched/unet.py', {'TTA', 'turn', 'unturn', 'norm', 'predict_full'}), ns_u)
ns_e = dict(np=np, cv2=cv2, torch=torch, F=F, TTA=ns_u['TTA'], turn=ns_u['turn'], unturn=ns_u['unturn']); exec(cut(L.HERE + 'patched/edgenet.py', {'norm', 'predict_full', 'ink_image'}), ns_e)
A = types.SimpleNamespace(predict_full=ns_u['predict_full']); E = types.SimpleNamespace(predict_full=ns_e['predict_full'], ink_image=ns_e['ink_image'])
out_dir = L.HERE + f'test_run/{which}/'; os.makedirs(out_dir, exist_ok=True)
ns = dict(np=np, cv2=cv2, os=os, json=json, sys=sys, time=time, subprocess=subprocess, A=A, E=E, SP=L.SP, U=out_dir, HERE=L.HERE,
          AREA='area_ng1', LINES='lines_ng1')       # blocks_noguide.py:31 sets these in a tuple assignment, which cut() skips
exec(cut(L.HERE + f'{which}/blocks_noguide.py', {'AREA_TTA', 'FT400', 'PEN', 'run'}), ns)
dev = torch.device('cpu') if '--cpu' in sys.argv else L.device(); dev, na, nl = L.load_nets(dev)
res = {}
for n in args:
    t0 = time.time(); ns['run'](n, (dev, na, nl), True); secs = round(time.time() - t0, 1)
    ref = 'up2thin' if (which == 'patched_400' and n in ns.get('FT400', set())) else 'atta8'
    r = {}
    for k, mine, theirs in (('area', f'{n}_pred_area_ng1.png', f'{n}_area.png'), ('lines', f'{n}_lines_lines_ng1.png', f'{n}_lines.png')):
        a = cv2.imread(out_dir + mine, 0).astype(int); b = cv2.imread(L.HERE + f'maps_plates/{ref}/{theirs}', 0)
        if b is None: r[k] = 'no reference map'; continue
        d = np.abs(a - b.astype(int)); r[k] = dict(max_abs=int(d.max()), share_differ=round(float((d > 0).mean()), 6), decision_differs=round(float(((a > 127) != (b > 127)).mean()), 7))
    res[n] = dict(reference=ref, seconds=secs, **r); print(n, json.dumps(res[n]), flush=True)
json.dump(res, open(L.HERE + f'logs/test_patch400_{which}.json', 'w'), indent=1)
