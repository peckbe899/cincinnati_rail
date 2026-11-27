"""gate_table.py (text_fix/step4, 27 Nov 2026): "rail and lines no worse anywhere", for each mask set and variant: every
score that is worse with the mask than without it (before), on any ground, kind, grid or plate. Also the finder4 against
finder3 change. Reads step4/scores/{f3,f4}/rail.json, lines_bench.json and lines.json.
    cd data/sanborn; python -B bench_2026-11-26/text_fix/step4/code/gate_table.py
RAIL (per ground and kind; plate 1A's tracks are not complete and Ben has no railroad there or on 5, so precision on 1A
and recall where Ben has no track are not truth): worse = recall10 down, precision10 down, found down, missed up, false
tracks up or false length up. Ink level, listed apart: ink_found down, ink_far_px up.
  'after'        both rules tuned on 44 (bridge + join)
  'after_nojoin' the bridge only
  'afterstrict'  neither rule: the fair number
LINES: plate 44 'worse on some grid' from bench44's paired gains; plates 5 and 1A bench_plate headline changes; Ben lines
lost (lines_compare.py). Variants: ink = "both", no drop; states0 = "states", no drop.
Writes step4/scores/gate.json and gate.txt."""
import json, os
SP = os.getcwd().replace('\\', '/') + '/'; ST = SP + 'bench_2026-11-26/text_fix/step4/'; SC = ST + 'scores/'
out = {}; L = []
R = {S: json.load(open(SC + f'{S}/rail.json', encoding='utf8')) for S in ('f3', 'f4') if os.path.exists(SC + f'{S}/rail.json')}


def rail_losses(b, a):
    W = []; I = []
    for kind in ('railroad', 'streetcar'):
        tb, ta = b['tracks'][kind], a['tracks'][kind]; ib, ia = b['ink'][kind], a['ink'][kind]
        if tb['recall10'] is not None and ta['recall10'] is not None and ta['recall10'] < tb['recall10']: W.append(f"{kind} recall {tb['recall10']} -> {ta['recall10']}")
        if tb['precision10'] is not None and ta['precision10'] is not None and ta['precision10'] < tb['precision10']: W.append(f"{kind} precision {tb['precision10']} -> {ta['precision10']}")
        fb, fa = tb['found_partial_missed'], ta['found_partial_missed']
        if fa[0] < fb[0] or fa[2] > fb[2]: W.append(f"{kind} found/partial/missed {fb} -> {fa}")
        if ta['false_tracks'] > tb['false_tracks'] or ta['false_len'] > tb['false_len']: W.append(f"{kind} false tracks {tb['false_tracks']} ({tb['false_len']} px) -> {ta['false_tracks']} ({ta['false_len']} px)")
        if ib['ink_found'] is not None and ia['ink_found'] is not None and ia['ink_found'] < ib['ink_found']: I.append(f"{kind} ink found {ib['ink_found']} -> {ia['ink_found']}")
        if ia['ink_far_px'] > ib['ink_far_px']: I.append(f"{kind} ink far {ib['ink_far_px']} -> {ia['ink_far_px']} px")
    return W, I


L.append('RAIL: masked against no mask (before). Track-level losses, then ink-level changes for the record.')
for S, rr in R.items():
    for when in ('after', 'after_nojoin', 'afterstrict'):
        for run, v in rr.items():
            if when not in v: continue
            W, I = rail_losses(v['before'], v[when]); out[f'rail:{S}:{when}:{run}'] = dict(track_losses=W, ink_changes=I)
            L.append(f"  {S} {when:12s} {run:11s} losses: {W if W else 'none'}" + (f" | ink: {I}" if I else ''))
if 'f3' in R and 'f4' in R:
    L.append('RAIL: finder4 against finder3 (same rules). Track-level losses, then ink-level.')
    for when in ('after', 'after_nojoin', 'afterstrict'):
        for run in R['f3']:
            if when not in R['f3'][run] or when not in R['f4'].get(run, {}): continue
            W, I = rail_losses(R['f3'][run][when], R['f4'][run][when]); Wg, _ = rail_losses(R['f4'][run][when], R['f3'][run][when])
            out[f'rail:f4-f3:{when}:{run}'] = dict(track_losses=W, ink_changes=I, track_gains=Wg)
            L.append(f"  f4vf3 {when:12s} {run:11s} worse: {W if W else 'none'} | better: {Wg if Wg else 'none'}" + (f" | ink worse: {I}" if I else ''))
if os.path.exists(SC + 'lines_bench.json'):
    LB = json.load(open(SC + 'lines_bench.json', encoding='utf8'))
    L.append('LINES: masked against control (44: worse on some grid; 5 and 1A: worse on the plate)')
    for k, v in LB.items():
        if 'f4-f3' in k: continue
        W = v.get('worse_on_some_grid', v.get('worse')); out[f'lines:{k}'] = W; L.append(f"  {k:22s} worse: {W if W else 'nothing'}")
    L.append('LINES: finder4 against finder3')
    for k, v in LB.items():
        if 'f4-f3' not in k: continue
        W = v.get('worse_on_some_grid', v.get('worse')); out[f'lines:{k}'] = W; L.append(f"  {k:22s} worse: {W if W else 'nothing'}")
if os.path.exists(SC + 'lines.json'):
    LC = json.load(open(SC + 'lines.json', encoding='utf8'))
    L.append('BEN LINES LOST / GAINED (lines_compare.py)')
    for k, v in LC.items():
        out[f'benlines:{k}'] = dict(lost=v['lost_lines'], gained=v['gained_lines'])
        if v['lost'] or v['gained']:
            L.append(f"  {k:20s} lost {v['lost']}: {[(l['kind'], l['len'], [round(x) for x in l['a']]) for l in v['lost_lines']]} | gained {v['gained']}: {[(l['kind'], l['len']) for l in v['gained_lines']]}")
json.dump(out, open(SC + 'gate.json', 'w', encoding='utf8', newline='\n'), indent=1)
open(SC + 'gate.txt', 'w', encoding='utf8', newline='\n').write('\n'.join(L) + '\n'); print('\n'.join(L))
