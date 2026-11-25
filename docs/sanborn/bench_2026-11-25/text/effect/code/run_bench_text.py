"""run_bench_text.py (text/effect, 25 Nov 2026): bench44.py --grids (the real outline step through outlines_text.py, CPU)
for one chain's stored maps of 44 with one text mask and mode, paired with that chain's own stored runs (no mask).
Writes only into text/effect/bench/<CHAIN>__<MASK>__<MODE>/ and bench/run_bench.log.
    cd data/sanborn; python -B bench_2026-11-25/text/effect/code/run_bench_text.py CHAIN MASK MODE [CHAIN MASK MODE ...]
CHAIN: base (bench44_maps, paired with diag/swap/runs_baseline44/base__grid*) or V1S1 V1S2 V2S1 V2S2
(train_v2_runs/eval/S/maps44, paired with train_v2_runs/eval/S/runs44/v2__grid*). MASK: a name in masks/44_map_<MASK>.png
or 'none'. MODE: lines | ink | both | none."""
import glob, os, shutil, subprocess, sys, time
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/'
E = SP + 'bench_2026-11-25/text/effect/'; BR = SP + 'bench_2026-11-25/diag/swap/runs_baseline44/'
MAPS = {'base': SP + 'bench44_maps'}; PAIR = {'base': BR + 'base__{grid}/bench44.json'}
for s in ('V1S1', 'V1S2', 'V2S1', 'V2S2'): MAPS[s] = SP + f'train_v2_runs/eval/{s}/maps44'; PAIR[s] = SP + f'train_v2_runs/eval/{s}/runs44/v2__{{grid}}/bench44.json'
os.makedirs(E + 'bench', exist_ok=True); log = open(E + 'bench/run_bench.log', 'a', encoding='utf8')
def say(*a):
    s = time.strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(map(str, a)); print(s, flush=True); log.write(s + '\n'); log.flush()
args = sys.argv[1:]
for k in range(0, len(args), 3):
    chain, mask, mode = args[k:k + 3]; name = f'{chain}__{mask}__{mode}'; out = E + f'bench/{name}/'
    if os.path.exists(out + 'runs44/v2_grids.json'): say('skip (done)', name); continue
    os.makedirs(out + 'runs44/cache', exist_ok=True)
    for f in glob.glob(BR + 'cache/decided_half_*.png'):
        if not os.path.exists(out + 'runs44/cache/' + os.path.basename(f)): shutil.copyfile(f, out + 'runs44/cache/' + os.path.basename(f))
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'TEXT_MODE': mode, 'TEXT_MASK': (E + f'masks/44_map_{mask}.png') if mask != 'none' else ''}
    say('RUN', name); t0 = time.time()
    r = subprocess.run(['python', '-B', TOOLS + 'bench44.py', '--grids', MAPS[chain], '--tag', 'v2', '--runs', out + 'runs44', '--jobs', '3', '--no-pic',
                        '--paired', PAIR[chain], '--outlines', E + 'code/outlines_text.py'], cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=env)
    open(out + 'stdout.txt', 'w', encoding='utf8').write(r.stdout[-200000:] + '\n---stderr---\n' + r.stderr[-20000:])
    say('done', name, 'exit', r.returncode, f'{time.time() - t0:.0f}s')
