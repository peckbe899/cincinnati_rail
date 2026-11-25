"""Collect the plate-5 rail scores of diag/rail5 into scores/summary.json and print a table (25 Nov 2026).
    cd data/sanborn; python -B bench_2026-11-25/diag/rail5/code/summary5.py"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); S = {}
for w in ('orig', 'proposed'):
    for g in ('nets', 'nets_ben', 'none'):
        r = json.load(open(os.path.join(ROOT, 'scores', f'{w}_{g}.json'))); row = {}
        for k in ('railroad', 'streetcar'):
            o = r['kinds'][k]
            for tol in (10, 30):
                t = o[f'tol{tol}']
                row[f'{k}_{tol}'] = dict(recall=t['recall'] if r['n_truth'][k] else None, precision=t['precision'], false_len=t['false_len'], found=t['found'], partial=t['partial'], missed=t['missed'], false_tracks=t['false_tracks'], broken=t['broken'])
            row[f'{k}_rule'] = dict(tracks=r['n_rule'][k], px=r['rule_px'][k], bin_px=o['bin']['bin_px'], bin_recall=o['bin']['recall'] if r['n_truth'][k] else None)
        S[f'{w}_{g}'] = row
        rr, c10, c30 = row['railroad_rule'], row['streetcar_10'], row['streetcar_30']
        print(f"{w:8s} {g:8s} | railroad: {rr['tracks']:2d} tracks {rr['px']:6d} px, all false (bin {rr['bin_px']} px) | streetcar 10px: R {100*c10['recall']:.1f}% P {100*c10['precision']:.1f}% "
              f"found/partial/missed {c10['found']}/{c10['partial']}/{c10['missed']} false {c10['false_len']} px, false tracks {c10['false_tracks']} | 30px: R {100*c30['recall']:.1f}% P {100*c30['precision']:.1f}% "
              f"f/p/m {c30['found']}/{c30['partial']}/{c30['missed']} false {c30['false_len']} px | rule {row['streetcar_rule']['tracks']} tracks {row['streetcar_rule']['px']} px")
S['truth'] = dict(file='picks22_guided/22-5/rail_ben.json (copy inputs/rail_ben_5_copy.json)', complete=True, railroad=0, streetcar_tracks=61, streetcar_px=73423)
json.dump(S, open(os.path.join(ROOT, 'scores', 'summary.json'), 'w'), indent=1)
