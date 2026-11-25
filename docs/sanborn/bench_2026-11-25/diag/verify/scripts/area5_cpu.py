"""area5_cpu.py (diag/verify, 25 Nov 2026): the area networks on plate 5, on the CPU (torch device 'cpu'; no GPU, no
training). Plate 5 was never trained on by area_ng1 (82A, 80, 43, 45) nor by V1 (those + 1A); V2 trained on 5's pseudo
labels (made from the batch's own maps), so V2 there is in sample. Input as blocks_noguide.predict and eval_v2 make it: the scan
cufp/22-5.jpg at half size (INTER_AREA) as RGB with the two guide channels blank, unet.predict_full (768 tiles, 64 px pad, the batch's
grid); weights loaded as eval_v2.py loads them (the project's own model files). Saves P(block)*255 as diag/verify/area5/<NAME>.png. First runs area_ng1 and compares with the batch's stored
unet_data/5_pred_area_ng1.png (to check that this CPU path gives the batch's map).
    venv python -B area5_cpu.py NAME [NAME ...]     (NAME: area_ng1, area_v2a_s1, area_v2a_s1_last, ...)
"""
import os, sys, time
import numpy as np, cv2, torch
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/'
OUT = SP + 'bench_2026-11-25/diag/verify/area5/'
sys.dont_write_bytecode = True
sys.path.insert(0, TOOLS + 'unet'); sys.path.insert(0, TOOLS)
argv = sys.argv[1:]; sys.argv = [sys.argv[0]]          # unet.py reads flags from sys.argv at import
import unet as U  # noqa: E402  (read-only use: UNet, predict_full)
torch.set_num_threads(max(1, (os.cpu_count() or 4) - 2))
os.makedirs(OUT, exist_ok=True)
full = cv2.imread(SP + 'cufp/22-5.jpg'); H, W = full.shape[:2]
img = cv2.resize(full, (W // 2, H // 2), interpolation=cv2.INTER_AREA); del full   # as blocks_noguide.predict / eval_v2 (not the JPEG img.jpg)
z = np.zeros(img.shape[:2], np.uint8); x = np.dstack([img[:, :, ::-1], z, z])
dev = torch.device('cpu')
for name in argv:
    f = SP + ('unet_data/models/' if name.endswith('ng1') else 'train_v2_runs/models/') + name + '.pt'
    net = U.UNet(); net.load_state_dict(torch.load(f, map_location='cpu', weights_only=False)); net.to(dev)
    t0 = time.time(); p = U.predict_full(net, dev, x)
    a = (p * 255).astype(np.uint8); cv2.imwrite(OUT + f'{name}.png', a)
    msg = f'{name}: {time.time() - t0:.0f} s, block share {(a > 127).mean():.4f}'
    if name == 'area_ng1':
        b = cv2.imread(SP + 'unet_data/5_pred_area_ng1.png', 0)
        msg += f'; against the batch map: max abs diff {int(np.abs(a.astype(int) - b).max())}, decision differs on {float(((a > 127) != (b > 127)).mean()):.6f} of px'
    print(msg, flush=True)
