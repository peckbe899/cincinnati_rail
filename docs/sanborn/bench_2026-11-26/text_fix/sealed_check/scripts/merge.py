"""Merge the two sealed halves into sealed_final (sealed cross-check, 26 Nov 2026). Reads sealed_A/truth and sealed_B/truth
(read-only), writes sealed_final/crops.json and sealed_final/annot/ (the hand inputs, unchanged copies). Run once; later
fixes are edits of the copies in sealed_final/annot (logged in sealed_final/fixes_log.txt).
    cd data/sanborn
    python -B bench_2026-11-26/text_fix/sealed_check/scripts/merge.py
Renames: half A's shared ditto annotation files DW##.txt become SA-DW##.txt (crops.json "annot" follows).
Half B's selection files and its two source files (_blocks_src.txt, _dittos_src.txt, already split into SB-*.txt by
builder B) go to annot/selection_B/; half A's json lists to annot/selection_A/. Every crop gets "half": "A" or "B"."""
import os, sys, json, shutil
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import FINAL, jdump
TF = os.path.abspath(os.path.join(HERE, '..', '..'))
A = os.path.join(TF, 'sealed_A', 'truth'); B = os.path.join(TF, 'sealed_B', 'truth')
AN = os.path.join(FINAL, 'annot')
if os.path.exists(os.path.join(FINAL, 'crops.json')) and '--force' not in sys.argv: raise SystemExit('sealed_final/crops.json exists; merge runs once')
os.makedirs(os.path.join(AN, 'selection_A'), exist_ok=True); os.makedirs(os.path.join(AN, 'selection_B'), exist_ok=True)
ca = json.load(open(os.path.join(A, 'crops.json'), encoding='utf8')); cb = json.load(open(os.path.join(B, 'crops.json'), encoding='utf8'))
out = {}
for k, c in ca.items():
    c = dict(c); c['half'] = 'A'
    if 'annot' in c: c['annot'] = 'SA-' + c['annot']
    out[k] = c
for k, c in cb.items():
    c = dict(c); c['half'] = 'B'; c.pop('scope', None)   # the scope boxes are written again by build_final.py
    out[k] = c
assert len(out) == len(ca) + len(cb)
for f in os.listdir(os.path.join(A, 'annot')):
    s = os.path.join(A, 'annot', f)
    if f.endswith('.json'): shutil.copy2(s, os.path.join(AN, 'selection_A', f))
    elif f.startswith('DW'): shutil.copy2(s, os.path.join(AN, 'SA-' + f))
    else: shutil.copy2(s, os.path.join(AN, f))
for f in os.listdir(os.path.join(B, 'annot')):
    s = os.path.join(B, 'annot', f)
    if f.endswith('.json') or f.startswith('_'): shutil.copy2(s, os.path.join(AN, 'selection_B', f))
    else: shutil.copy2(s, os.path.join(AN, f))
jdump(out, os.path.join(FINAL, 'crops.json'))
print(len(out), 'crops;', len(os.listdir(AN)), 'entries in annot/')
