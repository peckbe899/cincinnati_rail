"""v-44: do the two harnesses agree? The ORIGINAL harness (unchanged copy, v-44/harness/bench44.py, with the v-44 hooks to
the staged outlines.py and staged step 4) against the STAGED tools/sanborn/unet/bench44.py (real outlines.py, real
step 4, edit_server's clean/sheet), run by each on the same maps.

    python -B agree44.py  -> v-44/agree44.json

Compared per pair of runs: outlines.json, 44_edges.json, 44_shown.json byte for byte, and every number in bench44.json
except meta (headline, blocks, lines_shown, sheet, closure, on_print, workload, stages); also the decided-ground masks."""
import json, os, sys
import numpy as np
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks'))
from common import V, GRIDS, sha16  # noqa: E402
O, S = V + 'harness/runs/', V + 'staged_runs/'
PAIRS = [(f'merged__{g}', f'merged__grid{i}') for i, g in enumerate(GRIDS)] + [('merged__guided', 'merged__guided'), ('railshow__batch', 'railshow__grid0'),
                                                                                ('keepunl__batch', 'keepunl__grid0'), ('noholes__batch', 'noholes__grid0'), ('base__batch', 'base__grid0')]


def flat(d, p=''):
    if isinstance(d, dict):
        for k, v in d.items(): yield from flat(v, f'{p}.{k}' if p else k)
    elif isinstance(d, list):
        for i, v in enumerate(d): yield from flat(v, f'{p}[{i}]')
    else: yield p, d


if __name__ == '__main__':
    out = dict(pairs={})
    for a, b in PAIRS:
        if not (os.path.exists(O + a + '/bench44.json') and os.path.exists(S + b + '/bench44.json')): out['pairs'][f'{a} | {b}'] = 'missing'; continue
        A = json.load(open(O + a + '/bench44.json')); B = json.load(open(S + b + '/bench44.json'))
        fa = dict(flat({k: v for k, v in A.items() if k != 'meta'})); fb = dict(flat({k: v for k, v in B.items() if k != 'meta'}))
        diff = {k: (fa.get(k), fb.get(k)) for k in sorted(set(fa) | set(fb)) if fa.get(k) != fb.get(k)}
        files = {f: (sha16(O + a + '/' + f), sha16(S + b + '/' + f)) for f in ('outlines.json', '44_edges.json', '44_shown.json', '44_blockinst.png')}
        out['pairs'][f'{a} | {b}'] = dict(numbers_compared=len(fa), numbers_differ=len(diff), first_diffs=dict(list(diff.items())[:10]),
                                         files_identical={f: x == y and x is not None for f, (x, y) in files.items()})
        print(a, '|', b, 'numbers', len(fa), 'differ', len(diff), {f: x == y and x is not None for f, (x, y) in files.items()})
    m1 = cv2.imread(V + 'harness/cache/decided_half.png', 0); m2 = cv2.imread(S + 'cache/decided_half.png', 0)
    out['decided_ground_px_differ'] = None if m2 is None else int((m1 != m2).sum()); print('decided ground px differ', out['decided_ground_px_differ'])
    json.dump(out, open(V + 'agree44.json', 'w'), indent=1)
