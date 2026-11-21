"""Tick angle (ink_bins RAIL 'across', batch 0.7) on plate 44's folds and on 1A (rail-rules, 21 Nov 2026). Read-only.
Bins: 0.7 = runs/44_nomap_prop_bins.png; 0.6 = across/44_a0.6_bins.png (run_ink_bins.py --rail); 0.55 and 0.45 = the rail
agent's rail/exp/across/44_a0.55_bins.png, 44_a0.45_bins.png (same rules, --nomap). Railroad traced with orig tracing, then
with the 'single 600/60' filter. Prints railroad R/P/F1 at 10 px per fold, and 1A's railroad tracks (all on label text).
    cd data/sanborn
    python bench_2026-11-21/rail-rules/across44.py"""
import sys, os, json, importlib.util
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from fold_score import fscore
spec = importlib.util.spec_from_file_location('rt', os.path.join(HERE, 'proposed', 'rail_tracks.py')); rt = importlib.util.module_from_spec(spec); spec.loader.exec_module(rt)
T44 = json.load(open('picks22_guided/22-44/rail_ben.page_2026-11-21.json', encoding='utf8'))
B = {'0.7': os.path.join(HERE, 'runs/44_nomap_prop_bins.png'), '0.6': os.path.join(HERE, 'across/44_a0.6_bins.png'),
     '0.55': 'bench_2026-11-21/rail/exp/across/44_a0.55_bins.png', '0.45': 'bench_2026-11-21/rail/exp/across/44_a0.45_bins.png'}
B1A = {'0.7': os.path.join(HERE, 'runs/1A_prop_bins.png'), '0.6': os.path.join(HERE, 'across/1A_a0.6_bins.png'), '0.55': os.path.join(HERE, 'across/1A_a0.55_bins.png')}
res = {}
for a, bp in B.items():
    b = cv2.imread(bp, 0); rr = rt.railroad_tracks((b == 4).astype(np.uint8))
    for filt in (None, (600, 60)):
        P = rr if filt is None else rt.drop_alone(rr, *filt)
        o, _ = fscore('44', [dict(kind='railroad', pts=np.asarray(p).tolist()) for p in P], T44, 7219, 10768)
        k = f'{a} {"F600/60" if filt else "nofilter"}'; res[k] = {reg: o[reg]['railroad']['tol10'] for reg in ('all', 'A', 'B')}; res[k]['bin_px'] = int((b == 4).sum())
        print(k, ' | '.join(f"{reg} R{100 * o[reg]['railroad']['tol10']['recall']:.1f} P{100 * o[reg]['railroad']['tol10']['precision']:.1f} br{o[reg]['railroad']['tol10']['broken_interior']} ft{o[reg]['railroad']['tol10']['false_tracks']}" for reg in ('all', 'A', 'B')), 'bin px', res[k]['bin_px'], flush=True)
for a, bp in B1A.items():
    b = cv2.imread(bp, 0); rr = rt.railroad_tracks((b == 4).astype(np.uint8))
    res[f'1A {a}'] = dict(n=len(rr), px=round(sum(rt.plen(p) for p in rr)), n_f600=len(rt.drop_alone(rr, 600, 60)), bin_px=int((b == 4).sum()))
    print('1A', a, res[f'1A {a}'])
json.dump(res, open(os.path.join(HERE, 'across', 'across44.json'), 'w'), indent=1)
