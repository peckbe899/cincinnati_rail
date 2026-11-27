# Sealed held-out text truth, half B (26 Nov 2026)

Built by sealed builder B for the final gate. Plates: 56, 58, 63 (100 ft), 71, 76, 84, 88 (200 ft), 92 (400 ft).
Nobody tunes on this. No finder output, no bin 8, no words or shapes output and no other method output was opened on
any plate while choosing or labelling. No method was scored. Only the scans and paper masks of the 8 plates above were read.

## What is here

| | crops | target words | 100 ft | 200 ft | 400 ft |
|---|---|---|---|---|---|
| block numbers (SB-B01..B26) | 26 | 26 | 9 | 12 | 5 |
| ditto marks (SB-D01..D18) | 18 | 83 | 21 | 62 | 0 |
| full crop (SB-F1, plate 56) | 1 | (170 words, all kinds) | yes | | |

All counts MEASURED (scripts/stats.py, stats.json). 19 of the 26 block numbers and 12 of the 83 ditto marks touch a line
(builder's touches_line flag).

Ink size of the target words (ink px inside the word box, MEASURED):

| | words | median | min | max |
|---|---|---|---|---|
| block, 100 ft | 9 | 1,103 | 873 | 2,663 |
| block, 200 ft | 12 | 1,247 | 971 | 2,878 |
| block, 400 ft | 5 | 1,694 | 727 | 2,827 |
| ditto, 100 ft | 21 | 39 | 19 | 53 |
| ditto, 200 ft | 62 | 34 | 12 | 50 |

Mask pixels over all 45 crops (MEASURED): text 102,908; not-text ink 132,268; don't care 6,436,994 (most of it is
outside the scopes); paper 1,867,030. SB-F1 alone: text 46,057; not-text ink 84,949; don't care 2,033.

## Format (score_text.py runs on it unchanged)

Same layout as text_v1/truth: crops.json, `<id>_mask.png` (uint8: 0 paper, 1 non-text ink, 2 text ink, 3 don't care),
`<id>_words.json` (dict with a `words` list: id, reading, kind, flags, angle, height, length, poly, aabb, snapped,
touches_line, text_px, annot_line, plus `target` (true/false), `ink_px` and `text_px_final`), annot/ (hand inputs).

- crops.json, targeted crops: `"kind": "targeted"`, `"target": "block"` or `"ditto"`, `"scope_pad": 25`, `"scope"`
  (the scope boxes, full-plate px), plate, win, scale_ft_per_inch, why. The full crop: `"kind": "full"`, `"line_bridge": 4`.
- Scope of a targeted crop = the axis box of each target word (of its snapped rotated box) grown by 25 px each side.
  Inside the scope all ink is labelled; outside it the mask is 3 (paper too).
- Words: every target word plus every other word that reaches into a scope, with kinds. The scorer's recall by kind
  counts all words, so `block` also holds two non-target block numbers (the 4 in SB-D02, the 8 in SB-F1) and `ditto`
  one non-target ditto (in SB-B04). For target-only numbers, filter on `"target": true` in the words files.
- Kinds are the builder's: street, house, lotdim, lot, block, owner, bldg, story, pipe, sewer, rail, adj, ditto, other.
- Ditto reading is `"`; a ditto word is one mark (the tick pair, or one blob where the pair prints as one).

Scoring, from data/sanborn:
`python -B bench_2026-11-25/text_v1/code/score_text.py "MASK_WITH_{plate}" --codes 2,3 --truth bench_2026-11-26/text_fix/sealed_B/truth`.
Format check (MEASURED): the truth's own text (mask==2) scored as a binary mask gives P = R = F1 = 1.0000 and every word
found (format_check/self_check.json). That is the only scoring that was run.

## Conventions (Ben has not answered; as given)

Ditto marks and story heights are text. Hydrants, manholes, hooks, arrows and rail ticks are not text. A block side
through a row of house numbers stays a side. Pipe and sewer labels are text; the pipe or sewer line and its dashes beside
or under the label are not. Where text ink and line ink touch, the ink within 2 px of the contact is don't care (the v2
shared-ink rule). Lines crossing a big figure: the line ink is not text, the line ink next to the glyph is don't care.

