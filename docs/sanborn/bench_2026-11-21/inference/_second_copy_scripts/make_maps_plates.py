"""Network maps of batch plates (no truth) under an inference setting, for the scale check (GPU, DirectML).

    VENV_PYTHON make_maps_plates.py SETTING N [N ...] [--cpu] [--force]

SETTING (infer_lib options; 'up2' = scale normalisation for a 400-ft plate: both networks on the scan resampled x2
to the 200-ft training scale, maps resampled back to the plate's own size):
"""
import json, os, sys, time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np, cv2, torch
import infer_lib as L

SETTINGS = {
    'up2':        (dict(scale=2.0), dict(scale=2.0)),
    'up2_atta4':  (dict(scale=2.0, tta=4), dict(scale=2.0)),
    'atta4':      (dict(tta=4), {}),
    'atta8':      (dict(tta=8), {}),                                   # the recommended setting (area TTA x8, lines as the batch)
    'a_up2':      (dict(scale=2.0), {}),
    'up2thin':    (dict(scale=2.0, pen=3), dict(scale=2.0, pen=3)),   # x2 to the 200-ft street width, then pens thinned back
    'batchcopy':  ({}, {}),                       # the batch's own settings, recomputed (a check)
}
__doc__ += '\n'.join(f'  {k:10s} area {a}  lines {l}' for k, (a, l) in SETTINGS.items())

if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if not a.startswith('--')]; setting, plates = args[0], args[1:]
    ao, lo = SETTINGS[setting]; out = L.HERE + f'maps_plates/{setting}/'; os.makedirs(out, exist_ok=True)
    dev = torch.device('cpu') if '--cpu' in sys.argv else L.device(); nets = L.load_nets(dev)
    for n in plates:
        if os.path.exists(out + f'{n}_info.json') and '--force' not in sys.argv: print('have', n, file=sys.stderr); continue
        t0 = time.time(); full = cv2.imread(L.SP + f'cufp/22-{n}.jpg'); t_read = time.time() - t0
        pa, pl, t = L.chain(nets, full, ao, lo)
        cv2.imwrite(out + f'{n}_area.png', pa); cv2.imwrite(out + f'{n}_lines.png', pl)
        info = dict(plate=n, setting=setting, area=ao, lines=lo, device=str(dev), size=[full.shape[1], full.shape[0]], seconds=dict(read_s=round(t_read, 2), **t, total_s=round(time.time() - t0, 2)),
                    block_share=round(float((pa > 127).mean()), 4), line_share=round(float((pl > 127).mean()), 5))
        json.dump(info, open(out + f'{n}_info.json', 'w'), indent=1); print(json.dumps(info), flush=True)
        del full, pa, pl
