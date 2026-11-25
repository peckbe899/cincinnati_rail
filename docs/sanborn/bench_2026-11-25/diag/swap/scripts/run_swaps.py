"""run_swaps.py (diag/swap, 25 Nov 2026): eval_v2.py on swapped pairs and _last checkpoints. GPU inference only; nothing trained.
Each eval goes to diag/swap/eval/<NAME>/ and reuses diag/swap/runs_baseline44 (a copy of the six baseline plate-44 runs
from bench_2026-11-23/train/integrate/round2/driver_mini/eval/runs_baseline44, whose code record matches today's code).
    python run_swaps.py [NAME ...]     (default: all, in order; a NAME whose eval_v2.json exists is skipped)
"""
import os, subprocess, sys, time, json
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
VENV = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe'
EV = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/eval_v2.py'
D = SP + 'bench_2026-11-25/diag/swap/'; M = SP + 'train_v2_runs/models/'; U = SP + 'unet_data/models/'
A0, L0 = U + 'area_ng1.pt', U + 'lines_ng1.pt'
STEPS = dict(V1S1='v2a_s1', V1S2='v2a_s2', V2S1='v2b_s1', V2S2='v2b_s2')
JOBS = []
for s, k in STEPS.items(): JOBS.append((f'a__ng1+L_{s}', A0, M + f'lines_{k}.pt'))           # (a) baseline area + new line net
for s, k in STEPS.items(): JOBS.append((f'b__A_{s}+ng1', M + f'area_{k}.pt', L0))           # (b) new area net + baseline line net
for s, k in STEPS.items(): JOBS.append((f'c__{s}_last', M + f'area_{k}_last.pt', M + f'lines_{k}_last.pt'))   # (c) both _last
for s, k in STEPS.items(): JOBS.append((f'c__ng1+L_{s}_last', A0, M + f'lines_{k}_last.pt'))
for s, k in STEPS.items(): JOBS.append((f'c__A_{s}_last+ng1', M + f'area_{k}_last.pt', L0))
want = sys.argv[1:]
log = open(D + 'run_swaps.log', 'a', encoding='utf8')
def say(*a):
    s = time.strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(map(str, a)); print(s, flush=True); log.write(s + '\n'); log.flush()
for name, am, lm in JOBS:
    if want and name not in want: continue
    out = D + 'eval/' + name
    if os.path.exists(out + '/eval_v2.json'): say('skip (done)', name); continue
    cmd = [VENV, '-B', '-W', 'ignore', EV, '--area-model', am, '--lines-model', lm, '--out', out, '--grids', '0,1,2,3,4,5',
           '--baseline-runs', D + 'runs_baseline44', '--truth-1a', SP + 'train_v2/1A/streetmap.json', '--region-1a', SP + 'train_v2/1A/valmask.png']
    say('RUN', name, am, lm); t0 = time.time()
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    os.makedirs(out, exist_ok=True); open(out + '/stdout.txt', 'w', encoding='utf8').write(r.stdout + '\n---stderr---\n' + r.stderr)
    say('done', name, 'exit', r.returncode, f'{time.time() - t0:.0f}s')
    if r.returncode: say(r.stderr[-1500:])
