"""bench44: what blocks_noguide.py step 4 drops and keeps, and how much of each lies on Ben's lines (5 px, 20 deg).

    python step4_dropped.py [tag ...]      (default: batch guided)  -> step4_dropped.json
"""
import json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bench44 as B  # noqa: E402

if __name__ == '__main__':
    T = B.load_truth(); ben = B.LineSet(T['lines'], 20.0); out = {}
    for tag in (sys.argv[1:] or ['batch', 'guided']):
        polys = json.load(open(B.HERE + f'runs/{tag}/outlines.json')); g = {'dropped_short': [], 'dropped_paper_edge': [], 'kept_green': [], 'kept_orange': []}
        for p in polys:
            for s in p:
                k = 'dropped_short' if s['state'] == 'short' else ('dropped_paper_edge' if s.get('paper_edge') else ('kept_green' if s['state'] == 'on print' else 'kept_orange'))
                g[k].append((s['a'], s['b'], k))
        out[tag] = {}
        for k, v in g.items():
            ls = B.LineSet(v, 20.0); d = ls.dist_to(ben)
            out[tag][k] = dict(n=len(v), len_px=len(ls.P), on_ben_lines=round(float((d <= 5).mean()), 4) if len(d) else None)
        print(tag, json.dumps(out[tag]), flush=True)
    json.dump(out, open(B.HERE + 'step4_dropped.json', 'w'), indent=1)
