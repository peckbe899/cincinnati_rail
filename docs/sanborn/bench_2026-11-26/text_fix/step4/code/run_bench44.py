"""run_bench44.py (text_fix/step4, 27 Nov 2026): copy of text_v1/handoff/code/run_bench44.py with the mask set as a choice.
The plate-44 line bench over the 6 tile grids (tools/sanborn/unet/bench44.py --grids data/sanborn/bench44_maps, read
only), the outline step pointed at the hand-off copy that reads the mask (outline_hook.py -> outlines_text.py, byte
copies) and the hand-off step 4 (step4_text.py, byte copy). Writes only into step4/runs/bench44/.

    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/run_bench44.py CONFIG [CONFIG ...]
CONFIG:
  control          no mask: must give the stored baseline runs (diag/swap/runs_baseline44/base__grid*), paired with them
  f3_ink, f4_ink   the mask (step4/masks/<set>/44_text.png, codes 2,3) in the on-ink test only, "both" variant,
                   no 'on text' drop (--text-drop 0); paired with control
  f3_states0, f4_states0   the same with --text-where states (the shape step keeps the unmasked ink)"""
import glob, os, shutil, subprocess, sys, time
SP = os.getcwd().replace('\\', '/') + '/'; assert os.path.exists(SP + 'cufp'), 'run from data/sanborn'
TOOLS = os.path.normpath(SP + '../../tools/sanborn/unet').replace('\\', '/') + '/'
ST = SP + 'bench_2026-11-26/text_fix/step4/'; CODE = ST + 'code/'; OUT = ST + 'runs/bench44/'; os.makedirs(OUT, exist_ok=True)
BR = SP + 'bench_2026-11-25/diag/swap/runs_baseline44/'
MAPS = SP + 'bench44_maps'; STORED = BR + 'base__{grid}/bench44.json'; CTL = OUT + 'control/runs44/v2__{grid}/bench44.json'
CONF = {'control': ('', '0.5', STORED, 'both')}
for s in ('f3', 'f4'):
    CONF[f'{s}_ink'] = (ST + f'masks/{s}/44_text.png', '0', CTL, 'both')
    CONF[f'{s}_states0'] = (ST + f'masks/{s}/44_text.png', '0', CTL, 'states')
log = open(OUT + 'run_bench.log', 'a', encoding='utf8')
def say(*a):
    s = time.strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(map(str, a)); print(s, flush=True); log.write(s + '\n'); log.flush()
for name in sys.argv[1:]:
    mask, drop, paired, where = CONF[name]; out = OUT + f'{name}/'
    if os.path.exists(out + 'runs44/v2_grids.json'): say('skip (done)', name); continue
    os.makedirs(out + 'runs44/cache', exist_ok=True)
    for f in glob.glob(BR + 'cache/decided_half_*.png'):
        if not os.path.exists(out + 'runs44/cache/' + os.path.basename(f)): shutil.copyfile(f, out + 'runs44/cache/' + os.path.basename(f))
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'HANDOFF_TEXT_MASK': mask, 'HANDOFF_TEXT_DROP': drop, 'HANDOFF_TEXT_WHERE': where}
    cmd = ['python', '-B', TOOLS + 'bench44.py', '--grids', MAPS, '--tag', 'v2', '--runs', out + 'runs44', '--jobs', '3', '--no-pic',
           '--paired', paired, '--outlines', CODE + 'outline_hook.py', '--step4', CODE + 'step4_text.py']
    say('RUN', name, '| mask', mask or 'none', '| drop', drop, '| where', where); t0 = time.time()
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=env)
    open(out + 'stdout.txt', 'w', encoding='utf8').write(' '.join(cmd) + '\n' + r.stdout[-200000:] + '\n---stderr---\n' + r.stderr[-20000:])
    say('done', name, 'exit', r.returncode, f'{time.time() - t0:.0f}s')
