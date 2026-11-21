"""v-44: every plate-44 bench run, through the ORIGINAL harness (an unchanged copy, v-44/harness/bench44.py; cmp-checked
against bench44/bench44.py), runs in v-44/harness/runs/TAG/. CPU only, nothing trained, read-only on the repo.

    python -B run_bench.py [--jobs 5] [--only PREFIX,...]

Chains (each on the 6 tile grids of inference/maps/{batch,off1..5_tta1}, and some on the guided maps):
  base      the repo's outline step (bench44/outlines_copy.py, an I/O-only copy of tools/sanborn/unet/outlines.py) + the
            repo's step 4 (the harness default)                                       = the batch chain
  A         outline-quality alone: outline-quality/proposed/outlines_redirected.py + its step 4 (hooks/step4_A.py)
  merged    the STAGED outlines.py (hooks/outlines_staged.py) + the STAGED blocks_noguide.step4 (hooks/step4_staged.py)
  ablations of merged:
    noholes    --hole-parent 1e-9 (every hole gated out)
    hp0        --hole-parent 0 (every hole kept)
    norail     same outlines as merged, step 4 with every 'on rail' side given back its 'was' state (no rail test)
    railshow   same outlines as merged, step 4 RAIL_DROP = False ('on rail' shown orange)
    blankbins  --bins-png v-44/abl/blank_bins_44.png (no railroad ink at all: must equal norail)
    railrule   railroad from the rule run inside the step, WITHOUT Ben's tracks (abl/railrule_noben/outlines.py,
               --bins-png none): what a plate with no rail of Ben's would get
    keepunl    same outlines as merged, step 4 KEEP_UNLINED = True (option 2)
Writes v-44/runs_index.json (tag -> headline)."""
import json, os, shutil, subprocess, sys, time, concurrent.futures as cf
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks'))
from common import V, DATA, U, BENCH, MAPS, GRIDS, STAGED, mine  # noqa: E402
HB = V + 'harness/bench44.py'; RUNS = V + 'harness/runs/'
OQ = BENCH + 'outline-quality/proposed/outlines_redirected.py'
HOOK_O, HOOK_S4, HOOK_A = V + 'hooks/outlines_staged.py', V + 'hooks/step4_staged.py', V + 'hooks/step4_A.py'
GUIDED = (U + '44_pred_edge_v1.png', U + '44_lines_lines_v2.png')


def cfgs():
    C = []
    maps = [(g, MAPS + f'{g}/44_area.png', MAPS + f'{g}/44_lines.png') for g in GRIDS] + [('guided',) + GUIDED]
    for g, ar, li in maps:
        C.append(dict(tag=f'base__{g}', area=ar, lines=li))
        C.append(dict(tag=f'A__{g}', area=ar, lines=li, outlines=OQ, step4=HOOK_A))
        C.append(dict(tag=f'merged__{g}', area=ar, lines=li, outlines=HOOK_O, step4=HOOK_S4))
        if g == 'guided': continue
        C.append(dict(tag=f'noholes__{g}', area=ar, lines=li, outlines=HOOK_O, step4=HOOK_S4, env=dict(V44_OUTLINE_ARGS=json.dumps(['--hole-parent', '1e-9']))))
        C.append(dict(tag=f'railrule__{g}', area=ar, lines=li, outlines=HOOK_O, step4=HOOK_S4,
                      env=dict(V44_OUTLINES_PY=V + 'abl/railrule_noben/outlines.py', V44_EXTRA_PATH=json.dumps([STAGED.rstrip('/')]), V44_OUTLINE_ARGS=json.dumps(['--bins-png', 'none']))))
        for v in ('norail', 'railshow', 'keepunl'):
            C.append(dict(tag=f'{v}__{g}', area=ar, lines=li, outlines=HOOK_O, step4=HOOK_S4, env=dict(V44_STEP4={'keepunl': 'keepunlined'}.get(v, v)), reuse_from=f'merged__{g}'))
        if g == 'batch':
            C.append(dict(tag=f'hp0__{g}', area=ar, lines=li, outlines=HOOK_O, step4=HOOK_S4, env=dict(V44_OUTLINE_ARGS=json.dumps(['--hole-parent', '0']))))
            C.append(dict(tag=f'blankbins__{g}', area=ar, lines=li, outlines=HOOK_O, step4=HOOK_S4, env=dict(V44_OUTLINE_ARGS=json.dumps(['--bins-png', V + 'abl/blank_bins_44.png']))))
    return C


def run(c):
    tag = c['tag']; d = mine(RUNS + tag) + '/'; out = d + 'bench44.json'
    if os.path.exists(out): return tag, json.load(open(out))['headline'], 0.0
    cmd = [sys.executable, '-B', HB, '--area', c['area'], '--lines', c['lines'], '--tag', tag]
    if tag.split('__')[1] != 'batch': cmd.append('--no-pic')
    if c.get('outlines'): cmd += ['--outlines', c['outlines']]
    if c.get('step4'): cmd += ['--step4', c['step4']]
    if c.get('reuse_from'):
        src = RUNS + c['reuse_from'] + '/'
        while not os.path.exists(src + 'bench44.json'): time.sleep(3)
        os.makedirs(d, exist_ok=True)
        for f in ('outlines.json', 'outline_step.json', '44_blockinst.png', '44_blockmask.png', '44_outlines.json', 'hook.json'):
            if os.path.exists(src + f): shutil.copy2(src + f, d + f)
        cmd.append('--reuse')
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **c.get('env', {}))
    t0 = time.time(); r = subprocess.run(cmd, cwd=DATA, capture_output=True, text=True, encoding='utf8', errors='replace', env=e)
    os.makedirs(d, exist_ok=True); open(d + 'harness_stderr.txt', 'w', encoding='utf8').write(r.stderr)
    json.dump(dict(cmd=cmd, env=c.get('env', {}), returncode=r.returncode), open(d + 'run_cmd.json', 'w'), indent=1)
    if r.returncode: return tag, dict(error=r.stderr[-2000:]), time.time() - t0
    return tag, json.load(open(out))['headline'], time.time() - t0


if __name__ == '__main__':
    jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 5
    only = sys.argv[sys.argv.index('--only') + 1].split(',') if '--only' in sys.argv else None
    C = [c for c in cfgs() if not only or c['tag'].split('__')[0] in only]
    C.sort(key=lambda c: bool(c.get('reuse_from')))          # the runs others reuse go first
    idx = json.load(open(V + 'runs_index.json')) if os.path.exists(V + 'runs_index.json') else {}
    with cf.ThreadPoolExecutor(jobs) as ex:
        for tag, h, s in ex.map(run, C):
            idx[tag] = h; a = h.get('all', h)
            print(f'{tag:22s} {s:5.0f}s', json.dumps({k: a.get(k) for k in ('PQ', 'recall_interior', 'precision', 'precision_green', 'ben_blocks_closed', 'delete_len', 'draw_len')}) if 'all' in h else h, flush=True)
            json.dump(idx, open(V + 'runs_index.json', 'w'), indent=1)
