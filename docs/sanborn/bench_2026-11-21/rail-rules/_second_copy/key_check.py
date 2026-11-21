"""Picture of the KEY change on every plate where the proposed ink_bins.py found a KEY (rail-rules, 21 Nov 2026).
Read-only; writes key/key_check_*.jpg.
Each tile: the KEY box (green rectangle) with 150 px around it, at quarter size; the batch's rule tracks thick (railroad
red, streetcar orange), the proposed tracks thin (railroad black, streetcar blue).
    cd data/sanborn
    python bench_2026-11-21/rail-rules/key_check.py"""
import os, json
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.path.join(HERE, 'batch', 'bins_compare.json')))
tiles = []
for r in sorted(R, key=lambda r: r['plate']):
    N = r['plate']; x0, y0, x1, y1 = r['key']; im = cv2.imread(f'cufp/22-{N}.jpg', cv2.IMREAD_REDUCED_COLOR_4); H, W = im.shape[:2]
    X0, Y0, X1, Y1 = max(0, x0 - 150) // 4, max(0, y0 - 150) // 4, min(4 * W, x1 + 150) // 4, min(4 * H, y1 + 150) // 4
    c = im[Y0:Y1, X0:X1].copy(); off = np.array([X0, Y0])
    old = json.load(open(f'unet_data/{N}_rail_rule.json', encoding='utf8'))['tracks']
    tp = os.path.join(HERE, 'batch', 'tracks', f'{N}_rail_rule.json'); new = json.load(open(tp))['tracks'] if os.path.exists(tp) else []
    for t in old: cv2.polylines(c, [np.round(np.asarray(t['pts']) / 4 - off).astype(np.int32)], False, (0, 0, 230) if t['kind'] == 'railroad' else (0, 150, 255), 5)
    for t in new: cv2.polylines(c, [np.round(np.asarray(t['pts']) / 4 - off).astype(np.int32)], False, (0, 0, 0) if t['kind'] == 'railroad' else (200, 60, 0), 1)
    cv2.rectangle(c, (x0 // 4 - X0, y0 // 4 - Y0), (x1 // 4 - X0, y1 // 4 - Y0), (0, 200, 0), 2)
    c = cv2.resize(c, (240, int(240 * c.shape[0] / c.shape[1])), interpolation=cv2.INTER_AREA)
    c = cv2.copyMakeBorder(c, 18, max(0, 470 - c.shape[0] - 18), 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))[:470]
    cv2.putText(c, f"{N} rr {r['rr_in_key_before']} sc {r['sc_in_key_before']} px", (3, 13), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1); tiles.append(c)
for p in range(0, len(tiles), 12):
    t = tiles[p:p + 12]; t += [np.full_like(tiles[0], 255)] * (12 - len(t))
    cv2.imwrite(os.path.join(HERE, 'key', f'key_check_{p // 12}.jpg'), np.vstack([np.hstack(t[i:i + 6]) for i in range(0, 12, 6)]), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(len(tiles), 'tiles')
