"""Thumbnail montages of the batch's outline pictures (N_outlines.jpg), to sort cut plates by kind (visual-cut).

    python thumbs.py OUTNAME N [N ...]       (system python; reads only; writes OUTNAME.jpg here)
"""
import os, sys
import cv2, numpy as np
U = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/unet_data/'; OUT = os.path.dirname(os.path.abspath(__file__))
name, ns = sys.argv[1], sys.argv[2:]; tiles = []; TW = 760
for n in ns:
    im = cv2.imread(U + f'{n}_outlines.jpg')
    if im is None: continue
    s = TW / max(im.shape[:2]); t = cv2.resize(im, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)
    c = np.full((TW, TW, 3), 255, np.uint8); c[:t.shape[0], :t.shape[1]] = t
    cv2.putText(c, n, (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (0, 0, 255), 4)
    tiles.append(c)
while len(tiles) % 4: tiles.append(np.full((TW, TW, 3), 255, np.uint8))
rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
cv2.imwrite(os.path.join(OUT, name + '.jpg'), np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 80])
