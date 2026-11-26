"""summary.py - measured counts behind the truth-check report: per crop, the delivered and fixed pixel classes, what the
fixes moved, and how many fix lines touched each crop. Writes truth-check/scores/summary.json."""
import os, sys, json, re
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tc
out = {}
ops = {}
for line in open(os.path.join(tc.KEY, 'fixes.txt'), encoding='utf8'):
    if line.strip() and not line.startswith('#'):
        f = line.split(); ops.setdefault(f[1], []).append(f[0])
for c in ['H1', 'H2', 'H3', 'H4', 'T1', 'T2', 'T3', 'T4', 'T6', 'T7']:
    o = tc.truth(c); n = tc.truth(c, True)
    mv = {f'{a}->{b}': int(((o == a) & (n == b)).sum()) for a in range(4) for b in range(4) if a != b and ((o == a) & (n == b)).any()}
    scored_wrong = sum(v for k, v in mv.items() if k in ('1->2', '2->1'))
    out[c] = dict(words=len(tc.words(c, True)['words']), text_px_before=int((o == 2).sum()), text_px_after=int((n == 2).sum()),
                  nontext_px_after=int((n == 1).sum()), dontcare_px_before=int((o == 3).sum()), dontcare_px_after=int((n == 3).sum()),
                  moved=mv, moved_total=int((o != n).sum()), text_nontext_swaps=scored_wrong,
                  swaps_share_of_text_after=round(scored_wrong / max(1, int((n == 2).sum())), 5),
                  fix_lines={k: ops.get(c, []).count(k) for k in sorted(set(ops.get(c, [])))})
json.dump(out, open(os.path.join(tc.KEY, 'scores', 'summary.json'), 'w'), indent=1)
for c, d in out.items(): print(c, d)
