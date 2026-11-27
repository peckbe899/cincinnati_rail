"""CHECK ONLY (26 Nov 2026): where does dittofix add text near Ben's lines (44, 1A, 5) and inside his rail bands (44, 5)?

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/fix_ditto/code/check_new_text.py F3_DIR FIX_DIR OUT_DIR

New text = pixels that are text (2/3) in FIX and not in F3. Lists every 8-connected blob of new text that lies within
3 px of a Ben line (text/finder/scripts/benlines.py, imported read-only, as check_lines_rail.py does) or inside a rail
band (picks22_guided/22-N/rail_ben.json, read-only: 14 px round railroad tracks, 12 px round streetcar tracks), and
draws each one (scan | codes after, new text red, band tinted) for a look by eye. Writes only into OUT_DIR.
"""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
sys.path.insert(0, os.path.join(os.getcwd(), 'bench_2026-11-25', 'text', 'finder', 'scripts'))
import benlines

f3d, fxd, out = sys.argv[1:4]; os.makedirs(out, exist_ok=True); R = {}
COL = {1: (170, 170, 170), 2: (220, 0, 220), 3: (255, 120, 0), 4: (0, 200, 230), 5: (0, 150, 0)}
for N in ('44', '1A', '5'):
    a = cv2.imread(os.path.join(f3d, f'{N}_text.png'), 0); b = cv2.imread(os.path.join(fxd, f'{N}_text.png'), 0); H, W = a.shape
    new = np.isin(b, (2, 3)) & ~np.isin(a, (2, 3))
    m, _ = benlines.raster(N, W, H); d = cv2.distanceTransform((m == 0).astype(np.uint8), cv2.DIST_L2, 5)
    near = d <= 3
    band = np.zeros((H, W), bool); bands = {}
    p = f'picks22_guided/22-{N}/rail_ben.json'
    if N in ('44', '5') and os.path.exists(p):
        B = json.load(open(p, encoding='utf8'))
        for kind, tol in (('railroad', 14), ('streetcar', 12)):
            mm = np.zeros((H, W), np.uint8)
            for t in B['tracks']:
                if t['kind'] == kind and len(t['pts']) >= 2: cv2.polylines(mm, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 1)
            bands[kind] = cv2.dilate(mm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tol + 1, 2 * tol + 1))) > 0; band |= bands[kind]
    n, lb, st, _ = cv2.connectedComponentsWithStats(new.astype(np.uint8), connectivity=8)
    blobs = []; im = cv2.imread(f'cufp/22-{N}.jpg'); tiles = []
    for i in range(1, n):
        x, y, w, h, A = (int(v) for v in st[i]); sub = lb[y:y + h, x:x + w] == i
        nl = int((sub & near[y:y + h, x:x + w]).sum()); nb = int((sub & band[y:y + h, x:x + w]).sum())
        kinds = [k for k, bm in bands.items() if (sub & bm[y:y + h, x:x + w]).any()]
        blobs.append(dict(x=x, y=y, w=w, h=h, px=A, near_ben_line_3px=nl, in_rail_band=nb, band_kinds=kinds))
        if nl or nb:
            cx, cy = x + w // 2, y + h // 2; X0, Y0, X1, Y1 = max(0, cx - 40), max(0, cy - 40), min(W, cx + 40), min(H, cy + 40)
            o = np.full((Y1 - Y0, X1 - X0, 3), 245, np.uint8); cb = b[Y0:Y1, X0:X1]
            for v, c in COL.items(): o[cb == v] = c
            o[band[Y0:Y1, X0:X1] & (cb == 0)] = (230, 230, 180); o[near[Y0:Y1, X0:X1] & (cb == 0)] = (200, 230, 200); o[new[Y0:Y1, X0:X1]] = (0, 0, 255)
            t = cv2.resize(np.concatenate([im[Y0:Y1, X0:X1], o], 1), None, fx=4, fy=4, interpolation=cv2.INTER_NEAREST)
            t = np.concatenate([np.full((16, t.shape[1], 3), 255, np.uint8), t], 0)
            cv2.putText(t, f'{N} {x},{y} px{A} nearBen{nl} band{nb} {kinds}', (2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1); tiles.append(t)
    if tiles:
        h_ = max(t.shape[0] for t in tiles); w_ = max(t.shape[1] for t in tiles); cols = 3; rows = (len(tiles) + cols - 1) // cols
        S = np.full((rows * (h_ + 4), cols * (w_ + 4), 3), 128, np.uint8)
        for k, t in enumerate(tiles):
            r_, c_ = divmod(k, cols); S[r_ * (h_ + 4):r_ * (h_ + 4) + t.shape[0], c_ * (w_ + 4):c_ * (w_ + 4) + t.shape[1]] = t
        cv2.imwrite(os.path.join(out, f'new_text_near_ben_{N}.png'), S)
    R[N] = dict(new_text_px=int(new.sum()), new_blobs=len(blobs), blobs_near_ben_line_3px=sum(1 for q in blobs if q['near_ben_line_3px']),
                px_near_ben_line_3px=sum(q['near_ben_line_3px'] for q in blobs), blobs_in_rail_band=sum(1 for q in blobs if q['in_rail_band']),
                px_in_rail_band=sum(q['in_rail_band'] for q in blobs), rail_file=os.path.exists(p), listed=[q for q in blobs if q['near_ben_line_3px'] or q['in_rail_band']])
    print(N, {k: v for k, v in R[N].items() if k != 'listed'}, R[N]['listed'], flush=True)
json.dump(R, open(os.path.join(out, 'new_text_near_ben.json'), 'w', encoding='utf8', newline='\n'), indent=1)
