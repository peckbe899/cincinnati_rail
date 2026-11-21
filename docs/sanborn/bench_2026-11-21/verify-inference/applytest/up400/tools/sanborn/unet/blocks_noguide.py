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
     (green: on a printed line; orange: not settled. Sides along the paper's edge and short pieces are left out.)
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
# The area network's answer is averaged over its 8 turns and flips (unet.predict_full tta). Measured on plate 44 against
# Ben's street map, mean of 6 tile grids (bench_2026-11-21/inference): PQ 0.442 -> 0.482, higher on all 6 grids; his
# interior lines found 53.6% -> 55.8%, precision unchanged. About 6 s more per plate on the GPU. The line network
# stays at one pass (its TTA gained nothing on 44). The scans are not resampled: on 44 (100 ft) the area network at
# the 200-ft size scored PQ 0.12, and at twice the size 0.00.
AREA_TTA = 8
# OPTIONAL (not yet checked against truth): the 400-ft plates (census scale table, read on each sheet's printed note) are
# shown to both networks at twice the size, so their streets have the 200-ft widths the networks were taught, and then
# every dark line is thinned back by a PEN x PEN max filter (at twice the size the pen lines would be twice as wide as
# on any training plate; on 44 a 2 px change of pen width alone took PQ from 0.43 to 0.00-0.03). The maps are resized
# back to the plate's own size, so the outline step is unchanged. Judged by eye on 10 plates (bench_2026-11-21/inference,
# random samples of exported sides): about 90% of the exported length on a street side against 77% for the batch, and
# about 18% more right length; not on any ground truth. Measured with one area pass, so TTA stays off here.
FT400 = {'46', '47', '48', '49', '50', '92', '93A', '93B', '94', '95'}; PEN = 3


def run(N, nets, pred_only):
    t0 = time.time(); dev, na, nl = nets
    full = cv2.imread(SP + f'cufp/22-{N}.jpg')
    if full is None: raise RuntimeError(f'no scan cufp/22-{N}.jpg')
    H, W = full.shape[:2]; up = N in FT400; thin = lambda a: cv2.dilate(a, np.ones((PEN, PEN), np.uint8))
    if up: img = thin(cv2.resize(full, (2 * (W // 2), 2 * (H // 2)), interpolation=cv2.INTER_AREA if 2 * (W // 2) < W else cv2.INTER_CUBIC))
    else: img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    z = np.zeros(img.shape[:2], np.uint8)
    p = A.predict_full(na, dev, np.dstack([img[:, :, ::-1], z, z]), tta=1 if up else AREA_TTA)
    if up: p = cv2.resize(p, (W // 2, H // 2), interpolation=cv2.INTER_LINEAR)
    pa = (p * 255).astype(np.uint8); cv2.imwrite(U + f'{N}_pred_{AREA}.png', pa)
    f = thin(cv2.resize(full, (2 * W, 2 * H), interpolation=cv2.INTER_CUBIC)) if up else full; h, w = f.shape[:2]   # about 7 GB of memory on a PDF sheet
    inkimg, _ = E.ink_image(f); Z = np.zeros((h, w), np.uint8)
    x = np.dstack([f[:, :, ::-1], inkimg, Z, Z, cv2.resize(pa, (w, h), interpolation=cv2.INTER_LINEAR)]); del f, inkimg
    q = E.predict_full(nl, dev, x); del x
    if up: q = cv2.resize(q, (W, H), interpolation=cv2.INTER_LINEAR)
    cv2.imwrite(U + f'{N}_lines_{LINES}.png', (q * 255).astype(np.uint8))
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
    json.dump(dict(plate=N, made=int(time.time()), how='networks with a blank guide (blocks_noguide.py); not ground truth', area=AREA, lines=LINES, area_tta=1 if N in FT400 else AREA_TTA, resampled_x2_pen_thinned=N in FT400, blocks=rep['blocks'], sides=len(out),
                   green=sum(o['state'] == 'green' for o in out), share_on_printed_line_by_length=rep['share_on_printed_line_by_length']), open(U + f'{N}_blocks_ng.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(msg, f"| {rep['blocks']} blocks, {len(out)} sides, {sum(o['state'] == 'green' for o in out)} on a printed line ({100 * rep['share_on_printed_line_by_length']:.0f}% by length) | {time.time() - t0:.0f} s", flush=True)


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
