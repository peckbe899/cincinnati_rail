"""lines_compare.py (text_fix/step4, 27 Nov 2026): copy of text_v1/handoff/code/lines_compare.py for both mask sets, plus a
direct finder4-against-finder3 comparison. Editor lines of the masked runs against a reference run, per grid and per
plate, with the hand-off's definitions:
  shown lines       N_shown.json less state 'sheet', sampled every 1 px
  false length      samples more than 5 px from every line of Ben's (all kinds)
  false line        a shown line with under 20% of its samples within 8 px of Ben's lines
  on text           a false line with 50% or more of its samples within 5 px of text ink (the run's own mask, codes 2, 3)
  Ben line found    50% or more of its samples within 5 px of a shown line; lost / gained against the reference run
References: f3_* and f4_* against the control run (no mask); 'f4vf3_*': the f4 run against the f3 run of the same
variant ('on text' then uses the f4 mask). Lost and gained Ben lines are cut out of the scan (reference lines green,
compared lines red, Ben's line blue, the compared run's mask magenta) into step4/pics/lines/<name>_<k>.png.

    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/lines_compare.py
Writes step4/scores/lines.json and lines.txt."""
import json, os
import numpy as np, cv2
from scipy.spatial import cKDTree
SP = os.getcwd().replace('\\', '/') + '/'; ST = SP + 'bench_2026-11-26/text_fix/step4/'; PIC = ST + 'pics/lines/'
os.makedirs(ST + 'scores', exist_ok=True); os.makedirs(PIC, exist_ok=True)


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
    cv2.imwrite(PIC + f'{name}.png', v)


JOBS = []   # (plate, compared run dir, reference run dir, name, truth file, mask set of the compared run)
for c, ref in (('f3_ink', 'control'), ('f3_states0', 'control'), ('f4_ink', 'control'), ('f4_states0', 'control'), ('f4_ink', 'f3_ink'), ('f4_states0', 'f3_states0')):
    nm = c if ref == 'control' else 'f4vf3_' + c.split('_', 1)[1]
    JOBS += [('44', f'bench44/{c}/runs44/v2__grid{g}/', f'bench44/{ref}/runs44/v2__grid{g}/', f'{nm}_grid{g}', SP + 'streetmap/22-44.json', c[:2]) for g in range(6)
             if os.path.exists(ST + f'runs/bench44/{c}/runs44/v2__grid{g}/44_shown.json') and os.path.exists(ST + f'runs/bench44/{ref}/runs44/v2__grid{g}/44_shown.json')]
    JOBS += [(N, f'plates/{N}_{c}/', f'plates/{N}_{ref}/', f'{N}_{nm}', ST + f'truth/{N}_streetmap.json', c[:2]) for N in ('5', '1A')
             if os.path.exists(ST + f'runs/plates/{N}_{c}/bench_plate.json') and os.path.exists(ST + f'runs/plates/{N}_{ref}/bench_plate.json')]
out = {}; cache = {}; lines_txt = []
for N, rd, rc, name, tf, S in JOBS:
    if (N, S) not in cache:
        BL = json.load(open(tf, encoding='utf8'))['lines']; BP, BI = samples(BL); tc = cv2.imread(ST + f'masks/{S}/{N}_text.png', 0)
        tnear = cv2.dilate(np.isin(tc, (2, 3)).astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11)))
        cache[(N, S)] = (BL, cKDTree(BP), BP, BI, len(BL), np.bincount(BI, minlength=len(BL)), tnear, tc, cv2.imread(f'cufp/22-{N}.jpg'))
    BL, BT, BP, BI, nb, blen, tnear, tc, im = cache[(N, S)]
    s0, f0, sh0 = run(ST + 'runs/' + rc, N, BT, BP, BI, nb, blen, tnear); s1, f1, sh1 = run(ST + 'runs/' + rd, N, BT, BP, BI, nb, blen, tnear)
    lost = np.nonzero(f0 & ~f1)[0]; gained = np.nonzero(~f0 & f1)[0]
    r = dict(reference=rc, compared=rd, control=s0, masked=s1, ben_found0=int(f0.sum()), ben_found1=int(f1.sum()), lost=len(lost), gained=len(gained),
             lost_lines=[dict(k=int(k), kind=BL[k]['kind'], a=BL[k]['a'], b=BL[k]['b'], len=int(blen[k])) for k in lost],
             gained_lines=[dict(k=int(k), kind=BL[k]['kind'], a=BL[k]['a'], b=BL[k]['b'], len=int(blen[k])) for k in gained])
    for j, k in enumerate(lost): pic(f'lost_{name}_{j}', N, BL[k], sh0, sh1, tc, im)
    for j, k in enumerate(gained): pic(f'gained_{name}_{j}', N, BL[k], sh0, sh1, tc, im)
    out[name] = r
    lines_txt.append(f"{name:20s} false length {s0['false_len']:6d} -> {s1['false_len']:6d} | false lines {s0['false_lines']:3d} -> {s1['false_lines']:3d} (on text {s0['false_lines_on_text']:3d} -> {s1['false_lines_on_text']:3d}) | "
                     f"Ben lines found {r['ben_found0']} -> {r['ben_found1']} (lost {r['lost']}: {[(l['kind'], l['len'], [round(v) for v in l['a']]) for l in r['lost_lines']]}, gained {r['gained']}: {[(l['kind'], l['len'], [round(v) for v in l['a']]) for l in r['gained_lines']]})")
    print(lines_txt[-1], flush=True)
json.dump(out, open(ST + 'scores/lines.json', 'w', encoding='utf8', newline='\n'), indent=1)
open(ST + 'scores/lines.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(lines_txt) + '\n')
