"""mixed_check.py CROP [--fixed] - ink pieces that lie wholly inside one word box (grown 4 px) and carry text (2) together
with not text (1) or don't care (3). A piece that touches no line outside the box should be all text, so its 1 and 3
pixels are likely errors (or deliberate hand calls: hooks, dashes under a label). Sheet: pics/CROP_mixed_N.jpg."""
import sys, os, json, argparse
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tc


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cid'); ap.add_argument('--fixed', action='store_true')
    ap.add_argument('--min', type=int, default=4)
    a = ap.parse_args()
    c = tc.crops_all()[a.cid]; x0, y0 = c['win'][:2]
    sc = tc.scan(a.cid); tr = tc.truth(a.cid, a.fixed); W = tc.words(a.cid, a.fixed)['words']
    wb = np.zeros(tr.shape, np.uint8)
    for w in W:
        if w.get('poly'): cv2.fillPoly(wb, [np.round(np.array(w['poly'], float) - [x0, y0]).astype(np.int32)], 1)
    wbg = cv2.dilate(wb, np.ones((9, 9), np.uint8)) > 0
    n, lab, st, cen = cv2.connectedComponentsWithStats((tr > 0).astype(np.uint8), connectivity=8)
    out = []
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if ar > 3000: continue
        comp = lab[y:y + h, x:x + w] == i
        inside = (wbg[y:y + h, x:x + w] & comp).sum()
        if inside < ar: continue
        v = tr[y:y + h, x:x + w][comp]
        n2, n1, n3 = int((v == 2).sum()), int((v == 1).sum()), int((v == 3).sum())
        if n2 and n1 + n3 >= a.min:
            out.append(dict(x=int(x + x0), y=int(y + y0), w=int(w), h=int(h), area=int(ar), n1=n1, n3=n3, n2=n2, cx=float(cen[i][0] + x0), cy=float(cen[i][1] + y0)))
    print(a.cid, 'mixed pieces', len(out), 'px 1:', sum(d['n1'] for d in out), 'px 3:', sum(d['n3'] for d in out))
    S, R = 4, 24; cells = []
    for k, d in enumerate(out):
        cx, cy = int(d['cx'] - x0), int(d['cy'] - y0)
        xa, ya = max(0, cx - R), max(0, cy - R); xb, yb = min(tr.shape[1], cx + R), min(tr.shape[0], cy + R)
        s1 = sc[ya:yb, xa:xb]; t1 = tr[ya:yb, xa:xb]; ov = tc.overlay(s1, t1)
        L = cv2.resize(s1, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST); Rr = cv2.resize(ov, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST)
        cell = np.full((2 * R * S + 16, 4 * R * S + 6, 3), 255, np.uint8)
        cell[16:16 + L.shape[0], :L.shape[1]] = L; cell[16:16 + Rr.shape[0], 2 * R * S + 6:2 * R * S + 6 + Rr.shape[1]] = Rr
        cv2.putText(cell, f'{k} ({d["x"]},{d["y"]}) 1:{d["n1"]} 3:{d["n3"]} 2:{d["n2"]}', (2, 12), cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 0, 0), 1)
        cells.append(cell)
    tag = 'fx' if a.fixed else 'v'
    for s in range(0, len(cells), 30):
        grp = cells[s:s + 30]; cols = 4; rows = (len(grp) + cols - 1) // cols
        H, Wd = grp[0].shape[:2]; sheet = np.full((rows * (H + 4), cols * (Wd + 4), 3), 200, np.uint8)
        for j, ce in enumerate(grp):
            r_, q = divmod(j, cols); sheet[r_ * (H + 4):r_ * (H + 4) + H, q * (Wd + 4):q * (Wd + 4) + Wd] = ce
        cv2.imwrite(os.path.join(tc.PICS, f'{a.cid}_mixed{tag}_{s // 30}.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    json.dump(out, open(os.path.join(tc.PICS, f'{a.cid}_mixed{tag}.json'), 'w'), indent=0)


if __name__ == '__main__':
    main()
