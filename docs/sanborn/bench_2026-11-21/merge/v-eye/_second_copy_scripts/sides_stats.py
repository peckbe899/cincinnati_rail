"""merge/v-eye: bridges, holes and chords among the merged step's exported lines (21 Nov 2026).

    python -B sides_stats.py [N ...]   -> merge/v-eye/sides_stats.json

Per plate, of the lines the merged step exports (staged step 4):
  bridges   the bridging sides (outlines.py 'bridge': parallel / far / back), with their length
  holes     the street-hole sides (hole=True)
  chords    sides 250 px or longer whose own pixels are less than half on ink (Lab L < 140 within 2 px), i.e. a straight
            side cutting across a curve or open ground; listed with their ink share
On 44 each group is also scored against Ben's street map (share of length within 8 px of one of his lines).
"""
import json, os, sys
import numpy as np
import cv2
import common as C
import views as V
from lost import draw, share, L


def one(n):
    full = V.scan(n); H, W = full.shape[:2]
    ink = cv2.dilate(((cv2.cvtColor(full, cv2.COLOR_BGR2LAB)[..., 0] < 140)).astype(np.uint8), np.ones((5, 5), np.uint8))
    polys = json.load(open(V.src(n, 'merged'), encoding='utf8')); ex = V.exported('merged', polys)
    ben = draw((H, W), json.load(open(C.DATA + 'streetmap/22-44.json', encoding='utf8'))['lines']) if n == '44' else None
    rec = lambda s: dict(a=s['a'], b=s['b'], len=round(L(s)), state=s['state'], bridge=s.get('bridge'), ink=round(float(share(ink, s).mean()), 2),
                         **({'on_ben': round(float(share(ben, s).mean()), 2)} if ben is not None else {}))
    br = [rec(s) for s, h in ex if 'bridge' in s]; ho = [rec(s) for s, h in ex if h]
    ch = sorted([r for r in (rec(s) for s, h in ex if L(s) >= 250) if r['ink'] < 0.5], key=lambda r: r['ink'])
    out = dict(plate=n, exported=len(ex), exported_px=round(sum(L(s) for s, _ in ex)),
               bridges=dict(n=len(br), px=sum(r['len'] for r in br), by_why={w: sum(r['bridge'] == w for r in br) for w in ('parallel', 'far', 'back')},
                            green=sum(r['state'] == 'on print' for r in br), median_ink=float(np.median([r['ink'] for r in br])) if br else None, list=br),
               holes=dict(n=len(ho), px=sum(r['len'] for r in ho), list=ho), chords=dict(n=len(ch), px=sum(r['len'] for r in ch), list=ch))
    if ben is not None:
        for k in ('bridges', 'holes', 'chords'):
            lst = out[k]['list']; out[k]['on_ben_px'] = round(sum(r['len'] * r['on_ben'] for r in lst))
        out['all_on_ben_px'] = round(sum(L(s) * share(ben, s).mean() for s, _ in ex))
    V._full.pop(n, None)
    return out


if __name__ == '__main__':
    pl = sys.argv[1:] or C.PLATES; R = {}
    for n in pl:
        r = one(n); R[n] = r
        print(n, 'exported', r['exported'], r['exported_px'], '| bridges', r['bridges']['n'], r['bridges']['px'], r['bridges']['by_why'], 'green', r['bridges']['green'], 'median ink', r['bridges']['median_ink'],
              '| holes', r['holes']['n'], r['holes']['px'], '| chords', r['chords']['n'], r['chords']['px'],
              ('| on Ben: bridges %s holes %s chords %s all %s' % (r['bridges']['on_ben_px'], r['holes']['on_ben_px'], r['chords']['on_ben_px'], r['all_on_ben_px']) if n == '44' else ''), flush=True)
    json.dump(R, open(C.must_be_mine(C.ME + 'sides_stats.json'), 'w'), indent=1)
