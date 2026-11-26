"""tc.py - shared helpers for the truth check of the held-out crops H1-H4 and truth v2 T1-T7 (truth-check, 25 Nov 2026).
Reads only the scans, the truth masks and the word files. It never reads the finder, words, shapes or bin output."""
import os, json, math
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
KEY = os.path.abspath(os.path.join(HERE, '..'))                 # text_v1/truth-check
V1 = os.path.abspath(os.path.join(KEY, '..'))                   # text_v1
ROOT = os.path.abspath(os.path.join(V1, '..', '..'))            # data/sanborn
HELD = os.path.join(V1, 'heldout')                              # read only
TRUTH2 = os.path.join(V1, 'truth')                              # read only
FIXED = os.path.join(KEY, 'heldout_fixed')                      # my fixed copies of H1-H4
PICS = os.path.join(KEY, 'pics')
_c = {}


def crops_all():
    """all crop windows: H1-H4 from the two held-out crops files, T1-T7 from truth v2"""
    c = {}
    for f in ('crops_H1_H2.json', 'crops_H3_H4.json'):
        c.update(json.load(open(os.path.join(HELD, f), encoding='utf8')))
    c.update(json.load(open(os.path.join(TRUTH2, 'crops.json'), encoding='utf8')))
    return c


def src_dir(cid, fixed=False):
    if cid.startswith('H'): return FIXED if fixed else HELD
    return os.path.join(KEY, 'truth_v2_fixed') if fixed else TRUTH2


def plate_img(p):
    if ('img', p) not in _c: _c[('img', p)] = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{p}.jpg'))
    return _c[('img', p)]


def scan(cid):
    c = crops_all()[cid]; x0, y0, x1, y1 = c['win']
    return plate_img(c['plate'])[y0:y1, x0:x1].copy()


def truth(cid, fixed=False):
    return cv2.imread(os.path.join(src_dir(cid, fixed), f'{cid}_mask.png'), 0)


def words(cid, fixed=False):
    return json.load(open(os.path.join(src_dir(cid, fixed), f'{cid}_words.json'), encoding='utf8'))


COL = {1: (200, 110, 30), 2: (30, 30, 230), 3: (0, 200, 240)}    # BGR: not text blue, text red, don't care yellow


def overlay(sc, tr, fade=0.45):
    """scan faded on paper; ink coloured by truth class"""
    o = (255 - (255 - sc.astype(np.float32)) * fade).astype(np.uint8)
    for v, col in COL.items(): o[tr == v] = col
    return o


def draw_boxes(img, W, off, s, col=(0, 170, 0)):
    for w in W:
        p = w.get('poly')
        if not p: continue
        q = np.round((np.array(p, float) - off) * s).astype(np.int32)
        cv2.polylines(img, [q], True, col, 1, cv2.LINE_AA)


def grid(img, s, step=50, off=(0, 0), col=(160, 160, 160)):
    """faint grid every `step` crop px with full-plate labels"""
    h, w = img.shape[:2]
    for x in range(0, int(w / s) + 1, step):
        X = int(x * s); cv2.line(img, (X, 0), (X, 6), col, 1)
        cv2.putText(img, str(x + off[0]), (X + 2, 12), cv2.FONT_HERSHEY_PLAIN, 0.8, (0, 120, 0), 1)
    for y in range(0, int(h / s) + 1, step):
        Y = int(y * s); cv2.line(img, (0, Y), (6, Y), col, 1)
        cv2.putText(img, str(y + off[1]), (2, Y - 2), cv2.FONT_HERSHEY_PLAIN, 0.8, (0, 120, 0), 1)
    return img
