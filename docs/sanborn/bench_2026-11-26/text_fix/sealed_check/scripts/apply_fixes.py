"""Apply the cross-check fixes to the merged annotation files in sealed_final/annot (sealed cross-check, 26 Nov 2026).
    cd data/sanborn
    python -B bench_2026-11-26/text_fix/sealed_check/scripts/apply_fixes.py
Runs once on the merged copies (it refuses to run twice). Each fix is one entry below: the annotation file, the fix id,
the line it replaces (kept as a comment) or None for an added line, the new line, and the reason. Every fix was decided on
4-8x zooms of the scan beside the truth (sealed_check/pics). Added lines go into a '# ===== sealed-check fixes' section
at the end of the file. Dash pieces (EXCLPIECE) come from checks/dash_in_box.json, each looked at on pics/sus_dash_*.png
and pics/z_dash.png."""
import os, sys, json
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from common import FINAL
AN = os.path.join(FINAL, 'annot')
MARK = '# ===== sealed-check fixes (26 Nov 2026)'

FIXES = [
 # ---- block-number crops: line ink labelled text inside the target box
 ('SA-B08', 'F01', None, 'NOTTEXT 9395 2469 9485 2470 5', 'lot line along the foot of block 19 was text inside the box (snapline)'),
 ('SA-B09', 'F02', None, 'NOTTEXT 833 4060 833 4112 5', 'lot line above the first 2 of block 22 was text inside the box (snapline)'),
 ('SA-B25', 'F03', None, 'NOTTEXT 9565 815 9565 905 5', 'dashed edge of the alley band between the 1 and the 0 of block 10 was text (snapline)'),
 ('SB-B11', 'F04', None, 'EXCL 3985 3505 3989 3510', 'a 7 px dash of the dashed band edge was text by block 22'),
 # ---- words in a scope with a wrong box, or glyphs left not text
 ('SB-B17', 'F05', '4611 5190 4632 5190 14 | 51 | lot', '4611 5180 4632 5180 18 | 51 | lot | unsure', 'box lay 10 px below the glyphs of 51 (they were not text)'),
 ('SB-B25', 'F06', '5440 3230 5465 3230 16 | 297 | lot', '5426 3226 5462 3226 16 | 297 | lot', 'box missed the 2 of 297 (86 px not text)'),
 ('SB-B18', 'F07', '3133 5435 3169 5435 18 | 159 | house', '3181 5427 3216 5432 24 | 159 | house', 'box lay 45 px left of the glyphs, over a lot line'),
 ('SA-B13', 'F08', "8445 4310 8463 4310 14 | 68' | lotdim", "8443 4310 8475 4307 16 | 68' | lotdim", 'box missed the prime'),
 ('SA-B13', 'F09', '8506 4360 8521 4360 18 | 10 | lot', '8511 4355 8519 4384 21 | 10 | lot', 'the lot number 10 is turned about 75 degrees; the box missed the 1'),
 ('SA-DW03', 'F10', None, 'FORCE 764 3537 779 3567', 'SA-D21: the diagonal and bar of the 4 of lot 64 were not text'),
 ('SA-DW02', 'F11', None, 'FORCE 5614 2318 5624 2333', 'SA-D15: the diagonal of the story 2 was not text'),
 ('SB-D07', 'F12', None, 'FORCE 2298 1172 2308 1180', 'the diagonal of the 2 of house 3552 was not text'),
 ('SA-DW06', 'F13', None, 'NOTTEXT 2669 4852 2670 4912 5', 'SA-D29: the left wall of the pink building inside the box of the owner letter C was text (snapline)'),
 # ---- words cut by the scope edge that the builders had not typed (their in-scope glyph ink was not text)
 ('SA-B13', 'F14', None, "8542 4253 8581 4243 15 | 25.30' | lotdim | partial unsure", 'lot dimension cut by the scope edge was not typed'),
 ('SA-B13', 'F15', None, "8427 4287 8447 4284 18 | 2.50' | lotdim | partial unsure", 'lot dimension cut by the scope edge was not typed'),
 ('SA-B25', 'F17', None, '9631 911 9663 928 16 | H | owner | partial unsure', 'turned owner letter cut by the scope edge was not typed'),
 ('SB-B02', 'F18', None, '1920 5874 1933 5918 23 | 120 | lot | partial', 'turned lot number cut by the scope edge was not typed'),
 ('SB-B09', 'F19', None, '7655 3305 7692 3305 36 | 98 | lot | partial', 'lot number cut by the scope edge was not typed'),
 ('SB-B09', 'F20', None, '7762 3316 7772 3316 22 | 1 | story | partial', 'story height cut by the scope edge was not typed'),
 ('SB-B15', 'F21', None, "2186 1702 2240 1722 18 | 37.19' | lotdim | partial unsure", 'lot dimension cut by the scope edge was not typed (the 37 was not text)'),
 ('SB-B15', 'F22', None, '2200 1773 2222 1773 46 | E | owner | partial unsure', 'owner letter cut by the scope edge was not typed'),
 ('SB-B15', 'F23', None, '2152 1786 2180 1786 24 | 66 | lot | partial', 'lot number cut by the scope edge was not typed'),
 ('SB-B16', 'F24', None, '2693 5563 2732 5563 22 | 255 | lot | partial', 'lot number cut by the scope edge was not typed'),
 ('SB-B16', 'F25', None, '2622 5564 2655 5564 20 | 281 | lot | partial', 'lot number cut by the scope edge was not typed'),
 ('SB-B17', 'F26', None, "4511 5235 4568 5233 15 | 161.62' | lotdim | partial", 'lot dimension cut by the scope edge was not typed'),
 ('SB-B18', 'F27', None, '3198 5542 3223 5542 18 | 161 | lot | partial', 'lot number cut by the scope edge was not typed'),
 ('SB-B18', 'F28', None, '3128 5545 3158 5545 20 | 187 | lot | partial', 'lot number cut by the scope edge was not typed'),
 ('SB-B19', 'F29', None, "4394 892 4424 892 14 | 50' | lotdim | partial", 'lot dimension cut by the scope edge was not typed'),
 ('SB-B19', 'F30', None, '4504 890 4531 890 15 | 163 | lot | partial', 'lot number cut by the scope edge was not typed'),
 ('SB-D16', 'F31', None, '3285 4884 3306 4884 20 | 2. | story | partial', 'story height cut by the scope edge was not typed'),
 ('SB-D06', 'F32', None, '4149 2920 4169 2920 28 | 2 | story | partial', 'story height cut by the scope edge was not typed'),
 ('SB-D07', 'F33', None, '2246 1103 2260 1103 22 | 2 | story | partial', 'story height cut by the scope edge was not typed'),
 ('SB-B24', 'F34', None, '6064 3242 6090 3242 18 | 100 | lot | partial unsure', 'lot number in the dense grid, cut by the scope edge, was not typed'),
 ('SB-B24', 'F35', None, '6062 3267 6088 3267 18 | 101 | lot | partial unsure', 'lot number in the dense grid, cut by the scope edge, was not typed'),
 ('SB-B24', 'F36', None, '6064 3363 6090 3363 16 | 105 | lot | partial unsure', 'lot number in the dense grid, cut by the scope edge, was not typed'),
 ('SB-B25', 'F37', None, '5517 3157 5545 3157 18 | 14? | lot | partial unsure', 'right-hand column of the dense grid: the first figures (in scope) were not text'),
 ('SB-B25', 'F38', None, '5517 3182 5545 3182 16 | 44? | lot | partial unsure', 'right-hand column of the dense grid: the first figures (in scope) were not text'),
 ('SB-B25', 'F39', None, '5517 3203 5545 3203 16 | 45? | lot | partial unsure', 'right-hand column of the dense grid: the first figures (in scope) were not text'),
 ('SB-B25', 'F40', None, '5517 3224 5545 3224 16 | 46? | lot | partial unsure', 'right-hand column of the dense grid: the first figures (in scope) were not text'),
 ('SB-B25', 'F41', None, '5517 3244 5545 3244 16 | 47? | lot | partial unsure', 'right-hand column of the dense grid: the first figures (in scope) were not text'),
 # ---- full crop SA-F1
 ('SA-F1', 'F42', 'EXCLCIRC 4415 3690 14 filled dot (hydrant or manhole) inside the 24" SEWER label', 'EXCLCIRC 4401 3672 14 filled dot (hydrant or manhole) above the 24" SEWER label',
  'the circle lay 19 px below and 14 px right of the dot: most of the dot was text and the top of the label lost pixels'),
 ('SA-F1', 'F43', None, 'NOTTEXT 5296 4157 5332 4157 5', 'top wall of the small building inside the box of the story 2. (5304 4175) was text'),
 ('SA-F1', 'F44', None, '5229 3235 5238 3235 18 | LUDLOW | street | partial unsure nosnap', 'the foot of a big street letter (LUDLOW, above the window) enters the window by 353 and was not text'),
]


