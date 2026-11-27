"""DEV ONLY (integrate, 26 Nov 2026): which of block fix A's changed words does the gate keep (an A word box, grown 8 px,
overlaps a number that block fix B reads) and which does it drop? Writes the two box lists for sheet.py.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/integrate/code/gatelist.py ROOT N OUT_PREFIX
(ROOT/A/N_text.json and ROOT/Bf/N_text.json from devrun.py; writes OUT_PREFIX_kept.json, OUT_PREFIX_dropped.json)
"""
import json, os, sys
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

root, N, pre = sys.argv[1:4]
iA = json.load(open(os.path.join(root, 'A', f'{N}_text.json'))); iB = json.load(open(os.path.join(root, 'Bf', f'{N}_text.json')))
def grow(b, p=8): return [b[0] - p, b[1] - p, b[2] + p, b[3] + p]
def ov(a, b): return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
bb = [grow(c['box']) for c in iB['changes']]
kept, dropped = [], []
for c in iA['changes']:
    (kept if any(ov(grow(c['box']), b) for b in bb) else dropped).append(c['box'] + [c['to_text'] + c['to_shared']])
json.dump(kept, open(pre + '_kept.json', 'w')); json.dump(dropped, open(pre + '_dropped.json', 'w'))
pk = sum(k[4] for k in kept); pd = sum(k[4] for k in dropped)
print(f'{N}: A words {len(iA["changes"])}: kept {len(kept)} ({pk} px), dropped {len(dropped)} ({pd} px); B numbers {len(bb)}')
