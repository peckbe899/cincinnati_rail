"""v-code: bench44's 'intact_rings' counts a ring intact when no side is short or paper_edge; the merged step 4 also drops
'not on a line' and 'on rail'. Count both ways on the implementer's merged_batch run (read only)."""
import json, sys
import numpy as np
R = sys.argv[1]
P = json.load(open(R + '/outlines.json', encoding='utf8')); B = json.load(open(R + '/bench44.json', encoding='utf8'))
def joined(p): return all(np.hypot(*(np.array(p[k]['b']) - np.array(p[(k + 1) % len(p)]['a']))) <= 1.5 for k in range(len(p)))
bench = sum(all(s['state'] != 'short' and not s.get('paper_edge') for s in p) and joined(p) for p in P)
real = sum(all(s['state'] not in ('short', 'not on a line', 'on rail') and not s.get('paper_edge') for s in p) and joined(p) for p in P)
holes = sum(1 for p in P if p and p[0].get('hole'))
print(json.dumps(dict(run=R, polygons=len(P), holes=holes, intact_as_bench_counts=bench, intact_after_real_step4=real, headline_intact=B['headline']['all']['intact_rings'])))
