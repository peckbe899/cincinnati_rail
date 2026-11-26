"""What changed from truth v1 (text/inventory/truth) to truth v2 (text_v1/truth), 25 Nov 2026.

    cd data/sanborn
    python -B bench_2026-11-25/text_v1/truth-fix/scripts/changes.py

1. Pixels: for each crop, how many ink pixels moved between the classes 1 (not text), 2 (text) and 3 (don't care).
   Also the same for 'v1 + shared-ink rule only' (truth-fix/rebuild_share), to split the rule from the hand fixes.
2. Annotations: every line of annot/T#.txt that v2 removed, changed or added (difflib), with its v2 note.
Writes truth-fix/changes_v2.json and truth-fix/changes_v2_list.txt (the list that README.md quotes)."""
import difflib, json, os, sys
sys.dont_write_bytecode = True
import numpy as np, cv2
HERE = os.path.dirname(os.path.abspath(__file__)); FIX = os.path.normpath(os.path.join(HERE, '..'))
V1 = os.path.normpath(os.path.join(FIX, '..', '..', 'text', 'inventory', 'truth')); V2 = os.path.normpath(os.path.join(FIX, '..', 'truth'))
SH = os.path.join(FIX, 'rebuild_share')
NAME = {0: 'paper', 1: 'not text', 2: 'text', 3: "don't care"}
out = {'pixels': {}, 'pixels_share_rule_only': {}, 'annot': {}}
lines = []
for tid in ('T1', 'T2', 'T3', 'T4', 'T6', 'T7'):
    a = cv2.imread(os.path.join(V1, f'{tid}_mask.png'), 0); b = cv2.imread(os.path.join(V2, f'{tid}_mask.png'), 0)
    s = cv2.imread(os.path.join(SH, f'{tid}_mask.png'), 0)
    for key, m in (('pixels', b), ('pixels_share_rule_only', s)):
        t = {}
        for i in (1, 2, 3):
            for j in (1, 2, 3):
                if i != j:
                    n = int(((a == i) & (m == j)).sum())
                    if n: t[f'{NAME[i]} -> {NAME[j]}'] = n
        t['v1 counts'] = {NAME[v]: int((a == v).sum()) for v in (1, 2, 3)}; t['v2 counts'] = {NAME[v]: int((m == v).sum()) for v in (1, 2, 3)}
        out[key][tid] = t
    A = open(os.path.join(V1, 'annot', f'{tid}.txt'), encoding='utf8').read().splitlines()
    B = open(os.path.join(V2, 'annot', f'{tid}.txt'), encoding='utf8').read().splitlines()
    ch = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if op == 'equal': continue
        old = [x for x in A[i1:i2]]; new = [x for x in B[j1:j2]]
        ch.append(dict(op=op, v1_lines=[i1 + 1, i2], old=old, new=new))
    out['annot'][tid] = ch
    lines.append(f'## {tid}')
    OPS = ('NOTTEXT', 'FORCE', 'FORCELINE', 'EXCL', 'EXCLCIRC', 'CARE', 'CARELINE', 'CAREDIR')
    for c in ch:
        new = c['new']; old = [x for x in c['old'] if x.strip() and not x.startswith('#')]
        used = set()
        for k, x in enumerate(new):
            if not x.strip() or x.startswith('#'): continue
            if x.split()[0] in OPS:
                f = x.split(' v2: ', 1); lines.append(f'- {f[1] if len(f) > 1 else x}  [{f[0].strip()}]'); continue
            note = new[k - 1][len('# v2: '):].strip() if k and new[k - 1].startswith('# v2: ') else ''
            rd = x.split('|')[1].strip(); kind = x.split('|')[2].strip()
            # the v1 line it replaces: same place in the hunk (a word whose box or reading changed)
            cand = [y for y in old if '|' in y and y not in used and y.split('|')[2].strip() == kind]
            xy = lambda q: np.array([float(v) for v in q.split('|')[0].split()[:2]])
            o = min(cand, key=lambda y: float(np.abs(xy(y) - xy(x)).sum())) if cand else None
            if o is not None and float(np.abs(xy(o) - xy(x)).sum()) > 80: o = None
            if o: used.add(o); lines.append(f'- word {rd!r} ({kind}): {note or "changed"}  [v1: {o.strip()}] [v2: {x.strip()}]')
            else: lines.append(f'- word {rd!r} ({kind}): added, a missed word that v1 left as non-text  [v2: {x.strip()}]')
        for y in old:
            if y in used: continue
            k = next((i for i, n in enumerate(new) if n.strip() == '# ' + y.strip()), None)   # the line kept as a comment
            while k is not None and k > 0 and not new[k - 1].startswith('# v2: '): k -= 1
            nx = new[k - 1][len('# v2: '):] if k else next((n[len('# v2: '):] for n in new if n.startswith('# v2: ')), '')
            lines.append(f'- removed: {y.strip()}' + (f'  ({nx.strip()})' if nx else ''))
json.dump(out, open(os.path.join(FIX, 'changes_v2.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
open(os.path.join(FIX, 'changes_v2_list.txt'), 'w', encoding='utf8', newline='\n').write('\n'.join(lines) + '\n')
for tid, t in out['pixels'].items(): print(tid, {k: v for k, v in t.items() if 'counts' not in k})
print(sum(len([l for l in lines if l.startswith('- ')]) for _ in [0]), 'listed changes')