## How the targets were picked (seeds and lists in annot/selection.json)

Script: scripts/select_targets.py. Everything is seeded; the lists are complete.

**Block numbers.** Each plate was viewed at 1/4 size (pics/ov_P_RC.jpg) and every block number seen was listed with a
rough position (the `CANDS` table in select_targets.py, copied to selection.json; `?` = maybe not a block number). Each
list was shuffled with `random.Random(PLATE)` and the first K taken (K = 3 on the 100 and 200 ft plates, 5 on 92). Every
drawn candidate checked out at full size, so none was skipped. Drawn order (first K taken):

- 56 (23 listed): **16 17 12** 10 22 9 2 12½ 19 5 23 24 1 14 7 4 3 6 20 18 8 21 11
- 58 (61 listed): **36 20 51** 34 54 6 27 42 40 28 48 23 62 10 13 38 37 12 16 25 29 61 35 58 53 47 21 24 7 60 43 33 19 46 49 2 8 9 41 14 45 31 30 11 4 18 55 3 56 26 5 32 17 57 44 22 15 52 39 50 59
- 63 (31 listed): **15 18 21** 9 14 7? 2 17½ 26 25 12 6 27 23 20 8 19 11 24 28 3 4 30 22 5? 1? 13 16 17 31 29
- 71 (25 listed): **5 22 17** 14 16 6 7 19 12 13 11 8 10 2 9 24 15 25 21 1 3 23 18 20 4
- 76 (93 listed): **57 82 5** 51 97? 62? 39 38 ... (full list in selection.json)
- 84 (39 listed): **17 21 18** 39 25 24 4? 20 28 ... 
- 88 (33 listed): **6 27 13** 27B 17 32 19 29 20 9 ...
- 92 (14 listed): **12 13 8? 5? 4?** 14 15 7? 3 11 1 2 9 10 (the three `?` were confirmed as block numbers at full size)

The draw took them as they come: crossed by lot lines (56-16, 58-20, 58-51, 63-21, 71-5, 71-17, 76-57, 76-82, 76-5,
84-17, 84-21, 84-18, 88-6, 92-12), touching dashed boundaries (71-22), printed over a dense grid of small figures
(92-8, 92-5), thin and broken (92-4), and clean ones (63-18, 88-27, 88-13, 92-13).

**Built-up areas.** 250 x 250 px cells, 95% or more on the paper mask, with 5% or more coloured building fill (pink or
yellow by hue and saturation on the 1/4-size scan). Cells per plate (MEASURED): 56: 485, 58: 723, 63: 453, 71: 305,
76: 713, 84: 495, 88: 251, 92: 47.

**Ditto windows.** 500 x 400 px windows centred on a random point of a random built-up cell, `random.Random('ditto-PLATE')`,
kept if 99% on paper and not overlapping the full crop or an earlier window. Drawn in rounds of 2 windows per plate
(1 on 92). Rounds 1-3 were opened (6 windows per 100/200 ft plate) and plate 92 rounds 1-4 (4 windows); the round-4
windows of the other plates were drawn (`--rounds 4`) but never opened or used. Every ditto mark with any part inside an
opened window was taken. Windows by plate, in draw order (x0,y0,x1,y1), with the crop that holds their dittos:

