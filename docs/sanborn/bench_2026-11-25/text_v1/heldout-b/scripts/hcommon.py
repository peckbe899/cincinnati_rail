"""Shared helpers for the held-out text truth H3 and H4 (heldout-b, 25 Nov 2026).
Written from scratch for this task. It reads only the scans and the paper masks; it never reads the finder, words or
any other prototype output, and never reads Ben's truth.

Ink is the same rule as tools/sanborn/unet/ink_bins.py and the T1-T7 truth: Lab L < 140 (0..255 scale) on the paper
mask (cufp/N/png_alpha_s4.npy, resized nearest), so the masks line up pixel for pixel with N_bins.png."""
import os, json, math
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
KEYDIR = os.path.abspath(os.path.join(HERE, '..'))                        # text_v1/heldout-b
V1 = os.path.abspath(os.path.join(KEYDIR, '..'))                          # text_v1
OUT = os.path.join(V1, 'heldout')                                         # deliverables H3_*, H4_*
WORK = os.path.join(KEYDIR, 'work')
ANNOT = os.path.join(KEYDIR, 'annot')
ROOT = os.path.abspath(os.path.join(V1, '..', '..'))                      # data/sanborn
INK_L = 140
PAD = 100

CROPS = {
    'H3': dict(plate='47', win=[7040, 4560, 8540, 5560], scale_ft=400,
               why="400 ft PDF sheet: Bustard Moore's (twice) and Chas. Brown's subdivisions with dense rotated lot "
                   "numbers, plain and in brackets, and rotated lot dimensions along lot lines; FYFFE and AVE. along "
                   "the streets, Saffer, Kavanaugh and Schmann (partial); Ch. & Emma Zorn and Sub of Lot 7 in spaced "
                   "letters; small framed buildings with story figures; Eliza and Isaac spaced letters; a rotated 6 in. "
                   "water pipe label; [2] and block 27; large empty lots with long lines; a dense block of narrow lots "
                   "at the bottom right (don't care)"),
    'H4': dict(plate='54A', win=[7190, 3950, 8690, 4950], scale_ft=100,
               why='100 ft, heavy pink tint: Dandridge St with house numbers on both block faces, lot numbers '
                   '128-205, story heights and ditto marks, lot dimensions, block 36, Noah alley, 12" sewer and '
                   '6" water pipe labels, the word STREET of the street below'),
}

_cache = {}


def plate_img(p):
    k = ('img', p)
    if k not in _cache: _cache[k] = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{p}.jpg'))
    return _cache[k]


def paper(p):
    k = ('paper', p)
    if k not in _cache:
        H, W = plate_img(p).shape[:2]
        al = np.load(os.path.join(ROOT, 'cufp', p, 'png_alpha_s4.npy'))
        _cache[k] = cv2.resize(al.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    return _cache[k]


def window(p, x0, y0, x1, y1):
    """BGR crop and ink mask (bool) of a window, clipped to the plate; returns the clipped window too"""
    im = plate_img(p); H, W = im.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    c = im[y0:y1, x0:x1]; lab = cv2.cvtColor(c, cv2.COLOR_BGR2LAB)
    ink = (lab[..., 0] < INK_L) & paper(p)[y0:y1, x0:x1]
    return c, ink, (x0, y0, x1, y1)


def straight_runs(ink, length, nang=48):
    """Ink pixels that lie on a straight run of at least `length` px in one of nang directions: an opening with a
    1 px wide line kernel, after a 3x3 closing (a printed line on the scan is broken every few dozen px), cut back to
    the ink. Returns bool, and the index of the best direction per pixel (-1 where none)."""
    u = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    out = np.zeros(ink.shape, bool); c = length // 2
    for i in range(nang):
        a = math.pi * i / nang; k = np.zeros((length, length), np.uint8)
        d = np.array([math.cos(a), math.sin(a)]) * (length - 1) / 2
        cv2.line(k, (int(round(c - d[0])), int(round(c - d[1]))), (int(round(c + d[0])), int(round(c + d[1]))), 1, 1)
        out |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return out & ink


def rbox(x1, y1, x2, y2, h):
    """centre, unit vectors along and across, length and height of a typed word line"""
    L = math.hypot(x2 - x1, y2 - y1); ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    a = math.radians(ang); u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
    return np.array([(x1 + x2) / 2, (y1 + y2) / 2]), u, v, L, h, ang


def poly_of(c, u, v, L, h):
    return np.array([c - u * L / 2 - v * h / 2, c + u * L / 2 - v * h / 2, c + u * L / 2 + v * h / 2, c - u * L / 2 + v * h / 2])


def jdump(obj, path):
    with open(path, 'w', encoding='utf8', newline='\n') as f: json.dump(obj, f, indent=1, ensure_ascii=False)
