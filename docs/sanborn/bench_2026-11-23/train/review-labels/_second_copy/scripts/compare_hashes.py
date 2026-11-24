"""review-labels: compare the two load_hashes.py outputs.  python -B compare_hashes.py today.json staged.json OUT.json"""
import json, sys
a, b = (json.load(open(f, encoding='utf8')) for f in sys.argv[1:3]); out = {}
for N in a['plates']:
    pa, pb = a['plates'][N], b['plates'][N]
    out[N] = {k: pa[k] == pb[k] for k in ('area_x', 'area_label', 'area_edge_weights', 'area_edge_target', 'line_x', 'line_t', 'line_w', 'line_x_channels', 'windows')}
    out[N]['shapes'] = dict(area_x=pa['area_x']['shape'], line_x=pa['line_x']['shape'])
    out[N]['counts_equal'] = pa['counts'] == pb['counts']; out[N]['counts'] = pa['counts']
ok = all(all(v for k, v in r.items() if k not in ('shapes', 'counts')) for r in out.values())
res = dict(all_equal=ok, today=a['modules'], staged=b['modules'], plates=out)
json.dump(res, open(sys.argv[3], 'w', encoding='utf8', newline='\n'), indent=1); print(json.dumps(res, indent=1))
