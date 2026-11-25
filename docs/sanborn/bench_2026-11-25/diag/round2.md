# Round 2 of the blank-guide U-nets: design

Written 25 Nov 2026. **Not to be run until Ben says so.** Nothing here has been trained or run on the GPU. Each number names the script that made it. "Measured" means the script computed it from real outputs. "Estimate" means arithmetic or judgement.

## 1. In short

Round 1 lost because of the **area net**, not the line net and not the checkpoint choice:
- each new area net paired with the old line net reproduces its pair's whole loss, within 0.005 PQ;
- each new line net paired with area_ng1 scores the same as the baseline (-0.001 to +0.005);
- all of this is measured (swap: run_swaps.py, summarize.py; verify: collect_runs.py).

So round 2 is mostly about the area net. It changes five things:

1. **Ben's checked plates replace the pseudo plates.** Plates 1A and 5 are trained with his deletions, his additions and the printed text all labelled. The 11 pseudo plates are dropped.
2. **Seed controls.** The old recipe is retrained with 3 seeds, so we learn whether area_ng1 was a lucky draw. Every variant gets 3-4 seeds.
3. **Choices stay off plate 44.** Checkpoints are not chosen at all: the last weights are kept. Seeds are chosen on held-out ground, best of all a whole plate no net has seen: plate 7, if Ben checks it next. 44 stays the test and 90 the final check.
4. **The two nets are scored apart.** An area net is judged by its own map, and a line net is judged with a fixed, good area map. Only then is a pair scored.
5. **The line net leans less on the area map.** Its 7th input is blanked half the time, and when it is present it looks like a real map, not an in-sample one.

