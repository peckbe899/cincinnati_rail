# Sealed text truth, merged and cross-checked (26 Nov 2026)

This is the held-out truth for the final gate of the text finder. Nobody tunes on it.
It merges the two halves built by sealed builders A and B (bench_2026-11-26/text_fix/sealed_A/truth and sealed_B/truth, left unchanged).
A third agent (the cross-check) re-built both halves with one builder, checked them, and fixed clear errors here only.
No finder output, no bin 8 and no other method output was opened on any sealed plate, by any of the three.
No method was scored. score_text.py was run only on synthetic masks (below).

All numbers are MEASURED unless marked (e).

## What is here

114 crops on the 16 sealed plates: 6 9 52 56 58 63 (100 ft), 35 38 41 66 71 76 84 88 (200 ft), 46 92 (400 ft).

| | crops | target words | 100 ft | 200 ft | 400 ft |
|---|---|---|---|---|---|
| block numbers (SA-B01..26, SB-B01..26) | 52 | 52 | 18 | 24 | 10 |
| ditto marks (SA-D01..42, SB-D01..18) | 60 | 151 | 59 | 92 | 0 |
| full crops (SA-F1 plate 38, SB-F1 plate 56) | 2 | 645 words of all kinds | SB-F1 | SA-F1 | |

Ink size of the target words (ink pixels inside the word box):

| | words | median | min | max |
|---|---|---|---|---|
| block, 100 ft | 18 | 1,297 | 873 | 2,663 |
| block, 200 ft | 24 | 1,139 | 329 | 2,878 |
| block, 400 ft | 10 | 1,278 | 699 | 2,827 |
| ditto, 100 ft | 59 | 41 | 19 | 77 |
| ditto, 200 ft | 92 | 34 | 12 | 63 |

- The dittos are small: median 36 px over all 151; 28 of them have 26 px of ink or less. This is like plates 90 and 54A, not like T1-T7 (66 px).
- 38 of the 52 block numbers touch a line or have more than 5% of their box ink not text (crossed by a line).
- Pixels. Targeted crops, inside the scopes: text 100,474; not text 89,775; don't care 10,386. Full crops: text 163,510; not text 223,356; don't care 13,542.
- Words by kind, all crops (what score_text.py counts in "recall by kind"): lot 326, lotdim 235, ditto 170, house 154, story 115, owner 59, block 56, sewer 16, pipe 14, street 13, other 1.
  block and ditto include words that are not targets: the blocks 36 and 37 in SA-F1, block 8 in SB-F1, a block 4 in SB-D02, and 19 dittos (16 in SA-F1, one each in SA-B11, SA-B13, SB-B04).
  Block 36 of plate 38 was drawn by builder A's draw. It lies inside SA-F1, so it is labelled there and is not a target.
- stats.json has these counts.

## Format (score_text.py runs on it unchanged)

