"""sk_pic.py (skeptic): zoom sheets, scan beside finder codes (and the truth where a sealed crop covers the spot).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/skeptic/scripts/sk_pic.py OUT.png SPOTS.json [--zoom 4] [--panels 4|2]

SPOTS.json: a list of {plate, box [x0,y0,x1,y1] (full-plate px), label}. Each spot gives one row of panels:
  1 scan;  2 finder3 text (green) on the scan;  3 finder4: text both (green), new in finder4 (magenta), other codes
  faint (line ink blue, other ink orange);  4 truth if a sealed crop covers it (text green, non-text red, don't care grey).   --panels 2: only 1 and 3.
"""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
TR = 'bench_2026-11-26/text_fix/sealed_final'; G = 'bench_2026-11-26/text_fix/gate/out'
crops = json.load(open(f'{TR}/crops.json'))
_cache = {}


def get(path, flag):
    if path not in _cache:
        if len(_cache) > 6: _cache.clear()
        _cache[path] = cv2.imread(path, flag)
    return _cache[path]


def panel(plate, box, zoom, npan=4):
    x0, y0, x1, y1 = box
    im = get(f'cufp/22-{plate}.jpg', cv2.IMREAD_COLOR)[y0:y1, x0:x1]
    a = get(f'{G}/finder3/{plate}_text.png', cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1]
    b = get(f'{G}/finder4/{plate}_text.png', cv2.IMREAD_UNCHANGED)[y0:y1, x0:x1]
    ta = np.isin(a, (2, 3)); tb = np.isin(b, (2, 3))
    p1 = im.copy()
    p2 = im.copy(); p2[ta] = (0, 170, 0)
    p3 = (im * 0.5 + 127).astype(np.uint8); p3[b == 1] = (220, 120, 40); p3[b == 4] = (200, 60, 200); p3[b == 5] = (0, 140, 255)
    p3[ta & tb] = (0, 170, 0); p3[tb & ~ta] = (255, 0, 255)
    p4 = np.full_like(im, 255)
    for cid, c in crops.items():
        if c['plate'] != plate: continue
        cx0, cy0, cx1, cy1 = c['win']; ix0, iy0, ix1, iy1 = max(x0, cx0), max(y0, cy0), min(x1, cx1), min(y1, cy1)
        if ix1 <= ix0 or iy1 <= iy0: continue
        T = get(f'{TR}/{cid}_mask.png', 0)[iy0 - cy0:iy1 - cy0, ix0 - cx0:ix1 - cx0]
        sub = p4[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0]
        sub[T == 0] = (255, 255, 255); sub[T == 1] = (0, 0, 220); sub[T == 2] = (0, 170, 0); sub[T == 3] = (170, 170, 170)
        sub[(T == 0)] = (235, 235, 235)
    pp = (p1, p2, p3, p4) if npan == 4 else (p1, p3)
    ps = [cv2.resize(p, None, fx=zoom, fy=zoom, interpolation=cv2.INTER_NEAREST) for p in pp]
    gap = np.full((ps[0].shape[0], 6, 3), 60, np.uint8)
    out = [ps[0]]
    for q in ps[1:]: out += [gap, q]
    return np.hstack(out)


def main():
    a = sys.argv[1:]; out, spots = a[0], json.load(open(a[1]))
    zoom = int(a[a.index('--zoom') + 1]) if '--zoom' in a else 4
    npan = int(a[a.index('--panels') + 1]) if '--panels' in a else 4
    rows = []
    for s in spots:
        p = panel(s['plate'], s['box'], s.get('zoom', zoom), npan)
        lab = np.full((22, p.shape[1], 3), 255, np.uint8)
        cv2.putText(lab, f"{s.get('label', '')}  plate {s['plate']} box {s['box']}", (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        rows.append(np.vstack([lab, p]))
    Wm = max(r.shape[1] for r in rows)
    rows = [np.hstack([r, np.full((r.shape[0], Wm - r.shape[1], 3), 255, np.uint8)]) for r in rows]
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    cv2.imwrite(out, np.vstack(rows))
    print('wrote', out)


if __name__ == '__main__':
    main()