The full plan is 15 networks and 22 evaluations, about **12.5 GPU hours over two nights**, with a stop for Ben in between. A short version is 8 networks, about **6.6 h** (design_numbers.py, from round 1's measured times).

## 2. What round 1 taught us (the numbers this design rests on)

- **Area net.** The new area nets call narrow streets and alleys block, so Ben's blocks merge.
  - Street IoU on 44: area_ng1 0.815; new nets 0.715-0.838 (measured, swap pixel_maps44.py).
  - Where Ben's lines were lost, the new area nets call both sides block 21-62% of the time; the baseline does so 8-11% of the time (measured, errors summarize.py).
- **Open land is cut into pieces.** The new area nets also cut the creek, canal and railway land Ben left undecided:
  - void false blocks: 7.3-15.3 per grid, against 4.2 for the baseline (measured, swap fp_anatomy.py);
  - this is 45% of the summed loss (measured, verify collect_runs.py).
- **Seed noise is large.** The two seeds of one recipe differ by up to 0.10 PQ on 44 (V1: 0.368 against 0.470). The pooled seed sd is about 0.055 PQ (estimate from 2 seeds per variant; design_numbers.py). area_ng1 is a single unseeded draw, so it may have been a lucky one.
- **The 1A region misjudges.** It rated all four new area nets above area_ng1 (street IoU 0.875-0.920 against 0.840). On 44, three of the four are worse. The new nets had trained on the rest of 1A (measured, swap).
- **Checkpoint choice did not matter.** Mean paired gain: best -0.071, last -0.069 (measured, swap summarize.py).
- **1A was oversampled.** It got 20% of the area crops in V1: 486 crop views per taught pixel, against 57-92 for the old four plates (measured, recipe crop_shares.py).
- **The pseudo labels teach the wrong thing where Ben cares.**
  - On plate 5 they taught 56% of the length of the lines Ben later deleted as false as *positive* (51 of 83 lines), where the map recipe teaches 92% of it negative (measured, ben-labels deleted_split.py).
  - They leave 47-74% of the text within 40 px of a line unscored, against 19-22% on the labelled plates and 1A (measured, ben-labels text_all_plates.py).
- **Every line net leans hard on its area input.** Fed one of the three weaker new area maps (V1S1, V1S2, V2S1) instead of area_ng1's, a line net's F1 falls by 0.10-0.17, from 0.62-0.64 to 0.46-0.51. lines_ng1 falls just as far (measured, swap pixel_maps44.json; table in design_numbers.py).

## 3. Plates and their roles

| Plate | Role in round 2 | Why |
|---|---|---|
| 43, 45, 80, 82A | train (labels as today, byte for byte) | the old labelled plates; area_ng1's data |
| 1A | train (Ben's checked lines: 217, 71 added, 68 deleted) | his labels; small (3.15 M taught half px) |
| 5 | train (Ben's checked lines: 965, 347 added, 248 deleted; rail_ben.json complete) | his labels; 125 blocks, dense downtown with alleys |
| 7 | **selection plate, whole, never trained** (Plan A, once Ben has checked it) | chooses seeds and judges recipes on ground no compared net has seen |
| 44 | test only | Ben's ground truth and the benchmark; never trains, never chooses |
| 90 | final untouched check, once checked | 44 will have been used to decide twice |
| the 11 pseudo plates | dropped | see section 8 |

**Plan A (preferred): Ben checks plate 7 first.**
- 1A and 5 are then trained whole, with no validation region.
- Seeds are chosen on plate 7, and the recipe is judged on 7.
- 44 is then only a report, and 90 confirms.

**Plan B (if 7 is not ready):**
- 1A keeps its region right of Elm St.
- 5 holds out its right quarter: 25.4% of its paper, 42 of its 125 blocks, 0.39 M of its 1.46 M line px and 73 of its 214 non-sheet deletions (measured, design_numbers.py).
- Seeds are chosen on these two regions together. That is fair between seeds of one recipe: in round 1 the 1A region ranked the two seeds of each variant the same way 44 did (2 of 2; measured, train_v2_runs/summary.md).
- It is not fair between recipes, so in Plan B the recipe is judged on 44 under the rule in section 5, written before the run.

**Crop shares.** Crops are drawn in proportion to the square root of each plate's taught pixels, not equally per plate. This gives (estimate, design_numbers.py):
- 43: 21%, 45: 18%, 80: 17%, 82A: 19%;
- 1A: 7%, against 20% in V1;
- 5: 17%;
- the old four together: 76%.

## 4. The arms and the seed controls

All runs use 4,000 iterations, seeds 1, 2, 3 (and 4 for A2), and the last weights. The same seed gave bit-identical weights on this GPU over 30 iterations (measured, round 1 repeat_compare.json), so the seed should be the only randomness.

| Arm | Net | Plates | Recipe | Seeds | Question it answers |
|---|---|---|---|---|---|
| A0 | area | 43, 45, 80, 82A | **exactly area_ng1's** (train_noguide's legacy path, 255 squares, last weights), but seeded and without 44:val | 3 | Was area_ng1 a lucky draw? |
| A1 | area | 43, 45, 80, 82A | round-1 fixes (no 255 squares, square-root crop shares) | 3 | Do the fixes alone help or hurt? (first arm to cut) |
| A2 | area | old four + 1A + 5 | round 2: Ben's labels with the weights of section 6 | 4 | Do Ben's plates make a better area net? |
| L1 | line | old four + 1A + 5 | round-1 line recipe (today's map labels, 15% blank 7th input) | 2 | Control for L2's label changes |
| L2 | line | old four + 1A + 5 | round 2: section 6 labels, 7th input as section 7 | 3 | Do deletions, number negatives and a looser 7th input help? |

In all: 10 area nets and 5 line nets.

**What the seeds can and cannot tell (estimate, design_numbers.py).**
- With a seed sd of 0.055 PQ, the mean of 4 seeds has a standard error of 0.028.
- The A2-minus-A0 difference (4 seeds against 3) has a standard error of 0.042. So only a difference of about 0.08 PQ is clear on 44 alone.
- Six seeds in both arms would bring that to 0.032, at about 4 more hours (5 more area nets).
- Instead, the rule below asks for a seed-mean gain *and* a win by the chosen seed on most grids, and it reads pixel scores (street IoU), which are steadier than PQ.

**Optional: seed ensembles.** Averaging the area maps of 3 seeds should cut the seed noise in what ships. This can be tested before round 2 on plate 5 with no training, on the CPU, because the maps already exist (diag/verify/area5). area_ng1, V1S1 and V1S2 never saw plate 5. If their averaged map beats the best single map on 5's PQ_decided, the "chosen seed" below becomes "the 3-seed ensemble". That must be decided before the run.

## 5. Choosing checkpoints, seeds and the winner without touching 44

**Checkpoints.** None are chosen; the last weights are kept.
- Round 1 showed that choosing gained nothing: best and last differ by about ±0.04 PQ, within the noise, with equal means (measured, swap).
- The trainers still save every 250 iterations. An average of the last four (3,250-4,000) is an option, to be judged on the selection ground only.

**Seeds** (within one arm) are chosen on the selection ground: plate 7 in Plan A, the 1A and 5 regions in Plan B.
- Area nets: highest street IoU on decided ground. Ties go to the higher recall of narrow streets (streets under 40 ft called street).
- Line nets: highest F1 at 3 px, with area_ng1's map as the 7th input. That map is out of sample on 1A, 5 and 7.

**The rule, written into the driver before the run:**
1. **Luck check.** A0's three seeds are paired with lines_ng1 and scored on 44 (6 grids). The table shows where area_ng1 falls among them.
2. **A2 replaces area_ng1** only if all three hold, with lines_ng1 as the line net:
   - (a) A2's seed-mean PQ_decided gain over area_ng1 is above 0 and larger than A0's seed sd;
   - (b) A2's chosen seed gains PQ_decided on at least 4 of 6 grids, and loses no more than 0.01 PQ on all ground (the open land);
   - (c) its editor-line precision on decided ground is no more than 0.01 below area_ng1's.
3. **L2 replaces lines_ng1** only if, with area_ng1's stored maps (so the line net is judged alone), all of these hold:
   - its seed-mean PQ gain is at least 0;
   - its line precision rises by at least 0.02;
   - its printed-line recall falls by no more than 0.01;
   - its false length on near-street numbers and on pipes and sewers both fall.
4. **The final pair** is scored once on 44. Plate 90 must show a gain before the batch is rerun with it.

Plan A applies the same rule on plate 7, and 44 is then reported. Plan B applies it on 44, which then becomes a little optimistic for whatever ships.

**Every evaluation reports** (eval changes, section 10):
- PQ and PQ_decided;
- void false blocks;
- merges;
- editor-line precision, on decided and on undecided ground;
- false length on near-street numbers, and the line net's P(line) there;
- false length on pipes and sewers;
- on 1A, 5 and 7: how much of Ben's deleted-false lines the line map still draws.

## 6. Labels

Plates 1A and 5 are built by make_labels_v2.py's map mode with the changes below. They are built from frozen copies of Ben's files (sha256 recorded), never from his live files.

### 6a. Deleted lines as weighted hard negatives (Ben's first point)

**Most deletions are not "no line here".** On plate 5:
- 116 of the 214 non-sheet deletions (23.9 k px) are duplicates of a line Ben kept;
- 15 (1.9 k px) are partial;
- only 83 (13.9 k px) are false: no line there.

On 1A: 38 duplicates (11.0 k px), 6 partial, 21 false (4.8 k px). (Measured, ben-labels deleted_split.py.)

Duplicates must not become negatives, or they would fight the lines he kept.

**The rule.** A deleted line counts as false when under 60% of its points lie within 6 px of a final line. A moved line's old place counts too, when it is more than 8 px from the new one.
- Line net: an 11 px strip along it is "not a line" everywhere on the paper, except within 8 px of any final line. Weight 16 on ink and 4 off ink, against 4 and 1 for ordinary negatives.
- Area net: Ben's final map already gives both sides of a false line the same class. Round 2 doubles the area weight within about 10 half px of every deleted false line, so the net is pushed hardest where it once made a false side.

**"Just as important" both ways.** The lines Ben added (the misses) get the same factor:
- line weight 12 instead of 3 on his added inked lines;
- double area weight near them.

This makes found-wrongly and missed count equally per pixel, as Ben asked. The factor 4 for the line net is the ben-labels estimate's W_DEL; it is a starting value, not a measured optimum.

**Hard-crop sampling.** About 30% of line crops and 30% of area crops are centred on a hard pixel instead of drawn at random. A hard pixel is a deleted line, an added line, near-street text, a pipe or sewer in a street, or a narrow street (estimate of a sensible share). Without this, 14 k px of deletions on a 72 MP plate would almost never be in a crop.

**Expected effect (estimate, ben-labels estimate.py).** On 1A, the share of today's false response that sits under a negative weight rises from 0.74 to 0.84. The share under a heavy weight (6 or more) rises from 0 to 0.35.

### 6b. Numbers near streets, actively resisted (Ben's second point)

**What was measured:**
- On 44, numbers are a small factor: 6.5% of the baseline's false length lies on numbers within 40 px of a street. One seed (V2S1) doubles this to 12.7% (errors xtab.py).
- That rise came mostly through the area map. lines_ng1 fed V2S1's area map has P(line) 0.071 on those numbers, against 0.049 (verify numbers_check.py).
- On plate 5, 14 of Ben's deletions lie mostly on text, 26-224 px long (errors deletions2.py).
- **The false railroad on plate 5 is a different thing.** All 23 railroad tracks the rule found there are false (4,691 px). They sit on house numbers, frontage figures and lot lines with hook marks (rail5 summary5.py, reconstruct_deletes5.py).
  - They come from the rail *rule* (ink_bins, rail_tracks), not from either network.
  - Some lie on real block lines lettered with numbers: in 4 of the 9 groups, 40-49% of the false track length is within 8 px of Ben's lines (rail5 rail_on_lines5.py). The outline step then drops those real sides as "on rail" (outlines.py's own notes count 5 such real sides on plate 5).
  - rail5's proposed rule changes cut them from 23 tracks to 5 (measured, score_rail_bench.py). That is a rule fix outside round 2.

**What round 2 does:**
- **Line net.** Every text pixel (ink_bins bin 8, grown 1 px) on the paper is "not a line", except within 2 px of a positive. That includes the margin beside lines and the ground that is untaught today.
  - Weight 10 within 40 px of a positive and 6 beyond, against 4 today.
  - On 1A, text's share of the negative weight rises from 0.22 to 0.47 (estimate, ben-labels estimate.py).
- **Area net.** Block pixels in the 5-40 px band beside a street side that carry text get double weight. This stops the block edge sliding onto the numbers.
- **Audit before training (no GPU).** Under 1% of Ben's line pixels may lie within 3 px of a text negative. On 44, 1.5% of all text lies within 2 px of his lines (measured, ben-labels text_near_lines.py), so the 2 px protection matters.
- **Every evaluation reports** the numbers metric (section 5), so Ben can see it move.

### 6c. Street sides along the sheet edge with no ink (Ben's third point)

**Today's labels:**
- Lines of the kind "sheet_edge" are already left unscored: 80 lines on 5, 12 on 1A.
- But on plate 5, 45 of the 55 *drawn* lines along the edge have no ink under them (2,397 px), and the map recipe teaches them as positives. That is 0.6% of 5's positive line px (measured, ben-labels sheet_edge_lines.py, edge_pseudo5.py).
- On 44 (test only), 32 of 37 sheet-edge lines and 18 drawn or printed lines along the edge have no ink.

**Round 2:**
- Any of Ben's lines with ink support under 0.3 (share of points with ink within 2 px) is unscored in the line target, with its margin, whatever its kind.
- In the area label, 20 ft either side of such a line is unscored, and it is left out of the area net's edge target. The net is never asked to see a boundary that is not printed.
- The sheet-edge rule in the outline step stays responsible for these sides, and bench44 keeps scoring sheet-edge recall separately.

### 6d. Other area-label weights

Each of these is a code in a new weight image, so the factors can change without rebuilding the labels:
- **Narrow streets and alleys** (street pixels in streets under 40 ft wide): double weight. These are where the decided-ground loss sits.
- **Pipes and sewers in streets** (street pixels within 6 half px of bin 6 or 7 ink): double weight. The V1 area maps put 13.9 k px of false sides on pipes, against 6.6 k for the baseline (measured, verify pipe_check.py).

**Not changed: open land, the creek, the canal and the railway corridors.**
- Ben has not set the convention (question 1, section 11), so they stay unscored on his plates and as they are on the old four.
- Round 2 therefore does **not** fix the cut-up open land (A3). It only measures it separately (void false blocks, PQ against PQ_decided) and tolerates at most 0.01 PQ loss from it.

## 7. The line net's 7th input (the area map)

**Keep it for now, but stop it carrying area-net errors into the lines:**
- **Blank half the time.** The 7th input is blank (128) in 50% of crops on every plate, against 15%.
  - The V2 line nets were blanked in about 57% of their crops (round 1's estimate). Fed their own area maps, they lost 0.134 and 0.013 F1; lines_ng1 lost 0.151 and 0.012 with the same maps.
  - The V1 line nets (15% blank) lost 0.168 and 0.113, against 0.149 and 0.098 (measured, design_numbers.py).
  - So more blanking helped a little. That is only an estimate: 2 seeds, and confounded with the pseudo plates.
- **A realistic map when present.**
  - On 1A and 5: area_ng1's map, or V1S1's or V1S2's map of 5, picked at random per crop. All are out of sample.
  - On the old four plates every map is in sample, so it is cleaner than what the net gets in use. As a rough comparison on different ground, its accuracy is 0.945-0.974 against the labels there (recipe ch7_vs_ng1_training.py) but 0.936 on 44's decided ground (swap pixel_maps44.py). So it is degraded: blur, contrast pulled toward 0.5, shifted 0-4 half px (every map sits 1-2 by 2-4 half px off on 44; swap shift_test.py), and random erased patches.
- **Validation with a realistic map.** The line net is validated with area_ng1's map of 1A, 5 or 7, which is out of sample. It is also validated with a blank 7th input, and both are recorded.
- **A decision to drop the input.** In the evaluation, L2 is also scored with the 7th input blank. If blank is within 0.02 F1 and 0.005 PQ of the area-map case, the next round drops the 7th input altogether: 6 channels and no coupling.

Phase 0 has a 10-minute GPU inference test of the same question on the existing nets. It is optional, because those nets were trained with little blanking.

## 8. What round 1 did that round 2 drops

1. **The 11 pseudo plates.**
   - They cannot carry "not selected": only 25-63% of their paper is scored, against 82-96% on the labelled plates and 1A (measured, ben-labels text_all_plates.py).
   - They taught Ben's later-deleted false lines on 5 as positive.
   - They repeat the alley merges (11 of Ben's 55 blocks on 44 joined in its pseudo labels).
   - V2 against V1 was within seed noise (+0.041 PQ against a 0.10 spread).
   - Plate 5 leaves them to become a checked plate.
2. **`--area-blank pseudo`.** Replaced by the 50% blank rate on all plates.
3. **Equal crops per plate.** Replaced by square-root shares (1A falls from 20% to 7%).
4. **Keep-best on the 1A region, and the 1A region as a judge of recipes.**
5. **Validating the line net with area_in.png,** the in-sample area_ng1 map.
6. **The 2-seed shipping rule with area_ng1 as the only control.**

**Kept:**
- seeds;
- the 255-square fix (A0 against A1 tests it);
- atomic writes, manifest checks, and the guards that refuse 44 and 90 (and now 7);
- eval_v2's paired 6-grid scoring;
- the map recipe's WRONG_PX strip, now restricted as in 6a.

## 9. Order and GPU hours

Times are from round 1's own models: area net 45.1 min, line net 46.4 min, each 4,000 iterations. eval_v2 takes about 3 min per pair (2.4-3.2 measured). Training the two nets at once on the GPU was never tested, so everything runs one after the other.

| Phase | What | GPU |
|---|---|---|
| 0. Prepare (no training) | freeze Ben's 1A and 5 files; build train_v3 with the new label rules; run the label audits (6a-6c) and give Ben overlay pictures of plate 5's labels; the CPU ensemble test on plate 5; optionally, the 7th-input inference test | under 0.3 h of inference |
| **Stop: Ben looks at the label pictures and answers section 11** | | |
| 1. Area nets (night 1) | A0 ×3, A1 ×3, A2 ×4 | 7.5 h |
| 1e. Area scoring | selection-ground pixel scores; each of the 10 area nets with lines_ng1 on 44 | 0.5 h |
| **Stop: rule 2 applied; Ben reads the table** | | |
| 2. Line nets (night 2) | L1 ×2, L2 ×3 | 3.9 h |
| 2e. Line and pair scoring | each line net with area_ng1's stored maps, and with the chosen area net; final pairs | 0.6 h |
| **Total** | 15 nets, 22 evaluations | **about 12.5 h** |

**Short version (one night, about 6.6 h):** A0 ×3, A2 ×3, L2 ×2, and 10 evaluations. It loses A1 and L1, so a win or loss cannot then be put down to the fixes or to the label rules separately.

Outputs go to new folders: data/sanborn/train_v3/ and train_v3_runs/. Labels, scripts and models get a second copy, and nothing is written into unet_data.

## 10. Code changes needed (a list; none written)

**make_labels_v2.py (map mode; a new data folder, train_v3):**
1. Split Ben's deletions into duplicate, partial, false and moved-old (6 px / 60% / 8 px rules), and record the counts in meta.json.
2. Write a weight-code image for the line target (lines_w.png). The codes are: deleted-false strip on or off ink, added line, text near (40 px or less) or far, pipe or sewer.
3. Make text a negative everywhere on the paper (bin 8 grown 1 px, 2 px protection), the margin included.
4. Leave lines with ink support under 0.3 unscored, with their margin, whatever their kind.
5. Write a weight-code image for the area label (area_w.png). The codes are: narrow street, pipe or sewer in a street, text band beside a street, near a deleted-false line, near an added line. Also leave 20 ft either side of inkless lines untaught, and keep inkless lines out of edge.png.
6. Add a `--val-region` option for 5's right quarter (Plan B), or no valmask (Plan A).
7. Copy extra out-of-sample area maps of 1A and 5 as area_in_*.png.
8. Write an audit JSON:
   - the share of Ben's line px within 3 px of any new negative;
   - the inkless lines;
   - street taught on blank paper.
9. Make overlay pictures for Ben.
10. Refuse 44, 90 and the selection plate.

**unet.py (area):**
11. Read area_w.png and multiply its factors into the segmentation weight, beside today's edge weight.
12. Crop shares in proportion to the square root of the taught px (a `--share sqrt` option).
13. Centre about 30% of crops on hard pixels.
14. Keep the last weights by default (keep-best only on request), and an option to average the last K checkpoints.
15. Give the legacy path (train_noguide's recipe) `--seed` and `--out`, and let it run without 44:val. This is needed for A0.
16. Record the area-only validation metrics: street IoU, narrow-street recall, street called block, undecided called block.

**edgenet.py (line):**
17. Store the weight code as a 6th byte per pixel, about 20% more memory (2.3 GB for the six plates; estimate). Map the codes to weights given on the command line.
18. Add `--area-blank-rate` (default 0.15; round 2 uses 0.5), applied on every plate.
19. Augment the 7th input (blur, contrast, shift, erasure), and pick at random among several area_in maps.
20. Centre about 30% of crops on hard pixels.
21. Validate with a named out-of-sample area map, and also with a blank one; keep the last weights by default.

**eval_v2.py and bench_plate.py:**
22. An area-only mode: pixel scores of an area map against Ben's labels on 44, 1A, 5 and 7, split decided/undecided, plus narrow-street recall (as swap pixel_maps44.py).
23. A line-only mode: the line net with a fixed, stored area map.
24. The extra report lines of section 5:
    - void false blocks;
    - line precision on decided and undecided ground;
    - the numbers metric (as errors xtab.py);
    - pipe and sewer false length (as verify pipe_check.py);
    - the deleted-false response.
25. An ensemble option: average several area maps (and line maps) before the outline step.
26. Plate 7 (and later 90) as a plate with its own truth file (`bench_plate.py --make-truth`).

**A new driver (train_v3.py, beside train_v2.py):**
27. The arms of section 4, the phases and stops of section 9, and the rule of section 5 written in before the run.
28. A summary table with seed means, sd and worst seed per arm.

**The line editor (edit_page.html, edit_server.py),** tested on copies only, never on Ben's files:
29. Record rejected rail tracks in a sidecar file, for example rail_rejected.json beside rail_ben.json: kind, points, source rule, the rule file's time, and a reason ("numbers", "lot line", "other"). rail5/design/rejected_5_backfill_example.json shows the format; plate 5's 23 rejected tracks could be back-filled from unet_data/5_rail_rule.json into that sidecar, never into rail_ben.json. A sidecar keeps every reader of rail_ben.json working.
30. Optionally, a reason on delete ("no line here" or "wrong place").

**Outside round 2:** rail5's rail-rule changes (ink_bins, rail_tracks), reviewed on their own.

## 11. What Ben can do by hand that helps most

In order of value:

1. **Check plate 7 next.** It becomes the selection plate (Plan A), so seeds and recipes are judged on ground no compared net has seen, and 1A and 5 can train whole.
   - It is a dense West End plate at 100 ft with 26 mid-block alleys found and a clean batch output, so it should be a quick check (round 1 plate selection).
   - Alleys and narrow streets are where the decided-ground loss sits. Ben's blocks 3-4-9-10-11 on 44 merge in all four new pairs (errors summarize.py).
2. **Check plate 90 before anything ships.** By then 44 will have helped decide twice.
3. **Give the open-land convention** (question 1 below). If possible, check one plate with railway, creek or canal land, for example 53 (rail fan at Court St). That way the nets learn his convention from his own lines, not from the old plates' "open land is block".
4. **Move a line instead of deleting and redrawing it.** 58% of the deleted length on 5, and 64% on 1A, is a line he replaced (errors deletions2.py). The label maker has to guess these with a 6 px rule. A moved line, or a delete marked "wrong place", removes the guess.
5. **Keep deleting false rail tracks.** Once the editor records them (change 29), they become a test set for the rail rule, and their off-line pixels become "not a line" examples. A one-word reason helps: numbers, lot line or other.
6. **Mark inkless street sides at the sheet edge as sheet-edge lines,** or confirm that the label maker may treat any inkless line near the paper edge that way (6c).

**Questions for Ben:**
1. **Open land, Mill Creek, the canal and the railway corridors.** Is this ground block, street, or neither? Should the outline step ever close a ring along a creek bank or a railway edge? (Round 2 leaves this unscored until he answers.)
2. **Alleys and 12-ft passages.** Are they always block sides at 100 ft? And at 200 ft (the plate 60B question)?
3. **Numbers.** Are house numbers, frontage figures and lot numbers never block sides, while a block side that runs through a row of numbers is still a side? This sets the 2 px protection.
4. **Weights.** Do the starting factors look right to him?
   - deleted-false strips 16 on ink;
   - added lines 12;
   - numbers 10 near a street;
   - area hard pixels ×2.

## 12. Sources

All under data/sanborn/bench_2026-11-25/diag/ unless named otherwise:
- design/scripts/design_numbers.py, which writes design/design_numbers.json. It made this note's new numbers:
  - plate 5's right quarter;
  - the crop shares;
  - the seed standard errors (an estimate);
  - the 7th-input F1 drops (from swap's measurements);
  - the GPU hours (from round 1's measured minutes).
- swap/scripts: run_swaps.py, summarize.py, pixel_maps44.py, fp_anatomy.py, shift_test.py.
- errors: summarize.py, xtab.py, deletions2.py.
- verify/scripts: collect_runs.py, numbers_check.py, pipe_check.py.
- ben-labels/scripts: deleted_split.py, sheet_edge_lines.py, edge_pseudo5.py, text_all_plates.py, text_near_lines.py, estimate.py.
- recipe: crop_shares.py, ch7_vs_ng1_training.py.
- rail5/code: summary5.py, score_rail_bench.py, reconstruct_deletes5.py, rail_on_lines5.py.
- verify/scripts/label_prior.py gives the taught px per plate that design_numbers.py reads. Swap's 1A street IoU figures come from its inline check, with no script of its own.
- Elsewhere:
  - train_v2_runs/models/*.json (training minutes);
  - docs/sanborn/bench_2026-11-23/train/findings_full.md (plate selection, the smoke test and repeat_compare).
