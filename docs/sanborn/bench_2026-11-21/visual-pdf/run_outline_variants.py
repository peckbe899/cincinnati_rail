"""Run the outline step (outlines_ccomp_mask.py, a redirected copy of outlines.py) on the batch's own network maps for
every uncut PDF sheet, in one of three variants, CPU only, several sheets in parallel.

    python run_outline_variants.py VARIANT [--jobs 4] [N ...]
      VARIANT  external   : as the batch ran it (RETR_EXTERNAL, paper alpha only)  - a check that the copy reproduces the batch
               ccomp      : RETR_CCOMP (nested blocks and street holes kept), no map mask
               ccomp_mask : RETR_CCOMP and map_area.py's map ground (maparea_check/N_mask8.png) as the paper mask
Outputs: variants/VARIANT/N_outlines.json (counts), N_edges.json, N_outlines_poly.json, N_outlines.jpg, N_blockmask.png;
variants/VARIANT/summary.json.
"""
import glob, json, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__))
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'


def one(n, variant, out):
    args = [sys.executable, os.path.join(HERE, 'outlines_ccomp_mask.py'), n, 'area_ng1', 'lines_ng1', out]
    if variant in ('ccomp', 'ccomp_mask'): args.append('--ccomp')
    if variant == 'ccomp_mask': args += ['--mask', os.path.join(HERE, 'maparea_check', f'{n}_mask8.png')]
    t0 = time.time(); r = subprocess.run(args, capture_output=True, text=True)
    if r.returncode: return n, dict(error=(r.stderr.strip().splitlines() or ['?'])[-1])
    rep = json.loads(r.stdout.strip().splitlines()[-1]); rep['seconds'] = round(time.time() - t0); return n, rep


if __name__ == '__main__':
    a = sys.argv[1:]; variant = a.pop(0); jobs = 4
    if '--jobs' in a: i = a.index('--jobs'); jobs = int(a[i + 1]); del a[i:i + 2]
    pl = a or sorted([os.path.basename(os.path.dirname(p)) for p in glob.glob(D + 'cufp/*/source.json')], key=lambda s: int(''.join(c for c in s if c.isdigit())))
    out = os.path.join(HERE, 'variants', variant); os.makedirs(out, exist_ok=True)
    sp = os.path.join(out, 'summary.json'); summ = json.load(open(sp)) if os.path.exists(sp) else {}
    with ThreadPoolExecutor(jobs) as ex:
        for n, rep in ex.map(lambda n: one(n, variant, out), pl):
            summ[n] = rep; print(n, rep, flush=True)
            json.dump(summ, open(sp, 'w'), indent=1)
