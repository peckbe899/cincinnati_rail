"""Run the outline step (outlines_nest.py, outputs redirected) on the batch's own network maps (area_ng1 + lines_ng1) for
many plates and variants, CPU only, a few plates at a time, under the networks' venv as the batch ran it.

    python run_variants.py VARIANT [--jobs 3] [--force] [N ...]       (default: all 109 plates of run_plates.json)

VARIANT   switches given to outlines_nest.py
  legacy        --legacy                     the old outlines.py (must reproduce the batch byte for byte)
  new           --mask-cache MASKS           RETR_TREE (nested blocks + hole sides) + map ground on PDF sheets
  nest_only     --no-mask                    RETR_TREE without the map ground
  mask_only     --no-nest --mask-cache MASKS map ground, RETR_EXTERNAL as before
  new_live      (none)                       as 'new' but map_area.py run live (check that the cache is the same)
  new_gate      --mask-cache MASKS, OUTLINES_HOLE_GATE=3: a hole only in a block region <= 3 x the plate's median block
  final         outlines_bench_final.py N area_ng1 lines_ng1 OUT MASKS: the proposed outlines.py itself (I/O redirected)
MASKS = bench_2026-11-21/visual-pdf/maparea_check (N_mask8.png, map_area.py's own output for the 32 PDF sheets).
Outputs: runs_plates/VARIANT/N/{outlines.json, N_outlines.json, N_outlines.jpg, N_blockmask.png}, runs_plates/VARIANT/summary.json
"""
import json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
VPY = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet/.venv/Scripts/python.exe'
MASKS = D + 'bench_2026-11-21/visual-pdf/maparea_check'
VARIANTS = {'legacy': (['--legacy'], {}), 'new': (['--mask-cache', MASKS], {}), 'nest_only': (['--no-mask'], {}),
            'mask_only': (['--no-nest', '--mask-cache', MASKS], {}), 'new_live': ([], {}), 'new_gate': (['--mask-cache', MASKS], {'OUTLINES_HOLE_GATE': '3'}),
            'final': ([MASKS], {})}


def order(n): m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)


def one(n, variant, force):
    out = HERE + f'runs_plates/{variant}/{n}/'
    if not force and os.path.exists(out + f'{n}_outlines.json') and os.path.exists(out + 'outlines.json'):
        return n, dict(json.load(open(out + f'{n}_outlines.json')), reused=True)
    sw, env = VARIANTS[variant]; e = dict(os.environ, OUTLINES_NEST_OPTS='', **env)
    t0 = time.time()
    script = 'outlines_bench_final.py' if variant == 'final' else 'outlines_nest.py'   # final: the proposed code, I/O redirected (make_bench_copy.py)
    r = subprocess.run([VPY, '-W', 'ignore', HERE + script, n, 'area_ng1', 'lines_ng1', out] + sw, cwd=D, capture_output=True, text=True, encoding='utf8', errors='replace', env=e)
    if r.returncode: return n, dict(error=(r.stderr.strip().splitlines() or ['?'])[-1])
    rep = json.loads(r.stdout.strip().splitlines()[-1]); rep['seconds'] = round(time.time() - t0, 1)
    json.dump(rep, open(out + f'{n}_outlines.json', 'w', encoding='utf8', newline='\n'), indent=1)
    return n, rep


if __name__ == '__main__':
    a = sys.argv[1:]; variant = a.pop(0); jobs = 3; force = '--force' in a; a = [x for x in a if x != '--force']
    if '--jobs' in a: i = a.index('--jobs'); jobs = int(a[i + 1]); del a[i:i + 2]
    pl = a or sorted(json.load(open(D + 'unet_data/run_plates.json', encoding='utf8')).keys(), key=order)
    os.makedirs(HERE + f'runs_plates/{variant}', exist_ok=True)
    sp = HERE + f'runs_plates/{variant}/summary.json'; summ = json.load(open(sp)) if os.path.exists(sp) else {}
    with ThreadPoolExecutor(jobs) as ex:
        for n, rep in ex.map(lambda n: one(n, variant, force), pl):
            summ[n] = rep; print(variant, n, rep.get('error') or f"{rep.get('blocks')} blocks, {rep.get('holes')} holes, suspect {rep.get('suspect_why')}, {rep.get('seconds')} s", flush=True)
            json.dump(summ, open(sp, 'w'), indent=1)
