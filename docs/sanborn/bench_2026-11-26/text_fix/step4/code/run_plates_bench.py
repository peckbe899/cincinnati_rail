"""run_plates_bench.py (text_fix/step4, 27 Nov 2026): copy of text_v1/handoff/code/run_plates_bench.py with the mask set as a
choice. The line bench on plates 5 and 1A (bench_plate_text.py, byte copy: bench_plate.py's own scoring against Ben's
lines, the outline step pointed at the hand-off copy), before and after the mask. Writes only into step4/runs/plates/.

    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/run_plates_bench.py CONFIG [CONFIG ...] [--jobs 3]
Truth: step4/truth/N_streetmap.json (byte copies of the hand-off's, made from picks22_guided/22-N/edges_ben.json by
bench_plate.make_truth). Maps: the batch's, unet_data/N_pred_area_ng1.png + N_lines_lines_ng1.png (read only).
1A is scored with the region train_v2/1A/valmask.png as the hand-off did (region = fold A), and on the whole plate.
CONFIG: control (no mask), f3_ink / f4_ink ("both", no drop), f3_states0 / f4_states0 ("states", no drop)."""
import os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
SP = os.getcwd().replace('\\', '/') + '/'; assert os.path.exists(SP + 'cufp'), 'run from data/sanborn'
ST = SP + 'bench_2026-11-26/text_fix/step4/'; CODE = ST + 'code/'; OUT = ST + 'runs/plates/'; os.makedirs(OUT, exist_ok=True)
PL = {'5': None, '1A': SP + 'train_v2/1A/valmask.png'}
CONF = {'control': ('', '0.5', 'both')}
for s in ('f3', 'f4'):
    CONF[f'{s}_ink'] = (f'masks/{s}/{{N}}_text.png', '0', 'both'); CONF[f'{s}_states0'] = (f'masks/{s}/{{N}}_text.png', '0', 'states')


def one(job):
    N, c = job; tag = f'{N}_{c}'
    if os.path.exists(OUT + tag + '/bench_plate.json'): return f'skip {tag}'
    mask, drop, where = CONF[c]
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'HANDOFF_TEXT_MASK': (ST + mask.format(N=N)) if mask else '', 'HANDOFF_TEXT_DROP': drop, 'HANDOFF_TEXT_WHERE': where}
    cmd = ['python', '-B', CODE + 'bench_plate_text.py', '--plate', N, '--truth', ST + f'truth/{N}_streetmap.json', '--area', SP + f'unet_data/{N}_pred_area_ng1.png',
           '--lines', SP + f'unet_data/{N}_lines_lines_ng1.png', '--tag', tag, '--runs', OUT] + (['--region', PL[N]] if PL[N] else [])
    t0 = time.time(); r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=env)
    open(OUT + f'{tag}.log', 'w', encoding='utf8').write(' '.join(cmd) + '\n' + r.stdout[-100000:] + '\n---stderr---\n' + r.stderr[-20000:])
    return f'{"done" if r.returncode == 0 else "FAIL"} {tag} {time.time() - t0:.0f} s' + ('' if r.returncode == 0 else r.stderr[-1500:])


if __name__ == '__main__':
    a = sys.argv[1:]; jobs = int(a[a.index('--jobs') + 1]) if '--jobs' in a else 3
    cfgs = [x for x in a if x in CONF]
    work = [(N, c) for c in cfgs for N in ('5', '1A')]
    with ThreadPoolExecutor(jobs) as ex:
        for m in ex.map(one, work): print(time.strftime('%H:%M:%S'), m, flush=True)
