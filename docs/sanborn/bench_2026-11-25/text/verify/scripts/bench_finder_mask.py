"""verify (25 Nov 2026): the plate-44 outline bench with a text mask that uses NO truth: the finder's text (codes 2, 3, 4 of
finder/out/44_finder.png). The effect agent's line masks on 44 (Sref, I2, I2p, B2, B2L) all come from bin 8 of a sorting
made with Ben's street map (and, for Sref/I2, his rail), so their 'Ben lines lost' numbers may be optimistic.
Same harness as effect/code/run_bench_text.py (bench44.py --grids with effect/code/outlines_text.py, CPU), but every write
goes to verify/bench/. Read-only on the repo and on the other agents' folders.

    cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/bench_finder_mask.py CHAIN MODE [CHAIN MODE ...]
"""
import os, sys, glob, shutil, subprocess, time
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/'
V = SP + 'bench_2026-11-25/text/verify/'; E = SP + 'bench_2026-11-25/text/effect/'; BR = SP + 'bench_2026-11-25/diag/swap/runs_baseline44/'
MAPS = {'base': SP + 'bench44_maps'}; PAIR = {'base': BR + 'base__{grid}/bench44.json'}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'): MAPS[s] = SP + f'train_v2_runs/eval/{s}/maps44'; PAIR[s] = SP + f'train_v2_runs/eval/{s}/runs44/v2__{{grid}}/bench44.json'
os.makedirs(V + 'masks', exist_ok=True); os.makedirs(V + 'bench', exist_ok=True)
mf = V + 'masks/44_map_F.png'
if not os.path.exists(mf):
    c = cv2.imread(SP + 'bench_2026-11-25/text/finder/out/44_finder.png', 0); cv2.imwrite(mf, np.isin(c, (2, 3, 4)).astype(np.uint8) * 255)
log = open(V + 'bench/run_bench.log', 'a', encoding='utf8')
def say(*a):
    s = time.strftime('%H:%M:%S ') + ' '.join(map(str, a)); print(s, flush=True); log.write(s + '\n'); log.flush()
args = sys.argv[1:]
for k in range(0, len(args), 2):
    chain, mode = args[k:k + 2]; name = f'{chain}__F__{mode}'; out = V + f'bench/{name}/'
    if os.path.exists(out + 'runs44/v2_grids.json'): say('skip', name); continue
    os.makedirs(out + 'runs44/cache', exist_ok=True)
    for f in glob.glob(BR + 'cache/decided_half_*.png'):
        if not os.path.exists(out + 'runs44/cache/' + os.path.basename(f)): shutil.copyfile(f, out + 'runs44/cache/' + os.path.basename(f))
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'TEXT_MODE': mode, 'TEXT_MASK': mf}
    say('RUN', name); t0 = time.time()
    r = subprocess.run(['python', '-B', TOOLS + 'bench44.py', '--grids', MAPS[chain], '--tag', 'v2', '--runs', out + 'runs44', '--jobs', '3', '--no-pic',
                        '--paired', PAIR[chain], '--outlines', E + 'code/outlines_text.py'], cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=env)
    open(out + 'stdout.txt', 'w', encoding='utf8').write(r.stdout[-200000:] + '\n---stderr---\n' + r.stderr[-20000:])
    say('done', name, 'exit', r.returncode, f'{time.time() - t0:.0f}s')
