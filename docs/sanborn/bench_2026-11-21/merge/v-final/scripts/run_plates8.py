"""v-final: the APPLIED blocks_noguide.py N --outlines-only --out v-final/plates/N/ (venv, CPU) on the batch's saved maps,
for 8 plates of different kinds. Writes v-final/plates/N/ and v-final/plates8_run.json (stdout line, exit code, seconds).
    python -B run_plates8.py [--jobs 4]"""
import concurrent.futures as cf, json, os, subprocess, sys, time
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
VPY = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe'
PL = ['90', '30', '47', '1B', '60B', '5', '26A', '2']
env = dict(os.environ, PYTHONPATH=V + 'shim' + os.pathsep + 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet', PYTHONDONTWRITEBYTECODE='1')
def one(n):
    out = V + f'plates/{n}/'; t0 = time.time()
    r = subprocess.run([VPY, '-B', '-W', 'ignore', V + 'apply/tools/sanborn/unet/blocks_noguide.py', n, '--outlines-only', '--out', out], cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=env)
    open(V + f'plates/{n}.log', 'w', encoding='utf8').write(r.stdout + '\n----\n' + r.stderr)
    return n, dict(exit=r.returncode, seconds=round(time.time() - t0, 1), line=(r.stdout.strip().splitlines() or [''])[-1])
if __name__ == '__main__':
    os.makedirs(V + 'plates', exist_ok=True); jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 4; res = {}
    with cf.ThreadPoolExecutor(jobs) as ex:
        for n, d in ex.map(one, PL): res[n] = d; print(n, d, flush=True)
    json.dump(res, open(V + 'plates8_run.json', 'w'), indent=1)