def dash_fixes():
    """EXCLPIECE ops for the dash-like text pieces judged not text (dash_in_box.json indices, see pics/sus_dash_*.png)"""
    S = json.load(open(os.path.join(HERE, '..', 'checks', 'dash_in_box.json')))['suspects']
    crops = json.load(open(os.path.join(FINAL, 'crops.json'), encoding='utf8'))
    keep = [5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37,
            38, 39, 40, 41, 42, 43, 44, 45, 46, 48, 50, 52, 53, 54, 55, 56, 57, 58, 59, 60, 62, 63, 64, 67]
    # first round showed these pieces still text (EXCLPIECE needs the piece wholly inside the box): EXCL their exact bbox
    USE_EXCL = {5, 18, 19, 43, 44, 45, 46, 48, 50, 52, 53, 55, 56, 59, 60, 64}
    out = []; seen = set(); n = 45
    for i in keep:
        s = S[i]; b = s['box']; key = (s['crop'], tuple(b))
        if key in seen: continue
        seen.add(key); f = crops[s['crop']].get('annot', s['crop'])
        why = (f"{s['crop']}: a {s['px']} px dash or wall piece inside the box of {s['kind']} {s['reading']!r} was text "
               f"(dash_in_box #{i}: a dash of a dashed line, or the wall of a small building)")
        if i in USE_EXCL:   # the piece is joined to more text outside its bbox (a wall running on into the next box): EXCL its bbox
            out.append((f, f'F{n:02d}', None, f'EXCL {b[0]} {b[1]} {b[2]} {b[3]}', why)); n += 1
        else: out.append((f, f'F{n:02d}', None, f'EXCLPIECE {b[0] - 1} {b[1] - 1} {b[2] + 1} {b[3] + 1}', why)); n += 1
    return out


