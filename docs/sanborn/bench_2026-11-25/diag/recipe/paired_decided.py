"""Paired gains over area_ng1 + lines_ng1 on 44 (grid by grid, from each eval_v2.json), for PQ (all ground) and
PQ_decided (COCO's void rule: blocks lying in ground Ben's map leaves undecided are not counted), plus the false
blocks split into inside / outside his decided ground. Reads only."""
import json
EV = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/train_v2_runs/eval/'
out = {}
for s in ['V1S1', 'V2S1', 'V1S2', 'V2S2']:
    d = json.load(open(EV + f'{s}/eval_v2.json'))['bench44']; P = d['paired']['all']; A = d['v2']['all']
    out[s] = {k: dict(mean=P[k]['mean'], sd=P[k]['sd'], up=f"{P[k]['gains']}/{P[k]['of']}") for k in ('PQ', 'PQ_decided', 'fp', 'fp_decided', 'matched', 'merges', 'recall_interior', 'precision', 'delete_len')}
    out[s]['fp_outside_decided_mean'] = round(A['fp']['mean'] - A['fp_decided']['mean'], 2)
    out[s]['PQ_mean'] = A['PQ']['mean']; out[s]['PQ_decided_mean'] = A['PQ_decided']['mean']
b = json.load(open(EV + 'baseline/eval_v2.json'))['bench44']['v2']['all']
out['baseline'] = dict(PQ_mean=b['PQ']['mean'], PQ_decided_mean=b['PQ_decided']['mean'], fp=b['fp']['mean'], fp_decided=b['fp_decided']['mean'], fp_outside_decided_mean=round(b['fp']['mean'] - b['fp_decided']['mean'], 2))
for v in ('V1', 'V2'):
    out[v + '_seed_mean'] = dict(PQ_gain=round((out[v + 'S1']['PQ']['mean'] + out[v + 'S2']['PQ']['mean']) / 2, 4), PQ_decided_gain=round((out[v + 'S1']['PQ_decided']['mean'] + out[v + 'S2']['PQ_decided']['mean']) / 2, 4))
json.dump(out, open('C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/recipe/paired_decided.json', 'w'), indent=1)
for k, v in out.items(): print(k, json.dumps(v))
