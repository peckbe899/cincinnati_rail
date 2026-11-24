"""Integrator (23 Nov 2026): one overlay per plate folder of a train_v2-format data folder, quarter size (of the full scan).
    python -B overlay.py DATA_DIR OUT_DIR [PLATE ...]
Top: the area label over the scan (block green, street blue, not taught left bare). Bottom: the line target over the
scan (positive red, negative a light yellow wash, not scored bare). Orange: the validation boundary (valmask.png);
magenta box: the KEY box masked in meta.json (pseudo). Writes OUT_DIR/N.jpg (JPEG 85)."""
import json, os, sys
import numpy as np, cv2


def overlay(d, N, out):
    p = os.path.join(d, N); img = cv2.imread(os.path.join(p, 'img.jpg')); lab = cv2.imread(os.path.join(p, 'label.png'), 0); t = cv2.imread(os.path.join(p, 'lines.png'), 0)
    meta = json.load(open(os.path.join(p, 'meta.json'), encoding='utf8'))
    h, w = lab.shape; q = (w // 2, h // 2)
    base = cv2.resize(img, q, interpolation=cv2.INTER_AREA).astype(np.float32)
    lq = cv2.resize(lab, q, interpolation=cv2.INTER_NEAREST)
    A = base.copy()
    for v, col in ((1, (60, 200, 60)), (0, (230, 120, 30))):
        m = lq == v; A[m] = 0.55 * A[m] + 0.45 * np.array(col, np.float32)
    # lines: positives max-pooled so a 3 px full-size line shows at quarter size
    pos = cv2.resize(cv2.dilate((t == 1).astype(np.uint8), np.ones((3, 3), np.uint8)), q, interpolation=cv2.INTER_AREA) > 0
    neg = cv2.resize((t == 0).astype(np.uint8) * 255, q, interpolation=cv2.INTER_AREA) > 127
    L = base.copy(); L[neg] = 0.7 * L[neg] + 0.3 * np.array((120, 235, 255), np.float32); L[pos] = (0, 0, 230)
    A, L = A.clip(0, 255).astype(np.uint8), L.clip(0, 255).astype(np.uint8)
    vf = os.path.join(p, 'valmask.png')
    for I in (A, L):
        if os.path.exists(vf):
            v = cv2.resize(cv2.imread(vf, 0), q, interpolation=cv2.INTER_NEAREST)
            cs, _ = cv2.findContours((v > 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE); cv2.drawContours(I, cs, -1, (0, 140, 255), 4)
        kb = (meta.get('counts') or {}).get('key_box')
        if kb: cv2.rectangle(I, (kb[0] // 4, kb[1] // 4), (kb[2] // 4, kb[3] // 4), (255, 0, 255), 3)
    c = meta.get('counts', {})
    txt = f"{N} {meta['source']} {meta.get('ft_per_inch')} ft  block {c.get('block', 0)/1e6:.2f}M street {c.get('street', 0)/1e6:.2f}M  line+ {c.get('line_pos', 0)/1e6:.2f}M line- {c.get('line_neg', 0)/1e6:.1f}M (half/full px)"
    for I, s in ((A, 'AREA LABEL: green block, blue street'), (L, 'LINE TARGET: red line, yellow wash negative')):
        cv2.putText(I, s + '   ' + txt, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (0, 0, 0), 6); cv2.putText(I, s + '   ' + txt, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2)
    os.makedirs(out, exist_ok=True); cv2.imwrite(os.path.join(out, f'{N}.jpg'), np.vstack([A, L]), [cv2.IMWRITE_JPEG_QUALITY, 85])
    return os.path.join(out, f'{N}.jpg')


if __name__ == '__main__':
    d, out = sys.argv[1], sys.argv[2]
    plates = sys.argv[3:] or sorted(x for x in os.listdir(d) if os.path.isdir(os.path.join(d, x)))
    for N in plates: print(overlay(d, N, out), flush=True)
