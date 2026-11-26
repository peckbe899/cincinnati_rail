"""QA sheet of possible missed glyphs: python -B suspects.py H4 [minpx] [maxdim]
Every ink component in the window that is glyph sized (min px .. maxdim box) and is at least 80% non-text in the
built mask is cut out with 40 px of context, at 3x, scan on the left and mask on the right, numbered, into
work/<crop>_suspects_N.jpg (24 per sheet). The list goes to work/<crop>_suspects.json."""
import sys, os, json
import numpy as np, cv2
from scipy import ndimage as ndi
from hcommon import CROPS, OUT, WORK, window


def main():
    cid = sys.argv[1]; minpx = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    maxdim = int(sys.argv[3]) if len(sys.argv) > 3 else 45
    cr = CROPS[cid]; X0, Y0, X1, Y1 = cr['win']
    img, ink, _ = window(cr['plate'], X0, Y0, X1, Y1)
    m = cv2.imread(os.path.join(OUT, f'{cid}_mask.png'), 0)
    lab, n = ndi.label(ink, structure=np.ones((3, 3), int))
    objs = ndi.find_objects(lab); sizes = np.bincount(lab.ravel())
    out = []
    for k, sl in enumerate(objs, 1):
        hgt, wid = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if sizes[k] < minpx or max(hgt, wid) > maxdim: continue
        mm = lab[sl] == k
        if (m[sl][mm] == 1).mean() < 0.8: continue
        thin = min(hgt, wid) <= 4 and max(hgt, wid) >= 12
        out.append(dict(i=len(out), x=int(sl[1].start + X0), y=int(sl[0].start + Y0), w=int(wid), h=int(hgt),
                        px=int(sizes[k]), thin=bool(thin)))
    json.dump(out, open(os.path.join(WORK, f'{cid}_suspects.json'), 'w'), indent=0)
    col = np.full(img.shape, 250, np.uint8)
    col[m == 1] = (120, 120, 120); col[m == 2] = (0, 0, 230); col[m == 3] = (0, 210, 255)
    S, C = 3, 40
    cells = []
    for o in out:
        x0, y0 = o['x'] - X0 - C, o['y'] - Y0 - C; x1, y1 = x0 + o['w'] + 2 * C, y0 + o['h'] + 2 * C
        x0c, y0c, x1c, y1c = max(0, x0), max(0, y0), min(img.shape[1], x1), min(img.shape[0], y1)
        a = np.full((y1 - y0, x1 - x0, 3), 255, np.uint8); b = a.copy()
        a[y0c - y0:y1c - y0, x0c - x0:x1c - x0] = img[y0c:y1c, x0c:x1c]
        b[y0c - y0:y1c - y0, x0c - x0:x1c - x0] = col[y0c:y1c, x0c:x1c]
        cv2.rectangle(b, (C - 2, C - 2), (C + o['w'] + 1, C + o['h'] + 1), (230, 0, 230), 1)
        t = np.hstack([a, np.full((a.shape[0], 3, 3), 255, np.uint8), b])
        t = cv2.resize(t, None, fx=S, fy=S, interpolation=cv2.INTER_NEAREST)
        cv2.putText(t, f"{o['i']} ({o['x']},{o['y']})", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 0, 0), 1)
        cells.append(t)
    per = 24; cw = max([c.shape[1] for c in cells] + [1]); ch = max([c.shape[0] for c in cells] + [1])
    for s in range(0, len(cells), per):
        sheet = np.full((ch * 6, cw * 4, 3), 255, np.uint8)
        for j, c in enumerate(cells[s:s + per]):
            r, q = divmod(j, 4); sheet[r * ch:r * ch + c.shape[0], q * cw:q * cw + c.shape[1]] = c
        cv2.imwrite(os.path.join(WORK, f'{cid}_suspects_{s // per}.jpg'), sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print(cid, 'suspects', len(out), 'sheets', (len(cells) + per - 1) // per)


if __name__ == '__main__':
    main()
