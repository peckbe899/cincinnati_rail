"""Write the ditto annotation files and the ditto crops (sealed builder A, 26 Nov 2026).

    cd data/sanborn/bench_2026-11-26/text_fix/sealed_A
    python -B scripts/gen_ditto.py

Hand input: the dictionary W below (one entry per drawn window that holds ditto marks): the plate, the drawn window,
each ditto mark's ink box (measured by ditto_boxes.py from a rough centre, or typed from a 5-8x zoom when the mark
touches a line; marked 'hand'), and every other word near the marks, typed from 3-5x zooms (pics/dctx_*.png, dw_*.png,
w03_w12.png). Output:
  truth/annot/DW##.txt   one annotation file per window (ditto lines: nosnap boxes from the ink box, flag target)
  truth/annot/crops_ditto.json the crops: dittos whose scopes (box grown 25 px) overlap are one crop; window = the union of
                         the scopes grown 30 px; crops.json 'annot' = DW##, 'target_lines' = their annotation lines.
Crop ids SA-D01... in window order (round robin of the draw), then top to bottom, left to right."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__)); ANN = os.path.join(HERE, '..', 'truth', 'annot')
SCALE = {'6': 100, '9': 100, '52': 100, '35': 200, '38': 200, '66': 200, '46': 200}   # plate 46: the marks lie in its 200 ft inset
# window id: (plate, drawn window, draw round, [ditto boxes x0 y0 x1 y1 (x1, y1 exclusive), flags], [other word lines])
W = {
 'DW01': ('6', [668, 4902, 1168, 5402], 1, [
     ([690, 4962, 700, 4971], ''), ([760, 4961, 770, 4970], ''), ([843, 4961, 855, 4971], 'hand: one tick touches the rail tick'),
     ([987, 4963, 996, 4971], ''), ([1065, 4960, 1076, 4966], ''), ([1141, 4958, 1151, 4966], ''),
     ([692, 5143, 704, 5149], ''), ([769, 5139, 779, 5146], ''), ([846, 5137, 855, 5145], ''), ([917, 5136, 927, 5143], ''),
     ([995, 5136, 1004, 5143], ''), ([1074, 5135, 1082, 5141], ''), ([1147, 5133, 1156, 5141], 'hand: touches the rail line')], [
     '# a stub under the rail line at 905-918, 4960-4975 may be a ditto mark almost hidden by the line (the row spacing has a gap there);',
     '# it cannot be told at 10x, so it is not a target and its ink is do not care',
     'CARE 905 4960 918 4976 stub under the rail line: maybe a hidden ditto mark']),
 'DW02': ('52', [5295, 2216, 5795, 2716], 1, [
     ([5774, 2282, 5787, 2292], ''), ([5640, 2333, 5650, 2341], ''), ([5654, 2406, 5664, 2413], ''), ([5667, 2481, 5677, 2489], ''),
     ([5682, 2554, 5693, 2562], ''), ([5697, 2619, 5708, 2628], ''), ([5712, 2690, 5723, 2699], '')], [
     '5612 2326 5621 2326 22 | 2 | story', '5671 2302 5671 2350 17 | 331 | house', '5616 2394 5628 2394 26 | 2 | story',
     '5684 2376 5688 2446 18 | 329-27 | house | run', '5642 2463 5652 2463 20 | 2 | story', '5713 2525 5713 2567 16 | 325 | house',
     '5743 2268 5743 2310 26 | U | owner | unsure', '5760 2302 5760 2331 17 | 30 | lot | unsure', '5801 2258 5816 2258 20 | B | story | unsure',
     '5690 2688 5698 2688 30 | 1 | story', '5741 2656 5741 2702 18 | 321 | house']),
 'DW03': ('35', [338, 3115, 838, 3615], 1, [
     ([713, 3305, 723, 3317], ''), ([718, 3350, 727, 3360], ''), ([727, 3401, 736, 3411], ''), ([731, 3454, 740, 3464], ''),
     ([737, 3496, 746, 3506], ''), ([743, 3548, 753, 3560], ''), ([749, 3600, 758, 3609], '')], [
     '707 3392 694 3255 20 | 2912-14-16-18 | house | run unsure partial', '729 3588 711 3422 20 | 2900-02-04-06-08 | house | run unsure',
     '696 3610 692 3473 34 | AND | street | g:MIAMI_AND_ERIE_CANAL',
     '742 3312 772 3312 18 | 69 | lot', '743 3353 772 3353 20 | 68 | lot', '756 3403 785 3403 20 | 67 | lot', '744 3453 775 3453 18 | 66 | lot',
     '754 3502 783 3502 18 | 65 | lot', '757 3552 786 3552 22 | 64 | lot', '773 3600 803 3600 20 | 63 | lot',
     'EXCL 686 3387 699 3400 specks on the canal band between the two house runs']),
 'DW04': ('38', [3020, 3750, 3520, 4250], 1, [
     ([3403, 3906, 3411, 3917], 'hand: both ticks touch the lot line (ink map)'), ([3403, 3955, 3417, 3969], 'hand: the lower tick touches the lot line (ink map)')], [
     '3425 3905 3439 3905 20 | 5 | lot', '3426 3957 3440 3957 24 | 6 | lot',
     'CARE 3402 3906 3406 3914 upper ditto: contact with the lot line (the line rule took the tick as line ink)',
     'FORCE 3406 3906 3412 3914 upper ditto: the tick right of the contact is text']),
 'DW05': ('66', [8944, 2682, 9444, 3182], 1, [([9248, 2855, 9257, 2861], '')], [
     '9236 2831 9279 2831 18 | 857 | house', '9240 2893 9270 2893 20 | 104 | lot']),
 'DW06': ('46', [2330, 4674, 2830, 5174], 1, [
     ([2643, 4719, 2652, 4730], ''), ([2549, 4725, 2559, 4736], ''), ([2644, 4798, 2651, 4807], ''), ([2548, 4799, 2557, 4810], ''),
     ([2549, 4871, 2558, 4883], ''), ([2640, 4872, 2649, 4882], 'one piece measured; ticks close to the C')], [
     '2512 4730 2528 4730 22 | 14 | lot', '2575 4708 2575 4745 16 | 29 | house', '2583 4791 2583 4827 18 | 27 | house',
     '2577 4860 2577 4890 18 | 25 | house', '2618 4700 2618 4743 18 | 26 | house', '2621 4847 2621 4883 18 | 22 | house',
     '2510 4802 2524 4802 22 | 15 | lot', '2510 4865 2530 4865 26 | 16 | lot', '2670 4797 2700 4797 26 | 33 | lot | partial',
     '2643 4883 2669 4883 32 | C | owner | unsure', '2672 4870 2690 4870 30 | 34 | lot | partial unsure']),
 'DW07': ('9', [5139, 1722, 5639, 2222], 2, [
     ([5541, 1738, 5555, 1746], 'hand: both ticks hang from the line (ink map); rows 1738-39 do not care, 1740-45 text'), ([5543, 2214, 5556, 2227], 'its centre is 1 px inside the window edge'),
     ([5617, 2214, 5631, 2226], '')], [
     '5484 1713 5614 1713 16 | 93-91-89-87 | house | run partial', '5517 1768 5531 1768 22 | 3 | story',
     '5523 2194 5536 2194 28 | 3 | story', '5602 2194 5620 2194 28 | 3 | story', '5522 2260 5632 2260 24 | 86-84 | house | run partial',
     'CARE 5540 1738 5556 1740 ditto ticks at the contact with the line (2 px)', 'FORCE 5540 1740 5556 1746 ditto ticks below the contact are text']),
 'DW08': ('38', [8205, 4302, 8705, 4802], 2, [
     ([8505, 4692, 8515, 4700], ''), ([8563, 4744, 8573, 4751], ''), ([8620, 4797, 8629, 4803], 'its centre is 2 px inside the window edge')], [
     '8521 4665 8544 4665 34 | 27 | lot | partial', '8574 4734 8598 4710 18 | 28 | lot', '8522 4745 8575 4777 18 | 3322 | house',
     '8636 4760 8650 4788 18 | 29 | lot']),
 'DW09': ('6', [7822, 1464, 8322, 1964], 3, [
     ([8081, 1702, 8089, 1708], ''), ([8016, 1705, 8023, 1713], 'one blob (two ticks run together)'), ([8136, 1702, 8144, 1710], ''),
     ([8188, 1699, 8198, 1707], ''), ([8248, 1698, 8258, 1706], ''), ([8311, 1695, 8320, 1703], ''),
     ([7924, 1848, 7932, 1855], ''), ([7984, 1847, 7991, 1854], 'one blob'), ([8051, 1844, 8061, 1854], 'hand: touches the lot line'),
     ([8105, 1843, 8114, 1851], ''), ([8174, 1840, 8184, 1849], ''), ([8227, 1840, 8235, 1849], ''), ([8289, 1838, 8298, 1846], '')], [
     '7832 1740 8087 1740 22 | 1026-24-22-20-18 | house | run', '8117 1740 8172 1740 22 | 1016 | house',
     '8202 1738 8322 1738 24 | 12"SEWER | sewer | partial', '8014 1688 8027 1688 22 | 3 | story', '8122 1687 8138 1687 24 | 3 | story',
     '8151 1865 8167 1865 22 | 3 | story']),
 'DW10': ('9', [7518, 622, 8018, 1122], 3, [
     ([7542, 926, 7551, 936], 'hand: between two close lot lines'), ([7543, 1098, 7554, 1107], '')], [
     '7518 910 7532 910 22 | 3 | story', '7562 910 7581 910 22 | 3 | story', '7507 961 7611 961 20 | 28-26-1024 | house | run partial',
     '7483 1070 7556 1070 20 | 29-27 | house | run partial', '7520 1136 7539 1136 24 | 2 | story']),
 'DW11': ('35', [3429, 2994, 3929, 3494], 3, [([3431, 3187, 3441, 3193], ''), ([3468, 3187, 3476, 3194], '')], [
     '3388 3166 3413 3166 14 | 529 | house | partial', '3416 3166 3443 3166 14 | 527 | house', '3445 3166 3471 3166 14 | 525 | house',
     '3473 3166 3490 3166 14 | 523 | house | partial unsure', '3431 3219 3443 3219 20 | 2 | story', '3460 3220 3466 3220 22 | 1 | story',
     "3495 3196 3515 3196 14 | 125' | lotdim | partial", '3500 3220 3510 3220 20 | 12 | lot | partial unsure']),
 'DW12': ('66', [2613, 4822, 3113, 5322], 3, [
     ([2971, 4999, 2976, 5007], ''), ([2972, 5035, 2978, 5045], ''), ([2972, 5070, 2977, 5079], ''), ([2970, 5104, 2976, 5114], ''),
     ([2971, 5136, 2977, 5147], ''), ([2970, 5180, 2976, 5190], ''), ([2967, 5217, 2974, 5227], ''), ([2968, 5252, 2975, 5263], ''),
     ([2968, 5292, 2974, 5302], '')], [
     '2917 5000 2959 5000 22 | 225 | lot', '2917 5038 2952 5038 22 | 226 | lot', '2917 5074 2954 5074 22 | 227 | lot',
     '2917 5110 2952 5110 20 | 228 | lot', '2917 5143 2952 5143 20 | 229 | lot', '2916 5178 2954 5178 24 | 230 | lot',
     '2916 5213 2948 5213 22 | 231 | lot', '2916 5255 2951 5255 20 | 232 | lot', '2916 5291 2951 5291 20 | 233 | lot',
     '2916 5325 2954 5325 20 | 234 | lot', '3001 5335 2999 4925 24 | 45-47-49-51-53-59-61-63 | house | run unsure',
     '2970 5317 2970 5345 16 | 25 | lotdim | unsure']),
}

crops = {}; n = 0
for wid, (N, win, rnd, dittos, others) in W.items():
    lines = [f'# {wid}: plate {N}, drawn window {win} (round {rnd} of the seeded draw, builtup.py). Ditto marks: every one found inside the',
             '# window (centre inside), boxes from ditto_boxes.py (ink pieces near a rough centre) or typed by hand from 5-8x zooms. Other words',
             '# typed from 3-5x zooms. Full-plate px. Ditto lines are the ink box (nosnap): x0 yc x1 yc h.']
    tl = []
    for (x0, y0, x1, y1), note in dittos:
        if note: lines.append(f'# ditto: {note}')
        yc = (y0 + y1 - 1) / 2; fl = 'target nosnap' + (' unsure' if 'unsure' in note else '')
        lines.append(f'{x0} {yc:g} {x1 - 1} {yc:g} {y1 - y0} | " | ditto | {fl}'); tl.append((len(lines), [x0, y0, x1, y1]))
    lines += others
    with open(os.path.join(ANN, f'{wid}.txt'), 'w', encoding='utf8', newline='\n') as f: f.write('\n'.join(lines) + '\n')
    # clusters by scope overlap (aabb of a nosnap box is the ink box grown ~1.5 px; scope = aabb + 25)
    sc = [(ln, [b[0] - 27, b[1] - 27, b[2] + 27, b[3] + 27]) for ln, b in tl]
    groups = []
    for ln, s in sc:
        hit = [g for g in groups if any(not (s[2] < t[0] or s[0] > t[2] or s[3] < t[1] or s[1] > t[3]) for _, t in g)]
        new = [(ln, s)] + [m for g in hit for m in g]
        groups = [g for g in groups if g not in hit] + [new]
    groups.sort(key=lambda g: (min(s[1] for _, s in g), min(s[0] for _, s in g)))
    for g in groups:
        n += 1; X0 = min(s[0] for _, s in g) - 30; Y0 = min(s[1] for _, s in g) - 30; X1 = max(s[2] for _, s in g) + 30; Y1 = max(s[3] for _, s in g) + 30
        crops[f'SA-D{n:02d}'] = dict(plate=N, win=[X0, Y0, X1, Y1], scale_ft_per_inch=SCALE[N], kind='targeted', target='ditto', scope_pad=25,
                                    annot=wid, target_lines=sorted(ln for ln, _ in g),
                                    why=f'{len(g)} ditto mark(s) found in the seeded random built-up window {win} of plate {N} (round {rnd})')
json.dump(crops, open(os.path.join(ANN, 'crops_ditto.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
print(n, 'crops,', sum(len(c['target_lines']) for c in crops.values()), 'dittos')
for k, c in crops.items(): print(k, c['plate'], c['win'], c['annot'], c['target_lines'])
