"""label_prior.py (diag/verify, 25 Nov 2026): what share of the taught ground is STREET on each training plate of
train_v2 (label.png: 0 street, 1 block, 255 not taught; 1A outside its valmask only), and the street share the area net
actually saw in its crops, weighted by the crops each model json says were drawn per plate (an estimate: it assumes a
crop holds the plate's average mix). Also the same for area_ng1 (its four plates, equal crops, as train() draws).
Read-only. Writes diag/verify/label_prior.json.
    python -B label_prior.py
"""
import json, os
import numpy as np
import cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
OUT = SP + 'bench_2026-11-25/diag/verify/'
M = SP + 'train_v2_runs/models/'
man = json.load(open(SP + 'train_v2/manifest.json', encoding='utf8'))
plates = list(man['plates']) if isinstance(man['plates'], dict) else [e['plate'] for e in man['plates']]
P = {}
for p in plates:
    lab = cv2.imread(SP + f'train_v2/{p}/label.png', 0)
    vm = SP + f'train_v2/{p}/valmask.png'
    tr = np.ones(lab.shape, bool) if not os.path.exists(vm) else cv2.imread(vm, 0) == 0
    st = int(((lab == 0) & tr).sum()); bl = int(((lab == 1) & tr).sum()); un = int(((lab == 255) & tr).sum())
    P[p] = dict(street_share_of_taught=round(st / max(1, st + bl), 4), taught_share=round((st + bl) / max(1, st + bl + un), 4), taught_px=st + bl)
    print(p, P[p], flush=True)
R = dict(plates=P, models={})
for name in ('area_v2a_s1', 'area_v2a_s2', 'area_v2b_s1', 'area_v2b_s2'):
    d = json.load(open(M + name + '.json', encoding='utf8'))
    cd = d['crops_drawn']; tot = sum(cd.values())
    prior = sum(cd[p] * P[p]['street_share_of_taught'] for p in cd) / tot
    by_src = {}
    for p, n in cd.items():
        src = '1A' if p == '1A' else ('label' if p in ('43', '45', '80', '82A') else 'pseudo')
        by_src[src] = by_src.get(src, 0) + n / tot
    R['models'][name] = dict(street_prior_in_crops_est=round(prior, 4), crop_share=dict((k, round(v, 3)) for k, v in by_src.items()))
    print(name, R['models'][name])
ng = sum(P[p]['street_share_of_taught'] for p in ('43', '45', '80', '82A')) / 4
R['models']['area_ng1'] = dict(street_prior_in_crops_est=round(ng, 4), note='equal crops over 43, 45, 80, 82A (train() picks a plate uniformly); labels as train_v2 (byte-identical per the recipe agent)')
print('area_ng1', R['models']['area_ng1'])
json.dump(R, open(OUT + 'label_prior.json', 'w'), indent=1)
