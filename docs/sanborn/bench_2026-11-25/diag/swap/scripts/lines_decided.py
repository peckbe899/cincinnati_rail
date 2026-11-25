"""lines_decided.py (diag/swap, 25 Nov 2026): the editor lines' precision split by where they lie, from bench44.json
(lines_shown.all: precision, precision_decided, recall_interior, recall_interior_decided; workload delete_len) and the
shown length on / off the decided ground, mean over the 6 grids. System python.
    python -B lines_decided.py NAME RUNS44_DIR [...]
"""
import json, sys, glob
import numpy as np
a = sys.argv[1:]; out = {}
for name, runs in zip(a[::2], a[1::2]):
    R = []
    for f in sorted(glob.glob(runs.rstrip('/') + '/*__grid?/bench44.json')):
        b = json.load(open(f, encoding='utf8')); l = b['lines_shown']['all']; w = b['workload']['all']
        R.append(dict(precision=l['precision'], precision_decided=l['precision_decided'], recall_interior=l['recall_interior'], recall_interior_decided=l['recall_interior_decided'],
                      shown_len=l['shown_len'], delete_len=w['delete_len'], delete_n=w['delete_n'], draw_len=w['draw_len'], shown_len_off_ben=w['shown_len_off_ben']))
    out[name] = {k: round(float(np.mean([r[k] for r in R])), 4) for k in R[0]}; out[name]['grids'] = len(R)
    print(name, json.dumps(out[name]), flush=True)
