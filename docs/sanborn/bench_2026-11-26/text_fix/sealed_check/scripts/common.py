"""Shared helpers for the sealed cross-check and merge (sealed_check, 26 Nov 2026).
Copied from text_v1/truth-fix/scripts/common.py; changed: ROOT/INV point at data/sanborn and this sealed_check folder;
bins() is REMOVED (no bin and no method output is ever read for the sealed set); only the 16 sealed plates can be opened;
line_mask_bridged() is sealed builder B's addition (used on SB-F1 only, crops.json "line_bridge").
Ink is ink_bins.py's rule: Lab L < 140 (0..255) on the paper mask (cufp/N/png_alpha_s4.npy)."""
import os, json, math
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))     # data/sanborn (this is bench_2026-11-26/text_fix/sealed_check/scripts)
INV = os.path.abspath(os.path.join(HERE, '..'))                         # sealed_check
FINAL = os.path.abspath(os.path.join(HERE, '..', '..', 'sealed_final'))  # the merged truth
INK_L = 140
SEALED = {'6', '9', '52', '56', '58', '63', '35', '38', '41', '66', '71', '76', '84', '88', '46', '92'}
_cache = {}


def plate_img(p):
    if p not in SEALED: raise SystemExit(f'plate {p} is not a sealed plate')
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
    """ink pixels lying on a straight run of at least `length` px in any of nang directions (v2, unchanged)"""
    u = ink.astype(np.uint8); out = np.zeros_like(u)
    if close: u = cv2.morphologyEx(u, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    c = length // 2
    for i in range(nang):
        a = math.pi * i / nang; k = np.zeros((length, length), np.uint8)
        d = np.array([math.cos(a), math.sin(a)]) * c
        cv2.line(k, tuple(np.round(c - d).astype(int).tolist()), tuple(np.round(c + d).astype(int).tolist()), 1, thick)
        out |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k)
    return (out > 0) & ink.astype(bool)


def line_mask_bridged(ink, length, bridge=4, nang=72):
    """sealed-B addition (full crop SB-F1 only), copied unchanged: like line_mask, but gaps up to 2*bridge px along each
    tested direction are closed first. The result is cut back to ink."""
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


def rrect_poly(cx, cy, w, h, ang_deg):
    a = math.radians(ang_deg); u = np.array([math.cos(a), math.sin(a)]); v = np.array([-math.sin(a), math.cos(a)])
    c = np.array([cx, cy])
    return np.array([c - u * w / 2 - v * h / 2, c + u * w / 2 - v * h / 2, c + u * w / 2 + v * h / 2, c - u * w / 2 + v * h / 2])


def jdump(obj, path):
    with open(path, 'w', encoding='utf8', newline='\n') as f: json.dump(obj, f, indent=1, ensure_ascii=False)
