"""Block recognition on a plate that was never placed: the two networks with a blank guide (21 November 2026).

    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/blocks_noguide.py N [N ...] [--pred-only] [--outlines-only] [--out DIR]

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
  4. the outline sides as lines for the line editor (step4 below)     -> unet_data/N_edges.json
     (green: on a printed line that the line network also drew; orange: not settled. Left out: sides along the paper's
     edge or the printed furniture of an uncut sheet, short pieces, sides on no line at all, and sides on the rail.)
Steps 3 and 4 are refused on a plate that has a guide (unet_data/N_guide.png): its outlines and lines come from the
placement and are not to be written over. --pred-only stops after step 2 (to score the blank guide on such a plate).
--outlines-only skips steps 1 and 2 and runs 3 and 4 on the maps already saved (unet_data/N_pred_AREA.png and
N_lines_LINES.png): the networks are slow, the outline step is not, and run_plates.py redoes only it when it changes.
--out DIR writes every output of steps 3 and 4 into DIR (outlines.py --out DIR, DIR/N_edges.json, DIR/N_blocks_ng.json)
and nothing into the repo; with steps 1 and 2 the two maps go there too.
Never touches edges_ben.json or rail_ben.json. These are the networks' guess, not ground truth.

21 November 2026, the merged outline step (outlines.py; Ben: "Yes, merge it"; data/sanborn/bench_2026-11-21/merge):
- step4() is a function of its own, importable without torch (outlines.py uses it for its QA flag, bench44.py scores
  it): the torch, unet and edgenet imports are inside the functions that run the networks.
- It leaves out sides 'not on a line' (outline-quality's option 1: on plate 44 those are 6% on Ben's lines). With the
  merged step on 44: shown lines on his 82.3%, 5 of his 55 blocks close, delete 21.6k px. KEEP_UNLINED = True is
  option 2: every side of the closed rings is shown (orange): 69.1%, 16 close, delete 50.7k px.
- Sides on the rail ('on rail' in outlines.json): RAIL_DROP says whether they are left out or shown orange. On 44 the
  34 such sides are 2.7% on Ben's lines; leaving them out takes the shown lines on his from 76.3% to 82.3%, recall
  from 62.3% to 62.1% and his delete length from 33.1k to 21.6k px (shown orange: 76.3%, 33.1k px). On the rail-yard
  plates 1B, 3, 2 and 41 they are yard tracks by eye. So they are left out (merge/impl rail_sides44.py, rail_crops.py).
- N_blocks_ng.json and the last line printed (run_plates.json 'blocks') carry the street holes, the bridging sides, the
  sides on the rail and outlines.py's QA flag (suspect, suspect_why and qa: Q1 little of the line network's length
  reaches the editor, Q2 blocks nested in block ground, Q3 a scale the networks were not trained at, Q5 no map ground
  found on an uncut sheet).
- Ben's edits (picks22_guided/22-N/edges_ben.json) are keyed to the lines of unet_data/N_edges.json (their a0, b0): a
  new N_edges.json leaves every edit of his hanging. So on a plate with edges_ben.json, N_edges.json is never written
  again; the new lines go to unet_data/N_edges.new.json, and the run says so.
- outline_version(): a short hash of outlines.py, blocks_noguide.py and map_area.py, the outline step's version
  (outlines.py writes it into N_outlines.json, run_plates.py keeps it per plate and redoes the step where it changed).
"""
import hashlib, json, os, subprocess, sys, time
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
SP = _ws.DATA; U = SP + 'unet_data/'; AREA, LINES = 'area_ng1', 'lines_ng1'   # trained with the guide blank: train_noguide.py
KEEP_UNLINED = False   # False: sides on no line at all are left out (option 1); True: shown orange, so more rings close (option 2)
RAIL_DROP = True       # sides lying on the railroad ink ('on rail'): left out (True) or shown orange (False); see the docstring
VERSION_FILES = ('outlines.py', 'blocks_noguide.py', 'map_area.py')


