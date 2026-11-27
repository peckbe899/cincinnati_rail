"""run_bins.py (text_v1/handoff, 26 Nov 2026): the ink sorting (ink_bins_text.py, the hand-off copy) before and after the
text mask, on the grounds used by the earlier benches, then the rule tracks (rail_tracks_text.py). Writes only into
text_v1/handoff/runs/bins/.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/handoff/code/run_bins.py NAME [NAME ...] [--jobs 4]      (NAME as in RUNS, or 'all')

Each NAME runs three times: '<NAME>_before' (no mask), '<NAME>_after' (--text masks/<N>_text.png, codes 2,3; text may
bridge a gap between two ticks in the railroad rule) and '<NAME>_afterstrict' (the same with --no-text-bridge; these were
the first 'after' runs, made before the bridge existed, and renamed).
Grounds (as text/effect/code/run_bins.py and text/finder/rail_with_mask.py had them):
  44_map_ben     plate 44 with Ben's street map and Ben's rail on: what unet_data/44_bins.png is (the ink-bin reference)
  44_map         plate 44, Ben's street map, Ben's rail OFF (--no-ben): the rule's own rail, scored against his tracks
  44_nets44      plate 44 sorted as a plate with no street map: lines and blocks of the outline step itself on the
                 baseline maps, grid 0 (the stored run diag/swap/runs_baseline44/base__grid0, read only), rail off
  44_nomap       plate 44, no street map and no ground at all, rail off
  5_nets21       plate 5, the networks' block step as Ben saw it on 21 Nov, WITHOUT his line edits (diag/rail5/inputs,
                 read only; the ground of the 23 false railroad tracks), rail off
  5_now          plate 5 as ink_bins.py sorts it today: unet_data/5_edges.json with Ben's line edits, rail off
  5_none         plate 5 with no ground at all, rail off
  1A_now         plate 1A as sorted today (unet_data/1A_edges.json with Ben's line edits), rail off
The masks are the finder3 masks made from the scan alone (handoff/masks/N_text.png). Ben's rail (rail_ben.json) is read
only by ink_bins in 44_map_ben, as the plain run does; the other runs pass --no-ben."""
import os, sys, subprocess, time, json
from concurrent.futures import ThreadPoolExecutor
SP = os.getcwd().replace('\\', '/') + '/'; assert os.path.exists(SP + 'cufp'), 'run from data/sanborn'
HO = SP + 'bench_2026-11-25/text_v1/handoff/'; CODE = HO + 'code/'; OUT = HO + 'runs/bins/'; os.makedirs(OUT, exist_ok=True)
B0 = SP + 'bench_2026-11-25/diag/swap/runs_baseline44/base__grid0/'; R5 = SP + 'bench_2026-11-25/diag/rail5/inputs/'
RUNS = {'44_map_ben': ('44', []), '44_map': ('44', ['--no-ben']),
        '44_nets44': ('44', ['--no-ben', '--no-map', '--edges', B0 + '44_edges.json', '--outlines', B0 + 'outlines.json']),
        '44_nomap': ('44', ['--no-ben', '--no-map']),
        '5_nets21': ('5', ['--no-ben', '--edges', R5 + '5_edges.json', '--outlines', R5 + 'outlines.json']),
        '5_now': ('5', ['--no-ben']), '5_none': ('5', ['--no-ben', '--edges', R5 + 'no_such_file.json']),
        '1A_now': ('1A', ['--no-ben'])}


def one(job):
    name, when = job; N, extra = RUNS[name]; stem = OUT + f'{name}_{when}'
    if os.path.exists(stem + '_tracks.json'): return f'skip {name}_{when}'
    cmd = ['python', '-B', CODE + 'ink_bins_text.py', N] + extra + ['--save', stem + '.png', '--json', stem + '.json']
    if when != 'before': cmd += ['--text', HO + f'masks/{N}_text.png', '--text-codes', '2,3'] + (['--no-text-bridge'] if when == 'afterstrict' else [])
    t0 = time.time(); r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    open(stem + '.log', 'w', encoding='utf8').write(' '.join(cmd) + '\n' + r.stdout + '\n---stderr---\n' + r.stderr)
    if r.returncode: return f'FAIL {name}_{when} exit {r.returncode}: {r.stderr[-800:]}'
    cmd2 = ['python', '-B', CODE + 'rail_tracks_text.py', N, stem + '.png', stem + '_tracks.json'] + (['--text', HO + f'masks/{N}_text.png'] if when != 'before' else [])
    r2 = subprocess.run(cmd2, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    open(stem + '.log', 'a', encoding='utf8').write('\n' + ' '.join(cmd2) + '\n' + r2.stdout + '\n---stderr---\n' + r2.stderr)
    if r2.returncode: return f'FAIL tracks {name}_{when}: {r2.stderr[-800:]}'
    return f'done {name}_{when} {time.time() - t0:.0f} s | {r2.stdout.strip()}'


if __name__ == '__main__':
    a = sys.argv[1:]; jobs = int(a[a.index('--jobs') + 1]) if '--jobs' in a else 4
    names = [x for x in a if not x.startswith('--') and not x.isdigit()]
    if names == ['all']: names = list(RUNS)
    work = [(n, w) for n in names for w in ('before', 'after', 'afterstrict')]
    with ThreadPoolExecutor(jobs) as ex:
        for msg in ex.map(one, work): print(time.strftime('%H:%M:%S'), msg, flush=True)