| plate | w1 | w2 | w3 | w4 | w5 | w6 |
|---|---|---|---|---|---|---|
| 56 | 5748,2102: 0 | 9452,355: 0 | 6774,143: 0 | 8223,1856: 2 (D04) | 601,1430: 0 | 916,2439: 0 |
| 58 | 832,4575: 0 | 1384,3167: 6 (D01) | 7408,3279: 0 | 1029,203: 0 | 1864,551: 5 (D02) | 2583,2255: 8 (D03) |
| 63 | 7789,1374: 0 | 7272,829: 0 | 2101,3681: 0 | 4448,1789: 0 | 2064,2744: 0 | 6511,2982: 0 |
| 71 | 7019,6062: 0 | 4959,4799: 0 | 5035,2513: 2 (D05) | 3789,2473: 6 (D06) | 1810,1102: 8 (D07) | 3165,2810: 1 (D08) |
| 76 | 6182,2632: 0 | 3347,664: 3 (D09) | 1556,4757: 5 (D10) | 5394,1233: 1 (D11) | 1328,1330: 4 (D12) | 6836,1552: 7 (D13) |
| 84 | 5246,4012: 2 (D14) | 7349,5188: 1 (D15) | 2659,744: 0 | 3817,628: 0 | 7227,3504: 0 | 2910,4692: 18 (D16) |
| 88 | 6089,5625: 0 | 6858,2705: 2 (D17) | 909,2151: 0 | 2037,1827: 0 | 8238,6170: 0 | 3988,1824: 2 (D18) |
| 92 | 8441,2399: 0 | 8793,1780: 0 | 4829,4128: 0 | 7961,4835: 0 | | |

Each D crop's window is the random window grown by 40 px. Dittos were found by eye on 2x views of every window
(pics/dw_P_N.jpg) and 3-5x zooms, then a completeness sweep (scripts/ditto_sweep.py: pairs of small isolated ink pieces,
118 candidates looked at on pics/ditto_sweep.jpg) found 2 more on the lower edge of 71 w4 (added to SB-D06). No ditto was
found on plate 92 (400 ft) in 4 windows; 92 is mostly open land (47 built-up cells).

**Full crop.** `random.Random('SB-F1')` chose plate 56, then a built-up cell, then the window 3236,2670-4736,3670
(1500 x 1000, x by y), accepted on the first try. It does not overlap any targeted crop on 56.

## How it was labelled

- Builder: scripts/build.py, a copy of text_v1/truth-fix/scripts/build_truth_v2.py (the original is kept beside it as
  build_truth_v2_orig.py) with common.py and snapline.py copied. Same annotation syntax, snap, line peel, hand ops
  (EXCL, FORCE, CARE, CAREDIR, CARELINE, NOTTEXT, FORCELINE, EXCLCIRC) and shared-ink rule. Changes: paths; bin 8 removed
  (common.bins() deleted, check pictures show no method output); the `target` flag; the scope (outside = 3); ink_px and
  text_px_final per word; zoom check pictures; and for SB-F1 only (`line_bridge: 4`) an extra line peel: ink on a straight
  run of 121 px or more once gaps up to 8 px along the run are bridged is line ink. Without it the thin, broken street,
  pipe and building lines under labels on plate 56 were text inside word boxes (4,800 px moved, MEASURED; the places were
  checked at 6x and are lines: the street line under 12"W.P., the pipe line beside 12"W.PIPE, lot lines through 19, 20 and
  the block 8).
- Hand input: annot/_blocks_src.txt and annot/_dittos_src.txt (one section per crop, split into annot/<id>.txt by
  scripts/split_annot.py), annot/SB-F1.txt. Every hand fix carries a comment with its reason.
- Words were typed as centre lines (x1 y1 x2 y2 h) from 3x zooms with a 10 px grid, checked against the ink pieces
  (scripts/comps.py, ditto_pieces.py). Lines through glyphs were placed with snapline.py.
