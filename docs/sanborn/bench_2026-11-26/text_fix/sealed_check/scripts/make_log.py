"""Write sealed_final/fixes_log.txt, put the scope boxes into sealed_final/crops.json and write sealed_final/stats.json
(sealed cross-check, 26 Nov 2026).
    cd data/sanborn
    python -B bench_2026-11-26/text_fix/sealed_check/scripts/make_log.py
Pixel counts (all MEASURED): for each fix, 'own px' is the number of crop-window pixels whose class the op itself changed
(recorded by build_final.py before the shared-ink rule; for a word line it is the change of the crop as a whole, below);
for each crop, the pixels that differ between the merged truth before the fixes (sealed_check/v0_merged) and sealed_final,
by class change (0 paper, 1 not text, 2 text, 3 don't care)."""
import os, sys, json, collections
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from common import FINAL, jdump
CK = os.path.abspath(os.path.join(HERE, '..'))
crops = json.load(open(os.path.join(FINAL, 'crops.json'), encoding='utf8'))
log = json.load(open(os.path.join(CK, 'fixes_applied.json'), encoding='utf8'))
# own effect of each op, from the boxes of every crop that reads the file
eff = {}
for tid, c in crops.items():
    R = json.load(open(os.path.join(FINAL, f'{tid}_words.json'), encoding='utf8'))
    for b in R['boxes']:
        eff.setdefault((c.get('annot', tid), b['line']), {})[tid] = b.get('effect_px', 0)
def annot_lines(fn):
    return open(os.path.join(FINAL, 'annot', f'{fn}.txt'), encoding='utf8').read().split('\n')
diff = {}
for tid in crops:
    A = cv2.imread(os.path.join(CK, 'v0_merged', f'{tid}_mask.png'), 0); B = cv2.imread(os.path.join(FINAL, f'{tid}_mask.png'), 0)
    d = A != B; pairs = collections.Counter(f'{u}->{v}' for u, v in zip(A[d].tolist(), B[d].tolist()))
    if d.any(): diff[tid] = dict(total=int(d.sum()), **dict(sorted(pairs.items())))
files_to_crops = collections.defaultdict(list)
for tid, c in crops.items(): files_to_crops[c.get('annot', tid)].append(tid)
L = ['Sealed truth: fixes made by the cross-check (26 Nov 2026), in the merged copy only (sealed_final/annot).',
     'Every fix was decided on 4-8x zooms of the scan beside the truth (sealed_check/pics). Pixel counts are MEASURED.',
     "own px: crop-window pixels whose class the op itself changed (before the shared-ink rule); '-' for a word line.", '',
     'F00 (format, all half-B targeted crops): the scope box now includes its last row and column, as in half A (half B left',
     '    them out). 14,833 px of 44 half-B crops moved from don\'t care (3) to labelled: 0 paper or 1/2 ink (sealed_check/build_v0.log,',
     '    compare.py tmp/repro vs v0_merged). This is a format unification, not a truth fix.', '']
for e in log:
    fn = e['file']; lines = annot_lines(fn)
    k = next((i + 1 for i, x in enumerate(lines) if x.strip() == e['new']), None)
    own = eff.get((fn, k), {}) if k else {}
    ownt = ', '.join(f'{t} {v}' for t, v in own.items() if v) or ('-' if '|' in e['new'] else '0')
    L.append(f"{e['fix']} {fn}: {e['new']}")
    if e['old']: L.append(f"    replaces: {e['old']}")
    L.append(f"    why: {e['why']}")
    L.append(f"    own px: {ownt}")
L += ['', 'Per crop, pixels that differ from the merged truth before the fixes (sealed_check/v0_merged -> sealed_final):']
tot = collections.Counter()
for tid, d in sorted(diff.items(), key=lambda kv: -kv[1]['total']):
    L.append(f"  {tid:7s} {d['total']:6d} px   " + '  '.join(f'{k} {v}' for k, v in d.items() if k != 'total'))
    for k, v in d.items(): tot[k] += v
L.append(f"  ALL     {tot['total']:6d} px   " + '  '.join(f'{k} {v}' for k, v in sorted(tot.items()) if k != 'total'))
open(os.path.join(FINAL, 'fixes_log.txt'), 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n')
# scope boxes into crops.json
for tid, c in crops.items():
    if c.get('kind') == 'targeted':
        R = json.load(open(os.path.join(FINAL, f'{tid}_words.json'), encoding='utf8'))
        c['scope'] = R['scope']; c['scope_note'] = 'scope boxes [x0, y0, x1, y1], full-plate px, both ends included'
jdump(crops, os.path.join(FINAL, 'crops.json'))
# stats
S = dict(crops=collections.Counter(), targets={}, words_by_kind=collections.Counter(), pixels={})
for tid, c in crops.items():
    S['crops'][f"{c.get('target') or 'full'}_{c['half']}"] += 1
    R = json.load(open(os.path.join(FINAL, f'{tid}_words.json'), encoding='utf8')); M = cv2.imread(os.path.join(FINAL, f'{tid}_mask.png'), 0)
    sc = np.zeros(M.shape, bool)
    if R.get('scope'):
        X0, Y0 = c['win'][:2]
        for r in R['scope']: sc[max(0, r[1] - Y0):max(0, r[3] - Y0 + 1), max(0, r[0] - X0):max(0, r[2] - X0 + 1)] = True
    else: sc[:] = True
    p = S['pixels'].setdefault(c['kind'], dict(text=0, not_text=0, dont_care_in_scope=0, paper_in_scope=0))
    p['text'] += int((M == 2).sum()); p['not_text'] += int((M == 1).sum()); p['dont_care_in_scope'] += int(((M == 3) & sc).sum()); p['paper_in_scope'] += int(((M == 0) & sc).sum())
    for w in R['words']:
        S['words_by_kind'][w['kind']] += 1
        if w['target']:
            t = S['targets'].setdefault(f"{w['kind']}_{c['scale_ft_per_inch']}", dict(words=0, ink_px=[], unsure=0))
            t['words'] += 1; t['ink_px'].append(w['ink_px']); t['unsure'] += int('unsure' in w['flags'])
for k, t in S['targets'].items():
    v = sorted(t['ink_px']); t['ink_px_median'] = v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2; t['ink_px_min'] = v[0]; t['ink_px_max'] = v[-1]; del t['ink_px']
jdump(dict(S, crops=dict(S['crops']), words_by_kind=dict(S['words_by_kind'])), os.path.join(FINAL, 'stats.json'))
print('log', len(log), 'fixes; crops changed', len(diff), 'px', tot['total'])
