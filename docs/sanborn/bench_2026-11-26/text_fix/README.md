# Text fix: block numbers and ditto marks (26-27 Nov 2026)

Follow-up to text_v1 (docs/sanborn/bench_2026-11-25/text_v1/). There, finder3 missed block numbers crossed by lines
(0.891 against a 0.95 target) and two thirds of the ditto marks (0.332). This round fixed both on copies. No repo
tool, no file of Ben's and nothing in the batch outputs was changed. Nothing was downloaded and no U-net was trained.

The full agent reports are in findings_full.md. The working data is in data/sanborn/bench_2026-11-26/text_fix/
(3.5 GB). This folder is the second copy of its scripts, scores, truth masks, the frozen finder4 models, the block
readings and a few key pictures.

Conventions: Ben has not answered them yet, so this round used the plan's proposals.
- Ditto marks and story heights are text.
- Hydrants, manholes, hooks, arrows and rail ticks are not text.
- Ink within 2 px of a text-line contact is don't care.
- A line through a big figure is not text.

## What was built

- Dev truth, on plates that are not sealed:
  - 45 block numbers on 12 plates (dev_block/truth);
  - 200 ditto marks on 20 plates (dev_ditto/truth);
  - 73 marks that are not dittos: rail ticks from rail_ben.json on 44, dashes, hooks and line ends (dev_ditto/negatives).
- A new sealed held-out set on 16 plates that no text step had touched: 6 9 52 56 58 63 (100 ft), 35 38 41 66 71 76
  84 88 (200 ft), 46 92 (400 ft).
  - Two agents labelled it in halves. A third cross-checked, merged and fixed it (96 fixes, each in fixes_log.txt).
  - It holds 52 block numbers, 151 ditto marks and two full crops: SA-F1 on plate 38 and SB-F1 on plate 56. The final
    truth is sealed_final/.
  - Targets were drawn at random, seeded by plate name. No drawn target was skipped for being hard.
- Block fix A (geometry): it fits the lines crossing a figure from the ink outside its box, takes out only each line's
  own width, and gives the figure ink back to text.
- Block fix B (recognition): it reads the digits on thick ink, so a thin line through a figure does not hide it. It
  writes N_blocks.json with each reading, its box and flags.
- Ditto fix: it finds pairs of short ticks in rows, near figures, or strong pairs alone. Four dash tests come first.
  A mark must have paper all round it, so rail tick ends are never taken.
- finder4 = finder3, then the ditto fix, then both block fixes. B's changes are taken first, then A's wherever B left a
  pixel alone. It was frozen (integrate/FROZEN.txt holds the sha256 of every file) before any sealed plate was run.
  - Command, from data/sanborn:
    `python -B bench_2026-11-26/text_fix/integrate/code/finder4.py N --out DIR`
  - It takes 1.5 to 7 minutes a plate. Block fix A is the slow part.

## Gate on the sealed set (targets set before the run)

| gate | target | finder3 | finder4 | verdict |
|---|---|---|---|---|
| 1. Block numbers, pixel recall | >= 0.95 | 0.760 | 0.917 | FAIL |
| 1. Block numbers, words found | >= 95% | 39/52 | 49/52 (94.2%) | FAIL (one word short) |
| 2. Ditto marks, pixel recall | >= 0.90 | 0.625 | 0.822 | FAIL |
| 2. Ditto marks, words found | >= 90% | 87/151 | 127/151 (84.1%) | FAIL |
| 3. Full crops: F1 no worse than -0.002 | | 0.8901 | 0.8908 | pass |
| 3. Full crops: non-text ink called text, rise <= 0.3 points | | 4.408% | 4.492% | pass |
| 3. Full crops: street names, pixel recall | >= 0.95 | 0.921 | 0.929 | FAIL (finder3 fails it too) |
| 3. Full crops: street names, words | >= 95% | 9/9 | 9/9 | pass |
| 3. Full crops: straight-run proxy not higher | 474 px | 474 | 504 | FAIL (19 of the 30 px are a crop-edge artifact) |
| 4. Ben's line ink called text on 44, 1A, 5 (3 px) | <= 0.5% | 0.43% max | 0.459% max | pass (in-sample) |
| 4. No rail tick or streetcar dash newly taken | none | | none of 9 new blobs | pass (in-sample) |
| 5. H1-H4 F1 no worse than -0.002 | | 0.9269 | 0.9302 | pass (already seen) |

Overall: FAIL. finder4 is much better than finder3 on every sealed measure, but it misses the block and ditto targets.

