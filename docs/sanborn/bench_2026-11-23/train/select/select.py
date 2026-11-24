"""Selection agent (23 Nov 2026): the pseudo-label plates for V2, the exclusions, and the hand-check ranking.

    python -B select.py      -> selection.json in this folder (reads plates.json, pseudo_area*.json, load_cost.json,
                                ben1a.json, ben1a_lines.json, val1a.json, all made by the scripts beside it)

The choice itself was made by eye on views/sheet_*.jpg (all 104 unplaced plates; the merged step's overlay
unet_data/N_outlines.jpg with each block of picks22_guided/22-N/outlines.json tinted) and views/one_N.jpg (the
shortlist, with area_ng1's confident pixels beside it), together with the measures. EYE below records what was seen.
Every one of the 109 plates is put in exactly one group; the script checks that.
"""
import json, os

OUT = os.path.dirname(os.path.abspath(__file__))
J = lambda f: json.load(open(os.path.join(OUT, f), encoding='utf8'))

SELECT = [  # plate, kind, why, risk
    ('5', 'dense downtown, 100 ft, tint 0.49',
     'The cleanest 100-ft output in the batch: 64 blocks, one colour per printed block, CBD alleys (Shillito Pl, Opera Pl). 100 ft is the benchmark scale and has only 43 (+1A) in training.',
     'Alleys the nets never see stay taught as block (on 1A: 1.1% of street ground).'),
    ('54A', 'dense downtown (Over-the-Rhine north), 100 ft, heavy tint 0.65',
     'Tint 0.65, against 0.15-0.20 on the four labelled plates. Many alleys come out as confident street. The merged blocks look right apart from a few joins at the top.',
     'Heavy tint is where the area net is least sure, so a confident error there gets taught. Low on the eye check.'),
    ('53', 'dense downtown + rail fan + diagonal district, 100 ft, tint 0.59',
     'CBD grid, the Eggleston/Broadway diagonal blocks, a rail fan at Court St, and large lettering (court house).',
     'The rail fan comes out as one region: Ben has not decided the rail-ground rule.'),
    ('7', 'dense West End with mid-block alleys, 100 ft, tint 0.50',
     'Grid with mid-block alleys, 26 of them found as street holes. A very clean output.',
     'Alleys that were not found stay taught as block.'),
    ('51', 'downtown riverfront and wharves, 100 ft, tint 0.56',
     'The only plate where the river and wharves could be handled safely: the merged step puts no block on the river, so with the AND rule the river is left untaught. Tinted downtown otherwise.',
     'area_ng1 calls the river and the public landing CONFIDENT BLOCK. The pseudo label must keep block only inside merged blocks, or the river is taught as block. A few joins in the middle.'),
    ('66', 'dense 200-ft grid, tint 0.31',
     'The most blocks of any plate (106): small blocks, each found on its own. A 200-ft cut grid with more tint than 45, 80 and 82A.',
     '200-ft mid-block alleys are missed and taught as block, as on the labelled plates (a known limit).'),
    ('68', '200-ft grid + Zoo + irregular north edge, tint 0.54',
     'Heavy tint at 200 ft. The Zoological Garden is one large real block. Mixed grid and irregular streets.',
     'A few large joins at the top. The size cap drops 11% of the ground.'),
    ('76', '200-ft diagonal grid + KEY + Duck Creek industrial, tint 0.20',
     '98 blocks on two crossing grids (diagonal streets). Its KEY box is printed inside the map (box in census/rail_key.json).',
     'The KEY and the industrial ground by Duck Creek are one merged block: mask the KEY box and drop big blocks (14% of the ground under the strict cap).'),
    ('79', 'PDF sheet, 200 ft, 94 blocks',
     'The best PDF-sheet output. Not one of the 24 PDF sheets at 200 ft is in training (90 is held out). PDF scan colour, margins, KEY and large lettering.',
     'Off the map ground (the margins) is confident block: mask by N_mapground.png. Some joins on the left.'),
    ('89', 'PDF sheet, 200 ft, same-scale inset, estates/open land',
     'A second PDF sheet: an inset (upper right), large estates with unbuilt subdivisions, and a clean grid on the right half.',
     'Its big estate regions merge across roads (Iona Pl): 36% of the ground is dropped under the strict cap. The weakest of the ten; first to swap for a reserve.'),
]
RESERVE = [('67', '200 ft, tint 0.54, clean grid (a twin of 68)'), ('4', '100 ft, West End + rail terminal, tint 0.48'),
           ('12', '100 ft, tint 0.58, Central Parkway median joined'), ('28', '200 ft clean grid, 73 blocks, little tint'),
           ('11', '100 ft clean grid, tint 0.44'), ('60B', '200 ft clean grid, small; the 60B alley case (27 of ~30 missed)')]
