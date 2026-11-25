"""lines5_cpu.py (diag/verify, 25 Nov 2026): a line network's map of plate 5 on the CPU (no GPU, no training), fed a
given area map as its 7th input, exactly as blocks_noguide.predict builds the input (the full scan RGB, its ink image,
two blank guide channels, the half-size P(block) resized INTER_LINEAR) and edgenet.predict_full (1024 tiles, 96 px pad).
First (--check) runs lines_ng1 fed the batch's area_ng1 map and compares with the stored unet_data/5_lines_lines_ng1.png.
Writes diag/verify/plate5/maps/<TAG>/{5_area.png, 5_lines.png}.
    venv python -B lines5_cpu.py TAG AREA_PNG LINES_NET [TAG AREA_PNG LINES_NET ...]
"""
import os, sys, time, shutil
import numpy as np, cv2, torch
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
TOOLS = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/'
OUT = SP + 'bench_2026-11-25/diag/verify/plate5/maps/'
sys.dont_write_bytecode = True
sys.path.insert(0, TOOLS + 'unet'); sys.path.insert(0, TOOLS)
argv = sys.argv[1:]; sys.argv = [sys.argv[0]]
import unet as A, edgenet as E  # noqa: E402  (read-only use)
torch.set_num_threads(max(1, (os.cpu_count() or 4) - 2))
full = cv2.imread(SP + 'cufp/22-5.jpg'); H, W = full.shape[:2]
inkimg, _ = E.ink_image(full); Z = np.zeros((H, W), np.uint8); rgb = full[:, :, ::-1].copy(); del full
dev = torch.device('cpu')
for k in range(0, len(argv), 3):
    tag, apng, lnet = argv[k:k + 3]
    f = SP + ('unet_data/models/' if lnet.endswith('ng1') else 'train_v2_runs/models/') + lnet + '.pt'
    nl = A.UNet(classes=2, in_ch=7); nl.load_state_dict(torch.load(f, map_location='cpu', weights_only=False)); nl.to(dev); nl.eval()
    pa = cv2.imread(apng, 0)
    x = np.dstack([rgb, inkimg, Z, Z, cv2.resize(pa, (W, H), interpolation=cv2.INTER_LINEAR)])
    t0 = time.time(); q = E.predict_full(nl, dev, x); del x
    ql = (q * 255).astype(np.uint8); d = OUT + tag + '/'; os.makedirs(d, exist_ok=True)
    cv2.imwrite(d + '5_lines.png', ql); shutil.copyfile(apng, d + '5_area.png')
    open(d + 'source.txt', 'w').write(f'area {apng}\nlines net {f} fed that area map (CPU)\n')
    msg = f'{tag}: {time.time() - t0:.0f} s, line share {(ql > 127).mean():.5f}'
    if tag == 'check_batch':
        b = cv2.imread(SP + 'unet_data/5_lines_lines_ng1.png', 0)
        msg += f'; against the batch line map: max abs diff {int(np.abs(ql.astype(int) - b).max())}, decision differs on {float(((ql > 127) != (b > 127)).mean()):.7f} of px'
    print(msg, flush=True)
