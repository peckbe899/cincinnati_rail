"""railnew.py (final gate, CHECK ONLY): every blob of NEW text (finder4 text, not finder3 text) inside Ben's rail bands.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/gate/scripts/railnew.py F3_PATTERN F4_PATTERN OUT_DIR [N ...]   (default 44 5)

Bands as check_lines_rail.py: 14 px round Ben's railroad tracks, 12 px round his streetcar tracks
(picks22_guided/22-N/rail_ben.json, read only). New text = codes 2/3 in finder4 and not in finder3. Each 8-connected
blob of new text with a pixel in a band is listed (OUT_DIR/railnew.json) and drawn at 4x (OUT_DIR/railnew_N_k.png):
scan | finder4 codes (grey line ink, magenta old text, red new text, green other ink) with the band tinted blue,
plus the whole finder4 text piece the new blob belongs to. Writes only into OUT_DIR.
"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2

f3p, f4p, out = sys.argv[1:4]; plates = sys.argv[4:] or ['44', '5']; os.makedirs(out, exist_ok=True); R = {}
for N in plates:
    a = cv2.imread(f3p.replace('{plate}', N), 0); b = cv2.imread(f4p.replace('{plate}', N), 0); H, W = a.shape
    ta = np.isin(a, (2, 3)); tb = np.isin(b, (2, 3)); new = tb & ~ta; lost = ta & ~tb
    B = json.load(open(f'picks22_guided/22-{N}/rail_ben.json', encoding='utf8')); bands = {}
    for kind, tol in (('railroad', 14), ('streetcar', 12)):
        m = np.zeros((H, W), np.uint8)
        for t in B['tracks']:
            if t['kind'] == kind and len(t['pts']) >= 2: cv2.polylines(m, [np.round(np.array(t['pts'])).astype(np.int32)], False, 1, 1)
        bands[kind] = cv2.dilate(m, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * tol + 1, 2 * tol + 1))) > 0
    band = bands['railroad'] | bands['streetcar']
    n, lb, st, _ = cv2.connectedComponentsWithStats(new.astype(np.uint8), connectivity=8)
    nb_, lbb, stb, _ = cv2.connectedComponentsWithStats(tb.astype(np.uint8), connectivity=8)
    im = cv2.imread(f'cufp/22-{N}.jpg'); rows = []
    for i in range(1, n):
        x, y, w, h, A = (int(v) for v in st[i]); sub = lb[y:y + h, x:x + w] == i
        inb = {k: int((sub & bm[y:y + h, x:x + w]).sum()) for k, bm in bands.items()}
        if not any(inb.values()): continue
        pid = np.unique(lbb[y:y + h, x:x + w][sub]); pid = pid[pid > 0]
        px0 = min(int(stb[p, 0]) for p in pid); py0 = min(int(stb[p, 1]) for p in pid)
        px1 = max(int(stb[p, 0] + stb[p, 2]) for p in pid); py1 = max(int(stb[p, 1] + stb[p, 3]) for p in pid)
        r = dict(plate=N, k=len(rows), x=x, y=y, w=w, h=h, new_px=A, in_band=inb, piece_box=[px0, py0, px1, py1],
                 piece_px=int(sum(int(stb[p, 4]) for p in pid)), piece_new_share=round(A / max(1, sum(int(stb[p, 4]) for p in pid)), 3))
        cx, cy = (px0 + px1) // 2, (py0 + py1) // 2; s = max(40, (px1 - px0) // 2 + 25, (py1 - py0) // 2 + 25)
        X0, Y0, X1, Y1 = max(0, cx - s), max(0, cy - s), min(W, cx + s), min(H, cy + s)
        sc = im[Y0:Y1, X0:X1].copy(); o = (sc * 0.3 + 255 * 0.7).astype(np.uint8); cb = b[Y0:Y1, X0:X1]
        o[band[Y0:Y1, X0:X1]] = (o[band[Y0:Y1, X0:X1]] * 0.75 + np.array([255, 200, 120]) * 0.25).astype(np.uint8)
        o[cb == 1] = (150, 150, 150); o[cb == 5] = (0, 160, 0); o[cb == 4] = (0, 200, 230); o[np.isin(cb, (2, 3))] = (220, 0, 220)
        o[new[Y0:Y1, X0:X1]] = (0, 0, 255)
        z = max(2, min(6, 360 // max(1, 2 * s)))
        t_ = np.concatenate([sc, np.full((sc.shape[0], 2, 3), 255, np.uint8), o], 1); t_ = cv2.resize(t_, None, fx=z, fy=z, interpolation=cv2.INTER_NEAREST)
        cv2.putText(t_, f'{N} #{r["k"]} {x},{y} new {A}px band {inb}', (4, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 160), 1)
        cv2.imwrite(os.path.join(out, f'railnew_{N}_{r["k"]:02d}.png'), t_); rows.append(r)
    lb_n = cv2.connectedComponents((lost & band).astype(np.uint8), connectivity=8)[0] - 1
    R[N] = dict(new_text_px=int(new.sum()), lost_text_px=int(lost.sum()), new_in_band_px={k: int((new & bm).sum()) for k, bm in bands.items()},
                new_blobs_in_band=len(rows), lost_blobs_in_band=int(lb_n), blobs=rows)
    print(N, {k: v for k, v in R[N].items() if k != 'blobs'}, flush=True)
json.dump(R, open(os.path.join(out, 'railnew.json'), 'w', encoding='utf8', newline='\n'), indent=1)
