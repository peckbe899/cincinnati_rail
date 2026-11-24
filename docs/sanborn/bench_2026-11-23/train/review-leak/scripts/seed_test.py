"""review-leak: are the seeds really applied? Runs the STAGED trainers' train_data on the CPU (the device function is
replaced; no GPU is touched) for 2 iterations on train_v2 plate 1A, three times per network: seed 1, seed 1 again, seed 2.
Same seed must give the same weights, the same crops and the same validation history; another seed must not. Writes only
into bench_2026-11-23/train/review-leak/seed/.
cd data/sanborn; ../../tools/sanborn/unet/.venv/Scripts/python.exe -B bench_2026-11-23/train/review-leak/scripts/seed_test.py"""
import json, os, sys, time
import numpy as np
REPO = os.path.abspath('../..'); STAGED = os.path.normpath(os.path.join(REPO, 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet'))
sys.path.insert(0, os.path.join(REPO, 'tools/sanborn')); sys.path.insert(0, STAGED)
import torch  # noqa: E402
import unet as U, edgenet as E  # noqa: E402
assert os.path.normcase(os.path.dirname(os.path.abspath(U.__file__))) == os.path.normcase(STAGED)
torch.set_num_threads(8)


def cpu():
    return torch.device('cpu')


cpu.name = 'cpu (review-leak test)'
U.device = cpu; E.device = cpu
OUT = os.path.abspath('bench_2026-11-23/train/review-leak/seed') + os.sep; os.makedirs(OUT, exist_ok=True)
root = os.path.abspath('train_v2'); R = {}

# 1. the weights' start alone
U.seed_all(1); a = U.UNet().state_dict(); U.seed_all(1); b = U.UNet().state_dict(); U.seed_all(2); c = U.UNet().state_dict()
R['init_same_seed_equal'] = all(torch.equal(a[k], b[k]) for k in a); R['init_other_seed_differs'] = any(not torch.equal(a[k], c[k]) for k in a)
print(json.dumps(R), flush=True)


def sd(p): return torch.load(p, map_location='cpu', weights_only=True)


def maxdiff(p, q):
    A, B = sd(p), sd(q); return max(float((A[k].float() - B[k].float()).abs().max()) for k in A)


for kind, mod in (('area', U), ('lines', E)):
    runs = [('s1a', 1), ('s1b', 1), ('s2', 2)]
    for tag, seed in runs:
        t0 = time.time(); mod.train_data(f'{kind}_{tag}', root, ['1A'], 2, seed, {}, OUT, 1000); R[f'{kind}_{tag}_s'] = round(time.time() - t0, 1)
    J = {tag: json.load(open(OUT + f'{kind}_{tag}.json', encoding='utf8')) for tag, _ in runs}
    R[kind] = dict(
        last_same_seed_maxdiff=maxdiff(OUT + f'{kind}_s1a_last.pt', OUT + f'{kind}_s1b_last.pt'),
        last_other_seed_maxdiff=maxdiff(OUT + f'{kind}_s1a_last.pt', OUT + f'{kind}_s2_last.pt'),
        val_same_seed_equal=J['s1a']['history'][-1].get('val_pooled') == J['s1b']['history'][-1].get('val_pooled'),
        loss=[J[t]['history'][-1]['loss'] for t, _ in runs],
        json_seed=[J[t].get('seed') for t, _ in runs], json_manifest=[str(J[t].get('manifest_sha256'))[:12] for t, _ in runs],
        json_git=J['s1a'].get('git'), json_trainer_sha=(J['s1a'].get('trainer') or {}).get('sha256'), json_best=J['s1a'].get('best'),
        plates=[(p['spec'], p.get('val_box'), p.get('train_px', p.get('train_line_px'))) for p in J['s1a']['plates']], crops_drawn=J['s1a'].get('crops_drawn'))
    print(kind, json.dumps(R[kind]), flush=True)
import hashlib  # noqa: E402
R['manifest_sha256_now'] = hashlib.sha256(open(os.path.join(root, 'manifest.json'), 'rb').read()).hexdigest()
json.dump(R, open(OUT + 'seed_test.json', 'w'), indent=1)
print(json.dumps(R, indent=1))
