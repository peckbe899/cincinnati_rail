"""review-leak: (1) do the staged trainers refuse 44 and 90 however they are named, and a data folder that holds them?
(2) is 1A's area_in.png really area_ng1's blank-guide map (recomputed on the CPU from unet_data/models/area_ng1.pt as
blocks_noguide/eval_v2 make it)? Reads only (and the CPU). Writes review-leak/guards_and_area_in.json.
cd data/sanborn; ../../tools/sanborn/unet/.venv/Scripts/python.exe -B bench_2026-11-23/train/review-leak/scripts/guards_and_area_in.py"""
import json, os, sys
import numpy as np, cv2
REPO = os.path.abspath('../..'); STAGED = os.path.normpath(os.path.join(REPO, 'data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet'))
sys.path.insert(0, os.path.join(REPO, 'tools/sanborn')); sys.path.insert(0, STAGED)
import torch  # noqa: E402
import unet as U  # noqa: E402
torch.set_num_threads(8); R = {}
root = os.path.abspath('train_v2'); man, _ = U.read_manifest(root)


def refused(specs, r=root, m=man):
    try: U.plate_list(r, specs, m); return False
    except SystemExit as e: return str(e)[:120]


R['refuse'] = {repr(s): refused(s) for s in (['44'], ['44:val'], ['90'], ['90:val'], ['1A', '44'], ['43', '90:all'])}
t44 = os.path.abspath('bench_2026-11-23/train/labels/test44/map')   # the label agent's test folder that holds a 44 plate
R['refuse']['data folder labels/test44/map (holds 44), no plates named'] = refused([], t44, U.read_manifest(t44)[0])
R['note_case'] = 'plate names are upper-cased before the check; a folder named e.g. 044 would not be caught by name (none exists: data_checks.json, image_overlap3.json)'
print(json.dumps(R, indent=1), flush=True)
# (2) 1A's area_in against area_ng1 recomputed on the CPU
net = U.UNet(); net.load_state_dict(torch.load('unet_data/models/area_ng1.pt', map_location='cpu')); net.eval()
full = cv2.imread('cufp/22-1A.jpg'); H, W = full.shape[:2]; img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); z = np.zeros(img.shape[:2], np.uint8)
p = (U.predict_full(net, torch.device('cpu'), np.dstack([img[:, :, ::-1], z, z])) * 255).astype(np.uint8)
a = cv2.imread('train_v2/1A/area_in.png', 0); d = np.abs(p.astype(int) - a.astype(int))
R['area_in_1A_vs_area_ng1_cpu'] = dict(shape_equal=p.shape == a.shape, max_abs=int(d.max()), share_differs=round(float((d > 0).mean()), 6), share_differs_gt2=round(float((d > 2).mean()), 6),
                                       decision_differs=round(float(((p > 127) != (a > 127)).mean()), 6))
# and against another model, as a control that the comparison can tell models apart
print(json.dumps(R['area_in_1A_vs_area_ng1_cpu']), flush=True)
json.dump(R, open('bench_2026-11-23/train/review-leak/guards_and_area_in.json', 'w'), indent=1)
