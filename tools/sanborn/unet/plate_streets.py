"""Every street of a plate as a strip between its two printed block lines (14 November 2026).

    cd data/sanborn
    ../../tools/sanborn/unet/.venv/Scripts/python.exe ../../tools/sanborn/unet/plate_streets.py N

Ben, 14 November 2026: pull all the streets from the plate; they are what the U-nets are trained on. Today's parcels
cannot supply a street that was realigned (Reading, Ross on 82A) or one that is gone. The streets come from the plate:
- centre lines: the runs the guided reader traced (picks22_guided/22-N/merge.json "runs") plus hand-added streets
  (picks22_guided/22-N/streets_added.json: [{"name", "points": [[x, y], ...]}], plate px);
- for every piece of a centre line the printed block line is searched on each side: the scan's darkness along a line
  parallel to the piece, at every distance from HALF_MIN to HALF_MAX px; the block lines are the pair of clear dark lines
  nearest to equal distances either side (car tracks and pipes lie inside HALF_MIN or are dashed and fainter). Each
  found line is then turned onto the print (its two ends moved separately).
Writes unet_data/N_streets.json: pieces with "left" and "right" lines (None where no printed line was found), and
unet_data/N_streets_check.jpg (centre blue; block lines green; a piece with a side not found red).
"""
import json, os, sys
import numpy as np
import cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import _ws  # noqa: E402
N = sys.argv[1]; SP = _ws.DATA; D = SP + f'picks22_guided/22-{N}/'; OUT = SP + 'unet_data/'
HALF_MIN, HALF_MAX, TURN, CONTRAST, PIECE = 22, 95, 6, 22.0, 220.0
full = cv2.imread(SP + f'cufp/22-{N}.jpg'); H, W = full.shape[:2]
g = cv2.GaussianBlur(cv2.cvtColor(full, cv2.COLOR_BGR2GRAY), (3, 3), 0).astype(np.float32)
def dark(a, b):
    d = b - a; L = np.hypot(*d); t = np.linspace(0.05, 0.95, max(10, int(L)))
    q = a + np.outer(t, d); x = q[:, 0].round().astype(int); y = q[:, 1].round().astype(int); ok = (x >= 0) & (x < W) & (y >= 0) & (y < H)
    return float(g[y[ok], x[ok]].mean()) if ok.sum() > 0.6 * len(t) else None
def side_lines(a, b):
    """candidate block lines beside the piece a-b: {signed distance: contrast}, local darkness minima"""
    d = b - a; nrm = np.array([-d[1], d[0]]) / np.hypot(*d); prof = {}
    for o in range(-HALF_MAX - 4, HALF_MAX + 5):
        v = dark(a + nrm * o, b + nrm * o)
        if v is not None: prof[o] = v
    out = {}
    for o in prof:
        if abs(o) < HALF_MIN or abs(o) > HALF_MAX or any(k not in prof for k in (o - 4, o - 1, o + 1, o + 4)): continue
        c = min(prof[o - 4], prof[o + 4]) - prof[o]
        if c > CONTRAST and prof[o] <= prof[o - 1] and prof[o] <= prof[o + 1]: out[o] = c
    return out, nrm
def turn(a, b, nrm, o):
    best = min(((dark(a + nrm * (o + i), b + nrm * (o + j)) or 255, i, j) for i in range(-TURN, TURN + 1) for j in range(-TURN, TURN + 1)))
    return [(a + nrm * (o + best[1])).round(1).tolist(), (b + nrm * (o + best[2])).round(1).tolist()]
lines = []
M = json.load(open(D + 'merge.json', encoding='utf8'))
for r in M['runs']: lines.append((r['name'], r['rid'], np.array(r['points'], float)))
if os.path.exists(D + 'streets_added.json'):
    for k, r in enumerate(json.load(open(D + 'streets_added.json', encoding='utf8'))): lines.append((r['name'], f'added-{k + 1}', np.array(r['points'], float)))
# pass 1: every piece's best pair of lines. pass 2: a street keeps one width: the street's half-widths are the medians
# over its paired pieces (WIDTH_TOL px), every piece is searched again within WIDTH_TOL of them, and a piece with no
# printed line there (a crossing, a gap in the print) takes the street's width, so the strip runs through.
WIDTH_TOL = 6
def cut(pts):
    out = []
    for a, b in zip(pts[:-1], pts[1:]):
        L = np.hypot(*(b - a)); n = max(1, int(round(L / PIECE)))
        out += [(a + (b - a) * k / n, a + (b - a) * (k + 1) / n) for k in range(n) if L / n >= 30]
    return out
