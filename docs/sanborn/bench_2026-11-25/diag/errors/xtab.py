"""cross tables on DECIDED ground only (Ben's blocks + the streets between them), mean of 6 grids:
new false line length by ink; all false by ink; text checks; and a robustness check of 'new false' at 10 px with no
direction test.   python -B xtab.py  -> xtab.json"""
import json, os, sys
import numpy as np, cv2
from scipy.spatial import cKDTree
HERE = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/errors/'
sys.path.insert(0, HERE); sys.dont_write_bytecode = True
import census as C  # noqa: E402
L = C.load_layers(); ben = L['ben']; L['ben_tree'] = cKDTree(ben['P'])
gt = cv2.imread(HERE + 'runs/gt_half.png', cv2.IMREAD_UNCHANGED).astype(np.int32); dec = cv2.imread(HERE + 'runs/decided_half.png', 0) > 0
res = {}
for s in ['baseline'] + C.PAIRS:
    acc = []
    for g in range(6):
        r = dict(np.load(HERE + f'runs/{s}_g{g}.npz')); off = r['dp'] > 5; c = C.classify(r['P'], L, gt, dec); D = c['dec']
        band = (c['dstreet'] > 5) & (c['dstreet'] <= 40)
        x = dict(false_dec=int((off & D).sum()), shown_dec=int(D.sum()), false_dec_text_dom=int((off & D & (c['dom'] == 8)).sum()),
                 false_dec_nst=int((off & D & c['nst']).sum()), false_dec_band=int((off & D & band).sum()), false_dec_band_nst=int((off & D & band & c['nst']).sum()))
        for k in range(10): x[f'false_dec_ink{k}'] = int((off & D & (c['dom'] == k)).sum())
        if s != 'baseline':
            df = dict(np.load(HERE + f'runs/{s}_g{g}_diff.npz')); new = df['new']
            x['new_dec'] = int((new & D).sum())
            for k in range(10): x[f'new_dec_ink{k}'] = int((new & D & (c['dom'] == k)).sum())
            x['new_dec_nst'] = int((new & D & c['nst']).sum()); x['new_dec_band'] = int((new & D & band).sum()); x['new_dec_band_nst'] = int((new & D & band & c['nst']).sum())
            # robustness: new false at 10 px, no direction
            b = dict(np.load(HERE + f'runs/baseline_g{g}.npz')); boff = b['dp'] > 5
            t = cKDTree(b['P'][boff]); dd, _ = t.query(r['P'][off], k=1, distance_upper_bound=11)
            x['new_10px_nodir'] = int((dd > 10).sum()); x['new_5px_dir'] = int(new.sum())
            # same for lost: 10 px, no direction
        acc.append(x)
    res[s] = {k: float(np.mean([a[k] for a in acc])) for k in acc[0]}
json.dump(res, open(HERE + 'xtab.json', 'w'), indent=1)
for s, x in res.items():
    print('==', s, f"shown on decided {x['shown_dec']:.0f}, false on decided {x['false_dec']:.0f} ({x['false_dec'] / x['shown_dec']:.1%})")
    print('   false (decided) by ink:', ', '.join(f"{C.BIN_NAMES[k]} {x[f'false_dec_ink{k}']:.0f} ({x[f'false_dec_ink{k}'] / x['false_dec']:.0%})" for k in range(10)))
    print(f"   false (decided) on text dominant {x['false_dec_text_dom'] / x['false_dec']:.1%}; near-street text in window {x['false_dec_nst'] / x['false_dec']:.1%}; in 5-40 band {x['false_dec_band']:.0f}, on near-street text {x['false_dec_band_nst'] / max(1, x['false_dec_band']):.1%}")
    if s != 'baseline':
        print(f"   NEW false on decided {x['new_dec']:.0f}:", ', '.join(f"{C.BIN_NAMES[k]} {x[f'new_dec_ink{k}']:.0f} ({x[f'new_dec_ink{k}'] / x['new_dec']:.0%})" for k in range(10)))
        print(f"   NEW false decided near-street text {x['new_dec_nst'] / x['new_dec']:.1%}; band {x['new_dec_band']:.0f} -> {x['new_dec_band_nst'] / max(1, x['new_dec_band']):.1%}")
        print(f"   robustness: new false 5px+20deg {x['new_5px_dir']:.0f} vs 10px no direction {x['new_10px_nodir']:.0f}")
