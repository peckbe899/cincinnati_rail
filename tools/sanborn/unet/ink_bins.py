"""A first, rule-based sorting of a plate's black ink into bins, for Ben to look at in the line editor (17 November 2026).

    cd data/sanborn
    python ../../tools/sanborn/unet/ink_bins.py N [--win X0 Y0 X1 Y1] [--pic OUT.jpg]

Ben, 17 November 2026: "yes, try binning them and showing them in the plate editor so i can see". This is a rough first
guess made by rules at full size, not a trained classifier and not ground truth. It needs the plate's street map
(streetmap/22-N.json, street_map.py). Every dark pixel on the paper gets one bin:

  1 block line        ink on one of Ben's street-map lines
  2 lot line          other line ink in block ground
  3 building outline  ink on the edge of a pink or yellow fill
  4 railroad          a line with cross ticks (hatched), as along Vandalia on plate 44
  5 streetcar         heavy dashes, as down Hamilton on plate 44
  6 water pipe        a solid line in street ground that is not a block line (labelled "W. PIPE" on the print)
  7 sewer             thin dashes in street ground (labelled "SEWER" on the print)
  8 text and numbers  small separate marks
  9 not sorted        line ink where the ground is not known

Ben, same day: pipes and sewers are black, not coloured ("the sewage usually is a black line that says 'W. PIPE'"),
the coloured bands are not identified, and rail is two kinds ("the railroads (hatched lines like on Vandalia) and the
street cars (dashes like on Hamilton)"). So nothing here uses colour to tell one black line from another; colour only
finds the building fills.

How: marks are the connected pieces of ink. Small compact pieces are text; thin straight short pieces are dashes
(sewer in the street, dashed lot line in a block); thick straight short pieces are streetcar dashes. From the big
connected network the block lines and building outlines are taken out first, which lets the rest fall apart into
separate lines; a line carrying many short cross strokes is a railroad; the others are pipe (street ground) or lot line
(block ground). Ground is: inside a shape of the street map that closes = block; elsewhere the old area label
(unet_data/N_label.png, 0 street, 1 block, 255 not known), which was made from the reader's lines, not Ben's.
Writes unet_data/N_bins.png (the bin of every pixel) and unet_data/N_bins.json (counts).
"""
import json, sys, time
import numpy as np
import cv2
from scipy.spatial import cKDTree
NAMES = {1: 'block line', 2: 'lot line', 3: 'building outline', 4: 'railroad', 5: 'streetcar', 6: 'water pipe', 7: 'sewer', 8: 'text and numbers', 9: 'not sorted'}
COL = {1: (0, 150, 0), 2: (255, 140, 0), 3: (20, 70, 120), 4: (0, 0, 230), 5: (0, 150, 255), 6: (160, 0, 0), 7: (160, 170, 0), 8: (255, 0, 255), 9: (120, 120, 120)}   # BGR: green, light blue, brown, red, orange, navy, teal, magenta, grey
INK_L = 140      # darker than this (Lab L, 0..255) is ink
TEXT_MAX = 130   # a compact mark no bigger than this is text (street-name letters are about 90 px tall on plate 44)

def shape(lab, n):
    """every piece's area, bounding box, length and thickness (from its second moments, as for a straight bar)"""
    ys, xs = np.nonzero(lab); l = lab[ys, xs]; A = np.bincount(l, minlength=n).astype(float); A[A == 0] = 1
    mx = np.bincount(l, xs, n) / A; my = np.bincount(l, ys, n) / A; dx = xs - mx[l]; dy = ys - my[l]
    sxx = np.bincount(l, dx * dx, n) / A; syy = np.bincount(l, dy * dy, n) / A; sxy = np.bincount(l, dx * dy, n) / A
    t = (sxx + syy) / 2; d = np.sqrt(np.maximum(((sxx - syy) / 2) ** 2 + sxy ** 2, 0))
    return A, np.sqrt(12 * (t + d) + 1), np.sqrt(12 * np.maximum(t - d, 0) + 1), mx, my, 0.5 * np.arctan2(2 * sxy, sxx - syy)

def small_kinds(A, long_, thick, ext):
    """0 leave, 8 text, 7 thin dash, 5 streetcar dash, -1 a big piece"""
    k = np.full(len(A), -1, np.int8); fill = A / (long_ * thick)
    k[ext <= TEXT_MAX] = 8
    k[(thick <= 7.5) & (long_ >= 8) & (long_ <= 75) & (long_ / thick >= 3) & (fill >= 0.6) & (fill <= 1.5)] = 7
    k[(thick >= 8) & (thick <= 24) & (long_ >= 35) & (long_ <= 220) & (long_ / thick >= 3) & (fill >= 0.75) & (fill <= 1.4)] = 5
    k[(long_ >= 60) & (thick <= 12) & (long_ / thick >= 6)] = -1   # a straight piece of a broken line is a line, not text
    k[A < 6] = 0
    return k

