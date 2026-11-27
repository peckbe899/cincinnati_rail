"""The 200 ft concern (fix_block_a check): of the ink the truth calls NOT text that lies on straight runs of 61 px or more
(the skeptic's line proxy, text_v1/skeptic/scripts/sk_score.py lineish(): opening with 61 px line kernels every 7.5 deg),
how much a mask calls text, on the dev crops of one scale.
    cd data/sanborn; python -B .../code/straight200.py TRUTH_DIR MASK_PATTERN [SCALE=200] [--codes 2,3]
MASK_PATTERN holds {crop} (crop-size masks) or {plate} (plate-size masks). Prints totals and per crop. Dev check only."""
import json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2


def straight(t1):
    u = t1.astype(np.uint8); s = np.zeros_like(t1); L = 61
    for ang in np.arange(0, 180, 7.5):
        k = np.zeros((L, L), np.uint8); c = L // 2; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
        p0 = np.round(c - d * c).astype(int); p1 = np.round(c + d * c).astype(int); cv2.line(k, tuple(p0), tuple(p1), 1, 1)
        s |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return s


def main():
    a = sys.argv; td, pat = a[1], a[2]; sc = int(a[3]) if len(a) > 3 and not a[3].startswith('--') else 200
    codes = [int(v) for v in a[a.index('--codes') + 1].split(',')] if '--codes' in a else [2, 3]
    crops = json.load(open(os.path.join(td, 'crops.json'))); tot = [0, 0]; per = {}; cache = {}
    for cid, c in sorted(crops.items()):
        if c.get('scale_ft_per_inch') != sc or not os.path.exists(os.path.join(td, f'{cid}_mask.png')): continue
        x0, y0, x1, y1 = c['win']; p = pat.replace('{crop}', cid).replace('{plate}', c['plate'])
        if p not in cache: cache = {p: cv2.imread(p, 0)}
        m = cache[p]
        if m.shape != (y1 - y0, x1 - x0): m = m[y0:y1, x0:x1]
        tr = cv2.imread(os.path.join(td, f'{cid}_mask.png'), 0); s = straight(tr == 1); called = int((s & np.isin(m, codes)).sum())
        per[cid] = [called, int(s.sum())]; tot[0] += called; tot[1] += int(s.sum())
    print(json.dumps(dict(called=tot[0], straight_px=tot[1], share=round(tot[0] / max(1, tot[1]), 5), per_crop={k: v for k, v in per.items() if v[0]})))


if __name__ == '__main__':
    main()
