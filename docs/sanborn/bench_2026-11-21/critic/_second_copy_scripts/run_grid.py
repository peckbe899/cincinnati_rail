"""critic: paired check of the proposed outline-step changes against the tile-grid noise floor on plate 44.

The inference agent showed that moving the two networks' tile grids (6 equally valid grids, maps in
bench_2026-11-21/inference/maps/{batch,off1..5}_tta1 and {a_tta8,off1..5_a_tta8}) moves the batch's PQ on 44 between
0.430 and 0.471. Nobody ran the outline-step proposals on those grids. This script does, with an unchanged copy of
bench44.py in critic/harness/ (so every run folder is critic/harness/runs/TAG/), on the CPU, nothing trained:

  cur   : the repo's outlines.py (bench44's outlines_copy.py), step 4 as in the repo
  oq    : outline-quality's proposal (verify-outline-quality/patched/outlines_redirected.py + its patched step 4)
  nest  : outline-nesting's proposal (outline-nesting/outlines_bench_final.py), step 4 as in the repo

    python run_grid.py [--jobs 4] [--only oq,nest] [--maps tta1,tta8]

Writes critic/grid_runs.json (headline per run). Read-only on the repo. PYTHONDONTWRITEBYTECODE is set so no
__pycache__ is written next to any imported file.
"""
import json, os, subprocess, sys, concurrent.futures as cf
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
INF = SP + 'bench_2026-11-21/inference/maps/'
VAR = {
    'cur': dict(outlines=HERE + 'harness/outlines_copy.py', step4=None),
    'oq': dict(outlines=HERE + 'variants/oq_outlines_redirected.py', step4=HERE + 'variants/oq_step4_patched.py'),
    'nest': dict(outlines=HERE + 'variants/nest_outlines_bench_final.py', step4=None),
}
GRIDS = {'tta1': ['batch'] + [f'off{i}_tta1' for i in range(1, 6)], 'tta8': ['a_tta8'] + [f'off{i}_a_tta8' for i in range(1, 6)]}


def one(v, m):
    tag = f'{v}__{m}'; out = HERE + f'harness/runs/{tag}/bench44.json'
    if os.path.exists(out): return tag, json.load(open(out))
    cmd = [sys.executable, HERE + 'harness/bench44.py', '--area', INF + f'{m}/44_area.png', '--lines', INF + f'{m}/44_lines.png',
           '--outlines', VAR[v]['outlines'], '--tag', tag, '--no-pic']
    if VAR[v]['step4']: cmd += ['--step4', VAR[v]['step4']]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, env=env)
    if r.returncode: return tag, dict(error=r.stderr[-1500:])
    return tag, json.load(open(out))


if __name__ == '__main__':
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 4
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else list(VAR)
    maps = sys.argv[sys.argv.index('--maps') + 1].split(',') if '--maps' in sys.argv else list(GRIDS)
    todo = [(v, m) for v in only for g in maps for m in GRIDS[g]]
    res = json.load(open(HERE + 'grid_runs.json')) if os.path.exists(HERE + 'grid_runs.json') else {}
    with cf.ThreadPoolExecutor(jobs) as ex:
        for tag, d in ex.map(lambda vm: one(*vm), todo):
            res[tag] = d.get('headline', d); print(tag, json.dumps(res[tag].get('all', res[tag]))[:300], flush=True)
            json.dump(res, open(HERE + 'grid_runs.json', 'w'), indent=1)