def line_kernel(length, ang):
    k = np.zeros((length, length), np.uint8); c = length // 2; d = np.array([np.cos(ang), np.sin(ang)]) * c
    cv2.line(k, tuple(np.round(c - d).astype(int).tolist()), tuple(np.round(c + d).astype(int).tolist()), 1, 1); return k

def main():
    N = sys.argv[1]; t0 = time.time(); im = cv2.imread(f'cufp/22-{N}.jpg'); H, W = im.shape[:2]
    x0, y0, x1, y1 = (int(v) for v in sys.argv[sys.argv.index('--win') + 1:sys.argv.index('--win') + 5]) if '--win' in sys.argv else (0, 0, W, H)
    win = '--win' in sys.argv; im = im[y0:y1, x0:x1]; h, w = im.shape[:2]
    lab = cv2.cvtColor(im, cv2.COLOR_BGR2LAB); L = lab[..., 0]
    al = np.load(f'cufp/{N}/png_alpha_s4.npy'); paper = cv2.resize(al, (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1] > 0
    ink = (L < INK_L) & paper
    # building fills by colour (pink brick, yellow frame); an opening drops the narrow coloured bands, which are not buildings
    a = cv2.medianBlur(lab[..., 1], 5).astype(np.int16) - 128; b = cv2.medianBlur(lab[..., 2], 5).astype(np.int16) - 128
    fill = (((a >= 7) & (b <= 26)) | (b >= 32)) & (L >= INK_L) & paper
    fill = cv2.morphologyEx(cv2.morphologyEx(fill.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)), cv2.MORPH_OPEN, np.ones((15, 15), np.uint8))
    near_fill = cv2.dilate(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))) > 0
    deep_fill = cv2.erode(fill, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (19, 19))) > 0   # well inside a fill: a number printed on a building
    # ground and the block lines, from the street map
    SM = json.load(open(f'streetmap/22-{N}.json', encoding='utf8')); off = np.array([x0, y0])
    truth = np.zeros((h, w), np.uint8); closed = np.zeros((h, w), np.uint8)
    for l in SM['lines']: cv2.line(truth, tuple(np.round(np.array(l['a']) - off).astype(int).tolist()), tuple(np.round(np.array(l['b']) - off).astype(int).tolist()), 1, 13)
    for bl in SM['blocks']: cv2.fillPoly(closed, [np.round(np.array(bl['ring']) - off).astype(np.int32)], 1)
    old = cv2.resize(cv2.imread(f'unet_data/{N}_label.png', 0), (W, H), interpolation=cv2.INTER_NEAREST)[y0:y1, x0:x1]
    ground = np.where(closed == 1, 1, np.where(old == 0, 0, np.where(old == 1, 1, 2))).astype(np.uint8)   # 0 street, 1 block, 2 not known
    out = np.zeros((h, w), np.uint8)

    def small_pass(mask):
        """sort the small pieces of mask; returns what is left (the big pieces)"""
        n, lb, st, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
        A, lg, th, mx, my, an = shape(lb, n); ext = np.maximum(st[:, 2], st[:, 3]); k = small_kinds(A, lg, th, ext); k[0] = 0
        g = ground[np.clip(my.round().astype(int), 0, h - 1), np.clip(mx.round().astype(int), 0, w - 1)]
        k[(k == 7) & (g == 1)] = 2; k[(k == 7) & (g == 2)] = 9          # a thin dash in a block is a dashed lot line
        # a sewer is a row of dashes end to end. A thin stroke in the street with no other dash carrying on its line is a
        # figure 1 or a hyphen of a house number
        d = np.nonzero((k == 7) & (g == 0))[0]
        if len(d):
            P = np.c_[mx[d], my[d]]; T = cKDTree(P); chained = np.zeros(len(d), bool)
            for i, js in enumerate(T.query_ball_point(P, 160)):
                u = np.array([np.cos(an[d[i]]), np.sin(an[d[i]])])
                for j in js:
                    if j == i: continue
                    v = P[j] - P[i]; along = abs(v @ u); across = abs(v[0] * -u[1] + v[1] * u[0]); da = abs(((an[d[j]] - an[d[i]] + np.pi / 2) % np.pi) - np.pi / 2)
                    if across <= 7 and da <= 0.2 and along <= (lg[d[i]] + lg[d[j]]) / 2 + 45: chained[i] = True; break
            k[d[~chained]] = 8
        k[(k == 5) & (g != 0)] = 8                                       # a heavy bar off the street is a figure 1 of a block number
        kk = k[lb]; sel = mask & (kk > 0); out[sel] = kk[sel]; return mask & (kk == -1)

    big = small_pass(ink)
    blk = big & (truth == 1); out[blk] = 1
    bld = big & ~blk & near_fill; out[bld] = 3
    rest = small_pass(big & ~blk & ~bld)
    # text printed on a building is cut off from the page by its outline: a small piece that is all near a fill reads as outline. Put it back
    n, lb, st, _ = cv2.connectedComponentsWithStats((out == 3).astype(np.uint8), connectivity=8); A = st[:, 4].astype(float)
    indeep = np.bincount(lb.ravel(), deep_fill.ravel(), n) / np.maximum(A, 1); ext = np.maximum(st[:, 2], st[:, 3])
    txt = (ext <= TEXT_MAX) & (indeep >= 0.5); txt[0] = False; out[txt[lb] & (out == 3)] = 8
    # streetcar dashes that touch the thin line beside them: the parts of what is left that are 9 px thick or more
    # and letters that a line runs through (a street name crossed by a pipe line): thick, but not a bar
    E = lambda k: cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    th = cv2.morphologyEx(cv2.morphologyEx(rest.astype(np.uint8), cv2.MORPH_CLOSE, E(5)), cv2.MORPH_OPEN, E(7))
    n, lb, st, _ = cv2.connectedComponentsWithStats(th, connectivity=8)
    if n > 1:
        A, lg, tk, mx, my, _ = shape(lb, n); g = ground[np.clip(my.round().astype(int), 0, h - 1), np.clip(mx.round().astype(int), 0, w - 1)]
        bar = (tk >= 9) & (tk <= 24) & (lg >= 40) & (lg <= 220) & (lg / tk >= 3) & (g == 0); bar[0] = False
        let = ~bar & (np.maximum(st[:, 2], st[:, 3]) <= 200) & (np.maximum(st[:, 2], st[:, 3]) >= 25) & (A >= 150); let[0] = False
        for sel, kind in ((bar, 5), (let, 8)):
            m = (cv2.dilate(sel[lb].astype(np.uint8), E(7)) > 0) & rest; out[m] = kind; rest &= ~m
    # railroad: a long line carrying many short cross strokes. Short strokes = ink that a 9 px line fits along but a 23 px line does not
    r8 = rest.astype(np.uint8); short = np.zeros((h, w), np.uint8); long_ = np.zeros((h, w), np.uint8)
    for i in range(24):
        ang = np.pi * i / 24
        short |= cv2.morphologyEx(r8, cv2.MORPH_OPEN, line_kernel(9, ang)); long_ |= cv2.morphologyEx(r8, cv2.MORPH_OPEN, line_kernel(23, ang))
    stub = short & (1 - cv2.dilate(long_, np.ones((3, 3), np.uint8)))
    n, lb, st, _ = cv2.connectedComponentsWithStats(r8, connectivity=8); ns, ls, ss, cs = cv2.connectedComponentsWithStats(stub, connectivity=8)
    ok = (ss[:, 4] >= 5) & (ss[:, 4] <= 150); ok[0] = False
    owner = lb[np.clip(cs[:, 1].round().astype(int), 0, h - 1), np.clip(cs[:, 0].round().astype(int), 0, w - 1)]
    ticks = np.bincount(owner[ok & (owner > 0)], minlength=n); length = st[:, 4] / 4.5
    dens = ticks / np.maximum(length / 100, 0.01); rail = ((ticks >= 8) & (dens >= 1.0)) | ((ticks >= 4) & (dens >= 2.0))
    # a line inside a block of the street map that closes is a lot line with short strokes on it, not a railroad
    inblock = np.bincount(lb.ravel(), closed.ravel(), n) / np.maximum(st[:, 4], 1); rail &= inblock < 0.3; rail[0] = False
    rr = rest & rail[lb]; out[rr] = 4; rest &= ~rr
    out[rest & (ground == 0)] = 6; out[rest & (ground == 1)] = 2; out[rest & (ground == 2)] = 9
    cnt = {NAMES[k]: int((out == k).sum()) for k in NAMES}; tot = int(ink.sum())
    print(f'plate {N} window {x0},{y0}-{x1},{y1}: ink {tot} px, {100 * tot / max(1, paper.sum()):.1f}% of the paper | {time.time() - t0:.0f} s')
    for k in NAMES: print(f'  {k} {NAMES[k]:17s} {cnt[NAMES[k]]:9d} px  {100 * cnt[NAMES[k]] / max(1, tot):5.1f}%')
    print('  railroad pieces:', int(rail.sum()), '| ground of the ink: street', int((ink & (ground == 0)).sum()), 'block', int((ink & (ground == 1)).sum()), 'not known', int((ink & (ground == 2)).sum()))
    if '--pic' in sys.argv:
        c = (im * 0.35 + 255 * 0.65).astype(np.uint8)
        for k in NAMES: c[out == k] = COL[k]
        cv2.imwrite(sys.argv[sys.argv.index('--pic') + 1], c, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if not win:
        cv2.imwrite(f'unet_data/{N}_bins.png', out)
        json.dump(dict(plate=N, size=[W, H], note='rule-based first guess, not ground truth', ink_px=tot, bins={str(k): dict(name=NAMES[k], px=cnt[NAMES[k]], rgb=list(COL[k][::-1])) for k in NAMES}), open(f'unet_data/{N}_bins.json', 'w', encoding='utf8', newline='\n'), indent=1)

if __name__ == '__main__':
    main()
