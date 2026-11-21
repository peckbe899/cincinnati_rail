"""Train the two block networks for plates that were never placed: the guide left blank (21 November 2026).

    From the repo folder (3D), in PowerShell:      python tools\\sanborn\\unet\\train_noguide.py
    (it starts the networks' own Python, tools/sanborn/unet/.venv, by itself; about an hour and a half on this machine)

Ben, 21 November 2026: "the code should have run the block recognition too ... set up the part of the code that is
supposed to run that too". The networks there were (edge_v1, lines_v2) need a guide drawn through a placement; with the
guide blank they call 48% of plate 44's ground rightly (blocks_noguide.py has the numbers). This trains the same two
networks on the same plates with the guide blank throughout, plate 44 held out whole as before:
  1. unet.py    train area_ng1  82A:all 80:all 43:all 45:all 44:val --no-guide       the area network (block or street)
  2. unet.py    predict area_ng1 P --no-guide, for each of the five plates           its answer, the line network's input
  3. edgenet.py train lines_ng1 82A 80 43 45 44:val --no-guide --area area_ng1       the line network (block lines)
The scores on plate 44 are printed as it goes and kept in unet_data/models/area_ng1.json and lines_ng1.json; the log is
unet_data/train_ng1.log. A step whose result is already there is skipped (--redo trains again). Afterwards
run_plates.py runs the block recognition on every plate that has no placement (blocks_noguide.py).
"""
import os, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.normpath(os.path.join(HERE, '..', '..', '..', 'data', 'sanborn'))
PY = os.path.join(HERE, '.venv', 'Scripts', 'python.exe'); U = os.path.join(DATA, 'unet_data'); LOG = os.path.join(U, 'train_ng1.log')
TRAIN, VAL = ['82A', '80', '43', '45'], '44'; AREA, LINES = 'area_ng1', 'lines_ng1'


def step(what, args, made):
    if os.path.exists(made) and '--redo' not in sys.argv: print(f'{what}: already there ({os.path.basename(made)})', flush=True); return
    print(f'{what} ...', flush=True); t0 = time.time()
    with open(LOG, 'a', encoding='utf8', newline='\n') as f:
        f.write(f'===== {time.strftime("%Y-%m-%d %H:%M:%S")} {" ".join(args)}\n'); f.flush()
        p = subprocess.Popen([PY, '-W', 'ignore'] + args, cwd=DATA, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf8', errors='replace')
        for line in p.stdout: f.write(line); f.flush(); print('   ' + line.rstrip()[:230], flush=True)
        if p.wait(): sys.exit(f'{what} FAILED (exit {p.returncode}); see {LOG}')
    if made.endswith('.done'): open(made, 'w').write(time.strftime('%Y-%m-%d %H:%M:%S'))   # the line network saves as it goes, so its file alone does not say it finished
    print(f'{what}: done in {(time.time() - t0) / 60:.0f} min', flush=True)


if __name__ == '__main__':
    if not os.path.exists(PY): sys.exit(f'the networks\' Python is not there: {PY}')
    it = sys.argv[sys.argv.index('--iters') + 1] if '--iters' in sys.argv else '4000'; un = os.path.join(HERE, 'unet.py'); en = os.path.join(HERE, 'edgenet.py')
    step('1/3 area network', [un, 'train', AREA] + [p + ':all' for p in TRAIN] + [VAL + ':val', '--no-guide', '--iters', it], os.path.join(U, 'models', AREA + '.json'))
    for p in TRAIN + [VAL]: step(f'2/3 area answer on plate {p}', [un, 'predict', AREA, p, '--no-guide'], os.path.join(U, f'{p}_pred_{AREA}.png'))
    step('3/3 line network', [en, 'train', LINES] + TRAIN + [VAL + ':val', '--no-guide', '--area', AREA, '--iters', it], os.path.join(U, 'models', LINES + '.done'))
    print('trained. Now run:  python tools\\sanborn\\unet\\run_plates.py')
