"""verify-inference: rescore map pairs with MY copy of the bench44 harness (bench/bench44.py, a byte copy of
bench44/bench44.py; bench/outlines_copy.py a byte copy of bench44/outlines_copy.py).

    python rescore_agent_maps.py [--jobs 2] SRC:TAG [SRC:TAG ...]

SRC is either 'inf:V' (the inference agent's maps/V/44_area.png and 44_lines.png, read only) or 'mine:T'
(this folder's maps/T/44_pred_area_ng1.png and 44_lines_lines_ng1.png, written by verify_maps_patched.py).
Each run lands in bench/runs/TAG/. Prints and saves rescore.json (headline all/A/B per TAG).
"""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-inference/'
INF = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/inference/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
argv = sys.argv[1:]; jobs = 2
if '--jobs' in argv:
    i = argv.index('--jobs'); jobs = int(argv[i + 1]); argv = argv[:i] + argv[i + 2:]
KEYS = ('PQ', 'SQ', 'RQ', 'matched', 'merges', 'fp', 'PQ_decided', 'recall_interior', 'precision', 'precision_green', 'precision_orange', 'ben_blocks_closed', 'intact_rings', 'delete_len', 'draw_len')


def one(spec):
    src, tag = spec.rsplit(':', 1); kind, name = src.split(':', 1)
    if kind == 'inf': area, lines = INF + f'maps/{name}/44_area.png', INF + f'maps/{name}/44_lines.png'
    else: area, lines = V + f'maps/{name}/44_pred_area_ng1.png', V + f'maps/{name}/44_lines_lines_ng1.png'
    r = subprocess.run([sys.executable, '-B', V + 'bench/bench44.py', '--area', area, '--lines', lines, '--tag', tag], cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
    if r.returncode: print('FAILED', tag, r.stderr[-1500:], flush=True); return tag, None
    b = json.load(open(V + f'bench/runs/{tag}/bench44.json'))
    out = {f: {k: b['headline'][f].get(k) for k in KEYS} for f in ('all', 'A', 'B')}
    out['inputs'] = dict(area=area, lines=lines, meta={k: b['meta'][k] for k in b['meta'] if k in ('area', 'lines', 'inputs')})
    print('done', tag, out['all']['PQ'], out['A']['PQ'], out['B']['PQ'], flush=True)
    return tag, out


if __name__ == '__main__':
    with ThreadPoolExecutor(jobs) as ex: res = dict(ex.map(one, argv))
    f = V + 'rescore.json'; prev = json.load(open(f)) if os.path.exists(f) else {}
    prev.update({k: v for k, v in res.items() if v is not None}); json.dump(prev, open(f, 'w'), indent=1)
    for t in sorted(prev):
        a = prev[t]
        print('%-22s PQ %.4f (A %.4f B %.4f) RQ %.4f m %d mg %d fp %d rec %.4f prec %.4f closed %s' % (t, a['all']['PQ'], a['A']['PQ'], a['B']['PQ'], a['all']['RQ'], a['all']['matched'], a['all']['merges'], a['all']['fp'], a['all']['recall_interior'], a['all']['precision'], a['all']['ben_blocks_closed']))
