"""lines_compare.py (text_v1/handoff, 26 Nov 2026): editor lines of the masked runs against the control run (no mask), per grid
and per plate, with the definitions of text/verify/scripts/lines_recheck.py (the verify agent's line scorer):
  shown lines       N_shown.json less state 'sheet', sampled every 1 px
  false length      samples more than 5 px from every line of Ben's (all kinds)
  false line        a shown line with under 20% of its samples within 8 px of Ben's lines
  on text           a false line with 50% or more of its samples within 5 px of text ink (the mask's codes 2, 3)
  Ben line found    50% or more of its samples within 5 px of a shown line; lost / gained against the control run
Lost Ben lines are cut out of the scan (control lines green, masked lines red, Ben's line blue, mask magenta) into
handoff/pics/lines_lost_<run>_<grid>_<k>.png for looking at by eye.

    cd data/sanborn; python -B bench_2026-11-25/text_v1/handoff/code/lines_compare.py
Writes handoff/scores/lines.json and lines.txt."""
import json, os
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = os.getcwd().replace('\\', '/') + '/'; HO = SP + 'bench_2026-11-25/text_v1/handoff/'; os.makedirs(HO + 'scores', exist_ok=True); os.makedirs(HO + 'pics', exist_ok=True)


def samples(lines):
    P, I = [], []
    for k, e in enumerate(lines):
        a, b = np.array(e['a'], float), np.array(e['b'], float); n = max(1, int(np.ceil(np.hypot(*(b - a)))))
        t = (np.arange(n) + 0.5) / n; P.append(a[None] + t[:, None] * (b - a)[None]); I.append(np.full(n, k))
    return (np.concatenate(P), np.concatenate(I)) if P else (np.zeros((0, 2)), np.zeros(0, int))


def run(rd, N, BT, BP, BI, nb, blen, tnear):
    f = rd + f'{N}_shown.json' if os.path.exists(rd + f'{N}_shown.json') else rd + '44_shown.json'   # bench44 names it 44_shown.json on every plate
    sh = [e for e in json.load(open(f, encoding='utf8')) if e.get('state') != 'sheet']
    P, I = samples(sh); d, _ = BT.query(P); n = len(sh); L = np.bincount(I, minlength=n).astype(float)
    fl = (np.bincount(I, d <= 8, n) / np.maximum(L, 1)) < 0.2
    x = np.clip(P[:, 0].round().astype(int), 0, tnear.shape[1] - 1); y = np.clip(P[:, 1].round().astype(int), 0, tnear.shape[0] - 1)
    ont = (np.bincount(I, tnear[y, x] > 0, n) / np.maximum(L, 1)) >= 0.5
    dd, _ = cKDTree(P).query(BP); found = (np.bincount(BI, dd <= 5, nb) / np.maximum(blen, 1)) >= 0.5
    return dict(false_len=int((d > 5).sum()), false_lines=int(fl.sum()), false_lines_on_text=int((fl & ont).sum()), shown_lines=n), found, sh


def pic(name, N, ben_line, sh0, sh1, tc, im):
    a, b = np.array(ben_line['a'], float), np.array(ben_line['b'], float); c = (a + b) / 2; r = max(80, int(np.hypot(*(b - a)) / 2) + 40)
    H, W = tc.shape; x0, y0 = max(0, int(c[0]) - r), max(0, int(c[1]) - r); x1, y1 = min(W, int(c[0]) + r), min(H, int(c[1]) + r)
    v = (im[y0:y1, x0:x1] * 0.6 + 100).astype(np.uint8); v[np.isin(tc[y0:y1, x0:x1], (2, 3))] = (255, 0, 255)
    for sh, col, th in ((sh0, (0, 170, 0), 5), (sh1, (0, 0, 230), 2)):
        for e in sh: cv2.line(v, tuple((np.array(e['a']) - [x0, y0]).round().astype(int).tolist()), tuple((np.array(e['b']) - [x0, y0]).round().astype(int).tolist()), col, th)
    cv2.line(v, tuple((a - [x0, y0]).round().astype(int).tolist()), tuple((b - [x0, y0]).round().astype(int).tolist()), (255, 120, 0), 1)
    s = 600 / max(v.shape[:2]); v = cv2.resize(v, None, fx=s, fy=s, interpolation=cv2.INTER_AREA) if s < 1 else v
    cv2.imwrite(HO + f'pics/{name}.png', v)


