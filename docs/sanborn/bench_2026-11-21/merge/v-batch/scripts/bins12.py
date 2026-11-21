"""merge/v-batch: the staged ink_bins.py fallback on 12 plates, fed by this check's merged outline step (21 November 2026).

    python -B bins12.py run [--jobs 4]      -> v-batch/bins/N_bins.png, N_bins.json, N.log   (system python, as run_plates.py)
    python -B bins12.py measure             -> v-batch/bins12.json, printed table

Per plate: run_ink.py N --edges v-batch/plates/N/N_edges.json --outlines v-batch/plates/N/outlines.json
--save v-batch/bins/N_bins.png --json v-batch/bins/N_bins.json, cwd data/sanborn. That is what run_plates.py's ink step
reads after the outline step (N_edges.json, outlines.json, N_mapground.png beside it); none of these 12 plates has
edges_ben.json, so --edges loses nothing. 'before' is the repo's unet_data/N_bins.png / N_bins.json (the batch's; 90's
is the editor-button run of 14:09 with Ben's rail). Also: a before x after table of pixels (where the old bins' ink went).
"""
import concurrent.futures as cf, json, os, subprocess, sys, time
import numpy as np
import cv2
import common as C
PL = ['90', '30', '79', '60B', '64A', '26A', '5', '1B', '1A', '3', '47', '93A']   # PDF 200 ft x3, cut 200 ft x3, cut 100 ft x4, 400 ft x2
OUT = C.mine(C.ME + 'bins') + '/'
NAMES = {0: 'no ink', 1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}


def run_one(n):
    os.makedirs(OUT, exist_ok=True); d = C.ME + f'plates/{n}/'; t = time.time()
    cmd = [C.SYSPY, '-B', C.ME + 'scripts/run_ink.py', n, '--edges', d + f'{n}_edges.json', '--outlines', d + 'outlines.json', '--save', OUT + f'{n}_bins.png', '--json', OUT + f'{n}_bins.json']
    r = subprocess.run(cmd, cwd=C.DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=C.env())
    w = round(time.time() - t, 1); open(OUT + f'{n}.log', 'w', encoding='utf8').write(' '.join(cmd) + f'\nexit {r.returncode}, {w} s\n' + r.stdout + '\n----- stderr\n' + r.stderr)
    return n, f'exit {r.returncode}, {w} s'


def measure():
    rows = {}
    for n in PL:
        bj = json.load(open(C.U + f'{n}_bins.json', encoding='utf8')); aj = json.load(open(OUT + f'{n}_bins.json', encoding='utf8'))
        b = cv2.imread(C.U + f'{n}_bins.png', cv2.IMREAD_UNCHANGED); a = cv2.imread(OUT + f'{n}_bins.png', cv2.IMREAD_UNCHANGED)
        M = np.bincount(b.ravel().astype(np.int64) * 10 + a.ravel(), minlength=100).reshape(10, 10)
        log = open(OUT + f'{n}.log', encoding='utf8').read()
        rows[n] = dict(plate=n, group=C.group(n), before={v['name']: v['px'] for v in bj['bins'].values()}, after={v['name']: v['px'] for v in aj['bins'].values()},
                       ink_before=bj['ink_px'], ink_after=aj['ink_px'], note_before=bj.get('note'), note_after=aj.get('note'), ground_from=aj.get('ground_from'),
                       made_from=aj.get('made_from'), ben_rail_after=aj.get('ben_rail'), ben_rail_before=bj.get('ben_rail'),
                       bins_before_made=time.strftime('%Y-%m-%d %H:%M', time.localtime(os.path.getmtime(C.U + f'{n}_bins.png'))),
                       not_sorted_to={NAMES[k]: int(M[9, k]) for k in range(10) if M[9, k]},
                       railroad_before_to={NAMES[k]: int(M[4, k]) for k in range(10) if M[4, k]}, railroad_after_from={NAMES[k]: int(M[k, 4]) for k in range(10) if M[k, 4]},
                       same_pixels_share=round(float(np.trace(M[1:, 1:]) / max(1, M[1:, 1:].sum())), 4),
                       seconds=float(log.splitlines()[1].split(',')[1].split()[0]))
    json.dump(rows, open(OUT[:-5] + 'bins12.json', 'w'), indent=1)
    keys = ['block line', 'lot line', 'building outline', 'railroad', 'streetcar', 'water pipe', 'sewer', 'text and numbers', 'not sorted']
    print('plate group      ' + ' | '.join(keys))
    for n, r in rows.items():
        print(f"{n:4s} {r['group']:11s} " + ' | '.join(f"{r['before'][k]:,} -> {r['after'][k]:,}" for k in keys) + f" | {r['seconds']} s")


if __name__ == '__main__':
    if sys.argv[1] == 'run':
        jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 4
        want = [a for a in sys.argv[2:] if a in PL] or PL
        with cf.ThreadPoolExecutor(jobs) as ex:
            for n, msg in ex.map(run_one, want): print(n, msg, flush=True)
    else: measure()
