"""merge/impl: the HOLE_PARENT sweep table (fold A to choose, fold B to check) from bench44_runs/hp_* and merged_batch (= 3)."""
import json, os
I = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/impl/bench44_runs/'
K = ['PQ', 'recall_interior', 'precision', 'precision_green', 'delete_len', 'draw_len', 'ben_blocks_closed']; out = {}
for hp in ('0', '1.5', '2', '2.5', '3', '4', '6', '10'):
    t = 'merged_batch' if hp == '3' else f'hp_{hp}'; d = json.load(open(I + t + '/bench44.json')); r = json.load(open(I + t + '/outline_step.json'))['rep']
    out[hp] = {f: {k: d['headline'][f][k] for k in K} for f in ('all', 'A', 'B')}; out[hp]['holes'] = r['holes']; out[hp]['open_land'] = r['holes_in_open_land']
    print(hp.rjust(4), 'holes', r['holes'], 'gated', r['holes_in_open_land'], '| A', out[hp]['A'], '| B', out[hp]['B'])
json.dump(out, open(I + '../hole_sweep.json', 'w'), indent=1)
