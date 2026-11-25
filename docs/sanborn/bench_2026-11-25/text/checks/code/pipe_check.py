"""Pipe and sewer label checks by code.

  format   the text must read as  <d>" W. PIPE | <d>" W.P. | <d>" SEWER | <f>'<i>" SEWER  with a usual diameter
  beside   the nearest pipe-kind line beside the label (either side, parallel, within REACH px of the lettering) must be of
           the label's kind: 'W. PIPE' -> ink_bins 6 (a solid line in street ground), 'SEWER' -> ink_bins 7 (thin dashes).
           The bins come from unet_data/<plate>_bins.png, which is made by rules from the line shapes, not from the labels,
           so the two are independent evidence.
  run      labels of one kind along one street should give one diameter (soft: a pipe can change size)

Tested on 16 labels read by eye (data/pipe_labels.json), on the same labels with the kind swapped, on the labels moved
150 px across the street (a label put in the wrong place), and on every one-digit confusion of the diameters.
usage: python -B pipe_check.py      (prints the tables, writes out/pipes.json)
"""
import json, os, re, collections
import numpy as np
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
HERE = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.dirname(HERE)
SB = os.path.normpath(os.path.join(BASE, '..', '..', '..')) + os.sep
REACH = 60          # px from the edge of the lettering (20 ft at 100 ft/in)
HALF_H = 14         # half the height of the lettering, px (used when the lettering cannot be found in the text bin)
INLINE = 80         # px: a line that runs on in line with the label, beyond its ends (the label sits in a gap of the line)
COV = {6: 0.5, 7: 0.25}   # share of the label's length the line must run beside it (dashes cover less)
W_PIPE = {3, 4, 6, 8, 10, 12, 16, 20, 24, 30, 36, 42, 48}          # usual cast-iron main sizes (inches); an assumption
SEWER_IN = {6, 8, 9, 10, 12, 15, 18, 20, 21, 24, 27, 30, 33, 36, 42, 48, 54, 60, 66, 72}
RX = [(re.compile(r'^(\d{1,2})["”]\s*W\.?\s*P(?:IPE|\.)?$'), 'water pipe'),
      (re.compile(r'^(\d{1,2})["”]\s*SEWER$'), 'sewer'),
      (re.compile(r"^(\d{1,2})'\s*(\d{1,2})[\"”]\s*SEWER$"), 'sewer')]
KIND_BIN = {'water pipe': 6, 'sewer': 7}
CONF = [('3', '8'), ('1', '7'), ('5', '6'), ('6', '8'), ('0', '8'), ('0', '6'), ('4', '9'), ('2', '7'), ('3', '5'), ('5', '8'), ('1', '4')]
PARTNER = collections.defaultdict(set)
for a_, b_ in CONF:
    PARTNER[a_].add(b_); PARTNER[b_].add(a_)


def parse(text):
    t = text.strip().upper()
    for rx, kind in RX:
        m = rx.match(t)
        if m:
            d = int(m.group(1)) if len(m.groups()) == 1 else int(m.group(1)) * 12 + int(m.group(2))
            plaus = d in (W_PIPE if kind == 'water pipe' else SEWER_IN) or (kind == 'sewer' and len(m.groups()) == 2)
            return dict(kind=kind, inches=d, plausible=bool(plaus))
    return None


_B = {}


def bins(plate):
    if plate not in _B:
        _B[plate] = np.array(Image.open(f'{SB}unet_data/{plate}_bins.png'))
    return _B[plate]


def refine(plate, cx, cy, ang, L):
    """centre the label on its own lettering: the text-bin (8) pixels inside the rotated box (what stage 2 would give)"""
    B = bins(plate); H, W = B.shape
    th = np.radians(ang); u = np.array([np.cos(th), -np.sin(th)]); n = np.array([np.sin(th), np.cos(th)])
    r = int(L / 2 + 40)
    x0, x1 = max(0, int(cx - r)), min(W, int(cx + r)); y0, y1 = max(0, int(cy - r)), min(H, int(cy + r))
    yy, xx = np.nonzero(B[y0:y1, x0:x1] == 8)
    if len(xx) < 30:
        return cx, cy, HALF_H
    dx = xx + x0 - cx; dy = yy + y0 - cy
    t = dx * u[0] + dy * u[1]; o = dx * n[0] + dy * n[1]
    m = (np.abs(t) <= L / 2) & (np.abs(o) <= 30)
    if m.sum() < 30:
        return cx, cy, HALF_H
    om = float(np.median(o[m])); hh = float(np.percentile(np.abs(o[m] - om), 95))
    c = np.array([cx, cy]) + om * n
    return float(c[0]), float(c[1]), max(8.0, min(20.0, hh))