def pair(cand):
    lf = {o: c for o, c in cand.items() if o < 0}; rt = {o: c for o, c in cand.items() if o > 0}; best = None
    for ol, cl in lf.items():
        for orr, cr in rt.items():
            sc = cl + cr - 4.0 * abs(-ol - orr)
            if abs(-ol - orr) <= 14 and (best is None or sc > best[0]): best = (sc, ol, orr)
    return best
pieces = []; widths = {}
for name, rid, pts in lines:
    pcs = cut(pts); cands = [side_lines(p, q)[0] for p, q in pcs]; n_ = max(1, len(pcs))
    # the street's two half-widths: the distances at which the most pieces have a clear line (within 3 px), the two
    # sides within 20 px of each other; a street along the plate's edge has one side only
    vote = lambda o: sum(1 for c in cands if any(abs(k - o) <= 3 for k in c))
    vl = {o: vote(-o) for o in range(HALF_MIN, HALF_MAX + 1)}; vr = {o: vote(o) for o in range(HALF_MIN, HALF_MAX + 1)}
    best = max(((vl[i] + vr[j] - 0.02 * (i + j), i, j) for i in vl for j in vr if abs(i - j) <= (34 if rid.startswith('added') else 20) and vl[i] and vr[j]), default=None)
    hl = hr = None; good = []
    if best and vl[best[1]] >= 0.3 * n_ and vr[best[2]] >= 0.3 * n_: hl, hr = float(best[1]), float(best[2]); good = [1] * min(vl[best[1]], vr[best[2]])
    else:                                             # one side only: the clearest line on either side, in at least half the pieces
        ol = max(vl, key=lambda o: (vl[o], -o)); orr = max(vr, key=lambda o: (vr[o], -o))
        if max(vl[ol], vr[orr]) >= 0.5 * n_ and n_ >= 2:
            if vl[ol] >= vr[orr]: hl = float(ol); good = [1] * vl[ol]
            else: hr = float(orr); good = [1] * vr[orr]
    widths[rid] = dict(name=name, left_px=hl, right_px=hr, pieces=len(pcs), paired=len(good))
    for p, q in pcs:
        cand, nrm = side_lines(p, q); rec = dict(name=name, rid=rid, a=p.round(1).tolist(), b=q.round(1).tolist(), left=None, right=None, printed=[False, False])
        if hl is not None or hr is not None:
            for key, sign, hw, k in (('left', -1, hl, 0), ('right', 1, hr, 1)):
                if hw is None: continue
                near = {o: c for o, c in cand.items() if o * sign > 0 and abs(abs(o) - hw) <= WIDTH_TOL}
                if near: o = max(near, key=near.get); rec[key] = turn(p, q, nrm, o); rec['printed'][k] = True
                else: rec[key] = [(p + nrm * sign * hw).round(1).tolist(), (q + nrm * sign * hw).round(1).tolist()]
        pieces.append(rec)
json.dump(widths, open(OUT + f'{N}_street_widths.json', 'w', encoding='utf8', newline=chr(10)), indent=1)
json.dump(pieces, open(OUT + f'{N}_streets.json', 'w', encoding='utf8', newline='\n'))
v = (full * 0.8 + 50).astype(np.uint8); I = lambda p: tuple(np.round(p).astype(int))
for p in pieces:
    cv2.line(v, I(p['a']), I(p['b']), (230, 90, 0) if (p['left'] or p['right']) else (0, 0, 230), 3, cv2.LINE_AA)       # centre: blue; red = street with no width found
    for s_, k in (('left', 0), ('right', 1)):
        if p[s_]: cv2.line(v, I(p[s_][0]), I(p[s_][1]), (0, 150, 0) if p['printed'][k] else (0, 160, 255), 4, cv2.LINE_AA)   # green on a printed line, orange = carried at the street's width
cv2.imwrite(OUT + f'{N}_streets_check.jpg', cv2.resize(v, None, fx=0.5, fy=0.5, interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 85])
print('streets', len(lines), 'with a width', sum(1 for w_ in widths.values() if w_['left_px'] is not None or w_['right_px'] is not None), 'pieces', len(pieces), 'sides on a printed line', sum(sum(p['printed']) for p in pieces), 'of', 2 * len(pieces))
print('no width:', [w_['name'] for w_ in widths.values() if w_['left_px'] is None and w_['right_px'] is None and w_['pieces']])
