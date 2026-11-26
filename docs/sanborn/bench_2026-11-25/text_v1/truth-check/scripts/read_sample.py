"""read_sample.py CROP [--n 30 --seed 25 --fixed] - a sheet of N random words of a crop, each turned to read left to right
(rotated by its angle), shown at about 56 px glyph height beside the scan context, with the truth reading printed under it.
Writes pics/CROP_read.jpg and pics/CROP_read.json (the sample). Uses only the scan and the word file."""
import sys, os, json, argparse, random, math
import numpy as np, cv2
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tc


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('cid'); ap.add_argument('--n', type=int, default=30)
    ap.add_argument('--seed', type=int, default=25); ap.add_argument('--fixed', action='store_true')
    a = ap.parse_args()
    c = tc.crops_all()[a.cid]; plate = c['plate']
    W = tc.words(a.cid, a.fixed)['words']
    rnd = random.Random(f'{a.seed}-{a.cid}'); samp = rnd.sample(W, min(a.n, len(W)))
    img = tc.plate_img(plate); cells = []
    for k, w in enumerate(samp):
        P = np.array(w['poly'], float); ctr = P.mean(0)
        L = max(w.get('length', 40), 20) + 30; H = max(w.get('height', 20), 10) + 30
        ang = w.get('angle', 0.0)
        R = int(math.hypot(L, H) / 2 + 10)
        x0, y0 = int(ctr[0] - R), int(ctr[1] - R)
        sub = img[max(0, y0):y0 + 2 * R, max(0, x0):x0 + 2 * R].copy()
        if sub.shape[0] < 2 * R or sub.shape[1] < 2 * R:
            pad = np.full((2 * R, 2 * R, 3), 255, np.uint8); oy, ox = max(0, -y0), max(0, -x0)
            pad[oy:oy + sub.shape[0], ox:ox + sub.shape[1]] = sub; sub = pad
        M = cv2.getRotationMatrix2D((R, R), ang, 1.0)
        rot = cv2.warpAffine(sub, M, (2 * R, 2 * R), borderValue=(255, 255, 255))
        cut = rot[int(R - H / 2):int(R + H / 2), int(R - L / 2):int(R + L / 2)]
        s = 56.0 / max(8.0, w.get('height', 20))
        s = min(s, 700.0 / cut.shape[1])
        cut = cv2.resize(cut, None, fx=s, fy=s, interpolation=cv2.INTER_CUBIC)
        cell = np.full((cut.shape[0] + 40, 720, 3), 255, np.uint8); cell[:cut.shape[0], :cut.shape[1]] = cut
        txt = f'{k} {w["id"]} [{w["kind"]}] {" ".join(w["flags"])}'
        cv2.putText(cell, txt, (4, cut.shape[0] + 14), cv2.FONT_HERSHEY_PLAIN, 1.0, (90, 90, 90), 1)
        cv2.putText(cell, w['reading'].replace('½', '1/2').replace('°', 'deg').replace('±', '+-'), (4, cut.shape[0] + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2)
        cells.append(cell)
    cols = 3; colw = 724; rows = [cells[i:i + cols] for i in range(0, len(cells), cols)]
    sheet_rows = []
    for r in rows:
        h = max(ce.shape[0] for ce in r); row = np.full((h + 4, cols * colw, 3), 220, np.uint8)
        for j, ce in enumerate(r): row[:ce.shape[0], j * colw:j * colw + ce.shape[1]] = ce
        sheet_rows.append(row)
    sheet = np.vstack(sheet_rows)
    # split into two images if very tall
    half = len(sheet_rows) // 2
    cv2.imwrite(os.path.join(tc.PICS, f'{a.cid}_read_a.jpg'), np.vstack(sheet_rows[:half]), [cv2.IMWRITE_JPEG_QUALITY, 90])
    cv2.imwrite(os.path.join(tc.PICS, f'{a.cid}_read_b.jpg'), np.vstack(sheet_rows[half:]), [cv2.IMWRITE_JPEG_QUALITY, 90])
    json.dump([dict(k=k, id=w['id'], reading=w['reading'], kind=w['kind'], flags=w['flags']) for k, w in enumerate(samp)],
              open(os.path.join(tc.PICS, f'{a.cid}_read.json'), 'w', encoding='utf8'), indent=0, ensure_ascii=False)
    print(a.cid, len(samp), 'flagged', sum(1 for w in samp if w['flags']))


if __name__ == '__main__':
    main()