def beside(plate, cx, cy, ang, L, do_refine=True):
    """nearest pipe-kind line beside the label or running on in line with it:
    (distance px from the lettering, kind bin, coverage, side, where)"""
    B = bins(plate); H, W = B.shape
    if do_refine:
        cx, cy, hh = refine(plate, cx, cy, ang, L)
    else:
        hh = HALF_H
    th = np.radians(ang)
    u = np.array([np.cos(th), -np.sin(th)]); n = np.array([np.sin(th), np.cos(th)])
    tb = np.arange(-L / 2, L / 2 + 1, 2.0)
    ti = np.r_[np.arange(-L / 2 - INLINE, -L / 2 - 4, 2.0), np.arange(L / 2 + 4, L / 2 + INLINE, 2.0)]
    best = None

    def cov(ts, o, k):
        hit = np.zeros(len(ts), bool)
        for dd in (-1, 0, 1):
            P = np.array([cx, cy]) + np.outer(ts, u) + (o + dd) * n
            x = np.clip(P[:, 0].round().astype(int), 0, W - 1); y = np.clip(P[:, 1].round().astype(int), 0, H - 1)
            hit |= B[y, x] == k
        return hit.mean()

    for o in range(0, int(hh + REACH) + 1):
        for side in ((1,) if o == 0 else (-1, 1)):
            for k in (6, 7):
                ci = cov(ti, side * o, k)
                cb = cov(tb, side * o, k) if o >= hh else 0.0
                c, where = max((cb, 'beside'), (ci, 'in line'))
                if c >= COV[k]:
                    d = max(0.0, o - hh)
                    cand = (d, k, float(c), side, where)
                    if best is None or cand[0] < best[0] or (cand[0] == best[0] and cand[2] / COV[cand[1]] > best[2] / COV[best[1]]):
                        best = cand
        if best is not None and o > best[0] + hh + 2:
            break
    return best, (cx, cy, hh)


def check(lab, text=None, shift=0.0):
    _id, plate, t0, cx, cy, ang, L, street = lab
    text = t0 if text is None else text
    th = np.radians(ang); n = np.array([np.sin(th), np.cos(th)])
    p = parse(text)
    out = dict(id=_id, text=text, shift=shift)
    out['format'] = bool(p is not None)
    out['plausible'] = bool(p is not None and p['plausible'])
    if shift:
        cx0, cy0, _ = refine(plate, cx, cy, ang, L)
        cx2, cy2 = np.array([cx0, cy0]) + shift * n
        best, box = beside(plate, cx2, cy2, ang, L, do_refine=False)
    else:
        best, box = beside(plate, cx, cy, ang, L)
    out['centre'] = [round(box[0], 1), round(box[1], 1)]
    out['nearest'] = None if best is None else dict(kind={6: 'water pipe', 7: 'sewer'}[best[1]], dist_px=round(best[0], 1), coverage=round(best[2], 2), side=best[3], where=best[4])
    if p is None:
        out['beside'] = False
    else:
        out['beside'] = bool(best is not None and best[1] == KIND_BIN[p['kind']])
    return out


def run_consistency(labels, texts):
    """labels of one kind along one street: one diameter (returns ids of labels that disagree with the street's majority)"""
    groups = collections.defaultdict(list)
    for lab, t in zip(labels, texts):
        p = parse(t)
        if p:
            groups[(lab[1], lab[7], p['kind'])].append((lab[0], p['inches']))
    bad = set()
    for g, L in groups.items():
        if len(L) < 2:
            continue
        c = collections.Counter(d for _, d in L)
        top, k = c.most_common(1)[0]
        if k > len(L) / 2:
            bad |= {i for i, d in L if d != top}
        else:
            bad |= {i for i, _ in L}
    return bad


def main():
    labs = json.load(open(os.path.join(BASE, 'data', 'pipe_labels.json')))['labels']
    rep = {}
    print('== labels as read')
    T = [check(l) for l in labs]
    for r in T:
        print(f"  {r['id']:6s} {r['text']:12s} format {r['format']!s:5} plausible {r['plausible']!s:5} beside {r['beside']!s:5} nearest {r['nearest']}")
    print(f"  pass (format and beside): {sum(r['format'] and r['beside'] for r in T)} of {len(T)}")
    rep['true'] = T
    print('\n== kind swapped (W. PIPE <-> SEWER, same place)')
    S = []
    for l in labs:
        p = parse(l[2])
        sw = l[2].upper().replace('W. PIPE', '#').replace('W.P.', '#').replace('SEWER', 'W. PIPE').replace('#', 'SEWER')
        S.append(check(l, sw))
    print(f"  caught (beside fails): {sum(not r['beside'] for r in S)} of {len(S)}")
    rep['swapped'] = S
    print('\n== label moved 150 px across (either way)')
    M = [check(l, shift=s) for l in labs for s in (-150, 150)]
    print(f"  caught: {sum(not r['beside'] for r in M)} of {len(M)}")
    for r in M:
        if r['beside']:
            print('   not caught:', r['id'], r['shift'], r['nearest'])
    rep['moved'] = M
    print('\n== one-digit confusions of the diameter (format + run consistency)')
    D = []
    for i, l in enumerate(labs):
        for j, ch in enumerate(l[2]):
            if not ch.isdigit():
                continue
            for q in sorted(PARTNER.get(ch, ())):
                t = l[2][:j] + q + l[2][j + 1:]
                texts = [x[2] for x in labs]; texts[i] = t
                p = parse(t)
                bad = run_consistency(labs, texts)
                D.append(dict(id=l[0], true=l[2], read=t, plausible=bool(p and p['plausible']), run_ok=l[0] not in bad,
                              caught=bool((not p) or (not p['plausible']) or (l[0] in bad))))
    print(f"  variants {len(D)}; implausible size {sum(not d['plausible'] for d in D)}; run disagreement {sum(not d['run_ok'] for d in D)}; caught by either {sum(d['caught'] for d in D)} ({sum(d['caught'] for d in D) / len(D):.0%})")
    for d in D:
        if not d['caught']:
            print('   not caught:', d['id'], d['true'], '->', d['read'])
    rep['diameter'] = D
    json.dump(rep, open(os.path.join(BASE, 'out', 'pipes.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
