# Why the four retrained pairs did worse on plate 44: every report (25 November 2026)

Ben: "Yes, find out why the new pairs did worse, but hold off on another round until we are ready." Nothing was trained. Paths are in data/sanborn/bench_2026-11-25/diag/ (not in git); scripts are copied beside this file; the round-2 design is round2.md.

## swap

The loss comes from the area network. The line networks are not the problem. The checkpoint choice is not the problem either.

1. **Line nets.** Each of the four new line nets (best or _last) was paired with area_ng1. All eight pairs score the same as the baseline on plate 44: paired PQ gain -0.001 to +0.005. Pixel by pixel, their line maps are a little better than lines_ng1's: F1 at 3 px 0.616-0.644 against 0.595, and precision 0.57-0.62 against 0.55.
2. **Area nets.** Each new area net was paired with lines_ng1. Every one reproduces its pair's whole loss:

| area net | paired gain PQ (new area + lines_ng1) | pair's own gain |
|---|---|---|
| V1S1 | -0.147 | -0.142 |
| V1S2 | -0.041 | -0.040 |
| V2S1 | -0.075 | -0.072 |
| V2S2 | -0.025 | -0.028 |

   Plate 1A behaves the same way. With area_ng1 under them, the new line nets score PQ 0.09 on 1A, the same as the batch pair. With the new area nets, they score 0.10-0.41. So 1A's rise also came from the area nets, which had trained on the left part of 1A.
3. **How a worse area map does damage.**
   - Mixed maps (no GPU) split this into two routes. The bigger one is the outline step reading the new area map directly: -0.013 to -0.089 PQ on its own.
   - The smaller one is the area map fed to the line net as its 7th input: -0.038 to +0.007 on its own. Even this way, a worse area map makes both the old and the new line nets draw worse lines. Their line maps' F1 drops from 0.59-0.64 to 0.44-0.51.
4. **Two kinds of area-net error.**
   - (a) All four new area nets mark the railway, Mill Creek and canal corridors as non-block far more often than area_ng1. The outline step then cuts the land Ben left undecided into more closed rings. That gives 7-15 false blocks there, against 4 for the baseline. Ben leaves streets open where they meet the creek, canal or railway, so those sides are lines he would delete. This alone explains all of V2S2's loss. Without those false blocks, V2S2 would gain +0.012 PQ (4 of 6 grids up).
   - (b) Three of the four (V1S1, V1S2, V2S1) are also worse on the ground Ben decided. They call narrow streets and alleys block, so more of his blocks are lost in merges. Their street IoU is 0.715-0.743 against 0.815 for area_ng1. V2S2 is better than area_ng1 on that ground: street IoU 0.838 (best) and 0.851 (_last).
5. **Checkpoint choice.** Best and _last give the same mean paired gain: -0.071 and -0.069. Checkpoint by checkpoint (best, then _last):

| pair | best | _last |
|---|---|---|
| V1S1 | -0.142 | -0.135 |
| V1S2 | -0.040 | -0.057 |
| V2S1 | -0.072 | -0.100 |
| V2S2 | -0.028 | +0.015 (3 of 6 grids up) |

   The swing between checkpoints (about ±0.04) is the size of the grid-to-grid spread, and much smaller than the gap between seeds. One related finding: the 1A region says all four new area nets beat area_ng1, but on 44 three of the four are worse. The new nets trained on the rest of plate 1A, and area_ng1 never saw it. So that region cannot tell whether an area net works on a plate it has never seen.

No network was trained. All 20 GPU evaluations finished (exit 0), and the baseline runs were reused. When area_ng1 made the area maps here, they matched the stored batch maps bit for bit on all 6 grids. So step (d), "each new line net fed the stored baseline area maps", is the same as step (a).

All four line nets beat lines_ng1 pixel by pixel once the area map is good, but the ink rules still have to finish their lines. About 30% of every line net's drawn pixels lie more than 10 px from any of Ben's lines. In one crop I looked at, most of those were the dashed pipe and sewer lines along the streets. The outline step removes most of them.

### numbers

All measured on 25 Nov unless marked as an estimate. Scripts are in diag/swap/scripts/. PQ and the other plate-44 scores are means over the 6 tile grids with the merged outline step. "Gain" = this pair minus area_ng1 + lines_ng1, grid by grid, with (grids up of 6).

LINE NET SWAPS: area_ng1 + new line net (eval_v2.py via run_swaps.py; summarize.py -> summary.md)
- lines_v2a_s1 (V1S1): PQ 0.516, gain +0.005 (3/6); recall 0.629; precision 0.824; merges 12.0; false blocks 11.0
- lines_v2a_s2 (V1S2): PQ 0.512, gain +0.002 (3/6); recall 0.630; precision 0.819; merges 12.0; false blocks 11.5
- lines_v2b_s1 (V2S1): PQ 0.511, gain +0.000 (3/6); recall 0.627; precision 0.822; merges 12.2; false blocks 10.7
- lines_v2b_s2 (V2S2): PQ 0.511, gain +0.001 (4/6); recall 0.631; precision 0.806; merges 12.2; false blocks 11.2
- the same with the _last line nets: gain +0.005, +0.002, -0.001, +0.004
- baseline for comparison: PQ 0.511; recall 0.626; precision 0.833; merges 12.2; false blocks 10.8
- 1A region with these pairs: PQ 0.087-0.093 (batch 0.093)

