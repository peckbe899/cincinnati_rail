"""Thumbnails of every uncut PDF sheet (cufp/N/source.json), for looking at margin, KEY, title, scale note, insets.

    python make_thumbs.py            -> thumbs/N.jpg (1/8 size, ~1400 px wide), with a 1000-px full-size grid drawn

Read-only on the repo; writes only into this folder (bench_2026-11-21/visual-pdf/).
"""
import glob, os, sys
import cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thumbs')
os.makedirs(OUT, exist_ok=True)


def pdf_plates():
    ps = [os.path.basename(os.path.dirname(p)) for p in glob.glob(D + 'cufp/*/source.json')]
    return sorted(ps, key=lambda s: (int(''.join(c for c in s if c.isdigit())), s))


if __name__ == '__main__':
    pl = sys.argv[1:] or pdf_plates()
    for n in pl:
        im = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_REDUCED_COLOR_4)
        t = cv2.resize(im, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA)   # 1/8 of full size
        for x in range(0, t.shape[1], 125):
            cv2.line(t, (x, 0), (x, 12), (0, 0, 255), 1)
        for y in range(0, t.shape[0], 125):
            cv2.line(t, (0, y), (12, y), (0, 0, 255), 1)
        cv2.putText(t, n, (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 3)
        cv2.imwrite(os.path.join(OUT, f'{n}.jpg'), t, [cv2.IMWRITE_JPEG_QUALITY, 80])
        print(n, im.shape, flush=True)