Same layout as text_v1/truth:
- crops.json: one entry per crop: plate, win [x0, y0, x1, y1], scale_ft_per_inch, kind ("targeted" or "full"), why, half ("A" or "B").
  Targeted crops also have target ("block" or "ditto"), scope_pad 25, and scope (the scope boxes, full-plate px, both ends included).
  Half A's ditto crops also have annot (the shared annotation file, SA-DW##) and target_lines.
  SB-F1 has line_bridge 4 (half B's extra line rule, used on that crop only).
- <id>_mask.png: uint8, the size of the window. 0 paper, 1 ink that is not text, 2 text ink, 3 don't care. Ink is Lab L < 140 on the paper mask.
- <id>_words.json: a dict with a words list. Each word has id, reading, kind, flags, target (true for the drawn targets), angle, height, length, poly, aabb, ink_px, text_px_final (its text pixels in the mask; what the scorer counts) and annot_line. Also scope, the hand ops (boxes, each with its own pixel effect) and dropped_outside_scope.
- Scope of a targeted crop: each target word's axis box grown by 25 px. All ink inside the scope is labelled. Outside it the mask is 3, paper too.
- annot/: the hand inputs. SA-*.txt and SA-DW##.txt (half A), SB-*.txt (half B), each with the cross-check's fixes at the end. selection_A/ and selection_B/ hold the seeds, candidate lists and draws of each half.

Scoring, from data/sanborn:

```
python -B bench_2026-11-25/text_v1/code/score_text.py "MASK_WITH_{plate}" --codes 2,3 --truth bench_2026-11-26/text_fix/sealed_final
python -B bench_2026-11-26/text_fix/sealed_check/scripts/target_recall.py "MASK_WITH_{plate}" --codes 2,3
```

- On the targeted crops, pooled P/R/F1 only measures what lies inside the scopes. The numbers that matter are recall by kind (pixels and words) and non-text ink called text inside the scopes.
- score_text.py counts every word of a kind. target_recall.py counts only the 203 target words, by kind and scale, with the same rules, plus non-text ink called text in the block scopes and in the ditto scopes.

Format check (synthetic masks only; sealed_check/format_check/):

| mask | score_text.py ALL | recall by kind | target_recall.py |
|---|---|---|---|
| the truth itself (mask == 2) | P 1, R 1, F1 1 | every kind 1.000, every word found | 52/52 blocks, 151/151 dittos, non-text called text 0 |
| all ink | P 0.457, R 1 | every kind 1.000 | 52/52, 151/151, non-text called text 1.0 |
| nothing | R 0 | every kind 0 | 0/52, 0/151 |

## Conventions (Ben has not answered; the given defaults)

- Text: letters, digits, ' " . - and the like, ditto marks, story heights, pipe and sewer labels.
- Not text: hydrants, manholes, hooks, arrows, rail ticks, and every line with its dashes (lot, block, building and street lines, and the pipe or sewer line beside its label).
- A block side through a row of house numbers stays a side.
- Where text ink and line ink touch, the ink within 2 px of the contact is don't care (the v2 shared-ink rule).
- A line through a big figure is not text; the glyph ink next to it is don't care.
- A ditto word is one mark: the pair of ticks, or one blob where the pair prints as one.
- Faint ink lighter than L 140 is paper, as in v2.

## How the targets were picked (details in each half's README, copied in annot/selection_A and selection_B)

- Block numbers: each builder listed every block number seen on each plate at 1/4 size. Each list was shuffled with random.Random(plate name). The first 3 per plate (5 on the 400 ft plates 46 and 92) that are block numbers at 1:1 were taken.
- Dittos: windows drawn at random in built-up areas (seed 'ditto-' + plate). Every ditto in the opened windows was taken (half A: 22 windows, 12 with dittos; half B: 46 windows, 18 with dittos).
- Full crops: placed at random in built-up areas (seeds 'SA-F1' and 'SB-F1').

## Bias check (cross-check)

- Skips. Half A skipped 2 drawn candidates, both on plate 38: block 36 (it lies inside SA-F1 and is labelled there) and "25?" (not a block number at 1:1). Half B skipped none. Nothing was skipped because it was hard.
- Hard cases are in. 38 of 52 block targets are crossed by a line or touch one. Thin or broken ones are in (block 2 and 11 on plate 46, block 4 on plate 92). Two are printed over a dense grid of small figures (blocks 8 and 5 on plate 92).
- The 1/4-size lists miss some crossed figures. A seeded check (random.Random('sealed-check-bias') chose plates 38 and 58; one quadrant each) found 12 listed block numbers and 1 missing one: a bold 6 on plate 38 at about 4220,2760, crossed by an alley line. So about 1 in 13 (e) block numbers is missing from the lists, and the miss was a hard one. It was not added: it is on no list, and one figure would not change the rate much.
- Dittos: tiny tick pairs are in (28 of 151 have 26 px of ink or less). No 400 ft ditto was found (plate 92 has almost none; on plate 46 they were in its 200 ft inset). A sweep of the 68 opened windows for isolated tick pairs that no ditto word covers found 3 candidates, none a ditto. The sweep only finds about 1 in 5 known dittos, so it is a weak check.

## What the cross-check did

1. Merged the halves and rebuilt every crop with one builder (sealed_check/scripts/build_final.py, a merge of both half builders, which are copies of the v2 builder). Rebuilt with each half's own scope rule, it gives back all 114 masks with 0 differing pixels.
2. Unified the scope. Half B's scope boxes left out their last row and column; now both ends are included, as in half A. This moved 14,833 px of the 44 half-B targeted crops from don't care to labelled. It is a format change, not a fix.
3. Looked at every target word at 4-8x, scan beside truth (52 block numbers, 151 dittos), and every 375 x 250 tile of both full crops at 2x, scan beside truth.
4. Ran its own checks (sealed_check/scripts): glyph-sized not-text pieces next to words and alone; pieces inside one word box carrying not-text pixels; glyph pieces cut by the scope edge; dash-like text pieces inside word boxes; walls crossing word boxes; readings. Every hit was looked at on zooms.
5. Fixed clear errors: 96 fixes in 24 annotation files. Each fix, its reason and its pixel count is in fixes_log.txt. In all, 6,562 px changed class in 24 crops (3,456 text to not text, 1,916 not text to text, the rest to or from don't care).

The fixes, in short:
- Line ink inside a target box was text: block 19 on 52 (SA-B08), block 22 on 52 (SA-B09), block 10 on 46 (SA-B25, the dashed edge of the alley band), a dash by block 22 on 71 (SB-B11).
- Glyph ink was not text: the 4 of lot 64 (SA-D21), a story 2 (SA-D15), the 2 of house 3552 (SB-D07), the lot 51 by block 21 (SB-B17, box 10 px too low), the 2 of lot 297 (SB-B25), lot 159 (SB-B18, box 45 px off).
- Words cut by the scope edge had not been typed, so their in-scope glyph ink was scored as not text. 27 such words were added, 24 of them in half B (lot numbers and lot dimensions round block numbers on plates 56, 63, 76, 84 and 88, story heights in ditto scopes, and the dense grids on 92).
- A building wall was text inside the box of the owner letter C (SA-D29).
- SA-F1: the hydrant circle was 19 px off the dot, so most of the dot was text; the foot of a big street letter entering the window was not text; a building wall in a story box was text.
- 53 dash or wall pieces inside word boxes were text, mostly in the two full crops: the dashes of the dashed street line under the house numbers on Ludlow Ave, the dashed party walls beside the lot dimensions in the pink buildings, the sewer and pipe line dashes beside their labels, and the walls of small buildings in the boxes of story heights and lot numbers.

Tried and rejected: a builder rule that peeled shorter straight runs (21 px) leaving a word box. On the before/after pictures it took italic glyph strokes as often as walls, so walls were fixed by hand ops instead.

## Known doubtful spots

From half A:
- SA-B15 (plate 38): a lone bold 1 read as block 1. It may not be a block number.
- SA-B14 (block 7 on 38) and SA-B22 (block 2 on 46): a line runs along the stem; less than half of the box ink is text.
- SA-B12 (block 4 on 35): a dense junction, split by eye.
- Dittos touching lines (SA-D07, SA-D22, SA-D30, SA-D39): how much is text depends on the 2 px rule.
- Plate 66, SA-D42: the 9 marks are pairs of short dashes stacked across the reading direction (a ditto turned 90 degrees). Taken as dittos.
- Plate 6, 905-918, 4960-4975: a stub under the rail line may be a hidden ditto. Don't care.
- SA-F1: 76 words flagged unsure; the big letters of THEODORE are read only as letters.

From half B:
- SB-B24 and SB-B25 (blocks 8 and 5 on 92): printed over a dense grid. Up to about 15% (e) of each figure's ink could fairly go either way. The cross-check added 8 partial lot numbers in these two scopes; their readings are guesses ('14?', '44?' ...).
- SB-B26 (block 4 on 92): thin and broken.
- Dittos SB-D14 (5253,4170) and SB-D16 (3222,4852): unsure.
- SB-F1: the spaced owner letters and some upward lot numbers may be misread. Readings do not change the mask.

From the cross-check:
- SA-F1, the 80 in a yellow building near 5620,3440: the 8 lies on two lines and is all not text. It may be partly text.
- The wall check still finds 69 places in the full crops (1,989 text px) where a text stroke runs on into a line outside the box. Of 7 looked at, most were glyph strokes beside a line, so most are not errors (e).
- The partial words added at scope edges have rough boxes outside the scope; only their in-scope part is scored.

## Remaining truth noise (estimate)

- Full crops: walls and dashes still labelled text inside word boxes, and glyph ink lost to lines: about 500 to 1,000 px (e), 0.3 to 0.6% (e) of their 163,510 text px.
- Targeted scopes: the two dense grids on plate 92 (about 400 px (e) either way) and a few glyph ends at scope edges (about 100 to 200 px (e)): about 0.5% (e) of the 100,474 in-scope text px.
- Line contacts: 10,386 in-scope px are don't care by the 2 px rule. They are not scored, so they are not noise, but Ben's convention decides them.
- Target words: 2 or 3 block targets (SA-B15, SB-B24, SB-B25) and about 12 dittos (SA-D42's 9 turned marks, 2 unsure, a few that touch lines) could change with a ruling from Ben (e).
- Overall, about 1% (e) of text pixels may be in the wrong class. That is smaller than the gaps the gate is about (block 0.89, ditto 0.33 pixel recall on H1-H4).

## Rebuild

From data/sanborn:

```
python -B bench_2026-11-26/text_fix/sealed_check/scripts/merge.py --force       # fresh copies of both halves' annotations
python -B bench_2026-11-26/text_fix/sealed_check/scripts/apply_fixes.py          # the cross-check fixes
python -B bench_2026-11-26/text_fix/sealed_check/scripts/build_final.py all      # masks and words
python -B bench_2026-11-26/text_fix/sealed_check/scripts/make_log.py             # fixes_log.txt, scopes in crops.json, stats.json
```

make_log.py needs sealed_check/v0_merged (the merged truth before the fixes) for its per-crop counts.

## Files

- crops.json, <id>_mask.png, <id>_words.json, stats.json, fixes_log.txt, this README.
- annot/: the hand inputs with the fixes; annot/selection_A and annot/selection_B: seeds, candidate lists, draws, windows.
- Check pictures, scripts and check lists: bench_2026-11-26/text_fix/sealed_check/ (pics/, scripts/, checks/, format_check/).
