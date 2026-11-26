# Text-first steps 1-4: gates (26 Nov 2026)

Steps 1-4 of plan text_first.md, done on copies. No repo tool, no file of Ben's, and nothing in the batch outputs was changed.
Nothing was downloaded and no U-net was trained. The full agent reports are in findings_full.md. The working data is in
data/sanborn/bench_2026-11-25/text_v1/, and this folder is the second copy of its scripts, scores, truth masks, shipped
classifier weights and Ben's labelling sheets.

Conventions: Ben has not answered them yet, so all four steps used the plan's proposals.
- Ditto marks and story heights are text.
- Hydrants, manholes, hooks and rail ticks are not text.
- A block side through a row of house numbers stays a side.
- Pipe and sewer labels are text.

## Held-out scores (H1-H4: plates 90, 90, 47 and 54A; never used for tuning)

Truth: truth-check/heldout_fixed. Text means codes 2 and 3. I recomputed the pooled P/R/F1 with my own code and got the
gate scorer's numbers exactly. The skeptic's scorer also agrees.

| method | precision | recall | F1 | street names | block numbers | ditto |
|---|---|---|---|---|---|---|
| bin 8 (today's ink sorting) | 0.751 | 0.863 | 0.803 | 0.983 | 0.902 | 0.991 |
| finder v1 | 0.906 | 0.916 | 0.911 | 0.886 | 0.802 | 0.332 |
| finder v2 | 0.903 | 0.934 | 0.919 | 0.964 | 0.868 | 0.332 |
| finder v2 + classifier (finder3) | 0.924 | 0.930 | 0.927 | 0.978 | 0.891 | 0.332 |

Recall by kind is counted in pixels. By words, street names are 14 of 16 for v2 and 15 of 16 for finder3.

## Gates

| gate | target | result | verdict |
|---|---|---|---|
| Step 2, finder v2: F1 | >= 0.92 | 0.9186 | FAIL (by 0.001, within the truth noise) |
| Step 2: street-name recall | >= 0.95 | 0.964 (pixels); 0.875 (words) | pass in pixels, fail in words |
| Step 2: block-number recall | >= 0.95 | 0.868 | FAIL |
| Step 2: Ben's line ink called text (44, 1A, 5) | <= 0.5% | 0.49% max (plate 5, 3 px) | pass, but tuned on those plates |
| Step 3, classifier: no fixed target | better than v2 | F1 +0.008; false text 6.9% -> 5.3% | helps |
| v2 + classifier as the mask: F1 | >= 0.92 | 0.9269 (95% range 0.917-0.936) | pass |
| v2 + classifier: block numbers | >= 0.95 | 0.891 | FAIL |
| v2 + classifier: line ink | <= 0.5% | 0.43% max | pass, but tuned on those plates |
| Step 4, hand-off: no worse anywhere | no loss on any score | small losses on single grids and tracks | FAIL |

## Step 4 in brief (plates 44, 5 and 1A; these are also the plates the mask was tuned on)

- Plate 5: false railroad tracks fall from 23 to 2, or from 54 to 8 with no ground.
- Streetcar recall rises on 44 (0.797 -> 0.865), 5 (0.776 -> 0.803) and 1A (0.770 -> 0.887).
- Plate 44: railroad recall falls from 0.9823 to 0.9814 because of 56 px at the R of REILTY. Two rules written while
  looking at that track (text bridging tick gaps, joins across lettering) are part of this. Without them it is 0.9688.
- Plate 44 lines, "both" variant: precision +0.006 and recall +0.004 on all 6 grids. Grid 3 loses one block and grid 5
  loses the Ludlow house-number side.
- Plate 44 lines, "states" variant: no line of Ben's is lost. It costs one ring on 44 and one closed block on 5.

## Weak spots found

- Block numbers crossed by lines lose a figure, for example the 3 of 36 on H4.
- Ditto marks on 90 and 54A are tiny tick pairs, and every finder misses two thirds of them.
- Small building outlines round story figures on the 200 ft plate 90 are called text. This happens at 10-40 times the
  rate on the 100 ft plates, and no step-4 test covered it.
- The 400 ft crop H3 is the weakest (F1 0.86-0.87; SAFFER and FYFFE).
- Six thin dashes of the dashed line beside Ben's streetcar track on 44 are called text. Every finder version does this.

## Held-out leaks (checked; no verdict changes)

- finder2 was tuned in a window inside H3. Leaving that window out moves its F1 from 0.9186 to 0.9196.
- 495 classifier training rows lay inside H1 and H2. Refitting without them moves F1 from 0.9269 to 0.9264.