JOBS = [('44', f'bench44/{c}/runs44/v2__grid{g}/', f'bench44/{ctl}/runs44/v2__grid{g}/', f'{c}_grid{g}', SP + 'streetmap/22-44.json')
        for c, ctl in (('ink', 'control'), ('inkdrop', 'control'), ('states', 'control'), ('states0', 'control'), ('V2S1_inkdrop', 'V2S1_control'), ('V2S1_states', 'V2S1_control')) for g in range(6)
        if os.path.exists(HO + f'runs/bench44/{c}/runs44/v2__grid{g}/44_shown.json')]
JOBS += [(N, f'plates/{N}_{c}/', f'plates/{N}_control/', f'{N}_{c}', HO + f'truth/{N}_streetmap.json') for N in ('5', '1A') for c in ('ink', 'inkdrop', 'states', 'states0')]
out = {}; cache = {}; lines_txt = []
for N, rd, rc, name, tf in JOBS:
    if N not in cache:
        BL = json.load(open(tf, encoding='utf8'))['lines']; BP, BI = samples(BL); tc = cv2.imread(HO + f'masks/{N}_text.png', 0)
        tnear = cv2.dilate(np.isin(tc, (2, 3)).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
        cache[N] = (BL, cKDTree(BP), BP, BI, len(BL), np.bincount(BI, minlength=len(BL)), tnear, tc, cv2.imread(f'cufp/22-{N}.jpg'))
    BL, BT, BP, BI, nb, blen, tnear, tc, im = cache[N]
    s0, f0, sh0 = run(HO + 'runs/' + rc, N, BT, BP, BI, nb, blen, tnear); s1, f1, sh1 = run(HO + 'runs/' + rd, N, BT, BP, BI, nb, blen, tnear)
    lost = np.nonzero(f0 & ~f1)[0]; gained = np.nonzero(~f0 & f1)[0]
    r = dict(control=s0, masked=s1, ben_found0=int(f0.sum()), ben_found1=int(f1.sum()), lost=len(lost), gained=len(gained),
             lost_lines=[dict(k=int(k), kind=BL[k]['kind'], a=BL[k]['a'], b=BL[k]['b'], len=int(blen[k])) for k in lost],
             gained_lines=[dict(k=int(k), kind=BL[k]['kind'], len=int(blen[k])) for k in gained])
    for j, k in enumerate(lost): pic(f'lines_lost_{name}_{j}', N, BL[k], sh0, sh1, tc, im)
    for j, k in enumerate(gained): pic(f'lines_gained_{name}_{j}', N, BL[k], sh0, sh1, tc, im)
    out[name] = r
    lines_txt.append(f"{name:16s} false length {s0['false_len']:6d} -> {s1['false_len']:6d} | false lines {s0['false_lines']:3d} -> {s1['false_lines']:3d} (on text {s0['false_lines_on_text']:3d} -> {s1['false_lines_on_text']:3d}) | "
                     f"Ben lines found {r['ben_found0']} -> {r['ben_found1']} (lost {r['lost']}: {[(l['kind'], l['len']) for l in r['lost_lines']]}, gained {r['gained']}: {[(l['kind'], l['len']) for l in r['gained_lines']]})")
    print(lines_txt[-1], flush=True)
json.dump(out, open(HO + 'scores/lines.json', 'w', encoding='utf8', newline='\n'), indent=1)
open(HO + 'scores/lines.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(lines_txt) + '\n')
