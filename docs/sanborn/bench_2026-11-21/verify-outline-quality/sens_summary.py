"""verify-outline-quality: table of my plate-44 bench runs (runs/TAG/bench44.json from bench44_vcopy.py) -> sens_summary.json"""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)).replace(chr(92), '/') + '/'
K = ('PQ', 'matched', 'fp', 'merges', 'recall_interior', 'precision', 'precision_green', 'ben_blocks_closed', 'delete_len', 'draw_len')
out = {}
for t in ('v_batch', 'v_proposed', 'v_abc_keepall', 'sens_seedmin1000', 'sens_seedmin4000', 'sens_colgap125', 'sens_snap24', 'v_guided_cur', 'v_guided_proposed', 'v_guided_abc_keepall'):
    b = json.load(open(HERE + f'runs/{t}/bench44.json'))
    out[t] = {f: {k: b['headline'][f][k] for k in K} for f in ('all', 'A', 'B')}
    out[t]['editor_face_PQ'] = b['stages']['4_editor_shows']['blocks']['all']['PQ']; out[t]['outline_s'] = b['meta']['outline_step_seconds']
    h = out[t]
    print(f"{t:22s} PQ {h['all']['PQ']:.4f} (A {h['A']['PQ']:.4f} B {h['B']['PQ']:.4f}) rec {h['all']['recall_interior']:.4f} prec {h['all']['precision']:.4f} green {h['all']['precision_green']:.4f} closed {h['all']['ben_blocks_closed']} del {h['all']['delete_len']} draw {h['all']['draw_len']} faces-PQ {h['editor_face_PQ']} t {h['outline_s']}")
json.dump(out, open(HERE + 'sens_summary.json', 'w'), indent=1)
