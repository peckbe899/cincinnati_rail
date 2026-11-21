"""critic: which plate should Ben check next as a second ground-truth plate?

Joins (read-only) census/census.csv (batch indicators, scale, eye label, rail, KEY), outline-nesting/measure.csv
(blocks and lines after the nesting + map-mask fix) and rail/census/census.csv when present, and scores each
unplaced plate on what a second truth plate must do that plate 44 cannot:

  T1 group weight : share of the atlas ground in the plate's (source, scale) group (from the census ground_acres)
  T2 fix tested   : the proposed fixes change it (blocks after the nesting/mask fix vs the batch)
  T3 power        : enough blocks to score PQ (blocks after the fix; 44 has 55)
  T4 rail         : railroad and streetcar rule tracks present, KEY present (tests the KEY mask)
  T5 cost         : editor lines after the fix (a proxy for Ben's checking time)
  T6 not 44's kind: scale != 100 ft, or PDF sheet

    python truth_candidates.py      -> truth_candidates.json, truth_candidates.txt
Numbers are measured from those files; the ranking weights are my judgement and are printed.
"""
import csv, json, os
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
B = HERE + '../'
TRAIN = {'43', '44', '45', '80', '82A'}


def rows(p):
    return {r['plate']: r for r in csv.DictReader(open(p, encoding='utf8'))} if os.path.exists(p) else {}


def f(x, d=0.0):
    try: return float(x)
    except (TypeError, ValueError): return d


C = rows(B + 'census/census.csv'); M = rows(B + 'outline-nesting/measure.csv'); R = rows(B + 'rail/census/census.csv')
grp = lambda r: ('pdf' if r['source'].lower().startswith('pdf') else 'cut') + f"_{int(f(r['ft_per_inch']))}"
acres = {}
for n, r in C.items(): acres[grp(r)] = acres.get(grp(r), 0) + f(r['ground_acres'])
tot = sum(acres.values())
out = []
for n, r in C.items():
    if n in TRAIN: continue
    m = M.get(n, {}); g = grp(r)
    bb = f(m.get('batch_blocks'), f(r['blocks_exported'])); fb = f(m.get('final_blocks'), bb)
    fl = f(m.get('final_editor_lines'), f(r['editor_lines']))
    rr, sc = f(r['railroad_tracks']), f(r['streetcar_tracks'])
    d = dict(plate=n, group=g, ft=f(r['ft_per_inch']), eye=r.get('eye_check', ''), tint=round(f(r['tinted_share']), 3),
             acres=round(f(r['ground_acres'])), batch_blocks=int(bb), fixed_blocks=int(fb), fixed_editor_lines=int(fl),
             fixed_largest_map=m.get('final_largest_map', ''), railroad_tracks=int(rr), streetcar_tracks=int(sc),
             key=r.get('key_found', ''), suspect_batch=r.get('qa_suspect', ''), suspect_fixed=m.get('final_suspect', ''),
             group_ground_share=round(acres[g] / tot, 3))
    # judgement weights (printed in the txt): group ground share, fix tested, power, rail, cost, not 44's kind
    t1 = acres[g] / tot
    t2 = min(1.0, max(0.0, (fb - bb) / max(fb, 1)))
    t3 = min(1.0, fb / 55.0)
    t4 = min(1.0, rr / 20.0) * 0.5 + min(1.0, sc / 10.0) * 0.5
    t5 = 1.0 - min(1.0, fl / 1200.0)
    t6 = 1.0 if (g != 'cut_100') else 0.0
    big = f(m.get('final_largest_map'), 0.0)
    t7 = 1.0 - min(1.0, big / 0.5) if big else 0.5     # usable once fixed: no single block over half the map ground
    d['score'] = round(2 * t1 + 1.5 * t2 + 1.0 * t3 + 0.5 * t4 + 0.75 * t5 + 1.0 * t6 + 1.0 * t7, 3)
    d['parts'] = dict(group=round(t1, 2), fix=round(t2, 2), power=round(t3, 2), rail=round(t4, 2), cost=round(t5, 2), not44kind=t6, usable=round(t7, 2))
    out.append(d)
out.sort(key=lambda d: -d['score'])
json.dump(dict(group_ground_share={k: round(v / tot, 3) for k, v in acres.items()}, ranking=out), open(HERE + 'truth_candidates.json', 'w'), indent=1)
with open(HERE + 'truth_candidates.txt', 'w') as fo:
    fo.write('score = 2*group_ground_share + 1.5*fix_tested + 1*power + 0.5*rail + 0.75*cost + 1*not_44_kind + 1*usable (judgement)\n')
    fo.write('group ground shares: ' + json.dumps({k: round(v / tot, 3) for k, v in acres.items()}) + '\n')
    for d in out[:40]:
        fo.write(f"{d['plate']:5s} {d['group']:8s} eye={d['eye']:5s} tint={d['tint']:.2f} blocks {d['batch_blocks']:3d}->{d['fixed_blocks']:3d} "
                 f"lines_fixed={d['fixed_editor_lines']:5d} largest_map={d['fixed_largest_map']:6s} rr={d['railroad_tracks']:3d} sc={d['streetcar_tracks']:3d} "
                 f"key={d['key']:5s} susp {d['suspect_batch']}->{d['suspect_fixed']} score={d['score']} {d['parts']}\n")
print(open(HERE + 'truth_candidates.txt').read())
