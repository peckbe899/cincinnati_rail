# Sealed held-out set, half A (sealed builder A, 26 Nov 2026)

Text truth for the final gate. Nobody tunes on it. It covers plates 6, 9, 52 (100 ft), 35, 38, 41, 66 (200 ft) and 46 (400 ft, with a 200 ft inset).
No finder output, no bin 8 and no other method output was opened on these plates, while choosing or while labelling.
The only tools used were the scan (cufp/22-N.jpg) and its paper mask. No method was scored on this set.

## What is here

| | crops | target words | notes |
|---|---|---|---|
| block numbers (targeted) | SA-B01 ... SA-B26 | 26 | 9 at 100 ft (plates 6, 9, 52), 12 at 200 ft (35, 38, 41, 66), 5 at 400 ft (46) |
| ditto marks (targeted) | SA-D01 ... SA-D42 | 68 | 38 at 100 ft (6, 9, 52), 30 at 200 ft (35, 38, 66, and 6 in plate 46's 200 ft inset). None at 400 ft. None on plate 41. |
| full crop | SA-F1 | 475 words | plate 38 (200 ft), window 4237,3226 - 5737,4226 (1000 x 1500, y by x) |

All counts are MEASURED (truth/*_words.json).

Ink size of the targets (ink pixels in the word's box, MEASURED):
- Block numbers: median 1,091 px (100 ft: median 1,500, range 1,122-2,403; 200 ft: median 900, range 329-1,593; 400 ft: median 876, range 699-1,591).
- Ditto marks: median 39 px (100 ft: median 41, range 21-88; 200 ft: median 35, range 19-84). The pointer script measured the two ticks alone at a median of about 37 px (ditto_boxes_measured.json).
  Where a mark touches a line, the box count includes the line pixels in the box (SA-D07, SA-D30, SA-D39, SA-D22).
  These marks are small, like the 26 px median of plates 90 and 54A, not like the 66 px of T1-T7.

Every target's reading, ink px and scored text px is in its words.json (`target: true`, `ink_px`, `scored_text_px`).

## Format (score_text.py runs on it unchanged)

Same layout as text_v1/truth: crops.json, <id>_mask.png (0 paper, 1 ink that is not text, 2 text ink, 3 don't care) and <id>_words.json.
- **Targeted crops** have `"kind": "targeted"`, `"target": "block"` or `"ditto"` and `"scope_pad": 25`. The scope is each target word's box (its aabb) grown by 25 px.
  Inside the scope all ink is labelled. Outside it the mask is 3, paper included.
  words.json keeps the target words (kind block or ditto; reading the figures, or `"`) and every other word whose box meets the scope.
  Words wholly outside the scope are listed in `dropped_outside_scope`.
- **SA-F1** has `"kind": "full"`. Every ink pixel is labelled, as in H1-H4.
- Ditto crops share one annotation file per drawn window (`"annot": "DW##"`). `"target_lines"` names the annotation lines that are their targets.
- Format check (MEASURED): score_text.py was run with each truth mask as its own prediction (`--codes 2`). It read all 69 crops and gave P = R = F1 = 1 with every word found. That checks only the format. It is not a method score.

Rebuild:

```
cd data/sanborn/bench_2026-11-26/text_fix/sealed_A
python -B scripts/gen_ditto.py
python -B scripts/merge_crops.py
cd ../../..
python -B bench_2026-11-26/text_fix/sealed_A/scripts/build_truth_sa.py --all
```

## Conventions (Ben has not answered yet; these are used)

- Text: letters, digits, `' " . - ± ½`, ditto marks, story heights, and pipe and sewer labels.
- Not text: hydrants, manholes, hooks and rail ticks, and lines and their dashes.
- A block side through a row of house numbers stays a side.
- Where text ink and line ink touch, the ink within 2 px of the contact is don't care. This is v2's shared-ink rule, unchanged.
- A ditto word is one mark: the pair of ticks, or one blob when the two ticks run together. Each mark is boxed by its ink (`nosnap`).

## How the targets were picked (seeds and full lists)

**Block numbers.**
1. Each plate was viewed at 1/4 size (pics/quarter/q_N_rRcC.png).
2. Every block number I could see went into the list in annot/block_candidates.json, with its approximate position.
   Doubtful ones carry a `?`. On plate 46 only the 400 ft part was listed.
3. Each list was shuffled with `random.Random(plate)`, seeded with the plate name string (scripts/draw_blocks.py; the order is in annot/block_draw_order.json).
4. The first 3 per plate (5 on plate 46) that are block numbers at 1:1 were taken. Two were skipped, both on plate 38 (below); the draw was not redone.
5. On plates 6, 9 and 52 the 1/4-size position of some candidates was off by up to about 60 px. Each was found at 1:1 in that place.

Candidate counts (MEASURED): 6: 24, 9: 31, 52: 27, 35: 22, 38: 38, 41: 24, 66: 47, 46: 14.

Drawn, in draw order:

| plate | targets |
|---|---|
| 6 | 25, 13, 2 |
| 9 | 35, 27, 32 |
| 52 | 6, 19, 22 |
| 35 | 12, 13, 4 |
| 38 | 19, 36, 7 |
| 41 | 14, 2, 12 |
| 66 | 58, 19, 77 |
| 46 | 2, 6, 4, 10, 11 |

Plate 38 draw order: 19, 36, 7?, 25?, 1?, ...
- 36 (4940,3960) lies inside the full crop SA-F1, so it is labelled there (kind block), not as a targeted crop.
- 7? at 4800,2650 is a block number crossed by the street line: SA-B14.
- 25? at 9750,5800 is not a block number at 1:1. There are lot numbers and the letters of SHIELDS there (pics/blk_check5.png), so it was skipped.
- 1? at 1490,1628 became SA-B15. It is a big bold lone 1 in an open area, read as block 1 (unsure).

The drawn set includes block numbers that are hard for the finder (an estimate from what is printed):
- crossed by lines: 2 on plate 6, 32 on plate 9, 6, 19, 22 on plate 52, 13 on plate 35, 7, 19 on plate 38, 2 on plate 41, 58, 19, 77 on plate 66, 2, 6, 4, 10 on plate 46;
- in a building-outline corner: 25 on plate 6;
- in a dense junction: 4 on plate 35;
- thin or broken: 2 on plate 46 (thin, hand-like), 11 on plate 46 (broken strokes).

**Ditto marks.** Windows of 500 x 500 px were drawn at random over each plate (scripts/builtup.py ditto).
- Seed `'ditto-N'` (N = the plate name), with `random.randint` centres.
- A window was kept when it was built up: building colour covers 10% or more of it and paper 97% or more (rule in builtup.py).
- The windows (annot/ditto_windows.json) were opened round-robin over the plates (annot/ditto_round_robin.json).
- Rounds 1-3 were opened: 22 windows, since plate 46 has only one built-up window (in its 200 ft inset).

Every ditto mark whose centre lies inside an opened window was taken. A mark was found on the 2x window views (pics/dwin_*.png) and decided on 5-8x zooms (pics/dz_*.png, dctx_*.png).
A pointer script (scripts/tick_pairs.py: pairs of small ink pieces 3-14 px apart) listed spots to look at again; it decides nothing.

| window | plate | drawn window | round | ditto marks |
|---|---|---|---|---|
| DW01 | 6 | 668,4902-1168,5402 | 1 | 13 |
| DW09 | 6 | 7822,1464-8322,1964 | 3 | 13 |
| DW07 | 9 | 5139,1722-5639,2222 | 2 | 3 |
| DW10 | 9 | 7518,622-8018,1122 | 3 | 2 |
| DW02 | 52 | 5295,2216-5795,2716 | 1 | 7 |
| DW03 | 35 | 338,3115-838,3615 | 1 | 7 |
| DW11 | 35 | 3429,2994-3929,3494 | 3 | 2 |
| DW04 | 38 | 3020,3750-3520,4250 | 1 | 2 |
| DW08 | 38 | 8205,4302-8705,4802 | 2 | 3 |
| DW05 | 66 | 8944,2682-9444,3182 | 1 | 1 |
| DW12 | 66 | 2613,4822-3113,5322 | 3 | 9 |
| DW06 | 46 (200 ft inset) | 2330,4674-2830,5174 | 1 | 6 |

Opened windows with no ditto mark:
- 6 round 2;
- 9 round 1;
- 52 rounds 2 and 3;
- 35 round 2;
- 38 round 3;
- 41 rounds 1, 2 and 3;
- 66 round 2.

The marks of one window whose scopes overlap form one crop (42 crops).

**Full crop.**
1. `random.Random('SA-F1').choice(['35','38','41','66'])` chose plate 38.
2. With seed `'SA-F1-38'`, built-up 1500 x 1000 windows were drawn; the 14th draw was the first built-up one: 4237,3226-5737,4226 (building fill 13.8%).
3. The earlier draws with the colour rules before the fixes below landed elsewhere. The rule was fixed before any window was looked at.
4. The ditto windows on plate 38 avoid this window.

Fixes to the built-up rule before use:
- the plate paper is yellowish, so the colour thresholds are relative to each plate's paper;
- the dark scanner border is not fill;
- the sheet edge and tab are not fill.

## How it was labelled

- Builder: scripts/build_truth_sa.py, a copy of text_v1/truth-fix/scripts/build_truth_v2.py with common.py and snapline.py. The same ink rule (L < 140 on the paper), snap and shared-ink rule are used. The changes:
  - targeted scope;
  - shared annotation files;
  - CARESTRIP, a strip whose ink is all don't care, for a glyph stroke that lies on a line;
  - bin 8 removed from common.py and from the check tiles.
- Words were typed by eye from 2.5-5x zooms in plate px (annot/*.txt; format as text_v1 README).
- Every target was checked at 4-8x, scan beside truth: pics/check/tg_<id>_*.png, combined in pics/chkB_*.png, chkB_fix_0.png, chkDs_*.png, chkDm_0.png, chkDn_0.png, chkDfix_0.png.
- SA-F1 was read on 16 tiles at 2.5x (pics/F1/), checked on 16 tiles at 2x (pics/check/tile_SA-F1_rRcC.png) and fixed on 4-8x zooms (pics/check/zoom_SA-F1_*.png).
- Fixes after the check:
  - In 4 block crops a lot line has 1-3 px gaps, so the 121-px-free line rule missed it inside the box: B09, B22, B23 (line made not text) and B21 (dash made not text).
  - B17: the lot line lies along the diagonal of the 2, shared, so it is don't care.
  - B01: the building outline inside the box was made not text.
  - B08: the box was grown to the foot of the 9.
  - SA-F1: 9 word lines changed (one also adds a missed 50') and 14 ops added (each with its reason in annot/SA-F1.txt).

## Known doubtful spots

- **SA-B15 (plate 38, "1")**: a lone bold 1 read as block 1. It may be a different big figure; no second figure is near.
- **SA-B14 (plate 38, block 7)**: the stem of the 7 lies on the lot line. Only 265 of its 628 box ink px are text (MEASURED); the rest is line or shared.
- **SA-B22 (plate 46, block 2)**: a lot line runs down the whole 2. 388 of 876 px are text (MEASURED).
- **SA-B12 (plate 35, block 4)**: a dense junction; the line ink in the 4 was split by eye from the builder's line rule, not traced stroke by stroke.
- **Dittos touching lines**:
  - SA-D07 (6, at 1151,5137, on the rail line): the tick on the line is don't care.
  - SA-D30 (9, 5548,1742): both ticks hang from a line. Rows 1738-39 are don't care, 1740-45 text.
  - SA-D39 (9, 7547,931): between two close lot lines.
  - SA-D22 (38): both marks touch the lot line.

  In these, how much of the mark is text depends on the 2 px rule. About 15-60% of their box ink is text (MEASURED per word).
- **Plate 6, 905-918, 4960-4975**: a stub under the rail line where the ditto row has a gap. It may be a ditto mark hidden by the line. It is not a target, and its ink is don't care (CARE).
- **Plate 66, the ditto column (DW12)**: each mark is a pair of short dashes stacked across the reading direction (a ditto turned 90 degrees). All 9 are taken as ditto marks.
  The column of short dashes beside the house run at x 3001 (45-47-49-...) belongs to the run's dashes, not to the dittos.
- **SA-F1**:
  - 76 of 475 words are flagged unsure. Most are small rotated lot dimensions and house runs.
  - Three marks are don't care (CARE): a 2-like mark between hooks at 4386,3318; a 9-like and an 8-like mark at the lot corners by 134 and 94.625; and small marks under the lot line by 60' (4700-4765, 3932-3952).
  - The hatch strokes beside the big O at 5260,3320 are don't care.
  - The big spaced letters of THEODORE (5120-5380, 3240-3480) are each labelled with an owner word but read only as letters (unsure).
  - The small building outline by 134 (4460-4513, 3874-3897) is tangled with 2.134; the crossings are don't care.
- **Story heights in SA-F1**: the trailing period of `2.` is text by convention. A few periods touch building walls and become don't care by the 2 px rule.
- **Readings** flagged unsure may be wrong in a figure; the mask does not depend on readings.

## Files

- annot/: hand inputs.
  - SA-B##.txt, DW##.txt and SA-F1.txt: annotations.
  - block_candidates.json, block_draw_order.json: block lists and draw.
  - ditto_windows.json, ditto_round_robin.json, ditto_list.json, ditto_boxes_measured.json: ditto windows, centres and measured boxes.
  - full_window.json: the full-crop draw.
  - crops_blocks.json, crops_ditto.json, crops_full.json: the crop lists merged into crops.json.
- build.log: the last build's output.
- ../scripts/: view.py, sheet.py, zsheet.py, combine.py (pictures, scan only); draw_blocks.py, builtup.py (draws); tick_pairs.py, ditto_boxes.py (ditto pointer and boxes); gen_ditto.py, merge_crops.py, build_truth_sa.py, common.py, snapline.py (builder); check_sa.py (check pictures).
- ../pics/: all pictures looked at.
- ../_second_copy/: a copy of scripts, annotations, crops.json, words.json and this README (masks and pictures not copied).
