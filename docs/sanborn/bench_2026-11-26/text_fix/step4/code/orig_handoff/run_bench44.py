"""run_bench44.py (text_v1/handoff, 26 Nov 2026): the plate-44 line bench over the 6 tile grids (tools/sanborn/unet/bench44.py
--grids data/sanborn/bench44_maps, read only), with the outline step pointed at the hand-off copy that reads the mask
(outline_hook.py -> outlines_text.py) and the hand-off step 4 (step4_text.py). Writes only into handoff/runs/bench44/.

    cd data/sanborn; python -B bench_2026-11-25/text_v1/handoff/code/run_bench44.py CONFIG [CONFIG ...]
CONFIG:
  control   no mask: must give the stored baseline runs (diag/swap/runs_baseline44/base__grid*), against which it is paired
  ink       the mask (masks/44_text.png, codes 2,3) in the on-ink test only (--text-drop 0); paired with control
  inkdrop   the on-ink test and the 'on text' drop (--text-drop 0.5); paired with control
  states    inkdrop, but the shape step keeps the unmasked ink (--text-where states): only the side states change
  states0   states without the 'on text' drop (--text-drop 0)
  V2S1_control, V2S1_inkdrop   the same on the V2S1 pair's maps (train_v2_runs/eval/V2S1/maps44), for comparison"""
import glob, os, shutil, subprocess, sys, time
SP = os.getcwd().replace('\\', '/') + '/'; assert os.path.exists(SP + 'cufp'), 'run from data/sanborn'
TOOLS = os.path.normpath(SP + '../../tools/sanborn/unet').replace('\\', '/') + '/'
HO = SP + 'bench_2026-11-25/text_v1/handoff/'; CODE = HO + 'code/'; OUT = HO + 'runs/bench44/'; os.makedirs(OUT, exist_ok=True)
BR = SP + 'bench_2026-11-25/diag/swap/runs_baseline44/'
MAPS = {'base': SP + 'bench44_maps', 'V2S1': SP + 'train_v2_runs/eval/V2S1/maps44'}
STORED = {'base': BR + 'base__{grid}/bench44.json', 'V2S1': SP + 'train_v2_runs/eval/V2S1/runs44/v2__{grid}/bench44.json'}
CONF = {'control': ('base', '', '0.5', STORED['base']), 'ink': ('base', HO + 'masks/44_text.png', '0', OUT + 'control/runs44/v2__{grid}/bench44.json'),
        'inkdrop': ('base', HO + 'masks/44_text.png', '0.5', OUT + 'control/runs44/v2__{grid}/bench44.json'),
        'states': ('base', HO + 'masks/44_text.png', '0.5', OUT + 'control/runs44/v2__{grid}/bench44.json'),   # inkdrop with --text-where states
        'states0': ('base', HO + 'masks/44_text.png', '0', OUT + 'control/runs44/v2__{grid}/bench44.json'),   # ink with --text-where states (no drop)
        'V2S1_control': ('V2S1', '', '0.5', STORED['V2S1']), 'V2S1_inkdrop': ('V2S1', HO + 'masks/44_text.png', '0.5', OUT + 'V2S1_control/runs44/v2__{grid}/bench44.json'),
        'V2S1_states': ('V2S1', HO + 'masks/44_text.png', '0.5', OUT + 'V2S1_control/runs44/v2__{grid}/bench44.json')}
log = open(OUT + 'run_bench.log', 'a', encoding='utf8')
def say(*a):
    s = time.strftime('%Y-%m-%d %H:%M:%S ') + ' '.join(map(str, a)); print(s, flush=True); log.write(s + '\n'); log.flush()
for name in sys.argv[1:]:
    chain, mask, drop, paired = CONF[name]; out = OUT + f'{name}/'
    if os.path.exists(out + 'runs44/v2_grids.json'): say('skip (done)', name); continue
    os.makedirs(out + 'runs44/cache', exist_ok=True)
    for f in glob.glob(BR + 'cache/decided_half_*.png'):
        if not os.path.exists(out + 'runs44/cache/' + os.path.basename(f)): shutil.copyfile(f, out + 'runs44/cache/' + os.path.basename(f))
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'HANDOFF_TEXT_MASK': mask, 'HANDOFF_TEXT_DROP': drop, 'HANDOFF_TEXT_WHERE': 'states' if 'states' in name else 'both'}
    cmd = ['python', '-B', TOOLS + 'bench44.py', '--grids', MAPS[chain], '--tag', 'v2', '--runs', out + 'runs44', '--jobs', '3', '--no-pic',
           '--paired', paired, '--outlines', CODE + 'outline_hook.py', '--step4', CODE + 'step4_text.py']
    say('RUN', name, '| mask', mask or 'none', '| drop', drop); t0 = time.time()
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace', env=env)
    open(out + 'stdout.txt', 'w', encoding='utf8').write(' '.join(cmd) + '\n' + r.stdout[-200000:] + '\n---stderr---\n' + r.stderr[-20000:])
    say('done', name, 'exit', r.returncode, f'{time.time() - t0:.0f}s')
