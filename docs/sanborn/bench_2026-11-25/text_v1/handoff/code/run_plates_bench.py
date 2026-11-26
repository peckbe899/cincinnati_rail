"""run_plates_bench.py (text_v1/handoff, 26 Nov 2026): the line bench on plates 5 and 1A (bench_plate_text.py: bench_plate.py's
own scoring against Ben's lines, the outline step pointed at the hand-off copy), before and after the mask.
Writes only into handoff/runs/plates/.

    cd data/sanborn; python -B bench_2026-11-25/text_v1/handoff/code/run_plates_bench.py [--jobs 3]
Truth: handoff/truth/N_streetmap.json, made from picks22_guided/22-N/edges_ben.json by bench_plate.make_truth (for 1A it is
byte-identical to train_v2/1A/streetmap.json). Maps: the batch's, unet_data/N_pred_area_ng1.png + N_lines_lines_ng1.png.
1A is scored with the region train_v2/1A/valmask.png as eval_v2 did (region = fold A), and on the whole plate ('all').
Configs: control (no mask), ink (mask in the on-ink test only), inkdrop (on-ink test + 'on text' drop), states and states0
(inkdrop and ink with --text-where states: the shape step keeps the unmasked ink, only the side states change)."""
import os, subprocess, sys, time, json
from concurrent.futures import ThreadPoolExecutor
SP = os.getcwd().replace('\\', '/') + '/'; assert os.path.exists(SP + 'cufp'), 'run from data/sanborn'
HO = SP + 'bench_2026-11-25/text_v1/handoff/'; CODE = HO + 'code/'; OUT = HO + 'runs/plates/'; os.makedirs(OUT, exist_ok=True)
PL = {'5': None, '1A': SP + 'train_v2/1A/valmask.png'}
CONF = {'control': ('', '0.5'), 'ink': ('masks/{N}_text.png', '0'), 'inkdrop': ('masks/{N}_text.png', '0.5'), 'states': ('masks/{N}_text.png', '0.5'), 'states0': ('masks/{N}_text.png', '0')}   # states: inkdrop with --text-where states


def one(job):
    N, c = job; tag = f'{N}_{c}'
    if os.path.exists(OUT + tag + '/bench_plate.json'): return f'skip {tag}'
    mask, drop = CONF[c]; env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'HANDOFF_TEXT_MASK': (HO + mask.format(N=N)) if mask else '', 'HANDOFF_TEXT_DROP': drop, 'HANDOFF_TEXT_WHERE': 'states' if 'states' in c else 'both'}
    cmd = ['python', '-B', CODE + 'bench_plate_text.py', '--plate', N, '--truth', HO + f'truth/{N}_streetmap.json', '--area', SP + f'unet_data/{N}_pred_area_ng1.png',
           '--lines', SP + f'unet_data/{N}_lines_lines_ng1.png', '--tag', tag, '--runs', OUT] + (['--region', PL[N]] if PL[N] else [])
    t0 = time.time(); r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=env)
    open(OUT + f'{tag}.log', 'w', encoding='utf8').write(' '.join(cmd) + '\n' + r.stdout[-100000:] + '\n---stderr---\n' + r.stderr[-20000:])
    return f'{"done" if r.returncode == 0 else "FAIL"} {tag} {time.time() - t0:.0f} s' + ('' if r.returncode == 0 else r.stderr[-1500:])


if __name__ == '__main__':
    a = sys.argv[1:]; jobs = int(a[a.index('--jobs') + 1]) if '--jobs' in a else 3
    work = [(N, c) for c in ('control', 'ink', 'inkdrop', 'states', 'states0') for N in ('5', '1A')]
    with ThreadPoolExecutor(jobs) as ex:
        for m in ex.map(one, work): print(time.strftime('%H:%M:%S'), m, flush=True)
