"""v-final: plate 44 on the 6 tile grids with the ORIGINAL bench44 harness (copied unchanged into v-final/orig/).
  base__gridK   : the repo's outline step (the harness's outlines_copy.py) + the repo's step 4 (harness default)
  merged__gridK : the APPLIED merged outlines.py (orig/hook_outlines.py) + the applied blocks_noguide.step4 (orig/hook_step4.py)
Run folders: v-final/orig/runs/TAG/ (the harness writes next to itself). Writes v-final/orig_grid_runs.json.
    python -B run_orig.py [--jobs 3]
"""
import concurrent.futures as cf, json, os, subprocess, sys
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; INF = SP + 'bench_2026-11-21/inference/maps/'
NAMES = ['batch'] + [f'off{i}_tta1' for i in range(1, 6)]
VAR = {'base': [], 'merged': ['--outlines', V + 'orig/hook_outlines.py', '--step4', V + 'orig/hook_step4.py']}

def one(v, k):
    tag = f'{v}__grid{k}'; out = V + f'orig/runs/{tag}/bench44.json'
    if os.path.exists(out): return tag, json.load(open(out))
    cmd = ['python', '-B', V + 'orig/bench44.py', '--area', INF + f'{NAMES[k]}/44_area.png', '--lines', INF + f'{NAMES[k]}/44_lines.png', '--tag', tag, '--no-pic'] + VAR[v]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=env)
    open(V + f'orig/logs_{tag}.err', 'w', encoding='utf8').write(r.stderr)
    if r.returncode: return tag, dict(error=r.stderr[-2000:])
    return tag, json.load(open(out))

if __name__ == '__main__':
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 3
    res = {}
    t, d = one('base', 0); res[t] = d.get('headline', d); print(t, json.dumps(res[t].get('all', res[t]))[:400], flush=True)   # first alone: it makes the decided-ground cache
    todo = [(v, k) for v in VAR for k in range(6) if (v, k) != ('base', 0)]
    with cf.ThreadPoolExecutor(jobs) as ex:
        for tag, d in ex.map(lambda vk: one(*vk), todo):
            res[tag] = d.get('headline', d); print(tag, json.dumps(res[tag].get('all', res[tag]))[:400], flush=True)
            json.dump(res, open(V + 'orig_grid_runs.json', 'w'), indent=1)
    json.dump(res, open(V + 'orig_grid_runs.json', 'w'), indent=1)
