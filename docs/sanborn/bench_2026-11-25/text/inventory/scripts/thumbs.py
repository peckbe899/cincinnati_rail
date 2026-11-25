"""Thumbnails of the 8 inventory plates with a 500 px grid (full-size coordinates), for finding lettering by eye.
python -B thumbs.py   (run from anywhere)"""
import os, cv2
cv2.setNumThreads(4)
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))   # data/sanborn
OUT = os.path.join(os.path.dirname(__file__), '..', 'thumbs')
PLATES = ['44', '1A', '5', '90', '30', '60B', '47', '54A']
for p in PLATES:
    im = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{p}.jpg'))
    H, W = im.shape[:2]; s = 8
    t = cv2.resize(im, (W // s, H // s), interpolation=cv2.INTER_AREA)
    for x in range(0, W, 1000):
        cv2.line(t, (x // s, 0), (x // s, H // s), (255, 160, 0), 1)
        cv2.putText(t, str(x // 1000), (x // s + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
    for y in range(0, H, 1000):
        cv2.line(t, (0, y // s), (W // s, y // s), (255, 160, 0), 1)
        cv2.putText(t, str(y // 1000), (2, y // s + 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 0), 1)
    cv2.imwrite(os.path.join(OUT, f'{p}_s8.jpg'), t, [cv2.IMWRITE_JPEG_QUALITY, 85])
    print(p, W, H)