if __name__ == '__main__':
    allf = FIXES + dash_fixes(); log = []
    files = sorted(set(f[0] for f in allf))
    for fn in files:
        p = os.path.join(AN, f'{fn}.txt'); L = open(p, encoding='utf8').read().split('\n')
        if any(MARK in x for x in L): raise SystemExit(f'{fn}: fixes already applied')
        add = []
        for f, fid, old, new, why in [x for x in allf if x[0] == fn]:
            if old is None: add += [f'# {fid}: {why}', new]
            else:
                hit = [k for k, x in enumerate(L) if x.strip() == old]
                if len(hit) != 1: raise SystemExit(f'{fn} {fid}: line to replace found {len(hit)} times: {old}')
                k = hit[0]; L[k:k + 1] = [f'# {fid} was: {old}', f'# {fid}: {why}', new]
            log.append(dict(file=fn, fix=fid, old=old, new=new, why=why))
        while L and L[-1] == '': L.pop()
        L += ['', MARK] + add + ['']
        open(p, 'w', encoding='utf8', newline='\n').write('\n'.join(L))
    json.dump(log, open(os.path.join(HERE, '..', 'fixes_applied.json'), 'w', encoding='utf8'), indent=1, ensure_ascii=False)
    print(len(log), 'fixes in', len(files), 'files')
