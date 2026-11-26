"""Gate verdicts (26 Nov 2026) from the gate scorer's outputs. Reads gate/out/scores/*.json (score_text.py),
gate/out/my_score*.json, gate/out/lines_ref/*.json (finder2's check_lines_rail.py), gate/out/my_lines.json,
gate/out/my_rail_*.json. Writes gate/out/gate_summary.json and prints it.
    cd data/sanborn; python -B bench_2026-11-25/text_v1/gate/scripts/gate_summary.py"""
import json, os
G = 'bench_2026-11-25/text_v1/gate/out/'
S = lambda m, t: json.load(open(G + f'scores/{m}__{t}.json'))['pools']['ALL']
out = {}
for t in ('heldfix', 'helddeliv', 'v2'):
    for m in ('bin8', 'v1', 'v2', 'v3') + (('v3ex',) if t != 'v2' else ()):
        p = S(m, t); k = p['by_kind']
        out[f'{m}@{t}'] = dict(P=p['pix']['precision'], R=p['pix']['recall'], F1=p['pix']['f1'], nontext=p['nontext_called_text']['share'],
                               **{f'{kk}_R': k[kk]['recall'] for kk in ('street', 'block', 'house', 'ditto', 'lot', 'lotdim', 'story', 'owner', 'pipe', 'sewer') if kk in k},
                               street_words=f"{k['street']['words_found']}/{k['street']['words']}", block_words=f"{k['block']['words_found']}/{k['block']['words']}")
L = {m: json.load(open(G + f'lines_ref/{m}.json')) for m in ('bin8', 'v1', 'v2', 'v3')}
ML = json.load(open(G + 'my_lines.json'))
for m in L:
    out[f'{m}@ben_lines'] = {N: dict(ref_1px=L[m][N]['a_line_ink_1px']['share'], ref_3px=L[m][N]['a_line_ink_3px']['share'], ref_cut=L[m][N]['a_length']['finder_cut'],
                                     mine_1px=ML[N][m]['share_1'], mine_3px=ML[N][m]['share_3'], mine_cut=ML[N][m]['cut']) for N in ('44', '1A', '5')}
def verdict(m, t='heldfix'):
    o = out[f'{m}@{t}']; lmax = max(max(v['ref_3px'], v['mine_3px']) for v in out[f'{m}@ben_lines'].values())
    return dict(F1=o['F1'], F1_pass=o['F1'] >= 0.92, street=o['street_R'], street_pass=o['street_R'] >= 0.95, block=o['block_R'], block_pass=o['block_R'] >= 0.95,
                line_ink_max_3px=lmax, line_pass=lmax <= 0.005)
out['step2_gate'] = {m: verdict(m) for m in ('v2', 'v3')}
out['step2_gate_delivered_truth'] = {m: verdict(m, 'helddeliv') for m in ('v2', 'v3')}
json.dump(out, open(G + 'gate_summary.json', 'w'), indent=1)
for k, v in out.items(): print(k, json.dumps(v))
