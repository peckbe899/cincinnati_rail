"""Score a mask folder on the dev block truth (two folds), the dev ditto truth (if built) and T1-T7, with
text_v1/code/score_text.py (unchanged, run as a script), plus the 200 ft straight-run check on the dev windows.
    python -B .../scripts/score_all.py MASK_DIR OUT.json [--label NAME]
MASK_DIR holds N_text.png (hand-off codes; text = 2, 3) for every plate needed."""
import sys, os, json, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code'))
import numpy as np, cv2
import bfcommon as C

md, outp = sys.argv[1], sys.argv[2]; QUICK = '--quick' in sys.argv
SC = os.path.join(C.TV1, 'code', 'score_text.py'); TMP = os.path.join(C.ROOT, 'tmp', 'sc')
os.makedirs(TMP, exist_ok=True)
crops = C.dev_crops()
FA = [k for k, v in sorted(crops.items()) if v['plate'] in C.FOLD['A']]; FB = [k for k, v in sorted(crops.items()) if v['plate'] in C.FOLD['B']]


def run(truth, ids, tag):
    o = os.path.join(TMP, f'{tag}.json')
    cmd = [sys.executable, '-B', SC, os.path.join(md, '{plate}_text.png'), '--codes', '2,3', '--truth', truth, '--out', o, '--quiet']
    if ids: cmd += ['--crops', ','.join(ids)]
    subprocess.run(cmd, check=True, capture_output=True, cwd=C.DS)
    return json.load(open(o))


def blockwords(res, kind='block', targets_only=True):
    """block recall px and words over the crops' target words (or every word of the kind)"""
    tp = n = wf = nw = 0; per = {}
    for tid, r in res['crops'].items():
        pass
    return None


R = {}
def summarise(res, kinds=('block',)):
    a = res['pools']['ALL']; o = dict(P=a['pix']['precision'], R=a['pix']['recall'], F1=a['pix']['f1'], nontext_called_text=a['nontext_called_text']['share'])
    for k in kinds:
        if k in a['by_kind']: v = a['by_kind'][k]; o[k] = dict(recall=v['recall'], words=f"{v['words_found']}/{v['words']}")
    return o


# dev block truth: target words only (score_text's 'block' kind also holds any other block word in a scope; the targets are
# the only block words there, checked below)
for tag, ids in (('blockA', FA), ('blockB', FB)):
    res = run(os.path.join(C.DEVB, 'truth'), ids, tag)
    s = summarise(res, ('block', 'street', 'lot', 'house', 'lotdim', 'ditto', 'story', 'owner'))
    s['per_crop'] = {t: res['crops'][t]['by_kind'].get('block', {}).get('recall') for t in ids}
    R[tag] = s
# T1-T7 (truth v2)
res = None if QUICK else run(os.path.join(C.TV1, 'truth'), None, 't17')
R['t17'] = {} if QUICK else summarise(res, ('block', 'street', 'ditto', 'house', 'lot', 'story', 'owner', 'railroad lettering', 'adjoining sheet'))
if not QUICK: R['t17']['per_crop_F1'] = {t: res['crops'][t]['pix']['f1'] for t in res['crops']}
# dev ditto truth, if there
DD = os.path.join(C.DS, 'bench_2026-11-26', 'text_fix', 'dev_ditto', 'truth')
if not QUICK and os.path.exists(os.path.join(DD, 'crops.json')):
    dc = json.load(open(os.path.join(DD, 'crops.json'))); ids = [k for k in sorted(dc) if os.path.exists(os.path.join(DD, f'{k}_mask.png')) and os.path.exists(os.path.join(md, f"{dc[k]['plate']}_text.png"))]
    if ids:
        res = run(DD, ids, 'ditto'); R['ditto'] = summarise(res, ('ditto', 'block')); R['ditto']['crops'] = len(ids)


# 200 ft concern: on the dev 200 ft windows, non-text truth ink on straight runs >= 61 px called text (skeptic's lineish)
lineish = C.lineish


st = dict(px=0, called=0, by_scale={}); cache = {}
for tid, c in sorted(crops.items()):
    T = cv2.imread(os.path.join(C.DEVB, 'truth', f'{tid}_mask.png'), 0); x0, y0, x1, y1 = c['win']
    N = c['plate']
    if N not in cache: cache.clear(); cache[N] = cv2.imread(os.path.join(md, f'{N}_text.png'), 0)
    m = np.isin(cache[N][y0:y1, x0:x1], (2, 3)); s_ = lineish(T == 1)
    sc = str(c['scale_ft_per_inch']); b = st['by_scale'].setdefault(sc, dict(px=0, called=0))
    b['px'] += int(s_.sum()); b['called'] += int((s_ & m).sum()); st['px'] += int(s_.sum()); st['called'] += int((s_ & m).sum())
for b in [st] + list(st['by_scale'].values()): b['share'] = round(b['called'] / max(1, b['px']), 5)
R['straight_runs_dev'] = st
json.dump(R, open(outp, 'w'), indent=1)
for k in ('blockA', 'blockB'):
    print(k, {q: R[k][q] for q in ('block', 'F1', 'nontext_called_text')})
print('t17', {q: R['t17'].get(q) for q in ('F1', 'nontext_called_text', 'block', 'street', 'ditto')})
if 'ditto' in R: print('ditto', R['ditto'])
print('straight runs (dev windows)', st)
