"""orphans.py CROP [--fixed] - contact sheets of not-text ink pieces that could be missed glyph parts:
pieces of truth-1 ink (8-connected, inside the 1 class only) that are glyph-sized (area 6-500 px, each side <= 40 px,
not long and thin) and lie within 14 px of a word box, or are glyph-sized and far from every line run.
Each cell: scan | overlay at 3x, 60x60 px around the piece, numbered. Writes pics/CROP_orph_N.jpg and pics/CROP_orph.json.
Uses only the scan, the truth mask and the word boxes."""
import sys, os, json, argparse
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tc


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cid'); ap.add_argument('--fixed', action='store_true')
    ap.add_argument('--near', type=int, default=14); ap.add_argument('--per', type=int, default=40)
    a = ap.parse_args()
    c = tc.crops_all()[a.cid]; x0, y0 = c['win'][:2]
    sc = tc.scan(a.cid); tr = tc.truth(a.cid, a.fixed); W = tc.words(a.cid, a.fixed)['words']
    wb = np.zeros(tr.shape, np.uint8)
    for w in W:
        if w.get('poly'): cv2.fillPoly(wb, [np.round(np.array(w['poly'], float) - [x0, y0]).astype(np.int32)], 1)
    near = cv2.dilate(wb, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * a.near + 1, 2 * a.near + 1))) > 0
    one = (tr == 1).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(one, connectivity=8)
    cand = []
    for i in range(1, n):
        x, y, w, h, ar = st[i]
        if ar < 6 or ar > 500 or w > 40 or h > 40: continue
        if max(w, h) > 4 * max(1, min(w, h)) and max(w, h) > 18: continue      # long thin: dash or line stub
        comp = lab[y:y + h, x:x + w] == i
        if not (near[y:y + h, x:x + w] & comp).any(): continue
        cand.append(dict(i=int(i), x=int(x + x0), y=int(y + y0), w=int(w), h=int(h), area=int(ar), cx=float(cen[i][0] + x0), cy=float(cen[i][1] + y0)))
    print(a.cid, 'candidates', len(cand))
    S, R = 3, 30
    cells = []
    for k, d in enumerate(cand):
        cx, cy = int(d['cx'] - x0), int(d['cy'] - y0)
        xa, ya = max(0, cx - R), max(0, cy - R); xb, yb = min(tr.shape[1], cx + R), min(tr.shape[0], cy + R)
        s1 = sc[ya:yb, xa:xb]; t1 = tr[ya:yb, xa:xb]
        ov = tc.overlay(s1, t1); m1 = (lab[ya:yb, xa:xb] == d['i'])
        ov[m1] = (255, 0, 255)                                                    # the candidate in magenta
        L = cv2.resize(s1, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST); Rr = cv2.resize(ov, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST)
        cell = np.full((2 * R * S + 16, 4 * R * S + 6, 3), 255, np.uint8)
        cell[16:16 + L.shape[0], :L.shape[1]] = L; cell[16:16 + Rr.shape[0], 2 * R * S + 6:2 * R * S + 6 + Rr.shape[1]] = Rr
        cv2.putText(cell, f'{k} ({d["x"]},{d["y"]}) {d["w"]}x{d["h"]} a{d["area"]}', (2, 12), cv2.FONT_HERSHEY_PLAIN, 0.9, (0, 0, 0), 1)
        cells.append(cell)
    os.makedirs(tc.PICS, exist_ok=True)
    tag = 'fx' if a.fixed else 'v'
    for s in range(0, len(cells), a.per):
        grp = cells[s:s + a.per]; cols = 4; rows = (len(grp) + cols - 1) // cols
        H, Wd = grp[0].shape[:2]; sheet = np.full((rows * (H + 4), cols * (Wd + 4), 3), 200, np.uint8)
        for j, ce in enumerate(grp):
            r, q = divmod(j, cols); sheet[r * (H + 4):r * (H + 4) + H, q * (Wd + 4):q * (Wd + 4) + Wd] = ce
        cv2.imwrite(os.path.join(tc.PICS, f'{a.cid}_orph{tag}_{s // a.per}.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 90])
    json.dump(cand, open(os.path.join(tc.PICS, f'{a.cid}_orph{tag}.json'), 'w'), indent=0)


if __name__ == '__main__':
    main()
