"""verify-outline-nesting: per-plate checks of the agent's batch claims (21 Nov 2026).

    python check_plates.py legacy              byte-compare outline-nesting/runs_plates/legacy/N with the batch's own files
    python check_plates.py rerun N [N ...]     rerun MY bench copy (benchcopy/outlines_bench_final.py, generated from the diff
                                               applied to a copy of outlines.py) on N with the agent's map-mask cache, into
                                               plates/N/, and byte-compare with outline-nesting/runs_plates/final/N
Output: check_plates_<mode>.json
"""
import hashlib, json, os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = D + 'unet_data/'
AG = D + 'bench_2026-11-21/outline-nesting/runs_plates/'
VPY = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe'
MASKS = D + 'bench_2026-11-21/visual-pdf/maparea_check'
GUIDED = {'43', '44', '45', '80', '82A'}
same = lambda p, q: os.path.exists(p) and os.path.exists(q) and open(p, 'rb').read() == open(q, 'rb').read()


def img_same(p, q):
    a, b = cv2.imread(p, 0), cv2.imread(q, 0)
    return a is not None and b is not None and a.shape == b.shape and bool((a == b).all())


mode = sys.argv[1]
if mode == 'legacy':
    plates = sorted(json.load(open(U + 'run_plates.json', encoding='utf8')).keys())
    res = {}
    for n in plates:
        if n in GUIDED: continue
        res[n] = dict(outlines=same(AG + f'legacy/{n}/outlines.json', D + f'picks22_guided/22-{n}/outlines.json'),
                      blockmask=img_same(AG + f'legacy/{n}/{n}_blockmask.png', U + f'{n}_blockmask.png'))
    bad = {n: r for n, r in res.items() if not all(r.values())}
    print(len(res), 'unplaced plates;', sum(r['outlines'] for r in res.values()), 'outlines.json identical;', sum(r['blockmask'] for r in res.values()), 'block masks identical; not identical:', bad)
else:
    plates = sys.argv[2:]

    def one(n):
        out = HERE + f'plates/{n}/'
        r = subprocess.run([VPY, '-B', '-W', 'ignore', HERE + 'benchcopy/outlines_bench_final.py', n, 'area_ng1', 'lines_ng1', out, MASKS], cwd=D, capture_output=True, text=True, encoding='utf8', errors='replace',
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        if r.returncode: return n, dict(error=r.stderr[-800:])
        rep = json.loads(r.stdout.strip().splitlines()[-1])
        return n, dict(outlines_same_as_agent_final=same(out + 'outlines.json', AG + f'final/{n}/outlines.json'), blockmask_same=img_same(out + f'{n}_blockmask.png', AG + f'final/{n}/{n}_blockmask.png'),
                       blocks=rep['blocks'], holes=rep.get('holes'), holes_in_open_land=rep.get('holes_in_open_land'), suspect_why=rep.get('suspect_why'), map_ground=rep.get('map_ground'))
    with ThreadPoolExecutor(3) as ex: res = dict(ex.map(one, plates))
    for n, r in res.items(): print(n, r)
json.dump(res, open(HERE + f'check_plates_{mode}.json', 'w'), indent=1)
