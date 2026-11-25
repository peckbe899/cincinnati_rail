"""run_mixes.py (diag/swap, 25 Nov 2026): plate 44 end to end (bench44.py --grids, the real merged outline step) on
mixed maps that need no GPU: the maps the networks already made, recombined. Nothing is trained or run on the GPU.

For a step S (V1S1 ...) with area nets {ng1, S} and line nets {ng1, S}, three things can change: the area map the
OUTLINE STEP reads (Ao), the area map the LINE NET was fed as its 7th input (Ac), and the LINE NET itself (L).
  000 baseline (bench44_maps)                 001 eval a__ng1+L_S (GPU, run_swaps.py)
  010 mix m010: Ao ng1, lines of ng1 fed S's area map (eval b__A_S+ng1's lines)
  011 mix m011: Ao ng1, lines of S fed S's area map (train_v2_runs/eval/S's lines)
  100 mix m100: Ao S, lines of ng1 fed ng1's area map (bench44_maps' lines)
  101 mix m101: Ao S, lines of S fed ng1's area map (eval a__ng1+L_S's lines)
  110 eval b__A_S+ng1 (GPU)                   111 the run's pair (train_v2_runs/eval/S)
Each mix: diag/swap/mix/<S>_<code>/maps44/gridK/{44_area.png, 44_lines.png} (copies) and runs44/ (bench44 --grids,
tag v2, paired with the six baseline runs in diag/swap/runs_baseline44).
    python -B run_mixes.py [S_code ...]
"""
import os, shutil, subprocess, sys, time, glob
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/'
D = SP + 'bench_2026-11-25/diag/swap/'; BR = D + 'runs_baseline44/'
BASE = SP + 'bench44_maps/grid{g}/'
STEPS = ('V1S1', 'V1S2', 'V2S1', 'V2S2')


def srcs(s):
    pair = SP + f'train_v2_runs/eval/{s}/maps44/grid{{g}}/'; a_ = D + f'eval/a__ng1+L_{s}/maps44/grid{{g}}/'; b_ = D + f'eval/b__A_{s}+ng1/maps44/grid{{g}}/'
    return {'m010': (BASE + '44_area.png', b_ + '44_lines.png'), 'm011': (BASE + '44_area.png', pair + '44_lines.png'),
            'm100': (pair + '44_area.png', BASE + '44_lines.png'), 'm101': (pair + '44_area.png', a_ + '44_lines.png')}


log = open(D + 'run_mixes.log', 'a', encoding='utf8')
def say(*a):
    s = time.strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(map(str, a)); print(s, flush=True); log.write(s + '\n'); log.flush()


want = sys.argv[1:]
for s in STEPS:
    for code, (am, lm) in srcs(s).items():
        name = f'{s}_{code}'
        if want and name not in want: continue
        out = D + f'mix/{name}/'
        if os.path.exists(out + 'runs44/v2_grids.json'): say('skip (done)', name); continue
        miss = [p.format(g=g) for g in range(6) for p in (am, lm) if not os.path.exists(p.format(g=g))]
        if miss: say('skip (maps missing)', name, miss[:2]); continue
        for g in range(6):
            d = out + f'maps44/grid{g}/'; os.makedirs(d, exist_ok=True)
            shutil.copyfile(am.format(g=g), d + '44_area.png'); shutil.copyfile(lm.format(g=g), d + '44_lines.png')
            open(d + 'source.txt', 'w').write(f'area {am.format(g=g)}\nlines {lm.format(g=g)}\n')
        os.makedirs(out + 'runs44/cache', exist_ok=True)
        for f in glob.glob(BR + 'cache/decided_half_*.png'):
            if not os.path.exists(out + 'runs44/cache/' + os.path.basename(f)): shutil.copyfile(f, out + 'runs44/cache/' + os.path.basename(f))
        say('RUN', name); t0 = time.time()
        r = subprocess.run(['python', '-B', TOOLS + 'bench44.py', '--grids', out + 'maps44', '--tag', 'v2', '--runs', out + 'runs44', '--jobs', '3', '--paired', BR + 'base__{grid}/bench44.json'],
                           cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        open(out + 'stdout.txt', 'w', encoding='utf8').write(r.stdout + '\n---stderr---\n' + r.stderr[-20000:])
        say('done', name, 'exit', r.returncode, f'{time.time() - t0:.0f}s')
