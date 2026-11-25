"""Score the shape readers on three block faces of house numbers and two street names of plate 44 (25 Nov 2026).

    python -B bench_2026-11-25/text/shapes/scripts/eval_faces.py [--model model.npz] [--gdir glyphs] [--tag T]
    (from data/sanborn; --gdir: the glyph folder to read, e.g. glyphs_weak165; --tag names eval_faces_T.json)

TRUTH was read by Claude by eye from the scan (faces at 1.6x: look/face_*.png; streets: look/44_crop_knowlton.jpg,
look/44_crop_bluerock.jpg), not by Ben.
A face is a straight line through the centres of its house numbers; the words of extract_glyphs.py whose centre is
within BAND px of the line (and within its ends +-60 px) are read and put in order along it. Readers compared:
  knn_rej      classify.py's k-NN on Claude's cluster labels, all classes, touching figures cut (read.py), and a
               glyph further than 0.5 from every training glyph is '?' (counted wrong)
  knn_ctx      the same with no '?', and only digit (+ junk) training glyphs on a face, only letter (+ junk) ones on
               a street name
  knn_nosplit  knn_ctx without cutting touching figures
  font         1-NN against the font templates of fonts.py (all 47 fonts pooled), digit templates only on a face,
               letter templates only on a street name, touching figures cut the same way
  hybrid       the k-NN (all classes) says whether a glyph is junk; if not, the font templates say which character
Scores: characters by edit-distance alignment of the reading (digits/letters and '?') against the truth; a house
number counts as right when all its figures are matched and nothing extra was read inside it.
Writes eval_faces.json and look/eval_*.jpg.
"""
import json, os, sys
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from read import Reader, read_window, HERE  # noqa: E402
from fonts import shape_feats, match  # noqa: E402
from extract_glyphs import norm_glyph  # noqa: E402

BAND = 20
FACES = {   # name: (plate, (x0, y0), (x1, y1), truth with '-' and ' ' between numbers)
    'A Knowlton north side': ('44', (5642, 1944), (6211, 1888), '1424-22-20 1418 1416 1414 1412 1410 1408'),
    'B Blue Rock south side': ('44', (994, 3611), (1550, 3645), '1629 1625-23 1621 1613'),
    'C top row west of Hamilton': ('44', (1975, 214), (2600, 217), '1563-61 1559 1557 1555-53 1551 1549-47'),
}
STREETS = {   # name: (plate, box, truth)
    'KNOWLTON': ('44', (5720, 1975, 6140, 2045), 'KNOWLTON'),
    'BLUE ROCK': ('44', (955, 3500, 1410, 3575), 'BLUEROCK'),
}


class Restricted:
    """the k-NN reader with only some classes' training glyphs"""
    def __init__(self, R, allowed):
        self.__dict__.update(R.__dict__)
        keep = np.isin(R.classes[R.ytr], list(allowed))
        self.Ztr = R.Ztr[keep]; old = R.ytr[keep]
        self.classes = np.array([c for c in R.classes if c in allowed]); m = {c: i for i, c in enumerate(self.classes)}
        self.ytr = np.array([m[R.classes[i]] for i in old])
    read = Reader.read


class Hybrid:
    def __init__(self, R, allowed):
        self.R = R; self.F = FontReader(allowed)

    def read(self, bitmaps):
        a = self.R.read(bitmaps); b = self.F.read(bitmaps)
        return [x if x[0] == 'junk' else y for x, y in zip(a, b)]


class FontReader:
    def __init__(self, allowed):
        F = np.load(os.path.join(HERE, 'font_templates.npz'))
        keep = np.isin(F['label'], list(allowed))
        self.T = shape_feats(F['T'][keep]); self.lab = F['label'][keep]; self.asp = F['asp'][keep]

    def read(self, bitmaps):
        if not bitmaps: return []
        imgs = np.stack([norm_glyph(t) for t in bitmaps]); a = np.array([np.log(t.shape[1] / t.shape[0]) for t in bitmaps])
        b, d = match(shape_feats(imgs), a, self.T, self.asp)
        return [(str(self.lab[i]), float(x)) for i, x in zip(b, d)]