- Checks: every target at 4-8x, scan beside truth (pics/chkB_*.jpg, chkD_*.jpg, work/<id>_zoom.png, cz*.png); the other
  ink in every scope by an uncovered-piece pass (scripts/scope_pieces.py, scope_view.py; pics/sv_*.jpg); SB-F1 on 1.5x
  tiles scan beside truth (work/SB-F1_check_RC.jpg) and a leftover pass of every glyph-sized piece no word covers
  (scripts/full_view.py, work/SB-F1_lab_RC.jpg), with 3-6x zooms where in doubt (pics/zF*.jpg, cz7-9.png).
- Rebuild: `cd data/sanborn; python -B bench_2026-11-26/text_fix/sealed_B/scripts/make_crops.py;
  python -B bench_2026-11-26/text_fix/sealed_B/scripts/build.py all --check; python -B .../scripts/stats.py`.

## Known doubtful spots

- SB-B24 (block 8 on 92) and SB-B25 (block 5 on 92): the big figure is printed over a grid of tiny lot numbers, lot
  lines and arrows. The grid lines through the figure were made not text; three arrows are don't care; ten small lot
  numbers are flagged unsure. The figure's pixel recall there depends on where the grid lines are cut (estimate: up to
  15% of the figure's ink could fairly be called either way).
- SB-B26 (block 4 on 92): thin and broken; only part of the printed figure is darker than L 140.
- SB-B15 (block 5 on 76): two curved marks between 31.01' and the 5 are don't care (bracket or arc, cannot tell); an
  arrow tip is not text.
- SB-B11 (block 22 on 71): a round dot under the first 2 is don't care (period or speck).
- SB-B14 (block 82 on 76): the 8 is printed over the last figure of lot 261 (reading 261 unsure).
- Crossed block numbers: where a lot line runs along or beside a stem (the 1 of 17, of 18 and of 21 on 84)
  the line was cut out as not text by hand; a 1-2 px edge of the stem may be on either side.
- Dittos: SB-D14 second mark (5253,4170, a mark in a small yellow building, maybe a ditto, maybe a story tick), SB-D16
  mark at 3222,4852 (prints like a small x) are flagged unsure. A mark under lot 8 on 84 (7809-7823, 5347-5363) was
  first typed as a ditto and is now don't care, not a target.
- Dittos that sit on the edge of a random window (58: 1862,646; 71: 4081-4166, 2872) were taken.
- SB-F1 readings flagged unsure: the spaced owner letters (V.B.GIBSON'S is my guess for V, B., G, B, S, O, N, ', S; the
  left group ends N'S), the lot numbers 162 and 168 written upwards in narrow lots, 113, 161, 166, 4', 40.02' (partial),
  56 (now 56.46'). ALVIN and an ST. lie mostly right of the crop edge. A ⊥-shaped mark at 4696-4721, 2774-2817 and a
  tick at 3622-3627, 2887-2899 by the pipe valve were left not text; the hydrant dot is not text.
- Faint ink lighter than L 140 is in no class (paper), as in v2.

## Time

About 51 min wall clock in all, 19:21-20:12 by the system clock (MEASURED). The split is an estimate: reading and
selection 10 min, block numbers 12 min, ditto marks 13 min, full crop 12 min, README and copies 4 min.

## Files (all under bench_2026-11-26/text_fix/sealed_B/)

- truth/: crops.json, SB-*_mask.png, SB-*_words.json, stats.json, README.md, annot/ (hand inputs, selection.json with
  all seeds, candidate lists and draws, selection_round1.json, ditto_windows.json).
- scripts/: select_targets.py, build.py, build_truth_v2_orig.py, common.py, snapline.py, make_crops.py, split_annot.py,
  view.py, sheet.py, overview.py, comps.py, ditto_pieces.py, ditto_sweep.py, scope_pieces.py, scope_view.py,
  chk_targets.py, cz.py, full_view.py, stack.py, stats.py.
- work/: zoom check pictures per crop, SB-F1 check and leftover tiles. pics/: overviews, window views, check sheets.
- format_check/self_check.json: the format check above.
- _second_copy/: copies of scripts/, truth/ (masks, words, crops, annotations, README, stats).
