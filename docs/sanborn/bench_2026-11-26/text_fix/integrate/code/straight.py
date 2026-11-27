"""CHECK ONLY (integrate, 26 Nov 2026): the 200 ft line concern, the skeptic's stand-in for Ben's line ink
(text_v1/skeptic/scripts/sk_score.py lineish; the same rule as fix_ditto/code/check_straight.py, from which this is
copied and made to take several masks): truth-1 ink lying on a straight run of 61 px or more (opening with 61 px lines
every 7.5 deg) called text, on the dev windows (dev ditto truth and dev block truth, their scopes only; ink outside a
scope is 3, don't care), pooled by scale and by fold (each truth set's own folds, as score_all.py).

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/integrate/code/straight.py OUT.json NAME=PATTERN[:CODES] ... [--sets ditto,block]
"""
import os, sys, json
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from score_all import SETS, fold, ft_of, SEALED  # noqa: E402


def straight_of(t1):
    u = t1.astype(np.uint8); s = np.zeros(t1.shape, bool); L = 61
    for ang in np.arange(0, 180, 7.5):
        k = np.zeros((L, L), np.uint8); c = L // 2; d = np.array([np.cos(np.radians(ang)), np.sin(np.radians(ang))])
        p0 = np.round(c - d * c).astype(int); p1 = np.round(c + d * c).astype(int); cv2.line(k, tuple(p0.tolist()), tuple(p1.tolist()), 1, 1)
        s |= cv2.morphologyEx(u, cv2.MORPH_OPEN, k) > 0
    return s


args = sys.argv[1:]; SETS_USED = ('ditto', 'block')
if '--sets' in args: i = args.index('--sets'); SETS_USED = tuple(args[i + 1].split(',')); args = args[:i] + args[i + 2:]
outp = args[0]; meths = {}
for a in args[1:]:
    n, v = a.split('=', 1)
    if ':' in v and v.rsplit(':', 1)[1].replace(',', '').isdigit(): pat, codes = v.rsplit(':', 1)
    else: pat, codes = v, '2,3'
    meths[n] = (pat, [int(c) for c in codes.split(',')])
R = {}; cache = {}
def code(p):
    if p not in cache:
        if len(cache) > 6: cache.clear()
        cache[p] = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    return cache[p]
for nm in SETS_USED:
    tdir = SETS[nm]; crops = json.load(open(os.path.join(tdir, 'crops.json')))
    for k, c in sorted(crops.items(), key=lambda kv: kv[1]['plate']):
        mp = os.path.join(tdir, f'{k}_mask.png')
        if not os.path.exists(mp) or c['plate'] in SEALED: continue
        t = cv2.imread(mp, 0); x0, y0, x1, y1 = c['win']; st = straight_of(t == 1)
        r = dict(set=nm, plate=c['plate'], ft=ft_of(c), fold=fold(nm, c['plate']), straight_px=int(st.sum()))
        for n, (pat, tc) in meths.items():
            a = np.isin(code(pat.replace('{plate}', c['plate']))[y0:y1, x0:x1], tc); r[n] = int((st & a).sum())
        R[f'{nm}:{k}'] = r
out = {}
for ft in (100, 200, 400):
    for st_ in (None, 'ditto', 'block'):
        for fo in (None, 'A', 'B'):
            v = [r for r in R.values() if r['ft'] == ft and (st_ is None or r['set'] == st_) and (fo is None or r['fold'] == fo)]
            if not v: continue
            s = sum(r['straight_px'] for r in v); key = f'{ft}ft' + (f'_{st_}' if st_ else '') + (f'_fold{fo}' if fo else '')
            out[key] = dict(windows=len(v), straight_px=s, **{n: sum(r[n] for r in v) for n in meths})
            print(key, out[key], flush=True)
spots = {n: sorted([(r[n], k) for k, r in R.items() if r[n]], reverse=True)[:12] for n in meths}
print('windows with straight-run ink called text:', json.dumps(spots), flush=True)
json.dump(dict(methods={n: [p, c] for n, (p, c) in meths.items()}, pooled=out, by_window=R, spots=spots), open(outp, 'w', encoding='utf8', newline='\n'), indent=1)
