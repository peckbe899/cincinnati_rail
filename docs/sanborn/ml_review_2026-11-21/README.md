# Sanborn 1922 block recognition: review of the two networks and what surrounds them (21 November 2026)

Ben, 21 November 2026: "can you look at the current code for both to see if there's any ML or U-net improvements
that can be made? I want to be reasonably sure that the current versions of the codes are handling them correctly.
Feel free to look into different improvement methods for map recognition".

Covered: the area network (`unet.py`), the line network (`edgenet.py`), their labels (`make_labels.py`), the outline step
(`outlines.py`, `blocks_noguide.py`, `run_plates.py`), how they are scored, the rail tools, and a web search of
map-recognition methods. Six reviewers each had a second agent re-check every finding, two researchers each had a
feasibility check, and a final critic looked for gaps. All checks were read-only and ran on the CPU while the batch
used the GPU. Every finding with its check and evidence: `findings_full.md`. The review's scripts: `scripts/`
(named `folder__script.py`). Their pictures and data: `data/sanborn/ml_review_2026-11-21/` (not in git).

The only ground truth for blocks is plate 44 (`streetmap/22-44.json`, Ben's 55 closed blocks and 359 lines). Every
number below rests on that one plate.

## The short answer

The networks themselves are coded correctly:
- Channel order (RGB) and /255 scaling match between training and use.
- Tiling covers every plate size, and the 0.5 threshold is close to the best one.
- A CPU rerun reproduces the DirectML output to within 1/255.

What does not hold up is what is done with their answers, and how they are scored:

1. **Fixed now (b8fdcab):** the line editor had stopped reading each plate's rail "complete" flag. A comment had
   swallowed the statement (since bddf7bb, 19 Nov), so the next rail save wrote the previous plate's value. Also, a
   plain click on a point of a rule track marked the track as checked. Ben's files were checked: plate 44 is still
   complete (saved 18 Nov), and 1A is not complete (saved 21 Nov 00:05).
2. **Bug, not fixed (the batch uses it):** `outlines.py:92` keeps only outermost contours (`RETR_EXTERNAL`).
   - On the uncut PDF sheets the area network calls the margin, the KEY and open land "block". That forms one ring
     over 63-93% of the paper.
   - Every street becomes a hole in that ring, and every block the networks did find sits inside a hole. Both are
     thrown away.
   - Plate 30: the networks found 17 block regions, and the batch exports "1 blocks, 9 sides, 0% on a printed line".
   - 15 sheets export a single block: 22, 23, 27, 30, 47, 48, 50, 73, 78, 81, 88, 90, 92, 94 and 95. All are
     recorded as done.
3. **The batch's "91-99% on a printed line" is not a quality score.** It only says a side lies on some ink within
   about 2-4 px.
   - On plate 44 the blank-guide chain reports 96.1%. Its green sides are 78% right, and it finds 59% of Ben's printed
     lines.
   - After the editor filter, which drops short pieces and paper-edge pieces, it finds 52.5% of Ben's interior sides
     at 74% precision.
   - No block closes: the filter removes a piece from every one of the 36 outlines. The guided chain also closes 0.

## Findings on the networks, most important first

| # | What | Number | Fix |
|---|---|---|---|
| 1 | Line network: the 7th input (the area network's answer) comes from the plates the area network was trained on, so it is cleaner in training than in use | Street called block: 2-5% on training plates, 14.7% on 44. The line net leans on that input: with it as given, P 0.76 / R 0.61; blanked, P 0.40 / R 0.24; perfect, P 1.00 / R 0.92 | Area answers from networks that did not see the plate (4 trainings × ~46 min, overnight), plus realistic corruption instead of the 15% grey blank |
| 2 | The five labelled plates are one kind of map | Lightly tinted (15-26% of the paper); 35 of 80 scans are more tinted, 19 above 40%. **Corrected later the same day** (`docs/sanborn/bench_2026-11-21/`): 43 and 44 are at 100 ft to the inch and 45, 80 and 82A at 200. Over the batch, 36 plates are at 100 ft, 63 at 200 and 10 at 400 (46-50, 92-95, 93A/B). The scale is recorded nowhere | Record ft-per-inch per plate (and per inset). Do NOT resize 100-ft plates to 200 ft: measured on 44, PQ falls from 0.43 to 0.12. Put scale and pen-width augmentation into training instead |
| 3 | Ben's checked plate 44 is not the yardstick | Line precision is overstated: lines_ng1 is logged at P 0.634, and is 0.532 against Ben's lines. The area labels agree with his map on 98.6% of the ground it decides, so they are fine | Score against `streetmap/22-44.json` (lines P/R, blocks by panoptic quality) |
| 4 | Scores are not comparable between runs | Plate 44's line target changed (line share 0.0092 → 0.0128). On today's target lines_v2 is P 0.739 / R 0.787, not the logged 0.755 / 0.874 | Freeze the targets, write the target version and options into each model's json |
| 5 | The last weights are kept, not the best | edge_v1 ended at accuracy 0.9666 against a best of 0.9824 during the run. area_ng1 and lines_ng1 ended near their best | Weight averaging (EMA) or keep the best; seed torch (`manual_seed` is never called, so two runs differ) |
| 6 | Blank-guide training still pastes 255 squares into the guide | 25% of training crops (`unet.py:124`), never seen in use | Skip the guide shift and erase under `--no-guide` |
| 7 | Tiles disagree at their seams (GroupNorm per tile) | Block/street flips 5× as often at seams | Blend overlapping tiles (Hann window): +0.2 points |
| 8 | Flip test-time averaging, measured | area_ng1 on 44: accuracy 0.9127 → 0.9176, iou_street +1.4 points | 4 passes of the area network; cheap |
| 9 | Railway land is labelled block (today's parcels) | Up to 29% of area_ng1's errors on 44 sit along the rail (an upper bound), 0.3-2.3% of block pixels on the training plates | Leave ground near tracks untaught (255) |

## Better methods (research, measured on plate 44 against Ben's 55 blocks)

Panoptic quality (PQ, the ICDAR 2021 MapSeg metric) counts a block as found when it overlaps one of Ben's blocks by
IoU > 0.5. The current guided outlines score PQ 0.592: 35 of 55 blocks found and 11 false. 19 of the 20 misses are
merges, where one outline covers two or three blocks. The 94.7% pixel accuracy hides that one block in three is
wrong.

The first four need no retraining:
- **One watershed marker per block** (Chen et al., 2024 benchmark of historical-map vectorisation):
  - guided outlines: PQ 0.582 → 0.650;
  - blank-guide nets: PQ 0.515 → 0.602.
  - It is CPU only and about 15 lines in `outlines.py`.
- **On the 5 placed plates: street wherever either area network says street.** PQ 0.582 → 0.750 (47 of 55), and 0.790
  with the markers. The guided net copies today's map where 1922 had a street, for example Palm St.
- **Green only where the line network agrees:** green precision 78% → 85%.
- **Tune `outlines.py` on PQ:** its settings alone move PQ between 0.573 and 0.750. Tuning only on 44 will flatter
  the result.

With the next retraining (Ben runs it):
- small warps plus hue jitter, +3.6-4 PQ in the closest published setting;
- EMA weights;
- later, self-training on the confident pixels of the unchecked plates.

Not recommended for now:
- Segment Anything, MapSAM or DINOv2 foundation models: no gain at this data size, and untested on DirectML. MapSAM's
  railway F1 is 94.06 against the U-Net's 95.13 with full data.
- clDice and Betti topology losses.
- A learned (deep) watershed: PQ 28.5 in the benchmark, against a U-Net plus classical watershed.
- One network for everything.
- Moving to ROCm.

## Rail

- `ink_bins.py:344` and `score_rail.py:18` count unchecked `src: "rule"` tracks as Ben's. On 1A this lifts the rules'
  streetcar recall from 77.7% to 85.8%.
- A track Ben deletes leaves no record, so there are no "not rail" examples.
- Plate 44 is marked complete, but a 1,705 px ticked spur at about (3512, 2687) is not drawn. Ben should look at it.
- A rail network can be built from `edgenet.py`, trained only on complete plates (today only 44).

## Suggested order

1. After the batch: `outlines.py` keeps nested blocks and street holes, masks the sheet margin and KEY on uncut
   sheets, and flags a plate "suspect" when one outline covers more than 30% of the paper. Then rerun only the
   outline step on the affected sheets (CPU, no networks).
2. A scorer against Ben's map, writing to its own folder so 44's guided outputs are not overwritten.
3. Markers per block, the green gate, and closed rings from the sides. Measure each on 44.
4. One retraining bundle for Ben to run:
   - out-of-fold area answers;
   - no 255 squares;
   - a seed;
   - EMA;
   - warps and hue;
   - flip averaging when predicting.
5. A scale table, then the next plates to check: tinted, 100 ft and 400 ft.
