"""review-leak: recompute a plate's area_in.png from unet_data/models/area_ng1.pt on the CPU (blank guide, the scan at half
size INTER_AREA, as blocks_noguide/eval_v2 make it) and compare. Reads only.
cd data/sanborn; ../../tools/sanborn/unet/.venv/Scripts/python.exe -B bench_2026-11-23/train/review-leak/scripts/area_in_recompute.py 7"""
import json, os, sys
import numpy as np, cv2
REPO = os.path.abspath('../..'); sys.path.insert(0, os.path.join(REPO, 'tools/sanborn')); sys.path.insert(0, os.path.join(REPO, 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet'))
import torch  # noqa: E402
import unet as U  # noqa: E402
torch.set_num_threads(12); out = {}
net = U.UNet(); net.load_state_dict(torch.load('unet_data/models/area_ng1.pt', map_location='cpu', weights_only=False))   # the repo's own model (saved with DirectML tensors, as the pipeline loads it); net.eval()
for N in sys.argv[1:]:
    full = cv2.imread(f'cufp/22-{N}.jpg'); H, W = full.shape[:2]; img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); z = np.zeros(img.shape[:2], np.uint8)
    p = (U.predict_full(net, torch.device('cpu'), np.dstack([img[:, :, ::-1], z, z])) * 255).astype(np.uint8); a = cv2.imread(f'train_v2/{N}/area_in.png', 0); d = np.abs(p.astype(int) - a.astype(int))
    out[N] = dict(max_abs=int(d.max()), share_differs=round(float((d > 0).mean()), 6), decision_differs=round(float(((p > 127) != (a > 127)).mean()), 6)); print(N, json.dumps(out[N]), flush=True)
json.dump(out, open('bench_2026-11-23/train/review-leak/area_in_recompute.json', 'w'), indent=1)
