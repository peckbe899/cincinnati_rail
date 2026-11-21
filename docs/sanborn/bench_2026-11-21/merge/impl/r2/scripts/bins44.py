"""merge/impl/r2: the ink sorting on plate 44 without Ben's street map, against the sorting with it (21 Nov 2026).

    python -B bins44.py run RUNTAG [GRIDTAG]    the staged ink_bins.py on 44 (system python), --save into merge/impl/r2/bins44/
    python -B bins44.py score RUNTAG [GRIDTAG]  -> merge/impl/r2/bins44_RUNTAG.json

Reference ('ref'): the staged ink_bins.py 44 as a plain run sorts it (Ben's street map streetmap/22-44.json for the block
lines and blocks, the old label for the other ground; Ben's rail_ben.json, 26 tracks, complete); it must equal the repo's
unet_data/44_bins.png. Variants, all --no-map (sorted as a plate never placed), with the same rail:
  nets      the networks' block step = the staged outline step's 44 output on the batch grid (r2/bench44_runs/RUNTAG:
            its 44_edges.json, outlines.json and 44_outlines.json, which has a version)
  nets_gK   the same from grid K's run (GRIDTAG__gridK), K = 0..5
  none      no lines and no ground at all: what the batch did on every plate never placed
  batchout  the batch's own outline step on 44 (bench44/runs/batch): its 44_outlines.json has no version, so it is not
            used (ground 'none'): the check of the round-2 rule that only a versioned outline step is trusted
For each reference bin: the share of its ink pixels the variant puts in the same bin, and where the rest goes; on all the
paper and on the ground Ben decided (bench44's decided-ground mask).
"""
import concurrent.futures as cf, glob, json, os, sys
import numpy as np
import cv2
import common as C
O = C.IMPL + 'bins44/'; os.makedirs(O, exist_ok=True); RT = sys.argv[2]; GT = sys.argv[3] if len(sys.argv) > 3 else None
BR = C.IMPL + f'bench44_runs/{RT}/'; BB = C.DATA + 'bench_2026-11-21/bench44/runs/batch/'
V = {'ref': [], 'nets': ['--no-map', '--edges', BR + '44_edges.json', '--outlines', BR + 'outlines.json'],
     'none': ['--no-map', '--edges', O + 'no_such_file.json'], 'batchout': ['--no-map', '--edges', BB + '44_edges.json', '--outlines', BB + 'outlines.json']}
if GT:
    for k in range(6):
        g = C.IMPL + f'bench44_runs/{GT}__grid{k}/'; V[f'nets_g{k}'] = ['--no-map', '--edges', g + '44_edges.json', '--outlines', g + 'outlines.json']
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
F = lambda k: O + f'44_{RT}_{k}.png' if k not in ('ref', 'none', 'batchout') else O + f'44_{k}.png'


def run():
    def one(k):
        if os.path.exists(F(k)) and '--again' not in sys.argv: return k, 'had'
        out, js = C.ink_bins('44', F(k), V[k]); open(F(k)[:-4] + '.log', 'w').write(out); return k, (out.splitlines() or [''])[0][:200]
    with cf.ThreadPoolExecutor(4) as ex:
        for k, m in ex.map(one, list(V)): print(k, m, flush=True)


def conf(ref, test, sel):
    out = {}
    for k in NAMES:
        m = (ref == k) & sel; n = int(m.sum())
        if not n: out[NAMES[k]] = dict(px=0); continue
        c = np.bincount(test[m], minlength=10); t = (test == k) & sel
        out[NAMES[k]] = dict(px=n, same=round(float(c[k] / n), 4), of_variant_bin_ref_agrees=round(float((ref[t] == k).mean()), 4) if t.any() else None,
                             to={NAMES[j]: round(float(c[j] / n), 4) for j in NAMES if j != k and c[j] / n >= 0.005})
    ink = (ref > 0) & sel; out['all ink'] = dict(px=int(ink.sum()), same=round(float((ref[ink] == test[ink]).mean()), 4))
    return out


def score():
    ref = cv2.imread(F('ref'), 0); repo = cv2.imread(C.U + '44_bins.png', 0)
    dec = cv2.resize(cv2.imread(glob.glob(C.IMPL + 'bench44_runs/cache/decided_half_*.png')[0], 0), (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    res = dict(reference_equals_repo_44_bins=bool((ref == repo).all()), counts={}, ground_from={}, vs_ref={})
    for k in V:
        b = cv2.imread(F(k), 0); res['counts'][k] = {NAMES[j]: int((b == j).sum()) for j in NAMES}
        js = json.load(open(F(k)[:-4] + '.json')); res['ground_from'][k] = [js.get('ground_from'), js.get('outline_version')]
        if k != 'ref': res['vs_ref'][k] = dict(all=conf(ref, b, np.ones_like(dec)), decided=conf(ref, b, dec))
    g = [k for k in V if k.startswith('nets_g')]
    if g:
        res['grids'] = {m: dict(mean=round(float(np.mean([res['vs_ref'][k]['all'][m]['same'] for k in g])), 4), sd=round(float(np.std([res['vs_ref'][k]['all'][m]['same'] for k in g], ddof=1)), 4),
                                min=round(float(min(res['vs_ref'][k]['all'][m]['same'] for k in g)), 4), max=round(float(max(res['vs_ref'][k]['all'][m]['same'] for k in g)), 4))
                        for m in ('all ink', 'block line', 'lot line', 'building outline', 'water pipe', 'sewer')}
    json.dump(res, open(C.IMPL + f'bins44_{RT}.json', 'w'), indent=1)
    print('reference equals the repo 44_bins.png:', res['reference_equals_repo_44_bins'], '| ground_from', res['ground_from'])
    for k, d in res['vs_ref'].items():
        print(k.ljust(10), 'all ink', d['all']['all ink']['same'], 'decided', d['decided']['all ink']['same'], '|', {n: (d['all'][n].get('same'), d['all'][n].get('of_variant_bin_ref_agrees')) for n in ('block line', 'lot line', 'building outline', 'water pipe', 'sewer', 'not sorted')})
    if g: print('grids', res['grids'])


if __name__ == '__main__':
    run() if sys.argv[1] == 'run' else score()
