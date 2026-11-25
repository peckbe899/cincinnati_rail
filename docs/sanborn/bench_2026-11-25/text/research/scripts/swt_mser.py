"""No-download text detectors already inside OpenCV, tried on two plate-44 crops:
  - Stroke Width Transform, cv2.text.detectTextSWT (only in the unet venv's cv2 5.0 contrib build)
  - MSER regions (cv2.MSER_create), kept when character-sized
Draws their boxes on the crop: pics/swt_<name>.jpg and pics/mser_<name>.jpg, and prints run times.
Run with the unet venv python (-B). Picture only; no score (there is no text ground truth yet)."""
import os, sys, time, cv2, numpy as np
R = r'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D'
B = os.path.join(R, 'data/sanborn/bench_2026-11-25/text/research')
scan = cv2.imread(os.path.join(R, 'data/sanborn/cufp/22-44.jpg'))
crops = {'houses': (5400, 1600, 6500, 2100), 'ludlow': (8300, 2300, 9900, 3400)}
for n, (x0, y0, x1, y1) in crops.items():
    c = scan[y0:y1, x0:x1].copy()
    t = time.time()
    try:
        rects, draw, chain = cv2.text.detectTextSWT(c, True)
        dt = time.time() - t
        o = c.copy()
        for r in rects:
            x, y, w, h = [int(v) for v in r]
            cv2.rectangle(o, (x, y), (x + w, y + h), (0, 0, 255), 2)
        cv2.imwrite(os.path.join(B, f'pics/swt_{n}.jpg'), o)
        print(n, 'SWT boxes', len(rects), 'seconds', round(dt, 2), 'MP', round(c.shape[0] * c.shape[1] / 1e6, 2))
    except Exception as e:
        print(n, 'SWT failed', e)
    g = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY)
    t = time.time()
    ms = cv2.MSER_create(delta=5, min_area=30, max_area=4000)
    regs, bbs = ms.detectRegions(g)
    dt = time.time() - t
    o = c.copy(); k = 0
    for (x, y, w, h) in bbs:
        if 10 <= h <= 70 and 3 <= w <= 70:
            cv2.rectangle(o, (int(x), int(y)), (int(x + w), int(y + h)), (255, 0, 0), 1); k += 1
    cv2.imwrite(os.path.join(B, f'pics/mser_{n}.jpg'), o)
    print(n, 'MSER regions', len(bbs), 'char-sized', k, 'seconds', round(dt, 2))
