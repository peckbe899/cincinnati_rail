"""ggate.py (final gate): the five gate verdicts from the score files, with the targets set before the run.

    cd data/sanborn
    python -B bench_2026-11-26/text_fix/gate/scripts/ggate.py

Reads gate/scores/boot_sealed.json, gate/scores/lines/finder4.json, gate/pics/rail/railnew.json (and the eye verdicts
written below), gate/scores/heldout/boot_H.json. Writes gate/scores/gate_verdicts.json and prints it.
"""
import json
G = 'bench_2026-11-26/text_fix/gate'
O = json.load(open(f'{G}/scores/boot_sealed.json')); L = json.load(open(f'{G}/scores/lines/finder4.json'))
RN = json.load(open(f'{G}/pics/rail/railnew.json')); H = json.load(open(f'{G}/scores/heldout/boot_H.json'))
V = {}
b = O['block']['all']; V['1_block'] = dict(target='pixel recall >= 0.95 and words found >= 95%', pixel_recall=b['finder4']['pixel_recall'],
                                           words=f"{b['finder4']['words_found']}/{b['words']}", word_share=b['finder4']['word_share'],
                                           ci95=O['block']['boot_word']['finder4'], finder3=b['finder3'],
                                           verdict='PASS' if b['finder4']['pixel_recall'] >= 0.95 and b['finder4']['word_share'] >= 0.95 else 'FAIL')
d = O['ditto']['all']; V['2_ditto'] = dict(target='pixel recall >= 0.90 and words found >= 90%', pixel_recall=d['finder4']['pixel_recall'],
                                           words=f"{d['finder4']['words_found']}/{d['words']}", word_share=d['finder4']['word_share'],
                                           ci95=O['ditto']['boot_word']['finder4'], finder3=d['finder3'],
                                           verdict='PASS' if d['finder4']['pixel_recall'] >= 0.90 and d['finder4']['word_share'] >= 0.90 else 'FAIL')
f = O['full']['both']; a3, a4 = f['finder3'], f['finder4']
sw = [int(x) for x in a4['street_words'].split('/')]
sub = dict(F1=a4['F1'] >= a3['F1'] - 0.002, nontext=(a4['nontext_share'] - a3['nontext_share']) <= 0.003,
           street_pixels=a4['street_pixel_recall'] >= 0.95, street_words=sw[0] / sw[1] >= 0.95,
           straight=a4['straight_called_text'] <= a3['straight_called_text'])
V['3_full_no_harm'] = dict(F1=[a3['F1'], a4['F1']], nontext_points=[round(100 * a3['nontext_share'], 3), round(100 * a4['nontext_share'], 3)],
                           street_pixel_recall=[a3['street_pixel_recall'], a4['street_pixel_recall']], street_words=[a3['street_words'], a4['street_words']],
                           straight_called_text=[a3['straight_called_text'], a4['straight_called_text'], a4['straight_px']],
                           paired_diff_ci95=f['boot_tile']['diff_B_minus_A'], subtests={k: ('PASS' if v else 'FAIL') for k, v in sub.items()},
                           verdict='PASS' if all(sub.values()) else 'FAIL')
ln = {N: dict(px1=round(100 * L[N]['a_line_ink_1px']['share'], 4), px3=round(100 * L[N]['a_line_ink_3px']['share'], 4)) for N in ('44', '1A', '5')}
eye = dict(note='every new text blob in the rail bands was looked at by eye at 4x (pics/rail): none is a rail tick or a streetcar dash; '
                '44: feet of the E of AVENUE on the streetcar line (3 blobs, 2 on one E); 5: a big crossed figure (4 or A) at 4153,989 and a big 5 at 2807,2345 whose '
                'strokes meet a streetcar track end (a few px may be track ink), the joins of a big Q and an H with a track line (4 blobs, 2-11 px)',
           blobs={N: RN[N]['new_blobs_in_band'] for N in RN}, ticks_or_dashes=0)
V['4_lines_rail_in_sample'] = dict(line_ink_called_text_pct=ln, rail=eye,
                                   verdict='PASS' if all(v['px1'] <= 0.5 and v['px3'] <= 0.5 for v in ln.values()) and eye['ticks_or_dashes'] == 0 else 'FAIL')
h = H['full']; V['5_H1_H4'] = dict(F1=[h['both']['finder3']['F1'], h['both']['finder4']['F1']], by_crop={k: [h[k]['finder3']['F1'], h[k]['finder4']['F1']] for k in ('H1', 'H2', 'H3', 'H4')},
                                   paired_diff_ci95=h['both']['boot_tile']['diff_B_minus_A']['F1'],
                                   verdict='PASS' if h['both']['finder4']['F1'] >= h['both']['finder3']['F1'] - 0.002 else 'FAIL')
json.dump(V, open(f'{G}/scores/gate_verdicts.json', 'w'), indent=1)
for k, v in V.items(): print(k, v['verdict'], json.dumps({q: w for q, w in v.items() if q != 'verdict'})[:600])
