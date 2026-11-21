"""Census steps 2 and 4: failure modes, suspicion ranking, and the proposed QA flag checked against the census.

    python classify.py   -> classify.json (modes with counts, plates, atlas share; ranking; QA flag check), printed summary;
                            census.json / census.csv = census_base.json + rail_key.json + the verdict columns per plate

Each failure mode has an automatic test on census.json columns. The thresholds were set by looking at the census
distributions (cut plates vs PDF sheets, 44's own values) and then checked by eye on thumbnails (thumbs/). 'visual'
below records what the thumbnails showed, per flagged plate, so the flag's false alarms can be counted.
"""
import json, os, re, csv
HERE = os.path.dirname(os.path.abspath(__file__))
C = {r['plate']: r for r in json.load(open(HERE + '/census_base.json'))}
GUIDED = {'43', '44', '45', '80', '82A'}

MODES = {   # key: (title, test, what it costs)
    'ring': ('Sheet-wide block ring: one block region covers > 50% of the paper and runs along > 50% of its edge band',
             lambda r: r['largest_share'] > 0.5 and r['largest_on_edge_band'] > 0.5),
    'near_empty': ('Near-empty editor output: the editor keeps < 25% of the line length the line network drew',
                   lambda r: (r['editor_per_line'] or 0) < 0.25),
    'partial_loss': ('Partial loss: the editor keeps 25-60% of the line network\'s line length',
                     lambda r: 0.25 <= (r['editor_per_line'] or 0) < 0.6),
    'nested': ('Blocks dropped as nested (RETR_EXTERNAL, outlines.py:92): >= 1 block region inside a hole',
               lambda r: r['nested_dropped'] >= 1),
    'holes': ('Street sides lost on holes: >= 25% of the block boundary length is on holes, never fitted',
              lambda r: r['hole_share'] >= 0.25),
    'saturated': ('Area network calls >= 90% of the paper block', lambda r: r['area_block_share'] >= 0.9),
    'scale400': ('Printed at 400 ft to the inch: no training plate at that scale', lambda r: r['ft_per_inch'] == 400),
    'margin_lines': ('Margin exported as street sides: >= 5 editor lines, or >= 30% of them, within 150 px of the paper edge of an uncut sheet',
                     lambda r: r['source'] == 'pdf sheet' and (r['edge_lines'] >= 5 or (r['edge_lines_share'] or 0) >= 0.3)),
    'low_green': ('Low green share: < 80% of the editor lines on a printed line (or no editor lines)',
                  lambda r: r['green_share'] is None or r['green_share'] < 0.8),
    'big_region_cut': ('Big region on a cut plate (not a ring): one block region covers > 35% of the paper',
                       lambda r: r['source'] == 'cut plate' and r['largest_share'] > 0.35 and not (r['largest_share'] > 0.5 and r['largest_on_edge_band'] > 0.5)),
    'short_loss': ('Step 4 keeps < 60% of the fitted outline length (short pieces and paper-edge sides dropped)',
                   lambda r: (r['outline_kept_share'] or 0) < 0.6),
    'tint_unsure': ('Outside the training colour range: tinted share > 0.4 (training plates 0.15-0.26) and area-net unsure share > 0.2',
                    lambda r: r['tinted_share'] > 0.4 and r['area_unsure_share'] > 0.2),
    'small_piece': ('Small cut piece: < 25 acres of ground', lambda r: r['ground_acres'] < 25),
}
W = dict(near_empty=4, ring=3, partial_loss=2, holes=2, nested=1, low_green=1, margin_lines=1, saturated=1, scale400=1, big_region_cut=1, short_loss=1, tint_unsure=0.5, small_piece=0)

