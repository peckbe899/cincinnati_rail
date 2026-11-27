"""Shared helpers for sealed builder B (26 Nov 2026). Copied from text_v1/truth-fix/scripts/common.py; changed:
ROOT/INV point at data/sanborn and this sealed_B folder, and bins() is REMOVED (bin 8 of a sealed plate must never be
opened while choosing or labelling). Ink is ink_bins.py's rule: Lab L < 140 (0..255) on the paper mask
(cufp/N/png_alpha_s4.npy). Read-only on everything outside sealed_B."""
import os, json, math
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))     # data/sanborn (this is bench_2026-11-26/text_fix/sealed_B/scripts)
INV = os.path.abspath(os.path.join(HERE, '..'))                         # sealed_B; truth lives in INV/truth
INK_L = 140
ALLOWED = {'56', '58', '63', '71', '76', '84', '88', '92'}              # builder B's sealed plates; nothing else is opened
_cache = {}


def plate_img(p):
    if p not in ALLOWED: raise SystemExit(f'plate {p} is not one of builder B plates')
    k = ('img', p)
    if k not in _cache:
        for q in [q for q in _cache if q[1] != p]: del _cache[q]        # one plate in memory at a time
        _cache[k] = cv2.imread(os.path.join(ROOT, 'cufp', f'22-{p}.jpg'))
    return _cache[k]


def paper(p):
    k = ('paper', p)
    if k not in _cache:
        H, W = plate_img(p).shape[:2]
        al = np.load(os.path.join(ROOT, 'cufp', p, 'png_alpha_s4.npy'))
        _cache[k] = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST) > 0
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


def line_mask_bridged(ink, length, bridge=4, nang=72):
    """sealed-B addition (full crop only): like line_mask, but for each tested direction the ink is first closed with
    a 1 px line kernel of 2*bridge+1 px along that direction, so a printed line broken by the L<140 threshold into
    pieces with gaps up to 2*bridge px still counts as one straight run. The result is cut back to ink."""
    u = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    out = np.zeros_like(u); c = length // 2; b = bridge
    for i in range(nang):
        a = math.pi * i / nang; d = np.array([math.cos(a), math.sin(a)])
        kb = np.zeros((2 * b + 1, 2 * b + 1), np.uint8); e = d * b
        cv2.line(kb, tuple(np.round(b - e).astype(int).tolist()), tuple(np.round(b + e).astype(int).tolist()), 1, 1)
        v = cv2.morphologyEx(u, cv2.MORPH_CLOSE, kb)
        k = np.zeros((length, length), np.uint8); e = d * c
        cv2.line(k, tuple(np.round(c - e).astype(int).tolist()), tuple(np.round(c + e).astype(int).tolist()), 1, 1)
        out |= cv2.morphologyEx(v, cv2.MORPH_OPEN, k)
    return (out > 0) & ink.astype(bool)
