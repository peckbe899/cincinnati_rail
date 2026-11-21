"""Re-implementation of outlines.py's on_ink test (read-only on the repo), and a null test of it.
usage: python oink.py N  -> prints pass rates for stored sides, shifted sides, random-placed copies, Ben's lines (44)"""
import json, sys, os
import numpy as np, cv2
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'; U = SP + 'unet_data/'
OUT = os.path.dirname(os.path.abspath(__file__))
N = sys.argv[1]
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
alpha = cv2.resize(np.load(SP + f'cufp/{N}/png_alpha_s4.npy').astype(np.float32), (W, H)) > 0.5
hsv = cv2.cvtColor(full, cv2.COLOR_BGR2HSV); ink = (hsv[:, :, 2] < 120) | ((hsv[:, :, 1] < 90) & (hsv[:, :, 2] < 170)); del hsv
g = cv2.GaussianBlur(np.where(ink, cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), 255).astype(np.uint8), (3, 3), 0).astype(np.float32)
inner = cv2.erode(alpha.astype(np.uint8), np.ones((31, 31), np.uint8)) > 0
print(f'plate {N}: {W}x{H}, ink share of paper {ink[alpha].mean():.3f}')

def along(img, a, b, o=0.0):
    d = b - a; L = np.hypot(*d); nrm = np.array([-d[1], d[0]]) / (L or 1); t = np.linspace(0.06, 0.94, max(10, int(L))); q = a + np.outer(t, d) + nrm * o
    x = np.clip(q[:, 0].round().astype(int), 0, W - 1); y = np.clip(q[:, 1].round().astype(int), 0, H - 1); return img[y, x]
def on_ink(a, b):
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    return bool(max(np.mean([along(g, a + nrm * s, b + nrm * s, o).mean() for o in (-6, -3, 3, 6)]) - along(g, a + nrm * s, b + nrm * s).mean() for s in (-2, -1, 0, 1, 2)) > 25)
def score(a, b):
    """the margin on_ink thresholds (>25 passes)"""
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    return max(np.mean([along(g, a + nrm * s, b + nrm * s, o).mean() for o in (-6, -3, 3, 6)]) - along(g, a + nrm * s, b + nrm * s).mean() for s in (-2, -1, 0, 1, 2))
def coverage(a, b):
    """stricter alternative: share of samples along the line where a thin dark ridge parallel to it lies within 2 px
    (ink at the centre, paper at +-6 on both sides) -- a perpendicular crossing has ink at +-6 too and does not count"""
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d)
    c = np.min([along(g, a + nrm * s, b + nrm * s) for s in (-2, -1, 0, 1, 2)], axis=0)
    l = np.min([along(g, a + nrm * s, b + nrm * s) for s in (-7, -6, -5)], axis=0); r = np.min([along(g, a + nrm * s, b + nrm * s) for s in (5, 6, 7)], axis=0)
    return float(((c < 170) & (l > c + 40) & (r > c + 40)).mean())

def rate(segs, f=on_ink):
    if not segs: return float('nan'), float('nan'), 0
    ok = np.array([f(a, b) for a, b in segs], float); L = np.array([np.hypot(*(b - a)) for a, b in segs])
    return ok.mean(), (ok * L).sum() / L.sum(), len(segs)

rng = np.random.default_rng(0)
res = dict(plate=N)
o = json.load(open(SP + f'picks22_guided/22-{N}/outlines.json', encoding='utf8'))
sides = [(np.array(s['a']), np.array(s['b']), s['state']) for p in o for s in p if s['state'] != 'short' and not s.get('paper_edge')]
segs = [(a, b) for a, b, _ in sides]; Ls = np.array([np.hypot(*(b - a)) for a, b in segs])
agree = np.mean([on_ink(a, b) == (st == 'on print') for a, b, st in sides])
print(f'{len(segs)} kept sides (not short, not paper edge); reimplementation agrees with stored state on {100 * agree:.1f}%')
print(f'side length px: median {np.median(Ls):.0f}, p10 {np.percentile(Ls, 10):.0f}, p90 {np.percentile(Ls, 90):.0f}; share of sides < 130 px (kept only if on_ink): {np.mean(Ls < 130):.2f} by count, {Ls[Ls < 130].sum() / Ls.sum():.2f} by length')
res['stored'] = rate(segs)
print(f'stored sides pass on_ink: {100 * res["stored"][0]:.1f}% by count, {100 * res["stored"][1]:.1f}% by length')
long_ = [(a, b) for a, b in segs if np.hypot(*(b - a)) >= 130]
print(f'  of sides >= 130 px only (not pre-filtered by on_ink): {100 * rate(long_)[1]:.1f}% by length, n={len(long_)}')
sh = {}
for dd in (3, 5, 8, 12, 16, 24, 32, 48, 64, 96):
    ss = []
    for a, b in long_:
        d = b - a; n_ = np.array([-d[1], d[0]]) / np.hypot(*d); sg = rng.choice([-1, 1]); ss.append((a + n_ * dd * sg, b + n_ * dd * sg))
    ok = [(a, b) for a, b in ss if inner[int(np.clip((a[1] + b[1]) / 2, 0, H - 1)), int(np.clip((a[0] + b[0]) / 2, 0, W - 1))]]
    r = rate(ok); sh[dd] = r; print(f'  sides >= 130 px shifted {dd:3d} px sideways: pass {100 * r[1]:.1f}% by length (n={r[2]})')
