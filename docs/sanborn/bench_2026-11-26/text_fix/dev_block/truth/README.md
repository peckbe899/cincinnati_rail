# Dev truth for BLOCK NUMBERS: 45 targeted crops (26 Nov 2026)

Targeted truth for the block-number fix of the text finder. Each crop is a small window round one block number. Only a
small scope round the number is scored. It is DEV truth: fixers may look at it and tune on it.

Everything was decided by eye on the scan. No finder output and no bin 8 was looked at while choosing or labelling.
The truth files were frozen (md5 in `freeze_md5.json`) before any method was scored. Nothing outside
`bench_2026-11-26/text_fix/dev_block/` was written.

## Files (same layout as text_v1/truth, so `score_text.py` runs unchanged)

- `crops.json`: one entry per crop: `plate`, `win` [x0,y0,x1,y1] (full-plate px), `scale_ft_per_inch`, `kind: "targeted"`,
  `target: "block"`, `scope_pad: 25`, `win_pad: 60`, `targets` (word ids), `readings`, `why`, and `draw` (the plate's
  seed and the candidate's place in the seeded order).
- `DB##_mask.png`: uint8, window size. Inside the scope: 0 paper, 1 ink that is not text, 2 text ink, 3 don't care.
  Outside the scope: 3 everywhere (paper too).
- `DB##_words.json`: as in truth v2 (`reading`, `kind`, `flags`, `angle`, `height`, `length`, `poly`, `aabb`,
  `snapped`, `touches_line`, `text_px`, `annot_line`), plus `in_scope` (text px, don't-care px and all ink px of the word
  box inside the scope). The target word has `target: true` and `ink_size_px` (its text + don't-care px). Other words
  are listed when their box reaches into the scope; `cut_by_scope` when part of the box lies outside it.
- `annot/DB##.txt`: the hand input (v2 format, plus a `#plate N` line and the flag `target`). Every hand op has its
  reason after it.
- `t17_block_words.json`: the 7 block words of truth v2 T1-T7 (ids and boxes only; their masks stay in text_v1/truth).
- `freeze_md5.json`: checksums of every truth file at the freeze.
- `build.log`: the last build of all 45 crops.

Window = the snapped target box grown by 60 px. Scope = the target box (its rotated rectangle) grown by 25 px (a 51 x 51
square). Ink is ink_bins' rule (Lab L < 140 on the paper mask), so the masks line up with N_bins.png and the finders.

## Conventions (Ben has not answered; the plan's proposals)

Ditto marks and story heights are text. Hydrants, manholes, hooks and rail ticks are not text. A block side through a
row of house numbers stays a side. Pipe and sewer labels are text. Where text ink and line ink touch, the ink within
2 px of the contact is don't care (v2's shared-ink rule, unchanged). Where a figure's stroke lies ALONG a line for its
whole length (the 4's crossbar on DB13, the 5's top bar on DB41, the 1 of 18 beside a wall on DB25), the shared rows are
don't care (CARE), and the rest of the figure is text.

## How the block numbers were chosen

1. **Plates.** 12 non-sealed plates, all three scales: 100 ft 3, 54A, 12; 200 ft 30, 19, 26A, 64A, 74, 60B; 400 ft 49,
   93A, 48. Plates 44, 1A and 5 were left out because T1-T7 and the finders' tuning already use them.
2. **Survey.** Each plate was viewed at 1/4 size in 2 x 2 tiles (`scripts/survey.py`, `pics/survey/sv_*.jpg`) and every
   block number seen was listed with a rough position (`candidates/N.txt`). Each list was checked on a contact sheet of
   the scan round every candidate (`scripts/cands.py`, `pics/survey/cand_*.jpg`); italic lot numbers, sheet numbers and
   adjoining-sheet numbers seen at 1/4 size were dropped there (listed as comments in the candidate files), and badly
   placed candidates were placed again on a closer crop. On plate 48 only the 400 ft drawing was used (the 200 ft
   insets were left out).
3. **Draw** (`scripts/draw.py`, `candidates/draw.json`). The number per plate was fixed first (5 per 100 ft plate,
   3-4 per 200 ft plate, 2-4 per 400 ft plate: 15 + 22 + 8 = 45). Each plate's candidate list was shuffled with
   `random.Random(PLATE)` (the seed is the plate name as a string) and the first K eligible ones were taken. Eligible:
   a window round it (centre +-160 px) does not overlap H1-H4. Only block 36 on 54A (inside H4) was skipped.
   All draws were kept, however hard: a figure crossed by lines, one inside a spaced owner name, one in a 400 ft
   block of narrow lots.
4. **Labelling.** A 3x scan zoom round each draw (`scripts/zoom.py`, `pics/zoom/DB##.png`); where the survey
   position was off, the figure was placed again by eye on a wider zoom (`candidates/proposed.json` notes which). The
   word line was typed from the zoom; every other word reaching the scope was typed too.
5. **Build** with a copy of the v2 builder (`scripts/build_dev.py`, `common.py`, `snapline.py`), adapted for targeted
   crops: the window and scope come from the snapped target box; outside the scope the mask is 3; words.json keeps only
   words reaching the scope. The v2 rules (snap, line rule, hand ops, shared-ink rule) are unchanged.
6. **Checks.** Every crop: scan beside truth at 4x with the scope outlined (`pics/check/DB##_check.png`). Every crop
   with lines near the figure: 5-9x zooms (`pics/check/tz_DB##_*.png`, scan beside truth; `pics/zoom/*_z*.png` with an
   ink panel). Then two sweeps for missed text that use only the scan and the truth: every glyph-sized piece the truth
   calls not text (`scripts/blue_check.py`, `pics/check/blue_sheet_*.png`) and every thin 10-30 px piece
   (`pics/check/blue_thin_sheet.png`). They found 13 missed small words (lot numbers and dimensions at scope edges on
   DB17, DB25, DB26, DB41), now boxed.

## The set (all MEASURED)

- 45 block numbers on 12 plates: 15 at 100 ft (plates 3, 54A, 12), 22 at 200 ft (30, 19, 26A, 64A, 74, 60B), 8 at
  400 ft (49, 93A, 48). Candidates listed: 25 + 56 + 55 at 100 ft, 28 + 41 + 44 + 26 + 19 + 42 at 200 ft, 47 + 7 + 9 at
  400 ft (399 in all).
- Text px per block number (truth 2 in its box): median 1043, range 370-2215. By scale: median 1043 (100 ft), 1304
  (200 ft), 792 (400 ft). Height: median 51 px (100 ft), 56 px (200 ft), 50 px (400 ft).
- 29 of 45 touch a line (the builder's touch test); 30 have don't-care px where a line meets them.
- 135 other words lie (partly) in the scopes: lot numbers, dimensions, story figures, owner letters, 2 ditto marks.
- Two targets are flagged `unsure`: DB26 (block 24 on 26A, overprinted by a band edge and building lines) and DB41
  (block 15 on 49, in a 400 ft block of narrow lots). In both the figure is certain; where its strokes end and the
  lines begin is not.

## Scores, for reference only (score_text.py and scripts/analyze.py agree to the pixel)

Run from data/sanborn:

```
python -B bench_2026-11-25/text_v1/code/score_text.py "unet_data/{plate}_bins.png" --codes 8 --truth bench_2026-11-26/text_fix/dev_block/truth
python -B bench_2026-11-26/text_fix/dev_block/scripts/analyze.py "bin8=unet_data/{plate}_bins.png:8" "finder3=A|B:2,3" ...
```

finder2 and finder3 masks: text_v1's own for plates 54A, 30, 60B, 49 and 93A; for 3, 12, 19, 26A, 64A, 74 and 48 they
were made for this check with `text_v1/code/finder3.py N --out dev_block/finders/finder3` and `finder3.py N --off`
(finder3 with the classifier off is finder2: on 93A it gives text_v1's finder2 mask with 0 px different).

**Block-number recall** (pixels: truth-2 px of the block number called text; words: half or more found):

| method | 100 ft (15) | 200 ft (22) | 400 ft (8) | all 45 | words under 0.9 | non-text ink called text, in scope |
|---|---|---|---|---|---|---|
| bin 8 | 0.855, 15/15 | 0.899, 21/22 | 0.909, 8/8 | **0.885, 44/45** | 17 | 0.309 |
| finder2 | 0.703, 8/15 | 0.796, 17/22 | 0.791, 7/8 | **0.764, 32/45** | 22 | 0.057 |
| finder3 | 0.740, 11/15 | 0.826, 20/22 | 0.791, 7/8 | **0.792, 38/45** | 23 | 0.049 |

On the 7 T1-T7 block words (t17_block_words.json; same scorer, truth v2): bin 8 0.893 (7/7), finder2 0.843 (6/7),
finder3 0.843 (6/7). Pooled in-scope pixel scores (P / R / F1): bin 8 0.852 / 0.859 / 0.856, finder2 0.966 / 0.778 /
0.862, finder3 0.971 / 0.797 / 0.876; on a targeted set these say little beyond the rows above.

So this dev set is harder for the finders than H1-H4 (finder3 0.891 there, 6 words) and T1-T7 (0.843, 7 words): 0.792
on 45 words. bin 8 is about the same on all three (0.885-0.902).

## How block numbers are lost (finder3 unless said; pictures in ../pics/loss/ and ../pics/loss_overview_*.png)

Each target's text ink was cut into pieces (8-connected; the don't-care band at a line splits a figure into pieces).
`scripts/glyphs.py`, `scores/glyph_pieces.json`:

| pieces of block-number ink | bin 8 found | finder2 found | finder3 found |
|---|---|---|---|
| figures free of lines (29) | 28 (px 0.994) | 28 (0.990) | 29 (0.998) |
| figures touching or crossed by a line (80) | 70 (0.867) | 42 (0.660) | 52 (0.719) |
| bar-like figure 1s, free (8) | 3 (0.493) | 6 (0.783) | 6 (0.783) |
| bar-like figure 1s, touching a line (9) | 8 (0.911) | 4 (0.457) | 3 (0.333) |

1. **A figure crossed by, or joined to, a line loses the part on the line side, often the whole figure.** This is
   most of the loss. Whole figures lost: the 0 of 30 joined to a wall and two building lines (DB10), the 2 of 23 with a
   lot line along its right side (DB16), the 2 of 28 on a lot line and a wall (DB07), the half of 6½ cut by a lot line
   (DB18), the 2 of block 2 on a junction of three lines (DB05), the upper loop of 8 under a slanting line (DB43), most
   of the 9 under a lot-line junction (DB12), the 4 of 47 whose crossbar lies along a lot line (DB13), both figures of
   24 under a band edge (DB26). Missed px within 3 px of a line: 3,444; missed px of whole strokes away from lines:
   5,965 (most belong to these same crossed figures); 1-2 px rims: 1,114.
2. **Bold figure 1s.** A 1 is a plain bar. finder3 lost 8 of 17 bar-like pieces: a lone 1 48 px tall at 400 ft (DB45,
   block 1: 0 px found; probable cause (e): it is longer than finder2's 12-45 px lone-stroke rule), a 1 grazed by a slanting lot line
   (DB42), a 1 collinear with a wall (DB25), a 1 beside a thin lot line in a dense 400 ft block (DB41), and the two
   bar-like halves of the 8 of 85 split by a lot line (DB35). The classifier took one more: the 1 of 15 on DB01,
   whose flag touches a rail tick; finder2 found it (word 1.00), finder3 turns it to other ink (word 0.72). Probable
   cause (e): finder3 keeps only free strokes (touching no line ink) out of the classifier's reach.
3. **bin 8 has the opposite weakness**: it misses free bold 1s (only 3 of 8 found; the 1 of 19 on DB02, of 14 on DB22
   and DB34) and the top of a 5 cut by a line (DB39), but keeps most crossed figures, at the cost of calling 31% of the
   line ink in the scopes text (finder3 4.9%).
4. Figures free of lines are found by every method (finder3 29 of 29 pieces).

## Known limits

- One labeller, by eye; no second check yet. Edges of strokes along a line are a judgement (rule: rows shared with
  the line are don't care).
- Readings are certain for all 45 targets; some neighbour words are `unsure` (small lot numbers at 400 ft, the letter
  next to block 8 on 93A).
- The lists were made at 1/4 size: a block number very faint or hidden under a line may not have been listed at all
  (estimate: a few per plate, (e)). Plates with insets at another scale (48) used the main drawing only.
- The draw per plate is random, but the plates were chosen by me from the suggested list (not drawn).
- 13 small neighbour words at scope edges were only found by the two missed-text sweeps; others of that kind may remain
  (estimate: under 1% of the in-scope text px, (e)). They do not affect block recall.

## All 45 crops (recall = share of the block number's text px called text)

| crop | plate | ft | block | text px | care px | touches a line | other words in scope | bin 8 | finder2 | finder3 | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| DB01 | 3 | 100 | 15 | 1199 | 9 | yes | 0 | 0.83 | 1.00 | 0.72 |  |
| DB02 | 3 | 100 | 19 | 1043 | 0 | no | 0 | 0.75 | 1.00 | 1.00 |  |
| DB03 | 3 | 100 | 9 | 792 | 0 | no | 0 | 1.00 | 1.00 | 1.00 |  |
| DB04 | 3 | 100 | 8 | 745 | 178 | yes | 4 | 1.00 | 0.35 | 0.73 |  |
| DB05 | 3 | 100 | 2 | 477 | 139 | yes | 4 | 0.95 | 0.20 | 0.20 |  |
| DB06 | 54A | 100 | 4 | 771 | 0 | no | 1 | 1.00 | 1.00 | 1.00 |  |
| DB07 | 54A | 100 | 28 | 1236 | 316 | yes | 0 | 0.85 | 0.49 | 0.49 |  |
| DB08 | 54A | 100 | 5 | 668 | 110 | yes | 1 | 1.00 | 0.89 | 0.89 |  |
| DB09 | 54A | 100 | 8 | 874 | 64 | yes | 1 | 0.99 | 0.99 | 0.99 |  |
| DB10 | 54A | 100 | 30 | 1605 | 126 | yes | 3 | 0.81 | 0.32 | 0.32 |  |
| DB11 | 12 | 100 | 38 | 1745 | 215 | yes | 0 | 0.74 | 0.99 | 0.99 |  |
| DB12 | 12 | 100 | 9 | 887 | 205 | yes | 3 | 0.70 | 0.28 | 0.55 |  |
| DB13 | 12 | 100 | 47 | 1465 | 412 | yes | 5 | 0.89 | 0.41 | 0.41 |  |
| DB14 | 12 | 100 | 55 | 1427 | 337 | yes | 1 | 0.57 | 0.36 | 0.67 |  |
| DB15 | 12 | 100 | 20 | 2215 | 8 | no | 3 | 1.00 | 1.00 | 1.00 |  |
| DB16 | 30 | 200 | 23 | 1461 | 189 | yes | 9 | 0.96 | 0.42 | 0.42 |  |
| DB17 | 30 | 200 | 15 | 1043 | 202 | yes | 8 | 0.90 | 0.89 | 0.89 |  |
| DB18 | 30 | 200 | 6½ | 1827 | 159 | yes | 8 | 0.90 | 0.47 | 0.55 |  |
| DB19 | 30 | 200 | 2 | 900 | 0 | no | 0 | 1.00 | 1.00 | 1.00 |  |
| DB20 | 19 | 200 | 28 | 1472 | 39 | yes | 2 | 0.91 | 1.00 | 1.00 |  |
| DB21 | 19 | 200 | 41 | 1067 | 0 | no | 0 | 1.00 | 1.00 | 1.00 |  |
| DB22 | 19 | 200 | 14 | 863 | 0 | no | 2 | 0.73 | 1.00 | 1.00 |  |
| DB23 | 19 | 200 | 34 | 1483 | 0 | no | 2 | 1.00 | 1.00 | 1.00 |  |
| DB24 | 26A | 200 | 39½ | 1946 | 0 | no | 0 | 0.95 | 1.00 | 1.00 |  |
| DB25 | 26A | 200 | 18 | 1288 | 320 | yes | 10 | 0.58 | 0.68 | 0.68 |  |
| DB26 | 26A | 200 | 24 | 1174 | 260 | yes | 8 | 0.48 | 0.03 | 0.07 | unsure |
| DB27 | 26A | 200 | 46 | 1723 | 194 | yes | 7 | 0.94 | 0.82 | 0.82 |  |
| DB28 | 64A | 200 | 10 | 757 | 106 | yes | 9 | 0.90 | 0.80 | 0.89 |  |
| DB29 | 64A | 200 | 9 | 725 | 3 | yes | 3 | 1.00 | 0.99 | 0.99 |  |
| DB30 | 64A | 200 | 21 | 941 | 0 | no | 1 | 1.00 | 1.00 | 1.00 |  |
| DB31 | 64A | 200 | 2 | 652 | 50 | yes | 0 | 1.00 | 0.98 | 0.98 |  |
| DB32 | 74 | 200 | 8 | 1377 | 0 | no | 1 | 1.00 | 1.00 | 1.00 |  |
| DB33 | 74 | 200 | 2 | 800 | 159 | yes | 4 | 1.00 | 0.31 | 0.74 |  |
| DB34 | 74 | 200 | 14 | 1321 | 0 | no | 1 | 0.72 | 1.00 | 1.00 |  |
| DB35 | 60B | 200 | 85 | 1436 | 276 | yes | 4 | 0.95 | 0.48 | 0.63 |  |
| DB36 | 60B | 200 | 86 | 1522 | 0 | no | 0 | 1.00 | 1.00 | 1.00 |  |
| DB37 | 60B | 200 | 79 | 1320 | 163 | yes | 6 | 0.90 | 0.80 | 0.80 |  |
| DB38 | 49 | 400 | 2 | 615 | 48 | yes | 1 | 1.00 | 0.99 | 0.99 |  |
| DB39 | 49 | 400 | 5 | 666 | 35 | yes | 0 | 0.70 | 0.99 | 0.99 |  |
| DB40 | 49 | 400 | 4½ | 1038 | 0 | no | 0 | 0.89 | 0.96 | 0.96 |  |
| DB41 | 49 | 400 | 15 | 1249 | 558 | yes | 18 | 0.82 | 0.64 | 0.64 | unsure |
| DB42 | 93A | 400 | 13 | 878 | 28 | yes | 2 | 0.94 | 0.64 | 0.64 |  |
| DB43 | 93A | 400 | 8 | 806 | 108 | yes | 3 | 1.00 | 0.83 | 0.83 |  |
| DB44 | 48 | 400 | 5 | 778 | 0 | no | 0 | 1.00 | 1.00 | 1.00 |  |
| DB45 | 48 | 400 | 1 | 370 | 0 | no | 0 | 1.00 | 0.00 | 0.00 |  |

The T1-T7 block words are listed in `t17_block_words.json` (T1-045 4, T1-165 14, T2-081 17, T2-135 18, T3-002 24,
T6-095 15, T7-163 28). Score them on text_v1/truth with `--crops T1,T2,T3,T6,T7`.
