"""The guide channels (inputs 4 and 5 of the area net) at use time are zeros. What did each recipe do to the first
convolution's weights on them? Loads state dicts on the CPU only (no inference, no training). For V1/V2 (torch seeded)
the start weights are rebuilt with torch.manual_seed(seed); UNet() to show whether training moved them.
Venv python -B."""
import json, sys, torch
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/'
sys.path.insert(0, R + 'tools/sanborn/unet'); sys.path.insert(0, R + 'tools/sanborn')
import unet as A
out = {}
for nm, f, seed in [('area_ng1', R + 'data/sanborn/unet_data/models/area_ng1.pt', None),
                    ('area_v2a_s1', R + 'data/sanborn/train_v2_runs/models/area_v2a_s1.pt', 1), ('area_v2a_s1_last', R + 'data/sanborn/train_v2_runs/models/area_v2a_s1_last.pt', 1),
                    ('area_v2b_s2', R + 'data/sanborn/train_v2_runs/models/area_v2b_s2.pt', 2)]:
    sd = torch.load(f, map_location='cpu', weights_only=False); w = sd['down.0.0.weight'].float().cpu()   # (32, 5, 3, 3)
    r = dict(rgb_abs_mean=round(float(w[:, :3].abs().mean()), 5), guide_abs_mean=round(float(w[:, 3:].abs().mean()), 5))
    if seed is not None:
        torch.manual_seed(seed); w0 = A.UNet().state_dict()['down.0.0.weight']
        r['guide_max_change_from_start'] = float((w[:, 3:] - w0[:, 3:]).abs().max()); r['rgb_max_change_from_start'] = round(float((w[:, :3] - w0[:, :3]).abs().max()), 5)
    out[nm] = r; print(nm, r, flush=True)
json.dump(out, open(R + 'data/sanborn/bench_2026-11-25/diag/recipe/guide_weights.json', 'w'), indent=1)
