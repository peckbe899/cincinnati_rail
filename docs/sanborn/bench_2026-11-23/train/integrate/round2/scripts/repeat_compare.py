"""Integrator, round 2 (24 Nov 2026): repeat_gpu.sh's models compared. Same seed twice on the GPU: the largest weight
difference of NAME_last.pt and NAME.pt, and the validation history side by side; seed 2 against seed 1 for scale.
cd data/sanborn; ../../tools/sanborn/unet/.venv/Scripts/python.exe -B bench_2026-11-23/train/integrate/round2/scripts/repeat_compare.py"""
import json
import torch
O = 'bench_2026-11-23/train/integrate/round2/repeat/'; R = {}


def sd(p): return torch.load(p, map_location='cpu', weights_only=True)


def maxdiff(p, q):
    A, B = sd(p), sd(q); return max(float((A[k].float() - B[k].float()).abs().max()) for k in A)


for kind, key in (('area', 'iou_street'), ('lines', 'f1')):
    j = {t: json.load(open(O + f'{kind}_{t}.json', encoding='utf8')) for t in ('s1a', 's1b', 's2')}
    R[kind] = dict(device=j['s1a'].get('device'),
                   same_seed_last_maxdiff=maxdiff(O + f'{kind}_s1a_last.pt', O + f'{kind}_s1b_last.pt'),
                   same_seed_best_maxdiff=maxdiff(O + f'{kind}_s1a.pt', O + f'{kind}_s1b.pt'),
                   other_seed_last_maxdiff=maxdiff(O + f'{kind}_s1a_last.pt', O + f'{kind}_s2_last.pt'),
                   crops_same=j['s1a']['crops_drawn'] == j['s1b']['crops_drawn'],
                   val=dict((t, [h['val_pooled'][key] for h in j[t]['history']]) for t in j),
                   loss=dict((t, [h['loss'] for h in j[t]['history']]) for t in j),
                   best=dict((t, j[t]['best']) for t in j), s_per_iter=dict((t, [h['train_s_per_iter'] for h in j[t]['history']]) for t in j))
json.dump(R, open(O + 'repeat_compare.json', 'w'), indent=1); print(json.dumps(R, indent=1))
