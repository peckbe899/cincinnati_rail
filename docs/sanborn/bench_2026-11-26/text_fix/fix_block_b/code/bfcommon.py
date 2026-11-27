"""Shared bits for blockfix (fix_block_b, 26 Nov 2026). Run everything from data/sanborn.
Guards: never on a sealed plate; H1-H4 windows listed so tools can stay out of them."""
import json, os, re
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..'))                       # fix_block_b/
DS = os.path.normpath(os.path.join(ROOT, '..', '..', '..'))              # data/sanborn
SEALED = {'6', '9', '52', '56', '58', '63', '35', '38', '41', '66', '71', '76', '84', '88', '46', '92'}
HWIN = {'H1': ('90', (5640, 3950, 7140, 4950)), 'H2': ('90', (880, 2100, 2380, 3100)),
        'H3': ('47', (7040, 4560, 8540, 5560)), 'H4': ('54A', (7190, 3950, 8690, 4950))}
DEVB = os.path.join(DS, 'bench_2026-11-26', 'text_fix', 'dev_block')
TV1 = os.path.join(DS, 'bench_2026-11-25', 'text_v1')
# finder3 masks: text_v1's own where they exist, else the dev_block runs (made with text_v1/code/finder3.py unchanged)
F3_DIRS = [os.path.join(TV1, 'classifier', 'out', 'finder3'), os.path.join(DEVB, 'finders', 'finder3')]
# the two folds of the dev windows, by plate (scales mixed in both)
FOLD = {'A': ['3', '54A', '30', '26A', '74', '49'], 'B': ['12', '19', '64A', '60B', '93A', '48']}


def guard(N):
    if str(N) in SEALED: raise SystemExit(f'plate {N} is sealed: blockfix will not run on it')


def scale_of(N):
    t = json.load(open(os.path.join(DS, 'scale_table.json')))
    return int(t[str(N)]['ft_per_inch'])


def load_scan(N):
    guard(N)
    im = cv2.imread(os.path.join(DS, 'cufp', f'22-{N}.jpg')); H, W = im.shape[:2]
    al = np.load(os.path.join(DS, 'cufp', str(N), 'png_alpha_s4.npy'))
    paper = cv2.resize(al.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    return im, paper


def f3_path(N):
    for d in F3_DIRS:
        p = os.path.join(d, f'{N}_text.png')
        if os.path.exists(p): return p
    return None


def in_hwin(N, box, pad=0):
    """True when box (x0,y0,x1,y1) overlaps an H window on plate N (grown by pad)"""
    for _, (p, w) in HWIN.items():
        if p != str(N): continue
        if box[0] < w[2] + pad and box[2] > w[0] - pad and box[1] < w[3] + pad and box[3] > w[1] - pad: return True
    return False


def candidates(N):
    """dev_block's survey list of block numbers on plate N: [(x, y, reading, note)] (rough to ~30 px)"""
    p = os.path.join(DEVB, 'candidates', f'{N}.txt'); out = []
    if not os.path.exists(p): return out
    for ln in open(p, encoding='utf8'):
        ln = ln.strip()
        if not ln or ln.startswith('#'): continue
        t = ln.split(None, 3)
        if len(t) < 3: continue
        try: out.append((int(t[0]), int(t[1]), t[2], t[3] if len(t) > 3 else ''))
        except ValueError: pass
    return out


def dev_crops():
    return json.load(open(os.path.join(DEVB, 'truth', 'crops.json')))


def lineish(t1):
    """the skeptic's stand-in for line ink (text_v1/skeptic/scripts/sk_score.py): ink on straight runs of 61 px or more
    (opened with 61 px line kernels every 7.5 degrees)"""
    u = t1.astype(np.uint8); straight = np.zeros(t1.shape, bool); L = 61
    for ang in np.arange(0, 180, 7.5):
        k = np.zeros((L, L), np.uint8); c = L // 2; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
        cv2.line(k, tuple(np.round(c - d * c).astype(int).tolist()), tuple(np.round(c + d * c).astype(int).tolist()), 1, 1)
        straight |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return straight
