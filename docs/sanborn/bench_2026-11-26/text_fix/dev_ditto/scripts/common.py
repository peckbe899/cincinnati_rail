"""Shared helpers: dev_ditto copy (26 Nov 2026) of text_v1/truth-fix/scripts/common.py, itself copied from text/inventory/scripts/common.py for truth v2. Unchanged code; ROOT resolves to data/sanborn from dev_ditto/scripts too. bins() is never called by the dev_ditto scripts.
Ink is defined exactly as tools/sanborn/unet/ink_bins.py defines it: Lab L < 140 (0..255 scale) on the paper
(cufp/N/png_alpha_s4.npy), so every mask here lines up pixel for pixel with N_bins.png."""
import os, json, math
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))     # data/sanborn (this is text_v1/truth-fix/scripts)
INV = os.path.abspath(os.path.join(ROOT, 'bench_2026-11-25', 'text_v1'))  # truth v2 lives in INV/truth
INK_L = 140
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
        _cache[k] = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST) > 0
    return _cache[k]


def bins(p):
    k = ('bins', p)
    if k not in _cache: _cache[k] = cv2.imread(os.path.join(ROOT, 'unet_data', f'{p}_bins.png'), 0)
    return _cache[k]


def window(p, x0, y0, x1, y1):
    """BGR crop, Lab crop, ink mask (bool) of a window, clipped to the plate"""
    im = plate_img(p); H, W = im.shape[:2]
    x0, y0, x1, y1 = max(0, x0), max(0, y0), min(W, x1), min(H, y1)
    c = im[y0:y1, x0:x1]; lab = cv2.cvtColor(c, cv2.COLOR_BGR2LAB)
    ink = (lab[..., 0] < INK_L) & paper(p)[y0:y1, x0:x1]
    return c, lab, ink, (x0, y0, x1, y1)


def line_mask(ink, length, nang=36, thick=1, close=True):
    """ink pixels lying on a straight run of at least `length` px in any of nang directions (morphological opening
    with a 1 px line kernel). Text strokes shorter than `length` are not taken. close: fill pinholes and 1-2 px breaks
    (3x3 closing) first, since a printed line on the scan is broken every few dozen px; the result is cut back to ink."""
    u = ink.astype(np.uint8); out = np.zeros_like(u)
    if close: u = cv2.morphologyEx(u, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    c = length // 2
    for i in range(nang):
        a = math.pi * i / nang; k = np.zeros((length, length), np.uint8)
        d = np.array([math.cos(a), math.sin(a)]) * c
        cv2.line(k, tuple(np.round(c - d).astype(int).tolist()), tuple(np.round(c + d).astype(int).tolist()), 1, thick)
        out |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k)
    return (out > 0) & ink.astype(bool)


def rrect_poly(cx, cy, w, h, ang_deg):
    """corners of a rotated rectangle: centre, length along the reading direction w, height h, reading angle in degrees
    measured in image coordinates (y down): 0 left to right, 90 reading downwards, -90 reading upwards"""
    a = math.radians(ang_deg); u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
    c = np.array([cx, cy])
    return np.array([c - u * w / 2 - v * h / 2, c + u * w / 2 - v * h / 2, c + u * w / 2 + v * h / 2, c - u * w / 2 + v * h / 2])


def jdump(obj, path):
    with open(path, 'w', encoding='utf8', newline='\n') as f: json.dump(obj, f, indent=1, ensure_ascii=False)
