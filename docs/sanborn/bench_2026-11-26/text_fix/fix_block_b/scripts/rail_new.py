"""New text in Ben's rail bands (44 and 5; check only): pixels a new mask calls text that finder3 did not, within 14 px of
his railroad tracks and 12 px of his streetcar tracks (picks22_guided/22-N/rail_ben.json, read-only), as 8-connected
blobs, each written to a sheet to be looked at by eye, and pixels that stopped being text there.
    python -B .../scripts/rail_new.py BASE_DIR NEW_DIR OUT_STEM N [N ...]"""
import sys, os, json
import numpy as np, cv2
bd, nd, stem, plates = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:]; rep = {}
for N in plates:
    a = cv2.imread(os.path.join(bd, f'{N}_text.png'), 0); b = cv2.imread(os.path.join(nd, f'{N}_text.png'), 0); H, W = a.shape
    R = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8')); band = np.zeros((H, W), bool)
    for kind, tol in (('railroad', 14), ('streetcar', 12)):
        m = np.zeros((H, W), np.uint8)
        for t in R['tracks']:
            if t['kind'] == kind and len(t['pts']) >= 2: cv2.polylines(m, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 1)
        band |= cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tol + 1, 2 * tol + 1))) > 0
    ta, tb = np.isin(a, (2, 3)), np.isin(b, (2, 3)); new = tb & ~ta & band; gone = ta & ~tb & band
    n, lb, st, _ = cv2.connectedComponentsWithStats(new.astype(np.uint8), connectivity=8)
    rep[N] = dict(new_text_px_in_bands=int(new.sum()), text_px_lost_in_bands=int(gone.sum()), changed_px_in_bands=int(((a != b) & band).sum()),
                  new_blobs=[dict(x=int(st[i, 0]), y=int(st[i, 1]), w=int(st[i, 2]), h=int(st[i, 3]), px=int(st[i, 4])) for i in range(1, n)])
    print(N, rep[N]['new_text_px_in_bands'], 'new text px in rail bands,', n - 1, 'blobs;', rep[N]['changed_px_in_bands'], 'px of any code changed in the bands')
    if n > 1:
        im = cv2.imread(f'cufp/22-{N}.jpg'); tiles = []
        for i in range(1, n):
            cx, cy = st[i, 0] + st[i, 2] // 2, st[i, 1] + st[i, 3] // 2; X0, Y0 = max(0, cx - 60), max(0, cy - 60)
            s = im[Y0:Y0 + 120, X0:X0 + 120]; o = s.copy(); o[band[Y0:Y0 + 120, X0:X0 + 120]] //= 2; o[new[Y0:Y0 + 120, X0:X0 + 120]] = (0, 0, 255)
            tiles.append(cv2.resize(np.concatenate([s, o], 1), None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
        cv2.imwrite(f'{stem}_{N}.png', np.concatenate(tiles[:12], 0))
json.dump(rep, open(stem + '.json', 'w'), indent=1)