# Candidate QA rules, scored against the eye check (visual.json). The scoring is in-sample: the thresholds were set on
# the same 109 plates that were then looked at, so the counts are optimistic.
import statistics as _st
_bpm = _st.median(r['blocks_exported'] / r['paper_mpx'] for r in C.values())
CANDIDATES = {
    'critic: one region > 30% of the paper': lambda r: r['largest_share'] > 0.3,
    'critic: >= 1 nested region dropped': lambda r: r['nested_dropped'] >= 1,
    'critic: blocks per paper Mpx < 1/4 of median': lambda r: r['blocks_exported'] / r['paper_mpx'] < 0.25 * _bpm,
    'one region > 50% of the paper': lambda r: r['largest_share'] > 0.5,
    'ring (> 50% of paper and > 50% of edge band)': MODES['ring'][1],
    '>= 2 nested regions dropped': lambda r: r['nested_dropped'] >= 2,
    'hole share >= 0.25': lambda r: r['hole_share'] >= 0.25,
    'editor keeps < 60% of line-net length': lambda r: (r['editor_per_line'] or 0) < 0.6,
    'editor keeps < 25% of line-net length': lambda r: (r['editor_per_line'] or 0) < 0.25,
    'green share < 0.8 or no lines': lambda r: r['green_share'] is None or r['green_share'] < 0.8,
    'area block share >= 0.9': lambda r: r['area_block_share'] >= 0.9,
    'area unsure share > 0.25': lambda r: r['area_unsure_share'] > 0.25,
    'scale not 100/200 ft or not recorded': lambda r: r['ft_per_inch'] not in (100, 200),
}
# The proposed QA flag: 'suspect' when any of Q1-Q3 holds. Q4 is optional (catches 21, costs one false alarm, 32).
QA = [('Q1 the editor keeps < 60% of the line length the line network drew', CANDIDATES['editor keeps < 60% of line-net length']),
      ('Q2 >= 2 block regions dropped as nested', CANDIDATES['>= 2 nested regions dropped']),
      ('Q3 printed scale not 100 or 200 ft to the inch (no training plate), or not recorded', CANDIDATES['scale not 100/200 ft or not recorded'])]
QA_OPTIONAL = ('Q4 the area network calls >= 90% of the paper block', CANDIDATES['area block share >= 0.9'])

# What the thumbnails showed (visual.json, looked at by eye on 21 Nov 2026): bad / poor / ok
VISUAL = {k: v for k, v in json.load(open(HERE + '/visual.json')).items() if not k.startswith('_')}
BAD = lambda n: VISUAL.get(n, '')[:3] in ('bad', 'poo')


def order(n): m = re.match(r'(\d+)(.*)', n); return int(m.group(1)), m.group(2)


def score(f):
    fl = [n for n, r in C.items() if f(r)]
    return dict(flagged=len(fl), caught=sum(BAD(n) for n in fl), false_alarms=sorted((n for n in fl if not BAD(n)), key=order),
                missed=sorted((n for n in C if BAD(n) and n not in fl), key=order))


