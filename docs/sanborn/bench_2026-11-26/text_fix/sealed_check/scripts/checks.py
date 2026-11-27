"""Automatic truth checks on sealed_final (sealed cross-check, 26 Nov 2026). Reads only the scans, paper masks and the truth.
    cd data/sanborn
    python -B bench_2026-11-26/text_fix/sealed_check/scripts/checks.py [--truth DIR] [--out FILE.json]
Inside each crop's scope (targeted) or the whole window (full), per 8-connected ink piece:
  near_word   a glyph-sized piece (4-600 px, at most 60 px across) with no text pixel, within 8 px of a word box:
              a prime, a ditto tick or a glyph tip left outside the box? (lines, dashes and hooks also show up here)
  lone        the same, but further from every word: a missed small word or mark? (full crops and scopes)
  inbox_nt    a piece lying 90% or more inside one word box that has non-text pixels (3 or more): a glyph cut by a line,
              or a dash correctly made not text
  outbox_txt  text pixels more than 2 px outside every word box
  touch12     a text pixel 8-adjacent to a not-text pixel (the shared-ink rule should prevent it)
Per target word: low_share (less than half its box ink is text), reading (bad reading for its kind), ditto_pieces
(number of ink pieces in a ditto box), tick_near (a tick-sized non-text piece within 10 px of a ditto box).
Writes the list of suspects (with a box to look at) to --out."""
import os, sys, json, math, re, argparse
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, window, jdump

ap = argparse.ArgumentParser(); ap.add_argument('--truth', default=FINAL); ap.add_argument('--out', default=os.path.join(HERE, '..', 'checks', 'suspects.json'))
ap.add_argument('--crops'); a = ap.parse_args()
crops = json.load(open(os.path.join(a.truth, 'crops.json'), encoding='utf8'))
ids = a.crops.split(',') if a.crops else sorted(crops, key=lambda k: (crops[k]['plate'], k))
RX = {'block': r'^\d+[A-Z]?(½)?$', 'ditto': r'^"$', 'house': r'^[\d\-½ ]+[A-Z]?$', 'lot': r'^[\dA-Z½\-]+$'}
sus = []; stats = {}


def poly_mask(shape, poly, off, grow=0):
    m = np.zeros(shape, np.uint8); cv2.fillPoly(m, [np.round(np.array(poly, float) - off).astype(np.int32)], 1)
    if grow: m = cv2.dilate(m, np.ones((2 * grow + 1, 2 * grow + 1), np.uint8))
    return m > 0


for tid in ids:
    c = crops[tid]; p = c['plate']; X0, Y0, X1, Y1 = c['win']
    M = cv2.imread(os.path.join(a.truth, f'{tid}_mask.png'), 0)
    R = json.load(open(os.path.join(a.truth, f'{tid}_words.json'), encoding='utf8')); W = R['words']
    _, _, ink, _ = window(p, X0, Y0, X1, Y1)
    S = np.zeros(M.shape, bool)
    if R.get('scope'):
        for r in R['scope']: S[max(0, r[1] - Y0):max(0, r[3] - Y0 + 1), max(0, r[0] - X0):max(0, r[2] - X0 + 1)] = True
    else: S[:] = True
    off = np.array([X0, Y0])
    boxes = [poly_mask(M.shape, w['poly'], off) for w in W]
    anyb = np.zeros(M.shape, bool)
    for b in boxes: anyb |= b
    anyb2 = cv2.dilate(anyb.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    near8 = cv2.dilate(anyb.astype(np.uint8), np.ones((17, 17), np.uint8)) > 0
    n, lb, st, _ = cv2.connectedComponentsWithStats((ink & S).astype(np.uint8), connectivity=8)
    def add(chk, bx, **kw):
        sus.append(dict(crop=tid, plate=p, check=chk, box=[int(v) for v in bx], **kw))
    for i in range(1, n):
        x, y, w_, h_, area = st[i]
        sub = lb[y:y + h_, x:x + w_] == i; L = M[y:y + h_, x:x + w_][sub]
        n1, n2, n3 = int((L == 1).sum()), int((L == 2).sum()), int((L == 3).sum())
        bx = [x + X0, y + Y0, x + w_ + X0, y + h_ + Y0]
        if n2 == 0 and 4 <= area <= 600 and max(w_, h_) <= 60 and n1 > 0:
            if near8[y:y + h_, x:x + w_][sub].any(): add('near_word', bx, px=int(area), n1=n1, n3=n3)
            elif R['kind'] == 'full' or True: add('lone', bx, px=int(area), n1=n1, n3=n3)
        if n1 >= 3:
            for j, b in enumerate(boxes):
                if (b[y:y + h_, x:x + w_][sub]).sum() >= 0.9 * area:
                    add('inbox_nt', bx, px=int(area), n1=n1, n2=n2, n3=n3, word=W[j]['id'], reading=W[j]['reading'], wkind=W[j]['kind']); break
        o = (L == 2) & ~anyb2[y:y + h_, x:x + w_][sub]
        if o.sum() > 0: add('outbox_txt', bx, px=int(o.sum()), n2=n2)
    t2 = (M == 2).astype(np.uint8); t1 = (M == 1)
    adj = (cv2.dilate(t2, np.ones((3, 3), np.uint8)) > 0) & t1
    if adj.any():
        ys, xs = np.nonzero(adj); add('touch12', [xs.min() + X0, ys.min() + Y0, xs.max() + X0 + 1, ys.max() + Y0 + 1], px=int(adj.sum()))
    for j, w in enumerate(W):
        rx = RX.get(w['kind'])
        if rx and not re.match(rx, w['reading']): add('reading', w['aabb'], word=w['id'], reading=w['reading'], wkind=w['kind'])
        if not w['target']: continue
        if w['text_px_final'] < 0.5 * w['ink_px']: add('low_share', w['aabb'], word=w['id'], reading=w['reading'], ink=w['ink_px'], text=w['text_px_final'])
        if w['kind'] == 'ditto':
            b = boxes[j]; ids_in = np.unique(lb[b & ink & S]); ids_in = ids_in[ids_in > 0]
            add('ditto_pieces', w['aabb'], word=w['id'], pieces=int(len(ids_in)), sizes=[int(st[k][4]) for k in ids_in], info=True)
            g = cv2.dilate(b.astype(np.uint8), np.ones((21, 21), np.uint8)) > 0
            for k in np.unique(lb[g & ink & S]):
                if k == 0 or k in ids_in: continue
                x, y, w_, h_, area = st[k]; sub = lb[y:y + h_, x:x + w_] == k; L = M[y:y + h_, x:x + w_][sub]
                if (L == 2).sum() == 0 and area <= 80 and max(w_, h_) <= 20:
                    add('tick_near', [x + X0, y + Y0, x + w_ + X0, y + h_ + Y0], word=w['id'], px=int(area))
    stats[tid] = dict(pieces=int(n - 1))
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
jdump(dict(suspects=sus, stats=stats), a.out)
from collections import Counter
print(Counter(s['check'] for s in sus))
print('by half:', Counter((s['crop'][:2], s['check']) for s in sus if not s.get('info')))
