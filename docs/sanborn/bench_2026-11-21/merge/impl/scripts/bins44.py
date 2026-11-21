"""merge/impl: the ink sorting on plate 44 without Ben's street map, against the sorting with it (21 Nov 2026).

    python -B bins44.py run       the staged ink_bins.py on 44, every variant, --save into merge/impl/bins44/ (system python)
    python -B bins44.py score     -> merge/impl/bins44.json

Reference: ink_bins.py 44 as it runs today (Ben's street map streetmap/22-44.json for the block lines and blocks, the
old label for the other ground; Ben's 26 tracks in rail_ben.json, complete). The same rail in every variant, so only the
streets and ground differ. Variants (all --no-map: sorted as a plate never placed):
  merged        the networks' block step = the staged outline step's 44 output (bench44_runs/merged_batch: its
                44_edges.json and outlines.json), UNSURE off
  merged_uXX_YY the same, ground the area network gave XX < P*255 < YY off the blocks marked 'not known'
  batchlines    the batch's own outline step on 44 (bench44/runs/batch: 44_edges.json, outlines.json)
  none          no lines and no ground at all: what the batch did on every plate never placed
For each reference bin: the share of its ink pixels the variant puts in the same bin, and where the rest goes; on all the
paper and on the ground Ben decided (bench44's decided-ground mask: his blocks and the streets between them).
Rail check (--no-ben, as the rail agent scored it): ref_noben, merged_noben, none_noben; tracks by the rail agent's
rail_tracks_copy.py into merge/impl/bins44/, scored by its score_rail_bench.py against rail_ben.page_2026-11-21.json (28
tracks) -> rail44.json.
"""
import concurrent.futures as cf, json, os, subprocess, sys
import numpy as np
import cv2
import common as C
O = C.IMPL + 'bins44/'; os.makedirs(O, exist_ok=True); BR = C.IMPL + 'bench44_runs/merged_batch/'; BB = C.DATA + 'bench_2026-11-21/bench44/runs/batch/'
RAIL = C.DATA + 'bench_2026-11-21/rail/'
V = {'ref': [], 'merged': ['--no-map', '--edges', BR + '44_edges.json', '--outlines', BR + 'outlines.json', '--unsure', 'none'],
     'batchlines': ['--no-map', '--edges', BB + '44_edges.json', '--outlines', BB + 'outlines.json', '--unsure', 'none'],
     'none': ['--no-map', '--edges', O + 'no_such_file.json']}
for lo, hi in ((64, 191), (96, 160), (32, 224)):
    V[f'merged_u{lo}_{hi}'] = V['merged'][:-1] + [f'{lo},{hi}']
for k in ('ref', 'merged', 'none'): V[k + '_noben'] = V[k] + ['--no-ben']
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}


def run():
    def one(k):
        if os.path.exists(O + f'44_{k}.png') and '--again' not in sys.argv: return k, 'had'
        out, js = C.ink_bins('44', O + f'44_{k}.png', V[k]); open(O + f'44_{k}.log', 'w').write(out); return k, out.splitlines()[0][:150]
    with cf.ThreadPoolExecutor(5) as ex:
        for k, m in ex.map(one, list(V)): print(k, m, flush=True)
    for k in ('ref_noben', 'merged_noben', 'none_noben'):   # tracks, then the rail agent's scorer
        if not os.path.exists(O + f'44_{k}_rail_rule.json'):
            subprocess.run([C.SYSPY, '-B', RAIL + 'rail_tracks_copy.py', '44', O + f'44_{k}.png', O + f'44_{k}_rail_rule.json'], cwd=C.DATA, check=True, env=C.env())
        subprocess.run([C.SYSPY, '-B', RAIL + 'score_rail_bench.py', '44', O + f'44_{k}_rail_rule.json', C.DATA + 'picks22_guided/22-44/rail_ben.page_2026-11-21.json', O + f'rail_{k}', '--bins', O + f'44_{k}.png'],
                       cwd=C.DATA, check=True, env=C.env(), capture_output=True)


def conf(ref, test, sel):
    out = {}
    for k in NAMES:
        m = (ref == k) & sel; n = int(m.sum())
        if not n: out[NAMES[k]] = dict(px=0); continue
        c = np.bincount(test[m], minlength=10)
        out[NAMES[k]] = dict(px=n, same=round(float(c[k] / n), 4), to={NAMES[j]: round(float(c[j] / n), 4) for j in NAMES if j != k and c[j] / n >= 0.005})
    ink = (ref > 0) & sel; out['all ink'] = dict(px=int(ink.sum()), same=round(float((ref[ink] == test[ink]).mean()), 4))
    five = np.isin(ref, (1, 2, 3, 6, 7)) & sel; out['bins 1 2 3 6 7'] = dict(px=int(five.sum()), same=round(float((ref[five] == test[five]).mean()), 4),
                                                                        mean_of_shares=round(float(np.mean([out[NAMES[k]]['same'] for k in (1, 2, 3, 6, 7) if out[NAMES[k]]['px']])), 4))
    return out


def score():
    ref = cv2.imread(O + '44_ref.png', 0); batch = cv2.imread(C.U + '44_bins.png', 0)
    dec = cv2.resize(cv2.imread(C.IMPL + 'bench44_runs/cache/decided_half.png', 0), (ref.shape[1], ref.shape[0]), interpolation=cv2.INTER_NEAREST) > 0
    res = dict(reference_equals_batch_44_bins=bool((ref == batch).all()), counts={}, vs_ref={})
    for k in V:
        b = cv2.imread(O + f'44_{k}.png', 0); res['counts'][k] = {NAMES[j]: int((b == j).sum()) for j in NAMES}
        if k.endswith('_noben'): continue
        res['vs_ref'][k] = dict(all=conf(ref, b, np.ones_like(dec)), decided=conf(ref, b, dec))
    ref_nb = cv2.imread(O + '44_ref_noben.png', 0)
    for k in ('merged_noben', 'none_noben'):
        b = cv2.imread(O + f'44_{k}.png', 0); res['vs_ref'][k + '_vs_ref_noben'] = dict(all=conf(ref_nb, b, np.ones_like(dec)), decided=conf(ref_nb, b, dec))
    rail = {}
    for k in ('ref_noben', 'merged_noben', 'none_noben'):
        r = json.load(open(O + f'rail_{k}.json')); rail[k] = r
    res['rail'] = {k: dict(rule_tracks=rail[k]['n_rule'], **{kind: {f'tol{t}': {m: rail[k]['kinds'][kind][f'tol{t}'].get(m) for m in ('recall', 'precision', 'false_len', 'found', 'partial', 'missed', 'false_tracks', 'false_tracks_len')}
                                                                for t in (10, 30)} for kind in ('railroad', 'streetcar')}) for k in rail}
    json.dump(res, open(C.IMPL + 'bins44.json', 'w'), indent=1)
    for k, v in res['rail'].items(): print('rail', k, v)
    print('reference equals the batch 44_bins.png:', res['reference_equals_batch_44_bins'])
    for k, d in res['vs_ref'].items():
        print(k.ljust(30), 'all ink', d['all']['all ink']['same'], '| bins 12367', d['all']['bins 1 2 3 6 7'], '| decided 12367', d['decided']['bins 1 2 3 6 7']['same'],
              '|', {n: d['all'][n].get('same') for n in ('block line', 'lot line', 'building outline', 'water pipe', 'sewer', 'not sorted')})


if __name__ == '__main__':
    run() if sys.argv[1] == 'run' else score()
