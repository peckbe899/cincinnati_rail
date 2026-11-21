"""Synthetic off-scale check on the ground-truth plate: 44 made smaller, as if it were printed at a smaller scale.

    VENV_PYTHON make_synth44.py [--cpu] [--force]

Plate 44 is at 100 ft to the inch (2.97 px per ft on the scan). Resizing the scan by f = 0.25 (INTER_AREA) gives the
400-ft equivalent (0.74 px per ft, as the real 400-ft sheets: plate 47's scale bar gives 0.74). The small image is then
treated as a plate's whole scan and run through the two networks:
  native  : as the batch would run a 400-ft plate (no resampling)
  up2     : resampled x2 to the 200-ft training scale before both networks, maps resampled back (scale normalisation)
  up4     : resampled x4 to the 100-ft scale (44's and 43's own), maps resampled back
To score with bench44 the maps must be at 44's size. Two ways:
  *_back  : maps resampled back to the small plate (the deployable way: the outline step then runs at the plate's own
            resolution), then resized x4 to 44's size
  *_keep  : maps resized straight from the network's resolution to 44's size (as if the outline step ran at the
            normalised scale)
Also the 200-ft equivalent (f = 0.5), native and up2, for comparison with make_maps44.py's both_s0.5.
CAVEAT: shrinking a scan also thins the pen lines and the lettering (a 3-4 px line becomes about 1 px at f = 0.25). A
real 400-ft sheet is drawn with the same pens as a 100-ft one, so its lines stay 3-4 px wide; the synthetic plate is
harder than a real one for the line network.
Writes maps_synth/NAME/44_area.png, 44_lines.png, info.json (only inside this folder).
"""
import json, os, sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, torch
import infer_lib as L

dev = torch.device('cpu') if '--cpu' in sys.argv else L.device(); nets = L.load_nets(dev); _, na, nl = nets
full = cv2.imread(L.SP + 'cufp/22-44.jpg'); H, W = full.shape[:2]; w2, h2 = W // 2, H // 2
for f, ups in ((0.25, (1, 2, 4)), (0.5, (1, 2))):
    small = cv2.resize(full, (int(round(W * f)), int(round(H * f))), interpolation=cv2.INTER_AREA); hs, ws = small.shape[:2]
    for u in ups:
        tag = f"syn{int(round(100 / f))}_{'native' if u == 1 else f'up{u}'}"
        if all(os.path.exists(L.HERE + f'maps_synth/{tag}_{k}/info.json') for k in ('back', 'keep')) and '--force' not in sys.argv: continue
        t0 = time.time()
        # the area network at u x the small plate's half size (straight from the small scan, as infer_lib.area_map does)
        hu, wu = int(round(hs / 2 * u)), int(round(ws / 2 * u))
        img = cv2.resize(small, (wu, hu), interpolation=cv2.INTER_AREA if u == 1 else cv2.INTER_CUBIC) if u != 1 else cv2.resize(small, (ws // 2, hs // 2), interpolation=cv2.INTER_AREA)
        z = np.zeros(img.shape[:2], np.uint8); pa_net = L.predict(na, dev, np.dstack([img[:, :, ::-1], z, z]), L.prob_area, 768, 64)
        pa_back = L.u8(cv2.resize(pa_net, (ws // 2, hs // 2), interpolation=cv2.INTER_LINEAR))
        # the line network at u x the small plate's full size, fed the area map at that size
        fu = small if u == 1 else cv2.resize(small, (ws * u, hs * u), interpolation=cv2.INTER_CUBIC)
        ink, _ = L.ink_image(fu); Z = np.zeros(fu.shape[:2], np.uint8)
        x = np.dstack([fu[:, :, ::-1], ink, Z, Z, cv2.resize(L.u8(pa_net), (fu.shape[1], fu.shape[0]), interpolation=cv2.INTER_LINEAR)])
        pl_net = L.predict(nl, dev, x, L.prob_lines, 1024, 96, batch=4); secs = round(time.time() - t0, 1)
        pl_back = L.u8(cv2.resize(pl_net, (ws, hs), interpolation=cv2.INTER_LINEAR))
        for how in ('back', 'keep'):
            out = L.HERE + f'maps_synth/{tag}_{how}/'; os.makedirs(out, exist_ok=True)
            if how == 'back':
                A = cv2.resize(pa_back, (w2, h2), interpolation=cv2.INTER_LINEAR); Lm = cv2.resize(pl_back, (W, H), interpolation=cv2.INTER_LINEAR)
            else:
                A = L.u8(cv2.resize(pa_net, (w2, h2), interpolation=cv2.INTER_LINEAR)); Lm = L.u8(cv2.resize(pl_net, (W, H), interpolation=cv2.INTER_LINEAR))
            cv2.imwrite(out + '44_area.png', A); cv2.imwrite(out + '44_lines.png', Lm)
            info = dict(name=f'{tag}_{how}', shrink=f, up=u, small_size=[ws, hs], area_net_input=[img.shape[1], img.shape[0]], line_net_input=[fu.shape[1], fu.shape[0]],
                        seconds_networks=secs, area_block_share=round(float((A > 127).mean()), 4), line_share=round(float((Lm > 127).mean()), 5), device=str(dev))
            json.dump(info, open(out + 'info.json', 'w'), indent=1); print(json.dumps(info), flush=True)
