"""run_bins.py (text_fix/step4, 27 Nov 2026): copy of text_v1/handoff/code/run_bins.py with the mask set as a choice.
The ink sorting (ink_bins_text.py, byte copy of the hand-off's) before and after the text mask, on the 8 grounds the
hand-off used, then the rule tracks (rail_tracks_text.py, byte copy). Writes only into step4/runs/bins/<SET>/.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/step4/code/run_bins.py --set f3|f4 NAME [NAME ...] [--jobs 4]   (NAME in RUNS, or 'all')

SET f3 = finder3 masks (step4/masks/f3, byte copies of text_v1/classifier/out/finder3), f4 = finder4 masks (step4/masks/f4,
byte copies of text_fix/integrate/out/finder4, sha256 checked against integrate/FROZEN.txt).
Each NAME gives:
  <NAME>_before        no mask; tracks traced with no mask
  <NAME>_after         mask (codes 2,3), text may bridge a gap between two ticks (rule a, tuned on 44);
                       _after_tracks.json:        traced with the join across text (rule b, tuned on 44)
                       _after_tracks_nojoin.json: traced without the join (as the hand-off's file of that name)
  <NAME>_afterstrict   mask, --no-text-bridge; traced with --no-text-join: NEITHER rule (the fair run). The hand-off's
                       stored afterstrict tracks were traced before the join existed, so they are this too.
Only change from the hand-off's run_bins.py: the folder, the mask set, the two --no-text-join tracings."""
import os, sys, subprocess, time
from concurrent.futures import ThreadPoolExecutor
SP = os.getcwd().replace('\\', '/') + '/'; assert os.path.exists(SP + 'cufp'), 'run from data/sanborn'
ST = SP + 'bench_2026-11-26/text_fix/step4/'; CODE = ST + 'code/'
B0 = SP + 'bench_2026-11-25/diag/swap/runs_baseline44/base__grid0/'; R5 = SP + 'bench_2026-11-25/diag/rail5/inputs/'
RUNS = {'44_map_ben': ('44', []), '44_map': ('44', ['--no-ben']),
        '44_nets44': ('44', ['--no-ben', '--no-map', '--edges', B0 + '44_edges.json', '--outlines', B0 + 'outlines.json']),
        '44_nomap': ('44', ['--no-ben', '--no-map']),
        '5_nets21': ('5', ['--no-ben', '--edges', R5 + '5_edges.json', '--outlines', R5 + 'outlines.json']),
        '5_now': ('5', ['--no-ben']), '5_none': ('5', ['--no-ben', '--edges', R5 + 'no_such_file.json']),
        '1A_now': ('1A', ['--no-ben'])}
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}


def sh(cmd):
    return subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=ENV)


def one(job):
    S, name, when = job; N, extra = RUNS[name]; OUT = ST + f'runs/bins/{S}/'; stem = OUT + f'{name}_{when}'; mask = ST + f'masks/{S}/{N}_text.png'
    if os.path.exists(stem + '_tracks.json'): return f'skip {S} {name}_{when}'
    cmd = ['python', '-B', CODE + 'ink_bins_text.py', N] + extra + ['--save', stem + '.png', '--json', stem + '.json']
    if when != 'before': cmd += ['--text', mask, '--text-codes', '2,3'] + (['--no-text-bridge'] if when == 'afterstrict' else [])
    t0 = time.time(); r = sh(cmd)
    open(stem + '.log', 'w', encoding='utf8').write(' '.join(cmd) + '\n' + r.stdout + '\n---stderr---\n' + r.stderr)
    if r.returncode: return f'FAIL {S} {name}_{when} exit {r.returncode}: {r.stderr[-800:]}'
    tr = {'before': [('_tracks.json', [])], 'after': [('_tracks_nojoin.json', ['--text', mask, '--no-text-join']), ('_tracks.json', ['--text', mask])],
          'afterstrict': [('_tracks.json', ['--text', mask, '--no-text-join'])]}[when]
    msg = []
    for suf, ex in tr:
        cmd2 = ['python', '-B', CODE + 'rail_tracks_text.py', N, stem + '.png', stem + suf] + ex; r2 = sh(cmd2)
        open(stem + '.log', 'a', encoding='utf8').write('\n' + ' '.join(cmd2) + '\n' + r2.stdout + '\n---stderr---\n' + r2.stderr)
        if r2.returncode: return f'FAIL tracks {S} {name}_{when}{suf}: {r2.stderr[-800:]}'
        msg.append(f'{suf}: {r2.stdout.strip()}')
    return f'done {S} {name}_{when} {time.time() - t0:.0f} s | ' + ' || '.join(msg)


if __name__ == '__main__':
    a = sys.argv[1:]; jobs = int(a[a.index('--jobs') + 1]) if '--jobs' in a else 4
    sets = a[a.index('--set') + 1].split(',') if '--set' in a else ['f3']
    assert all(s in ('f3', 'f4') for s in sets), sets
    skip = {a[a.index(o) + 1] for o in ('--jobs', '--set') if o in a}
    names = [x for x in a if not x.startswith('--') and x not in skip]
    if names == ['all']: names = list(RUNS)
    for s in sets: os.makedirs(ST + f'runs/bins/{s}/', exist_ok=True)
    work = [(s, n, w) for s in sets for n in names for w in ('before', 'after', 'afterstrict')]
    with ThreadPoolExecutor(jobs) as ex:
        for msg in ex.map(one, work): print(time.strftime('%H:%M:%S'), msg, flush=True)
