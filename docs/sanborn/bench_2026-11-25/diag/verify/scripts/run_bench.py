"""run_bench.py (diag/verify, 25 Nov 2026): bench44.py --grids (the real merged outline step, CPU) on each
diag/verify/mix/<NAME>/maps44, paired with the six baseline runs in diag/swap/runs_baseline44. Writes only into
diag/verify/mix/<NAME>/runs44 and diag/verify/run_bench.log. Extra bench44 options after '--' (e.g. --outlines HOOK).
    python -B run_bench.py NAME [NAME ...] [-- extra bench44 args]
"""
import glob, os, shutil, subprocess, sys, time
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/'
D = SP + 'bench_2026-11-25/diag/verify/'; BR = SP + 'bench_2026-11-25/diag/swap/runs_baseline44/'
args = sys.argv[1:]; extra = []
if '--' in args: k = args.index('--'); extra = args[k + 1:]; args = args[:k]
log = open(D + 'run_bench.log', 'a', encoding='utf8')
def say(*a):
    s = time.strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(map(str, a)); print(s, flush=True); log.write(s + '\n'); log.flush()
for name in args:
    out = D + f'mix/{name}/'
    if os.path.exists(out + 'runs44/v2_grids.json'): say('skip (done)', name); continue
    os.makedirs(out + 'runs44/cache', exist_ok=True)
    for f in glob.glob(BR + 'cache/decided_half_*.png'):
        if not os.path.exists(out + 'runs44/cache/' + os.path.basename(f)): shutil.copyfile(f, out + 'runs44/cache/' + os.path.basename(f))
    say('RUN', name, ' '.join(extra)); t0 = time.time()
    r = subprocess.run(['python', '-B', TOOLS + 'bench44.py', '--grids', out + 'maps44', '--tag', 'v2', '--runs', out + 'runs44', '--jobs', '3', '--no-pic',
                        '--paired', BR + 'base__{grid}/bench44.json'] + extra,
                       cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
    open(out + 'stdout.txt', 'w', encoding='utf8').write(r.stdout[-200000:] + '\n---stderr---\n' + r.stderr[-20000:])
    say('done', name, 'exit', r.returncode, f'{time.time() - t0:.0f}s')
