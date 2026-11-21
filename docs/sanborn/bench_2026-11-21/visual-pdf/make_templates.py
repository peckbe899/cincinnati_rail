"""Cut the printed furniture of the 1922 atlas from two sheets, as quarter-size greyscale templates for map_area.py.

    python make_templates.py        -> templates/*.png and templates/preview.jpg

Boxes are full-size px of cufp/22-N.jpg, read off crops by eye (crops/*.jpg). These are stamps printed the same way on
every sheet (the KEY, the scale bars with the copyright line, the 'ATLAS OF CINCINNATI' title line, the compass rose);
the hand-lettered 'SCALE n FT. TO AN INCH' notes vary a little from sheet to sheet, so two of each are cut.
"""
import os
import numpy as np, cv2
D = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
HERE = os.path.dirname(os.path.abspath(__file__)); T = os.path.join(HERE, 'templates'); os.makedirs(T, exist_ok=True)
CUT = {   # name: (plate, x0, y0, x1, y1) full-size px
    'key': ('19', 6230, 262, 7090, 1730),
    'title': ('19', 10280, 270, 10870, 365),          # 'ATLAS OF CINCINNATI, O.' only: VOL. 1 and 2 both match
    'bar200': ('19', 8490, 6840, 9790, 7060),
    'bar400': ('47', 4120, 6960, 5360, 7185),
    'bar400b': ('92', 2680, 6380, 3940, 6580),        # a second stamp of the 400-ft bar (comma in 'Copyright, 1922,')
    'note200a': ('19', 10120, 670, 11040, 825),
    'note200b': ('72', 5250, 405, 6170, 545),
    'note400a': ('94', 9220, 468, 10140, 608),
    'rose': ('19', 3932, 584, 4292, 944),
}
if __name__ == '__main__':
    prev = []
    for name, (n, x0, y0, x1, y1) in CUT.items():
        g = cv2.imread(D + f'cufp/22-{n}.jpg', cv2.IMREAD_GRAYSCALE)[y0:y1, x0:x1]
        q = cv2.resize(g, ((x1 - x0) // 4, (y1 - y0) // 4), interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(T, f'{name}.png'), q); print(name, q.shape)
        prev.append(cv2.copyMakeBorder(q, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=0))
    w = max(p.shape[1] for p in prev)
    cv2.imwrite(os.path.join(T, 'preview.jpg'), np.vstack([cv2.copyMakeBorder(p, 0, 0, 0, w - p.shape[1], cv2.BORDER_CONSTANT, value=255) for p in prev]))