def outline_version():
    """the outline step's version: a short hash of outlines.py, blocks_noguide.py and map_area.py"""
    h = hashlib.sha256()
    for f in VERSION_FILES:
        p = os.path.join(HERE, f)
        h.update(f.encode() + b'\0' + (open(p, 'rb').read() if os.path.exists(p) else b'missing') + b'\0')
    return h.hexdigest()[:12]


def step4(polys, keep_unlined=None, rail_drop=None):
    """the outline sides (outlines.json) as the line editor's lines (N_edges.json): green where the side is on a printed
    line the line network also drew ('on print'), orange where it is not settled. Left out: short pieces, sides along the
    paper's edge (paper_edge), sides on no line at all ('not on a line', unless keep_unlined) and sides on the rail
    ('on rail', if rail_drop). The sides of a street hole (hole=True) and the bridging sides are lines like any other."""
    keep_unlined = KEEP_UNLINED if keep_unlined is None else keep_unlined; rail_drop = RAIL_DROP if rail_drop is None else rail_drop
    out = []
    for poly in polys:
        for s in poly:
            st = s['state']
            if st == 'short' or s.get('paper_edge') or (st == 'not on a line' and not keep_unlined) or (st == 'on rail' and rail_drop): continue
            out.append(dict(src='read', name='', a=s['a'], b=s['b'], state='green' if st == 'on print' else 'orange'))
    return out


def predict(N, nets, odir):
    """steps 1 and 2: the two networks' maps of plate N, written into odir (unet_data/ or --out DIR)"""
    import unet as A, edgenet as E  # noqa: E402   (torch: only here)
    dev, na, nl = nets
    full = cv2.imread(SP + f'cufp/22-{N}.jpg')
    if full is None: raise RuntimeError(f'no scan cufp/22-{N}.jpg')
    H, W = full.shape[:2]; img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); z = np.zeros(img.shape[:2], np.uint8)
    p = A.predict_full(na, dev, np.dstack([img[:, :, ::-1], z, z])); pa = (p * 255).astype(np.uint8); cv2.imwrite(odir + f'{N}_pred_{AREA}.png', pa)
    inkimg, _ = E.ink_image(full); Z = np.zeros((H, W), np.uint8)
    x = np.dstack([full[:, :, ::-1], inkimg, Z, Z, cv2.resize(pa, (W, H), interpolation=cv2.INTER_LINEAR)])
    q = E.predict_full(nl, dev, x); cv2.imwrite(odir + f'{N}_lines_{LINES}.png', (q * 255).astype(np.uint8))
    return f'plate {N:4s} block share {float((p > 0.5).mean()):.2f}, line share {float((q > 0.5).mean()):.3f}'