AREA NET SWAPS: new area net + lines_ng1 (same scripts)
- area_v2a_s1: PQ 0.364, gain -0.147 (0/6); recall 0.445; precision 0.645; merges 12.7; false blocks 22.3
- area_v2a_s2: PQ 0.469, gain -0.041 (1/6); recall 0.524; precision 0.676; merges 10.3; false blocks 14.0
- area_v2b_s1: PQ 0.435, gain -0.075 (0/6); recall 0.348; precision 0.726; merges 9.7; false blocks 18.2
- area_v2b_s2: PQ 0.485, gain -0.025 (2/6); recall 0.599; precision 0.792; merges 12.0; false blocks 17.8
- 1A region with these pairs: PQ 0.103, 0.357, 0.255, 0.263 (the pairs' own: 0.104, 0.356, 0.256, 0.263)

_LAST CHECKPOINTS (eval_v2.py via run_swaps.py)
- both nets _last: V1S1 0.376 (-0.135, 0/6); V1S2 0.454 (-0.057, 0/6); V2S1 0.411 (-0.100, 0/6); V2S2 0.526 (+0.015, 3/6; recall 0.644, precision 0.760, false blocks 15.8)
- _last area + lines_ng1: -0.135, -0.052, -0.097, +0.017
- mean gain of the four pairs: best -0.071, _last -0.069
- weights, best against _last, largest difference (torch on CPU): lines_v2a_s2 0.0 (identical); other line nets 0.0005-0.032; area nets 0.004-0.045

MIXED MAPS, NO GPU (run_mixes.py; bench44 --grids). Gains for V1S1 / V1S2 / V2S1 / V2S2:
- only the outline step's area map is new (m100): -0.089 / -0.059 / -0.085 / -0.013
- only the line net's 7th input is the new area map, with lines_ng1 (m010): -0.010 / -0.038 / -0.009 / +0.007
- the 7th input is new, with the new line net (m011): -0.032 / -0.034 / +0.008 / +0.003
- outline step reads the new area map, new line net fed area_ng1's map (m101): -0.088 / -0.063 / -0.084 / -0.006

FALSE BLOCKS BY KIND (fp_anatomy.py; best pairs, per 6-grid mean; the void kind is blocks more than half on ground Ben did not decide: the creek, canal and railway land)
- baseline: void 4.2, merge 5.8, street 0.8
- V1S1: void 15.3, merge 6.0
- V1S2: void 7.3, merge 5.8
- V2S1: void 11.5, merge 6.3
- V2S2: void 11.8, merge 6.3
- Ben's blocks lost in merges: baseline 27.2; V1S1 32.5, V1S2 29.5, V2S1 28.7, V2S2 27.3
- matched: baseline 27.7; V1S1 22.3, V1S2 25.5, V2S1 25.7, V2S2 27.7

PQ WITHOUT THE VOID FALSE BLOCKS (pq_without_void.py; bench44's own PQ formula with those blocks left out, a measured counterfactual)
- gains: V1S1 -0.099 (0/6), V1S2 -0.024, V2S1 -0.038, V2S2 +0.012 (4/6), V2S2_last +0.054 (6/6)
- bench44's PQ_decided gains: V1S1 -0.099, V1S2 -0.027, V2S1 -0.040, V2S2 +0.009 (4/6), V2S2_last +0.051

EDITOR LINES BY GROUND (lines_decided.py): precision on decided ground / precision overall
- baseline 0.916 / 0.833
- V2S2 0.925 / 0.779
- V1S1 0.797 / 0.633

AREA MAPS AGAINST BEN'S 44, pixel by pixel on decided ground (pixel_maps44.py, 6 grids)
Columns: accuracy; street IoU; mean P on street; mean P on block; unsure share (0.2 < P < 0.8); street called block; gross street called block (more than 10 px from any boundary); share of undecided ground called block

| area map | accuracy | street IoU | mean P street | mean P block | unsure | street called block | gross | undecided called block |
|---|---|---|---|---|---|---|---|---|
| area_ng1 | 0.936 | 0.815 | 0.182 | 0.943 | 0.108 | 0.127 | 0.106 | 0.820 |
| V1S1 best | 0.899 | 0.715 | 0.247 | 0.925 | 0.105 | 0.214 | 0.182 | 0.760 |
| V1S2 best | 0.907 | 0.739 | 0.218 | 0.924 | 0.115 | 0.185 | 0.163 | 0.780 |
| V2S1 best | 0.904 | 0.741 | 0.180 | 0.898 | 0.122 | 0.146 | 0.106 | 0.710 |
| V2S2 best | 0.943 | 0.838 | 0.135 | 0.938 | 0.092 | 0.089 | 0.061 | 0.735 |
| V1S1 last | 0.901 | 0.721 | 0.238 | 0.925 | 0.099 | 0.208 | 0.177 | 0.760 |
| V1S2 last | 0.906 | 0.735 | 0.217 | 0.927 | 0.105 | 0.188 | 0.167 | 0.783 |
| V2S1 last | 0.905 | 0.743 | 0.180 | 0.902 | 0.117 | 0.146 | 0.112 | 0.733 |
| V2S2 last | 0.948 | 0.851 | 0.111 | 0.942 | 0.079 | 0.073 | 0.053 | 0.763 |

- undecided ground within about 15 half px of railroad ink, called block (grid 0; inline check against unet_data/44_bins.png bin 4): area_ng1 0.30; V1S1 0.25, V1S2 0.21, V2S1 0.10, V2S2 0.13

LINE MAPS AGAINST BEN'S 44 LINES, 3 px tolerance (pixel_maps44.py; drawn = P > 0.5; precision against all his lines)
Columns: recall printed / drawn / sheet edge; precision; precision on decided ground; share of drawn px more than 10 px from any of his lines; F1 on interior lines (printed + drawn)

| line map | printed | drawn | sheet edge | precision | prec. decided | far | F1 |
|---|---|---|---|---|---|---|---|
| lines_ng1, area_ng1 input | 0.690 | 0.345 | 0.699 | 0.554 | 0.623 | 0.341 | 0.595 |
| new nets, area_ng1 input | 0.700-0.725 | 0.359-0.379 | 0.663-0.695 | 0.574-0.617 | 0.661-0.736 | 0.27-0.30 | 0.619-0.644 |
| new nets, own area input: V1S1 | 0.523 | 0.344 | 0.569 | 0.429 | | 0.48 | 0.461 |
| V1S2 | 0.585 | 0.378 | 0.643 | 0.473 | | | 0.511 |
| V2S1 | 0.563 | 0.302 | 0.516 | 0.451 | | | 0.485 |
| V2S2 | 0.670 | 0.336 | 0.792 | 0.640 | 0.767 | 0.23 | 0.631 |

- lines_ng1 fed each new area map, F1: V1S1 0.445, V1S2 0.497, V2S1 0.443, V2S2 0.582
- _last line nets fed area_ng1, F1: 0.616-0.629

PLATE 1A VALIDATION REGION, area accuracy against train_v2/1A/label.png (inline check, whole-plate maps)
- street IoU: area_ng1 0.840; V1S1 0.882, V1S2 0.908, V2S1 0.875, V2S2 0.920
- on 44, three of these four are worse than area_ng1 (table above)

MAP SHIFT (shift_test.py; best shift and accuracy at 0 -> at best shift)
- 44, grid 0: every area map is best moved by (1-2, 2-4) half px. area_ng1 (1, 2): 0.937 -> 0.940; the others gain 0.3-0.8 points
- 1A: (1, 1) for every map

CHECKS
- area_ng1's maps in all 8 runs that used it are bit-identical to bench44_maps on all 6 grids (eval_v2 info.json). So (d) "line net fed the stored baseline maps" is (a).
- b__ runs' area maps have the same sha256 as the run's pair maps
- all six baseline plate-44 runs reused ("same code")
- GPU: 20 eval_v2 runs, 09:35-10:31 on 25 Nov, each 2.4-3.2 min, all exit 0
- 16 mixed bench44 --grids runs, all exit 0
- nothing written outside diag/swap: find -newer shows no changes in train_v2_runs, train_v2, unet_data, picks22_guided, streetmap, bench44_maps or bench_2026-11-23; git status tools/ is clean

### causes

- **A1** The area network causes the loss. The new line networks are as good as lines_ng1, or slightly better.
  - evidence: - New area net + lines_ng1 reproduces each pair's gain within 0.005: -0.147/-0.142, -0.041/-0.040, -0.075/-0.072, -0.025/-0.028.
- area_ng1 + each new line net, best or _last (8 pairs): -0.001 to +0.005 PQ; recall 0.627-0.631 against 0.626; false blocks 10.7-11.5 against 10.8.
- Pixel by pixel, with area_ng1's map as input, the new line nets have F1 0.616-0.644 against 0.595 and precision 0.57-0.62 against 0.55.
- On 1A, the same split holds (area swaps reproduce each pair's 1A score, line swaps stay at 0.09).
  - size: All of it: 100% of each pair's PQ loss, within 0.005 PQ (measured).
  - confidence: high
  - round 2: Focus round 2 on the area net. The line nets' recipe can stay as it is (V1 or V2), but always score a line net with a fixed, good area map, and score the area net on its own.
- **A2** Of the two routes by which the area map does damage, the bigger is the outline step reading it directly (seeds and watershed). The smaller is the line net, which leans hard on the area map it is fed as its 7th input.
  - evidence: - Mixed maps, no GPU. Only the outline step's area map new: -0.089 / -0.059 / -0.085 / -0.013. Only the 7th input new: -0.010 / -0.038 / -0.009 / +0.007. Both: -0.147 / -0.041 / -0.075 / -0.025. The two do not simply add up.
- A worse area map as 7th input makes both old and new line nets worse: lines_ng1's F1 falls from 0.595 to 0.443-0.497 with V1S1/V1S2/V2S1's maps.
- Picture lines_panel_V1S1_north.jpg: where the area map calls a narrow street block, both line nets stop drawing that street's sides.
  - size: Outline-step route: 0.013-0.089 PQ. 7th-input route: up to 0.038 PQ (measured, each on its own).
  - confidence: high
  - round 2: Judge an area net by its maps on a held-out plate before any end-to-end run. Do not trust a line net's validation score made with area_ng1's in-sample maps (area_in.png): at use it gets another net's map. Consider training the line net with the 7th input blanked or noised more often than 15% of the time, so it relies less on the area map.
- **A3** The new area nets mark the railway, Mill Creek and canal corridors as non-block far more often than area_ng1. The outline step then rings the creek and rail land Ben left undecided into many separate false blocks, whose sides along the creek and track are lines Ben would delete.
  - evidence: - Void false blocks: baseline 4.2; new 7.3-15.3 (best), 9.5-15.7 (_last).
- Undecided ground near railroad ink called block: area_ng1 0.30, new 0.10-0.25.
- Pictures fp_base_grid0.jpg, fp_V2S2_grid0.jpg and fp_V2S2_grid0_void_crop.jpg: the new rings follow Mill Creek, the railroad and the canal bed. ben44_lines_void_crop.jpg shows that Ben left those streets open there.
- V2S2's editor-line precision on decided ground is 0.925 against 0.916, but 0.779 against 0.833 over all.
- This is the same kind of error as Ben's false railroad positives on plate 5.
  - size: Measured by recomputing PQ without the void false blocks:
- V2S2 -0.028 -> +0.012: all of V2S2's loss.
- V1S1 0.043, V1S2 0.016, V2S1 0.034 of their losses.
- About 0.02-0.07 of overall editor-line precision.
  - confidence: high (measured; the cause in the training data is not yet found)
  - round 2: - Give the area net 'not a block' examples for railway, creek and canal land.
- Use Ben's deleted lines (plate 5: 248 marked wrong; 1A: 68) and his rail tracks (rail_ben.json) as negatives, as he asked.
- Or have the outline step leave a side open where it runs along rail or creek, as Ben's rule does.
- Report bench44's PQ_decided beside PQ, so this ground is visible separately.
- **A4** Three of the four new area nets (V1S1, V1S2, V2S1) are also worse on the ground Ben decided. They call narrow streets and alleys block, so more of his blocks are merged. V2S2 is better than area_ng1 there. The spread between seeds is larger than the gap to area_ng1, so area_ng1 may have been a lucky seed.
  - evidence: - Street called block: area_ng1 0.127; V1S1 0.214, V1S2 0.185, V2S1 0.146; V2S2 0.089 (best) and 0.073 (_last).
- Street IoU: area_ng1 0.815; 0.715, 0.739, 0.741, 0.838.
- Ben's blocks lost in merges: 27.2 against 32.5, 29.5, 28.7, 27.3. Matched: 27.7 against 22.3, 25.5, 25.7, 27.7.
- Picture area_V1S1_grid0.jpg: whole narrow streets in the north centre (Lingo St area) are red, i.e. called block.
- Same recipe, two seeds: street IoU 0.741 (V2S1) against 0.838 (V2S2).
  - size: After the void false blocks are taken out (measured):
- V1S1 0.099, V2S1 0.038, V1S2 0.024 PQ.
- V2S2 none (+0.012).
  - confidence: medium-high that it is the area net on decided ground (measured). Low on why: seed, recipe or 1A cannot be told apart without training.
  - round 2: - Train several seeds per variant.
- Choose among them on a plate never trained on, not on 1A's right-hand part.
- Check that the labels teach narrow streets and alleys as street (Ben's checked 1A and 5 street maps).
- **A5** The checkpoint choice is not the cause. But the 1A region used to choose it cannot tell whether an area net works on a new plate: it favours nets that trained on the rest of plate 1A.
  - evidence: - Mean paired gain: best -0.071, _last -0.069.
- _last is better for V1S1 (+0.007) and V2S2 (+0.043), worse for V1S2 (-0.017) and V2S1 (-0.028).
- lines_v2a_s2 best equals _last bit for bit; the other weight differences are small (cosine schedule).
- On 1A's region all four new area nets beat area_ng1 (street IoU 0.875-0.920 against 0.840). On 44, three of the four are worse.
- area_ng1 never saw 1A; the new nets trained on its left part.
  - size: About ±0.04 PQ between best and _last in one run, against a grid-to-grid spread of 0.01-0.03 and a seed-to-seed spread of about 0.10 (measured). Only V2S2_last beats the baseline: +0.015, 3 of 6 grids up (+0.051 on decided ground). That is within the noise.
  - confidence: high
  - round 2: - Choose seeds and checkpoints on a whole plate never trained on, with the area map scored on its own (street IoU and the false-block kinds).
- Plate 5 is now fully checked by Ben and could be that plate if it is taken out of the pseudo set.
- Or average the last few checkpoints.
- Keep plate 44 out of the choice, as now.
- **A6** Minor: every area map, area_ng1 included, sits about 1-2 half px right and 2-4 half px down of Ben's map on 44. This is not a cause of the loss.
  - evidence: The best shift gains only 0.3-0.8 points of accuracy (shift_test.py). On 1A, every map's best shift is (1, 1).
  - size: Under 1 point of accuracy; it affects all networks alike (measured).
  - confidence: high
  - round 2: None needed now. Note it if the boundaries are ever scored at 1-2 px.

### files

Everything is under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/swap/

Results:
- summary.md and summary.json (every plate-44 evaluation, with paired gains, PQ decided and 1A)
- eval/<NAME>/eval_v2.json: 20 GPU evaluations, each with maps44/, runs44/, maps1A/, runs1A/ and stdout.txt. NAME is one of:
  - a__ng1+L_<STEP>
  - b__A_<STEP>+ng1
  - c__<STEP>_last
  - c__ng1+L_<STEP>_last
  - c__A_<STEP>_last+ng1
- mix/<STEP>_m010|m011|m100|m101/: 16 mixed-map runs, each with maps44/gridK/source.txt and runs44/v2_grids.json
- pixel/pixel_maps44.json: area and line maps scored pixel by pixel on 44
- fp/*.json: false and missed blocks by kind, per grid; fp/pq_without_void.json
- runs_baseline44/: a copy of the six baseline runs from bench_2026-11-23/train/integrate/round2/driver_mini/eval/runs_baseline44
- run_swaps.log and run_mixes.log

Pictures (pics/):
- fp_base_grid0.jpg, fp_V2S2_grid0.jpg, fp_V1S1_grid0.jpg
- fp_V2S2_grid0_void_crop.jpg, fp_base_grid0_void_crop.jpg
- ben44_lines_void_crop.jpg
- area_base_grid0.jpg, area_V1S1_grid0.jpg, area_V2S2_grid0.jpg
- lines_panel_V1S1_north.jpg

Scripts (scripts/, with a second copy in _second_copy/scripts/):
- run_swaps.py
- run_mixes.py
- summarize.py
- pixel_maps44.py
- fp_anatomy.py
- pq_without_void.py
- lines_decided.py
- shift_test.py
- fp_picture.py
- area_err_picture.py
- lines_panel.py

## errors

I counted every plate-44 error from the eval outputs that already exist. Nothing was trained, I ran nothing on the GPU, and I wrote nothing outside diag/errors. My recount matches bench44.json exactly on all 30 runs (5 pairs x 6 grids).

The new pairs lose on 44 for three reasons. None of them is mainly the numbers.

1. **Lost lines (the biggest cost for V1S1, V2S1 and V1S2).** Both new networks stop seeing block lines that the baseline found.
   - At the lost lines, the new line nets' P(line) drops from about 0.7-0.8 to 0.2-0.4.
   - The new area nets call both sides of a lost line "block" 21-62% of the time; the baseline does so 8-11% of the time.
   - The losses cluster in the dense north-west and north blocks with 12-ft passages and alleys. Ben's blocks 3-4-9-10-11 merge in all four pairs (5 of 6 grids), and 18-19-20-28-29-30 merge in V1S1, V2S1 and V1S2. Bond St (blocks 35 and 42) and the south side of Spring Grove are also lost.
   - V1 has no pseudo plates and loses these lines too. So the pseudo labels alone do not explain the merges.
   - The lost lines are not tied to tint or to text. 9-11% of lost samples have text beside them, against 9.6% of all Ben's lines.
   - Alleys are not over-represented either: 18-26% of the lost length is on alleys, against 19% of all Ben's lines.

2. **Extra false blocks.** Almost all of them are not new false ground. They are pieces of the open land the baseline already called one big false block: by Mill Creek, the canal and the railway, and the Ludlow estate.
   - The baseline has 5 such blocks per grid, covering 24.4 Mpx. The pairs have 7.8-16.2 blocks, covering 20-23 Mpx.
   - The new nets cut that land along the creek banks, canal and railway edges. PQ counts every piece as a false block.
   - False blocks on the ground Ben decided are unchanged: 6.3-7.0 against 6.7.
   - This is the whole of V2S2's loss. On Ben's decided ground V2S2 beats the baseline: PQ_decided +0.009 (up on 4 of 6 grids) and precision_decided +0.0085 (up on 6 of 6). Recall_decided is -0.028.

3. **New false lines on decided ground.**
   - V1 puts block sides on the water pipes and sewers in the middle of streets: 37-42% of its new false length there (V2S2: 5%).
   - Other kinds: no-ink closures 18-30%, text 13-29%, building edges 9-12%, lot lines 9-17%.
   - Across the whole plate, 52-77% of all new false length lies in ground Ben left undecided (the creek, canal and rail land), on creek banks that the ink rules file as "lot line".

**Ben's point on numbers near streets, tested on 44.**
- Only V2S1 is worse than the baseline.
  - 12.7% of its false length lies on numbers within 40 px of a street, against 6.5% for the baseline.
  - Inside the 5-40 px band beside the streets, 39% of its false length is on such numbers. Chance is 23% and the baseline is 26%.
  - Its line net's mean P(line) on those numbers is 0.079, against 0.049.
- V1S1, V1S2 and V2S2 are at chance (23-24%) and at or below the baseline: 5.0-5.9% of false length.
- Because all pairs draw more false lines, all of them have more false length on text in absolute terms: 5.5-7.2k px against 3.7k.
- So numbers are a small, seed-dependent confounder on 44, not the main cause.
- False sides of false blocks on near-street numbers: baseline 5.1%, the pairs 2.9-7.0%.
- Railroad ink lies under 1% or less of the false length in every run, so rail is not a factor on 44.

**Ben's point on learning from deletions, checked on plates 5 and 1A (read-only).**
- On plate 5, 58% of the deleted length (93 of 214 non-sheet deleted lines) runs within 5 px of a line Ben kept, in the same direction. These are lines he replaced or moved, not "no street here". On 1A it is 64%.
- Only about 94 lines on plate 5 (14.4k px) are clean "no street here" deletions.
- So "not a line" labels must be built only from deleted length that is not under a kept line. Otherwise they will contradict the lines Ben kept.
- On plate 5, 14 deleted lines lie mostly on text, all 5-34 px from a kept street. They are short (26-224 px, about 1k px in all). These are Ben's "numbers near streets".

**The 10 biggest new errors, by eye** (grid 0, full-size crops):
1. The 12-ft passages and the alley between the dense 25-ft-lot blocks (x 2979-4379, y 1076-2076). The new area nets fill them in as block, and the line nets stop drawing their sides. About 10k px lost in V1S1 and V2S1. It is the same in V1S2; V2S2 is milder (about 5k px).
2. Bond St (40 ft). The south side and a block side are lost. False sides sit on the dashed 12-inch sewer in the middle of Bond and on the water pipe and 30-inch sewer in the side streets.
3. The deep lots between Spring Grove and Mill Creek. Spring Grove's south block line and one side of the 33-ft street are lost. Sides were placed on the water pipe in the middle of Spring Grove and on a lot back-line by the creek.
4. A small creek through the open Ludlow-estate land (ground Ben did not decide). Both line nets draw the banks; the new area nets cut the land along them, so the banks now show as block sides.
5. Blocks 33 and 34 at Powers St (V1S2). Block 33's left and bottom sides are lost. A false side lies on an inner lot line where the area map darkened one lot strip.
6. The Clopper and Bethell parcels by Mill Creek (undecided ground). The creek banks and the railroad's edge are shown as block sides.
7. North-west. A block side slid off the block line onto the "6-inch W. PIPE" line in the street. There are also false lines on lot back-lines and along a green tint band.
8. Ludlow Ave by the creek strips. The avenue's sides are lost; false lines on the water-strip banks and on a building edge.
9. Cornwall Pl by the railway lane. Sides that run along an orange tint band are lost; false lines on the dashed sewer in the lane and on lot lines.
10. The Mill Creek banks at Alibone St. The banks are shown as sides, and short ends of Alibone St are lost.

### numbers

All are measured unless marked as an estimate. "Mean" is over the 6 tile grids, and lengths are in full-size px (1 sample = 1 px). Every script is in data/sanborn/bench_2026-11-25/diag/errors/.

**Reproduction check (collect.py).** Precision, recall_interior, PQ, false blocks, merges and matched agree with every bench44.json, 30 of 30.

**Headline, mean of 6 grids (summarize.py).**
- PQ / false blocks / merges / matched: baseline 0.511 / 10.8 / 12.2 / 27.7; V1S1 0.368 / 22.2 / 12.7 / 22.3; V2S1 0.438 / 18.5 / 9.8 / 25.7; V1S2 0.471 / 13.7 / 10.3 / 25.5; V2S2 0.482 / 18.2 / 12.0 / 27.7.
- False shown length: baseline 23.8k; V1S1 50.5k; V2S1 30.5k; V1S2 47.9k; V2S2 33.0k.

**Against the baseline on the same grid, mean (grid 0 in brackets) (census.py, summarize.py).**

| pair | new false | baseline false now gone | Ben's lines lost | Ben's lines gained |
|---|---|---|---|---|
| V1S1 | 41.8k (44.3k) | 15.2k | 42.8k (43.0k) | 11.0k |
| V2S1 | 26.7k (25.7k) | 20.0k | 54.3k (53.6k) | 10.6k |
| V1S2 | 39.5k (38.4k) | 15.5k | 33.5k (33.6k) | 15.5k |
| V2S2 | 25.9k (24.3k) | 16.6k | 20.1k (18.8k) | 17.6k |

- Robustness (xtab.py): measured at 10 px with no direction test, "new false" changes by 2% or less.

**New false length by the ink under it, mean (summarize.py).**

| pair | lot line | pipe | no ink | text | building | sewer |
|---|---|---|---|---|---|---|
| V1S1 | 29% | 23% | 15% | 15% | 6% | 4% |
| V2S1 | 31% | 4% | 20% | 25% | 6% | 5% |
| V1S2 | 30% | 23% | 13% | 14% | 5% | 6% |
| V2S2 | 48% | 2% | 15% | 17% | 4% | 1% |

- Share of new false length in undecided (void) ground: 61% / 53% / 52% / 77%. Off Ben's blocks: 76-86%. More than 40 px from his lines: 67-79%.

**New false on decided ground only (xtab.py).**
- V1S1: 16.2k; pipe 26%, sewer 8%, no ink 22%, text 17%.
- V2S1: 12.6k; text 29%, no ink 27%, lot line 16%.
- V1S2: 19.1k; pipe 31%, sewer 11%.
- V2S2: 6.0k.
- Share of shown length on decided ground that is false: baseline 8.3%, V1S1 20.1%, V2S1 17.7%, V1S2 20.1%, V2S2 7.5%.

**Lost lines, mean (summarize.py).**
- Line net P at lost Ben lines, pair against baseline: V1S1 0.22 vs 0.78; V2S1 0.40 vs 0.80; V1S2 0.28 vs 0.75; V2S2 0.43 vs 0.69.
- Area net says block on both sides (14 px out), pair against baseline: 62% vs 10%; 41% vs 8%; 50% vs 10%; 21% vs 11%.
- Alley share of lost length (partner line under 75 px away): 25 / 18 / 26 / 19%, against 19% of all Ben's lines.
- Text beside lost lines: 9-11%, against 9.6% of all Ben's lines. Tint of 0.4 or more: 27-36%, against 34%.

**Blocks (fp_cover.py, pq_parts.py).**
- False blocks that are not merges, per grid: baseline 5.0; V1S1 16.2; V2S1 12.2; V1S2 7.8; V2S2 11.8.
- Of those, the pieces at least 50% inside the baseline's own false ground: 14.7, 11.7, 6.7 and 11.8.
- False-block area in undecided ground: baseline 24.4 Mpx; the pairs 20.0-22.9 Mpx.
- False blocks on decided ground: 6.7, 6.8, 7.0, 6.3, 6.3.
- PQ_decided: baseline 0.538; V1S1 0.439; V2S1 0.498; V1S2 0.511; V2S2 0.547.
- Paired gain in PQ_decided: -0.099 (0 of 6 grids up), -0.040 (1/6), -0.027 (2/6), +0.009 (4/6).
- Paired gain in precision_decided: V2S2 +0.0085 (6/6 grids up); the others -0.09 to -0.12.
- *Estimate* (arithmetic, PQ formula with the baseline's false-block count): PQ would be 0.416, 0.475, 0.485 and 0.520. So the extra false blocks cost about 0.048, 0.037, 0.014 and 0.038 of PQ, and the lost matches cost the rest: 0.095, 0.036, 0.026 and -0.009.
- Ben's blocks lost on 5-6 of 6 grids (summarize.py): 4 and 10 in every pair; 5, 31, 33, 42 and 44 in V1.

**Ben's point on numbers (summarize.py, xtab.py), mean of 6 grids.**

| | false length on numbers within 40 px of a street | in the 5-40 px band (chance 23.3%) | line net mean P on those numbers | share with P above 0.5 |
|---|---|---|---|---|
| baseline | 6.5% | 25.9% | 0.049 | 0.048 |
| V1S1 | 5.0% | 23.4% | 0.046 | |
| V2S1 | 12.7% | 39.3% | 0.079 | 0.080 |
| V1S2 | 5.0% | 24.0% | 0.047 | |
| V2S2 | 5.9% | 24.3% | 0.044 | |

- False length whose main ink is text: 15.5 / 14.3 / 23.7 / 13.7 / 16.6%.
- False sides of false blocks on numbers near streets: 5.1 / 2.9 / 7.0 / 4.0 / 4.0%.

**Deletions on plates 5 and 1A (deletions.py, deletions2.py).**
- Plate 5: 248 lines deleted, 34 of them sheet lines. 58.4% of the length of the 214 other deleted lines runs within 5 px of a kept line in the same direction. Lines with less than 20% of their length beside a kept line: 94 (14.4k px).
- Deleted length on numbers near streets: 4.7%. Inside the band: 11.7%, against a chance of 29.3%.
- 14 deleted lines lie at least 50% on text. Each is 26-224 px long, with a median distance of 5-34 px to the nearest kept line.
- Plate 1A: 63.7% of the deleted length runs beside a kept line; 3 deleted lines lie mostly on text.
- Caveat: bin 1 on plates 5 and 1A is made from the editor's own lines, so the "block line" share of the deletions there is circular.

### causes

- **C1** Lost block lines. Both new networks stop seeing printed block lines that the baseline found, mostly in the dense north-west and north blocks with 12-ft passages and alleys, at Bond St and on the south side of Spring Grove. The area net joins the ground across the street, the line net no longer draws the line, and the blocks merge. Ben's blocks 3-4-9-10-11 merge in all four pairs (5 of 6 grids); 18-19-20-28-29-30 merge in V1S1, V2S1 and V1S2.
  - evidence: Measured (census.py, summarize.py).
- Lost length per grid: V1S1 42.8k px, V2S1 54.3k, V1S2 33.5k, V2S2 20.1k.
- Line net P at lost lines, pair against baseline: 0.22-0.43 vs 0.69-0.80.
- Area net says block on both sides: 21-62% vs 8-11%.
- Line net mean P on all block-line ink: baseline 0.66; V1S1, V2S1 and V1S2 0.55-0.58; V2S2 0.66.
- The lost lines are not tied to text (9-11% vs 9.6%), tint (27-36% vs 34%) or alleys (18-26% vs 19%).
- Crops err_1, err_2, err_3, err_5, err_7, err_8 and err_9, with area_err1/2/3/5.
- V1 has no pseudo plates and still loses these lines, so the pseudo labels alone do not explain them.
  - size: Estimate (pq_parts.py counterfactual): PQ about -0.095 for V1S1, -0.036 for V2S1 and -0.026 for V1S2; V2S2 gains about +0.009. Recall_interior_decided, measured: -0.19, -0.25, -0.12 and -0.03.
  - confidence: high that this is where the loss is; low on which recipe change causes it (the census cannot separate them)
  - round 2: - Before training, separate the two networks: one inference-only row that feeds area_ng1's maps to each new line net, and the reverse. This needs GPU inference, which this task did not allow.
- Teach the street sides Ben added as positives with extra weight (347 on plate 5, 71 on 1A).
- Add narrow passages and alleys as an explicit check, using Ben's blocks 3-4-9-10-11 and 18-30 style ground on non-44 plates.
- Check whether choosing the checkpoint on the 9-block 1A region rewards merging.
- **C2** Extra false blocks are mostly the same open land cut into more pieces: by Mill Creek, the Erie canal and the railway, and the Ludlow estate. The baseline already calls this ground one big false block; the new area nets cut it along creek banks, the canal and railway edges, and PQ counts every piece.
  - evidence: Measured (fp_cover.py).
- Non-merge false blocks per grid: baseline 5.0, the pairs 7.8-16.2. Of those, 6.7-14.7 are pieces at least 50% inside the baseline's own false ground.
- False-block area in undecided ground: 24.4 Mpx for the baseline against 20.0-22.9 Mpx for the pairs.
- False blocks on decided ground: 6.3-7.0 against 6.7.
- On grid 0 the baseline has one 18.1 Mpx false block, which V2S2 splits into pieces of 7.1, 5.8, 1.2, 1.0 and 0.9 Mpx.
- Crops err_4, err_6 and err_10; overview_*_g0.jpg.
  - size: Estimate (pq_parts.py): PQ about -0.048 (V1S1), -0.037 (V2S1), -0.014 (V1S2), -0.038 (V2S2). This is all of V2S2's loss: its PQ_decided is +0.009 (4 of 6 grids up) and precision_decided +0.0085 (6 of 6), both measured.
  - confidence: high
  - round 2: - Ask Ben whether open land by the creek, canal and railway is block or not. Today the pseudo labels teach it as block (open issue 3 of the 23 Nov findings), while 44's truth leaves it out.
- Teach creek banks, canal edges and railway edges as 'not a street side', per Ben's water rule.
- Report PQ_decided and false-block area beside PQ in the shipping rule, so that cutting one false block into pieces is not read as new error.
- **C3** V1 places block sides on the water pipes and sewers that run down the middle of streets, instead of on the block line. The outline step slides each side onto the strongest detected line nearby.
  - evidence: Measured (xtab.py, summarize.py).
- Pipe and sewer share of the new false length on decided ground: V1S1 34%, V1S2 42%, V2S1 11%, V2S2 5%.
- All false length on pipe ink: baseline 5.5k px; V1S1 12.1k; V1S2 10.8k; V2S1 1.8k; V2S2 1.0k.
- Line net P at the new false samples, pair against baseline: 0.46-0.60 vs 0.15-0.29.
- Crops err_2, err_3 and err_7: the side sits on the '6-inch W. PIPE' or '12-inch SEWER' line in the street while Ben's line beside it is lost.
  - size: About 9-10k px of the new false length per grid in V1, measured. Its effect on PQ is not separated from C1.
  - confidence: high
  - round 2: - Make pipe and sewer ink in street ground (bins 6 and 7) explicit 'not a line' targets for the line net.
- V2's pseudo plates appear to have taught this already, so keep that part.
- **C4** Numbers printed near street lines (Ben's point). They pull false lines only in V2S1, which is a seed-dependent failure. The other three pairs are at chance.
  - evidence: Measured (summarize.py, xtab.py).
- False length on numbers within 40 px of a street: V2S1 12.7%, baseline 6.5%, the others 5.0-5.9%.
- Inside the 5-40 px band (chance 23.3%): V2S1 39%, baseline 26%, the others 23-24%.
- Line net mean P on those numbers: V2S1 0.079, baseline 0.049, the others 0.044-0.047.
- In absolute terms every pair has more false length on text than the baseline (5.5-7.2k px against 3.7k) because it has more false lines overall.
- On plate 5, 14 deleted lines lie mostly on text, 5-34 px from a kept street (deletions2.py).
  - size: Small on 44. About 2.5-3.9k px of false length per grid lies on near-street numbers, against 1.5k for the baseline. That is 5-13% of the false length.
  - confidence: high (measured); medium that it matters more on plates like 5
  - round 2: - As Ben asked, add explicit 'not a line' targets on bin-8 ink within 40 px of street lines.
- Track the line net's mean P on near-street numbers (baseline 0.049) as a check at every evaluation, so that a seed like V2S1 is caught.
- **C5** Lines Ben deleted are not all 'no street here'. Most of the deleted length is a line he replaced or moved.
  - evidence: Measured (deletions2.py), read-only.
- Plate 5: 58% of the deleted length (93 of 214 non-sheet deleted lines) runs within 5 px of a kept line in the same direction. Only about 94 lines (14.4k px) are clean deletions.
- Plate 1A: 64%.
  - size: Not a cause of the 24 Nov loss. It decides how Ben's deletions can be used as negatives.
  - confidence: high
  - round 2: - Build the 'not a line' labels from deleted length that is more than 5 px from any kept line in the same direction.
- Keep the 34 sheet lines Ben marked wrong separate, since they are sheet-edge rules, not ink.

### files

All files are under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/errors/. A second copy of the scripts and results is in _second_copy/.

**Scripts** (system python, run with -B; read-only on the repo):
- collect.py: recomputes bench44's scores sample by sample. Writes runs/*.npz, *.json and *_inst.png.
- census.py: classifies the errors by ink, distance to Ben's lines, tint and region. Writes census.json and layers.npz.
- summarize.py: the tables. Writes summary.txt and summary.json.
- fp_cover.py: false blocks against the baseline's false ground, and the decided-ground scores. Writes fp_cover.json.
- pq_parts.py: the PQ counterfactual. Writes pq_parts.txt.
- xtab.py: decided-ground cross-tables and the robustness check. Writes xtab.json.
- clusters.py: the 10 biggest new errors. Writes clusters.json and pics/err_1..10.jpg.
- areacrop.py: area-map crops. Writes pics/area_err1..10.jpg.
- overview.py: quarter-size maps per pair. Writes pics/overview_{V1S1,V2S1,V1S2,V2S2}_g0.jpg.
- deletions.py and deletions2.py: Ben's deleted lines on plates 5 and 1A. Write deletions.json and deletions2.txt.

**Pictures worth opening:**
- pics/overview_V2S2_g0.jpg and pics/overview_V1S1_g0.jpg (red = new false, magenta = lost, orange = new false block);
- pics/err_1.jpg with pics/area_err1.jpg (the alley merges);
- pics/err_4.jpg (creek banks);
- pics/err_7.jpg (side moved onto a water pipe).

Nothing was written in tools/, unet_data, picks22_guided, streetmap, cufp, train_v2 or train_v2_runs: I checked this with find -newer. edges_ben.json and rail_ben.json were only read.

## recipe

I trained nothing and ran no network inference. I only read the code, the logs, the model files and the saved maps, and wrote into diag/recipe only. git status for tools/ is clean.

Short answer: the loss comes from the new AREA networks. The new line networks are not the problem. The swap agent's provisional evaluations pair area_ng1 with each of the four new line nets, and all four score PQ 0.511-0.516 on plate 44, the same as the baseline (0.511). I checked this pixel by pixel: given area_ng1's map as their 7th input, all four new line nets draw Ben's 44 lines better than lines_ng1 does. Given their own new area maps, three of the four get much worse. So the new area maps hurt twice: once in the outline step, and again through the line net's 7th input.

What changed between ng1 and V1, item by item:
- Same as ng1:
  - the four labelled plates (img, label and edge are byte-identical; lines.png is equal);
  - learning rate and schedule, crop size, batch size, 4000 iterations, augmentations, losses and network design;
  - the evaluation code.
  - Plate 44's baseline maps are byte-identical to the bench's maps on all 6 grids, and the baseline PQ (0.5106) equals the 21 Nov number.
- Changed, but negligible:
  - The line net's 7th input on the four plates is the batch's re-prediction, not the exact map lines_ng1 trained on. 0.30-0.39% of paper pixels change their block/street call.
  - The 255 squares in the guide do not matter when the guide is blank in use. In V1 the guide weights never moved from their starting values, and in use the guide input is zeros for every pair. What the squares did during ng1's training is unknown.
- Changed, and plausibly costly (all on the area side):
  1. Plate 1A takes 20% of the area net's crops. Each of its taught pixels is seen about 480 times, against 57-92 times on the labelled plates. Its labels are a different style:
     - 37% of its taught ground is street, against 13-20% on the old labels;
     - blank paper is taught as street 44% of the time, against 2-12%;
     - its open ground is not taught at all, while the old labels call open land block.
  2. The four labelled plates get only 74-88% as many crops as under ng1 (36-45% in V2).
  3. The checkpoint was chosen on 1A's right-hand region. That score ranks area_ng1 last of the five pairs, but plate 44 ranks it first. It chose iterations 3000-3500, while the learning rate was still well above zero. On area_ng1's own record, its street score on 44 was still rising after 3000.
  4. Different random seeds.

Two seeds of V1 differ by 0.10 PQ on 44. The area nets spread widely on Ben's ground (IoU street 0.715-0.838), and area_ng1 (0.816) falls inside that range. So area_ng1's 0.511 could well be a lucky draw. Only retraining the old recipe with 2-3 seeds can settle this.

The evaluation also matters here. The headline PQ counts false blocks in the 46% of 44 that Ben's map leaves undecided: the Mill Creek valley, the railways and the canal bed. The new area nets break that open land into more pieces: 12-16 against 9.2. That gives 7-15 false blocks there, against 4.2 for the baseline. Inside the ground Ben decided, false blocks are equal for all pairs (6.3-7.0). Under PQ_decided (only Ben's decided ground counts), V2S2 beats the baseline (+0.009, higher on 4 of 6 grids). The V2 seed mean then falls only 0.015 below the baseline, and V1 0.063 below.

On Ben's points:
- V2's pseudo labels for plate 5 taught 54% of the length of the 248 lines Ben deleted as true lines.
- They taught only 23% of the 347 lines he added as lines, and 8.5% of them as "not a line".
- On 1A, the lines he deleted were taught "not a line" over 44% of their length.

I made no new training round.

### numbers

Measured unless marked "estimate". All scripts are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/recipe/ (system python unless noted).

TRAINING DATA, 43/45/80/82A
- img.jpg, label.png and edge.png in train_v2 have the same sha256 as unet_data's N_img.jpg, N_label.png and N_edge.png. (sha256sum, run by hand; recorded in no file)
- lines.png equals edgenet.load's target: the integrator's verify_train_v2.json, not re-run by me.
- 7th input: train_v2 area_in.png against the maps lines_ng1 actually trained on (ml_review snapshots taken before the batch overwrote them on 21 Nov at 10:06-10:35). Share of paper pixels whose >127 call flips: 43 0.297%, 45 0.294%, 80 0.341%, 82A 0.394%. Mean |difference| 0.9-1.1 grey levels. (ch7_vs_ng1_training.py)
- Plate weights: 1.0 for all four plates in V1 and V2. Learning rate (Adam 1e-3, cosine to 0 at 4000), crops 384/448, batch 8/6, 4000 iterations, augmentations and losses are all unchanged. (unet_ng1_to_head.diff, edgenet_ng1_to_head.diff: git diff 3824103..HEAD)

CROPS PER PLATE (crop_shares.py)
- Estimate: the ng1 area-net crops are inferred from its sampler and the acceptance rates.
  - Area-net crops: ng1 about 8615 / 8272 / 7176 / 7937 (43 / 45 / 80 / 82A).
  - V1 crops as a share of that: 0.74 / 0.77 / 0.88 / 0.80.
  - V2 crops as a share of that: 0.36-0.45.
  - 1A's share of all crops: V1 20.3%, V2 10%. The pseudo plates' share in V2: 50%.
- Times each taught pixel is seen in V1: 43 57, 45 78, 80 92, 82A 69, 1A 486. For ng1 (estimate): 77-104.
- Line-net crops, V1 as a share of ng1's (ng1's count estimated): 0.69-0.96; V2: 0.34-0.48. Crops per 1000 line pixels: 1A 20.8, the four plates 3.9-6.3.
- Learning rate at the chosen iterations: 3000 1.46e-4, 3500 3.8e-5, 3750 9.6e-6, 4000 0.

1A LABELS (ink_under_ben_lines.py, blank_paper.py; counts from meta.json)
- Whole plate: block 1.99M px, street 1.17M, untaught 2.93M. Paper 3.72M px, 15.3% of it untaught.
- Training part (left of Elm St): block 1.23M, street 0.75M.
- Street share of taught ground: 1A 0.37; 43 0.20, 45 0.17, 80 0.13, 82A 0.17; 44's 21 Nov label 0.24.
- P(street | blank paper, taught): 1A 0.44; 43 0.12, 45 0.055, 80 0.021, 82A 0.036.
- Street within 60 half px of the paper edge: 1A 0.68; 43 0.77, 45 0.41, 80 0.37, 82A 0.62; 44 0.57. So 1A is in line with the old labels at the edge.
- Street ground lying nearer a sheet-edge line than any other of Ben's lines: 13.9% of 1A's street (162k px; 75k in the training part). Sheet-edge lines are not scored in the line target.
- My ink test cannot check whether the sheet-edge lines have printed ink under them: the cut paper edge reads as ink (98.8% "on ink" on 1A).

WHERE THE AREA LOSS IS ON 44 (area44_confusion.py, grid 0, against 44's 21 Nov label)
- IoU street, ≥200 half px from the paper edge: baseline 0.689; new nets 0.546-0.626.
- IoU street, <60 px from the paper edge: baseline 0.817; new nets 0.743-0.839.
- So the loss is in the interior, not at the sheet edge.

AREA MAPS AGAINST BEN'S DECIDED GROUND (area44_vs_ben.py, 6-grid mean IoU street)
- baseline 0.816, V1S1 0.715, V2S1 0.741, V1S2 0.739, V2S2 0.838.

OPEN LAND (openland44.py)
- Undecided ground is 46% of 44's paper.
- Share of it called block: baseline 0.82; new nets 0.71-0.78.
- Pieces of 1500 half px or more: baseline 9.2; V1S1 15.5, V2S1 14.2, V1S2 12.2, V2S2 16.3.
- Picture check: pics/fp44_*.jpg (pic_fp44.py).

FALSE BLOCKS AND PQ_decided (paired_decided.py, from eval_v2.json)
- False blocks inside Ben's decided ground: baseline 6.67, V1S1 6.83, V2S1 7.0, V1S2 6.33, V2S2 6.33.
- False blocks outside it: baseline 4.17; V1S1 15.33, V2S1 11.5, V1S2 7.33, V2S2 11.83.
- Paired gain over the baseline, PQ: V1S1 −0.142 (higher on 0 of 6 grids), V2S1 −0.072 (0/6), V1S2 −0.040 (1/6), V2S2 −0.028 (1/6).
- Paired gain, PQ_decided: V1S1 −0.099 (0/6), V2S1 −0.040 (1/6), V1S2 −0.027 (2/6), V2S2 +0.009 (4/6).
- Seed means: V1 −0.091 PQ / −0.063 PQ_decided; V2 −0.050 / −0.015.

DOES THE 1A CHECKPOINT SCORE TRACK 44? (val_vs_44.py)
- My emulation of the trainers' 1A score matches theirs within 0.007 (swap_lines_check.py).
- Area IoU street on 1A's region: baseline 0.840, V1S1 0.882, V2S1 0.875, V1S2 0.908, V2S2 0.920.
- The same score on 44 against the 21 Nov target: 0.696 / 0.573 / 0.580 / 0.615 / 0.653.
- Spearman rank correlation of the 1A scores with 44 PQ: −0.1 over all 5 pairs; 0.8 over the 4 new pairs only (n = 4).
- On area_ng1's own record, 44 IoU street was 0.641 at iteration 3000, 0.690 at 3500 and 0.701 at 4000 (area_ng1.json). Estimated cost of stopping early, using that curve: about −0.06 at 3000 (V2) and −0.01 at 3500 (V1).

LINE NETS ARE NOT THE PROBLEM (swap_lines_check.py, grid 0)
- 44 line F1 against the 21 Nov target, fed area_ng1's map: V1S1 0.667, V2S1 0.668, V1S2 0.656, V2S2 0.682. lines_ng1: 0.633.
- Fed their own area map: 0.492 / 0.517 / 0.548 / 0.674.
- Recall of Ben's lines within 3 px, area_ng1's map against their own: 0.648 vs 0.481, 0.651 vs 0.505, 0.638 vs 0.555, 0.662 vs 0.614. lines_ng1: 0.627.
- Swap agent's numbers (provisional; read from diag/swap/eval/a__ng1+L_*/eval_v2.json): area_ng1 + new line nets give PQ 0.5157, 0.5108, 0.5123, 0.5114 (V1S1, V2S1, V1S2, V2S2).

MAP CALIBRATION AGAINST THE OUTLINE STEP'S THRESHOLDS (map_calibration44.py, 6-grid means)
- Line-map pixels between 90 and 127 (the two thresholds): 0.10-0.12% of paper for every pair, so the maps are near-binary.
- Area-map pixels in the 64-191 band: 10.0-12.2% for every pair.
- Share of drawn line pixels lying more than 12 px from Ben's lines: baseline 0.33; V1S1 0.47, V2S1 0.40, V1S2 0.41, V2S2 0.22.

GUIDE WEIGHTS (guide_weights.py, venv python, CPU, state dicts only)
- V1/V2 first-layer weights on the guide inputs: largest change from their starting values is 0.0.
- area_ng1's guide weights were trained (mean |w| 0.071).

PLATE 5 PSEUDO TARGET AGAINST BEN'S CHECK (plate5_pseudo_vs_ben.py; edges_ben.json read only)
- 248 lines he deleted (46.3k px): 54.4% taught as line, 0.1% as "not a line", 45.5% not scored.
- 347 lines he added (101k px): 22.7% line, 8.5% "not a line", 68.8% not scored.
- On 1A, the 68 lines he deleted: 43.6% "not a line", 42.4% line (within 2 px of a kept or added line), 13.9% not scored.

SEED NOISE (estimate)
- V1 seeds differ by 0.102 PQ, V2 seeds by 0.044.
- Pooled seed standard deviation ≈ 0.056 PQ, from only 2 pairs, so very uncertain.
- With that, 3 seeds per arm resolve differences of about 0.09 PQ or more. Resolving 0.05 needs about 10 seeds per arm.

EVALUATION
- The code hashes in all 5 eval_v2.json files equal the current tools files.
- Baseline maps are byte-identical to bench44_maps on grids 0-5 (sha256sum, run by hand; recorded in no file).
- Baseline 0.5106 equals docs/sanborn/bench_2026-11-21/critic/paired_stats.json new_mean 0.5106.

### causes

- **C1** The loss sits in the new area networks. Their maps make worse outlines, and they also degrade the new line nets through the 7th input. The line-net recipe (1A, pseudo plates, area-blank) did not cost anything.
  - evidence: Swap agent (provisional): area_ng1 + each new line net gives PQ 0.511-0.516 (baseline 0.511). Pixel check on 44: fed area_ng1's map, the new line nets reach F1 0.656-0.682 and Ben-line recall 0.638-0.662, against lines_ng1's 0.633 / 0.627. Fed their own area maps, three of the four fall to F1 0.49-0.55 and recall 0.48-0.55. The area maps' IoU street on Ben's ground: baseline 0.816; V1S1 0.715, V2S1 0.741, V1S2 0.739, V2S2 0.838.
  - size: Measured: essentially the whole gap. Each new line net scores the baseline's PQ when paired with area_ng1.
  - confidence: high (the swap numbers are provisional)
  - round 2: Keep the line recipe. Spend round 2 on the area net. Choose and check the line net with the area net it will actually be paired with, not with area_ng1's map: the trainers' 1A F1 moved by -0.05 to +0.07 when the partner map was swapped in.
- **C2** Plate 1A takes 20% of the area net's crops (10% in V2), and its map-style labels teach a different picture from the old labels.
  - evidence: Each 1A taught pixel is seen about 486 times, against 57-92 on the labelled plates. 1A's taught ground is 37% street (old labels 13-20%). 1A teaches blank paper as street 44% of the time (old labels 2-12%). Its open ground is untaught, while the old labels call open land block. On 44 the new area nets call less of the undecided open land block (0.71-0.78 against 0.82) and break it into 12-16 pieces (against 9.2). They lose IoU street in the interior (0.55-0.63 against 0.69), not at the sheet edge. They also gain on 1A's region (0.875-0.920 against 0.840). The extra street they call on 44's open land is blank paper only at the open land's base rate (47-54% against 50%), so the 'blank paper is street' link is not shown.
  - size: Estimate only: no run without 1A exists to separate it from C3-C5. The open-land false blocks alone cost 0.028 PQ (V1 seed mean) and 0.035 PQ (V2), measured as the PQ gap minus the PQ_decided gap.
  - confidence: medium
  - round 2: Weight 1A by its taught area (about 4-5% of the crops), not at a full 1/5 share. Ask Ben to settle the open-land convention, then teach it the same way on every plate (or leave it untaught everywhere). Do not let the plate that holds the validation ground dominate training. The sheet-edge street bands (13.9% of 1A's street) are in line with the old labels at the edge and do not explain the loss.
- **C3** Checkpoint choice on 1A's right-hand region. The score there does not track plate 44 across recipes, and it picked early checkpoints.
  - evidence: The 1A region ranks area_ng1's map last of the five pairs (IoU street 0.840 against 0.875-0.920) and its lines last too (F1 0.707 against 0.740-0.833), while 44 ranks the baseline first. Spearman correlation with 44 PQ is -0.1 over all 5 pairs and 0.8 over the 4 new ones (n = 4). The area nets were kept at iterations 3500 (V1) and 3000 (V2), with learning rate 3.8e-5 and 1.5e-4. On area_ng1's own 44 record, IoU street was 0.641 at 3000, 0.690 at 3500 and 0.701 at 4000. V2S2's 3000 checkpoint was a spike on 1A (0.9255, with 0.904 and 0.901 either side). The 1A region is in-plate for the new nets: the left part of 1A was trained on, it is the same scan, and it holds only 9 of Ben's blocks.
  - size: Estimate from area_ng1's own curve: about -0.06 IoU street on 44 for V2's area nets (kept at 3000) and about -0.01 for V1 (3500). The effect on PQ is not measured.
  - confidence: medium-low
  - round 2: Now, with GPU inference only: evaluate area_v2*_last.pt with lines_ng1 and with their own line nets (about 3 min each). In round 2, keep the last weights (the learning-rate schedule ends at 0), or choose on held-out ground from several plates that are not trained on.
- **C4** Fewer passes over the four labelled plates, because more plates share the same 4000 iterations.
  - evidence: Area-net crops on 43/45/80/82A are 74-88% of ng1's in V1 and 36-45% in V2. Line-net crops are 69-96% (V1) and 34-48% (V2). area_ng1's 44 score was still rising at iteration 4000.
  - size: Unknown. Estimate: small to moderate for V1, larger for V2 (but V2 beat V1 by 0.041 PQ on the seed mean).
  - confidence: low-medium
  - round 2: Scale the iterations with the data, so each labelled plate keeps about ng1's 8000 area crops; or sample by taught area.
- **C5** Seed noise in the area network. area_ng1 is a single draw from an unseeded start and may have been lucky.
  - evidence: V1 seeds give PQ 0.368 and 0.470; V2 seeds 0.438 and 0.482. The four new area nets span IoU street 0.715-0.838 on Ben's ground, and area_ng1 (0.816) falls inside that span; V2S2's area net is above it. Line-net seed noise is small: 0.511-0.516 when each new line net is paired with area_ng1.
  - size: Estimate: pooled seed standard deviation about 0.056 PQ, from only 2 pairs, so very uncertain. V2's gap (-0.050) is within about 1 standard deviation; V1's gap (-0.091) is about 1.6.
  - confidence: plausible, unproven
  - round 2: Not run; described only. Arm O: the 21 Nov area recipe (guide shifted, 255 squares, plates 82A/80/43/45 trained whole, 4000 iterations, keep last, 44 not loaded) with seeds 1-3. This needs a --seed on the old trainer path, seeding torch and the sampler. Pair each with lines_ng1 (and optionally its own line net, trained on its own img.jpg maps). Arm N: --data train_v2 43 45 80 82A, seeds 1-3, keep last (V1 without 1A). Arm L: the existing _last.pt files, no training. Score all with eval_v2 on 6 grids, reporting PQ, PQ_decided and area IoU on Ben's ground. Cost: about 6 area trainings of 47 min plus about 10 evaluations, roughly 5 h of GPU. Arm O's spread answers 'lucky draw'; O against N tests the sampler and the 255 squares; N against V1 tests 1A; L tests keep-best. Three seeds resolve only gaps of about 0.09 PQ or more; 0.05 needs about 10 seeds per arm.
- **C6** The headline PQ counts false blocks in the ground Ben's map leaves undecided (46% of 44's paper: the Mill Creek valley, the railways, the canal bed, the estates). The new area nets break that open land into more pieces than area_ng1 does.
  - evidence: False blocks inside Ben's decided ground are equal for all pairs (6.3-7.0). False blocks outside it: baseline 4.2; new pairs 7.3-15.3. PQ_decided gains over the baseline: V1S1 -0.099, V2S1 -0.040, V1S2 -0.027, V2S2 +0.009 (higher on 4 of 6 grids). The merged outline step's settings (ring closure, HOLE_PARENT 3, the rail rules) were themselves chosen on 44 with ng1's maps. Its fixed thresholds do not favour ng1's calibration: the line maps are near-binary for every pair (0.10-0.12% of paper between 90 and 127). Evaluation code and baseline maps are identical to the bench.
  - size: Measured: 0.028 PQ (V1 seed mean) and 0.035 PQ (V2) of the gaps; all of V2S2's gap (-0.028 PQ against +0.009 PQ_decided).
  - confidence: high
  - round 2: Report PQ_decided beside PQ in the shipping rule. Ask Ben whether open land is block or not, so a net is neither rewarded nor punished for how finely it cuts the creek valley.
- **C7** Changes that are NOT the cause: the labelled plates' data, the training settings, the guide squares at use time, and the evaluation itself.
  - evidence: img, label and edge are byte-identical, and lines.png is equal. The 7th input differs from lines_ng1's training input on 0.30-0.39% of paper pixels. Learning rate, crops, batch, iterations, augmentations and losses are identical (git diff 3824103..HEAD). The V1/V2 guide weights stayed exactly at their starting values (largest change 0.0), and the guide input is zeros in use for every pair. Every evaluation carries the current tools' code hashes, and the baseline maps are byte-identical to bench44_maps.
  - size: Measured: about 0.
  - confidence: high
  - round 2: Nothing to fix. Make the trainer and the batch read the same input (img.jpg or a fresh resize) so the 7th input stays exact. Keep the guide blank.
- **C8** V2's pseudo targets taught the batch's own mistakes. This is Ben's point that the deleted lines matter as much as the missed ones.
  - evidence: Plate 5, against Ben's check of 25 Nov: 54.4% of the length of the 248 lines he deleted as wrong was taught as true line, and only 0.1% as 'not a line'. Of the 347 lines he added, 22.7% was taught as line and 8.5% as 'not a line'. On 1A (map labels) the lines he deleted were 43.6% 'not a line'. The area net never sees deletions at all: its labels are block and street ground only.
  - size: No measured cost on 44 in this run: V2 beat V1 by 0.041 PQ on the seed mean, and V2's line nets score 0.511 with area_ng1.
  - confidence: high for the label counts; the effect is unmeasured
  - round 2: Where Ben has checked a plate (5, 1A), build its targets from his check: deleted lines as strong 'not a line', added lines as line, with the pseudo targets dropped there. Also make deletions reach the area label: a deleted side should not become a block edge.

### files

Everything below is under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/recipe/.

Scripts and their results (system python unless noted):
- Code diffs, ng1 commit 3824103 to HEAD: unet_ng1_to_head.diff, edgenet_ng1_to_head.diff
- 7th input against what lines_ng1 trained on: ch7_vs_ng1_training.py, ch7_vs_ng1_training.json
- Crops per plate, learning rate at the chosen iterations: crop_shares.py, crop_shares.json
- 1A label style, ink under Ben's lines, labels at the paper edge: ink_under_ben_lines.py, ink_under_ben_lines.json
- Blank paper taught as street: blank_paper.py, blank_paper.json
- Map calibration against the outline step's thresholds, side states: map_calibration44.py, map_calibration44.json
- 1A checkpoint score against 44: val_vs_44.py, val_vs_44.json
- Area errors on 44 by distance from the paper edge: area44_confusion.py, area44_confusion.json
- Area maps against Ben's decided ground: area44_vs_ben.py, area44_vs_ben.json
- Open land on 44: openland44.py, openland44.json
- PQ against PQ_decided gains: paired_decided.py, paired_decided.json
- Line nets fed area_ng1's map against their own area map: swap_lines_check.py, swap_lines_check.json
- Guide weights (venv python -B, CPU only): guide_weights.py, guide_weights.json
- Plate 5 and 1A targets against Ben's check: plate5_pseudo_vs_ben.py, plate5_pseudo_vs_ben.json
- Pictures: pic_1A_label.py writes pics/1A_label_lines.jpg, 1A_label_lines_full.jpg, 43_label.jpg and 82A_label.jpg. pic_fp44.py writes pics/fp44_baseline.jpg, fp44_V1S1.jpg, fp44_V1S2.jpg, fp44_V2S2.jpg, plus fp44_grid0.json.
  - In fp44: green = matches one of Ben's blocks, blue = merge, red = false block in his decided ground, orange = false block in undecided ground.
  - It is my own rough classification of grid 0, so its counts differ a little from bench44's.

Second copy of all scripts and both diffs: _second_copy/

Read but not written: train_v2_runs/models/*.json; train_v2_runs/eval/*/eval_v2.json, maps44, maps1A, runs44; unet_data/models/area_ng1.json, lines_ng1.json, train_ng1.log; ml_review_2026-11-21/verify-line-net/snap/; and the swap agent's diag/swap/eval/a__ng1+L_*/ (provisional). edges_ben.json was read only, never written; I did not open rail_ben.json.

## ben-labels

Ben's two points hold up against the code and the measurements. The labels do not explain all of the loss, though: V1's line labels handle deletions and numbers about as well as the baseline's plates, so V1's drop needs another cause (recipe or seed). Nothing was trained, no GPU was used, and nothing outside diag/ben-labels was written.

1. DELETED LINES. Most of the lines Ben deleted were not false lines. They were spare copies of a real street side: 38 of 65 on 1A, 116 of 214 on 5, 129 of 159 on 44. A spare copy sits on true ink, so it must stay positive. The truly false ones (21 on 1A, 83 on 5, 26 on 44) lie on water pipes, lot lines, numbers, building outlines and streetcar lines.
   - 1A, Ben's map label (used in V1 and V2): about 95% of the false lines' pixels are already taught negative. The weight is the ordinary ink weight of 4, so they hold only 0.8% of the negative loss weight. It still helped where it was taught: the nets' response on those lines fell from 66% (baseline) to 13-27%.
   - 5, pseudo label (used in V2, made before Ben checked 5): it taught 51 of the 83 false lines as LINES. None of their pixels were negative.
   - 5, Ben's misses: 28 of the 347 lines he added were taught as "not a line", and 73% of the added lines' pixels were not scored.
   - This is built into the pseudo recipe. Negatives must stay 6 px or more from anything the line net already fires on. So 0% of the baseline's false response on 5 was ever negative: 94% unscored, 6% taught positive.
   - Area net: the ground under and beside false lines is labelled correctly on map plates (mostly street, some block), but it is not weighted up. On pseudo 5 it is 100% untaught.

2. NUMBERS NEAR STREETS. Numbers are taught as negatives at the same weight as any other ink (about 3.1-3.3 on average), not more.
   - 6-22% of the number ink within 40 px of a true line sits in the 2-9 px band beside it. 67-100% of that band is not scored.
   - In V2, half the line-net crops come from pseudo plates. There, 47-74% of the numbers near lines are not scored: 39% across V2's crops, against 20% for V1 and the baseline.
   - On 44, numbers make up 19-30% of the line nets' false pixels. That is not more than their share of all ink (44%). Water pipes and lot lines are the bigger sources.
   - In the editor lines Ben actually sees, it is clear. False lines that run mostly through numbers went from 25 (baseline) to 40-53 in all four new pairs. By eye, they are drawn along rows of house numbers 20-40 px inside the block and along lot-dimension numbers.
   - Area net errors are not more frequent near numbers on 44. On 1A they are about 1.7-2 times more frequent.

3. SHEET-EDGE STREETS.
   - 1A: the 19 lines Ben drew along the sheet edge all have printed ink under them, and are rightly taught positive. The sheet-outline pieces are not scored.
   - 5: 45 of 55 have no ink. They are short stubs along the paper's street tabs (median 28 px, 2,397 px in all). The pseudo label leaves them unscored. The map recipe would teach them 100% positive, which is 0.6% of 5's positives. Small, but it teaches "draw on bare paper".
   - 44: 13 drawn lines and 5 printed lines along the edge have no ink and are taught positive.

4. PROPOSAL (see causes). The line net would treat:
   - Ben's false deletions as hard negatives at weight 16. Spare copies stay positive.
   - number ink as negative everywhere on the paper, including the band beside a line, at weight 10 within 40 px of a line and 6 beyond. Ink within 2 px of a true line is protected.
   - inkless drawn lines as not scored.
   - on fully checked plates, all paper more than 8 px from his lines as "not a street side".

   Static estimate, not a prediction of PQ:
   - 1A's held-out region: the share of today's false response under a negative weight goes from 50-75% to 80-89%, with 32-58% at weight 6 or more. Scoring the whole paper raises it to 91-97%.
   - 5: from 0% (pseudo label) or 64% (Ben's map label) to 78%; 96% with the whole paper scored.
   - 44: from 28-62% to 44-70%; 97-99% with the whole paper scored.
   - Pseudo line labels should not be used again. Plate 5 now has its own label from Ben's check.

### numbers

All MEASURED unless marked ESTIMATE. Scripts are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/ben-labels/scripts/ (run from data/sanborn with system python -B).

-- Groundwork --
map_now.py: rebuilding 1A's map labels in memory gives train_v2/1A/lines.png and label.png pixel for pixel (0 px differ). So the 5-now and 44 labels are what today's code would make. 44 is never trained; its label is for diagnosis only.
edges_ben.json: 5 was saved 25 Nov 14:20Z, after train_v2/5 was made on 24 Nov. 1A's label used today's file (24 Nov 00:31Z).

-- Q1: deleted network lines, split into spare copies / part copies / false lines (deleted_split.py) --
Split, 1A: 65 deleted = 38 spare copies / 6 part / 21 false (lengths 11043 / 911 / 4752 px).
Split, 5: 214 = 116 / 15 / 83.
Split, 44: 159 = 129 / 4 / 26.
Main ink under each false line, 44 (26 lines): text 13, water pipe 6, sewer 2, streetcar 2, other 3.
Main ink, 5 (83): water pipe 28, lot line 22, text 12, building 10, streetcar 6, sewer 4, block line 1.
Main ink, 1A (21): building outline 10, lot line 5, text 3, streetcar 2, pipe 1.

-- Q1: how the false lines are taught (3 px wide) --
1A map label (V1, V2): 94.7% negative, 0.5% positive, 4.8% not scored. All 21 lines are mostly negative. Weight = NEG_INK 4 on ink, like any ink.
1A: false lines hold 0.8% of the plate's negative loss weight (estimate.py).
5 pseudo label (V2): 56.2% positive, 0% negative, 43.8% not scored. 51 of 83 lines are mostly positive.
5 map recipe on Ben's 25 Nov lines (not trained): 92.1% negative.
44 map recipe (hypothetical): 97.7% negative.

-- Q1: how the spare copies are taught --
1A: 70% positive, 28% not scored, 2% negative.
44: 62% positive, 36% not scored, 1.6% negative.

-- Q1: area net under false lines (label 0 street / 1 block / 255 untaught) --
Under, 1A: 58 / 39 / 3%. Beside, 1A: 53 / 39 / 8%.
Under, 5 pseudo: 0 / 0 / 100%. Beside, 5 pseudo: 6 / 2 / 92%.
Under, 5 map: 67 / 13 / 20%.
Under, 44 map: 65 / 25 / 11%.
(taught_ben_lines.py, deleted_split.py)

-- Q1: lines Ben added (misses) (taught_ben_lines.py) --
1A map: 99.99% positive (70 of 71 lines).
44 map: 100% positive.
5 pseudo: 19.0% positive, 8.4% negative, 72.6% not scored. 28 of 347 lines mostly negative; 251 mostly not scored.
5 pseudo, area net under the misses: 26% block, 74% untaught.
5 pseudo, moved lines' old (wrong) places: 21 of 27 taught positive.

-- Q1: plate 5 pseudo label against Ben (pseudo_vs_ben.py) --
Precision 94.8% within 6 px. Recall 64.5%.
Ben's line pixels in the pseudo label: 54% positive, 3% negative, 43% not scored.
Baseline's false pixels on 5 under the pseudo label: 0% negative, 94.2% not scored, 5.8% positive (estimate.py).

-- Q1: did 1A's negatives work? Share of the false deleted lines' core the nets still draw, whole plate / held-out region (pseudo_vs_ben.py) --
baseline 66% / 34%. V1 20-27% / 26-34%. V2 13-14% / 12%.

-- Q2: number ink within 40 px of a true line (text_near_lines.py) --
44 map: 1.07M px. 8.3% of it in the 2-9 px band beside the line, and 67% of that band is not scored. Overall 81% negative, 15% not scored. Mean weight 3.32.
1A map: 0.43M px. 20.7% in the band (73% not scored). Overall 80% negative, 20% not scored. Weight 3.13.
5 pseudo: 1.74M px. 21.8% in the band (100% not scored). Overall 37% negative, 63% not scored. Weight 1.48.
5 map now: 22.8% in the band (67% not scored). Overall 82% negative. Weight 3.26.
43 (make_labels.py): 17.4% in the band (82% not scored). Overall 64% negative, 17% positive. Weight 3.05.
Other ink 9-40 px from a line gets weight 3.40-3.83, the same as numbers.

-- Q2: every training plate (text_all_plates.py) --
Numbers within 40 px of a line left not scored: label plates 19-22%, 1A 20%, pseudo plates 47-74%.
Crop-weighted: baseline plates 20.1% not scored (weight 3.17); V1 20.0% (3.16); V2 39.4% (2.40).
Pseudo plates are 12,092 of V2's 24,000 line-net crops.
Positive pixels with number ink within 1 px: label plates 20-31% (house numbers touching the line); 1A 0.3%.

-- Q2: line-net false pixels on 44, grid0 (more than 6 px from Ben's lines) (false_response.py) --
Share on numbers: baseline 24.2%, V1S1 19.2%, V1S2 22.3%, V2S1 29.4%, V2S2 24.3%. Grid3 is within 1 point.
Numbers are 44.5% of 44's ink, so false response is not concentrated on numbers.
Water pipes: 38.6 / 31.8 / 32.5 / 28.1 / 8.6% (same order of pairs).
Lot lines: 12.6 / 18.2 / 20.7 / 23.7 / 39.9%.
Distance of the false pixels on numbers from the nearest true line (estimate.py): baseline 6% at 6-9 px, 13% at 9-20, 15% at 20-40, 66% beyond 40. V2S1: 6 / 24 / 25 / 45%.

-- Q2: false editor lines on 44, grid0 (fewer than 20% of points within 8 px of Ben's lines) (false_response.py) --
baseline 101 of 376; text-dominated 25.
V1S1 223 of 469; text 46.
V1S2 214 of 515; text 40.
V2S1 152 of 407; text 53.
V2S2 155 of 444; text 46.
Pictures confirm rows of house numbers and lot-dimension numbers.

-- Q2: 1A held-out region (false_response.py) --
Share of false pixels on numbers: baseline 28.4%, V1S1 37.0%, V1S2 34.7%, V2S1 60.2%, V2S2 50.1%.
V2: 61-69% of the false pixels are 6-20 px from a true line.

-- Q2: area net error rate near numbers vs away --
44 baseline 7.2% vs 8.0%. 44 new pairs 6.0-11.8% vs 6.3-11.4% (no excess).
1A held-out: baseline 8.9% vs 5.4%. New pairs 4.6-7.6% vs 2.5-3.7%.

-- Q3: sheet-edge lines (sheet_edge_lines.py, edge_pseudo5.py) --
1A: 19 of 69 drawn lines lie along the edge (median distance 60 px or less). 0 without ink (support 0.87-1.0, checked by eye). All positive, which is right.
1A: 12 sheet-outline pieces, 10 without ink; 100% not scored.
5: 55 of 347 drawn lines along the edge. 45 without ink (support under 0.3; 2,397 px in all, median 28 px), 2 weak, 8 inked.
5: those 45 are 100% not scored in the pseudo label and 100% positive in the map recipe (0.59% of the plate's positives).
5: 80 sheet-outline pieces, 65 without ink; 99.5% not scored.
44: 13 of 16 drawn lines along the edge without ink, plus 5 printed lines without ink (4,605 px). All taught positive by the map recipe.

-- Q4: proposed label, ESTIMATE from today's maps, no training (estimate.py, estimate_complete.py, estimate_plus_bins.py) --
Each line: share of the false pixels taught negative now -> share under the proposal (share at weight 6 or more; mean weight now -> proposed) -> share with the whole paper scored.
1A held-out, baseline: 67% -> 81% (hard 32%; weight 2.30 -> 4.72) -> 97%.
1A held-out, V1S1: 75% -> 89% (42%) -> 96%.
1A held-out, V1S2: 62% -> 80% (37%) -> 94%.
1A held-out, V2S1: 62% -> 86% (58%; 1.98 -> 6.48) -> 93%.
1A held-out, V2S2: 50% -> 82% (54%) -> 91%.
5 baseline: pseudo 0% / map 64% -> 78% (32%; 2.18 -> 5.00) -> 96%.
44 baseline: 62% -> 70% (25%) -> 98%.
44 V1S1: 56% -> 64% (20%) -> 99%.
44 V1S2: 56% -> 67% (23%) -> 98%.
44 V2S1: 59% -> 70% (29%) -> 98%.
44 V2S2: 28% -> 44% (25%) -> 97%.
Number rule alone covers: 44 19-29% of false pixels; 1A held-out 29-57%; 5 25%.
Deletion rule alone covers: 1A 3-12%; 5 11%; 44 1% (44's deletions came from an older guided run).
Variant with lot-line, rail, streetcar, pipe and sewer ink also negative beyond 9 px: 44 88-95%, 1A held-out 87-95%, 5 94%.
Cost: negative-to-positive loss weight 16.6 -> 24.8 (1A), 18.3 -> 27.3 (5), 17.7 -> 28.3 (44).
Cost: numbers' share of the negative weight 22-23% -> 46-50%; deletions' share 0.5-0.8% -> 1.5-2.2%.
Positive pixels lost to the inkless rule: 0 on 1A, 0.6% on 5, 2.1% on 44.

### causes

- **C1** The pseudo labels (V2) taught the networks' own false lines as lines, and by construction can never teach 'not a line' where the network already fires
  - evidence: Plate 5 is the only pseudo plate Ben has checked.
- 51 of its 83 false lines were taught positive, with 0% of their pixels negative. 28 of Ben's 347 added lines were taught negative; 73% of the added lines' pixels were not scored. 21 of 27 wrongly placed lines were taught positive at their old place.
- The baseline's whole false response on 5 is 0% negative, 94% not scored and 6% positive under the pseudo label. This follows from the recipe: negatives must stay 6 px or more from any line-net response above 0.1.
- Pseudo precision against Ben is 94.8%, recall 64.5%. (deleted_split.py, taught_ben_lines.py, pseudo_vs_ben.py, estimate.py)
  - size: Pseudo plates are 50.4% of V2's line-net crops. On 5, 56% of the false lines' pixels were taught as lines. This caps what V2 can unlearn. V2 still beat V1 for both seeds, so it is not the main cause of the loss against the baseline.
  - confidence: high that the labels behave this way; medium on how much 44 PQ it costs
  - round 2: Do not use pseudo line labels. Use plate 5 as a map plate with the 25 Nov check. If pseudo plates stay, use them only for the area net, at low weight.
- **C2** Numbers are taught no more strongly than any other ink. The ones hugging a line are not scored, and in V2 39% of the numbers near lines were not scored
  - evidence: Number ink 9-40 px from a line: about 90% negative at weight 3.5-3.9, the same as other ink.
- In the 2-9 px band beside a line, 67-100% of the number ink is not scored. Overall not scored near lines: map and label plates 15-20%, pseudo plates 47-74%. Crop-weighted: 20% for baseline and V1, 39% for V2.
- 44: false editor lines that run mostly through numbers went from 25 (baseline) to 40-53 in all four new pairs. By eye they follow rows of house numbers 20-40 px inside the block.
- 1A held-out: numbers are 28% of the baseline's false pixels and 35-60% of the new pairs'.
- But on 44 numbers are only 19-30% of the false pixels, against 44% of all ink. Pipes and lot lines are larger sources. (text_near_lines.py, text_all_plates.py, false_response.py, crops_false_text.py)
  - size: 15-28 extra text-driven false lines per new pair on 44 (grid0). Numbers are 19-30% of 44's false pixels and 29-60% on 1A's held-out region.
  - confidence: medium. V1 has the same number treatment as the baseline yet also doubled its text false lines, so numbers partly reflect a general rise in false lines that the labels do not explain.
  - round 2: Make number ink (ink_bins bin 8, dilated 1 px) negative everywhere on the paper, including the band beside a line. Keep everything within 2 px of a true line out of it, because house numbers touch the line. Weight 10 within 40 px of a line, 6 beyond. Raise POS from 3 to about 4.5 to keep the negative-to-positive balance.
- **C3** Ben's deletions are mostly spare copies of real lines. The truly false ones are taught negative on map plates, but only at the ordinary ink weight
  - evidence: Spare copies or part copies of a final line: 44 of 65 deletions on 1A, 131 of 214 on 5, 133 of 159 on 44. They are correctly kept positive or not scored.
- False ones on 1A: 95% negative at weight 4. They hold 0.8% of the negative weight. That still helped: the nets' response on them fell from 66% (baseline) to 13-27%, and in the held-out region from 34% to 12% (V2).
- Old code (make_labels.py) blanks a deleted line, leaving it not scored, instead of using it as a negative. (deleted_split.py, pseudo_vs_ben.py, estimate.py)
  - size: The deleted strips cover 3-12% of the false response on the training plates. Raising their weight to 16 lifts their share of the negative weight from 0.8% to 2.2% (estimate).
  - confidence: high
  - round 2: Split each deletion against Ben's final lines. A spare copy (60% or more of its points within 6 px of a final line) gets no change. A false line or part copy gets an 11 px strip, only where it is more than 8 px from every final line, made negative everywhere on the paper: weight 16 on ink, 4 off ink. A moved line's old place more than 8 px from the new place is treated the same. Area net: weight the ground near false lines like a verified edge (1 + 6·exp(-d/4)). The area net's edge output should get target 0 on the false line's core at BCE weight 6.
- **C4** The map recipe leaves large parts of a fully checked plate unscored, so 'not selected' is not taught. The false response lies largely in that ground
  - evidence: Under the map recipe, 38-72% of 44's false pixels and 25-50% of 1A's held-out false pixels are not scored.
- 44's map label leaves 27.3M of 64M paper pixels not scored; open land, rail yards and the band beyond the street rays are never scored.
- Scoring as negative all paper more than 8 px from Ben's lines (any kind) would reach 97-99% of 44's false pixels, 91-97% on 1A held-out, 96% on 5. (estimate_complete.py)
  - size: The largest single change in static coverage: from 28-62% to 97-99% on 44 (estimate).
  - confidence: medium. It is only valid where Ben has checked the whole plate (44, 1A, 5), and it adds 1.7M negative pixels on 1A and 3.6M on 5.
  - round 2: On fully checked plates, score as negative every paper pixel beyond LINE+GAP+1 (8 px) of his final lines. Pixels off ink get weight 1, ink 4, with the number and deletion weights on top. Leave the area label alone there, since open land is not settled. A variant also makes his ink classes for lot lines, rail, streetcar, water pipe and sewer negative beyond 9 px at weight 6.
- **C5** Ben's inkless street stubs at the sheet edge would be taught as positive line ink
  - evidence: 1A: none. All 19 edge lines he drew lie on printed ink (checked by eye).
- 5: 45 of 55 have no ink (2,397 px in all, median 28 px). The map recipe teaches them 100% positive; the pseudo label leaves them not scored.
- 44: 13 drawn lines and 5 printed lines without ink are taught positive.
- Sheet-outline pieces are already not scored (99.5-100%). (sheet_edge_lines.py, edge_pseudo5.py)
  - size: Small: 0.59% of 5's positive pixels, 0 on 1A, 2.1% on 44. It did not touch V1 or V2.
  - confidence: high
  - round 2: A line whose ink support is under 0.3 is not scored, with the same margin as a sheet edge. The street map and the area label keep it. Ben could also mark these lines 'none', which the code already treats as not scored.
- **C6** Numbers are not a problem for the area net on 44. Its label under deleted lines is right but not weighted up
  - evidence: 44 error rate near numbers vs away: baseline 7.2% vs 8.0%; new pairs 6.0-11.8% vs 6.3-11.4%. On 1A it is 1.7-2.1 times higher near numbers.
- Ground under false lines: 1A 58% street / 39% block; 44 65% / 25%. 5 pseudo: 100% untaught. (false_response.py, deleted_split.py)
  - size: Small on 44, with no excess near numbers. Unknown on 1A.
  - confidence: medium
  - round 2: Leave the area label as it is. Add only the extra weight near false lines (C3). Optionally double the weight near numbers. Do not train the area net on pseudo labels at false lines.

### files

All outputs are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/ben-labels/ (nothing else was written; tools/, train_v2, unet_data, picks22_guided and Ben's files are untouched).

Scripts (run from data/sanborn with python -B), in .../diag/ben-labels/scripts/:
- common.py: shared helpers
- map_now.py: today's map labels for 1A, 5 and 44, in memory, written to map_now/. 1A matches train_v2 exactly.
- taught_ben_lines.py: Q1, deleted, added and moved lines against the current labels
- deleted_split.py: Q1, deletions split into spare copies and false lines, the ink under the false ones, and how each kind is taught
- pseudo_vs_ben.py: Q1, plate 5's pseudo label against Ben, and the 1A response on his deletions
- text_near_lines.py: Q2, numbers near lines by distance
- text_all_plates.py: Q2, numbers on every train_v2 plate, crop-weighted for V1 and V2
- false_response.py: Q2, what ink the false pixels lie on (44, 1A, 5), area errors near numbers, false editor lines on 44
- crops_false_text.py, crop_45_text.py, crop_1A_edge.py: pictures
- sheet_edge_lines.py, edge_pseudo5.py: Q3
- estimate.py, estimate_complete.py, estimate_plus_bins.py: Q4, the proposed label and its static coverage

Results (JSON): taught_ben_lines.json, deleted_split.json, lines_1A.json, lines_5.json, lines_44.json, pseudo_vs_ben.json, text_near_lines.json, text_all_plates.json, false_response.json, sheet_edge_lines.json, sheet_edge_rows_*.json, edge_pseudo5.json, estimate.json, estimate_complete.json, estimate_plus_bins.json.

Ink sorting re-run today with Ben's edits (ink_bins.py --save): bins_1A_now.png/.json, bins_5_now.png/.json, bins_43_now.png/.json.

Diagnosis-only labels (never for training): map_now/ (1A, 5 and 44 label, lines, edge and streetmap files).

Pictures checked by eye:
- false_text_lines_44_V2S1.jpg and false_text_lines_44_baseline.jpg: false lines drawn along house-number rows and lot-dimension numbers
- false_px_1A_heldout_V2S1.jpg and false_px_1A_heldout_baseline.jpg
- sheet_edge_crops_5.jpg: inkless stubs on the paper's street tabs
- sheet_edge_drawn_1A.jpg: 1A's edge lines lie on printed ink
- text_vs_pos_45.jpg: the number class is mostly real text; house numbers touch the block lines

## rail5

Rail on plate 5 (diag key rail5). Nothing in the repo was changed, nothing was trained and the GPU was not used. edges_ben.json and rail_ben.json were only read; rail_ben.json's sha256 is the same before and after.

1. Rules re-run with Ben's tracks off. I ran copies of today's ink_bins.py (commit 0c4c205) and rail_tracks.py on plate 5, with every write redirected into diag/rail5. Run on the networks' block ground without Ben's line edits, they give back the 80 rule tracks Ben was shown in the editor (unet_data/5_rail_rule.json, 21 Nov 18:50), track for track. So this run is exactly what Ben checked.
- Railroad: Ben drew none (the plate is marked complete), so all 23 rule railroad tracks are false: 4,691 px of track and 29,381 px of railroad ink.
- Streetcar against his 61 tracks (73,423 px): recall 76.2% at 10 px and 79.1% at 30 px, precision 100% at both. Of his tracks, 30 were found, 19 partly found and 12 missed. No false streetcar tracks.
- Ground changes the railroad result a lot. With no ground at all (how the batch ran on the morning of 21 Nov) the rules make 54 false railroad tracks (14,327 px). Adding Ben's line edits changes nothing for railroad.

2. The false railroad, checked in full-size crops. They sit in 9 places, and three kinds of ink fool the tick rule:
- **House numbers along the street side of a block** (George St, Sixth St, Fifth St and others): 4 places, 14 tracks, 1,539 px. The digits written against the block line look like ticks crossing it. These are the "numbers near the streets": 40-49% of their length lies within 8 px of Ben's street lines.
- **Lot lines with Sanborn hook marks**: 3 places, 6 tracks, 2,636 px. This includes the two long "In Lot" lines in blocks 49 and 50; the big block number "50" was even put in the railroad ink.
- **Lot numbers written across a lot line**: 2 places, 3 tracks, 514 px.

Two side effects:
- The outline step drops any block side lying on railroad ink. On 5 it dropped one real street side at y≈4012 (the house numbers 304-310), and Ben had to add a 543 px line there.
- The spacing between ticks cannot tell these apart from real track. False rows on 5 have a median gap of 72 px; true rows on 44 have 60-77 px.

3. The proposed fixes (rail_rules.diff, on copies), the first test on a plate they were not tuned on.
- One of the three ink_bins hunks had to be moved by hand, because ink_bins.py changed after the diff was made.
- The KEY mask does nothing on 5 (no KEY on the plate; the bins are identical, 0 px different).
- Railroad drops from 23 to 5 false tracks (4,691 to 2,253 px). Every house-number and lot-number row goes. The two long hook-mark lot lines stay, because they are longer than the 600 px cut.
- With no ground: 54 to 21 false tracks (14,327 to 8,769 px). The 15 left are 10 house-number rows and 5 hook-mark lines.
- Streetcar (the longer join, 350 px instead of 150): recall 76.2% to 80.8% at 10 px; missed tracks 12 to 8; found 30 to 34. Precision 100% to 98.7% (741 px). All of that "false" length is in three places where the line runs under a street name (STREET, VINE, ELM) and Ben's tracks stop. By eye, the track does carry on under the lettering. This is the same result as on 44.
- Plate 5 has now been studied closely, so it is no longer a clean test for further rule changes.

4. Keeping Ben's deleted rule tracks as negatives (design only, nothing changed).
- rail_ben.json gets a 'rejected' list. Each entry holds kind, pts, src 'rule', at (time) and rule {made, bins_made}. A rule track that Ben keeps but changes also gets a 'from_rule' record of its original points.
- edit_page.html:
  - del() (line 363) adds an entry before it removes an unchecked rule track;
  - snap('rail') and doUndo (lines 113-114) save and restore the list, so Ctrl+Z also takes a rejection back;
  - saveRail (line 222) sends the list;
  - the load (line 97) reads it back;
  - K, dragging or adding or removing a point, and the 'complete' tick record from_rule.
- edit_server.py /saverail (lines 158-171): check the entries like tracks. Keep the list already in the file when a save arrives without one (an older page still open), so it is never lost.
- The editor should only record the deletion; the reason is worked out later from the shapes. A rejected track counts as 'not rail' unless 80% or more of it lies within 10 px of one of his final tracks: then it was 'redrawn' (same kind) or the 'wrong kind' (other kind), and it is not a negative. This matters on 5: by shape, he changed or redrew 56 of the 57 rule streetcar tracks and kept only 1 as it was.
- Uses:
  - ink_bins.py and the outline step's 'on rail' test ignore railroad ink under rejected tracks;
  - the scorer counts rejected tracks as certain false positives, even on plates not marked complete;
  - a future rail learner gets them as hard negatives.
- Rejected rail must **not** become a negative for the street-line network. The house-number rows lie on real street sides.
- Plate 5's 23 deletions can be recovered exactly, because the rule file has not changed since Ben saw it. design/rejected_5_backfill_example.json shows them; writing them into rail_ben.json is Ben's call. (The line editor already records deleted lines: 248 lines marked 'wrong' on 5.)

On why the new network pairs did worse: rail is not an input to either network. Through plate 5's training labels the false rail did at most this: one 102 px side was dropped, and it was then neither taught as a line nor as a non-line. This is my reading of make_labels_v2.py, not a measurement. Rail is very unlikely to be a real cause of V2's loss.

### numbers

All are measured unless marked "by eye" or "estimate". Run from data/sanborn with python -B; scripts are in bench_2026-11-25/diag/rail5/code/.

Truth: rail_ben.json for 5 is complete, with 0 railroad and 61 streetcar tracks (73,423 px). From the scorer.

**Is the re-run the same as what Ben saw?**
- run_ink_bins5.py (--which orig --ground nets) and then run_tracks5.py give 80 tracks: 23 railroad (4,691 px) and 57 streetcar (54,681 px).
- These are identical, track for track, to unet_data/5_rail_rule.json (checked with an inline comparison).
- One ink_bins run takes 27 s.

**Scores of today's rules** (score_rail_bench.py, then summary5.py; railroad recall n/a, Ben has no railroad)

| run (ground) | railroad: false tracks / px | railroad bin | streetcar recall / precision, 10 px | 30 px | found / partial / missed (10 px) |
|---|---|---|---|---|---|
| as Ben saw (nets) | 23 / 4,691 (precision 0%) | 29,381 px | 76.2% / 100.0% | 79.1% / 100.0% | 30 / 19 / 12 |
| nets with Ben's line edits | 23 / 4,691 | 29,381 px | 77.8% / 100% | 80.5% / 100% | 31 / 18 / 12 |
| no ground | 54 / 14,327 | 81,635 px | 78.8% / 100% | 81.4% / 100% | 31 / 18 / 12 |

- As Ben saw: 0 false streetcar tracks and 0 px of false streetcar length. Streetcar tracks broken into pieces: 12 at 10 px, 13 at 30 px.

**Scores with the proposed fixes** (rail_rules.diff on copies; same scripts)

| run (ground) | railroad: false tracks / px | streetcar recall / precision, 10 px | 30 px | found / partial / missed | false streetcar px |
|---|---|---|---|---|---|
| nets | 5 / 2,253 | 80.8% / 98.7% | 83.2% / 98.9% | 34 / 19 / 8 (10 px), 37 / 16 / 8 (30 px) | 741 (10 px), 621 (30 px) |
| nets with Ben's line edits | 5 / 2,253 | 81.7% / 98.8% | 84.0% / 99.0% | | |
| no ground | 21 / 8,769 | 82.6% / 98.8% | 84.9% / 99.0% | | |

- With the fixes there are still 0 false streetcar tracks; broken tracks are 9 at 10 px.
- KEY mask on 5: the bins are identical with and without it (0 px different, inline check after the runs). There is no KEY on 5.

**Where the false railroad lies** (crops5.py; groups by place, reasons by eye from full-size crops)

| what fooled the rule | places | tracks | px |
|---|---|---|---|
| house numbers along street sides | 4 | 14 | 1,539 |
| lot lines with hook marks | 3 | 6 | 2,636 |
| lot numbers across lot lines | 2 | 3 | 514 |

- Kept by the proposed fix: groups 7 and 8 (the hook-mark lot lines in blocks 49 and 50), 5 tracks, 2,253 px.
- Share of length within 8 px of Ben's street lines (rail_on_lines5.py): house-number groups 0.40-0.49; hook-mark and lot-number groups 0.01-0.13.
- Railroad ink within 6 px of Ben's street lines (rail_on_lines5.py): 4,532 of 29,381 px (15%) on the nets ground; 20,866 of 81,635 px (26%) with no ground.
- The outline step's 'on rail' side (rail_on_lines5.py plus an inline check): 1 side, (5265,4014)-(5367,4011), 100% on Ben's lines. It is missing from 5_edges.json, and Ben added a 543 px line over it.
- No-ground tracks the proposed fix keeps that the nets run does not have (montage_none5.py; classes by eye): 15 tracks, 5,743 px. Of these, 10 are house-number rows (3,166 px) and 5 are hook-mark lines (2,572 px).

**Tick spacing, real track against the false rows** (tick_gaps.py, ink_bins.railroad from the copy)
- Gap between ticks, 10th-90th percentile: false rows on 5 38-86 px (median 72.1); true rows on 44 71.6-75.4 px; true rows on 90 51-121 px.
- Relative spread of the gaps (IQR over median): false on 5, median 0.32; true on 44, 0.04; true on 90, 0.15, with a 90th percentile of 0.59.
- So neither spacing nor evenness separates them.

**Streetcar misses**
- The largest (scores JSON plus inline checks; causes by eye):
  - Vine St, track 41: 3,552 px missed; the streetcar ink bin covers only 27.7% of it.
  - Elm St, track 15: 2,505 px missed; bin covers 37.3%. In both places the line is printed thinner and almost solid.
  - Curves: the Plum and Ninth junction (7 tracks, about 850 px) and the S-curve on John St (track 29, 750 px).
- The proposed fix's false streetcar (inline check, crop_car.py; by eye) is 3 stretches of 314, 234 and 190 px, all under the street names STREET, VINE and ELM.

**What Ben did with the 80 rule tracks** (reconstruct_deletes5.py; estimate from shapes, not a record)
- Railroad: 23 deleted (4,689 px).
- Streetcar: 1 kept as it was; 56 changed or redrawn (53,703 px); 0 deleted as false.
- Only 16 of his 295 points coincide with a rule point.

### causes

- **R1** The tick rule reads house numbers along street-side block lines as railroad ticks: digits written against the block line cross it on both sides.
  - evidence: Full-size crops rr_group03-06 (George St 525-519; 310-08-306 and 304; 562 and 560; 542-40-538), looked at by eye. Their tracks lie 40-49% within 8 px of Ben's street lines (rail_on_lines5.py). With no ground, 10 of the 15 tracks the fix keeps are house-number rows (montage_none5.py).
  - size: 14 of the 23 tracks Ben deleted (1,539 px, 33% of the false length), measured. With no ground: 3,166 px still left after the proposed fix.
  - confidence: high
  - round 2: The proposed drop_alone fix removes all 14 on the networks' block ground. It does not help without a ground, where whole block faces of numbers join into rows longer than 600 px. A rule fix needs a test on the shape of the ink, not the spacing: spacing does not separate them (tick_gaps.py). A rough idea, not measured: a tick is a short straight bar crossing the line evenly; a digit is curved and mostly on one side. The surer route is a learned rail classifier with Ben's rejected tracks as hard negatives. Never use them as negatives for street lines, because these rows sit on real street sides.
- **R2** Lot lines carrying Sanborn hook marks pass as railroad. Long ones survive the proposed 'short and alone' drop.
  - evidence: Crops rr_group02, 07 and 08: the In Lot 392/391 and 390/389 lines in blocks 49 and 50, plus lots 162-166 over 189-193. The big block number '50' is in the railroad ink. Tick gaps of the false rows (median 72 px) overlap the true rows on 44 (60-77 px), and evenness overlaps plate 90 (tick_gaps.py).
  - size: 6 tracks and 2,636 px of the 23 (measured). The 5 tracks (2,253 px) the proposed fix keeps are all of this kind. With no ground, 5 more lines (2,572 px) survive.
  - confidence: high
  - round 2: This is the main thing left after rail_rules.diff. The fix should be a shape test on the tick (a hook is S-shaped, a railroad tick is a straight bar), or the rejected list as learned negatives. Lengthening the 600 px cut would start costing real spurs. Plate 5 has now been studied, so test any rule change on another complete plate.
- **R3** Lot numbers written across a lot line pass as railroad ticks.
  - evidence: Crops rr_group00 (lots 237-233) and rr_group01 (73 S 74 S 75).
  - size: 3 tracks, 514 px (measured). The proposed fix removes all of them.
  - confidence: high
  - round 2: Covered by rail_rules.diff (drop_alone) on this plate.
- **R4** False railroad ink on street sides makes the outline step drop real block sides (RAIL_DROP), which become street lines that are never shown.
  - evidence: The side (5265,4014)-(5367,4011) is 'on rail' in outlines.json and is missing from 5_edges.json. It lies 100% on Ben's lines, and he added a 543 px line over it (rail_on_lines5.py plus an inline check). 15% of the railroad ink (nets ground) and 26% (no ground) lies within 6 px of Ben's street lines.
  - size: On 5 today: 1 side, about 102 px (measured). The outlines.py docstring says 5 sides with the batch's no-ground bins (not re-measured here). Effect on V2 through plate 5's labels: about zero, my estimate from reading make_labels_v2.py (an 'on rail' side is neither positive nor negative).
  - confidence: high (mechanism); medium (effect on V2)
  - round 2: Have outlines.py ignore railroad ink lying under Ben's rejected tracks. Use the proposed rule (fewer house-number tracks) before RAIL_DROP. Count dropped 'on rail' sides that fall on Ben's lines, per plate, as a check.
- **R5** Ben's deletions of rule tracks are not kept anywhere, so the negatives he makes for the rail rules are thrown away.
  - evidence: edit_page.html del() (line 363) removes the track from the list and nothing else; /saverail (edit_server.py 158-171) writes only 'tracks'. On 5, the 23 railroad deletions can be recovered only because unet_data/5_rail_rule.json has not been re-made since (the re-run gives it back exactly). Only 1 of 57 rule streetcar tracks was kept as it was; 56 were changed or redrawn (reconstruct_deletes5.py, estimate).
  - size: 23 tracks and 4,689 px of certain negatives on 5. Every plate checked in the editor loses its deletions the next time rail_tracks.py runs.
  - confidence: high
  - round 2: Design (nothing changed):
- Add a 'rejected' list to rail_ben.json: {kind, pts, src:'rule', at, rule:{made, bins_made}}. Record it in del() for unchecked rule tracks, and include it in snap('rail')/undo, saveRail and the load at line 97.
- Rule tracks Ben keeps but edits get 'from_rule' with their original points.
- The server checks the entries and keeps the list already in the file when a save arrives without one.
- Readers decide the meaning: 'not rail' unless 80% or more lies within 10 px of a final track ('redrawn' or 'wrong kind').
- Uses: ink_bins.py and the outline step ignore rail ink under rejected tracks; the scorer counts them as certain false positives; any rail learner gets them as hard negatives; the street-line net never gets them as negatives.
- Backfill 5 from design/rejected_5_backfill_example.json only if Ben agrees. For 90 and 1A, first check that their rule file is still the one he was shown.
- **R6** Streetcar misses: where the line is printed thinner and almost solid (Vine, Elm), and on curves (the Plum/Ninth junction, the John St S-curve).
  - evidence: Crops car_vine_t41, car_elm_t15(_b), car_missed_cluster and car_missed_t29. The streetcar ink bin covers only 27.7% and 37.3% of tracks 41 and 15.
  - size: 12 of Ben's 61 tracks missed (8 with the proposed fix). Tracks 41 and 15 alone account for 6,057 px, 35% of the 17,474 px missed at 10 px (measured).
  - confidence: medium (causes by eye)
  - round 2: Loosen the bar test (thickness and length) for nearly solid heavy lines, and follow curves when joining dashes. The longer join (car_reach 350) already recovers 4 tracks. Its 741 px 'false' length is under street names: Ben's tracks stop at the lettering and the rule's carry on. Agree with Ben which way to draw it before scoring the next change.

### files

All are under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/rail5/ (about 63 MB). A second copy of the scripts and key JSON is in _second_copy/.

**code/**
- orig/ink_bins.py and orig/rail_tracks.py: byte copies of the repo's files (sha256 3b461d06… and 16a4c4ed…).
- proposed/ink_bins.py and proposed/rail_tracks.py: rail_rules.diff applied. rail_tracks.py is identical to bench_2026-11-21/rail-rules/proposed.
- rail_rules_local.diff, ink_bins_hunk1.rej, ported_ink_bins.diff and ported_rail_tracks.diff: how the diff was applied (one hunk moved by hand).
- run_ink_bins5.py: writes are guarded; --which orig|proposed and --ground nets|nets_ben|none.
- run_tracks5.py and score_rail_bench.py: the second is a copy of the 21 Nov scorer.
- summary5.py, crops5.py, crop_car.py, montage_none5.py, rail_on_lines5.py, tick_gaps.py and reconstruct_deletes5.py.

**inputs/**
- Copies of 5_edges.json, 5_outlines.json, outlines.json, 5_rail_rule.json, 5_bins.json, rail_ben_5_copy.json and rail_ben_1A_copy.json, with sha256.txt.

**runs/**
- {orig,proposed}_{nets,nets_ben,none}: _bins.png, _bins.json, _bins.log and _tracks.json for each.

**scores/**
- {run}.json and .jpg (quarter size) for each run, score_all.log, summary.json.
- rail_on_lines5.json, tick_gaps.json, reconstructed_verdicts5.json.

**crops/**
- overview_5.jpg: the 9 false-railroad places, numbered.
- rr_group00…08_*.png: full-size crops of each place, plain above or beside the overlay. In the overlay, red is the railroad ink, blue the rule track, green what the proposed fix keeps and yellow Ben's streetcar.
- groups.json.
- proposed_none_extra_0/1.png and orig_none_extra_0-2.png: montages of the no-ground tracks.
- car_*.png: streetcar misses and the stretches under street names.

**design/**
- rejected_5_backfill_example.json: the 23 deleted railroad tracks in the proposed 'rejected' format, each with what was seen by eye. An example only; no tool reads it.

## skeptic

The new area networks (the ones that call each piece of ground block or street) caused all of the loss, and most of it only shows on plate 44. The line networks did not cause it, and neither did the checkpoint choice or the threshold. All numbers are measured unless marked otherwise.

1) Area net, not line net. Each new area net paired with the old line net reproduces its pair's loss to within 0.005 PQ. Each new line net paired with the old area net scores -0.001 to +0.005 on 44 and +0.000 on plate 5 (collect_runs.py, plate5_table.py).

2) Where the loss sits. The four pairs lose 0.283 PQ in total on 44.
- 0.126 of it (45%) is the open land by Mill Creek, the canal and the railway, which Ben left undecided. The new area maps cut it along the creek, the railway and Spring Grove, and PQ counts each piece as a false block.
- 0.157 (55%) is on ground Ben decided, and V1S1 alone accounts for 0.099 of that.

3) Most of it is specific to plate 44. Plate 5 was never trained on by area_ng1 or V1. I ran the nets there on the CPU and scored one tile grid against Ben's checked plate-5 lines:
- the V1 pairs score -0.010 (seed 1) and +0.043 (seed 2);
- the V1S2 area map beats area_ng1's (street IoU 0.873 against 0.853);
- V1S1 is slightly worse (0.833).

On 44 the outline step lifts area_ng1's map by +0.077 on decided ground but the new maps by only +0.008 to +0.050. On plate 5 it lifts the V1 maps more (+0.069 and +0.079) than area_ng1's (+0.043).

4) V1S1 is a genuinely weaker draw. It is the worst on both plates.

So the most likely reading:
- one weak seed (V1S1);
- new area nets that treat creek, rail and canal land as not-block, which PQ on 44 punishes;
- a plate-44 benchmark on which the existing chain happens to suit area_ng1 best.

It is not evidence that the new training recipe makes area networks worse in general. Caveats: plate 5 is one grid, and Ben's plate-5 lines started from the batch's lines, which favours area_ng1 there.

- Not re-checked: the rail5 and ben-labels agents' causes (they were not in my brief), the recipe report after its item 3 (it was cut off), and swap A6 (the 1-2 px map shift, which it said is not a cause).
- Plate-5 caveats:
  - The end-to-end runs use one tile grid; on 44 the grid-to-grid spread is about 0.01-0.04 PQ.
  - Ben's plate-5 truth began as the batch's lines, which favours the baseline.
  - V2 trained on plate 5's pseudo labels, so V2 is in sample there.
  - A neutral check needs a second fully checked plate scored on all 6 grids, either plate 90 or plate 5 kept out of the pseudo set.
- Seed against recipe cannot be separated without training. V1S1 is weak on both plates, and each variant has only two seeds.
- The training-side reason the new nets cut up the open land (fewer crops from the old-style label plates) is an estimate, not a test.
- I ran the area and line networks on the CPU (torch device cpu, no GPU, no training) to make the plate-5 maps. The check run reproduced the batch's stored plate-5 maps: decisions identical on every pixel.
- Nothing was written outside diag/verify. I checked this with find -newermt, and git status of tools/ is clean.

All files are under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-25/diag/verify/:
- scripts/: collect_runs.py, calib.py, run_bench.py, outlines_var.py, prep_var.py, var_table.py, pipe_check.py, numbers_check.py, label_prior.py, area5_cpu.py, score_area5.py, lines5_cpu.py, run_plate5.py, plate5_table.py
- results: runs_table.json, calib.json, var_table.json, pipe_check.json, numbers_check.json, label_prior.json, area5_scores.json, plate5_table.json
- run folders: mix/ (36 bench runs on 44), plate5/ (maps, runs, streetmap_5.json), area5/
- a second copy is in _second_copy/

- **swap-A1: the area net causes the loss; the new line nets are as good as lines_ng1 or slightly better** confirmed: Measured: I re-read all 30 plate-44 bench44.json files and the 8 a__ and 8 b__ swap runs with my own collector (verify/scripts/collect_runs.py, output in runs_table.json). Each new area net paired with lines_ng1 reproduces its pair's gain to within 0.005 (-0.147/-0.142, -0.041/-0.040, -0.075/-0.072, -0.025/-0.028). area_ng1 paired with each new line net scores -0.001 to +0.005. I also checked this on a second plate, plate 5, which neither area_ng1 nor V1 ever trained on. I ran the nets on the CPU (lines5_cpu.py, run_plate5.py, plate5_table.py). area_ng1 with the V1S1 or V1S2 line net gives PQ 0.405, exactly the batch pair's 0.405, with recall +0.032 and +0.016. The CPU path reproduces the batch's own plate-5 maps: the block/street and line/no-line decisions are identical on every pixel. Corrected: True on 44 and on plate 5. 'The area net' here includes how the rest of the chain reacts to its map. Two errors other agents blamed on the line nets also follow the area net: see C3 and C4.
- **swap-A2: of the two routes, the outline step reading the area map does more harm than the area map fed to the line net (its 7th input)** partly: Measured with the swap agent's mix runs (collect_runs.py). The two routes do not add up, and how much they interact is as large as the loss itself. For V1S2: outline-step route alone -0.059, plus 7th-input route alone -0.038, makes -0.097, but the real loss is -0.041. For V1S1 the same sum is -0.099 against a real -0.147. So which route is 'bigger' depends on the pair. A clearer view comes from bench44's own stage scores. On the ground Ben decided, the new area maps on their own (stage 0) score -0.059, +0.001, +0.020 and +0.080 PQ against area_ng1's map. After the outline step the same four score -0.099, -0.027, -0.040 and +0.009. On plate 44 the outline step lifts area_ng1's map by +0.077, but the new maps by only +0.008 to +0.050. On plate 5 it is the other way round: +0.043 for area_ng1's map, +0.069 and +0.079 for the V1 maps (plate5_table.py). Corrected: Most of the decided-ground loss on 44 appears at the outline step, not in the area maps themselves. And this happens on 44 only: on plate 5 the outline step helps the V1 maps more than area_ng1's.
- **swap-A3 / errors-C2: the extra false blocks are open land by Mill Creek, the canal and the railway, cut into more pieces (one cause, reported twice; do not add the two)** confirmed: Measured (collect_runs.py). PQ gain minus PQ_decided gain is 0.043, 0.013, 0.032 and 0.037 for the four pairs: 0.126 of the summed 0.283 loss, that is 45%. In the pictures fp_base_grid0.jpg and fp_V2S2_grid0.jpg, the baseline makes 3 large false blocks on that land, and V2S2 makes 11 pieces cut along Mill Creek, Spring Grove Ave and the railway. Those cuts follow real features that are not blocks, so in practice the cost is extra lines Ben would delete. PQ counts every piece as a false block. Plate 5 has little such land (9.5% of its paper is undecided, against 46% on 44), which helps explain why the V1 pairs do not lose there. Why the area nets cut it is an estimate (label_prior.py, calib.py): the share of training crops from the four old-style plates, which teach open land as block, fell from 100% (ng1) to 80% (V1) and 40% (V2). The share of 44's paper called block falls in step: 0.75, then 0.735-0.74, then 0.69-0.71. Corrected: 45% of the summed loss. It is mostly how PQ scores ground Ben left undecided, not a new kind of error on ground he decided.
- **swap-A4: three of the four new area nets are also worse on decided ground; area_ng1 may have been a lucky seed** partly: On 44 this is measured: decided-ground PQ loss is 0.099 (V1S1), 0.040 (V2S1) and 0.027 (V1S2), while V2S2 gains 0.009. That is 0.157 in all, of which V1S1 is 63%. On plate 5, which area_ng1 and V1 never saw, the ranking changes (score_area5.py, against Ben's plate-5 labels): street IoU is 0.853 for area_ng1, 0.873 for V1S2 (0.879 for its last checkpoint) and 0.833 for V1S1. End to end on plate 5 (one tile grid), the V1S2 pair scores +0.043 PQ and the V1S1 pair -0.010. V1S1 is the weakest net on both plates. V1S2 is worse than area_ng1 on 44 but better on 5. Caveat: Ben's plate-5 lines began as the batch's lines, which favours area_ng1 there. Corrected: Only V1S1 is clearly a weaker area net on both plates. For V1S2 and V2S1 the decided-ground loss is specific to plate 44.
- **swap-A5 / recipe-3: the checkpoint choice is not the cause, but the 1A region cannot judge an area net** confirmed: Measured (collect_runs.py): the mean paired gain is -0.071 for the best checkpoints and -0.069 for the last. The 1A region favours the new nets, which trained on the left part of 1A. Plate 44 is not neutral either: it favours area_ng1. On 44, area_ng1 ranks 1st of 5; on plate 5 it ranks behind V1S2 and ahead of V1S1. Corrected: Neither 1A nor 44 is a neutral judge between area_ng1 and the new nets.
- **errors-C1: lost block lines in the dense north-west, at Bond St and along Spring Grove** partly: Where the lines are lost is correct, and the merges match the PQ split. But they are lost because of the area map, not the line net. With area_ng1's map as input, the new line nets lose nothing (the a__ runs on 44; aV1S1 and aV1S2 on plate 5). The picture lines_panel_V1S1_north.jpg shows lines_ng1 also dropping those lines when it is fed V1S1's area map. The proposed fix (extra weight on Ben's added lines for the line net) aims at the wrong network. Corrected: Lost lines and merges come from area maps that call narrow streets block. The line nets only follow what the area map says.
- **errors-C3: V1 places block sides on water pipes and sewers in the street; V2's pseudo plates taught the line net not to** refuted: Measured (pipe_check.py, mean of 6 grids). False length lying on pipe and sewer ink: baseline 6.6k px. Same area net with a different line net (area_ng1 + V1 line nets): 7.0k and 6.1k. V1 area nets + lines_ng1: 13.9k and 13.8k. V2 area nets + lines_ng1: 2.8k and 1.5k. The line net makes no difference, the area net does. Corrected: The pipe and sewer sides come from the V1 area maps, which call street ground block so the outline step slides the side onto the pipe line in the street. The V2 area nets bring them below the baseline. Teaching the line net 'pipe is not a line' would not have prevented this.
- **errors-C4: near-street numbers (Ben's point) attract false lines only in V2S1, depending on the seed** partly: The size is confirmed and small (numbers_check.py): 1.5k px of false length per grid for the baseline, 3.8k for V2S1, 1.9k-2.5k for the others. But it is mostly V2S1's area net. lines_ng1 fed V2S1's area map has mean P(line) 0.071 on near-street numbers, against 0.049 for the baseline. V2S1's own line net fed area_ng1's map has 0.054. False length on those numbers: 3.7k when only V2S1's area net is used (b__), 2.3k when only its line net is used (a__). Corrected: Numbers near streets are a small confounder on 44, and it reaches the line net mainly through the area map it is fed.
- **errors-C5: most of Ben's deleted length is a line he replaced or moved, not 'no street here'** confirmed: I re-ran deletions2.py (read-only): 58.4% on plate 5 and 63.7% on 1A, exactly as reported. My own split of the 58.4% on plate 5: 30.5% of the deleted length lies beside a network line Ben kept (a duplicate), and 27.9% beside a line Ben drew himself (deleted, then redrawn). The 1A map labels already turn an 11 px strip along each line marked wrong into negatives (make_labels_v2.py, WRONG_PX), and positives override that strip. Plate 5's 248 deletions were not used in this run, because plate 5 went in as a pseudo plate. Corrected: This is not a cause of the loss. Ben's 'learn from deletions' already applies to map plates. Deletions beside a kept line or a line Ben drew must not become 'not a line' targets.
- **recipe-1: 1A takes 20% of the area crops, and its label style (37% street, blank paper taught as street) is plausibly costly** partly: The street share is confirmed (label_prior.py): 0.379 on 1A, against 0.13-0.20 on the old plates. Estimated street share in the crops each net saw: 0.168 for ng1, 0.210 for all four new nets. But the blank-paper mechanism is not supported by the recipe agent's own numbers: of the open land that flipped from block to street on 44, 47-54% is blank paper, which is the base rate (50%). And V2, with half of V1's 1A share, calls more of the open land street than V1 does. Corrected: 1A shifts the street prior, but it does not explain the cut-up open land. The fall in crops from the old-style plates fits better (estimate).
- **recipe-2: the four labelled plates get fewer crops (74-88% in V1, 36-45% in V2)** partly: It fits the open-land shift (estimate, see A3). It does not explain decided-ground quality: V2S2, with the fewest old-plate crops, is the best of all five nets on 44's decided ground and on plate 5, while V1S1, with the most, is the worst on both. Corrected: Seed-to-seed spread outweighs this effect on decided ground.
- **verify-new: the area-map threshold (calibration), or outline-step constants tuned to area_ng1** refuted: Measured with the real outline step on 6 grids (calib.py, outlines_var.py, run_bench.py, var_table.py; 28 bench runs, all exit 0). Re-thresholding each new map so that it calls as much of the paper block as area_ng1 makes all four pairs worse by 0.007-0.011 PQ. Changing the outline constants: SEED_B 10 shrinks the four gaps by 0.020-0.026, but drops the baseline by 0.029. SEED_B 20, MK_SEED_MIN 1000 and MK_SEED_MIN 4000 move them by 0.015 or less (mostly 0.004 or less). Corrected: Neither the threshold nor a tuned constant explains it. The extra lift that area_ng1 gets from the outline step (A2) is specific to plate 44, not to any one setting.
