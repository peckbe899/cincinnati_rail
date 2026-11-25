"""verify (25 Nov 2026): the shapes agent's digit reader on a bigger, independent test: every number the INVENTORY agent read
by eye in truth crops T1-T3 (plate 44), i.e. readings made by another agent, on boxes the shapes agent never used.
Plate 44 is held out of model_no44.npz (53,244 training glyphs from 1A, 5, 3, 90, 94; checked: model.npz has 68,118
of which 14,874 are from 44).

    cd data/sanborn; python -B bench_2026-11-25/text/verify/scripts/read_truth44.py [--model model_no44.npz] [--reader knn_ctx|font]

Words used: kinds house, lot, lotdim, story; not flagged unsure, partial or run; with at least one digit. The shapes
agent's own code does the reading (imported read-only from text/shapes/scripts: read_window, Restricted, FontReader,
score). Extracted words (extract_glyphs.py's word grouping) whose centre lies in the truth word's box (grown 6 px) are
read and put in order along the truth reading direction. Scored on the digits only (primes, points, hyphens left out):
figures right by edit-distance alignment; a number is right when every figure is right and nothing extra is read.
Writes verify/out/read_truth44_<reader>.json."""
import json, os, sys
import numpy as np, cv2
SP = os.getcwd(); T = os.path.join(SP, 'bench_2026-11-25', 'text'); V = os.path.join(T, 'verify')
sys.path.insert(0, os.path.join(T, 'shapes', 'scripts'))
from read import Reader, read_window  # noqa
import eval_faces as EF  # noqa
mf = sys.argv[sys.argv.index('--model') + 1] if '--model' in sys.argv else 'model_no44.npz'
rn = sys.argv[sys.argv.index('--reader') + 1] if '--reader' in sys.argv else 'knn_ctx'
R = Reader(os.path.join(T, 'shapes', mf)); DIG = set('0123456789')
Rd = EF.Restricted(R, DIG | {'junk'}) if rn == 'knn_ctx' else EF.FontReader(DIG)
crops = json.load(open(os.path.join(T, 'inventory', 'truth', 'crops.json')))
D = np.load(os.path.join(T, 'shapes', 'glyphs', '44.npz')); cen = D['cen']
res = []; tot = {}
for tid in ('T1', 'T2', 'T3'):
    W = json.load(open(os.path.join(T, 'inventory', 'truth', f'{tid}_words.json'), encoding='utf8'))['words']
    for w in W:
        fl = w.get('flags') or []
        if w['kind'] not in ('house', 'lot', 'lotdim', 'story') or any(f in fl for f in ('unsure', 'partial', 'run')): continue
        truth = ''.join(c for c in w['reading'] if c in DIG)
        if not truth or not w.get('poly'): continue
        P = np.array(w['poly'], float); c0 = P.mean(0); Pg = c0 + (P - c0) * 1.0
        # grow the box by 6 px
        u = P - c0; Pg = P + 6 * u / np.maximum(np.linalg.norm(u, axis=1, keepdims=True), 1)
        x0, y0 = Pg.min(0) - 2; x1, y1 = Pg.max(0) + 2
        _, ws = read_window('44', (x0, y0, x1, y1), Rd, split=True, rej=1e9, D=D)
        ang = np.deg2rad(w.get('angle', 0.0)); dvec = np.array([np.cos(ang), np.sin(ang)])
        sel = [x for x in ws if cv2.pointPolygonTest(Pg.astype(np.float32), (x['x'], x['y']), False) >= 0]
        sel.sort(key=lambda x: np.array([x['x'], x['y']]) @ dvec)
        text = ''.join(x['text'] for x in sel)
        s = EF.score(truth, text, DIG); s.update(tid=tid, kind=w['kind'], reading=w['reading'], read_raw=text, touches_line=bool(w.get('touches_line')))
        s['exact'] = int(s['numbers_right'] == s['numbers'] and s['numbers'] == 1)
        res.append(s)
        k = tot.setdefault(w['kind'], dict(words=0, figs=0, right=0, wrong=0, missed=0, extra=0, exact=0))
        k['words'] += 1; k['figs'] += s['n']; k['right'] += s['right']; k['wrong'] += s['wrong']; k['missed'] += s['missed']; k['extra'] += s['extra']; k['exact'] += s['exact']
allk = {f: sum(v[f] for v in tot.values()) for f in ('words', 'figs', 'right', 'wrong', 'missed', 'extra', 'exact')}; tot['ALL'] = allk
for k, v in tot.items():
    print(f"{k:7s} words {v['words']:4d} exact {v['exact']:4d} ({100 * v['exact'] / max(1, v['words']):.0f}%) | figures right {v['right']}/{v['figs']} ({100 * v['right'] / max(1, v['figs']):.0f}%) wrong {v['wrong']} missed {v['missed']} extra {v['extra']}")
# by touching a line
for tl in (False, True):
    r = [x for x in res if x['touches_line'] == tl]
    print('touches_line', tl, 'words', len(r), 'exact', sum(x['exact'] for x in r), f"({100 * sum(x['exact'] for x in r) / max(1, len(r)):.0f}%)")
json.dump(dict(model=mf, reader=rn, totals=tot, words=res), open(os.path.join(V, 'out', f'read_truth44_{rn}_{mf[:-4]}.json'), 'w'), indent=1)