EXCLUDE = {
    'rule: benchmark, never trained or used for checkpoints': ['44'],
    'rule: planned second truth plate': ['90'],
    'already labelled (current labels)': ['43', '45', '80', '82A'],
    "Ben's check (3/4 train, quarter validation)": ['1A'],
    '400 ft: the area net calls almost the whole sheet block (viewed: 46-50, 92-95, 93A, 93B)': ['46', '47', '48', '49', '50', '92', '93A', '93B', '94', '95'],
    'suspect in the merged step (Q1/Q2), and broken by eye': ['2', '3', '41'],
    'small piece (under 11 MP), little ground, mostly edge': ['8B', '15B', '54B', '55B', '64B', '82B', '83B'],
    'river or wharves inside a block': ['1B', '26A', '52', '59A', '59B', '60A', '21', '23'],
    'rail yards joined into blocks': ['13', '37', '40'],
    'open land / hillside joined across roads (most of the plate)': ['25', '26B', '31', '35', '39', '61', '64A', '65', '70', '71', '75', '85A', '19', '22', '24', '27', '30', '32', '73', '74', '81', '88'],
    'PDF sheet with an inset at another scale (400 ft)': ['78'],
    'KEY inside a block plus large joins': ['29', '34'],
    'large joins across streets over a big share of the plate': ['6', '9', '10', '14', '15A', '16', '17', '55A', '56', '57', '62', '63'],
    'fair, not needed (kind already covered by a better plate) or reserve': ['4', '11', '12', '8A', '58', '18A', '18B', '28', '67', '85B', '60B', '83A', '84', '38', '69', '33', '87', '20', '36', '42', '72', '77', '86', '91'],
}
CHECK = [
    ('7', 'Mid-block alleys at 100 ft are the main loss on 44 (all 32 misses there are joins). Pseudo labels cannot teach them: on 1A the line net misses them too, and a 12 px band round its lines catches 4.5% of the errors. 7 has the densest alley grid and a clean output, so the check is quick.'),
    ('54A', 'Heavy tint (0.65) at 100 ft, which sits next to 1A (0.75) in the tint range, with 3x 1A\'s ground (75.6 MP against 24.3 MP). A clean output, so Ben has few edits.'),
    ('60B', 'The 200-ft mid-block alley case (27 of ~30 missed). Small (18.9 MP, 40 blocks), so the quickest check of the list. Do it once Ben has decided whether 200-ft alleys are block sides.'),
    ('79', 'The only way to teach the PDF-sheet look with true labels: 90 stays out, and no PDF sheet is labelled. 94 blocks.'),
    ('51', "Sets Ben's river and wharf rule on a tinted downtown plate. The pseudo label has to leave the river out."),
    ('5', 'CBD at 100 ft, 64 blocks with alleys. A clean output.'),
]


def main():
    R = {r['plate']: r for r in J('plates.json')}
    pa, ps, lc = J('pseudo_area.json'), J('pseudo_area_strict.json'), J('load_cost.json')
    seen = [p for p, *_ in SELECT] + [p for ps_ in EXCLUDE.values() for p in ps_]
    dup = {p for p in seen if seen.count(p) > 1}; missing = set(R) - set(seen); extra = set(seen) - set(R)
    assert not dup and not missing and not extra, (dup, missing, extra)
    bpp = lc['79']['held_bytes_per_px']
    lab_mpx = {N: R[N]['full_mpx'] for N in ('43', '45', '80', '82A', '1A')}
    plates = []
    for p, kind, why, risk in SELECT:
        r = R[p]
        plates.append(dict(plate=p, kind=kind, scale_ft=r['ft_per_inch'], source=r['source'], W=r['W'], H=r['H'], full_mpx=r['full_mpx'], tint=float(r['census_tinted_share']),
                           merged_blocks=r['merged_blocks'], merged_holes=r['merged_holes'], area_conf_share=r['area_conf_share'],
                           taught_half_mpx_sketch=pa['pseudo'][p]['taught_half_mpx'], taught_half_mpx_strict=ps['pseudo'][p]['taught_half_mpx'],
                           taught_acres_sketch=pa['pseudo'][p]['taught_acres'], taught_acres_strict=ps['pseudo'][p]['taught_acres'],
                           big_block_share_strict=ps['pseudo'][p]['big_block_share_of_ground'], key_box=pa['pseudo'][p]['key_masked'],
                           line_net_gb_est=round(r['full_mpx'] * 1e6 * bpp / 2 ** 30, 2), why=why, risk=risk))
    sel_mpx = sum(x['full_mpx'] for x in plates)
    out = dict(
        made_by='data/sanborn/bench_2026-11-23/train/select/select.py', K=len(SELECT), plates=plates, reserve=[dict(plate=p, note=n) for p, n in RESERVE],
        excluded=EXCLUDE, check_by_hand=[dict(rank=i + 1, plate=p, why=w) for i, (p, w) in enumerate(CHECK)],
        totals=dict(
            labelled_today=pa['labelled_total'], labelled_by_plate=pa['labelled'],
            selected_taught_half_mpx_sketch=round(sum(x['taught_half_mpx_sketch'] for x in plates), 1), selected_taught_half_mpx_strict=round(sum(x['taught_half_mpx_strict'] for x in plates), 1),
            selected_taught_acres_sketch=round(sum(x['taught_acres_sketch'] for x in plates)), selected_taught_acres_strict=round(sum(x['taught_acres_strict'] for x in plates)),
            selected_full_mpx=round(sel_mpx, 1), labelled_plus_1A_full_mpx=round(sum(lab_mpx.values()), 1),
            line_net_bytes_per_full_px_measured=bpp, line_net_gb_labelled_plus_1A_est=round(sum(lab_mpx.values()) * 1e6 * bpp / 2 ** 30, 2),
            line_net_gb_selected_est=round(sel_mpx * 1e6 * bpp / 2 ** 30, 2),
            area_net_gb_all_est=round((sel_mpx + sum(lab_mpx.values())) * 1e6 / 4 * 11 / 2 ** 30, 2),
            load_seconds_measured={k: v['seconds'] for k, v in lc.items()},
            scale_mix_after_V2={'100': ['43', '1A'] + [x['plate'] for x in plates if x['scale_ft'] == 100], '200': ['45', '80', '82A'] + [x['plate'] for x in plates if x['scale_ft'] == 200]}),
        ben1a=J('ben1a.json'), ben1a_lines=J('ben1a_lines.json'), val1a=J('val1a.json'))
    json.dump(out, open(os.path.join(OUT, 'selection.json'), 'w', encoding='utf8', newline='\n'), indent=1)
    print(json.dumps(out['totals'], indent=1))


if __name__ == '__main__':
    main()