def run(N, nets, pred_only, outlines_only=False, out=None):
    t0 = time.time(); odir = (os.path.abspath(out).replace('\\', '/') + '/') if out else U
    if out: os.makedirs(odir, exist_ok=True)
    if outlines_only:
        maps = [odir + f'{N}_pred_{AREA}.png', odir + f'{N}_lines_{LINES}.png']
        if out and not all(os.path.exists(m) for m in maps): maps = [U + f'{N}_pred_{AREA}.png', U + f'{N}_lines_{LINES}.png']   # --out: the saved maps of the plate
        if not all(os.path.exists(m) for m in maps): raise RuntimeError(f'--outlines-only: no saved maps ({", ".join(os.path.basename(m) for m in maps)}); run the networks first')
        pa = cv2.imread(maps[0], 0); msg = f'plate {N:4s} block share {float((pa > 127).mean()):.2f}, maps as saved'; del pa
    else:
        msg = predict(N, nets, odir); maps = [odir + f'{N}_pred_{AREA}.png', odir + f'{N}_lines_{LINES}.png']
    if pred_only: print(msg, f'| {time.time() - t0:.0f} s', flush=True); return
    if os.path.exists(U + f'{N}_guide.png'): print(msg, '| has a guide: outlines and lines left as they are', flush=True); return
    cmd = [sys.executable, os.path.join(HERE, 'outlines.py'), N, AREA, LINES]
    if out: cmd += ['--out', odir, '--area-png', maps[0], '--lines-png', maps[1]]
    r = subprocess.run(cmd, cwd=SP, capture_output=True, text=True, encoding='utf8', errors='replace')
    if r.returncode: raise RuntimeError('outlines: ' + ((r.stderr + r.stdout).strip().splitlines() or ['failed'])[-1])
    rep = json.loads(r.stdout.strip().splitlines()[-1])
    out_e = step4(json.load(open((odir + 'outlines.json') if out else SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8')))
    ef = odir + f'{N}_edges.json'; note = ''
    if not out and os.path.exists(SP + f'picks22_guided/22-{N}/edges_ben.json'):
        # Ben's edits are keyed to the lines of N_edges.json: a new N_edges.json would leave them hanging
        ef = U + f'{N}_edges.new.json'; note = f' | Ben has edited this plate\'s lines (picks22_guided/22-{N}/edges_ben.json, keyed to unet_data/{N}_edges.json): N_edges.json left as it is, the new lines are in {N}_edges.new.json'
    json.dump(out_e, open(ef + '.tmp', 'w', encoding='utf8', newline='\n')); os.replace(ef + '.tmp', ef)
    green = sum(o['state'] == 'green' for o in out_e); why = rep.get('suspect_why', [])
    json.dump(dict(plate=N, made=int(time.time()), how='networks with a blank guide (blocks_noguide.py); not ground truth', area=AREA, lines=LINES, version=rep.get('version'),
                   blocks=rep['blocks'], holes=rep.get('holes', 0), bridges=rep.get('bridges', 0), on_rail=rep.get('on_rail'), rail=rep.get('rail'), sides=len(out_e), green=green,
                   edges_file=os.path.basename(ef), keep_unlined=KEEP_UNLINED, rail_drop=RAIL_DROP, share_on_printed_line_by_length=rep['share_on_printed_line_by_length'],
                   suspect=bool(why), suspect_why=why, qa=rep.get('qa', {})), open(odir + f'{N}_blocks_ng.json', 'w', encoding='utf8', newline='\n'), indent=1)
    print(msg, f"| {rep['blocks']} blocks, {rep.get('holes', 0)} holes, {len(out_e)} sides, {green} green ({100 * rep['share_on_printed_line_by_length']:.0f}% of side length on ink), "
          f"{rep.get('bridges', 0)} bridges, {rep.get('on_rail') or 0} on the rail | {time.time() - t0:.0f} s" + (' | SUSPECT: ' + '; '.join(why) if why else '') + note, flush=True)


if __name__ == '__main__':
    pl = [a for a in sys.argv[1:] if not a.startswith('--')]; out = None
    if '--out' in sys.argv: out = sys.argv[sys.argv.index('--out') + 1]; pl.remove(out)
    only = '--outlines-only' in sys.argv; nets = None
    if not only:
        import torch  # noqa: E402
        import unet as A  # noqa: E402
        for m in (AREA, LINES):
            if not os.path.exists(U + f'models/{m}.pt'): sys.exit(f'no network {m} yet (unet_data/models/{m}.pt): train it first with train_noguide.py')
        dev = A.device()
        na = A.UNet(); na.load_state_dict(torch.load(U + f'models/{AREA}.pt', map_location='cpu')); na.to(dev)
        nl = A.UNet(classes=2, in_ch=7); nl.load_state_dict(torch.load(U + f'models/{LINES}.pt', map_location='cpu')); nl.to(dev)
        nets = (dev, na, nl)
    bad = 0
    for n in pl:
        try: run(n, nets, '--pred-only' in sys.argv, only, out)
        except Exception as e: bad += 1; print(f'plate {n:4s} FAILED: {e}', flush=True)
    sys.exit(1 if bad else 0)
