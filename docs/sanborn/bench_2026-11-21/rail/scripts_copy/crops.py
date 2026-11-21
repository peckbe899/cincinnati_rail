"""Full-size crops with rail overlays (bench_2026-11-21/rail). Read-only on the repo; writes into OUTDIR only.

    cd data/sanborn
    python bench_2026-11-21/rail/crops.py N BINS.png RULE_TRACKS.json OUTDIR  x0,y0,x1,y1[:name] ... [--truth TRUTH.json] [--scale S]
    python bench_2026-11-21/rail/crops.py N BINS.png RULE_TRACKS.json OUTDIR --missed TRUTH.json   (one crop per missed stretch)

Overlay: rule railroad bin ink red, streetcar bin ink orange, rule tracks thin black (railroad) / blue (streetcar) lines,
Ben's tracks (if given) thin green (railroad) / magenta (streetcar), offset-free."""
import sys, os, json
import numpy as np, cv2


def overlay(im, B, rule, truth, x0, y0, x1, y1):
    c = im[y0:y1, x0:x1].copy(); b = B[y0:y1, x0:x1] if B is not None else None
    if b is not None:
        c[b == 4] = (0, 0, 230); c[b == 5] = (0, 150, 255)
    off = np.array([x0, y0])
    for t in rule:
        p = np.round(np.asarray(t['pts']) - off).astype(np.int32); cv2.polylines(c, [p], False, (0, 0, 0) if t['kind'] == 'railroad' else (200, 60, 0), 2)
    for t in truth or []:
        if t.get('src') == 'rule': continue
        p = np.round(np.asarray(t['pts']) - off).astype(np.int32); cv2.polylines(c, [p], False, (0, 170, 0) if t['kind'] == 'railroad' else (200, 0, 200), 1)
    return c


if __name__ == '__main__':
    N, bp, rp, od = sys.argv[1:5]; os.makedirs(od, exist_ok=True)
    im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    B = cv2.imread(bp, 0) if bp != '-' else None
    rule = json.load(open(rp, encoding='utf8'))['tracks'] if rp != '-' else []
    truth = json.load(open(sys.argv[sys.argv.index('--truth') + 1], encoding='utf8'))['tracks'] if '--truth' in sys.argv else None
    sc = float(sys.argv[sys.argv.index('--scale') + 1]) if '--scale' in sys.argv else 1.0
    wins = []
    for a in sys.argv[5:]:
        if a[0].isdigit() and ',' in a:
            box, _, name = a.partition(':'); wins.append((tuple(int(v) for v in box.split(',')), name or box.replace(',', '_')))
    for (x0, y0, x1, y1), name in wins:
        x0, y0 = max(0, x0), max(0, y0); x1, y1 = min(W, x1), min(H, y1)
        c = overlay(im, B, rule, truth, x0, y0, x1, y1)
        if sc != 1: c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(od, f'{N}_{name}.jpg'), c, [cv2.IMWRITE_JPEG_QUALITY, 90]); print('wrote', os.path.join(od, f'{N}_{name}.jpg'))