if __name__ == '__main__':
    tot_p = sum(r['paper_mpx'] for r in C.values()); tot_a = sum(r['ground_acres'] for r in C.values())
    modes = {}
    for k, (title, f) in MODES.items():
        ps = sorted((n for n, r in C.items() if f(r)), key=order)
        modes[k] = dict(title=title, plates=ps, count=len(ps), share_plates=round(len(ps) / len(C), 3),
                        share_paper=round(sum(C[n]['paper_mpx'] for n in ps) / tot_p, 3), share_ground=round(sum(C[n]['ground_acres'] for n in ps) / tot_a, 3),
                        lines_lost_nested_px=sum(C[n]['nested_len'] for n in ps) if k == 'nested' else None,
                        pdf=sum(C[n]['source'] == 'pdf sheet' for n in ps), cut=sum(C[n]['source'] == 'cut plate' for n in ps),
                        bad_or_poor_by_eye=sum(BAD(n) for n in ps))
    rank = []
    for n, r in C.items():
        hit = [k for k, (_, f) in MODES.items() if f(r)]
        s = sum(W[k] for k in hit) + (1 - min(1.0, r['editor_per_line'] or 0))
        rank.append(dict(plate=n, score=round(s, 2), modes=hit, source=r['source'], ft_per_inch=r['ft_per_inch'], editor_lines=r['editor_lines'], editor_per_line=r['editor_per_line'],
                         largest_share=r['largest_share'], nested_dropped=r['nested_dropped'], hole_share=r['hole_share'], green_share=r['green_share'], visual=VISUAL.get(n, '')))
    rank.sort(key=lambda x: -x['score'])
    for i, x in enumerate(rank, 1): x['rank'] = i
    cand = {k: score(f) for k, f in CANDIDATES.items()}
    final = score(lambda r: any(f(r) for _, f in QA)); final_opt = score(lambda r: any(f(r) for _, f in QA + [QA_OPTIONAL]))
    per_rule = {name: sorted((n for n, r in C.items() if f(r)), key=order) for name, f in QA + [QA_OPTIONAL]}
    flagged = sorted((n for n, r in C.items() if any(f(r) for _, f in QA)), key=order)
    nbad = sum(BAD(n) for n in C)
    pdf = [r for r in C.values() if r['source'] == 'pdf sheet']
    extra = dict(edge_lines_on_pdf_sheets=sum(r['edge_lines'] for r in pdf), pdf_sheets_with_edge_lines=sum(r['edge_lines'] > 0 for r in pdf),
                 pdf_editor_lines=sum(r['editor_lines'] for r in pdf), nested_regions_total=sum(r['nested_dropped'] for r in C.values()),
                 regions_found_total=sum(r['regions_found'] for r in C.values()), blocks_exported_total=sum(r['blocks_exported'] for r in C.values()),
                 dropped_by_straighten_total=sum(r['dropped_by_straighten'] for r in C.values()),
                 batch_state_done=sum(r['batch_state'] == 'done' for r in C.values()), plates_with_log_issues=sum(bool(r['log_issues']) for r in C.values()),
                 bad_or_poor_paper_share=round(sum(C[n]['paper_mpx'] for n in C if BAD(n)) / tot_p, 3), bad_or_poor_ground_share=round(sum(C[n]['ground_acres'] for n in C if BAD(n)) / tot_a, 3))
    out = dict(modes=modes, ranking=rank, extra=extra, visual_bad_or_poor=nbad, candidates=cand,
               qa=dict(rules=[name for name, _ in QA], optional=QA_OPTIONAL[0], flagged=flagged, n_flagged=len(flagged), per_rule=per_rule, result=final, result_with_optional=final_opt))
    json.dump(out, open(HERE + '/classify.json', 'w'), indent=1)
    # the census itself: base columns + rail in the KEY + the verdict columns
    RK = json.load(open(HERE + '/rail_key.json')) if os.path.exists(HERE + '/rail_key.json') else {}
    R = {x['plate']: x for x in rank}; rows = []
    for n in sorted(C, key=order):
        r = dict(C[n]); k = RK.get(n, {})
        r.update(key_found=k.get('key_score', 0) >= 0.6, railroad_px_in_key=k.get('railroad_px_in_key'), streetcar_px_in_key=k.get('streetcar_px_in_key'), rule_tracks_in_key=k.get('rule_tracks_in_key'))
        r.update(suspicion_rank=R[n]['rank'], suspicion_score=R[n]['score'], failure_modes=' '.join(R[n]['modes']),
                 qa_suspect=n in flagged, qa_why='; '.join(name.split(' ')[0] for name, f in QA if f(C[n])) + ('; Q4' if QA_OPTIONAL[1](C[n]) else ''),
                 eye_check=VISUAL.get(n, ''))
        rows.append(r)
    json.dump(rows, open(HERE + '/census.json', 'w'), indent=1)
    with open(HERE + '/census.csv', 'w', newline='', encoding='utf8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); [w.writerow(r) for r in rows]
    for k, m in modes.items(): print(f"{k:15s} {m['count']:3d} plates ({m['pdf']} pdf, {m['cut']} cut; {m['bad_or_poor_by_eye']} bad/poor by eye) | {100 * m['share_plates']:.0f}% plates {100 * m['share_paper']:.0f}% paper {100 * m['share_ground']:.0f}% ground | {' '.join(m['plates'])}")
    print('\nranking (top 30):')
    for x in rank[:30]: print(f"{x['rank']:3d} {x['plate']:4s} {x['score']:5.2f} {x['source'][:3]} {x['ft_per_inch']} e/l {x['editor_per_line']} lines {x['editor_lines']} | {' '.join(x['modes'])} | {x['visual'][:60]}")
    print('\nextra:', extra, '| bad or poor by eye:', nbad)
    print('\ncandidate rules (flagged / caught of', nbad, '/ false alarms / missed):')
    for k, v in cand.items(): print(f"  {k:46s} {v['flagged']:3d} {v['caught']:3d}  FA {len(v['false_alarms']):2d} {' '.join(v['false_alarms'][:24])}  | missed {len(v['missed'])}: {' '.join(v['missed'])}")
    print('\nQA flag (Q1-Q3):', final['flagged'], 'flagged,', final['caught'], 'of', nbad, 'caught; false alarms', final['false_alarms'], '; missed', final['missed'])
    print('with Q4:', final_opt['flagged'], 'flagged,', final_opt['caught'], 'caught; false alarms', final_opt['false_alarms'], '; missed', final_opt['missed'])
    for name, ps in per_rule.items(): print(f'  {name}: {len(ps)}: {" ".join(ps)}')
