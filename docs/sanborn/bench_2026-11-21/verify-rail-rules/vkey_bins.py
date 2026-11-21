"""verify-rail-rules (21 Nov 2026): for plates re-run with patched/ink_bins.py (keyplates/N_patched_bins.png, made by
vrun_ink_bins.py as the batch ran them, without --nomap), compare with
  unet_data/N_bins.png (the batch's bins): pixels that differ, inside and outside the KEY box the log reports
  rail-rules/batch/N_bins.png (their proposed bins), where it exists
and draw a picture of each KEY box (quarter size) with the batch's rule tracks and the patched tracks there.
Writes keyplates/vkey_bins.json and keyplates/N_key.jpg here.
    cd data/sanborn
    python bench_2026-11-21/verify-rail-rules/vkey_bins.py 36 1B 34 25"""
import os, sys, re, json, importlib.util
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); RR = os.path.join(os.path.dirname(HERE), 'rail-rules'); O = os.path.join(HERE, 'keyplates')
spec = importlib.util.spec_from_file_location('rtp', os.path.join(HERE, 'patched', 'rail_tracks.py')); RP = importlib.util.module_from_spec(spec); spec.loader.exec_module(RP)
res = {}
for N in sys.argv[1:]:
    Bp = cv2.imread(os.path.join(O, f'{N}_patched_bins.png'), 0); Bb = cv2.imread(f'unet_data/{N}_bins.png', 0)
    m = re.search(r'the printed KEY at \((\d+), (\d+), (\d+), (\d+)\)', open(os.path.join(O, f'{N}_patched.log')).read())
    inbox = np.zeros(Bp.shape, bool)
    if m: x0, y0, x1, y1 = map(int, m.groups()); inbox[y0:y1, x0:x1] = True
    d = Bp != Bb; r = dict(key_box=list(map(int, m.groups())) if m else None, differ_outside=int((d & ~inbox).sum()), differ_inside=int((d & inbox).sum()),
                         batch_rail_px_inside=dict(railroad=int(((Bb == 4) & inbox).sum()), streetcar=int(((Bb == 5) & inbox).sum())),
                         patched_rail_px_inside=dict(railroad=int(((Bp == 4) & inbox).sum()), streetcar=int(((Bp == 5) & inbox).sum())))
    tp = os.path.join(RR, 'batch', f'{N}_bins.png')
    if os.path.exists(tp): r['differ_from_theirs'] = int((cv2.imread(tp, 0) != Bp).sum())
    if m:
        im = cv2.imread(f'cufp/22-{N}.jpg'); pad = 300; X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(Bp.shape[1], x1 + pad), min(Bp.shape[0], y1 + pad)
        c = (im * 0.5 + 127).astype(np.uint8)
        c[(Bb == 4)] = (0, 0, 255); c[(Bb == 5)] = (255, 0, 255)       # batch bins: railroad red, streetcar magenta
        bt = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
        for t in bt: cv2.polylines(c, [np.round(np.asarray(t['pts'])).astype(np.int32)], False, (0, 0, 0), 9)   # batch tracks black
        for t in RP.tracks(Bp): cv2.polylines(c, [np.round(np.asarray(t['pts'])).astype(np.int32)], False, (0, 200, 0), 5)   # patched tracks green
        cv2.rectangle(c, (x0, y0), (x1, y1), (255, 128, 0), 8)
        cv2.imwrite(os.path.join(O, f'{N}_key.jpg'), cv2.resize(c[Y0:Y1, X0:X1], None, fx=0.4, fy=0.4, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
    res[N] = r; print(N, json.dumps(r), flush=True)
json.dump(res, open(os.path.join(O, 'vkey_bins.json'), 'w'), indent=1)
