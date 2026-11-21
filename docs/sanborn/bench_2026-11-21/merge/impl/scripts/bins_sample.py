"""merge/impl: the ink bins before and after, on plate 90 and a sample of other plates never placed (21 Nov 2026).

    python -B bins_sample.py [N ...]       (default 90 5 66 3 30 60B 64A)  -> merge/impl/bins_sample.json

For each plate:
  1. the staged blocks_noguide.py N --outlines-only --out merge/impl/bng/N  (the outline step on the batch's saved maps
     and step 4, as run_plates.py will now run it; its N_edges.json, outlines.json, N_mapground.png go there)
  2. the staged ink_bins.py N --edges bng/N/N_edges.json --outlines bng/N/outlines.json --save bins_sample/N_after.png
     (Ben's rail as it is in rail_ben.json, as the real run would read it)
Before = unet_data/N_bins.png / N_bins.json as they are today (the batch's, or on 90 the run of the editor's button at
14:09 after Ben drew the rail, both with the old ink_bins.py).
"""
import concurrent.futures as cf, json, os, subprocess, sys
import numpy as np
import cv2
import common as C
O = C.IMPL + 'bins_sample/'; os.makedirs(O, exist_ok=True)
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
PL = [a for a in sys.argv[1:]] or ['90', '5', '66', '3', '30', '60B', '64A']


def one(n):
    d = C.IMPL + f'bng/{n}/'
    if not os.path.exists(d + f'{n}_edges.json'):
        r = subprocess.run([C.VPY, '-B', C.SU + 'blocks_noguide.py', n, '--outlines-only', '--out', d], cwd=C.DATA, capture_output=True, text=True, env=C.env())
        if r.returncode: return n, dict(error=(r.stdout + r.stderr)[-1500:])
        open(d + 'blocks_noguide_stdout.txt', 'w').write(r.stdout)
    out, js = C.ink_bins(n, O + f'{n}_after.png', ['--edges', d + f'{n}_edges.json', '--outlines', d + 'outlines.json'])
    open(O + f'{n}_after.log', 'w').write(out)
    before = json.load(open(C.U + f'{n}_bins.json', encoding='utf8')); B = cv2.imread(C.U + f'{n}_bins.png', 0); A = cv2.imread(O + f'{n}_after.png', 0)
    tr = np.bincount(B.ravel().astype(np.int64) * 10 + A.ravel(), minlength=100).reshape(10, 10)
    return n, dict(before={v['name']: v['px'] for v in before['bins'].values()}, after={NAMES[k]: int((A == k).sum()) for k in NAMES}, after_note=js['note'], made_from=js['made_from'],
                   blocks_line=open(d + 'blocks_noguide_stdout.txt').read().strip().splitlines()[-1],
                   not_sorted_before_went_to={NAMES[j]: int(tr[9, j]) for j in NAMES if tr[9, j]}, rail_same=bool(((B == 4) == (A == 4)).all() and ((B == 5) == (A == 5)).all()),
                   railroad_px_before_after=[int(tr[4].sum()), int(tr[:, 4].sum())], streetcar_px_before_after=[int(tr[5].sum()), int(tr[:, 5].sum())])


res = json.load(open(C.IMPL + 'bins_sample.json')) if os.path.exists(C.IMPL + 'bins_sample.json') else {}
with cf.ThreadPoolExecutor(4) as ex:
    for n, r in ex.map(one, PL):
        res[n] = r; print(n, json.dumps(r)[:900], flush=True)
json.dump(res, open(C.IMPL + 'bins_sample.json', 'w'), indent=1)
