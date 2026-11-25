"""PQ parts per pair (mean of 6 grids) from the runs' bench44.json, and what PQ would be with the pair's matches but
the baseline's false-block count (a counterfactual, computed from PQ = SQ * TP / (TP + FP/2 + FN/2)).
    python -B pq_parts.py"""
import json, numpy as np
EV = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/train_v2_runs/eval/'
R = {}
for s in ['baseline', 'V1S1', 'V2S1', 'V1S2', 'V2S2']:
    rows = []
    for g in range(6):
        b = json.load(open(EV + f'{s}/runs44/v2__grid{g}/bench44.json'))
        h = b['headline']['all']; o = b['blocks']['outlines']['all']; od = b['blocks']['outlines_decided']['all']
        rows.append(dict(PQ=h['PQ'], SQ=h['SQ'], tp=o['matched'], fp=o['fp'], fn=o['fn'], merges=o['merges'], PQd=od['PQ'], fpd=od['fp'], lost_in_merges=o['gt_lost_in_merges']))
    R[s] = rows
for s, rows in R.items():
    m = lambda k: np.mean([r[k] for r in rows])
    # counterfactual: the pair's TP and SQ, the baseline's fp on that grid
    cf = np.mean([r['SQ'] * r['tp'] / (r['tp'] + 0.5 * R['baseline'][g]['fp'] + 0.5 * r['fn']) for g, r in enumerate(rows)])
    # counterfactual 2: the pair's fp, the baseline's TP and SQ
    cf2 = np.mean([R['baseline'][g]['SQ'] * R['baseline'][g]['tp'] / (R['baseline'][g]['tp'] + 0.5 * r['fp'] + 0.5 * R['baseline'][g]['fn']) for g, r in enumerate(rows)])
    print(f"{s:8s} PQ {m('PQ'):.3f} SQ {m('SQ'):.3f} TP {m('tp'):.2f} FP {m('fp'):.2f} FN {m('fn'):.2f} merges {m('merges'):.2f} lost_in_merges {m('lost_in_merges'):.2f} | PQ_decided {m('PQd'):.3f} fp_decided {m('fpd'):.2f} | PQ with baseline fp {cf:.3f} | baseline matches with this fp {cf2:.3f}")
