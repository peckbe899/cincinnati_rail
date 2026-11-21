"""v-44: the staged ink_bins.py on plate 44, every output with --save/--json into v-44/bins/ (never N_bins.*).

    python -B bins44.py run [--jobs 4]     the ink-sorting runs (system python, cwd data/sanborn, via launch.py)
    python -B bins44.py compare            per-bin agreement and confusions -> v-44/bins44.json

Runs (ben = with Ben's rail_ben.json as ink_bins reads it; noben = --no-ben, the rules alone):
  ref_staged[_noben]   staged ink_bins with Ben's street map (the reference)
  ref_repo[_noben]     the repo's ink_bins.py (unchanged) with his map: the staged refactor must give the same bins
  nets_merged[_noben]  staged fallback: --no-map --edges/--outlines = the merged step's 44 output (harness/runs/merged__batch)
  nets_base[_noben]    staged fallback fed the repo step's (batch chain's) 44 output (harness/runs/base__batch)
  nets_merged_gK       the fallback fed the merged step on tile grid K (merged__off{K}_tta1), ben only
  none[_noben]         no lines and no ground (--no-map, --edges/--outlines pointing at no file): as the batch sorted
                       the plates never placed"""
import json, os, subprocess, sys, time, concurrent.futures as cf
import numpy as np
import cv2
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks'))
from common import V, DATA, U, STAGED, RU, mine, env, sha16  # noqa: E402
OUT = V + 'bins/'; RUNS = V + 'harness/runs/'; LAUNCH = V + 'scripts/launch.py'
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}


def runs():
    R = {}
    for nb in ('', '_noben'):
        x = ['--no-ben'] if nb else []
        R['ref_staged' + nb] = (STAGED + 'ink_bins.py', x)
        R['ref_repo' + nb] = (RU + '/ink_bins.py', x)
        R['nets_merged' + nb] = (STAGED + 'ink_bins.py', ['--no-map', '--edges', RUNS + 'merged__batch/44_edges.json', '--outlines', RUNS + 'merged__batch/outlines.json'] + x)
        R['nets_base' + nb] = (STAGED + 'ink_bins.py', ['--no-map', '--edges', RUNS + 'base__batch/44_edges.json', '--outlines', RUNS + 'base__batch/outlines.json'] + x)
        R['none' + nb] = (STAGED + 'ink_bins.py', ['--no-map', '--edges', OUT + 'NO_SUCH_FILE.json', '--outlines', OUT + 'NO_SUCH_FILE.json'] + x)
    for k in range(1, 6):
        R[f'nets_merged_g{k}'] = (STAGED + 'ink_bins.py', ['--no-map', '--edges', RUNS + f'merged__off{k}_tta1/44_edges.json', '--outlines', RUNS + f'merged__off{k}_tta1/outlines.json'])
    return R


def one(name, code, extra):
    save = mine(OUT + f'{name}.png'); js = OUT + f'{name}.json'
    if os.path.exists(save): return name, 'exists', 0
    cmd = ['python', '-B', LAUNCH, code, '44', '--save', save] + (['--json', js] if code.startswith(STAGED) else []) + extra
    t0 = time.time(); r = subprocess.run(cmd, cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=env())
    open(OUT + f'{name}.log', 'w', encoding='utf8').write(' '.join(cmd) + '\n' + r.stdout + r.stderr)
    return name, r.returncode, round(time.time() - t0)


def compare():
    ink_dec = cv2.resize(cv2.imread(V + 'harness/cache/decided_half.png', 0), (10768, 7219), interpolation=cv2.INTER_NEAREST) > 127
    ref = cv2.imread(OUT + 'ref_staged.png', 0); res = dict(note='rows = reference bin (staged ink_bins with Ben\'s street map), share of its px that the test puts in each bin; '
                                                             'agree_by_ref = that share on the diagonal; agree_by_test = share of the test\'s bin-k px the reference also calls k', runs={})
    old = cv2.imread(U + '44_bins.png', 0)
    res['ref_staged_vs_unet_data_44_bins_png'] = dict(px_differ=int((ref != old).sum()), unet_sha=sha16(U + '44_bins.png'))
    for f in sorted(os.listdir(OUT)):
        if not f.endswith('.png'): continue
        name = f[:-4]; t = cv2.imread(OUT + f, 0)
        rf = cv2.imread(OUT + ('ref_staged_noben.png' if name.endswith('_noben') else 'ref_staged.png'), 0)
        o = dict(px_differ_from_ref=int((t != rf).sum()))
        for scope, sel in (('all', (rf > 0) | (t > 0)), ('decided', ((rf > 0) | (t > 0)) & ink_dec)):
            a, b = rf[sel].astype(np.int64), t[sel].astype(np.int64); M = np.bincount(a * 10 + b, minlength=100).reshape(10, 10)
            d = dict(ink_px=int(sel.sum()), all_ink_same_bin=round(float(np.trace(M) / max(1, M.sum())), 4), bins={})
            for k in NAMES:
                rowk, colk = M[k].sum(), M[:, k].sum()
                conf = {NAMES.get(j, 'no bin'): round(float(M[k, j] / rowk), 4) for j in range(10) if j != k and rowk and M[k, j] / rowk >= 0.005}
                d['bins'][NAMES[k]] = dict(ref_px=int(rowk), test_px=int(colk), agree_by_ref=round(float(M[k, k] / rowk), 4) if rowk else None,
                                           agree_by_test=round(float(M[k, k] / colk), 4) if colk else None, ref_goes_to=dict(sorted(conf.items(), key=lambda kv: -kv[1])))
            o[scope] = d
        js = OUT + f'{name}.json'
        if os.path.exists(js): j = json.load(open(js, encoding='utf8')); o['ground_from'] = j.get('ground_from'); o['made_from'] = j.get('made_from'); o['note'] = j.get('note')
        res['runs'][name] = o
    json.dump(res, open(V + 'bins44.json', 'w', encoding='utf8'), indent=1)
    for n, o in res['runs'].items():
        print(f"{n:22s} differ {o['px_differ_from_ref']:9d} | all ink {o['all']['all_ink_same_bin']:.4f} decided {o['decided']['all_ink_same_bin']:.4f} | " +
              ' '.join(f"{k[:6]} {v['agree_by_ref']}" for k, v in o['all']['bins'].items()))
    print('ref_staged vs unet_data/44_bins.png: px differ', res['ref_staged_vs_unet_data_44_bins_png'])


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    if sys.argv[1] == 'run':
        jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 4
        only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
        R = {k: v for k, v in runs().items() if not only or k in only}
        with cf.ThreadPoolExecutor(jobs) as ex:
            for r in ex.map(lambda kv: one(kv[0], *kv[1]), R.items()): print(*r, flush=True)
    else: compare()
