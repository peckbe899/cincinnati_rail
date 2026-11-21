"""CPU only, read-only: area_ng1 on part of plate 44 from N_img.jpg (training path, JPEG q92) vs from the full scan
resized in memory with INTER_AREA (blocks_noguide.py:38 path). How different is the channel the line net gets?"""
import sys, json, time
sys.argv = [sys.argv[0]]
sys.path.insert(0, 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet')
import numpy as np, cv2, torch
torch.set_num_threads(8)
import unet as A
S = 'C:/Users/peckb/AppData/Local/Temp/claude/8945a8e3044b4e4c/2a2bcb12-80e8-4366-9a59-3be15cce3445/scratchpad/ml_review/verify-line-net/'
R = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
na = A.UNet(); na.load_state_dict(torch.load(R + 'unet_data/models/area_ng1.pt', map_location='cpu', weights_only=False)); na.eval()
jp = cv2.imread(R + 'unet_data/44_img.jpg'); full = cv2.imread(R + 'cufp/22-44.jpg'); H, W = full.shape[:2]
mem = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
print('shapes', jp.shape, mem.shape, 'mean abs px diff', float(np.abs(jp.astype(np.int16) - mem.astype(np.int16)).mean()))
y0, y1, x0, x1 = 200, 1700, 800, 3100
lab = cv2.imread(R + 'unet_data/44_label.png', 0)[y0 + 150:y1 - 150, x0 + 150:x1 - 150]
res = {}
for k, im in (('jpg', jp), ('mem', mem)):
    a = np.ascontiguousarray(im[y0:y1, x0:x1, ::-1]); z = np.zeros(a.shape[:2], np.uint8)
    t0 = time.time(); p = A.predict_full(na, 'cpu', np.dstack([a, z, z]))[150:-150, 150:-150]; res[k] = p
    m = lab != 255; print(k, 'acc', round(float(((p > 0.5) == (lab == 1))[m].mean()), 4), round(time.time() - t0), 's', flush=True)
snap = cv2.imread(S + 'snap/44_pred_area_ng1.png', 0)[y0 + 150:y1 - 150, x0 + 150:x1 - 150].astype(np.float32) / 255
d = dict(jpg_vs_snapshot_mean_abs=round(float(np.abs(res['jpg'] - snap).mean()), 5),
         mem_vs_jpg_mean_abs=round(float(np.abs(res['mem'] - res['jpg']).mean()), 5),
         mem_vs_jpg_flipped_share=round(float(((res['mem'] > 0.5) != (res['jpg'] > 0.5)).mean()), 5),
         unsure_jpg=round(float(((res['jpg'] > 0.1) & (res['jpg'] < 0.9)).mean()), 4), unsure_mem=round(float(((res['mem'] > 0.1) & (res['mem'] < 0.9)).mean()), 4))
print(d); json.dump(d, open(S + 'v4_imgpath.json', 'w'), indent=1)
