"""ben-labels diagnosis helpers (25 Nov 2026). Read-only on the repo; writes only into this diag folder."""
import os, sys, json
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); DIAG = os.path.abspath(os.path.join(HERE, '..'))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..', '..', '..')); SP = os.path.join(REPO, 'data', 'sanborn') + '/'
LINE, GAP, NEG_INK, POS, WRONG_PX, K = 3, 4, 4.0, 3.0, 11, 2      # edgenet.py / make_labels_v2.py constants

def scan(N): return cv2.imread(SP + f'cufp/22-{N}.jpg')

def ink_edgenet(bgr):
    """edgenet.ink_image's ink mask (the pixels that get NEG_INK when taught negative)"""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    return (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170))

def alpha_full(N, W, H): return cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
def alpha_half(N, w, h): return cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (w, h), interpolation=cv2.INTER_LINEAR) > 0.5

def ben(N): return json.load(open(SP + f'picks22_guided/22-{N}/edges_ben.json', encoding='utf8'))

def raster(lines, shape, scale=1.0, thick=1, val=1):
    m = np.zeros(shape, np.uint8)
    for a, b in lines: cv2.line(m, tuple(np.round(np.asarray(a, float) * scale).astype(int)), tuple(np.round(np.asarray(b, float) * scale).astype(int)), val, thick)
    return m

def mid_dist(a, b, p, q):
    """distance from the midpoint of a-b to the segment p-q"""
    a, b, p, q = (np.asarray(v, float) for v in (a, b, p, q)); m = (a + b) / 2; d = q - p; L2 = float(d @ d) or 1.0
    t = np.clip(((m - p) @ d) / L2, 0, 1); return float(np.hypot(*(m - (p + t * d))))

def groups(N):
    """Ben's lines on plate N by what he did: dict name -> list of (a, b) full px"""
    B = ben(N)['lines']; g = dict(deleted_net=[], deleted_sheet=[], added=[], moved_old=[], moved_new=[])
    for s in B:
        v = s.get('verdict')
        if v == 'wrong':
            (g['deleted_sheet'] if s.get('src') == 'sheet' else g['deleted_net']).append((s['a0'], s['b0']))
        elif s.get('added'):
            g['added'].append((s['a'], s['b']))
        elif s.get('moved') and mid_dist(s['a0'], s['b0'], s['a'], s['b']) > 8:
            g['moved_old'].append((s['a0'], s['b0'])); g['moved_new'].append((s['a'], s['b']))
    return g

def share(mask, arr, vals):
    n = int(mask.sum()); return {str(v): (round(float(((arr == v) & mask).sum()) / max(1, n), 4)) for v in vals} | {'px': n}

def wj(path, obj): json.dump(obj, open(path, 'w', encoding='utf8', newline='\n'), indent=1)
