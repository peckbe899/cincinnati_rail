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
     (green: on a printed line; orange: not settled. Sides along the paper's edge and short pieces are left out.
     On an uncut PDF sheet the paper's edge is the edge of its map ground, so margin, KEY and title sides are left out
     too. The sides of a street hole in block ground, hole=True in outlines.json, are street sides like any other.)
     N_blocks_ng.json and the last line printed (run_plates.json 'blocks') carry outlines.py's QA flag: 'SUSPECT' and
     the reasons (Q1 little of the line network's length reaches the editor, Q2 blocks nested in block ground, Q3 a scale
     the networks were not trained at, Q5 no map ground found on an uncut sheet).
Steps 3 and 4 are refused on a plate that has a guide (unet_data/N_guide.png): its outlines and lines come from the
placement and are not to be written over. --pred-only stops after step 2 (to score the blank guide on such a plate).
Never touches edges_ben.json or rail_ben.json. These are the networks' guess, not ground truth.
"""
import json, os, subprocess, sys, time
import numpy as np
import cv2
import torch
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
import unet as A, edgenet as E  # noqa: E402
SP = _ws.DATA; U = SP + 'unet_data/'; AREA, LINES = 'area_ng1', 'lines_ng1'   # trained with the guide blank: train_noguide.py


def run(N, nets, pred_only):
    t0 = time.time(); dev, na, nl = nets
    full = cv2.imread(SP + f'cufp/22-{N}.jpg')
    if full is None: raise RuntimeError(f'no scan cufp/22-{N}.jpg')
    H, W = full.shape[:2]; img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); z = np.zeros(img.shape[:2], np.uint8)
    p = A.predict_full(na, dev, np.dstack([img[:, :, ::-1], z, z])); pa = (p * 255).astype(np.uint8); cv2.imwrite(U + f'{N}_pred_{AREA}.png', pa)
    inkimg, _ = E.ink_image(full); Z = np.zeros((H, W), np.uint8)
    x = np.dstack([full[:, :, ::-1], inkimg, Z, Z, cv2.resize(pa, (W, H), interpolation=cv2.INTER_LINEAR)])
    q = E.predict_full(nl, dev, x); cv2.imwrite(U + f'{N}_lines_{LINES}.png', (q * 255).astype(np.uint8))
    msg = f'plate {N:4s} block share {float((p > 0.5).mean()):.2f}, line share {float((q > 0.5).mean()):.3f}'
    if pred_only: print(msg, f'| {time.time() - t0:.0f} s', flush=True); return
    if os.path.exists(U + f'{N}_guide.png'): print(msg, '| has a guide: outlines and lines left as they are', flush=True); return
    r = subprocess.run([sys.executable, os.path.join(HERE, 'outlines.py'), N, AREA, LINES], cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
    if r.returncode: raise RuntimeError('outlines: ' + (r.stderr.strip().splitlines() or ['failed'])[-1])
    rep = json.loads(r.stdout.strip().splitlines()[-1]); out = []
    for poly in json.load(open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8')):
        for s in poly:
            if s['state'] == 'short' or s.get('paper_edge'): continue
            out.append(dict(src='read', name='', a=s['a'], b=s['b'], state='green' if s['state'] == 'on print' else 'orange'))
    json.dump(out, open(U + f'{N}_edges.json.tmp', 'w', encoding='utf8', newline='\n')); os.replace(U + f'{N}_edges.json.tmp', U + f'{N}_edges.json')
    why = rep.get('suspect_why', [])
    json.dump(dict(plate=N, made=int(time.time()), how='networks with a blank guide (blocks_noguide.py); not ground truth', area=AREA, lines=LINES, blocks=rep['blocks'], holes=rep.get('holes', 0), sides=len(out),
                   green=sum(o['state'] == 'green' for o in out), share_on_printed_line_by_length=rep['share_on_printed_line_by_length'], suspect=bool(why), suspect_why=why, qa=rep.get('qa', {})),
              open(U + f'{N}_blocks_ng.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(msg, f"| {rep['blocks']} blocks, {len(out)} sides, {sum(o['state'] == 'green' for o in out)} on a printed line ({100 * rep['share_on_printed_line_by_length']:.0f}% by length) | {time.time() - t0:.0f} s"
          + (' | SUSPECT: ' + '; '.join(why) if why else ''), flush=True)


if __name__ == '__main__':
    pl = [a for a in sys.argv[1:] if not a.startswith('--')]
    for m in (AREA, LINES):
        if not os.path.exists(U + f'models/{m}.pt'): sys.exit(f'no network {m} yet (unet_data/models/{m}.pt): train it first with train_noguide.py')
    dev = A.device()
    na = A.UNet(); na.load_state_dict(torch.load(U + f'models/{AREA}.pt', map_location='cpu')); na.to(dev)
    nl = A.UNet(classes=2, in_ch=7); nl.load_state_dict(torch.load(U + f'models/{LINES}.pt', map_location='cpu')); nl.to(dev)
    bad = 0
    for n in pl:
        try: run(n, (dev, na, nl), '--pred-only' in sys.argv)
        except Exception as e: bad += 1; print(f'plate {n:4s} FAILED: {e}', flush=True)
    sys.exit(1 if bad else 0)
