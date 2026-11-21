"""v-final: counts of the 8 plates run by run_plates8.py (v-final/plates/N/), measured here, against the implementer's
merge/impl/r2/batch104_final.json and the batch's own unet_data/N_edges.json. Read only on the repo.
    python -B measure8.py  -> v-final/measure8.json"""
import json, os, sys
import numpy as np
V = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/'
SP = 'C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/'
sys.path.insert(0, V + 'shim'); sys.path.insert(1, V + 'apply/tools/sanborn/unet'); sys.path.append('C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/tools/sanborn/unet')
import _ws  # noqa: E402,F401
import blocks_noguide as BN  # noqa: E402
import edit_server as ES  # noqa: E402  (the repo's clean())
assert BN.__file__.replace(os.sep, '/').startswith(V), BN.__file__
IMP = json.load(open(SP + 'bench_2026-11-21/merge/impl/r2/batch104_final.json'))
L = lambda e: float(np.hypot(e['b'][0] - e['a'][0], e['b'][1] - e['a'][1]))
res = {}
for n in ['90', '30', '47', '1B', '60B', '5', '26A', '2']:
    d = V + f'plates/{n}/'; P = json.load(open(d + 'outlines.json')); R = json.load(open(d + f'{n}_outlines.json')); E = json.load(open(d + f'{n}_edges.json'))
    assert E == BN.step4(P), n                     # N_edges.json is step 4 of outlines.json
    sides = [s for p in P for s in p]; cl = ES.clean(E)
    old = json.load(open(SP + f'unet_data/{n}_edges.json'))
    m = dict(blocks=sum(1 for p in P if not p[0].get('hole')), holes=sum(1 for p in P if p[0].get('hole')), sides_all=len(sides), step4_lines=len(E), step4_len=round(sum(map(L, E))),
             green=sum(e['state'] == 'green' for e in E), editor_lines=len(cl), editor_len=round(sum(map(L, cl))), on_rail=sum(s['state'] == 'on rail' for s in sides),
             not_on_line_dropped=sum(s['state'] == 'not on a line' and not s.get('paper_edge') for s in sides), paper_edge_sides=sum(bool(s.get('paper_edge')) for s in sides),
             bridges=sum('bridge' in s for s in sides), suspect=R['suspect'], why=R['suspect_why'], version=R['version'], map_ground=R['map_ground'], rail=R['rail'][:60],
             batch_step4_lines=len(old), batch_step4_len=round(sum(map(L, old))))
    I = IMP[n]; m['implementer'] = {k: I.get(k) for k in ('blocks', 'holes', 'sides_all', 'exported', 'exported_len', 'editor_lines', 'editor_len', 'on_rail', 'not_on_line_dropped', 'paper_edge_sides', 'bridges', 'suspect', 'version')}
    m['same_as_implementer'] = all([m['blocks'] == I['blocks'], m['holes'] == I['holes'], m['sides_all'] == I['sides_all'], m['step4_lines'] == I['exported'], abs(m['step4_len'] - I['exported_len']) <= 1,
                                    m['editor_lines'] == I['editor_lines'], m['on_rail'] == I['on_rail'], m['suspect'] == I['suspect'], m['version'] == I['version']])
    res[n] = m; print(n, {k: m[k] for k in ('blocks', 'holes', 'step4_lines', 'step4_len', 'green', 'editor_lines', 'on_rail', 'suspect', 'batch_step4_lines', 'same_as_implementer')}, m['why'])
json.dump(res, open(V + 'measure8.json', 'w'), indent=1)