res['shifted'] = sh
# random placement: each long side moved to a random spot on the paper, same length and direction
rp = []
ys, xs = np.nonzero(inner[::8, ::8])
for a, b in long_:
    for _ in range(3):
        k = rng.integers(len(xs)); c = np.array([xs[k] * 8, ys[k] * 8], float); d = (b - a) / 2
        if inner[int(np.clip(c[1] + d[1], 0, H - 1)), int(np.clip(c[0] + d[0], 0, W - 1))] and inner[int(np.clip(c[1] - d[1], 0, H - 1)), int(np.clip(c[0] - d[0], 0, W - 1))]: rp.append((c - d, c + d))
r = rate(rp); res['random_same_dir'] = r; print(f'random spot, same length and direction as a side: pass {100 * r[1]:.1f}% by length (n={r[2]})')
# random spot, random direction
rr = []
for a, b in long_:
    L = np.hypot(*(b - a))
    for _ in range(3):
        k = rng.integers(len(xs)); c = np.array([xs[k] * 8, ys[k] * 8], float); th = rng.uniform(0, np.pi); d = np.array([np.cos(th), np.sin(th)]) * L / 2
        if inner[int(np.clip(c[1] + d[1], 0, H - 1)), int(np.clip(c[0] + d[0], 0, W - 1))] and inner[int(np.clip(c[1] - d[1], 0, H - 1)), int(np.clip(c[0] - d[0], 0, W - 1))]: rr.append((c - d, c + d))
r = rate(rr); res['random_any_dir'] = r; print(f'random spot, random direction: pass {100 * r[1]:.1f}% by length (n={r[2]})')
# alternative test: coverage
cv_true = np.array([coverage(a, b) for a, b in long_]); cv_sh8 = []; cv_sh16 = []; cv_sh32 = []
for a, b in long_:
    d = b - a; n_ = np.array([-d[1], d[0]]) / np.hypot(*d)
    for dd, lst in ((8, cv_sh8), (16, cv_sh16), (32, cv_sh32)):
        sg = rng.choice([-1, 1]); lst.append(coverage(a + n_ * dd * sg, b + n_ * dd * sg))
cv_rp = np.array([coverage(a, b) for a, b in rp])
for nm, arr in (('stored >=130', cv_true), ('shift 8', np.array(cv_sh8)), ('shift 16', np.array(cv_sh16)), ('shift 32', np.array(cv_sh32)), ('random same dir', cv_rp)):
    print(f'coverage {nm:16s}: median {np.median(arr):.2f}, share >= 0.5: {np.mean(arr >= 0.5):.2f}, >= 0.7: {np.mean(arr >= 0.7):.2f}')
res['cov'] = dict(true=cv_true.tolist(), sh8=cv_sh8, sh16=cv_sh16, sh32=cv_sh32, rp=cv_rp.tolist())
# score margins
sc_t = np.array([score(a, b) for a, b in long_]); sc_r = np.array([score(a, b) for a, b in rp])
print(f'on_ink margin (pass > 25): stored sides median {np.median(sc_t):.0f}; random same-dir median {np.median(sc_r):.0f}, p75 {np.percentile(sc_r, 75):.0f}')
if N == '44':
    sm = json.load(open(SP + 'streetmap/22-44.json', encoding='utf8'))
    for kind in ('printed', 'drawn', 'sheet_edge'):
        bl = [(np.array(l['a'], float), np.array(l['b'], float)) for l in sm['lines'] if l['kind'] == kind and np.hypot(l['b'][0] - l['a'][0], l['b'][1] - l['a'][1]) > 20]
        bl_in = [(a, b) for a, b in bl if inner[int(np.clip((a[1] + b[1]) / 2, 0, H - 1)), int(np.clip((a[0] + b[0]) / 2, 0, W - 1))]]
        r = rate(bl_in); c = np.array([coverage(a, b) for a, b in bl_in]) if bl_in else np.array([np.nan])
        print(f"Ben's {kind} lines (inner): on_ink pass {100 * r[1]:.1f}% by length (n={r[2]}); coverage median {np.median(c):.2f}, >=0.5 {np.mean(c >= 0.5):.2f}")
        if kind == 'printed':
            for dd in (5, 8, 12, 16, 24, 32, 48):
                ss = []
                for a, b in bl_in:
                    d = b - a; n_ = np.array([-d[1], d[0]]) / np.hypot(*d); sg = rng.choice([-1, 1]); ss.append((a + n_ * dd * sg, b + n_ * dd * sg))
                r = rate(ss); c = np.array([coverage(a, b) for a, b in ss])
                print(f"  Ben's printed lines shifted {dd:2d} px: on_ink pass {100 * r[1]:.1f}% by length; coverage>=0.5 {np.mean(c >= 0.5):.2f}")
json.dump(res, open(os.path.join(OUT, f'oink_{N}.json'), 'w'), default=float)