My own check (27 Nov): I re-scored the sealed set with separate code (verify/verify_fix.py, not the gate's,
the skeptic's or score_text.py; output in verify/verify_fix_out.json). It gives every number in the table exactly: block 0.9169 and 49/52, ditto 0.8220 and
127/151, full-crop F1 0.8908, non-text 4.492%, streets 0.9291. My word fill equals the builder's count on all 1,159
words. H1-H4 re-scored the same way gives 0.9269 and 0.9302. The gate's finder4 masks for plates 6 and 38 have the
same sha256 as the skeptic's fresh runs of the frozen tool.

By scale (finder4):
- Block numbers: 100 ft 0.936 (17/18), 200 ft 0.920 (23/24), 400 ft 0.865 (9/10).
- Dittos: 100 ft 0.746 (44/59), 200 ft 0.881 (83/92). The set has no 400 ft dittos.

## Why things are still missed

- Block numbers: figure strokes that run along a lot or block line, or are crossed by one, stay line ink.
  - Numbers not crossed by a line: 14/14 found, pixel recall 1.000.
  - Crossed numbers: 35/38 found, pixel recall 0.881.
  - Thin figures: 0.799.
  - The three misses: the 19 on plate 52 (a thin figure on a lot-line crossing), the 19 on plate 66 (its 1 stands
    against a vertical line), and the 5 on plate 92 (its top bar lies on a grid line).
- Dittos: the old cause is fixed. Tiny tick pairs went from 0.227 to 0.967 (27/28). The new causes are:
  - marks touching a line: 15/25 found. The ditto fix needs paper round a mark, so by design it can never take these;
  - one-blob marks with no row of like marks: 16/31 found. Plate 6 alone has 9 misses, in brick buildings.
  - The dev set hid this. At 100 ft, 2% of dev dittos touch a line and 7% are one blob; in the sealed set it is 27%
    and 29%.

## Skeptic

- No verdict is overturned by its letter.
- Gate 1 is closer than it looks. Words from one plate are not independent. By plate, the 95% range of pixel recall
  is 0.870-0.960, and finder4 meets both targets in 8-10% of draws.
- Gate 2's FAIL is firm. It needs 9 more words.
- Gate 3 is a FAIL by its letter, but not harm. finder3 fails the street bar too, and finder4 improves on it. 19 of the
  30 straight-run px come from cv2's default border, which counts the outside of a crop as ink. With the real plate ink
  beyond the edge, the rise is 11 px. I checked that the gate's code uses cv2's default border.
- The no-harm tests have little power. 96% of finder4's 302,899 changed px on the sealed plates lie outside every
  scored area. A seeded eye sample puts about 12.5% of those px wrong, and up to 37.5% if every unsure piece is wrong.
  Most wrong px come from block fix A, on curved outlines (a creek bank, 724 px), building walls and ornaments.
- No leak was found: no sealed path, plate id, window or command line appears in 3,750 dev and fixer files. The freeze
  came before the H1-H4 scoring.

## Step 4 re-run (hand-off on 44, 5 and 1A, with finder4's mask)

- Block 28 on 44: mostly back in text. Its 8 goes from 0% to 60% text.
- Block 15 on 1A: not fixed. Its tall 1, crossed by lines, was rejected by block fix B as "lone 1: thick ink round
  it", and it still goes to the pipe bin. The 138 px streetcar error through the 15 stays.
- Outlines on 44 and 1A are byte-identical to the finder3 runs. Plate 5 is a little better.
- "No worse anywhere" still fails. Almost every loss is the hand-off's own and is the same with finder3. finder4's own
  extra harm is 4 px of Ben's streetcar track on 44 (at the foot of the N of AVENUE) and 2 px more of a false
  railroad track on plate 5.
- finder4's moves in the 44 ink bins: 13,423 px. By eye, 57 of 77 sampled pieces are right. The wrong ones are a round
  symbol in the corner, a solid disc, a thin line through KNOWLTON split into sewer dashes, and one dash.

## Ditto and dash notes

- The ditto fix sometimes takes a dash of a dashed lot line: 2 of 15 sampled on plate 5, 1 on SA-F1, 1 on 44 and 1 on
  plate 66. No rail tick and no streetcar dash was taken.
- The 73 dev negatives are unchanged by finder4.

## Open for Ben

1. Keep finder4 as the working text finder while the fixes go on, or keep finder3? (Nothing goes into the repo
   tools without his say-so.)
2. Ditto rulings that decide the 100 ft result:
   - Is a ditto that touches a line text, or don't care? This affects 11 of the 24 misses.
   - Are the one-blob marks in plate 6's brick buildings dittos?
   - Are the marks beside the plate 6 railroad ticks dittos (skeptic/pics/p6_rail_dittos.png)?
   - Are the stacked short dashes in plate 66's ditto column dittos?
3. Is "never a dash" strict for dashed lot lines too, or only for rail and streetcar?
4. Block fix A: keep it for recall (dev 0.909 with it, 0.850 without), or ask for a version that refuses curved
   strokes, walls and ornaments?
5. Is a figure stroke running along a line line ink or don't care? The truth sets and Ben's line check disagree.
6. Should the next fix go after big lone figures crossed by lines, like the 1 of block 15 on 1A?
7. Before the next gate:
   - a fresh held-out set (this one is now used);
   - the straight-run proxy fixed at crop edges;
   - street recall counted on street letters only;
   - more full crops where finder4 changes a lot (plate 76), or a seeded eye sample of whole-plate changes.
8. About 10 minutes on sealed_check/pics/diff/fix1_00-02.png and fix2_00.png would confirm the 96 sealed truth fixes.
9. Deleting bulky intermediates later, about 2 GB in all (re-makeable runs, copies of finder3 masks and check
   pictures). Nothing has been deleted.

## Folder

- code is in each agent folder: */code/ or */scripts/. finder4 and its three post-steps are in integrate/code/, and
  the models it uses are in integrate/models/.
- Truth masks: dev_block/truth, dev_ditto/truth, dev_ditto/negatives, sealed_final.
- Block readings on whole plates: gate/out/finder4/N_blocks.json (16 sealed plates) and integrate/out/finder4/ (10 dev
  plates).
- Scores: */scores/. The gate verdicts are in gate/scores/gate_verdicts.json.
- Key pictures: gate/pics/sealed (block and ditto misses), sealed_check/pics/diff (truth fixes), skeptic/pics,
  step4/pics/spots.
