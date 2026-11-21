"""Block recognition on a plate that was never placed: the two networks with a blank guide (21 November 2026).

    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/blocks_noguide.py N [N ...] [--pred-only]

Ben, 21 November 2026, after checking the rail on plate 1A: "the code should have run the block recognition too. Did
it? if not, set up the part of the code that is supposed to run that too". It had not: the batch (run_plates.py) only
sorted the ink and traced the rail. The block recognition (unet.py's area network, edgenet.py's line network,
outlines.py) was built for a PLACED plate: both networks take a guide, today's blocks and centre lines drawn onto the
plate through its placement, and only 43, 44, 45, 80 and 82A have one. Those networks (edge_v1, lines_v2) do not work
with the guide left blank. Measured on plate 44, which neither was trained on: ground called block or street rightly
94.7% with the guide, 48.2% with it blank; of Ben's street lines 76% found with the guide and 61% blank, and of what the
line network drew 62% lay on his lines with the guide, 29% blank. So a second pair is trained with the guide blank
throughout (train_noguide.py: area_ng1, lines_ng1), and that pair is run here:
  1. area network  (AREA)  scan at half size + blank guide            -> unet_data/N_pred_AREA.png   P(block)
  2. line network  (LINES) scan, ink image, blank guide, that P(block) -> unet_data/N_lines_LINES.png P(block line)
  3. outlines.py N AREA LINES                                          -> picks22_guided/22-N/outlines.json, N_outlines.jpg
  4. the outline sides as lines for the line editor                    -> unet_data/N_edges.json
     (green: on a printed line that the line network also drew; orange: not settled. Sides along the paper's edge,
     short pieces and sides on no line at all are left out: on plate 44 those are 5-7% right, bench_2026-11-21.)
Steps 3 and 4 are refused on a plate that has a guide (unet_data/N_guide.png): its outlines and lines come from the
placement and are not to be written over. --pred-only stops after step 2 (to score the blank guide on such a plate).
Never touches edges_ben.json or rail_ben.json. These are the networks' guess, not ground truth.
"""
import json, os, subprocess, sys, time
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'; OUT = HERE.replace(chr(92), '/') + '/../bng_run/'; os.makedirs(OUT, exist_ok=True); AREA, LINES = 'area_ng1', 'lines_ng1'   # trained with the guide blank: train_noguide.py


def run(N, nets, pred_only):
    t0 = time.time(); dev, na, nl = nets
    full = cv2.imread(SP + f'cufp/22-{N}.jpg')
    if full is None: raise RuntimeError(f'no scan cufp/22-{N}.jpg')
    H, W = full.shape[:2]; img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); z = np.zeros(img.shape[:2], np.uint8)
    pa = cv2.imread(U + f'{N}_pred_{AREA}.png', 0); p = pa / 255.0   # REDIRECTED: stored map instead of the network
    q = cv2.imread(U + f'{N}_lines_{LINES}.png', 0) / 255.0   # REDIRECTED: stored map instead of the network
    msg = f'plate {N:4s} block share {float((p > 0.5).mean()):.2f}, line share {float((q > 0.5).mean()):.3f}'
    if pred_only: print(msg, f'| {time.time() - t0:.0f} s', flush=True); return
    if os.path.exists(U + f'{N}_guide.png') and '--ignore-guide' not in sys.argv: print(msg, '| has a guide: outlines and lines left as they are', flush=True); return
    r = subprocess.run([sys.executable, os.path.join(HERE, 'outlines_redirected.py'), N, AREA, LINES, OUT + f'{N}/'], cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
    if r.returncode: raise RuntimeError('outlines: ' + (r.stderr.strip().splitlines() or ['failed'])[-1])
    rep = json.loads(r.stdout.strip().splitlines()[-1]); out = []
    for poly in json.load(open(OUT + f'{N}/outlines.json', encoding='utf8')):
        for s in poly:
            if s['state'] in ('short', 'not on a line') or s.get('paper_edge'): continue
            out.append(dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange'))
    json.dump(out, open(OUT + f'{N}_edges.json.tmp', 'w', encoding='utf8', newline='\n')); os.replace(OUT + f'{N}_edges.json.tmp', OUT + f'{N}_edges.json')
    json.dump(dict(plate=N, made=int(time.time()), how='networks with a blank guide (blocks_noguide.py); not ground truth', area=AREA, lines=LINES, blocks=rep['blocks'], sides=len(out), bridges=rep.get('bridges', 0),
                   green=sum(o['state'] == 'green' for o in out), share_on_printed_line_by_length=rep['share_on_printed_line_by_length']), open(OUT + f'{N}_blocks_ng.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(msg, f"| {rep['blocks']} blocks, {len(out)} sides, {sum(o['state'] == 'green' for o in out)} on a printed line ({100 * rep['share_on_printed_line_by_length']:.0f}% by length) | {time.time() - t0:.0f} s", flush=True)


if __name__ == '__main__':
    pl = [a for a in sys.argv[1:] if not a.startswith('--')]
    dev = na = nl = None   # REDIRECTED: no networks
    bad = 0
    for n in pl:
        try: run(n, (dev, na, nl), '--pred-only' in sys.argv)
        except Exception as e: bad += 1; print(f'plate {n:4s} FAILED: {e}', flush=True)
    sys.exit(1 if bad else 0)
