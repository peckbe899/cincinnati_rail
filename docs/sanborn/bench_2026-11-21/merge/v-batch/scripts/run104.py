"""merge/v-batch: the staged merge on the 104 unplaced plates, outlines only, from the batch's saved maps (21 Nov 2026).

    python -B run104.py [--jobs 6] [N ...]

Per plate: the venv runs the staged blocks_noguide.py N --outlines-only --out v-batch/plates/N/ (the path run_plates.py
takes when only the outline step changed: it reads unet_data/N_pred_area_ng1.png and N_lines_lines_ng1.png, runs the
staged outlines.py with --out, then step 4), cwd data/sanborn, as the batch ran it. Nothing is written outside v-batch.
Writes plates/N/{outlines.json, N_outlines.json, N_edges.json, N_blocks_ng.json, ...}, plates/N/run.json (wall seconds,
exit, the last printed line) and logs/N.log.
"""
import concurrent.futures as cf, json, os, subprocess, sys, time
import common as C


def run_one(n):
    d = C.mine(C.ME + f'plates/{n}') + '/'; os.makedirs(d, exist_ok=True)
    if os.path.exists(d + 'run.json') and '--again' not in sys.argv:
        r = json.load(open(d + 'run.json')); return n, f"had ({r['exit']})"
    t = time.time()
    r = subprocess.run([C.VPY, '-B', C.SU + 'blocks_noguide.py', n, '--outlines-only', '--out', d], cwd=C.DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=C.env())
    w = round(time.time() - t, 1)
    open(C.mine(C.ME + f'logs/{n}.log'), 'w', encoding='utf8').write(r.stdout + '\n----- stderr\n' + r.stderr)
    last = (r.stdout.strip().splitlines() or [''])[-1]
    json.dump(dict(plate=n, exit=r.returncode, wall_seconds=w, last=last, started=time.strftime('%H:%M:%S', time.localtime(t))), open(d + 'run.json', 'w'), indent=1)
    return n, f'exit {r.returncode}, {w} s | {last[:200]}'


if __name__ == '__main__':
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 6
    args = [a for i, a in enumerate(sys.argv[1:], 1) if not a.startswith('--') and sys.argv[i - 1] != '--jobs']
    want = args or C.plates104(); t = time.time()
    with cf.ThreadPoolExecutor(jobs) as ex:
        for n, msg in ex.map(run_one, want): print(n, msg, flush=True)
    print('all', len(want), 'plates', round(time.time() - t), 's wall, jobs', jobs, flush=True)
