"""errors census, stage 3: the tables (mean over the 6 tile grids, and grid 0 = the batch grid), from census.json and the
per-sample masks of runs/ (collect.py, census.py). Cross-tables are recomputed here from the samples.
    python -B summarize.py   -> summary.json + summary.txt (the tables as printed)
"""
import json, os, sys
import numpy as np, cv2
from scipy.spatial import cKDTree
HERE = os.path.dirname(os.path.abspath(__file__)).replace('\\', '/') + '/'
sys.path.insert(0, HERE); sys.dont_write_bytecode = True
import census as C  # noqa: E402

STEPS = ['baseline'] + C.PAIRS
OUT = []


def p(*a):
    s = ' '.join(str(x) for x in a); print(s, flush=True); OUT.append(s)


def main():
    d = json.load(open(HERE + 'census.json'))
    L = C.load_layers(); ben = L['ben']; L['ben_tree'] = cKDTree(ben['P'])
    gt = cv2.imread(HERE + 'runs/gt_half.png', cv2.IMREAD_UNCHANGED).astype(np.int32); dec = cv2.imread(HERE + 'runs/decided_half.png', 0) > 0
    part = np.load(HERE + 'runs/ben_partner.npy'); interior = np.isin(ben['lab'], ('printed', 'drawn'))
    bc = C.classify(ben['P'], L, gt, dec)
    S = {}
    ref = d['reference']
    for step in STEPS:
        for g in range(6):
            o = d['runs'][f'{step}_g{g}']; r = dict(np.load(HERE + f'runs/{step}_g{g}.npz'))
            js = json.load(open(HERE + f'runs/{step}_g{g}.json'))
            off = r['dp'] > 5; cP = C.classify(r['P'], L, gt, dec)
            band = (cP['dstreet'] > 5) & (cP['dstreet'] <= 40)
            x = dict(PQ=o['blocks']['PQ'], fp=o['blocks']['fp'], merges=o['blocks']['merges'], matched=o['blocks']['matched'],
                     shown=o['shown_len'], false=o['false_len'], false_green=o['false_by_state']['green'],
                     missed_interior=o['missed_interior']['n'], missed_alley=o['missed_interior_partner_lt75'])
            # Ben's point: false line on text / numbers
            x['false_on_text_dom'] = int(((cP['dom'] == 8) & off).sum()); x['false_text_in_window'] = int((cP['text'] & off).sum())
            x['false_near_street_text'] = int((cP['nst'] & off).sum())
            x['false_in_band'] = int((band & off).sum()); x['false_in_band_nst'] = int((band & off & cP['nst']).sum())
            x['true_in_band'] = int((band & ~off).sum())
            for k in range(10): x[f'false_ink_{k}'] = int(((cP['dom'] == k) & off).sum())
            x['false_street_ground'] = int((~cP['inblk'] & off).sum()); x['false_void'] = int((~cP['dec'] & off).sum())
            x['false_far40'] = int(((cP['dstreet'] > 40) & off).sum())
            # false block sides
            fbs = o['false_block_sides_off_ben']
            x['fb_sides_off'] = fbs['n']; x['fb_sides_text_dom'] = fbs.get('ink', {}).get('text/numbers', 0); x['fb_sides_nst'] = fbs.get('near_street_text_in_window', 0)
            x['fb_sides_text_win'] = fbs.get('any_text_in_window', 0)
            # false blocks by kind (a merge is a false block that holds half or more of 2+ Ben blocks)
            mp = set(js['blocks']['merge_p'])
            kinds = {'merge (2+ Ben blocks)': 0, 'piece of a Ben block': 0, 'street ground as block': 0, 'mixed': 0}
            kinds_new = dict.fromkeys(kinds, 0); area_new = dict.fromkeys(kinds, 0)
            for f in o['false_blocks']:
                k = 'merge (2+ Ben blocks)' if f['id'] in mp else f['kind']; kinds[k] += 1
                if f.get('new'): kinds_new[k] += 1; area_new[k] += f['area']
            x['fp_kinds'] = kinds; x['fp_kinds_new'] = kinds_new; x['fp_area_new'] = area_new
            x['fp_void_major'] = sum(1 for f in o['false_blocks'] if f['share_decided'] < 0.5 and f['id'] not in mp)
            x['line_net_on_text'] = o['line_net_on_text']
            if step != 'baseline':
                df = dict(np.load(HERE + f'runs/{step}_g{g}_diff.npz')); new = df['new']; lost = df['lost']; gained = df['gained']
                x['new_false'] = int(new.sum()); x['fixed_false'] = int(df['fixed'].sum()); x['lost'] = o['lost']['n']; x['gained'] = o['gained']['n']
                for k in range(10): x[f'new_ink_{k}'] = int(((cP['dom'] == k) & new).sum())
                x['new_street_ground'] = int((~cP['inblk'] & new).sum()); x['new_void'] = int((~cP['dec'] & new).sum()); x['new_far40'] = int(((cP['dstreet'] > 40) & new).sum())
                x['new_tinted'] = int(((cP['tint'] >= 0.4) & new).sum()); x['new_untinted'] = int(((cP['tint'] < 0.1) & new).sum())
                x['new_foldA'] = int((cP['foldA'] & new).sum())
                for k, nm in enumerate(C.CELLS): x[f'new_cell_{nm}'] = int(((cP['cell'] == k) & new).sum())
                for (a, b) in C.DBINS: x[f'new_d_{a:g}'] = int(((cP['dstreet'] >= a) & (cP['dstreet'] < b) & new).sum())
                x['new_green'] = o['new_false_by_state']['green']
                x['new_nst'] = int((cP['nst'] & new).sum()); x['new_text_dom'] = int(((cP['dom'] == 8) & new).sum())
                x['new_in_band'] = int((band & new).sum()); x['new_in_band_nst'] = int((band & new & cP['nst']).sum())
                x['new_lineP_pair'] = o['new_false_lineP']['pair_mean']; x['new_lineP_base'] = o['new_false_lineP']['baseline_mean']
                li = lost & interior
                x['lost_alley'] = int((li & (part < 75)).sum()); x['lost_street'] = int((li & (part >= 75)).sum())
                x['gained_alley'] = int((gained & interior & (part < 75)).sum())
                x['lost_drawn'] = o['lost_by_kind']['drawn']; x['lost_printed'] = o['lost_by_kind']['printed']; x['lost_sheet_edge'] = o['lost_by_kind']['sheet_edge']
                x['lost_text_win'] = int((li & bc['text']).sum()); x['lost_tinted'] = int((li & (bc['tint'] >= 0.4)).sum()); x['lost_untinted'] = int((li & (bc['tint'] < 0.1)).sum())
                x['lost_void'] = int((li & ~bc['dec']).sum()); x['lost_foldA'] = int((li & bc['foldA']).sum())
                for k, nm in enumerate(C.CELLS): x[f'lost_cell_{nm}'] = int(((bc['cell'] == k) & li).sum())
                x['lost_lineP_pair'] = o['lost_lineP']['pair_mean']; x['lost_lineP_base'] = o['lost_lineP']['baseline_mean']
                x['lost_area_both_block_pair'] = o['lost_area_across']['pair']['both_sides_block']; x['lost_area_both_block_base'] = o['lost_area_across']['baseline']['both_sides_block']
                x['lost_area_both_street_pair'] = o['lost_area_across']['pair']['both_street']; x['lost_area_one_side_pair'] = o['lost_area_across']['pair']['one_side_block']
                x['lost_area_one_side_base'] = o['lost_area_across']['baseline']['one_side_block']
                x['ben_blocks_lost'] = o['ben_blocks_lost']; x['ben_blocks_won'] = o['ben_blocks_won']; x['merges_new'] = o['merges_new']; x['merges_gone'] = o['merges_gone']
            S[(step, g)] = x
    # reference shares for Ben's lines
    p('REFERENCE: Ben interior length', int(interior.sum()), '| Ben interior with partner < 75 px (alley/narrow street):', int((interior & (part < 75)).sum()),
      '| text in window on Ben interior:', int((interior & bc['text']).sum()))
    p('REFERENCE: 5-40 px band beside Ben lines (paper, every 4th px):', ref)
    def mean(step, k): return float(np.mean([S[(step, g)][k] for g in range(6)]))
    def g0(step, k): return S[(step, 0)][k]
    p('\n== headline (mean of 6 grids | grid 0)')
    p('step  PQ  fp  merges  matched  shown  false  false_green  missed_interior  missed_alley')
    for s in STEPS:
        p(s, *[f"{mean(s, k):.4g}|{g0(s, k):.4g}" for k in ('PQ', 'fp', 'merges', 'matched', 'shown', 'false', 'false_green', 'missed_interior', 'missed_alley')])
    p('\n== changes against the baseline, same grid (mean of 6 | grid 0): px of length')
    p('pair new_false fixed_false lost gained lost_alley(partner<75) lost_street gained_alley lost_printed lost_drawn lost_sheet_edge')
    for s in C.PAIRS:
        p(s, *[f"{mean(s, k):.0f}|{g0(s, k)}" for k in ('new_false', 'fixed_false', 'lost', 'gained', 'lost_alley', 'lost_street', 'gained_alley', 'lost_printed', 'lost_drawn', 'lost_sheet_edge')])
    p('\n== NEW false line length by ink under it (mean of 6 grids, px; share of new false)')
    p('pair ' + ' '.join(C.BIN_NAMES[k] for k in range(10)))
    for s in C.PAIRS:
        n = mean(s, 'new_false'); p(s, *[f"{mean(s, f'new_ink_{k}'):.0f}({mean(s, f'new_ink_{k}') / n:.0%})" for k in range(10)])
    p('ALL false line length by ink (mean of 6 grids, px; share of all false)')
    for s in STEPS:
        n = mean(s, 'false'); p(s, *[f"{mean(s, f'false_ink_{k}'):.0f}({mean(s, f'false_ink_{k}') / n:.0%})" for k in range(10)])
    p('\n== NEW false: where (mean of 6 grids; share of new false)')
    p('pair  street_ground  void(undecided)  >40px_from_Ben  tint>=0.4  tint<0.1  foldA  green')
    for s in C.PAIRS:
        n = mean(s, 'new_false'); p(s, *[f"{mean(s, k) / n:.0%}" for k in ('new_street_ground', 'new_void', 'new_far40', 'new_tinted', 'new_untinted', 'new_foldA', 'new_green')])
    p('NEW false by distance to Ben lines (share): ' + ' '.join(f'{a:g}-{b:g}' for a, b in C.DBINS))
    for s in C.PAIRS:
        n = mean(s, 'new_false'); p(s, *[f"{mean(s, f'new_d_{a:g}') / n:.0%}" for a, b in C.DBINS])
    p('NEW false by 3x3 cell (share): ' + ' '.join(C.CELLS))
    for s in C.PAIRS:
        n = mean(s, 'new_false'); p(s, *[f"{mean(s, f'new_cell_{c}') / n:.0%}" for c in C.CELLS])
    p('ALL false: street ground / void / >40 px (share)')
    for s in STEPS:
        n = mean(s, 'false'); p(s, *[f"{mean(s, k) / n:.0%}" for k in ('false_street_ground', 'false_void', 'false_far40')])
    p('\n== LOST lines: where and why (mean of 6 grids)')
    p('pair lost  alley_share  text_in_window_share  tint>=0.4  tint<0.1  void  foldA | lineP at lost: pair vs baseline | area both sides block: pair vs baseline | one side: pair vs base | both street pair')
    for s in C.PAIRS:
        n = mean(s, 'lost')
        p(s, f"{n:.0f}", *[f"{mean(s, k) / n:.0%}" for k in ('lost_alley', 'lost_text_win', 'lost_tinted', 'lost_untinted', 'lost_void', 'lost_foldA')],
          f"| {mean(s, 'lost_lineP_pair'):.2f} vs {mean(s, 'lost_lineP_base'):.2f} | {mean(s, 'lost_area_both_block_pair'):.0%} vs {mean(s, 'lost_area_both_block_base'):.0%}",
          f"| {mean(s, 'lost_area_one_side_pair'):.0%} vs {mean(s, 'lost_area_one_side_base'):.0%} | {mean(s, 'lost_area_both_street_pair'):.0%}")
    p('LOST by 3x3 cell (share): ' + ' '.join(C.CELLS))
    for s in C.PAIRS:
        n = mean(s, 'lost'); p(s, *[f"{mean(s, f'lost_cell_{c}') / n:.0%}" for c in C.CELLS])
    p('Ben interior by 3x3 cell (share):', *[f"{((bc['cell'] == k) & interior).sum() / interior.sum():.0%}" for k in range(9)])
    p('\n== NEW false: line net P at the new false samples, this pair map vs baseline map (mean of 6)')
    for s in C.PAIRS: p(s, f"{mean(s, 'new_lineP_pair'):.2f} vs {mean(s, 'new_lineP_base'):.2f}")
    p('\n== FALSE BLOCKS by kind (sum over 6 grids; new = IoU <= 0.5 with every baseline false block, same grid)')
    for s in STEPS:
        tot = {k: sum(S[(s, g)]['fp_kinds'][k] for g in range(6)) for k in S[(s, 0)]['fp_kinds']}
        nw = {k: sum(S[(s, g)]['fp_kinds_new'][k] for g in range(6)) for k in S[(s, 0)]['fp_kinds']}
        ar = {k: round(sum(S[(s, g)]['fp_area_new'][k] for g in range(6)) / 6 / 1e6, 2) for k in S[(s, 0)]['fp_kinds']}
        p(s, 'all:', tot, '| new:', nw if s != 'baseline' else '-', '| new area Mpx per grid:', ar if s != 'baseline' else '-', '| non-merge fp mostly in void:', sum(S[(s, g)]['fp_void_major'] for g in range(6)))
    p('\n== BEN\'S POINT: false lines on text and numbers (mean of 6 grids)')
    p('step  false_len  dominant_ink_text  any_text_in_7x7  near-street_text(<=40px)_in_7x7 | in the 5-40 px band: false_len, share on near-street text (reference band share %.1f%%)' % (100 * ref['band_share_near_street_text']))
    for s in STEPS:
        n = mean(s, 'false'); nb = mean(s, 'false_in_band')
        p(s, f"{n:.0f}", f"{mean(s, 'false_on_text_dom'):.0f} ({mean(s, 'false_on_text_dom') / n:.1%})", f"{mean(s, 'false_text_in_window'):.0f} ({mean(s, 'false_text_in_window') / n:.1%})",
          f"{mean(s, 'false_near_street_text'):.0f} ({mean(s, 'false_near_street_text') / n:.1%})", f"| {nb:.0f}, {mean(s, 'false_in_band_nst') / max(nb, 1):.1%}")
    p('NEW false on text (pairs only): dominant text, near-street text, in band share')
    for s in C.PAIRS:
        n = mean(s, 'new_false'); nb = mean(s, 'new_in_band')
        p(s, f"{mean(s, 'new_text_dom'):.0f} ({mean(s, 'new_text_dom') / n:.1%})", f"{mean(s, 'new_nst'):.0f} ({mean(s, 'new_nst') / n:.1%})", f"band {nb:.0f}: {mean(s, 'new_in_band_nst') / max(nb, 1):.1%}")
    p('false BLOCK sides off Ben (mean of 6): length, dominant text, any text in window, near-street text')
    for s in STEPS:
        n = mean(s, 'fb_sides_off')
        p(s, f"{n:.0f}", f"{mean(s, 'fb_sides_text_dom'):.0f} ({mean(s, 'fb_sides_text_dom') / max(n, 1):.1%})", f"{mean(s, 'fb_sides_text_win'):.0f} ({mean(s, 'fb_sides_text_win') / max(n, 1):.1%})", f"{mean(s, 'fb_sides_nst'):.0f} ({mean(s, 'fb_sides_nst') / max(n, 1):.1%})")
    p('line net response on ink (mean of 6): near-street text meanP / share P>0.5 | far text | block line ink | lot line ink')
    for s in STEPS:
        t = lambda k: np.mean([S[(s, g)]['line_net_on_text'][k] for g in range(6)])
        p(s, f"{t('near_street_mean_P'):.3f}/{t('near_street_share_P_gt_half'):.3f} | {t('far_text_mean_P'):.3f}/{t('far_text_share_P_gt_half'):.3f} | {t('block_line_ink_mean_P'):.3f}/{t('block_line_ink_share_P_gt_half'):.3f} | {t('lot_line_ink_mean_P'):.3f}/{t('lot_line_share_P_gt_half'):.3f}")
    p('\n== Ben blocks lost / won and merges, grid 0')
    for s in C.PAIRS:
        x = S[(s, 0)]; p(s, 'lost', x['ben_blocks_lost'], 'won', x['ben_blocks_won'], 'new merges', x['merges_new'], 'merges gone', x['merges_gone'])
    json.dump({f'{k[0]}_g{k[1]}': v for k, v in S.items()}, open(HERE + 'summary.json', 'w'), indent=1)
    open(HERE + 'summary.txt', 'w').write('\n'.join(OUT) + '\n')


if __name__ == '__main__':
    main()
