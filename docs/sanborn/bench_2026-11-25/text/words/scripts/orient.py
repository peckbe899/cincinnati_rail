"""Which way up a string is. Three cues, no OCR:
  rule      a string is read left to right (Sanborn letters along a sloping street read downhill or uphill, but always
            rightwards); a string within VERT degrees of vertical is read bottom to top (FERGUS, house numbers and lot
            dimensions along the north-south streets of plate 44)
  marks     a feet mark or ditto (high) comes after the figures, a decimal point (low) inside, a period (low) after;
            turned over these become low-before and high-inside, which the print does not use
  shapes    nearest-neighbour test of the string's glyphs, turned each way, against the glyphs of the plate's own
            near-horizontal strings (upright by the rule): the turn whose glyphs look more like the upright bank wins.
            Nothing is fitted: the bank is the plate's own glyphs.
Patches are 32 x 32 px with the string's height scaled to 22 px."""
import numpy as np
import cv2

VERT = 12.0          # degrees
PH = 32; HS = 22.0   # patch size, string height in the patch


def frames(u):
    """reading direction u (unit) -> up vector (image y runs down)"""
    return np.array([u[1], -u[0]])


def patch(lab, gl, c, u, h, box):
    """glyph gl (1-based label in lab) around centre c, read along u, height h -> PH x PH float patch (ink 1)"""
    x, y, w, hh = box; pad = int(0.8 * h) + 4
    x0, y0 = max(0, x - pad), max(0, y - pad); x1, y1 = min(lab.shape[1], x + w + pad), min(lab.shape[0], y + hh + pad)
    m = (lab[y0:y1, x0:x1] == gl).astype(np.float32)
    k = HS / max(h, 1.0); up = frames(u)
    # patch coords: X = k * (p - c) . u + PH/2 ; Y = -k * (p - c) . up + PH/2, with p = crop pixel + (x0, y0)
    A = np.array([[k * u[0], k * u[1]], [-k * up[0], -k * up[1]]])
    t = np.array([PH / 2, PH / 2]) - A @ (np.asarray(c) - [x0, y0])
    M = np.c_[A, t].astype(np.float32)
    p = cv2.warpAffine(m, M, (PH, PH), flags=cv2.INTER_LINEAR, borderValue=0)
    p = cv2.GaussianBlur(p, (3, 3), 0.8)
    return p


def vec(p):
    v = p.ravel().astype(np.float32); v -= v.mean(); n = np.linalg.norm(v)
    return v / n if n > 0 else v


def best_sim(T, B, chunk=2048):
    """for each row of T, the largest cosine with any row of B"""
    out = np.empty(len(T), np.float32)
    for i in range(0, len(T), chunk):
        out[i:i + chunk] = (T[i:i + chunk] @ B.T).max(1)
    return out


def mark_vote(marks, flip):
    """+1 per mark placed as the print places marks, -1 per mark placed as it never does, for the chain order (flip
    False) or the reversed order (flip True)"""
    v = 0
    for m in marks:
        place, pos = m['place'], m['pos']
        if flip:
            place = {'high': 'low', 'low': 'high'}.get(place, place); pos = {'before': 'after', 'after': 'before'}.get(pos, pos)
        if place == 'mid': continue
        if (place, pos) in (('high', 'after'), ('low', 'inside'), ('low', 'after')): v += 1
        elif (place, pos) in (('low', 'before'), ('high', 'before')): v -= 1
    return v
