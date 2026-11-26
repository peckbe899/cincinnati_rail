"""prime_check.py CROP [--fixed] - words whose reading ends in a prime (') or inch mark ("), and ditto marks: is there a
small not-text ink piece (area 3-60 px, sides <= 12 px) within 12 px of the word box? Such a piece is often the prime or
the second tick of a ditto that the typed box left out. Writes a numbered sheet pics/CROP_prime_N.jpg (scan | overlay,
piece in magenta, word box in green) and pics/CROP_prime.json. Uses only the scan, the truth mask and the word boxes."""
import sys, os, json, argparse
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tc


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cid'); ap.add_argument('--fixed', action='store_true')
    a = ap.parse_args()
    c = tc.crops_all()[a.cid]; x0, y0 = c['win'][:2]
    sc = tc.scan(a.cid); tr = tc.truth(a.cid, a.fixed); W = tc.words(a.cid, a.fixed)['words']
    one = (tr == 1).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(one, connectivity=8)
    small = np.zeros(n, bool)
    for i in range(1, n):
        x, y, w, h, ar = st[i]; small[i] = 3 <= ar <= 60 and w <= 12 and h <= 12
    out = []
    for w in W:
        r = w['reading']
        if not (r.endswith("'") or r.endswith('"') or w['kind'] == 'ditto'): continue
        pm = np.zeros(tr.shape, np.uint8)
        cv2.fillPoly(pm, [np.round(np.array(w['poly'], float) - [x0, y0]).astype(np.int32)], 1)
        grown = cv2.dilate(pm, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))) > 0
        ids = np.unique(lab[grown & (one > 0)]); ids = [int(i) for i in ids if i > 0 and small[i]]
        for i in ids:
            out.append(dict(word=w['id'], reading=r, kind=w['kind'], piece=i, x=int(st[i][0] + x0), y=int(st[i][1] + y0),
                            w=int(st[i][2]), h=int(st[i][3]), area=int(st[i][4]), cx=float(cen[i][0] + x0), cy=float(cen[i][1] + y0),
                            poly=w['poly']))
    print(a.cid, 'pieces', len(out))
    S, R = 4, 24; cells = []
    for k, d in enumerate(out):
        cx, cy = int(d['cx'] - x0), int(d['cy'] - y0)
        xa, ya = max(0, cx - R), max(0, cy - R); xb, yb = min(tr.shape[1], cx + R), min(tr.shape[0], cy + R)
        s1 = sc[ya:yb, xa:xb]; t1 = tr[ya:yb, xa:xb]; ov = tc.overlay(s1, t1); ov[lab[ya:yb, xa:xb] == d['piece']] = (255, 0, 255)
        L = cv2.resize(s1, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST); Rr = cv2.resize(ov, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST)
        tc.draw_boxes(Rr, [dict(poly=d['poly'])], np.array([xa + x0, ya + y0]), S)
        cell = np.full((2 * R * S + 16, 4 * R * S + 6, 3), 255, np.uint8)
        cell[16:16 + L.shape[0], :L.shape[1]] = L; cell[16:16 + Rr.shape[0], 2 * R * S + 6:2 * R * S + 6 + Rr.shape[1]] = Rr
        cv2.putText(cell, f'{k} {d["word"]} {d["reading"]} ({d["x"]},{d["y"]}) a{d["area"]}', (2, 12), cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 0, 0), 1)
        cells.append(cell)
    for s in range(0, len(cells), 30):
        grp = cells[s:s + 30]; cols = 4; rows = (len(grp) + cols - 1) // cols
        H, Wd = grp[0].shape[:2]; sheet = np.full((rows * (H + 4), cols * (Wd + 4), 3), 200, np.uint8)
        for j, ce in enumerate(grp):
            r_, q = divmod(j, cols); sheet[r_ * (H + 4):r_ * (H + 4) + H, q * (Wd + 4):q * (Wd + 4) + Wd] = ce
        cv2.imwrite(os.path.join(tc.PICS, f'{a.cid}_prime_{s // 30}.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    json.dump([{k: v for k, v in d.items() if k != 'poly'} for d in out], open(os.path.join(tc.PICS, f'{a.cid}_prime.json'), 'w'), indent=0)


if __name__ == '__main__':
    main()
