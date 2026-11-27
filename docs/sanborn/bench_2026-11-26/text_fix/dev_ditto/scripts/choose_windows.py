"""Draw random 400 x 300 windows in built-up areas, seeded by plate name (dev_ditto, 26 Nov 2026).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/dev_ditto/scripts/choose_windows.py [--n 30]

For each plate of PLATES, draws window corners uniformly over the plate with random.Random('ditto-' + plate) and keeps
the first --n windows (in draw order) that pass:
  - wholly on the paper (99% or more of the window's pixels on cufp/N/png_alpha_s4.npy);
  - BUILT-UP: 3% or more of the window shows building colour (measured at 1/4 size): pink (Lab a* more than 5 above
    the plate's median a* on the paper: brick) or yellow (b* more than 7 above the median b*: frame). This uses only
    the scan colours, set by eye on plates 90 and 5 (pics/colour_90.jpg, colour_5.jpg);
  - INKED (v2, added after the first look: plate 90's rank 4 and 86's rank 2 were bare paper whose yellowed edge passed
    as building colour): 2.5% or more of the window's full-size pixels are ink (L < 140 on the paper). Same draws, same
    order; the v1 list is kept in choose/windows_v1.json;
  - not overlapping the old held-out crops H1-H4 (grown by 25 px) nor an earlier kept window of the same plate.
Every draw and its verdict goes to choose/windows_all.json; the kept windows, in order, to choose/windows.json.
The windows are then looked at IN THIS ORDER and every ditto mark inside is taken, whatever it looks like.
Reads only the scan and its paper mask: never a finder output, never bins."""
import json, os, random, sys
sys.dont_write_bytecode = True
import numpy as np, cv2

HERE = os.path.dirname(os.path.abspath(__file__)); DD = os.path.normpath(os.path.join(HERE, '..'))
PLATES = {100: ['44', '5', '1A', '3', '54A', '2', '4', '12', '57'],
          200: ['90', '30', '60B', '19', '26A', '64A', '74', '86'],
          400: ['47', '49', '93A', '94', '48']}
SEALED = set('6 9 52 56 58 63 35 38 41 66 71 76 84 88 46 92'.split())
HELD = {'90': [[5640, 3950, 7140, 4950], [880, 2100, 2380, 3100]], '47': [[7040, 4560, 8540, 5560]], '54A': [[7190, 3950, 8690, 4950]]}
WW, WH = 400, 300
S = 4          # colour map at 1/4 size
BUILT = 0.03   # building-colour share of a window
INKED = 0.025  # v2: ink share of a window (full size)


def overlap(a, b, pad=0):
    return not (a[2] + pad <= b[0] or b[2] + pad <= a[0] or a[3] + pad <= b[1] or b[3] + pad <= a[1])


def colour_map(p):
    im = cv2.imread(f'cufp/22-{p}.jpg'); H, W = im.shape[:2]
    s = cv2.resize(im, (W // S, H // S), interpolation=cv2.INTER_AREA)
    al = np.load(f'cufp/{p}/png_alpha_s4.npy'); pap = cv2.resize(al.astype(np.uint8), (W // S, H // S), interpolation=cv2.INTER_NEAREST) > 0
    lab = cv2.cvtColor(s, cv2.COLOR_BGR2LAB).astype(np.int16)
    am, bm = np.median(lab[..., 1][pap]), np.median(lab[..., 2][pap])
    pink = (lab[..., 1] > am + 5) & pap; yel = (lab[..., 2] > bm + 7) & pap & ~pink
    L = cv2.cvtColor(im, cv2.COLOR_BGR2LAB)[..., 0]
    papf = cv2.resize(al.astype(np.uint8), (W, H), interpolation=cv2.INTER_NEAREST) > 0
    ink = ((L < 140) & papf).astype(np.float32)
    inkq = cv2.resize(ink[:H // S * S, :W // S * S], (W // S, H // S), interpolation=cv2.INTER_AREA)   # ink share per 4x4 cell
    return (W, H), pap, pink | yel, dict(a_med=float(am), b_med=float(bm)), inkq


def main():
    n_keep = int(sys.argv[sys.argv.index('--n') + 1]) if '--n' in sys.argv else 30
    allrec, keep = {}, {}
    for scale, plates in PLATES.items():
        for p in plates:
            assert p not in SEALED
            (W, H), pap, bld, med, inkq = colour_map(p)
            ip = cv2.integral(pap.astype(np.uint8)); ib = cv2.integral(bld.astype(np.uint8)); ii = cv2.integral(inkq.astype(np.float64))
            box = lambda I, x0, y0, x1, y1: int(I[y1, x1] - I[y0, x1] - I[y1, x0] + I[y0, x0])
            seed = f'ditto-{p}'; rng = random.Random(seed); draws = []; kept = []
            for k in range(5000):
                if len(kept) >= n_keep: break
                x0 = rng.randrange(0, W - WW); y0 = rng.randrange(0, H - WH); w = [x0, y0, x0 + WW, y0 + WH]
                a = [x0 // S, y0 // S, (x0 + WW) // S, (y0 + WH) // S]; area = (a[2] - a[0]) * (a[3] - a[1])
                fp = box(ip, *a) / area; fb = box(ib, *a) / area; fi = float(ii[a[3], a[2]] - ii[a[1], a[2]] - ii[a[3], a[0]] + ii[a[1], a[0]]) / area
                why = 'ok'
                if fp < 0.99: why = 'off paper'
                elif fb < BUILT: why = 'not built-up'
                elif fi < INKED: why = 'too little ink'
                elif any(overlap(w, h, 25) for h in HELD.get(p, [])): why = 'overlaps H1-H4'
                elif any(overlap(w, q['win']) for q in kept): why = 'overlaps an earlier window'
                d = dict(draw=k, win=w, paper=round(fp, 3), building=round(fb, 3), ink=round(fi, 4), verdict=why); draws.append(d)
                if why == 'ok': kept.append(dict(rank=len(kept) + 1, win=w, building=round(fb, 3), ink=round(fi, 4), draw=k))
            allrec[p] = dict(scale=scale, seed=seed, colour=med, size=[W, H], draws=draws)
            keep[p] = dict(scale=scale, seed=seed, windows=kept)
            print(p, scale, 'draws', len(draws), 'kept', len(kept), 'built-up share of draws on paper',
                  round(sum(d['verdict'] != 'off paper' and d['building'] >= BUILT for d in draws) / max(1, sum(d['verdict'] != 'off paper' for d in draws)), 3))
    os.makedirs(os.path.join(DD, 'choose'), exist_ok=True)
    json.dump(allrec, open(os.path.join(DD, 'choose', 'windows_all.json'), 'w'), indent=0)
    json.dump(keep, open(os.path.join(DD, 'choose', 'windows.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