def align(truth, pred):
    """Levenshtein alignment; returns list of ops (t_index or None, p_index or None)"""
    n, m = len(truth), len(pred); D = np.zeros((n + 1, m + 1), int); D[:, 0] = range(n + 1); D[0, :] = range(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = min(D[i - 1, j] + 1, D[i, j - 1] + 1, D[i - 1, j - 1] + (truth[i - 1] != pred[j - 1]))
    i, j, ops = n, m, []
    while i or j:
        if i and j and D[i, j] == D[i - 1, j - 1] + (truth[i - 1] != pred[j - 1]): ops.append((i - 1, j - 1)); i -= 1; j -= 1
        elif i and D[i, j] == D[i - 1, j] + 1: ops.append((i - 1, None)); i -= 1
        else: ops.append((None, j - 1)); j -= 1
    return ops[::-1]


def score(truth_full, pred_text, keep):
    t = [c for c in truth_full if c in keep]; tnum = []; k = -1; prev = ' '
    for c in truth_full:
        if c in keep:
            if prev not in keep: k += 1
            tnum.append(k)
        prev = c
    p = [c for c in pred_text if c in keep or c == '?']
    ops = align(t, p); ok = sub = dele = ins = 0; bad = set(); last_t = None
    for ti, pj in ops:
        if ti is not None and pj is not None:
            if t[ti] == p[pj]: ok += 1
            else: sub += 1; bad.add(tnum[ti])
            last_t = ti
        elif ti is not None: dele += 1; bad.add(tnum[ti]); last_t = ti
        else:
            ins += 1
            if last_t is not None: bad.add(tnum[last_t])
    nn = max(tnum) + 1 if tnum else 0
    return dict(truth=''.join(t), read=''.join(p), n=len(t), right=ok, wrong=sub, missed=dele, extra=ins, numbers=nn, numbers_right=nn - len(bad))


def face_words(N, a, b, R, split=True, rej=None, gdir='glyphs'):
    a, b = np.array(a, float), np.array(b, float); u = (b - a) / np.linalg.norm(b - a); L = np.linalg.norm(b - a)
    box = (min(a[0], b[0]) - 80, min(a[1], b[1]) - 80, max(a[0], b[0]) + 80, max(a[1], b[1]) + 80)
    D, W = read_window(N, box, R, split=split, rej=rej if rej is not None else 1e9, gdir=gdir)
    sel = []
    for w in W:
        v = np.array([w['x'], w['y']]) - a; along = v @ u; across = abs(v[0] * -u[1] + v[1] * u[0])
        if across <= BAND and -60 <= along <= L + 60: sel.append((along, w))
    sel.sort(key=lambda x: x[0])
    return D, [w for _, w in sel]


def main():
    mf = sys.argv[sys.argv.index('--model') + 1] if '--model' in sys.argv else os.path.join(HERE, 'model.npz')
    R = Reader(mf); DIG = set('0123456789'); LET = set('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    gdir = sys.argv[sys.argv.index('--gdir') + 1] if '--gdir' in sys.argv else 'glyphs'; tag = sys.argv[sys.argv.index('--tag') + 1] if '--tag' in sys.argv else ''
    readers = {'knn_rej': (lambda allowed: R, True, 0.5), 'knn_ctx': (lambda allowed: Restricted(R, allowed | {'junk'}), True, None),
               'knn_nosplit': (lambda allowed: Restricted(R, allowed | {'junk'}), False, None), 'font': (lambda allowed: FontReader(allowed), True, None),
               'hybrid': (lambda allowed: Hybrid(R, allowed), True, None)}
    print('model', mf, '| glyphs', gdir)
    out = {}; tot = {}
    for rn, (mk, split, rej) in readers.items():
        Rd = mk(DIG)
        for fname, (N, a, b, truth) in FACES.items():
            D, W = face_words(N, a, b, Rd, split, rej, gdir)
            text = ' '.join(w['text'] for w in W)
            s = score(truth, text, DIG); s['words'] = [w['text'] for w in W]; out.setdefault(rn, {})[fname] = s
            s['glyphs'] = [[int(k), ch] for w in W for k, ch, _ in w['glyphs']]   # in reading order, for face_check.py
            for k in ('n', 'right', 'wrong', 'missed', 'extra', 'numbers', 'numbers_right'): tot.setdefault(rn, {}).setdefault(k, 0); tot[rn][k] += s[k]
            if rn in ('knn_ctx', 'font'):
                im = cv2.imread(f'cufp/22-{N}.jpg'); x0 = int(min(a[0], b[0]) - 80); y0 = int(min(a[1], b[1]) - 60); x1 = int(max(a[0], b[0]) + 80); y1 = int(max(a[1], b[1]) + 60)
                c = (im[y0:y1, x0:x1] * 0.55 + 255 * 0.45).astype(np.uint8)
                for w in W:
                    k0 = w['glyphs'][0][0]; bx, by = D['bbox'][k0][:2]
                    cv2.putText(c, w['text'].replace('_', '').replace('.', ''), (int(bx - x0), int(by - y0 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 0, 0), 2)
                cv2.imwrite(os.path.join(HERE, 'look', f'eval{tag}_{rn}_{fname.split()[0]}.jpg'), c)
        Rl = mk(LET)
        for sname, (N, box, truth) in STREETS.items():
            D, W = read_window(N, box, Rl, split=False, rej=rej if rej is not None else 1e9, gdir=gdir)
            W = sorted([w for w in W if any(ch not in '._' for ch in w['text'])], key=lambda w: w['x'])
            text = ''.join(w['text'] for w in W)
            s = score(truth, text, LET); s['words'] = [w['text'] for w in W]; out[rn][sname] = s
            for k in ('n', 'right', 'wrong', 'missed', 'extra'): tot.setdefault(rn + ' streets', {}).setdefault(k, 0); tot[rn + ' streets'][k] += s[k]
    for rn in readers:
        print(f'== {rn}')
        for name, s in out[rn].items():
            print(f"  {name:28s} truth {s['truth']:34s} read {s['read']:40s} right {s['right']}/{s['n']}  wrong {s['wrong']} missed {s['missed']} extra {s['extra']}"
                  + (f"  numbers right {s['numbers_right']}/{s['numbers']}" if name in FACES else ''))
        t = tot[rn]; ts = tot[rn + ' streets']
        print(f"  FACES: figures right {t['right']}/{t['n']} ({100 * t['right'] / t['n']:.0f}%), wrong {t['wrong']}, missed {t['missed']}, extra {t['extra']}; "
              f"numbers right {t['numbers_right']}/{t['numbers']} | STREETS: letters right {ts['right']}/{ts['n']}, wrong {ts['wrong']}, missed {ts['missed']}, extra {ts['extra']}")
    json.dump(dict(note=__doc__, model=mf, glyphs=gdir, per=out, totals=tot), open(os.path.join(HERE, f'eval_faces{tag}.json'), 'w'), indent=1, default=str)


if __name__ == '__main__':
    main()
