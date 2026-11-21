# Sanborn batch benchmark: every agent result in full (21 November 2026)

Raw results of the benchmark workflow (14 agents). The README beside this file is the summary. Paths named here are in data/sanborn/bench_2026-11-21/ (not in git); the scripts, diffs and key tables are copied into this folder under the same names.

## measure: bench44

I built a one-command benchmark for plate 44 and measured the batch on it. Everything is in data/sanborn/bench_2026-11-21/bench44/. Nothing in the repo was changed, and plate 44's files were checked afterwards. All runs were on the CPU and no network was trained.

What the harness does: it runs the batch's outline step on the batch's own maps for 44 (area_ng1 and lines_ng1), applies the step-4 filter from blocks_noguide.py, and then applies the line editor's own clean() and sheet() to get exactly what the editor would show. It scores that against Ben's street map: blocks (panoptic quality), lines, closure, the batch's own "on a printed line" share, and Ben's editing workload. Every score is also given for two folds of the plate.

Faithfulness: run on the guided maps, the outline copy reproduces the stored picks22_guided/22-44/outlines.json byte for byte, with the same SHA-256. This holds under both Pythons (cv2 4.13 and cv2 5.0), and the block mask is identical too. The harness also agrees with the earlier review's scorers: PQ is identical on all 5 runs, and line scores are within 0.002.

How the batch did on 44 (measured):
- **Blocks:** PQ 0.431 (SQ 0.852, RQ 0.506). 23 of Ben's 55 blocks are matched. 13 exported outlines are merges, and they swallow all 32 missed blocks: there are no splits and no other kind of miss. Restricted to the ground Ben decided, PQ is 0.455.
- **Lines the editor shows:** they find 53.2% of Ben's interior lines by length, and 74.8% of what is shown lies on his lines. Green lines are 77.5% right; orange lines are 7.0% right.
- **Closure:** none of the 55 blocks close, even when line ends are snapped across gaps of up to 40 px. None of the 36 outlines survives step 4 as an intact ring.
- **The batch's own claim:** it reports 96.1% of side length "on a printed line", against the true 74.8% (77.5% for green).
- **Ben's workload:** he would delete 184 of 495 shown lines (32.5k px) and draw 164 of his 320 interior lines himself (80.1k of 189.6k px).

The guided chain scores PQ 0.592 but finds fewer lines: recall 41.1% at 73.1% precision.

Where the loss is, from the cheap upper bounds:
- Ben's blocks as the area map with the batch line map: PQ 0.938, all 55 matched, 0 merges.
- The batch area map with Ben's lines as the line map: PQ 0.563, 54 matched, but 77 false blocks (46 of them on ground Ben decided).
- Both from Ben: 0.995 on decided ground, 49 of 55 blocks close, 48 rings intact.

So the block loss is mostly the area map. Where it calls a narrow street or alley "block", no street seed sits between two blocks and they merge. For lines, both networks matter about equally. On its own, the outline step plus step 4 loses only about 7 points of recall and 6 blocks of closure.

Loss step by step for the batch chain (PQ / interior line recall / precision at 5 px):

| Step | PQ | Recall | Precision |
|---|---|---|---|
| Area map alone | 0.455 | 0.407 | 0.285 |
| Watershed regions | 0.431 | 0.334 | 0.269 |
| Straightened outlines | 0.431 | 0.553 | 0.520 |
| Step-4 filter | no block closes | 0.531 | 0.747 |
| What the editor shows | no block closes | 0.532 | 0.748 |

The watershed regions score 0.562 / 0.460 at 8 px, because a region boundary sits a few px off the centre of the line. Step 4 drops 1,619 short pieces (65.2k px, only 6.2% of it on Ben's lines) and 18 paper-edge sides. Dropping them is right for precision, but it breaks every ring.

The folds differ a lot: the batch scores 0.474 on fold A and 0.385 on fold B; the guided chain 0.501 and 0.677. As an estimate, one block moving from merged to matched is worth about 0.014 PQ overall and about 0.03 within a fold.

Not in scope: rail was not scored. rail_ben.json still holds 26 tracks, so the 28-track page file is the current rail truth.

One slip: a copy of the review's PQ scorer was written for about a minute directly into data/sanborn/bench_2026-11-21/, outside bench44/, and then moved into bench44/. Nothing else was written outside the folder.

**Numbers**

All measured on plate 44 against streetmap/22-44.json. Line tolerance is 5 px with directions within 20 degrees. Values are for the whole plate unless marked. All produced by bench44.py, gathered by run_baselines.py into baselines.json, unless another script is named.

BATCH CHAIN (area_ng1 + lines_ng1, outline copy run in the venv as the batch runs it)
- Blocks: PQ 0.4309, SQ 0.8524, RQ 0.5055; 36 predicted blocks, 23 matched, 13 false, 32 missed.
- Of those: 13 merges, 32 true blocks lost in merges, 0 split, 0 missed otherwise.
- Blocks on the ground Ben decided: PQ 0.4545, 9 false blocks.
- Fold A: PQ 0.4737 (decided 0.506), 13 matched, 6 merges.
- Fold B: PQ 0.3852 (decided 0.4018), 10 matched, 7 merges.
- Shown lines:
  - Recall of Ben's interior lines (printed + drawn): 0.5316 (printed 0.5824, drawn 0.2437).
  - Precision 0.7475; green 0.7753 (128.5k px); orange 0.0704 (5.3k px).
  - On decided ground: recall 0.5815, precision 0.8855.
  - Recall at 3/4/6/8 px: 0.507/0.524/0.537/0.543. Precision: 0.719/0.740/0.752/0.756.
  - Fold A: recall 0.550, precision 0.731. Fold B: recall 0.510, precision 0.769.
- Sheet edge:
  - The editor's sheet outline covers 0.943 of Ben's 21.6k px of sheet-edge lines; the network lines cover 0.031.
  - 0.686 of the sheet outline's length is a street side; Ben deletes 22 pieces (11.6k px).
- Closure: 0 of 55 of Ben's blocks closed at snap 1.5, 10 or 40 px (no faces form at all). 0 of 36 outlines are intact rings.
  - If step 4 kept every side: 3 blocks close at 10 px, 11 at 40 px (a what-if).
- The batch's own "on a printed line" share by length is 0.961, against a true precision of 0.7475 (0.7753 for green).
- Editor workload:
  - Delete 184 of 495 shown lines, 32,545 px (33.8k px of what is shown is off Ben's lines).
  - Draw 164 of his 320 interior lines, 80,094 px (88.8k px of his 189.6k px missed).
- Time: outline step 16-19 s; whole run 31-56 s on the system Python, 54-61 s on the venv (the machine was shared with other agents).

LOSS STEP BY STEP, BATCH CHAIN (PQ / decided PQ / interior recall and precision at 5 px / at 8 px)
- 0 Area map alone (P > 0.5 regions): 0.455 / 0.485 / 0.407, 0.285 / 0.541, 0.373
- 1 Watershed regions: 0.431 / 0.460 / 0.334, 0.269 / 0.562, 0.460
- 2 Straightened outlines: 0.431 / 0.455 / 0.553, 0.520 / 0.574, 0.534
- 3 Step-4 filter (what N_edges.json would hold): no faces / no faces / 0.531, 0.747 / 0.543, 0.756
- 4 What the editor shows: no faces / no faces / 0.532, 0.748 / 0.543, 0.756
- What step 4 removes and keeps (step4_dropped.py):
  - drops 1,619 short pieces (65.2k px, 6.2% on Ben's lines) and 18 paper-edge sides (6.8k px, 45.7% on his lines);
  - keeps 499 green sides (128.4k px, 77.5% on his lines) and 30 orange sides (5.3k px, 7.0%).

GUIDED CHAIN (edge_v1 + lines_v2)
- Blocks: PQ 0.5918, SQ 0.8539, RQ 0.6931; 35 matched, 11 false, 9 merges, 19 lost in merges.
- Decided ground: PQ 0.6401. Fold A 0.501, fold B 0.677.
- Shown lines: recall 0.4109, precision 0.731; green 0.8435, orange 0.0317.
- 0 blocks closed, 0 intact rings. Own "on a printed line" share 0.865.
- Workload: delete 28.1k px, draw 113.0k px.

UPPER BOUNDS (maps from make_oracle_maps.py)
- Ben's blocks as the area map, batch line map:
  - PQ 0.9384 (decided 0.9851); 55 matched, 0 merges, 5 false.
  - Lines: recall 0.799, precision 0.853. Closed 31 of 55, 30 intact rings.
- Batch area map, Ben's lines as the line map:
  - PQ 0.5630 (decided 0.6757); 54 matched, 77 false (46 on decided ground).
  - Lines: recall 0.875, precision 0.883. Closed 28, 26 intact rings.
- Both from Ben:
  - PQ 0.7843 (decided 0.9947); 55 matched, 29 false, all on ground Ben did not decide.
  - Lines: recall 0.925, precision 0.914. Closed 49 of 55, 48 intact rings.

HOOK EXAMPLE (bench44.py --step4 variants/step4_green_only.py)
- Dropping orange: precision 0.748 to 0.775, recall 0.532 to 0.530, delete length 32.5k to 27.5k px.

FAITHFULNESS (bench44.py --faith)
- The outline copy on edge_v1 + lines_v2 gives outlines.json with SHA-256 5d8dcda4294d85d0..., identical to the stored picks22_guided/22-44/outlines.json.
- Same result under the venv (cv2 5.0) and the system Python (cv2 4.13). The block mask is identical to unet_data/44_blockmask.png (0 px differ). About 17 s.

CROSS-CHECK (xcheck_review_scorers.py)
- The review's pq44 gives identical PQ and match counts on all 5 runs (batch 0.431 23/13/32; guided 0.592 35/11/20).
- The review's evallib line scores are within 0.002 (batch at 4 px: recall 0.5227 vs 0.5240, precision 0.7391 vs 0.7397).

ESTIMATES (not measured)
- One block moving from merged to matched is worth about +0.014 PQ on the whole plate and about +0.03 within a fold.
- The workload counts are a proxy: a line less than half on Ben's lines counts as deleted, and one of his lines less than half found counts as drawn. Moving and trimming are not counted.

**Harness**

Harness: C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/bench44/bench44.py. It works with the system python, or with the venv python, which gives the same numbers but is slower. The outline step always runs under --python (default: the networks' venv, as the batch runs it).

COMMAND LINE (from the bench44 folder; prints the full JSON on stdout, progress on stderr):
  python bench44.py [--area PNG] [--lines PNG] [--outlines PY] [--step4 PY] [--python EXE] [--tag NAME] [--reuse] [--tol 5] [--ang 20] [--no-pic]
- Defaults:
  - --area: unet_data/44_pred_area_ng1.png (half size, P(block)*255).
  - --lines: unet_data/44_lines_lines_ng1.png (full size, P(line)*255).
  - --outlines: bench44/outlines_copy.py, an exact copy of tools/sanborn/unet/outlines.py. Only its input/output lines differ; `diff` shows it.
- Examples:
  - The batch baseline: `python bench44.py --tag batch`.
  - Faithfulness: `python bench44.py --faith`. It exits 0 only if outlines.json matches the stored guided file byte for byte.
  - All baselines: `python run_baselines.py [--reuse]` writes baselines.json.
  - Oracle maps: `python make_oracle_maps.py`.

VARIANT HOOKS
- --outlines FILE.py: the harness runs `PYTHON FILE.py 44 AREA_PNG LINES_PNG RUN_DIR` with the working directory data/sanborn.
  - It must write RUN_DIR/outlines.json in outlines.py's polygon format: a list of polygons, each a list of sides {a, b, state in 'on print' / 'on detected line only' / 'not on a line' / 'short', paper_edge}.
  - It must print its counts JSON as the last stdout line; share_on_printed_line_by_length is used.
  - Optional: RUN_DIR/44_blockmask.png (half-size binary mask, as outlines.py writes) or RUN_DIR/44_blockinst.png (half-size 16-bit instance labels). These feed the watershed stage of the breakdown; use blockinst for per-block-marker variants.
  - Start a variant from a copy of outlines_copy.py.
- --step4 FILE.py: defines step4(polys) and returns an edges list in N_edges.json format: {src, name, a, b, state 'green'/'orange'}. The default is blocks_noguide.py lines 49-52 as they are. Example: variants/step4_green_only.py.
- --area / --lines: any maps of the right kind. The area map can be any size (it is resized as outlines.py does). The line map must be full size, 10768 x 7219.
- --reuse: rescore an existing runs/TAG/outlines.json without rerunning the outline step.

OUTPUT: runs/TAG/
- outlines.json, 44_outlines.json/.jpg, 44_blockmask.png: from the outline step.
- 44_edges.json: what N_edges.json would hold.
- 44_shown.json: what the editor shows (edit_server.clean plus sheet).
- bench44.json: all scores.
- 44_bench.jpg: quarter size. Shown lines on Ben's lines are green, off them red; his lines that were missed are blue.

JSON KEYS (every score has 'all', 'A' and 'B')
- meta: input paths with sha256[:16], tol_px, ang_deg, outline_step_seconds, total_seconds, decided_ground, folds.
- headline.{all,A,B}: PQ, SQ, RQ, matched, merges, gt_split, fp, PQ_decided, fp_decided, recall_interior, precision, precision_green, precision_orange, ben_blocks_closed (snap 10, IoU >= 0.8), intact_rings, delete_len, draw_len.
- blocks.outlines / blocks.outlines_decided: PQ, SQ, RQ, gt, pred, matched, fp, fn, merges, gt_lost_in_merges, gt_split, gt_missed_other.
- lines_shown: recall_interior, recall_printed, recall_drawn, recall_sheet_edge, precision, precision_green, precision_orange, *_len, recall_interior_decided, precision_decided, tol_sensitivity{3px, 4px, 6px, 8px}.
- sheet: ben_sheet_edge_len, ben_sheet_edge_recall_by_sheet_outline, ben_sheet_edge_recall_by_network_lines, sheet_outline_len, sheet_outline_precision.
- closure.faces.<3_step4_edges | 4_editor_shows | whatif_all_outline_sides_kept>_snap<1.5 | 10 | 40>: faces, closure{ben_blocks_closed_iou80, ben_blocks_closed_iou50}, blocks_from_faces(_decided).
- closure.outline_rings: outlines, all_sides_kept_by_step4, sides_join_end_to_end, intact.
- on_print: batch_share_on_printed_line_by_length, shown_on_ben_lines_by_length, green_on_ben_lines_by_length, and more.
- workload: delete_n, delete_len, shown_len_off_ben, draw_n, draw_len, ben_interior_len_missed, sheet_outline_delete_n, sheet_outline_delete_len.
- stages.<0_area_map_alone | 1_watershed_regions | 2_straightened_outlines | 3_step4_edges | 4_editor_shows>: blocks, blocks_decided, lines (with tol_sensitivity).

DEFINITIONS
- Panoptic quality (PQ): COCO matching at IoU > 0.5 on half-size rasters. A merge is a predicted block holding at least 50% of each of 2 or more of Ben's blocks.
- Decided ground: Ben's 55 blocks, plus every pixel off them where (distance to the nearest block) + (distance to the next block or to the paper edge) is 260 px or less (cached in cache/decided_half.png; picture: folds_and_decided_ground.jpg). Everything else follows COCO's void rule: a prediction more than half in void is not a false positive, and void pixels leave its area.
- Lines: both sets are sampled every 1 px. A sample matches when the other set has a sample within 5 px whose direction is within 20 degrees. Interior = printed + drawn. Precision is measured against all of Ben's lines.
- Closure: the shown lines plus the sheet outline, each end extended by the snap, are polygonized; faces of 400 px2 or more count as blocks, as street_map.py does.

FOLD SPLIT (full-size px; picture: folds_and_decided_ground.jpg)
- Fold A, 'north-west grid + east': (x < 2950 and y < 3560) or x >= 5400. It holds 28 of Ben's blocks (49% of block area, 57% of the paper), 87.0k px of printed lines and 15.4k px of drawn lines.
- Fold B, 'south-west + middle': the rest. 27 blocks, 74.0k px printed, 13.0k px drawn.
- The cuts follow streets: x = 2950 runs between blocks 8/34 and 18/28, y = 3560 along Blue Rock St, x = 5400 along Mad Anthony St. Blocks 5, 12 and 22 straddle the x = 5400 cut slightly and go to A by centroid; 38 goes to B; 37 and 41 cross x = 2950 and go to B.
- Ben's blocks and predicted blocks are assigned by centroid, line samples by their own position, and whole lines (workload) by their midpoint.
- Use: tune on A, test on B (or the reverse).

TIME (CPU, 21 Nov, machine shared with other agents): outline step 16-23 s; one full run 31-56 s on the system Python, 54-61 s on the venv; --reuse 12-35 s; run_baselines.py 3-4 min; --faith about 19 s.

**Files**

All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/bench44/:
- bench44.py: the harness. One command, JSON output; the docstring holds usage, hooks, JSON keys, definitions and timings.
- outlines_copy.py: exact copy of tools/sanborn/unet/outlines.py with every output redirected (the default outline step).
- make_oracle_maps.py: builds maps/44_area_benblocks.png (Ben's blocks as the area map) and maps/44_lines_benlines.png (Ben's lines as the line map).
- run_baselines.py: runs the 5 baselines and writes baselines.json (headline numbers, stage table, closure, rings, on-print share, workload, sheet).
- step4_dropped.py writes step4_dropped.json: what step 4 drops and keeps, and how much of it lies on Ben's lines.
- xcheck_review_scorers.py writes xcheck_review_scorers.json (cross-check against the review's pq44 and evallib). xcheck_pq44_review_copy.py is an unchanged copy of the review's research-maps_pq44.py.
- variants/step4_green_only.py: example of the --step4 hook.
- runs/batch/: the benchmark baseline.
  - outlines.json: the batch's outline step on 44.
  - 44_edges.json, 44_shown.json, bench44.json.
  - 44_bench.jpg: shown lines green on Ben's lines, red off them; his missed lines blue.
  - 44_outlines.jpg.
- runs/guided/, runs/ub_benarea+batchlines/, runs/ub_batcharea+benlines/, runs/ub_benarea+benlines/: the other baselines.
- runs/batch+step4_green_only/: the hook example.
- runs/area_ng1+lines_ng1/: a fresh default run, identical to runs/batch.
- runs/_faith/, runs/_faith_venv/, runs/_faith_sys/: the faithfulness runs; their outlines.json is byte-identical to picks22_guided/22-44/outlines.json.
- runs/_venvcheck/: the same scores under the venv Python.
- folds_and_decided_ground.jpg: picture of the fold cuts and the decided ground.
- cache/decided_half.png: the decided-ground mask.
- _second_copy_scripts/: a second copy of every script.

### B1 [high] Block loss is mostly the area map: narrow streets and alleys called block, so neighbouring blocks merge

- **kind:** measurement
- **plates:** 44 measured; probably every plate with narrow alleys (estimate)
- **evidence:** Batch: 23 of 55 blocks matched. All 32 misses are merges, with 13 exported outlines each holding at least half of 2 or more of Ben's blocks; there are 0 splits. With Ben's blocks as the area map and the batch's own line map: 55 of 55 matched, 0 merges, PQ 0.938 (0.985 on decided ground). With the batch area map and Ben's lines: 54 of 55 matched, but 77 false blocks (46 on decided ground), PQ 0.563. The false blocks are street strips that area_ng1 calls block, cut out by the true lines. Area map alone: 0.455; after the watershed: 0.431; straightening does not change PQ. Matched blocks also fit loosely: SQ 0.85, against 0.98 with Ben's area map. (bench44.py, run_baselines.py)
- **impact:** Up to +0.5 PQ: 0.431 against 0.938 with a perfect area map
- **fix:** Change the outline step, then retrain later. Cut the block seeds with the line map so every block gets its own watershed marker, and add street seeds along strong detected lines. The earlier review measured about +0.09 PQ at the watershed stage on 44 for markers. Write it as an --outlines variant, tune on fold A and test on fold B. The longer-term fix is on the area-net side: out-of-fold area maps and less street called block.
- **effort:** Outline variant about 30-50 lines, CPU only; scored in under a minute per try

### C1 [high] Nothing the editor shows closes into a block; the cause is corner joining on noisy maps, not the step-4 filter as such

- **kind:** failure-mode
- **plates:** 44 measured: 0 of 55 closed. The review saw the same pattern on the other plates
- **evidence:** Batch: 0 of 55 of Ben's blocks closed, at snap 1.5, 10 or 40 px (no faces form). 0 of 36 outlines survive step 4 whole, and none have all sides joined end to end. Step 4 drops 1,619 short pieces (65.2k px). Only 6.2% of that length is on Ben's lines, so dropping them is right for precision, but every ring loses at least one piece. With both maps from Ben the same code keeps 48 of 84 rings whole and 49 of 55 blocks close, so the filter works on clean input; the corners fail on the batch maps. If step 4 kept everything: 3 blocks close at 10 px, 11 at 40 px. (bench44.py closure.*, step4_dropped.py)
- **impact:** From 0 blocks Ben gets for free to as many as are matched (23 today)
- **fix:** In the outline step, join every kept side to the next kept side even across a run of short pieces. Intersect the two lines when the corner is plausible; otherwise add a bridging side marked as a corner. That way the rings survive step 4. Measure with closure.faces.4_editor_shows_snap10 and closure.outline_rings.
- **effort:** About 20-40 lines in an --outlines variant

### M1 [medium] The batch's 'on a printed line' share overstates quality by about 21 points

- **kind:** measurement
- **plates:** 44 measured; the same number is in every run_plates.json entry
- **evidence:** share_on_printed_line_by_length 0.961, against a true precision of 0.7475 for what is shown and 0.7753 for green. Recall of Ben's interior lines is 0.532. On decided ground precision is 0.886, so about half of the false length lies where Ben left the ground open (rail corridor, canal, creek). (bench44.py on_print, lines_shown)
- **fix:** Stop reporting the on-print share as a quality number. Report bench44's headline (PQ, recall, precision, blocks closed) for 44 next to each batch run.
- **effort:** None for the bench; a log change for run_plates

### P1 [medium] Orange sides are almost all wrong

- **kind:** proposal
- **plates:** 44 measured
- **evidence:** Orange is 7.0% on Ben's lines for the batch (30 sides, 5.3k px) and 3.2% for the guided chain (14.6k px). The --step4 hook dropping orange: precision 0.748 to 0.775, recall 0.532 to 0.530, delete length 32.5k to 27.5k px. (variants/step4_green_only.py via bench44.py)
- **impact:** +2.7 points precision for -0.2 points recall
- **fix:** Hide orange by default in step 4, or gate it on the line network as the review suggested. Check it on fold B.
- **effort:** 1 line

### M2 [medium] Editor workload on 44 is high, especially lines Ben must draw

- **kind:** measurement
- **plates:** 44 measured; estimated by a 50% rule
- **evidence:** Delete 184 of 495 shown lines (32.5k px). Draw 164 of his 320 interior lines (80.1k of 189.6k px). Also delete 22 sheet-outline pieces (11.6k px). With a perfect area map: draw 33.8k px. With a perfect line map: 14.7k px. (bench44.py workload)
- **fix:** Track draw_len and delete_len as headline numbers. They fall mainly with B1 (merges) and C1 (closure).
- **effort:** Already in the harness

### M3 [medium] Loss step by step: the straightening helps lines; the filter trades recall for precision

- **kind:** measurement
- **plates:** 44
- **evidence:** Interior recall and precision at 5 px:
- area map alone: 0.407 / 0.285;
- watershed regions: 0.334 / 0.269 (0.562 / 0.460 at 8 px, because a region boundary sits a few px inside the line's centre);
- straightened outlines: 0.553 / 0.520;
- step 4: 0.531 / 0.747;
- editor clean(): 0.532 / 0.748.
PQ: 0.455, then 0.431, then 0.431, then no faces. (bench44.py stages)
- **fix:** Judge each change at its own stage. Compare region stages at 8 px (tol_sensitivity) and line stages at 5 px.
- **effort:** In the harness

### M4 [medium] The two folds disagree a lot; small gains are noise

- **kind:** measurement
- **plates:** 44, two folds
- **evidence:** Batch: fold A 0.474, fold B 0.385. Guided: fold A 0.501, fold B 0.677. Estimate: one block moving from merged to matched is worth about +0.014 PQ on the whole plate and about +0.03 within a fold. (bench44.py headline.A and headline.B)
- **fix:** Tune on fold A and report fold B. Count a change as real only if it gains on both folds and by about 0.03 PQ or more overall. Ben checking a second plate would be the real test.
- **effort:** None

### P2 [low] Sheet outline: about a third of it is not a street side

- **kind:** proposal
- **plates:** 44 measured
- **evidence:** The editor's sheet() outline covers 94.3% of Ben's sheet-edge lines (21.6k px), but only 68.6% of its 36.9k px length is a street side; Ben deletes 22 pieces (11.6k px). The network lines cover only 3.1% of his sheet-edge lines. (bench44.py sheet)
- **impact:** About 11.6k px less to delete on 44
- **fix:** Untested: hide sheet pieces that run through ground the area map calls block deep inside the paper.
- **effort:** Small, in the editor or step 4

### M5 [low] Line scores depend on the tolerance for some maps

- **kind:** measurement
- **plates:** 44
- **evidence:** Batch recall at 3/4/5/6/8 px: 0.507/0.524/0.532/0.537/0.543, so it is stable. But the run with Ben's blocks as the area map jumps from 0.744 at 4 px to 0.799 at 5 px (precision 0.797 to 0.853): in places Ben's lines sit 4-5 px off the network ridge. (xcheck_review_scorers.json, tol_sensitivity)
- **fix:** Keep 5 px as the main tolerance and read tol_sensitivity before claiming a gain smaller than a few points.
- **effort:** None

### V1 [low] The harness is faithful to the repo code and to the earlier review's scorers

- **kind:** measurement
- **plates:** 44
- **evidence:** bench44.py --faith: the outline copy on edge_v1 + lines_v2 reproduces picks22_guided/22-44/outlines.json byte for byte (SHA-256 5d8dcda4294d85d0) under both Pythons, and the block mask is identical. The review's pq44 gives the same PQ and counts on all 5 runs. Its evallib line scores agree within 0.002. The scores are identical under the system Python and the venv (runs/_venvcheck). Ben's own lines through faces() give 55 faces and PQ 1.0.
- **fix:** Nothing to fix. Rerun --faith after any change to outlines_copy.py.
- **effort:** None

## measure: census

I ran a health census on all 109 plates of today's batch. It uses the batch outputs only, all on the CPU, and writes only to data/sanborn/bench_2026-11-21/census/. Plates 43, 44, 45, 80 and 82A had no outline step in the batch, so I ran a redirected copy of outlines.py on their ng1 maps; it reproduces the review's 44 numbers (36 blocks, 96.1% on a printed line). Every per-plate indicator is measured from the files. The only judgement is the visual label, which I gave each plate by eye from thumbnails.

Main results:

1. The batch's losses sit almost entirely on the uncut PDF sheets and the 400-ft plates, and plate 44 is neither. By eye, 27 plates are bad or poor: 16 bad (the editor gets almost none of the plate's streets) and 11 poor (a district dropped or many blocks merged). They are 25% of the plates, 29% of the paper and 56% of the ground area.
   - 22 of the 32 PDF sheets are bad or poor, and all 10 plates at 400 ft.
   - Cut plates: 0 of 39 at 200 ft, 3 of 36 at 100 ft (only the small pieces 8B, 15B and 55B).
   - Plate 44 ranks 73rd of 109 by suspicion. Its batch outline step scores PQ 0.431 against Ben's map: 23 of 55 blocks found, 13 false, and all 32 misses are merges (anchor44.py). That is below the review's 0.515, which used the guided lines_v2 in place of lines_ng1. So a plate that looks 'ok' in the census is only as good as 0.43.

2. On the 200-ft PDF sheets, the networks themselves mostly worked. The outline step threw their work away. On 90 the networks found nearly every block and street, and the editor got 3 lines. Over the atlas:
   - 3,123 block regions were found and 2,930 exported.
   - 154 were dropped as nested on 28 plates, and 39 more by straighten().
   - On 15 sheets the editor keeps less than 25% of the line length the line network drew; healthy plates keep 0.74 to 0.86.
   - On the 400-ft sheets the area network also misses most streets: line-network share 0.006 against 0.027 on cut plates.

3. Scale, read for all 109 plates. I read the printed note on the uncut sheet each plate comes from; 23 plates also have a georeference measurement, and all 23 agree within 2%.
   - 36 plates are at 100 ft to the inch, 63 at 200 and 10 at 400.
   - Correction to the review: plates 43 and 44 are at 100 ft (read, and measured 101.0 and 101.1 ft/in from their placements). The training set is therefore 43 at 100 ft plus 45, 80 and 82A at 200 ft, and the ground-truth plate is a 100-ft plate. It is not true that all training plates are at 200 ft.
   - Insets at another scale found on 46, 48, 78 and 94.

4. Smaller failures:
   - 432 editor lines on 30 of the 32 PDF sheets lie within 150 px of the paper edge (the margin exported as street sides).
   - 38 rail rule tracks sit inside the printed KEY box (its RAILROAD and TROLLEY samples) on 32 plates.
   - All 109 plates are recorded 'done' with no log errors, so the batch record does not show any of these failures.

5. Proposed QA flag: a plate is 'suspect' if any of these holds:
   - Q1: the editor keeps less than 60% of the line network's line length;
   - Q2: 2 or more block regions are dropped as nested;
   - Q3: the printed scale is not 100 or 200 ft, or not recorded.

   It flags 25 plates, catches 25 of the 27 bad or poor plates, has no false alarms, and misses 21 and 55B. Adding Q4 (area network calls 90% or more of the paper block) catches 21 at the cost of one false alarm (32). The review critic's gate 'one region over 30% of the paper' would have flagged 48 plates with 21 false alarms. These counts are in-sample: I set the thresholds on the same plates I then judged.

**Numbers**

MEASURED (from batch outputs):
- 109 plates: 77 cut plates, 32 PDF sheets; 109 recorded 'done', 0 log failures; total 5,070 s, median 41 s, max 143 s (plate 28). census.py, from run_plates.json and run_plates.log
- Block regions found 3,123, exported 2,930; 154 dropped as nested on 28 plates; 39 dropped by straighten(). census.py, classify.py ('extra')
- Plates exporting exactly 1 block: 17 (8B 22 23 27 30 47 48 55B 73 78 81 82B 88 90 92 94 95). census.py
- Share of the line network's line length that reaches the editor, median by group:
  - cut 100 ft: 0.744; cut 200 ft: 0.856;
  - PDF 200 ft: 0.582; PDF 400 ft: 0.155;
  - plate 44: 0.737.
  - (census_finish.py, venv Python for its thinning)
- Hole-boundary share, median: cut 200 ft 0.075, cut 100 ft 0.08, PDF 200 ft 0.293, PDF 400 ft 0.619. census.py (definition of critic c9)
- Area-net block share, median: cut 100 ft 0.684, cut 200 ft 0.783, PDF 200 ft 0.875, PDF 400 ft 0.952. census.py
- Tinted share above every training plate (over 0.26): 36 plates; over 0.4: 22. Correlation of tint with area-net unsure share on cut plates: r = 0.44. census.py
- Editor lines within 150 px of the paper edge on PDF sheets: 432 lines on 30 of 32 sheets (7,390 editor lines on PDF sheets in all). census_finish.py, classify.py
- Rail rule tracks inside the printed KEY box: 38 tracks on 32 plates (KEY found on all 32 PDF sheets, match score 0.72 or more, and on cut plates 1B, 29, 34, 37, 76). rail_key.py
- Rule tracks in all: 4,092 railroad and 1,214 streetcar; railroad over 15% of the ink on 1B, 2, 3, 9, 41 (rail-yard plates). census.py
- Plate 44, batch outline step against Ben's map: PQ 0.431, SQ 0.852, RQ 0.505; 23 found, 13 false, 32 missed, all by merge. anchor44.py (the review's research-maps_pq44.py, imported)
- Plate 44 indicators: tint 0.255, block share 0.75, unsure 0.223, largest region 0.275, 36 blocks, 529 editor lines, green 0.943, suspicion rank 73 of 109. classify.py

SCALE (read by eye, georeference measured):
- 100 ft: 36 plates (1A-18B, 43, 44, 51-58, 62, 63); 200 ft: 63; 400 ft: 10 (46-50, 92, 93A, 93B, 94, 95). Read from scale/notes_*.jpg made by scale_find.py; table written by scale_table.py
- Georeference check on 23 plates (QGIS points, corrected for GDAL's 150-dpi PDF render, and placement grids): all within 2% of the read value; 43 = 101.0 ft/in, 44 = 101.1, 45 = 201.4, 80 = 201.8, 82A = 199.6. scale_measure.py
- Insets: 46 (200-ft inset), 48 (three 200-ft sub-plats), 78 (400-ft inset), 94 (200-ft sub-plat). Found by eye; other sheets were not searched systematically (scale_insets.py found nothing usable).
- Ground area: 100 ft 4,498 acres (6.6%); 200 ft 36,409 acres (53.8%); 400 ft 26,767 acres (39.5%). census_finish.py

JUDGED BY EYE (visual.json, thumbnails from thumbs.py):
- bad 16, poor 11, ok 82. 'ok' means no worse than plate 44; on 560-px panels a single merged block cannot be seen, so 'ok' is weak evidence.
- Bad or poor: 25% of plates, 29% of paper, 56% of ground. classify.py
- Bad or poor by group: cut 100 ft 3/36, cut 200 ft 0/39, cut 400 ft 2/2, PDF 200 ft 14/24, PDF 400 ft 8/8. classify.py

QA FLAG CHECK (in-sample, classify.py; counts are flagged / bad-or-poor caught / false alarms / missed):
- Q1-Q3: 25 / 25 / 0 / 2 (21, 55B).
- Q1-Q4: 27 / 26 / 1 (32) / 1 (55B).
- Single rules:
  - editor keeps < 60%: 23 / 23 / 0 / 4;
  - 2 or more nested: 16 / 16 / 0 / 11;
  - hole share 0.25 or more: 21 / 21 / 0 / 6;
  - scale not 100 or 200 ft: 10 / 10 / 0 / 17;
  - critic's 'region over 30% of paper': 48 / 27 / 21 / 0;
  - critic's '1 or more nested': 28 / 21 / 7 / 6;
  - critic's 'blocks per paper Mpx under a quarter of the median': 20 / 20 / 0 / 7.

**Files**

All files are under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/census/ (about 70 MB). This is the only copy: the rules allow writing nowhere else.

Census outputs:
- census.csv and census.json: 109 rows × 80 columns. They hold:
  - source, size, paper share and paper Mpx;
  - tinted share, area-net block and unsure shares, line-network share;
  - block-mask share, regions found, largest-region share and its edge-band share;
  - nested regions dropped (count, length, area), holes and hole share;
  - blocks exported, sides (all, short, paper-edge), editor lines, green share, editor length;
  - share on print and on the detected line, short pieces;
  - railroad and streetcar px and tracks, rail inside the KEY;
  - seconds, batch state and log issues;
  - ft_per_inch with status, inset and measured value, training scale, ground acres, blocks per 100 acres;
  - line-network skeleton length, editor_per_line, outline_kept_share, edge lines;
  - suspicion rank and score, failure modes, qa_suspect, qa_why, eye check.
- census_raw.json, census_base.json: intermediate files.
- classify.json: failure modes (count, plates, share of plates, paper and ground), full ranking, candidate QA rules scored, the proposed flag's results.
- visual.json: my eye label for each of the 109 plates.
- rail_key.json: KEY box and rail found inside it.
- anchor44.json: PQ of the batch outline step on 44.

Scale:
- scale/scale_table.json: the scale per plate.
- scale/measured.json: the georeference check.
- scale/notes_00-07.jpg: the crops I read the scale notes from.
- scale/sheet_N.jpg: 1/8-size overviews of the uncut sheets.
- scale/inset78.jpg, scale/inset94.jpg, scale/crop57_note.jpg.

Thumbnails (thumbs/):
- thumb_{95,94,27,88,81,78,50,48,22,47,90,23}.jpg: the 12 worst plates.
- thumb_59A.jpg, thumb_63.jpg.
- sheet_*.jpg: contact sheets covering every other plate.
- key_boxes.jpg: rail found in the KEY.
- Drawing key: red = street holes dropped, magenta = nested blocks dropped, cyan = regions with no fitted side, blue = largest region, green and orange = editor lines, grey = dropped short and paper-edge sides.

Outline step on the five placed plates: guided_ol/ (43, 44, 45, 80, 82A; the batch refused these).

Scripts (the run order is in census.py's docstring):
- census.py, census_finish.py (needs the venv Python for thinning), scale_find.py, scale_measure.py, scale_table.py;
- classify.py, thumbs.py, rail_key.py, anchor44.py;
- outlines_copy.py: the review's critic_outlines_copy.py, which is outlines.py with its outputs redirected;
- scale_insets.py: its result was not usable.

### C1 [high] The outline step throws away what the networks found on uncut PDF sheets: a margin block ring plus RETR_EXTERNAL

- **kind:** bug
- **plates:** 23 plates (21 PDF sheets): near-empty 22 23 27 30 47 48 50 73 78 81 88 90 92 94 95; partial 41 46 49 72 74 91 (and 8B 15B on Q1)
- **evidence:** Thumbnails thumbs/thumb_90/30/27/88/22/23.jpg: the red (street holes) and magenta (blocks found but dropped as nested) fills cover most of the map, yet 1-14 editor lines are exported, mostly on the paper edge. On 90 the networks found nearly every block and the editor gets 3 lines; on 30: 22 regions found, 1 exported. Atlas: 154 nested regions dropped on 28 plates. Hole share: median 0.293 on 200-ft PDF sheets against 0.075 on 200-ft cut plates. Editor keeps under 25% of the line network's length on 15 sheets (census.json: nested_dropped, hole_share, editor_per_line).
- **impact:** Largest single loss in the batch: 34% of the paper and about half the ground area of the atlas sits on plates where blocks are dropped as nested. Most of it should come back with no retraining, judging by 90, 30, 27 and 88.
- **fix:** In a copy of outlines.py: use RETR_CCOMP or RETR_TREE, fit straighten() to hole contours and to nested outer contours, and mask the map margin and KEY box on PDF sheets before the watershed (mk=1). Then re-run only the outline step on the 32 PDF sheets on the CPU and recompute the census; the census columns are the before numbers.
- **effort:** medium

### C2 [high] Scale table for all 109 plates; correction: plates 43 and 44 are at 100 ft to the inch, not 200

- **kind:** measurement
- **plates:** all 109: 36 at 100 ft, 63 at 200 ft, 10 at 400 ft; insets on 46, 48, 78, 94
- **evidence:** Read on every plate's uncut sheet (scale/notes_00-07.jpg). Checked against 23 georeferenced plates (scale/measured.json), all within 2%: the 43 and 44 placements give 101.0 and 101.1 ft/in; 45, 80 and 82A about 200. Earlier docs (INSTRUCTIONS22.md:154, reports/2026-11-13_newplates_43) also say 43 is at 100 ft. Critic-2's 'all five training plates about 200 ft' is wrong. So is its c10_scale44 reading: 44 at native size is a 100-ft plate, its 0.5x test stood for 200 ft, not 400.
- **impact:** The ground-truth plate 44 is the minority training scale (100 ft). No 200-ft or 400-ft plate has truth, although 200-ft plates are 54% of the ground and 400-ft plates 40%.
- **fix:** Use scale/scale_table.json as the per-plate ft_per_inch record, with a per-inset entry where a sheet has one. In blocks_noguide, resample 400-ft plates by 2x to 200 ft before both networks and scale outlines.py's pixel constants. Both 100 and 200 ft are already in training (1 and 3 plates).
- **effort:** small

### C3 [high] 400-ft sheets: the area network misses most streets as well as losing them in the outline step

- **kind:** failure-mode
- **plates:** 10 (46 47 48 49 50 92 93A 93B 94 95), all bad or poor by eye
- **evidence:** Line-network share 0.006 on 400-ft PDF sheets against 0.027 to 0.029 on cut plates. Area block share median 0.952. thumb_50 and thumb_47 show streets found only in fragments; on 48 the streets are fragmentary even inside the 200-ft insets. Blocks per 100 acres: 0.03 on 400-ft sheets against 8 on 200-ft cut plates (census.json).
- **impact:** 40% of the atlas's ground area; currently almost no usable block lines.
- **fix:** Resample by 2x to 200 ft before both networks (C2), then re-run the census on these 10. Add one 400-ft plate to the truth only after that.
- **effort:** medium

### C4 [medium] The sheet margin is exported as editor street sides on PDF sheets

- **kind:** bug
- **plates:** 30 of 32 PDF sheets (432 lines); on 22 23 27 30 73 81 88 90 95 almost every exported line
- **evidence:** census.json edge_lines: editor lines whose middle is within 150 full px of the paper edge. outlines.py marks paper_edge only when the middle is outside a 31-px erosion of the paper, but on an uncut sheet the paper edge is the scanner bed or the margin. Orange and green lines run along the sheet edge in thumb_30, thumb_81 and thumb_88.
- **impact:** 432 of 7,390 editor lines on PDF sheets are pure noise for Ben to delete.
- **fix:** For source 'pdf', set paper_edge for sides within the margin band (about 150 px), or better outside a map-area polygon (the neat line). Skip sheet() lines for PDF plates in the editor (review pp-10).
- **effort:** small

### C5 [medium] Rail rules find the printed KEY's RAILROAD and TROLLEY samples as tracks

- **kind:** bug
- **plates:** 32 plates, 38 tracks: 1B 21 22 23 24 27 30 32 36 37 41 42 46 48 49 50 72 73 74 76 77 78 79 81 86 88 89 90 91 92 94 95
- **evidence:** rail_key.py locates the KEY by matching its '-KEY-' header (score 0.72 to 0.95 on all 32 PDF sheets and on cut plates 1B, 29, 34, 37, 76; at most 0.44 on plates without one). Inside the box: 49,824 railroad px and 53,947 streetcar px of the bins on PDF sheets, 38 rule tracks. thumbs/key_boxes.jpg shows the railroad bin (red) on the sample line and the streetcar bin (orange) on the trolley sample. This confirms review rail-6.
- **impact:** A false track on about 30% of the plates. Small in px, but every one must be deleted by hand, and they would be negatives for a rail network.
- **fix:** Mask the KEY box (header match, then a fixed box below it) before ink_bins and rail_tracks. The matcher is already in rail_key.py.
- **effort:** small

### C6 [high] Proposed QA flag ('suspect') for run_plates / blocks_noguide, checked against the census

- **kind:** proposal
- **plates:** flags 25: 8B 15B 22 23 27 30 41 46 47 48 49 50 72 73 74 78 81 88 90 91 92 93A 93B 94 95
- **evidence:** Rules:
- Q1: editor_len / line-network skeleton length < 0.6;
- Q2: 2 or more nested block regions dropped;
- Q3: ft_per_inch not 100 or 200, or not recorded.

Against the eye check: 25 flagged, 25 of 27 bad or poor caught, 0 false alarms, 2 missed (21: open land with green lines on the river banks; 55B: an 8-acre piece). The optional Q4 (area block share 0.9 or more) catches 21 and adds one false alarm (32).

The critic's gates do worse: 'one region over 30% of the paper' flags 48 with 21 false alarms (cemeteries, parks and estates on cut plates); '1 or more nested' gives 7 false alarms and 6 misses. In-sample: the thresholds were set on these plates. classify.py, classify.json 'candidates'.
- **impact:** Today all 109 plates are 'done' with no log issue, including 15 near-empty ones; the flag would have marked every bad plate.
- **fix:** Compute Q1 and Q2 at the end of the outline step: line skeleton length from N_lines (half size, thinned), editor length from the edges, and a RETR_TREE nesting count. Q3 needs the scale table. Write state 'suspect' plus the reasons into run_plates.json and show them in the editor's plate list.
- **effort:** small

### C7 [high] The benchmark plate does not cover where the batch fails

- **kind:** measurement
- **plates:** 44 (rank 73 of 109); PDF sheets 22 of 32 bad or poor; cut 200-ft plates 0 of 39
- **evidence:** Bad or poor by eye, by group: cut 100 ft 3/36 (small pieces only), cut 200 ft 0/39, cut 400 ft 2/2, PDF 200 ft 14/24, PDF 400 ft 8/8. Plate 44 is a cut 100-ft plate, and its indicators sit in the healthy middle of the census. Its PQ (0.431, anchor44.py) measures the merge errors common to 'ok' plates, not the post-processing loss that costs 56% of the ground.
- **impact:** Tuning only on 44 cannot show, or reward, the largest available gain.
- **fix:** Keep 44 for PQ and merges, but add a second truth plate: a 200-ft PDF sheet where the networks found most blocks (90 or 30, quick to check by eye), and later a 400-ft one after resampling. Use the census as an atlas-wide regression check on each change: suspect count, editor_per_line by group, nested total.
- **effort:** medium

### C8 [medium] The batch chain scores PQ 0.431 on 44, below the review's 0.515 (which used lines_v2)

- **kind:** measurement
- **plates:** 44
- **evidence:** anchor44.py: the outline step (outlines_copy.py) on the batch's own 44_pred_area_ng1.png and 44_lines_lines_ng1.png gives 23 of 55 found, 13 false, 32 missed, all by merge. The same score on the block mask before straightening is 0.431. The review's 0.515 (findings_full.md:782) paired area_ng1 with the guided lines_v2 as a stand-in, because lines_ng1 did not exist yet.
- **impact:** Even plates marked 'ok' in the census probably lose about a third of their blocks to merges.
- **fix:** Use 0.431 as the batch baseline for 44. Markers per block (review M1) target exactly these merges.
- **effort:** small

### C9 [low] A big region on a cut plate is mostly a real big parcel, not a failure

- **kind:** failure-mode
- **plates:** 15 flagged (8B 15B 25 26B 31 37 39 55B 59B 61 64A 64B 71 82B 83B); 3 bad or poor by eye
- **evidence:** Contact sheets thumbs/sheet_2.jpg and sheet_61.jpg: cemeteries, parks, estates and open land are one block. Only the small pieces 8B, 15B and 55B are real merges.
- **impact:** Avoids 12 to 21 false alarms.
- **fix:** Do not gate on the largest-region share for cut plates. Gate on it only together with the edge band on PDF sheets (the ring), or drop it.
- **effort:** small

### C10 [medium] Tinted plates lie outside the training colour range (risk, not yet a seen failure)

- **kind:** failure-mode
- **plates:** 36 plates with tint over 0.26 (above every training plate and 44), 22 over 0.4; mostly 100-ft downtown cut plates (1A 1B 2 4 5 7 8B 12 51-55B ...)
- **evidence:** census.json tinted_share, area_unsure_share. Unsure share correlates with tint on cut plates (r = 0.44). Contact sheets show no failure at 560 px, so the effect is unmeasured, not absent.
- **impact:** About 6% of the ground but a third of the plates, the densest downtown ones.
- **fix:** Make a tinted 100-ft plate (e.g. 54A or 51) the next truth plate after a PDF sheet. Hue jitter in the next retraining (review M6).
- **effort:** medium

### C11 [low] Step 4 drops about a quarter to a third of the fitted outline length even on healthy plates

- **kind:** failure-mode
- **plates:** 30 plates under 60% kept (25 of them bad or poor); median kept 0.718 on cut 100-ft plates, 0.79 on cut 200-ft, 0.652 on 44
- **evidence:** census.json outline_kept_share = editor length / length of every side of every exported polygon. Confirms review pp-6 across the atlas.
- **impact:** No block closes in the editor.
- **fix:** As pp-6: fit pieces across short gaps, or keep short pieces that the line network supports.
- **effort:** medium

### C12 [low] River banks, creek banks and rail lines exported as green street sides

- **kind:** failure-mode
- **plates:** seen on 21 (Ohio river banks), 19 (Muddy Creek), 59A (rail lines); not detected automatically
- **evidence:** thumbs/sheet_21.jpg and thumb_59A.jpg. Confirms review pp-4 on unplaced plates.
- **impact:** A minority of lines, but they are shown as checked (green).
- **fix:** Gate green on line-network support (review: green precision 78% to 85% on 44), and keep the rail bins out of the block-line candidates.
- **effort:** medium

## measure: visual-cut

I audited the batch's block lines on 14 cut (non-PDF) plates by eye. The lines checked are exactly what the line editor shows: clean(N_edges.json) plus sheet(), with clean() copied from edit_server.py. Each plate was compared with its scan in overviews and in crops at 0.4-1.0x full size. The plates were: downtown at 100 ft (5, 10, 53, 1A); residential at 200 ft (66, 60B); heavily tinted (1B, 2, 8B, 54B); riverside (2, 26A, 52, 3); hillside (64A, 52, 26A); rail yard (1B, 3, 2). I also ran plate 44 through a scratch copy of the outline step on the batch's own two maps, so it could be classified against Ben's map with the same tools.

**Plate 44, the benchmark, all measured:**
- PQ 0.431: 23 of 55 blocks found, 13 false outlines, and all 32 misses are merges.
- Precision 0.754 by length.
- Recall: 0.59 of Ben's printed sides and 0.25 of his drawn sides.
- The earlier review's PQ of 0.515 used the guided lines_v2 network, not the batch's lines_ng1.

**What costs Ben the most time (editor time is my estimate):** over the 14 plates it comes to about 470 min, or 1.4-55 min per plate; plate 44 itself is about 65 min.
1. Closing the outlines, about 68% of the time: line ends that stop short of a corner or a gap, sides broken into pieces, and corners left open. Measured: 0.5-1.3 open ends per editor line. Open corner gaps have a median of 159-190 px, so only 0-5 per plate fall within the editor's 60 px Close-corners reach. The outline step drops 9% (66, 60B) to 34% (53) of the outline as short pieces; on 44 it is 31%.
2. Missed alleys and streets, about 18%: two blocks merged into one outline. These are the hardest to spot, because nothing is drawn where the alley should be. Counted by eye:
   - 60B: about 27 of about 30 mid-block alleys missed.
   - 5: 16.
   - 10: 9.
   - 53 and 2: 8 each.
   - 1A: 7.
   - 66: at least 6.
3. Lines along rail tracks, about 7%, concentrated on the yard plates:
   - 1B: 149 lines (32.9k px, 24% of its editor line length).
   - 3: 154 lines (28.0k px).
   - 2: 82 lines (16.5k px).
   - On 44, every line lying mostly on the rule's railroad or streetcar ink is wrong: 32 lines, none on Ben's map.

**Why lines go missing on plate 44 (measured):** of Ben's 189k px of interior street sides, 54% reach the editor. Of the 88k px that are lost:
- at least 31k px are in places where neither network saw the street and the block mask swallowed it (the networks' fault);
- about 23k px are in places where the street survived in the block mask but no side was exported (the outline step's fault);
- the rest is unclear.

**Error types seen elsewhere that plate 44 does not contain**, so its score cannot see them:
- the Ohio River and its wharves inside one block covering 17-30% of the paper (1B, 2, 3, 26A, 52);
- dense rail yards and fans;
- gasometers;
- the printed key box on a cut plate (1B);
- buildings or structures standing in wide streets called block: market houses and Garfield Place's centre strip on 5, the Central Parkway median on 1A, viaducts on 53 and 64A, a playground on 2;
- the 100-ft scale, with wide named downtown alleys;
- large-scale insets with giant lettering (8B, 54B);
- hillside roads, steps and the incline (52, 64A, 26A).

Heavy tint showed no error type of its own.

**Numbers**

MEASURED:
- 44, batch outline step: PQ 0.431, 23 of 55 blocks found (tp), 13 false (fp), 32 missed, all 32 by merging. Script: merges44.py, using pq44_copy.py, an unchanged copy of research-maps_pq44.py.
- 44: 13 outline polygons each cover 2-5 of Ben's blocks. Of the gaps they join, 19 are under 45 px (alley width) and 20 are wider. Script: merges44.py.
- 44: precision 0.754 by length over all exported sides; green 0.781; green with line-network support 0.852. Recall: Ben's printed sides 0.590, drawn sides 0.251, sheet-edge sides 0.031. Script: score_copy.py (verify-postproc_score.py) on out44/44_outlines_poly.json.
- 44: of Ben's 189,395 px of interior sides, 101,572 px (53.6%) are found. Of the lost length:
  - neither network saw the street and the mask swallowed it: 31,129 px;
  - line network missed it, street side unknown: 22,548 px;
  - both networks saw it, street kept, side not exported: 14,653 px;
  - only the area network saw it, street kept: 6,763 px.
  Script: cause44.py.
- 44: false editor lines (under 20% on Ben's lines), by the ink under them: railroad 31 lines / 9,737 px; lot line 37 / 5,326; no ink 30 / 5,071; water pipe 34 / 4,780; text 30 / 3,766; building 7 / 896; sewer 5 / 421. Script: merges44.py.
- 44: lines more than 50% on the rail ink bins: 32 lines, 9,923 px, none of them on Ben's lines. Script: auto_audit.py, then the inline check.
- 44: the street-side 'blank paper' test does not separate right lines from wrong ones, so it was dropped. Script: auto_audit.py, then the inline check.
- Editor lines (count / px) per plate. Script: auto_audit.py.
  - 44: 495 / 133,542
  - 5: 598 / 189,464
  - 1A: 161 / 45,661
  - 10: 394 / 128,426
  - 53: 660 / 165,400
  - 66: 712 / 253,277
  - 60B: 263 / 83,678
  - 1B: 557 / 138,341
  - 2: 485 / 138,983
  - 8B: 12 / 2,590
  - 54B: 13 / 5,840
  - 26A: 464 / 151,102
  - 52: 443 / 138,634
  - 64A: 529 / 120,432
  - 3: 510 / 139,516
- Open line ends per plate: total; breaks (two broken ends per break); open corner ends with median gap; dangling ends. Script: auto_audit.py.
  - 44: 583; 126 breaks; 67 corner ends, 190 px; 263 dangling
  - 5: 618; 183; 94, 170 px; 157
  - 1A: 190; 32; 31, 165 px; 94
  - 10: 496; 139; 63, 176 px; 154
  - 53: 816; 176; 165, 184 px; 298
  - 66: 380; 108; 82, 162 px; 81
  - 60B: 143; 55; 9, 100 px; 23
  - 1B: 678; 126; 111, 176 px; 314
  - 2: 629; 127; 116, 185 px; 259
  - 26A: 434; 82; 113, 178 px; 157
  - 52: 579; 132; 97, 186 px; 217
  - 64A: 521; 107; 113, 159 px; 194
  - 3: 646; 116; 102, 173 px; 311
- Corner ends within the editor's 60 px Close-corners reach: 0-5 per plate. Script: auto_audit.py summary.
- Outline length dropped as short pieces. Script: linebins.py.
  - 66: 9.4%; 60B: 8.9%; 26A: 20.6%; 5: 21.6%; 54B: 22.5%; 10: 27.1%
  - 3: 27.9%; 1A: 28.7%; 52: 29.7%; 64A: 30.3%; 44: 31.4%
  - 1B: 31.9%; 2: 32.0%; 53: 34.2%; 8B: 39.3%
- Lines more than 50% on the rail bins (lines / px). Script: auto_audit.py.
  - 1B: 149 / 32,907
  - 3: 154 / 27,954
  - 2: 82 / 16,533
  - 26A: 64 / 13,020
  - 52: 63 / 9,850
  - 64A: 53 / 7,845
  - 5: 17 / 3,378
  - 53: 22 / 3,102
  - 10: 9 / 2,676
  - 66: 9 / 2,086
  - 1A: 2 / 517
  - 60B: 0
- Largest block-mask piece as a share of the paper. Script: slivers.py.
  - 64A: 0.635; 8B: 0.479; 1B: 0.295; 54B: 0.291; 44: 0.275
  - 52: 0.261; 2: 0.222; 10: 0.19; 1A: 0.185; 60B: 0.174
  - 3: 0.173; 26A: 0.17; 53 and 66: under 0.05
- Small or thin block pieces (under 25% of the plate median, or under 90 px wide). Script: slivers.py.
  - 2 and 3: 18 each; 53 and 1B: 11 each; 26A: 9; 5: 8; 52: 7
  - 10 and 66: 5 each; 1A: 4; 44: 3; 64A: 1; 60B, 8B and 54B: 0

BY EYE (count once, expect about +-30%), from views/ and annotated/:
- Alleys missed (full plus partial):
  - 60B: 27 (22+5); 5: 16 (9+7); 10: 9 (5+4); 53: 8 (4+4); 2: 8 (4+4); 1A: 7 (4+3)
  - 66: 6 (3+3), and probably more, because 200-ft alleys are hard to see at overview scale
  - 1B: 3; 26A: 3; 52: 2; 64A: 2; 3: 2; 8B: 1
- Missed stub alleys and courts: 5: 5; 66: 3; others 0-2.
- Streets not cut: 64A: 5; 26A: 4; 52: 4; 1B: 3; 53: 2; 2: 2; 3: 2; 10: 1; 5, 1A, 66 and 60B: 0.
- Structures or spills in streets: 5: 5; 53: 4; 1A: 2; 10, 1B, 2, 26A, 52 and 54B: 2 each.
- Water bodies called block: 1B, 2, 26A, 52: 1 each; 3: 2; 44: 1 (creek and canal).
- Gasometer arcs on 1B: 3. Freight house and depot walls: 1B and 2 together about 6. Key-box lines on 1B: 2.
- Lot lines kept: 53: 1 (lot 168); 66: 1-2.

ESTIMATED (tally.py; length = count x typical block side; time per editor operation assumed, see the script's docstring):
- Ben's editor time over the 14 unplaced plates, about 471 min in total:
  - dangling ends 151; broken sides 116; alleys and streets 86; corners 55
  - rail 31; small pieces 15; spills 10; walls, lots, text and pipes 5; water banks 2
- Per plate (min): 53: 54.6; 1B: 53.0; 3: 50.3; 2: 49.9; 5: 47.3; 52: 40.5; 64A: 36.2; 10: 34.4; 26A: 34.1; 66: 25.2; 60B: 24.2; 1A: 17.5; 8B: 2.0; 54B: 1.4.
- Plate 44: 65.5 min.

**Files**

All files are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/visual-cut/. Nothing was written anywhere else.

Main scripts (all read-only on the repo):
- vlib.py: loader and drawing; copies edit_server's clean() and sheet().
- view.py: overviews and crops.
- annotate.py: the annotated crops.
- auto_audit.py: open ends, rail-bin lines, on-Ben check for 44.
- slivers.py: piece sizes and widths.
- linebins.py: ink under lines; dropped short length.
- notches.py.
- netcrop.py: network panels.
- ends_view.py.
- tally.py: by-eye counts plus time estimates, giving tally.json and tally_out.txt.
- merges44.py: PQ and merges on 44.
- cause44.py: which step lost Ben's sides.
- outlines_copy.py: the outline step with outputs redirected, giving out44/.
- pq44_copy.py and score_copy.py: copies of the review's scorers.
- census_cut.py and thumbs.py: plate selection.

Pictures:
- annotated/: 17 marked crops. 5_alleys_markets, 60B_midblock_alleys, 1B_river_key_rail, 1B_gasometers, 53_railfan_viaduct, 26A_river_rail_stubs, 64A_hillside_streets, 2_riverfront, 10_downtown_alleys, 66_residential_200ft, 52_mount_adams, 3_rail_yard, 1A_parkway_alley, 8B_inset, 54B_inset, 44_creek_canal_rail and 44_alleys_streets (with Ben's lines in magenta).
- views/: N_overview.jpg for all 15 plates, the zooms, and net_5_4100_3000.jpg and net_60B_1950_1050.jpg (what each network said on a missed alley).
- thumbs/: montages of all 72 cut plates.

Data:
- audit/: N_audit.json, N_slivers.json, N_linebins.json, N_notches.json; 44_merges.json, 44_cause.json, 44_score.json.
- out44/: the batch outline step on 44.

### VC-1 [high] Outlines are not closed: line ends stop short, sides are broken, corners are left open (largest share of Ben's time)

- **kind:** failure-mode
- **plates:** every plate audited (15 including 44); worst 53, 1B, 3, 2, 44
- **evidence:** auto_audit.py: 0.5-1.3 open ends per editor line, for example 53 with 816 open ends on 660 lines, 44 with 583 on 495, and 66 with 380 on 712. Open corner gaps have a median of 159-190 px on every plate except 60B, and only 0-5 corner ends per plate are within the editor's 60 px Close-corners reach. linebins.py: 9-34% of the outline is dropped as short pieces. cause44.py: on 44, 14.7k px of Ben's sides were seen by both networks and kept as street, but never exported, plus 6.8k px seen by the area network only. annotated/5_alleys_markets.jpg and views/ends_53_0_4400.jpg show the end types.
- **impact:** About 322 of 471 estimated editor minutes on the 14 plates (68%). No block closes on its own. Most corners need a select-two-lines-and-C, because the gaps are wider than C's 60 px reach.
- **fix:** In outlines.py straighten() (lines 56-90):
1. Join neighbouring 'line' sides that lie on one straight line across runs of short pieces (the review's pp-3 bridge; on 44, broken pairs 136 to 67 and recall +3 points).
2. Then extend every line to its next line in ring order, skipping short pieces, when they meet at more than 20 degrees within about 250 px, and export the closed ring.
The causes:
- outlines.py:57: approxPolyDP with TOL 8 cuts a notched area edge into pieces.
- outlines.py:63 and :70: pieces under MINLEN 60 or CUT 130 become 'short'.
- outlines.py:71-88: meet() closes a corner only if the next piece is a 'line' within CORNER 120 px, and refuses near-parallel pieces (:73).
- blocks_noguide.py:51 drops the short pieces.
- edit_server.clean() joins pieces only within 25 px.
Score on 44 by counting Ben blocks closed.
- **effort:** small (about 40 lines in straighten, CPU only, measurable on 44)

### VC-2 [high] Missed alleys: blocks merged across alleys, and stub alleys and courts not drawn

- **kind:** failure-mode
- **plates:** 11 of 14 by eye: 60B about 27, 5 16 (+5 stubs or courts), 10 9, 53 8, 2 8, 1A 7, 66 at least 6, 1B 3, 26A 3, 8B 1; 44 measured
- **evidence:** Plate 44: merges44.py finds 13 polygons each covering 2-5 of Ben's blocks, 32 of 55 blocks lost by merging (PQ 0.431), and 19 joined gaps under 45 px. cause44.py: 31.1k px of Ben's sides lie where neither network saw the street and the mask swallowed it. netcrop.py on 5 (L'Hommedieu Alley, about 40 px wide): the area network gives P(block) > 0.5 across the alley and the line network draws nothing. On 60B (alleys about 15-18 px) the area network dips only faintly and the line network draws nothing, so only a dropped V-notch is left at each alley mouth. Pictures: annotated/60B_midblock_alleys.jpg, 5_alleys_markets.jpg, 10_downtown_alleys.jpg, 44_alleys_streets.jpg.
- **impact:** About 86 min (18%) of the estimated time, at about 40 s each, because Ben must find the alley on the print with nothing drawn there and then draw two sides and four corners. These are the errors Ben is most likely to overlook.
- **fix:** Mainly the networks. Their labels teach 1922 alleys that are gone today as block, and their sides as 'not a line' (review labels-5 and line-2), and the 100-ft plates are outside the training scale.
- Retrain with Ben's checked alleys (44, and future plates) plus a skeleton-recall loss.
- Resample 100-ft plates to 200 ft (review critic-2).
In outlines.py:
- Seed streets also from thin P<0.5 ridges of the area map, without erosion. Today outlines.py:38 (SEED_S = 8) can never seed a street narrower than about 17 px, which is every 10-12 ft alley at 200 ft.
- Use one watershed marker per block (review M1). The two-label watershed at :42 cannot split blocks that touch.
- **effort:** medium for the outlines.py part (CPU); the retraining is Ben's

### VC-3 [high] Rail tracks and yards become block lines and small spurious blocks

- **kind:** failure-mode
- **plates:** 1B, 3, 2 most; 26A, 52, 64A, 53 fan; 44 has 32 such lines
- **evidence:** auto_audit.py, lines more than 50% within 6 px of the railroad or streetcar bins: 1B 149 lines / 32.9k px (24% of its editor line length), 3 154 / 28.0k, 2 82 / 16.5k, 26A 64 / 13.0k, 52 63 / 9.9k, 64A 53 / 7.8k. On 44 all 32 such lines (9.9k px) are off Ben's map and none is right. Yard fragments: slivers.py finds 18 small or thin pieces on 2 and on 3 (3 on 44). Pictures: annotated/3_rail_yard.jpg, 1B_river_key_rail.jpg, 53_railfan_viaduct.jpg, 2_riverfront.jpg.
- **impact:** About 31 min estimated, mostly 5-8 min each on 1B, 3 and 2, plus the yard fragments. Easy to delete, but tedious.
- **fix:** outlines.py: read unet_data/N_bins.png, which run_plates.py writes earlier in the same pass. Demote any side more than 50% on bins 4 or 5 to orange, or drop it: on 44 this removes 9.9k px of wrong line and no right line. Treat ground covered by dense rail bins as undecided (mk = 1, like off-paper at outlines.py:40). Causes: the line network draws tracks (review pp-4), and outlines.py:31 and :54 accept track ink as printed line.
- **effort:** small (about 15 lines)

### VC-4 [medium] Water called block: Ohio River, wharves, creek and canal inside one huge block; bank lines exported as street sides

- **kind:** failure-mode
- **plates:** 1B (29.5% of paper), 52 (26%), 2 (22%), 3 (17%, river and Mill Creek), 26A (17%); 60B river bank about 3k px; 44 creek and canal (27.5%)
- **evidence:** slivers.py gives the largest block-mask piece's share of the paper (see numbers). Seen in views/*_overview.jpg and annotated/1B_river_key_rail.jpg, 26A_river_rail_stubs.jpg, 44_creek_canal_rail.jpg (creek and canal bank lines).
- **impact:** Few lines to delete (about 2 min estimated), but one outline swallows the river, and on 44 it costs a false outline in PQ.
- **fix:** Area network: water is never taught. outlines.py: before the watershed, mask printed water (the blue water tint) as off-map (mk = 1, alpha = 0), so its banks are not exported. Add a QA flag 'suspect' when one piece covers more than 15% of the paper (review critic-1).
- **effort:** small

### VC-5 [medium] Structures and spills in wide streets called block: market houses, esplanade, parkway median, viaducts, playground, inset streets

- **kind:** failure-mode
- **plates:** 5 (5), 53 (4), 1A (2, incl. Central Parkway median), 10, 1B, 2, 26A, 52, 54B (2 each); not on 44
- **evidence:** By eye: on 5 the Sixth Street Market House and the Flower Market are inside blocks 29 and 26, and Garfield Place's centre strip is inside block 42. On 1A the Central Parkway median is a thin block with about 3.6k px of orange lines. On 54B the area spills into Alma St and its side is missing. slivers.py finds 0-16 thin pieces (under 90 px wide) per plate. Pictures: annotated/5_alleys_markets.jpg, 1A_parkway_alley.jpg, 54B_inset.jpg, 53_railfan_viaduct.jpg.
- **impact:** About 10 min estimated. The side of the true block is missing or displaced, and wrong lines lie in the street.
- **fix:** Area network: these look like blocks and are untaught (examples once Ben checks a 100-ft plate). outlines.py: drop pieces with an inscribed width under about 90 px or under 10% of the plate median (today MIN_AREA = 6000 px at :26 and :47 is 1-3% of a median block). Flag pieces bounded by street seeds on two opposite sides.
- **effort:** small (post-processing); the training examples are Ben's

### VC-6 [medium] Streets not cut: hillside paper streets, stub streets, steps, incline, streets running to the river

- **kind:** failure-mode
- **plates:** 64A (5; 14 polygons, one covering 64% of the paper), 26A (4), 52 (4), 1B (3), 53, 2, 3 (2 each), 10 (1); 44: 20 wide gaps joined
- **evidence:** Pictures: annotated/64A_hillside_streets.jpg (unbuilt avenue and viaduct), 26A_river_rail_stubs.jpg (Gabriel St and Center St stubs), 52_mount_adams.jpg (Wood Steps, incline), 2_riverfront.jpg (Elm St and Race St to the river). Plate 44 numbers from merges44.py.
- **impact:** Included in the 86 min for alleys and streets; each street costs about 40 s.
- **fix:** Same causes and fixes as VC-2, plus the 'suspect' QA flag for very large pieces.
- **effort:** medium

### VC-7 [low] Wrong ink taken as block line: lot lines, water pipes and sewers, text, building walls including gasometers

- **kind:** failure-mode
- **plates:** 44 measured; 1B (3 gasometer arcs, freight houses), 2 (freight depot and station walls), 53 (one lot), 66 (lot or drive lines), 8B and 54B (sides dropped under lettering)
- **evidence:** merges44.py, false editor lines on 44 by ink: lot line 37 lines / 5.3k px, water pipe and sewer 39 / 5.2k, text 30 / 3.8k, building 7 / 0.9k. On unplaced plates only a few were seen at the audit scale; at full size 66 was clean (views/ends_66_5800_4700.jpg). Pictures: annotated/1B_gasometers.jpg. Shallow notches at house numbers (notches.py, depth under 30 px) number 26-135 per plate and show up as broken sides rather than wrong lines.
- **impact:** About 5 min estimated, plus the broken sides counted in VC-1.
- **fix:** Make green require line-network support (review pp-2: green precision on 44 from 78% to 85%). Make a run of 3 or more sides turning the same way orange, to catch gasometers and banks. The line network should be taught pipes and lot lines as negatives in the next retraining.
- **effort:** small

### VC-8 [low] Small spurious blocks, paper-edge slivers and the printed key box

- **kind:** failure-mode
- **plates:** 2 and 3 (18 each, mostly the yard), 53 (11, 5 at the edge), 1B (11, key box), 26A (9), 5 (8), 1A (4, one on a paper tab); 44: 3
- **evidence:** slivers.py. Pictures: views/1A_overview.jpg (polygon 13 on a paper tab), views/53_overview.jpg (Fountain Square pieces), annotated/1B_river_key_rail.jpg (key box lines).
- **impact:** About 15 min estimated.
- **fix:** Base MIN_AREA (outlines.py:26 and :47) on the plate's median block and require a minimum inscribed width. Widen the paper-edge band (outlines.py:94, now 15 px) for sides running parallel to the edge. Add a per-sheet 'not map' polygon (key, scale, title) for cut plates as well (review critic-1).
- **effort:** small

### VC-9 [high] Benchmark blind spots: error types on the unplaced plates that plate 44 does not contain

- **kind:** measurement
- **plates:** 44 against all 14
- **evidence:** Present on 44: alley and street merges; rail (2 corridors, 32 lines); creek and canal banks; lot lines; pipes and sewers; text; broken sides; open corners; dangling ends; 3 small pieces. Absent from 44:
- the Ohio River and wharves as one block (1B, 2, 3, 26A, 52);
- dense rail yards and fans (1B, 3, 2, 53), with up to 154 track lines and 18 fragments per plate;
- gasometers (1B);
- a printed key box on a cut plate (1B);
- structures in wide streets (5, 1A, 53, 2, 64A);
- the 100-ft scale, with wide named downtown alleys and courts (5, 10, 53, 1A, 2, 1B, 52, 3);
- large-scale insets with giant lettering (8B, 54B);
- hillside roads, terraces, steps and an incline (64A, 52, 26A).
Heavy tint (1A 0.75, 54B 0.85) showed the same error types as light plates. The 200-ft lightly tinted plates (66, 60B) drop only 9% of the outline as short pieces, against 31% on 44.
- **impact:** A change scored only on 44 cannot show gains or losses on water, yards, street structures, insets, hillsides or the 100-ft scale.
- **fix:** Add one checked plate of each kind to the truth set: a 100-ft downtown plate (5 or 53), a yard plate (1B or 3), a riverfront plate (2 or 52), a hillside plate (64A) and an inset. Until then, report the truth-free measures for every batch plate (auto_audit.py, slivers.py, linebins.py): open ends per line, the share on rail bins, the largest piece's share of the paper, and the number of small pieces.
- **effort:** small for the measures; Ben's time for the truth plates

### VC-10 [medium] The batch's benchmark number on plate 44

- **kind:** measurement
- **plates:** 44
- **evidence:** outlines_copy.py (critic_outlines_copy.py) run on 44_pred_area_ng1.png and 44_lines_lines_ng1.png into out44/: 36 blocks, 96.1% 'on a printed line'.
- merges44.py: PQ 0.431 (23 tp, 13 fp, 32 fn, all by merging).
- score_copy.py: precision 0.754 by length; recall 0.590 printed, 0.251 drawn.
- cause44.py: 53.6% of Ben's interior side length reaches the editor.
The review's PQ of 0.515 for area_ng1 used the guided lines_v2, not lines_ng1.
- **impact:** This is the baseline any change should be compared against on 44.
- **fix:** Use out44/ together with merges44.py, score_copy.py and cause44.py as the before numbers.
- **effort:** none

## measure: visual-pdf

I audited the batch on the 32 uncut sheets taken from PDFs. All of them have cufp/N/source.json: 19-24, 27, 30, 32, 36, 41, 42, 46-50, 72-74, 77-79, 81, 86, 88-92, 94 and 95. Plate 93 exists only as the cut plates 93A and 93B, so it is not a PDF sheet. 77, 79 and 89 were not on the list but are PDF sheets, so I included them.

1. What is printed on the sheets (checked by eye on thumbnails and full-size crops):
- No sheet has a neat line, meaning no printed frame around the map. The drawing simply stops, and blank paper runs to the paper edge.
- Every sheet has the same printed parts: a KEY box (top left, top centre, top right, bottom left or bottom right, depending on the sheet), the title 'ATLAS OF CINCINNATI, O. VOL. 1 or 2' with the plate number in the top-right corner, a hand-lettered 'SCALE n FT. TO AN INCH' note, a scale bar with the line 'Copyright 1922 by the Sanborn Map Co.', and one compass rose with a long arrow (plate 19 has two).
- 24 sheets are 200 ft to the inch. 8 sheets are 400 ft to the inch: 46, 47, 48, 49, 50, 92, 94 and 95. The earlier review listed only 46-50; 92, 94 and 95 are new.
- Insets at another scale: 200-ft insets on 46, 48 (Sub Plats A, B and C), 92 ('Sub. Plan') and 94 ('Sub. Plat'), and a 400-ft inset on 78 (printed 'Scale 1" = 400''). 47 has a small 'Detail of lots 44 & 45' box at a larger scale, with no scale printed.
- Boxed insets, or panels split by a heavy rule, at the main scale: 19, 21, 23, 24, 27, 36, 41, 42, 72, 73, 74, 89, 91 and 92.
- All of this is in scale_table.json.

2. What the networks got right underneath the broken outlines:
- My copy of the outline step reproduces the batch exactly on 32 of 32 sheets: the same blocks and every exported side.
- Inside the map ground, the area network finds 784 block regions (nested ones included, at least outlines.py's minimum block size) across the 32 sheets. The batch exported 445 blocks.
- The pictures in potential/ show the networks tracing most streets in the urban parts. Examples: plate 90, where the batch exported 1 block with 3 sides; plate 30, 1 block with 9 sides.
- Run on the batch's own network maps, the two fixes (RETR_CCOMP, which keeps nested blocks and street holes, plus my map mask) give:
  - 884 blocks instead of 445;
  - 14,457 exported sides instead of 7,390;
  - 2 sheets with 5 or fewer blocks instead of 18.
- RETR_CCOMP alone gives 591 blocks and leaves 7 sheets with 5 or fewer blocks.

3. The map-area detector, map_area.py (CPU only, 5-13 s per sheet). It finds:
- the paper, with its own test;
- the KEY, the title with the plate number, the scale notes, the scale bars and the compass roses with their arrows, by template matching;
- the heavy inset and panel rules, including stretches where the rule is printed thinner.

For the map ground itself, it closes and fills the printed ink. It returns a full-size mask, polygons, the excluded boxes, the frame lines, and the separate regions (main map and each inset). I checked every overlay by eye:
- The KEY, title, scale note and scale bar were found on all 32 sheets, and all 33 compass roses were found.
- 28 sheets are fully right.
- 4 are partly wrong:
  - 23: the lower panel stays joined to the main map;
  - 27: St. Joseph Cemetery, which is open towards the bottom of the sheet, is marked off-map;
  - 46: only the inset's scale bar is boxed, not the main map's;
  - 91: the diagonal rule does not split the sheet in two.
- The mask is identical under the networks' venv (OpenCV 5.0) and system Python (OpenCV 4.13).

4. Problems that remain after both fixes:
- The 400-ft sheets: the networks see about 2.5 times less street. Plates 50 and 95 still come out as 1-2 blocks covering 96% of the map ground.
- The insets at another scale need their own resampling. A single scale per sheet would get them wrong.
- Open land is called block: on the 200-ft sheets, a median 80% of the block ground lies in regions over 20 acres.
- Rivers, the canal bed and rail land are also called block.
- Bug in the repo's paper mask for plate 24 (cufp/24/png_alpha_s4.npy): it marks the boxed inset as off the paper, so the batch treated that inset as off-paper.

None of these numbers is a quality score: there is no ground truth on any PDF sheet.

**Numbers**

All numbers are measured unless marked "estimated" or "read by eye". Paths are relative to C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/visual-pdf/.

Reproduction check
- My copy of the outline step reproduces the batch on 32 of 32 PDF sheets: same block counts and identical exported sides. [run_outline_variants.py external, then compare_variants.py]

The batch against the two outline fixes (32 PDF sheets) [compare_variants.py, on variants/*/ from run_outline_variants.py]
- Batch: 445 blocks, 7,390 exported sides, 6,929 green. 18 sheets with 5 or fewer blocks. On all 32 sheets the largest block is bigger than the map ground, because it includes the margin.
- RETR_CCOMP alone: 591 blocks, 15,951 sides, 15,067 green. 7 sheets with 5 or fewer blocks.
- RETR_CCOMP plus the map mask: 884 blocks, 14,457 sides, 13,956 green. 2 sheets with 5 or fewer blocks (50 and 95, both 400 ft). 19 sheets still have one block covering more than 30% of the map ground.
- Examples (batch → both fixes):
  - 30: 1 block / 9 sides → 34 / 512
  - 90: 1 / 3 → 45 / 524
  - 22: 1 / 1 → 10 / 258
  - 27: 1 / 5 → 42 / 336
  - 94: 1 / 0 → 14 / 398
  - 50: 2 / 26 → 1 / 149
  - 95: 1 / 5 → 2 / 153

What the networks found [net_potential.py → potential.json]
- Area-network block regions inside the map ground (nested ones included, at least 6,000 full-size px): 784 across 32 sheets. Outermost regions only: 433. The batch exported 445.
- Share of the ground outside the map (margin, KEY, title) that the area network calls block: median 0.978, range 0.90-0.995.
- Share of the map ground it calls block: median 0.837 on 200-ft sheets, 0.934 on 400-ft sheets.
- Largest area-network region as a share of the map ground: median 0.37 on 200-ft sheets, 0.86 on 400-ft sheets.
- Share of line-network pixels that fall outside the map: median 0.031 (0.25-0.32 on 50 and 95).

Detector, map_area.py [test_map_area.py → maparea_check/summary.json, every overlay checked by eye]
- Found correctly: KEY 32/32, title 32/32, main scale note 32/32, scale bar 32/32 (on 46 only the inset's bar), compass roses 33/33.
- Map ground as a share of the paper: 0.42 (plate 22) to 0.84 (plate 77).
- 5-13 s per sheet on the CPU.
- Identical mask under the venv (OpenCV 5.0) and system Python (OpenCV 4.13) on 30, 48, 78 and 92. [inline check]
- Agreement between its own paper mask and the repo's png_alpha_s4 (overlap divided by union): 0.984-0.992 on 31 sheets, 0.960 on plate 24.

Template scores [probe_templates.py (unblurred) and map_area.py (blurred)]
- Real KEYs 0.72-0.99 against non-KEY ground at most 0.29 (unblurred).
- Compass roses: real 0.74-1.0, best non-rose 0.59.
- A second scale bar must score at least 0.85: heavy rules scored 0.60-0.76, the 46 inset's bar 0.84 before blurring.

Scale (read by eye) [scale_table.json, make_thumbs.py, crop.py]
- 24 sheets at 200 ft to the inch; 8 at 400 ft (46, 47, 48, 49, 50, 92, 94, 95).
- 200-ft scale bar: 0-600 ft = 912 full-size px on plate 19, i.e. 1.52 px per ft (measured on a crop, about ±1%).
- 400-ft bar: 0-1200 ft = 887 px on plate 47, i.e. 0.74 px per ft.

200-ft against 400-ft sheets [failure_modes.py → failure_modes.json]
- Medians, 200 ft (24 sheets) against 400 ft (8 sheets):
  - street share of the map: 0.163 against 0.066;
  - line share of the map: 0.020 against 0.008;
  - width of the street corridors found: 40 against 18 half-size px (52.6 against 48.6 ft);
  - blocks after both fixes: 29 against 8.5;
  - share of block ground in regions over 20 acres: 0.80 against 0.99.
- Largest block after both fixes: 70-470 acres on 200-ft sheets, 980-2,200 acres on 400-ft sheets. The acreage of the 200-ft insets on 400-ft sheets is estimated, because it is computed at the main scale.
- The vertical fold in the middle of each sheet has no measurable effect (line share in the fold band is about the same as elsewhere).

Insets [inset_check.py → inset_check.json]
- 200-ft insets on 400-ft sheets: street share 0.107-0.169, line share 0.011-0.025. Their 400-ft main maps: 0.034-0.090 and 0.003-0.009.
- 78's 400-ft inset: street share 0.083, against 0.112 for its 200-ft main map.

**Files**

All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/visual-pdf/

Detector
- map_area.py: the detector. map_area(scan_bgr, alpha_s4=None) returns a dict (mask, mask8, polygons, excluded, frames, regions, flags); map_mask(scan_bgr) returns the full-size bool mask. The CLI writes only into the folder given by --out.
- templates/*.png and make_templates.py: the templates (must stay beside map_area.py).
- map_area_final_snapshot.py: second copy of the final map_area.py.
- map_area_v1.py: the first version, kept for the record.

Detector check
- maparea_check/N_map_area.jpg: overlays I checked by eye (off-map grey, map edge green, KEY and title magenta, scale note and bar blue, compass rose orange, rules red, region labels).
- maparea_check/N_map_area.json: polygons, boxes, regions, scores.
- maparea_check/N_mask8.png: 1/8-size masks for all 32 sheets.
- maparea_check/summary.json.
- mont/final_00.jpg to final_15.jpg: the overlays in pairs.
- test_map_area.py, montage.py.
- maparea_check_v1/ and maparea_check_v4/: earlier versions, kept for the record.

Sheet audit
- thumbs/N.jpg (make_thumbs.py) and crops/*.jpg (crop.py): what I looked at.
- scale_table.json: the scale of every sheet and inset.
- probe_templates.py / probe_templates.json: first template-score probe.

Network potential
- potential/N.jpg: network maps above the batch export.
- potential/N_mapmask.jpg: network maps with off-map ground greyed.
- potential.json, from net_potential.py.

Outline fixes
- outlines_ccomp_mask.py: redirected copy of outlines.py with --mask and --ccomp switches.
- run_outline_variants.py: runs it on all sheets; results in variants/external (reproduces the batch), variants/ccomp, variants/ccomp_mask (final masks) and variants/ccomp_mask_v4mask (earlier masks).
- compare_variants.py → compare_variants.json and compare/N.jpg (batch above, both fixes below).

Remaining failure modes
- failure_modes.py → failure_modes.json.
- inset_check.py → inset_check.json.

### pdf-1 [high] The outline step throws away almost everything the networks found on the PDF sheets; RETR_CCOMP plus the map mask recovers most of it

- **kind:** bug
- **plates:** All 32 PDF sheets. 14 sheets exported a single block: 22, 23, 27, 30, 47, 48, 73, 78, 81, 88, 90, 92, 94 and 95 (46 and 50 exported 2).
- **evidence:** My copy reproduces the batch exactly on 32 of 32 sheets. On every sheet the batch's largest block includes the margin (it is 1.0-2.1 times the size of the map ground). The area network calls a median 97.8% of the margin, KEY and title ground block. RETR_CCOMP alone: 445 → 591 blocks, 7 sheets left with 5 or fewer. RETR_CCOMP plus the map mask: 884 blocks, 14,457 sides, 2 sheets with 5 or fewer. Pictures: compare/30.jpg and compare/47.jpg (batch on top, both fixes below); potential/90_mapmask.jpg (network maps with off-map ground greyed).
- **impact:** Turns 18 near-empty sheets into usable first guesses (only 50 and 95 stay near-empty). No quality score is possible without ground truth.
- **fix:** In a copy of outlines.py: use alpha = map_area.map_mask(scan), or load maparea_check/N_mask8.png and resize it to full size with INTER_NEAREST; then use RETR_CCOMP and straighten both outer and hole contours. outlines_ccomp_mask.py is a working copy with both changes behind switches (--mask, --ccomp). Off-map ground is then seeded as street side, and sides along it count as paper_edge and are dropped.
- **effort:** small: about 15 lines in an outlines.py copy; map_area costs 5-13 s per sheet on the CPU

### pdf-2 [high] No neat line on any PDF sheet: the map area has to be inferred from the ink and the printed parts (map_area.py)

- **kind:** measurement
- **plates:** all 32
- **evidence:** Every thumbnail checked, plus full-size corner crops of 22, 30, 72 and 90: the drawing stops and blank paper runs to the edge. map_area.py finds the KEY 32/32, title 32/32, scale note 32/32, scale bar 32/32 and compass rose 33/33 (all checked by eye in maparea_check/N_map_area.jpg and mont/final_*.jpg). Partly wrong on 4 sheets: 23 (the sheet-24 panel stays joined to the main map; same scale), 27 (St. Joseph Cemetery is open towards the bottom of the sheet and is marked off-map; it is open land), 46 (the main 400-ft scale bar is not boxed; it sits on the map's bottom edge), 91 (the diagonal rule does not split the sheet; same scale).
- **impact:** Removes margin, KEY, title, scale note, scale bar and compass roses from the block step, and gives one island per inset.
- **fix:** Use map_area.py as delivered. Its 'regions' output gives the main map and each inset separately, for per-region scaling.
- **effort:** done

### pdf-3 [medium] The repo's paper mask for plate 24 cuts its boxed inset off the paper

- **kind:** bug
- **plates:** 24 (31 other sheets agree with map_area's paper mask at 0.984-0.992)
- **evidence:** In cufp/24/png_alpha_s4.npy the inset box at the left middle (about x 300-2150, y 3830-5120 full-size px) is 0 (crops/alpha24_small.png). Its overlap-over-union with map_area's own paper mask is 0.960. outlines.py treats alpha = 0 as off-paper, so the batch never looked inside that inset.
- **impact:** The inset of 24 gets outlines.
- **fix:** On PDF sheets, use map_area's own paper and map mask (it already ignores alpha_s4 except to compare). Separately, find out how png_alpha_s4 is built for PDF sheets: an inset frame touching the paper edge must not be flooded as scanner bed. Do not rewrite the file in place without Ben.
- **effort:** small

### pdf-4 [high] 400-ft sheets: the networks barely see the streets, and two sheets stay near-empty after the fixes

- **kind:** failure-mode
- **plates:** 8 sheets: 46, 47, 48, 49, 50, 92, 94, 95. The review knew only 46-50.
- **evidence:** Medians, 400 ft against 200 ft: street share of the map 0.066 against 0.163; line share 0.008 against 0.020; corridor width found 18 against 40 half-size px; blocks after both fixes 8.5 against 29; 99% against 80% of block ground in regions over 20 acres. Plates 50 and 95 still give 1-2 blocks whose largest covers 96% of the map ground (potential/50.jpg shows the area network calling almost the whole sheet block).
- **impact:** The only route to usable output on a quarter of the PDF sheets.
- **fix:** Resample each region by s = ft_per_inch / 200 (2 for a 400-ft region) before both networks. Map P(block) and P(line) back. Scale outlines.py's pixel constants (SEED_B, SEED_S, MINLEN, SLIDE, CUT, MIN_AREA) by the same factor. The scale comes from scale_table.json, and the region from map_area's 'regions'.
- **effort:** medium

### pdf-5 [medium] Insets at another scale need their own resampling

- **kind:** failure-mode
- **plates:** 46 (200-ft inset), 48 (Sub Plats A, B, C at 200 ft), 92 ('Sub. Plan' at 200 ft), 94 ('Sub. Plat' at 200 ft), 78 (400-ft inset on a 200-ft sheet)
- **evidence:** In the 200-ft insets the networks see street 0.107-0.169 and line 0.011-0.025; in their 400-ft main maps 0.034-0.090 and 0.003-0.009. 78's 400-ft inset 0.083 against 0.112 for its main map. map_area separates each of these insets as its own region (48: A and B are joined to each other, but they share a scale).
- **impact:** With a single resample per sheet, these insets would be scaled to the wrong size.
- **fix:** Resample per region, not per sheet. Join the regions in maparea_check/N_map_area.json to scale_table.json, and give each region its own resample and its own constants.
- **effort:** small on top of pdf-4

### pdf-6 [high] Open land called block: huge regions bounded by property lines get exported as blocks with green sides

- **kind:** failure-mode
- **plates:** all; worst 21, 24, 32, 41, 72-74, 78, 81, 88, 91 and every 400-ft sheet
- **evidence:** After both fixes, a median 80% of the block ground on 200-ft sheets (99% on 400-ft) lies in regions over 20 acres. The largest are 70-470 acres on 200-ft sheets (73: 470 acres, Ault Park plus open land). On compare/30.jpg, green sides run along estate and property lines and a private road. Green only means 'on some ink'.
- **impact:** Most of the sides gained on the suburban PDF sheets are open-land sides that Ben would have to delete.
- **fix:** (a) Do not export, or mark 'open', blocks larger than about 20 acres. (b) Keep a side only if a parallel printed line runs at street width beside it (a street is two parallel lines; a property line is one). (c) Gate green on line-network support, as the review measured on 44 (78% → 85%). Ben's 44 leaves this ground undecided, so it cannot be scored there.
- **effort:** small to medium

### pdf-7 [medium] Water, canal and rail land are called block

- **kind:** failure-mode
- **plates:** 19, 20, 21, 22, 23 (Ohio River); 41, 42, 90 (Mill Creek, canal bed, Fair Grounds); 95 (Little Miami / Ohio); 41 (rail yards)
- **evidence:** Seen on the overlays only, not measured: potential/90_mapmask.jpg (Mill Creek and the race track inside one block), maparea_check/21_map_area.jpg (the river between the two panels is map ground and called block). Where the river reaches the margin, the mask takes it off-map. Where it lies between panels (21, 23), it stays map ground.
- **impact:** Large false blocks along every river sheet.
- **fix:** Treat ground that is uniformly blank or water-tinted over a large area as 'not block' before the watershed (blue shoreline tint, no lot lines inside). Leave the ground along tracks untaught, as the review suggests.
- **effort:** medium

### pdf-8 [low] Detector misses that remain

- **kind:** failure-mode
- **plates:** 23, 27, 46, 91
- **evidence:** 23: the lower panel joins the main map next to the compass rose, where the rule is thin. 27: St. Joseph Cemetery is off-map. 46: the main 400-ft scale bar is not boxed. 91: the diagonal rule does not split the sheet. Earlier versions also missed 72's title, the insets of 24, 48, 78 and 89, and a scale note on the paper's top edge; all of these are fixed in the delivered version and checked.
- **impact:** Small: 23 and 91 are one scale, 27 is open land, and 46's bar sits on the map edge.
- **fix:** Leave as is, or let Ben draw a map-area polygon once per sheet in the editor for these 4.
- **effort:** small

### pdf-9 [medium] Exported sides are still broken into short pieces

- **kind:** failure-mode
- **plates:** all, worst on the 400-ft sheets
- **evidence:** Seen on compare/30.jpg and compare/47.jpg, not counted: many sides come out as short dashes along a street. This is the review's 'no block closes' finding, still present after the fixes.
- **impact:** More editing per block for Ben.
- **fix:** Close rings from the sides (the review's step 3), and use one watershed marker per block (PQ 0.515 → 0.602 on 44 in the review).
- **effort:** medium

## measure: rail

I re-ran the batch's rail rules on plate 44 with Ben's tracks switched off and scored them against his complete tracks (all 28, including today's spur), then did the same on 1A against its 10 checked tracks. I also took a rail census of the whole batch with visual checks, and measured fixes. Scripts and outputs are in data/sanborn/bench_2026-11-21/rail/ (second copy of the scripts in scripts_copy/). Nothing in the repo was changed, no GPU was used and nothing was trained.

How the copies were checked (measured): my copies of ink_bins.py and rail_tracks.py give the same bins and tracks as the batch, pixel for pixel and track for track, on plates 3 and 5. On 44, the bins are identical to the earlier review's rules-alone file. The batch's ink_bins hash (de9b79144123) is the current file.

PLATE 44, the only complete plate (measured; in-sample, because the tick rules were tuned on 44):
- Railroad, run as the batch ran 44 (with the street map). Ben drew 21 tracks, 43,106 px.
  - Within 10 px: 98.4% of his length found, at 99.5% precision.
  - Within 30 px: 99.3%, at 99.7%.
  - Tracks: 19 found, 2 partial, 0 missed, 0 false tracks. The 2 partial ones are a double-line siding (73%) and a crossover (66%).
  - Broken tracks: 6 of his 21 are covered by 2 or more rule pieces in their middle.
  - The spur Ben drew today was found by the rules. With it counted as truth, precision rises from 98.8% to 99.5%.
- Railroad, run as the batch ran the other 104 plates (no street map, no label): precision falls to 97.9% (10 px) and 98.1% (30 px). Three false tracks appear (672 px, on lot lines and text). Recall does not change.
- Streetcar. Ben drew 7 tracks, 15,308 px.
  - Within 10 px: 79.8% found, at 100% precision. Within 30 px: 82.6%, at 100%.
  - Tracks: 4 found, 3 partial, 0 missed.
  - The rules give 13 pieces for his 7 tracks, with 7 gaps inside his tracks.
- The batch's own 44 file is not a benchmark: Ben's tracks are mixed in, and it holds 1 streetcar track that covers 16% of his streetcar.

PLATE 1A, partial truth (measured):
- Streetcar against the 10 checked tracks: 63.8% found within 10 px, 69.7% within 30 px. Precision is at least 99.9% (10 px) and 100% (30 px); it is only a lower bound because the plate is not complete. Tracks: 5 found, 4 partial, 1 missed.
- Railroad: Ben drew none. The rules give 5 tiny tracks (453 px), and by eye all 5 lie on label text.

THE BATCH (107 plates; 44 and 1A left out because Ben's tracks are mixed in):
- Rule railroad: 4,063 tracks, 3.36M px. 1,953 of them are under 300 px. Eight yard plates hold 39% of the length.
- Rule streetcar: 1,213 tracks, 945k px.
- Precision estimated by eye from random points, uniform by length (estimated):
  - railroad about 85% (41 of 48 points on real track; the misses are lot lines with hook marks and lines of text);
  - streetcar about 96% (46 of 48).
- Recall outside 44 and 1A is unknown.
- What goes wrong, and where:
  - Lot lines with hook marks are taken as railroad on unplaced plates.
  - The printed KEY's sample symbols are taken as rail on 36 plates.
  - Streetcar chains break where a street name is printed over the line.
  - Two kinds of rail drawn without ticks are not handled:
    - 83B: the railroad is drawn only as its right-of-way, so nothing is found;
    - 95 (a 400-ft plate): a double-line track on curves gives only streetcar fragments.
  - 54B, 64B and 82B really have no rail.

WHAT THE FIXES DO (measured on 44; batch effects measured, judged by eye):
- Drop a railroad track shorter than 600 px when no other railroad track is within 60 px:
  - On 44 run as an unplaced plate, precision returns to 99.5% with no recall loss.
  - On the batch it removes 240 tracks. By eye, 31 of 36 sampled were false.
- Mask the KEY before the rules: removes 37 tracks that are certainly false.
- Streetcar join distance 300 px (from 150): recall on 44 goes from 82.6% to 86.3% at 100% precision; on 1A from 69.7% to 73.6%.
- Streetcar join distance 400 px (looser): recall 87.9% on 44 and 86.9% on 1A.
  - The extra length it draws on 44 all lies in 5 gaps in Ben's own tracks under street names (1,820 px, 12% of his streetcar).
  - Against tracks bridged under those names, its precision on 44 is 100%.
  - Batch-wide it cuts streetcar pieces from 1,213 to 947. By eye, 29 of 32 sampled points on the length it adds are real.
- Two other fixes help on some plates and hurt on others:
  - The area network's block mask removes 48-69% of hook rail, but also about 1% of real yard track, and all of the real railroad on 400-ft plate 46.
  - A stricter tick angle costs 0.5 points of recall on 44.

IN-SAMPLE WARNING: 44 is the plate the rules were tuned on (43 too, by eye). The 600 px / 60 px filter and the 300-400 px streetcar settings were chosen after looking at 44's errors. Every 44 number is therefore a training-set number. 1A (streetcar only) and the visual samples are the only out-of-sample checks.

**Numbers**

MEASURED, plate 44, rules alone with the street map, against the 28 tracks in rail_ben.page_2026-11-21.json (score_rail_bench.py on runs/44_map_rail_rule.json; output scores/44_map.json):
- Railroad within 10 px: recall 98.4%, precision 99.5%, 228 px false.
- Railroad within 30 px: recall 99.3%, precision 99.7%.
- Railroad tracks within 10 px: found 19, partial 2, missed 0; false tracks 0; 6 of 21 split in their middle; gaps 0. Rule tracks: 19 (41,214 px).
- Streetcar within 10 px: recall 79.8%, precision 100%.
- Streetcar within 30 px: recall 82.6%, precision 100%.
- Streetcar tracks within 30 px: found 4, partial 3, missed 0; 4 of 7 split in their middle; 7 gaps. Rule tracks: 13 (11,941 px).
- Bin level as score_rail.py measures it: railroad 98.8% (1,193 px of railroad ink far from his tracks), streetcar 85.2% (1,086 px far).

MEASURED, plate 44, run as an unplaced plate (no street map, no label) (score_rail_bench.py; scores/44_nomap.json):
- Railroad within 10 px: recall 98.4%, precision 97.9%.
- Railroad within 30 px: recall 99.3%, precision 98.1%.
- Railroad: 3 false tracks (672 px); bin far 5,580 px.
- Streetcar within 30 px: recall 83.4%, precision 100%.

MEASURED, plate 44, other references (score_rail_bench.py):
- Against the old rail_ben.json (26 tracks, no spur): railroad precision within 10 px 98.8% (scores/44_map_oldtruth26.json).
- The batch's own 44 file (Ben's tracks mixed in): streetcar 1 track, recall 16.0% within 30 px (scores/44_batch_mixed.json).

MEASURED, plate 1A against the 10 checked streetcar tracks (score_rail_bench.py; scores/1A.json):
- Streetcar within 10 px: recall 63.8%, precision at least 99.9%.
- Streetcar within 30 px: recall 69.7%, precision at least 100%.
- Streetcar tracks: found 5, partial 4, missed 1.
- Streetcar bin recall 77.7%.
- Rule railroad: 5 tracks, 453 px, all on label text by eye (crops/1A_rr_ab.jpg).

MEASURED, gaps in Ben's own streetcar (truth_gaps.py):
- 44: 5 gaps, 1,820 px. All 5 lie under street-name lettering (checked by eye, crops/44_V4_gaps.jpg and exp/truth_gaps_44.jpg).
- 1A: 2 gaps, 757 px.

MEASURED, streetcar tracing changes (exp_streetcar.py, exp_proposed.py; recall and precision within 30 px):
- Join distance 300 px: 44 recall 86.3%, precision 100%. 1A recall 73.6%, precision at least 94.4%.
- Join distance 400 px, 25 px off the line, a lone piece of 250 px or more kept: 44 recall 87.9%, precision 95.7%. 1A recall 86.9%, precision at least 90.3%.
- Against 44 tracks bridged under the street names: batch 74.6% → 400 px setting 82.9%, at 100% precision (exp/score_bridged_*.json).
- Batch-wide, streetcar pieces 1,213 → 1,027 (300 px) or 947 (400 px setting) (exp_proposed.py --census).
- The 400 px setting adds 133,018 px; by eye 29 of 32 sampled points on it are real (exp_p2_added.py; exp/p2/added_sample.jpg).

MEASURED, railroad filters (exp_filters.py, exp_f1b.py):
- Short-and-alone filter (600 px, 60 px): 44 unplaced precision within 10 px 97.9% → 99.5%, recall unchanged.
- Batch: it drops 240 tracks (62,357 px) of 4,063. By eye 31 of 36 sampled drops were false (exp/lone_dropped_sample36.jpg).
- Stricter version where only a track of 600 px or more counts as a neighbour: 1A railroad 5 → 0. Batch drops 1,591 tracks (277,074 px); by eye about 21 of 24 sampled extra drops were false.

MEASURED, area-network block mask (exp_area_run.sh, exp_area_score.py; share of rule railroad length removed):
- 44 unplaced: precision 97.9% → 99.5%.
- Hook plates: 5 −48%, 11 −62%, 12 −58%, 14 −69%.
- Yard plates: 3 −1.0%, 1B −1.4% (mostly real track by eye).
- 400-ft plate 46: −100% (all real track).

MEASURED, stricter tick angle (exp_across_run.sh, compare_runs.py):
- Limit 0.55: 44 recall within 10 px 98.4% → 97.9%. Plate 5 −39%, 14 −37%, 12 −70%, yard 3 −0.8%.
- Limit 0.55 with the short-and-alone filter: plate 5 −51%, 14 −82%.

MEASURED, census (census_rail.py, key_find.py; 107 plates):
- Railroad: 4,063 tracks, 3,364,096 px; 1,953 tracks under 300 px.
- Streetcar: 1,213 tracks, 945,113 px.
- Eight yard plates (1B, 2, 3, 9, 23, 41, 52, 64A) hold 39.4% of railroad length.
- No railroad found on 10 plates: 8B, 54B, 55B, 56, 60B, 64B, 82B, 83B, 93A, 95.
- No rail of either kind on 4 plates: 54B, 64B, 82B, 83B.
- KEY found on 36 plates (all 32 PDF sheets plus cut plates 29, 34, 37, 76); 20 railroad and 17 streetcar rule tracks inside (9,990 px).
- 28 plates are mostly short railroad inside predicted block ground (hook suspects). That list wrongly includes the 400-ft plates.

ESTIMATED, visual samples uniform by length (sample_points.py, montage.py; sample/rr48.jpg, sample/sc48.jpg):
- Batch railroad precision about 85% (41 of 48 real). Only 2 of the 7 false points sat on tracks the stricter version of the filter removes.
- Batch streetcar precision about 96% (46 of 48).

**Files**

All in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/rail/ (second copy of every script in scripts_copy/). Run everything from data/sanborn.

Copies of the rail tools, all writes redirected (I checked both reproduce the batch on plates 3 and 5):
- ink_bins_copy.py: needs --save. Extra options: --json; --nomap (run as an unplaced plate); --area PNG [--area-thr --area-erode]; --key x0,y0,x1,y1; and the tick angle through --rail '{"across": A}'.
- rail_tracks_copy.py: N BINS.png OUT.json.

Main scorer:
- score_rail_bench.py N RULE.json TRUTH.json OUTPREFIX [--bins B.png] [--nopic].
- Gives railroad and streetcar recall and precision within 10 and 30 px, found/partial/missed, broken (also counted on each track's middle), gaps, false tracks, cross-kind and bin level.
- src:'rule' truth tracks are not scored.

Benchmark runs and scores:
- runs/44_map_*, runs/44_nomap_*, runs/1A_*: rules-alone bins and tracks.
- scores/44_map.json and .jpg, 44_nomap, 44_batch_mixed, 1A, 44_map_oldtruth26: the scores (.jpg: found green or blue, missed red or magenta, false orange or purple).
- missed_runs.py, false_runs.py: where the misses and false stretches are.
- truth_gaps.py: gaps in Ben's tracks.

Census:
- census_rail.py → census/census.csv and census.json (per plate), hook_candidates.json.
- key_find.py → census/key_boxes.json, census/key/*.jpg.
- Visual checks: census/hooks_14_5_11.jpg, census/key_check_montage.jpg; visual/*_overview.jpg and grids (5, 14, 3, 41, 46, 56, 95, 54A, 12, 1B, 59A, 54B, 64B, 82B, 83B, 60B, 93A); visual/83B_diag.jpg, 64B_diag.jpg, grid_400ft.jpg.
- sample/rr48.jpg and sc48.jpg: random length samples (sample_points.py, montage.py).
- crops/: full-size crops of misses on 44 and 1A.

Experiments:
- rail_variants.py: the proposed functions (streetcar_tracks_v2, drop_lone_short, drop_in_box).
- exp_streetcar.py → exp/streetcar_variants.json.
- exp_filters.py → exp/filters_*.json, lone_dropped_sample36.jpg.
- exp_f1b.py → exp/f1b_extra_sample24.jpg.
- exp_area_run.sh, exp_area_run2.sh, exp_area_score.py → exp/area/ (yards_area_dropped.jpg).
- exp_across_run.sh, compare_runs.py → exp/across/.
- exp_proposed.py → exp/proposed/ (scores for 44 and 1A, census_proposed.json).
- exp_p2_added.py → exp/p2/added_sample.jpg.
- exp/44_truth_bridged.json: a scratch truth copy with the 5 gaps under street names bridged (not Ben's file).

### R1 [high] Lot lines with hook marks are read as railroad on unplaced plates

- **kind:** failure-mode
- **plates:** 28 plates are mostly short railroad inside block ground. Worst: 5, 11, 12, 14, 8A, 17, 15A, 18A, 18B, 38, 54A, 71. Hooks are also mixed into 59A, 1B and others.
- **evidence:** Measured:
- On 44 run without a street map (how the batch ran 104 plates), 3 false tracks of 672 px appear, and railroad precision within 10 px falls from 99.5% to 97.9%.
- The ink_bins.py rule that a row inside a block needs 6 ticks has no blocks to work with on unplaced plates (no label, closed mask empty).

By eye:
- 21 of 21 short, alone, in-block tracks on 5, 11 and 14 are hooked lot lines (census/hooks_14_5_11.jpg).
- Plate 5 (downtown) shows no real railroad among its 54 rule tracks (visual/5_overview.jpg).
- 7 of 48 points sampled along batch railroad length are false, all hooked lot lines or text (sample/rr48.jpg).
- **impact:** The largest source of false railroad by track count. Ben's editor shows hundreds of short false tracks: 1,953 of 4,063 rule railroad tracks are under 300 px.
- **fix:** Measured on 44 and on census plates:
- (a) After rail_tracks.py, drop a railroad track shorter than 600 px when no other railroad track is within 60 px (rail_variants.drop_lone_short).
  - 44 unplaced: precision back to 99.5%, recall unchanged.
  - Batch: 240 tracks (62k px) removed, 31 of 36 sampled drops false.
- (b) Stricter version: only a track of 600 px or more counts as a neighbour.
  - Removes 1,591 tracks (277k px); about 21 of 24 sampled extra drops false.
  - Clears 1A's 5 false text tracks.
- (c) Optional: tick stroke ends must lie more squarely across the line (|cos| at most 0.55, not 0.7).
  - With (a), removes 51-82% of rule railroad on hook plates 5 and 14.
  - Costs 0.5 points of recall within 10 px on 44 and about 1% of yard track on plate 3.
- Do NOT use the area network's block mask by itself:
  - On 44 it gives the same precision, but it removed all of the real railroad on 400-ft plate 46 and 1.0-1.4% of real yard track on 3 and 1B.
  - Use it, if at all, only on 100/200-ft plates.
- **effort:** small (a, b), medium (c)

### R2 [medium] The printed KEY's RAILROAD and TROLLEY samples are found as rail, on cut plates too

- **kind:** failure-mode
- **plates:** 36: all 32 PDF sheets, plus cut plates 29, 34, 37 and 76. 1B also has a partial KEY at its cut edge that template matching misses.
- **evidence:** Measured:
- key_find.py matches the KEY of plate 86 at 1/8 size. Scores are 0.51-1.0 on 36 plates; I checked 6 by eye (census/key_check_montage.jpg).
- Inside the boxes: 20 railroad tracks (about 300 px each) and 17 streetcar tracks (200-330 px), 9,990 px in all.
- The bins hold 54,957 px of railroad and 58,545 px of streetcar inside the KEYs.
- **impact:** 37 certainly false tracks in the editor. A rail network would be taught that real rail symbols are not rail.
- **fix:** Find the KEY by template (census/key_boxes.json already lists the boxes) and clear its ink before the rules run. ink_bins_copy.py --key x0,y0,x1,y1 does this. This removes 37 tracks that are certainly false; on 44 it has no effect. Store the box as an ignore region for any rail network. Also, the sheet titles print the scale ('SCALE 200 FT. TO AN INCH', '400 FT'), which fills the review's scale table for uncut sheets.
- **effort:** small

### R3 [medium] Streetcar chains break where street names are printed over the line, and where heavy dashes are sparse

- **kind:** failure-mode
- **plates:** every streetcar plate (102 have streetcar). Measured on 44 and 1A.
- **evidence:** Measured:
- rail_tracks.streetcar_tracks joins dashes only within 150 px. On 44 that gives 13 rule pieces for 7 tracks, with 7 gaps; streetcar recall is 82.6% within 30 px, against 85.2% for the bin itself.
- Misses checked by eye (crops/44_sc_*.jpg):
  - dashes broken by 'AVE.' and 'HAMILTON';
  - Ludlow Ave's sparse heavy dashes, about 330 px apart;
  - a Hamilton curve;
  - dashes run into lettering, which the bin misses.
- **impact:** +4 to +5 points of streetcar recall on 44 (+17 on 1A with the 400 px setting). About 22% fewer streetcar pieces for Ben to join.
- **fix:** Measured:
- (a) Join distance 300 px:
  - 44: 82.6% → 86.3% at 100% precision.
  - 1A: 69.7% → 73.6%, at a lower-bound precision of 94.4%; the false length lies between 1A's unchecked rule tracks.
- (b) Join distance 400 px, 25 px off the line, a lone piece of 250 px or more kept, curved pieces traced:
  - 44: 87.9%. 1A: 86.9%.
  - Batch-wide pieces fall from 1,213 to 947, and by eye 29 of 32 sampled points on the added length are real.
- The 'lone piece' and 'curved piece' parts changed nothing on 44 or 1A. The gain comes from the longer join.
- Not yet done: a bar test that copes with dashes run into lettering, for the bin's 15% loss.
- **effort:** small

### R4 [medium] Ben's own streetcar tracks stop under street names: 12% of 44's streetcar, so scores and targets depend on a convention

- **kind:** measurement
- **plates:** 44 (5 gaps, 1,820 px), 1A (2 gaps, 757 px)
- **evidence:** Measured:
- truth_gaps.py finds 5 pairs of streetcar track ends on 44 that face each other along one line, 211-591 px apart.
- By eye, all 5 sit under HAMILTON, AVE., AVENUE and SPRING-GROVE (exp/truth_gaps_44.jpg, crops/44_V4_gaps.jpg).
- Every 'false' metre of the 400 px streetcar setting on 44 lies in these gaps. Against bridged tracks (exp/44_truth_bridged.json, a scratch copy) its precision is 100%.
- **impact:** Changes the streetcar benchmark by up to 8 points, and decides whether a network learns continuous lines.
- **fix:** Ask Ben whether a track should run on under a street name. If yes, draw it through, or bridge it automatically in the scorer and the training targets. If no, keep his tracks as they are, but mark the lettering as 'not scored' when training a network.
- **effort:** small

### R5 [medium] The batch's rail files on 44 and 1A are not rules output (earlier finding rail-4, confirmed)

- **kind:** bug
- **plates:** 44, 1A
- **evidence:** Measured:
- unet_data/44_rail_rule.json has 1 streetcar track (recall 16.0% within 30 px), against 13 pieces and 82.6% from the rules alone.
- 1A's file has 0 streetcar tracks; the rules alone give 13.
- run_plates.json streetcar_px for 44 is 159,342 against 104,337 from the rules alone; for 1A, 105,825 against 66,948.
- **impact:** Anyone benchmarking from unet_data on the only two checked plates would get circular or nonsense numbers.
- **fix:** Have run_plates.py also write a rules-only N_bins_rule.png and N_rail_rule_only.json, made with --no-ben. Use only those for benchmarks and pseudo-labels.
- **effort:** small

### R6 [low] Railroad tracks come out in several pieces at switches and crossovers; double-line sidings are missed

- **kind:** failure-mode
- **plates:** 44 measured; all yards (59A, 37, 26A, 29: 50-65% of their rule tracks under 300 px)
- **evidence:** Measured on 44:
- 6 of 21 Ben railroad tracks are covered by 2 or more rule pieces in their middle (100 px in from each end).
- 334 px of the American Can Co. double-line siding is missed (Ben track 13, 73% covered).
- A crossover is 66% covered.

Census: 1,953 of 4,063 batch railroad tracks are under 300 px.
- **impact:** Editing effort in yards, not accuracy. Recall within 30 px is already 99.3% on 44.
- **fix:** Not measured. Join railroad pieces whose ends are within about 30 px and run straight on (the switch-join test with a wider radius). Treat a ticked double line as one track.
- **effort:** medium

### R7 [medium] Rail drawn without ticks or heavy dashes is not covered: right-of-way-only railroads and double-line tracks

- **kind:** failure-mode
- **plates:** 83B (P.C.C.&St.L. R.R. Richmond Div. drawn as a right-of-way strip), 95 (400 ft, a double line of heavy plus thin lines on curves and a loop). Probably other outer and 400-ft plates.
- **evidence:** By eye:
- 83B: 0 rail found, but a labelled railroad crosses the plate as two thin boundary lines (visual/83B_diag.jpg).
- 95: 0 railroad found; 5 streetcar fragments (1,947 px) lie on a long double-line track (visual/grid_400ft.jpg).
- 54B, 64B and 82B do have no rail (visual/grid_small.jpg, visual/82B_all.jpg).
- 400-ft plate 46: the ticked railroads are found well (visual/grid_400ft.jpg).
- **impact:** Unknown length. Every railroad on outer plates drawn this way is invisible to the rules.
- **fix:** Ask Ben how these should be recorded: as railroad, as streetcar or interurban, or as a third kind. They need either a rule for parallel thin or heavy lines with a railroad label, or network training examples.
- **effort:** medium

### R8 [high] In-sample tuning: every 44 number is a training-set number

- **kind:** measurement
- **plates:** 44 (complete), 1A (streetcar only, begun)
- **evidence:** Measured and documented:
- The ink_bins.py docstring (lines 99-108) and CAR comment (50-52) tuned the rules against 44; 43 was tuned by eye.
- The proposed 600 px / 60 px filter and the 300-400 px streetcar settings were chosen after looking at 44's errors.
- Out-of-sample evidence comes only from 1A's streetcar (recall 69.7% within 30 px) and the visual samples (railroad about 85%, streetcar about 96% precision).
- **impact:** The 98-99% railroad figures should not be quoted as batch quality. The batch-wide railroad precision is nearer 85% (estimated).
- **fix:** Ben should complete more plates before the rules are tuned further, and always hold out 2 whole plates. Report rules and network on the same held-out plates with score_rail_bench.py.
- **effort:** n/a

### R9 [low] The 'share in block' outlier flag misfires on 400-ft plates

- **kind:** measurement
- **plates:** 46, 47, 48, 49, 50, 94
- **evidence:** Measured: on 400-ft sheets the area network calls open land block, so real railroad (46: Cincinnati & Westwood R.R., C. & O. R.R. of Ind.) scores 76-80% 'in block'. A 'hook suspect' flag based on it, or an area-mask filter, would delete real track: the mask removed 100% on 46.
- **impact:** Prevents a fix for R1 from deleting real railroad on outer plates.
- **fix:** Gate any filter based on the area network by plate scale. Record the scale per plate (it is printed on the PDF sheets).
- **effort:** small

### R10 [medium] Proposal: a rail network built from edgenet.py

- **kind:** proposal
- **plates:** Currently complete: 44 only. Suggested for Ben to complete: 1A, 5, 14, 3, 20, 46 (95 or 83B for the untick-marked kinds).
- **evidence:** Measured on 44: 55 of 323 paper tiles of 448 px hold railroad and 43 hold streetcar. The census shows four kinds of plate that 44 does not cover:
- 100-ft downtown with hooks (5, 1A);
- 200-ft residential with hooks (14, 12);
- yards (3, 1B, 41);
- 400-ft and PDF sheets with a KEY (46, 95, 20).

The rules are already near 99% right on yards, so a yard is quick to check. Hook plates give the hard negatives a network most needs (R1).
- **impact:** The only way past the ceiling of hand-written rules on hooks, lettering and untick-marked rail. Untestable until more plates are complete.
- **fix:** Inputs:
- RGB plus edgenet.ink_image, 4 channels, at full size (ticks are 13-24 px, railroad lines 2-3 px).
- No guide. Leave out P(block), or blank it half the time: it is in-sample on training plates and wrong on 400-ft plates.
- Crops of 448 px are enough: the streetcar gaps under lettering are 211-591 px.

Outputs and loss:
- Two sigmoid channels (railroad, streetcar), each with its own mask.
- edgenet.predict_full (softmax channel 1) must be rewritten for sigmoid outputs.
- Loss: masked BCE plus Dice per channel.

Targets:
- Ben's checked polylines: railroad 5 px wide, streetcar 13 px.
- Run continuously under lettering if Ben agrees (R4); otherwise make the lettering 'not scored'.
- Positives drawn last.
- Not scored:
  - ±12 px around railroad and ±15 px around streetcar;
  - off the paper;
  - KEY boxes (census/key_boxes.json);
  - src:'rule' tracks;
  - on begun plates, everything not drawn.

Negatives:
- On complete plates only: all other ink, weighted ×4 as NEG_INK.
- Extra hard-negative crops on hooked lot lines, street-name lettering and dimension lines (240 census drops, 21 confirmed hooks), and on 'rejected' tracks once the editor records them (earlier finding rail-3).

Plates:
- At least 6 more complete plates (7 in all), with 2 held out whole:
  - finish 1A;
  - 5 (100 ft, 53 streetcar rule tracks, 54 railroad rule tracks that by eye are all hooks);
  - 14 (200 ft, 28 streetcar, 24 hook 'railroad');
  - 3 (yard, 179 railroad);
  - 20 (PDF sheet with KEY, 8 railroad, 9 streetcar, cheap);
  - 46 (400 ft).
- Hold out 14 and 46.
- Add 95 or 83B once Ben decides how untick-marked rail is recorded.

Starting from the rules' output:
- Pretraining on rules-only bins (never mixed ones) is possible from yard plates.
- It must include negatives, or it collapses to 'rail everywhere'.

Scoring: score_rail_bench.py, which does both tolerances, track level and gaps.
- **effort:** medium (code), large (Ben's checking)

## experiment: outline-nesting

I wrote a proposed version of tools/sanborn/unet/outlines.py (and a small change to blocks_noguide.py) and measured it on all 109 plates of today's batch. It uses the batch's own saved network maps, ran on the CPU in the networks' venv, and trains nothing. It is saved as a unified diff and NOT applied: both repo files still have their original SHA-256, and nothing under tools/, unet_data, picks22_guided, streetmap or cufp has changed since the session started.

What the change does:
1. Nested blocks and street holes. RETR_TREE replaces RETR_EXTERNAL. Every block region is now a block, including one that sits inside another region's hole. Each hole of at least MIN_AREA gives its street sides as a polygon whose sides carry hole=True.
   - Hole polygons are listed first, then blocks outermost first. A reader that fills polygons in order (bench44 does) paints each block over its holes, as before.
   - Hole gate: a hole inside a region more than 3 times the plate's median block is skipped (constant HOLE_PARENT = 3.0). On 44 those holes are pockets of unsure ground by Mill Creek, the canal, the railway and big parcels, not streets.
2. Map ground on the 32 uncut PDF sheets. visual-pdf's map_area.py replaces the paper mask. The margin, KEY, title, scale notes and bars, compass roses and inset frames are seeded as street, and sides along them become paper_edge, which step 4 drops.
3. QA flag 'suspect', with the census thresholds:
   - Q1: the editor keeps less than 60% of the line network's thinned line length;
   - Q2: 2 or more block regions are nested inside another;
   - Q3: the scale is not 100 or 200 ft, or not recorded (census scale table);
   - Q5: a PDF sheet whose map ground could not be found.
   It goes into N_outlines.json, N_blocks_ng.json and the last printed line, which run_plates.json stores as 'blocks'.

Checks, all measured:
- The --legacy switch of my bench copy reproduces the batch byte for byte on all 104 unplaced plates (outlines.json identical, block mask identical) and passes bench44's --faith check under both Pythons.
- The measured code (outlines_bench_final.py) is generated mechanically from outlines_proposed.py by make_bench_copy.py; `diff` shows only input and output lines.
- The diff applies cleanly with `patch -p1` to copies of the repo files and reproduces both proposed files.
- Live map_area.py and the cached masks give identical outlines on sheets 30 and 90.

Plate 44 (bench44 harness, measured): it does not get worse on any headline except Ben's delete length, which rises by 124 px.
- PQ stays 0.431: 44 has no nested regions, and holes do not change the block raster.
- Recall of Ben's interior lines 0.532 to 0.547; precision 0.748 to 0.752; green precision 0.775 to 0.779.
- Draw length 80.1k to 77.4k px; delete length 32,545 to 32,669 px.
- Both folds gain: fold A recall 0.550 to 0.563 and precision 0.731 to 0.736; fold B 0.510 to 0.527 and 0.769 to 0.773.
- On decided ground: recall 0.582 to 0.600, precision 0.886 to 0.888.
- It is better at every tolerance from 3 to 8 px.
- The gains are small (below the 3-point bar for PQ), but they appear on both folds.

PDF sheets, 24 at 200 ft (measured, measure.py and summarize.py):
- blocks 425 to 815; exported sides 6,841 to 10,421; editor lines 6,278 to 9,549;
- sheets with 5 or fewer blocks 11 to 0;
- sheets whose largest block covers more than half the map ground 21 to 7;
- lines within 150 px of the paper edge 365 to 77;
- suspect 13 to 2.
- Most of the PDF gain comes from the map mask: the mask alone gives 806 blocks. Nesting adds nested blocks where a block ring remains inside the map (41, 47, 74, 94).

400-ft sheets and the census's suspect cut plates:
- The 8 PDF sheets at 400 ft improve (blocks 20 to 70, editor lines 501 to 1,396) but still fail; they stay flagged by Q3.
- The census's suspect cut plates 8B, 15B, 93A and 93B, and 55B, are essentially unchanged (exported sides 223 to 227), because their failure is in the networks.

Hole sides judged by eye (estimates):
- On PDF sheets the gate drops about 90% of hole-side length, and by eye about 75% of hole sides there are real streets (36 yes, 7 no, 5 unsure of 48 sampled).
- On other cut plates the gated hole sides add 946 lines (+2.8%), about half right by eye (13 of 24 sampled; the wrong ones are mostly lot lines).

QA flag: 25 suspect plates before, 14 after. 11 sheets are cleared (22 23 27 30 72 73 78 81 88 90 91) and none is newly flagged.

Sheets where the fix still fails (checked by eye on before/after overlays):
- All 8 400-ft sheets (46 47 48 49 50 92 94 95): one block covers 48-99% of the map ground, because the area network misses streets at 400 ft.
- 200-ft sheets with one block over half the map ground:
  - 21: Ohio River and open land;
  - 32: open land merged with a district;
  - 41: rail yards called block (flagged Q2);
  - 72: rail and open land;
  - 73 and 74: suburban roads that end in open land, so they never separate blocks (74 flagged Q2);
  - 78: open land.
- Merged districts covering 30-50% of the map ground: 22, 24, 81, 88.
- map_area misses: 23 (two panels joined), 27 (cemetery), 46 (scale bar) and 91 (diagonal rule).
- Cut plates 8B, 15B, 55B, 93A and 93B: the area network merges blocks, and 93A and 93B are 400-ft plates.

One slip: my first faith run wrote a run folder into bench44/runs/ (the harness writes next to itself). I moved it into my folder at once, then deleted it after rerunning with a harness copy that lives in my folder. Nothing else was written outside my folder; a temporary file copy made in the system temp folder (/tmp) was deleted.

**Baseline:** Plate 44, the batch chain (area_ng1 + lines_ng1, the batch's outline step plus step 4 plus the editor's clean()):
- PQ 0.4309 (SQ 0.8524, RQ 0.5055): 23 matched, 13 false, 13 merges; PQ on decided ground 0.4545.
- Recall of Ben's interior lines 0.5316; precision 0.7475; green 0.7753; orange 0.0704.
- On decided ground: recall 0.5815, precision 0.8855.
- Fold A: PQ 0.4737, recall 0.5498, precision 0.7312. Fold B: PQ 0.3852, recall 0.5101, precision 0.7691.
- Ben's blocks closed 0; intact rings 0; delete 32,545 px; draw 80,094 px.
- Source: bench44/runs/batch/bench44.json (bench44.py). My --legacy run reproduces every number (outline-nesting/runs/batch_legacy/bench44.json, run with bench44_copy.py, an unchanged copy of the harness).

All other plates: the batch's own files, picks22_guided/22-N/outlines.json and unet_data/N_edges.json, read by measure.py ('batch' columns of measure.json and measure.csv). Exceptions:
- For the five placed plates, 'batch' is my --legacy run. It is byte-identical in method: the legacy switch reproduced all 104 unplaced plates byte for byte (outlines.json and N_blockmask.png).
- The 'before' QA flag and editor_per_line come from census/census.json (classify.py, census_finish.py).

Before totals (measured, summarize.py):
- 24 PDF sheets at 200 ft: 425 blocks, 6,841 exported sides, 6,278 editor lines; 11 sheets with 5 or fewer blocks; 21 sheets whose largest polygon exceeds half the map ground (it is the margin ring); 365 lines within 150 px of the paper edge; 13 suspect.
- 8 PDF sheets at 400 ft: 20 blocks, 549 exported sides, 501 editor lines; all 8 suspect.
- 5 weak cut plates (8B 15B 93A 93B 55B): 14 blocks, 223 exported sides.
- 72 other cut plates: 2,471 blocks, 33,474 exported sides, 30,216 editor lines.

### variant legacy (check, not a proposal)

- what: outlines_nest.py --legacy: RETR_EXTERNAL and the paper mask only, i.e. the old outlines.py with its outputs redirected. The QA flag is still computed. It is a faithfulness check of my copy.
- plate 44: Identical to the batch baseline on every headline number:
- PQ 0.4309; recall 0.5316; precision 0.7475; delete 32,545 px; draw 80,094 px.
- bench44_copy.py, runs/batch_legacy/bench44.json.
- --faith on the guided maps is byte-identical (SHA 5d8dcda4294d85d0) under the venv (cv2 5.0) and the system Python (cv2 4.13): runs/_faith_legacy_venv and runs/_faith_legacy_sys.
- other plates: outlines.json byte-identical to the batch on 104 of 104 unplaced plates, and N_blockmask.png identical on 104 of 104 (run_variants.py legacy, then an inline check).
- time: 44: 18.4 s for the outline step (venv; runs_timing/timing.json). PDF sheet 90: 9.2 s.

### variant mask_only

- what: map_area.py's map ground replaces the paper on the 32 PDF sheets; RETR_EXTERNAL is kept (--no-nest).
- plate 44: Unchanged from the batch (44 is a cut plate, so the code path is identical to legacy).
- other plates: Measured (summarize.py):
- 24 PDF sheets at 200 ft: blocks 425 to 806; exported sides 6,841 to 10,357; editor lines 6,278 to 9,490; sheets with 5 or fewer blocks 11 to 0; largest block over half the map ground 21 to 7; edge lines 365 to 77; suspect 13 to 2.
- 8 sheets at 400 ft: blocks 20 to 58; exported sides 549 to 1,116; editor_per_line median 0.155 to 0.364.
- This is most of the PDF gain.
- time: Not timed separately. map_area.py itself takes 5-13 s per sheet (visual-pdf).

### variant nest_only

- what: RETR_TREE: nested blocks plus hole sides with no hole gate and no map mask.
- plate 44: Same as 'new' below, because 44 is not a PDF sheet:
- PQ 0.4309; recall 0.5471; precision 0.7357.
- bench44_copy.py, runs/nest.
- other plates: PDF sheets at 200 ft: blocks 425 to 549; exported sides to 13,082. But the margin ring stays: 21 sheets still have a 'block' bigger than the map ground; edge lines 388; 13 suspect.
- Not useful alone on PDF sheets.
- (summarize.py)
- time: -

### variant new (nest + mask + QA, no hole gate)

- what: RETR_TREE (nested blocks and every hole of at least MIN_AREA), the map mask on PDF sheets, and the QA flag.
- plate 44: Measured with bench44_copy.py, runs/nest:
- PQ 0.4309 (unchanged).
- Recall 0.5316 to 0.5471; precision 0.7475 to 0.7357 (WORSE by 1.2 points); green 0.7753 to 0.7625.
- Delete 32,545 to 35,692 px; draw 80,094 to 77,429 px.
- On decided ground: recall 0.5815 to 0.6000, precision 0.8855 to 0.8884.
- Fold A precision 0.7312 to 0.7101; fold B 0.7691 to 0.7703.
- 17 holes. The 7 on decided ground (Pope, Kendall, Apple St and other alleys) lie 96-100% on Ben's lines; the other 10 lie 0% on his lines: Mill Creek banks, a sewer line, lot lines and the railway. Of 6.1k px of hole sides, 48.2% lie on Ben's lines (holes44.py, view_holes44.py).
- other plates: Measured, summarize.py:
- 24 PDF sheets at 200 ft: blocks 815; exported sides 11,908; editor lines 10,947.
- 8 sheets at 400 ft: blocks 70; exported sides 2,557.
- 72 other cut plates: exported sides 33,474 to 37,010 (1,121 holes).
- By eye on a random sample of 48 PDF hole sides, uniform by length (sample_holes.py, sample_holes/verdicts.json): 36 real street sides, 7 wrong (rail, creek, a lot line), 5 unsure. That estimates about 75% right; the sample is small.
- time: As final.

### variant final = PROPOSED (nest + mask + hole gate 3x median + QA)

- what: As 'new', but a hole inside a block region more than 3 times the plate's median block area is skipped (HOLE_PARENT = 3.0; counted as holes_in_open_land). The code measured is outlines_bench_final.py, generated from outlines_proposed.py by make_bench_copy.py (only input and output lines differ).
- plate 44: Measured (bench44_copy.py --outlines outlines_bench_final.py, runs/final; byte-identical to runs/nest_gate3):
- Blocks: PQ 0.4309, SQ 0.8524, RQ 0.5055; 23 matched, 13 false, 13 merges; PQ on decided ground 0.4545 (all unchanged).
- Lines: recall 0.5465 (+1.5 points); precision 0.7518 (+0.4); green 0.7791; orange 0.0704.
- On decided ground: recall 0.6000, precision 0.8884.
- Fold A: recall 0.5628, precision 0.7356. Fold B: recall 0.5273, precision 0.7730. Both folds gain on both numbers.
- Recall/precision by tolerance: 3 px 0.5218/0.7236; 4 px 0.5388/0.7441; 6 px 0.5517/0.7562; 8 px 0.5587/0.7604. All are above the batch.
- Workload: delete 32,669 px (+124 px, one pocket hole by the railway in a region 2.5 times the median block); draw 77,429 px (-2,665 px).
- Closure 0 of 55 and intact rings 0, unchanged.
- Holes: 7 kept, 13 skipped as open land. The skipped holes held 3.1k px of exported side, 0.1k px of it on Ben's lines (Wilson St).
- QA: not suspect (editor_per_line 0.754, nested 0, 100 ft).
- other plates: Measured (run_variants.py final, measure.py, summarize.py).
24 PDF sheets at 200 ft:
- blocks 425 to 815; exported sides 6,841 to 10,421; editor lines 6,278 to 9,549;
- median green share 0.942 to 0.975;
- median largest block 1.19 to 0.30 of the map ground;
- sheets with 5 or fewer blocks 11 to 0; largest block over half the map ground 21 to 7;
- edge lines 365 to 77; suspect 13 to 2 (41 and 74, both Q2).
Examples, batch to final (blocks / editor lines):
- 30: 1 / 9 to 34 / 398; 90: 1 / 3 to 45 / 455; 27: 1 / 5 to 42 / 284;
- 22: 1 / 1 to 10 / 218; 81: 1 / 9 to 17 / 295; 88: 1 / 14 to 16 / 278.
8 PDF sheets at 400 ft:
- blocks 20 to 70; editor lines 501 to 1,396; 5 or fewer blocks 7 to 2 (50, 95);
- largest block over half the map ground 8 to 7; all 8 still suspect.
Cut plates:
- 8B, 15B, 93A, 93B, 55B: exported sides 223 to 227 (not helped).
- 72 other cut plates (44 and the training plates included): blocks 2,471 to 2,476 (nested blocks on 2, 17, 37, 56, 75); exported sides 33,474 to 34,420 (+946 lines from 348 holes; 61 plates changed).
- By eye, 24 sampled gated hole sides on cut plates other than 44 (sample_holes_cut/verdicts.json): 13 real alleys or streets, 10 lot lines or a sewer, 1 unsure, an estimated 54%. Plate 7's mid-block alleys are a clear good case.
On PDF sheets the gate keeps only 49.7k of 523.7k px of hole side (sample_holes.py; by eye about 75% of those were streets).
QA flag: 25 to 14 suspect plates (8B 15B 41 46 47 48 49 50 74 92 93A 93B 94 95). Cleared: 22 23 27 30 72 73 78 81 88 90 91. Newly flagged: none.
Eye check of every PDF sheet's overlay: thumbs/N_final.jpg and N_new_gate.jpg, and the montages thumbs/pdf_after_0-7.jpg.
- time: Measured, runs_timing/timing.json, venv, one after the other:
- 44: 18.4 s to 18.9 s.
- PDF sheet 90 with live map_area: 9.2 s to 29.5 s.
- All 109 plates, 3 in parallel with cached masks: median 22.4 s, max 44.6 s (runs_plates/final/summary.json).

**Recommended:** Adopt 'final' (outline-nesting.diff). On plate 44 the measured gain over the batch is +1.5 points of recall (0.532 to 0.547), +0.4 points of precision (0.748 to 0.752) and -2.7k px of lines Ben must draw. PQ stays 0.431, and the gain shows on both folds and at every tolerance. The only worse number is +124 px of delete length.

The big gain is on the uncut PDF sheets (measured counts, no truth there):
- 200-ft sheets: 425 to 815 blocks and 6,278 to 9,549 editor lines; no sheet left with 5 or fewer blocks (11 before); margin lines 365 to 77.
- 14 of the 15 near-empty sheets of the batch now give 10-45 blocks each. 95 still gives 2.

Before applying:
1. Put map_area.py and its templates/ folder into tools/sanborn/unet/. Otherwise the diff imports it from bench_2026-11-21/visual-pdf, and Python may leave a __pycache__ there.
2. Copy census/scale/scale_table.json to data/sanborn/scale_table.json for Q3. The diff falls back to the census copy.
3. Rerun bench44's --faith afterwards. It will no longer be byte-identical, because 44 now gets hole polygons; --legacy is the faith check.

Open choice for Ben: HOLE_PARENT. With the gate off (HOLE_PARENT = 0), the PDF sheets keep about 1,500 more street sides, about 75% right by eye on 48 samples (an estimate). But 44's precision drops 1.2 points, because pockets by Mill Creek and the railway get exported. Decide this once a PDF sheet has truth (census C7).

Next steps this work points to, in order:
1. Resample the 400-ft sheets by 2 before both networks (census C2/C3). Those 8 sheets are still one block.
2. Check one 200-ft PDF sheet into the truth (90 or 30 look quick). That would decide the hole gate and give a PDF benchmark.
3. Keep rail-bin and water ground out of block lines (visual-cut VC-3/VC-4). These are the same wrong sides that hole pockets produce.
4. Add a PDF-only Q6 flag, 'largest block over 50% of the map ground'. In-sample it would also catch 21, 32, 72, 73 and 78; it is untested and not in the diff.

**Regressions:** Measured:
- 44: Ben's delete length +124 px (32,545 to 32,669). One pocket hole by the railway in a region 2.5 times the median block, below the gate's 3 times.
- Other cut plates: +946 exported lines from holes (+2.8% across 72 plates). By eye about half are lot lines inside blocks (13 of 24 sampled were real alleys or streets; an estimate from a small sample). So Ben would delete about 6 lines and gain about 6 alley sides per plate. Hole perimeter under about 700 px catches most lot-line pockets, but also 4 of 7 good alley holes on 44, so it was not adopted.
- PDF sheets: the hole gate drops about 90% of the hole-side length the ungated version gives (49.7k of 523.7k px kept). By eye most of it is real streets inside merged districts (sheets 30, 24, 41, 72, 73, 88). That is recall left on the table; it is not worse than the batch.
- Exported side counts fall on a few healthy sheets (36: 441 to 407, 79: 887 to 832, 20: 563 to 550) because margin sides are now dropped. Edge lines on 79 fall 57 to 5, and blocks rise on all three. This is intended.

Could go wrong (not measured):
- Format. Hole polygons are new entries in outlines.json. Readers that use sides (blocks_noguide step 4, make_labels.py, crop.py) or fill polygons in list order (bench44) are fine. A future reader that fills each polygon on its own would paint holes as blocks unless it checks hole=True. 'blocks' now counts only block polygons.
- map_area.py is a bench file. If it is not found on a PDF sheet, the code falls back to the old paper mask and flags Q5. Known detector misses: 23 (two panels joined), 27 (cemetery marked off-map), 46 (main scale bar not boxed), 91 (diagonal rule not split).
- Plate 24 now includes its boxed inset, because map_area.py's own paper is used instead of the faulty png_alpha_s4. The editor's sheet() still draws png_alpha_s4's outline.
- The QA flag clears 11 sheets that are only partly fixed: 72, 73 and 78 still have one block over half the map ground, and 22 over a third. It misses 21, 32, 72, 73, 78 and 55B. The thresholds are the census's, chosen in-sample.
- Q1 needs cv2.ximgproc.thinning. The networks' venv has it; cv2 4.13 in the system Python does not, and there Q1 is reported as not computed.
- The outline step on PDF sheets takes 15-20 s longer (live map_area plus more contours).
- No truth exists on any PDF or cut plate but 44. Every 'better' outside 44 is a count or an eye judgement.

**Diff:** C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/outline-nesting/outline-nesting.diff (157 lines; covers tools/sanborn/unet/outlines.py and tools/sanborn/unet/blocks_noguide.py; tested with `patch -p1` on copies of the repo files in the scratchpad; NOT applied)

**Files:** All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/outline-nesting/ (about 1.4 GB, mostly runs_plates/*/N_outlines.jpg; the folders for the variants other than 'final' can be deleted if space matters). Second copy of every script: _second_copy_scripts/.

The proposal:
- outline-nesting.diff
- outlines_proposed.py: the proposed outlines.py.
- blocks_noguide_proposed.py
- outlines_bench_final.py: the proposed code with input and output redirected, made by make_bench_copy.py.

Bench tools:
- outlines_nest.py: bench copy with switches --legacy, --no-nest, --no-mask, --mask-cache and the environment variable OUTLINES_HOLE_GATE.
- bench44_copy.py: unchanged copy of bench44.py, so runs land in this folder; cache/decided_half.png and outlines_copy.py are copied with it.
- run_variants.py: runs a variant on many plates into runs_plates/VARIANT/N/.
- measure.py: measure.json and measure.csv, the per-plate before/after indicators.
- summarize.py: summary.json, the group totals and QA before/after.

Plate 44:
- runs/batch_legacy, runs/nest, runs/nest_gate3, runs/final: bench44.json, 44_bench.jpg and the other run outputs.
- runs/_faith_legacy_venv and runs/_faith_legacy_sys: faith checks.
- holes44.py, view_holes44.py: runs/nest/holes44.json and holes44_view.jpg.
- hole_features.py, pair_test.py, hole_support.py: gate ideas that were rejected, with their .json outputs.

Eye checks:
- thumbs.py: thumbs/N_VARIANT.jpg, batch above and variant below.
- montage_after.py: thumbs/pdf_after_0-7.jpg and cut_after_0.jpg.
- sample_holes.py: sample_holes/ (PDF, 48 samples, verdicts.json) and sample_holes_cut/ (cut plates, 24 samples, verdicts.json).

Timing: runs_timing/timing.json.

### check (verdict: confirmed)

- **reason:** I reran everything the agent claimed and got the same results. Plate 44 matches to the last digit: the batch baseline, the proposal, both folds and every tolerance. My output files are byte-identical to the agent's. The diff applies cleanly to copies of the two repo files, and the patched files run unchanged from end to end. The agent's per-plate outputs match my reruns on 8 plates. Its legacy runs match the batch on all 104 unplaced plates, and its group totals match my own recount.

Overfitting to 44 is low:
- The nesting fix and the map mask have no tuned constant.
- The one tuned constant, the hole gate HOLE_PARENT = 3, sits in a flat range. Values from 2 to 4 give the same fold-A numbers.
- Any gate chosen on fold A alone, from 1.5 to 4, still beats the batch on fold B.

But 44 cannot test the parts that make the big PDF-sheet gains. It has no nested regions (PQ is unchanged), and it is a cut plate, so the map mask never runs on it. Those gains rest on counts and eye checks only.

Caveats the agent did not report (none of them reverses the verdict):
1. **Streets along the map edge are dropped on PDF sheets.** Sides along the edge of the map ground now count as paper edge and are dropped. On PDF sheets the editor's sheet outline is the paper edge (going by the harness's copy of edit_server's sheet()), not the map edge. So real street sides along the map border disappear from the editor. Across the 24 PDF sheets at 200 ft that is 201 batch lines, about 64k px. Against that, about 3,600 lines are gained.
2. **The proposed tool code reads from bench folders.** It imports map_area.py from bench_2026-11-21/visual-pdf and reads the scale table from bench_2026-11-21/census/scale. If that table goes missing, every plate gets flagged 'Q3 scale not recorded'. Copy both into durable places before applying.
3. **Two hole counts do not add up.** 'holes' counts hole polygons written; 'holes_in_open_land' counts candidate holes before straightening. On 44, no gate gives 17 holes, while gate 3 gives 7 + 13 = 20.
- **corrected_numbers:** No corrections. Every number I re-derived equals the agent's.

**Plate 44**, measured with harness/bench44.py, an unchanged copy of bench44.py (runs/batch and runs/final). Batch to proposal:
- PQ 0.4309 to 0.4309; SQ 0.8524, RQ 0.5055, 23 matched, 13 false, 13 merges, all unchanged.
- PQ on decided ground: 0.4545, unchanged.
- Recall of Ben's interior lines: 0.5316 to 0.5465.
- Precision: 0.7475 to 0.7518.
- Green precision: 0.7753 to 0.7791. Orange precision: 0.0704, unchanged.
- Delete length: 32,545 to 32,669 px. Draw length: 80,094 to 77,429 px.
- On decided ground: recall 0.5815 to 0.6000; precision 0.8855 to 0.8884.
- Fold A: recall 0.5498 to 0.5628; precision 0.7312 to 0.7356; delete unchanged at 19,700 px.
- Fold B: recall 0.5101 to 0.5273; precision 0.7691 to 0.7730; delete 12,845 to 12,969 px. The whole +124 px delete is in fold B.
- Recall / precision by tolerance, after: 3 px 0.5218/0.7236; 4 px 0.5388/0.7441; 6 px 0.5517/0.7562; 8 px 0.5587/0.7604.
- Ben's blocks closed: 0, unchanged.

**Gate sweep on 44** (gate_sweep44.py; recall / precision / delete, all folds):
- No gate: 0.5471 / 0.7357 / 35,692 px.
- 1.5: 0.5424 / 0.7511 / 32,545 px.
- 2 and 2.5: 0.5465 / 0.7525 / 32,545 px. Slightly better than the proposal.
- 3 (proposed) and 4: 0.5465 / 0.7518 / 32,669 px.
- 6 and 10: 0.5465 / 0.7446 / 33,982 px.

**Group totals**, recounted with my own script (recount_groups.py), batch to proposal:
- 24 PDF sheets at 200 ft: blocks 425 to 815; exported sides 6,841 to 10,421; sheets with 5 or fewer blocks 11 to 0; suspect after: 41 and 74.
- 8 PDF sheets at 400 ft: blocks 20 to 70; all 8 still suspect.
- Weak cut plates (8B 15B 93A 93B 55B): exported sides 223 to 227.
- Other cut plates: 2,476 blocks after; 34,420 exported sides after.
- Suspect plates after: 14, the same list as the agent's.

**New measured number** (lost_lines.py): batch lines the proposal drops on the 24 PDF sheets at 200 ft:
- 361 lines (97k px) off the map ground. This is margin, KEY and frame, which is meant to go.
- 201 lines (64k px) within 40 px inside the map edge. These are mostly real street sides along the map border; I checked 79 and 89 by eye.
- 29 lines (7k px) well inside the map.

**New estimate, by eye**, of all 33 kept holes on cut plates 5 and 11 (view_holes.py):
- 20 right (named or unnamed alleys and courts), 7 wrong (lot lines), 6 partly right or unsure.
- By count, 61% right.
- By exported length, about 79% right (13.9k of 17.7k px), about 9% wrong (1.5k px) and 13% unsure. The wrong ones are short pockets.
- **diff_applies:** Yes, measured.

- outline-nesting.diff applies cleanly with `patch -p1` (dry run, then real) to copies of tools/sanborn/unet/outlines.py and blocks_noguide.py in verify-outline-nesting/repo_copy/.
- The patched files are byte-identical to the agent's outlines_proposed.py and blocks_noguide_proposed.py.
- **The patched copy runs** unmodified, from e2e/ under the networks' venv on the CPU, with -B so no .pyc is written under tools/. Steps 3 and 4 completed on 44 and on PDF sheet 90:
  - 44: 36 blocks, 547 sides, 7 holes, not suspect.
  - 90: 45 blocks, 498 sides, 3 holes, map ground from map_area.py, not suspect.
  - Outputs equal the harness final run (44) and the agent's final run (90).
- **Caveat for applying it for real:** the patched outlines.py finds map_area.py, with its templates/, in bench_2026-11-21/visual-pdf, and the scale table in bench_2026-11-21/census/scale/scale_table.json. Neither is in tools/. Without the scale table every plate would be flagged Q3.
- **overfit_risk:** Low for the code itself, but plate 44 only tests a small part of it.

- **RETR_TREE nesting:** a structural fix with no new constant. MIN_AREA is reused.
- **Map mask:** never runs on 44, which is a cut plate.
- **Hole gate:** set by looking at 44's holes on both folds, but it sits on a plateau. Gates from 1.5 to 4 give identical fold-A numbers, so a tune-on-A choice would pick any of them. All of them beat the batch on fold B (recall at least 0.5184 against 0.5101, precision at least 0.7717 against 0.7691). Gate 2 to 2.5 is marginally better than 3 on B.
- **How big the gain on 44 is:** +1.5 points recall and +0.4 points precision, below the 3-point bar. The gain holds on both folds.
- **Where the big gains are:** on PDF sheets, which have no ground truth. Those are counts plus eye checks.
  - map_area.py's templates were cut from those same 32 sheets, so the mask is in-sample there.
  - The QA thresholds come from the census of the same batch. They are descriptive flags, not scores.
- **Hole sides on other cut plates:** mixed. About 61% right by count and about 79% by length on plates 5 and 11 (my estimate by eye). The wrong ones are short lot-line pockets, so a minimum hole-side length or width would likely remove most of them.
- **repo_clean:** Yes, the experiment changed nothing outside its folders.

- **tools/:** `git status --short tools/sanborn` is empty. outlines.py and blocks_noguide.py are tracked and still have SHA-256 bccc2b34… and 3700ff13…. No file under tools/ is newer than 12:11 today, which is when the experiment started; the __pycache__ times are unchanged from 00:10.
- **Tracked files under data/sanborn:** the only changes are 8 modified 82A files, dated 14 Nov 2026, so before the experiment, and 6 deleted files sbg/picks22/s22-82A_a–f.json. A deleted file has no date to check, but they belong to the same set of 82A changes.
- **Other folders:** no file newer than 12:11 in unet_data, picks22_guided, streetmap, cufp, bench44, visual-pdf or census.
- **My own writes:** only my folder, plus one empty timestamp file I made in the system temp folder for the date check and then deleted. Nothing in outline-nesting is newer than my scripts.
- **evidence:** All my files are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-outline-nesting/.

1. **Reproducing the plate-44 numbers.**
   - harness/ holds an unchanged copy of bench44.py and outlines_copy.py, plus the cache.
   - benchcopy/outlines_bench_final.py was regenerated with the agent's make_bench_copy.py from the diff applied to a copy of outlines.py. It is byte-identical to the agent's outlines_bench_final.py.
   - compare44.py writes compare44.json. My runs/batch outlines.json, 44_edges.json and 44_shown.json have the same SHA as bench44/runs/batch and the agent's runs/batch_legacy. My runs/final files have the same SHA as the agent's runs/final.

2. **Applying and running the diff.**
   - `patch -p1` applies cleanly in repo_copy/. The results are byte-identical (cmp) to the agent's outlines_proposed.py and blocks_noguide_proposed.py.
   - e2e/run_e2e.py runs the patched files unmodified. It uses a fake _ws pointing at e2e/data/sanborn, and blocks_noguide.run() is fed the batch's saved maps in place of the networks.
   - The maps it writes again are identical to the batch maps.
   - On 44, outlines.json, 44_edges.json and the block mask equal the harness final run.
   - On 90, with map_area.py run live, outlines.json equals the agent's final run, which used the cached masks.
   - 90_blocks_ng.json carries the QA fields (editor_per_line 0.877, 200 ft, not suspect).

3. **Per-plate checks** (check_plates.py).
   - 'legacy': the agent's legacy outlines.json and block masks are identical to the batch on 104 of 104 unplaced plates.
   - 'rerun' of my bench copy on 7, 41, 30, 2, 75, 8B, 47 and 17: outlines.json and block mask identical to the agent's final runs on all 8.
   - recount_groups.py independently reproduces the group totals.

4. **Overfitting.**
   - gate_sweep44.py (gate_sweep44.json and sweeps/) shows the plateau described above.
   - Fold A is identical for gates 1.5 to 4. Every gate from 1.5 to 10 beats the batch on fold B, in both recall and precision.

5. **Overlays I looked at myself.**
   - Agent's thumbs/30_new_gate.jpg: the batch had 1 'block', the margin ring with 9 lines. The proposal has 34 blocks and 398 editor lines, mostly on real streets. Large merged districts remain, and the hole gate leaves their inner streets out.
   - Agent's thumbs/5_final.jpg: block sides are unchanged and 16 hole pieces are added. I zoomed into all of them in holes_view/5_holes.jpg: mostly named courts and alleys (Bailey Ct, Olympia Ct, Thorpe, L'Hommedieu, Starry Alley), plus 3 lot-line pockets.
   - Agent's thumbs/cut_after_0.jpg: 8B's 2 hole pieces look like lot lines; 15B, 93A and 93B are unchanged failures of the networks.
   - My own crops in holes_view/11_holes.jpg: Betts, Rider, Gorman, Barton and several alleys right; 4 short lot lines wrong.
   - My own lost/79_lost.jpg and lost/89_lost.jpg: the lost edge-band lines lie along streets on the map border (Madison Rd and Ruth Ave on 79; Woodford Rd and the east edge on 89).

6. **Other checks.**
   - The only readers of outlines.json under tools/ (make_labels.py, crop.py and blocks_noguide step 4) use sides only, so hole polygons are harmless there today.

## experiment: outline-quality

I tried the three outline-step changes on plate 44, first one at a time and then together. I scored them with my copy of the bench44 harness, ran a fold-A/fold-B parameter sweep, checked the combined change on 4 cut plates and 1 PDF sheet, and wrote two unified diffs. The diffs are not applied. Everything is in data/sanborn/bench_2026-11-21/outline-quality/. All runs were on the CPU and nothing was trained.

Main results, all measured on plate 44 against Ben's street map (bench44_copy.py, gathered by compare_runs.py):
- (a) One watershed marker per block seed is the only change that moves block quality. PQ rises from 0.431 to 0.517, and both folds gain: A 0.474 to 0.544, B 0.385 to 0.490. Matched blocks go from 23 to 29. The earlier review measured only +0.009 for markers on these maps because it still traced the union of the blocks. Here each block is traced on its own.
- (b) The green gate does not change which lines are shown, only their colour. Green precision rises from 0.775 to 0.848.
- (c) Closed rings (collinear sides joined, corners extended, bridges otherwise) close 18 of Ben's 55 blocks, against 0 in the batch. Open line ends drop from 608 to 1 and recall rises from 0.532 to 0.619. The cost is many wrong 'bridge' lines: precision falls to 0.646.
- Combined (a+b+c) at outlines.py's own constants: PQ 0.543 (A 0.562, B 0.523), recall 0.619, precision 0.646, green precision 0.841, 18 blocks closed at both snap 1.5 and snap 10.
- Same, but step 4 also drops sides and bridges that lie on no line at all: precision 0.760, recall 0.610, 6 blocks closed, 261 open ends. This version is better than the batch on PQ, recall, precision, green precision, draw length and open ends. Delete length is about the same (33.1k against 32.5k px).
- (d) The sweep found nothing better than outlines.py's current constants that holds on both folds. Tuning on fold A and testing on B gains 0.019 PQ over the untuned settings. Tuning on B and testing on A loses 0.024. The ring settings I picked by hand were picked by the sweep in both directions.
- The redirected copy of the proposed outlines.py gives exactly what I measured: its outlines.json is byte-identical to the combined variant's, under both Pythons.
- On cut plates 5, 66, 3 and 64A the combined change does nothing strange (block counts 62 to 64, 105 to 106, 38 to 44 and 14 to 18). On PDF sheet 90 it lifts the batch's single block to 41, because blocks are now traced one by one. That incidentally gets around the RETR_EXTERNAL nesting loss.

**Baseline:** Batch outline step on plate 44: the batch's own maps (44_pred_area_ng1.png and 44_lines_lines_ng1.png), outlines.py unchanged, run in the venv as the batch runs it. I re-measured it in my folder as runs/batch_repro with bench44_copy.py, an unchanged copy of bench44.py, and it reproduces the bench44 baseline exactly (measured):
- Blocks: PQ 0.4309 (fold A 0.4737, fold B 0.3852), PQ on decided ground 0.4545. 23 matched, 13 false, 13 merges.
- Shown lines: recall of Ben's interior lines 0.5316, precision 0.7475, green 0.7753, orange 0.0704.
- Closure: 0 of 55 blocks closed, 0 intact rings.
- Ben's workload: delete 32,545 px (184 lines), draw 80,094 px (164 lines).
- The batch's own 'on a printed line' share: 0.961.

Faithfulness (measured, check_faith.py, faith_sys.json and faith_venv.json):
- outlines_oq.py with every switch off gives outlines.json and the block mask byte for byte, under system Python (cv2 4.13) and the venv (cv2 5.0). That holds against bench44/runs/batch/outlines.json (batch maps) and against picks22_guided/22-44/outlines.json (guided maps).
- On plates 5, 66, 3, 64A and 90 the no-switch run equals the batch's stored picks22_guided/22-N/outlines.json (plates_check.py, batch_reproduced = true).

Open ends and estimated editor time for 44 come from open_ends44.py: 608 open ends, about 61.5 minutes. The time is an estimate built from visual-cut's guesses per edit (tally.py: deleting a line 3 s, drawing a side 8 s, closing an end 3 s).

### variant a_markers: one watershed marker per block seed

- what: Block seeds (P>0.5, eroded SEED_B=14 as now) are cut by the line map: P(line)>0.5, dilated 3 px. Each 4-connected piece of 2,000 px or more gets its own watershed label; smaller crumbs are left to the watershed. After the watershed, each block is opened and size-filtered (the union opening is exact because blocks are 1 px apart) and traced on its own. outlines.py traces the union with RETR_EXTERNAL, which joins touching blocks again. Nothing else changes (variants/v_a_markers.py, outlines_oq.py markers=True).
- plate 44: Measured, bench44_copy.py into runs/a_markers, table from compare_runs.py:
- PQ 0.5174 (A 0.5442, B 0.4899), against 0.4309 (A 0.4737, B 0.3852). Decided ground: 0.5438 against 0.4545.
- 29 matched (A 15, B 14), 11 false, 12 merges.
- Watershed-stage PQ 0.498.
- Recall 0.5358, precision 0.753, green 0.780.
- 0 blocks closed. Delete 31.9k px, draw 79.4k px.
- Gain on both folds: +0.070 (A) and +0.105 (B).
- No 4-connected piece held two watershed labels in any run (sweeps/*.jsonl, mixed_pieces = 0).
- other plates: Only as part of the combined variant (see abc).
- time: Outline step 24.6 s in the venv against 19.3 s for the batch (machine shared and at 100% CPU).

### variant b_gate: green needs line-network support

- what: At outlines.py:108 a side is 'on print' (green) only when on_ink AND dt (detected line under it). On ink without line support it becomes 'on print only', which step 4 exports as orange (variants/v_b_gate.py).
- plate 44: Measured, runs/b_gate:
- Green precision 0.8483 (A 0.8658, B 0.827), against 0.7753 (A 0.7587, B 0.7972).
- Orange precision 0.186, against 0.070.
- The shown set is unchanged, so PQ (0.4309), recall (0.5316), precision (0.7475), delete and draw are all unchanged.
- In the combined run, 'on print only' sides are 76 sides, 16.5k px, of which 27% lie on Ben's lines (analyse_sides.py).
- other plates: Green share of editor length with the combined variant and drop_nol: 5: 0.982 to 0.925; 66: 0.986 to 0.967; 3: 0.970 to 0.902; 64A: 0.964 to 0.827 (plates_check.py). That is the gate moving unsupported sides to orange.
- time: Negligible (21.5 s against 19.3 s; noise on a loaded machine).

### variant c_rings: closed rings

- what: In straighten(), short pieces are dropped and the fitted sides are closed into a ring (outlines_oq close_ring):
- Neighbours on one straight line (within 4 degrees, each end within 12 px of the other's line, gap up to 250 px) are joined into one side and slid onto the detected line again.
- Each side is extended to its intersection with the next side when that point is within 400 px and does not turn either side back on itself.
- Ends within 12 px are joined at their midpoint.
- Otherwise a 'bridge' side is added; it is tested on ink and line like any side.
This is variants/v_c_rings.py, without markers.
- plate 44: Measured, runs/c_rings:
- PQ 0.4583 (A 0.5111, B 0.4018).
- Recall 0.6111, precision 0.6388.
- Ben blocks closed: 15 at snap 10, 11 at snap 1.5 (fold A 11, fold B 4). 30 intact rings.
- Open ends 1 (open_ends44.py).
- Delete 62.6k px, draw 68.7k px.
- Settings sweep (rings1, with markers and gate): COLIN_OFF 12 against 6 raises closure from 14 to 17. Re-sliding joined sides adds 1 more (18). RING_CORNER 400 against 250 or 120 gives recall 0.619 against 0.611/0.604 with the same closure.
- Bridges with markers and gate (analyse_sides.py, _probe_par.py): 169 on 44.
  - Bridges on no line: 'parallel' 111 (16.6k px, 5% on Ben's lines), 'far' 29 (8.8k px, 13%), 'back' 8 (0.9k px, 2%).
  - Bridges on print: 73-85% right.
- other plates: See abc.
- time: Outline step 22.3 s (with markers about 25 s).

### variant abc: (a)+(b)+(c) at outlines.py's own constants, step 4 unchanged (keep everything)

- what: markers + gate + rings (COLIN_OFF 12, join re-slide 12, RING_CORNER 400). SEED_B 14, SEED_S 8, THR 127, MIN_AREA 6000 are as now (variants/v_abc.py). proposed/outlines.py implements exactly this: its redirected copy gives a byte-identical outlines.json, under both Pythons.
- plate 44: Measured, runs/abc:
- PQ 0.5430 (A 0.5621, B 0.5231). Decided ground 0.5651.
- 29 matched, 8 false, 12 merges.
- Recall 0.6194 (A 0.6219, B 0.6163).
- Precision 0.6462 (A 0.6304, B 0.6658). Green 0.8414, orange 0.1917.
- Ben blocks closed: 18 at snap 10 and 18 at snap 1.5 (A 11, B 7). 33 intact rings.
- Delete 61.6k px (302 lines), draw 68.1k px (141 lines). Open ends 1.
- Estimated editor time about 34 min, against about 61.5 min for the batch (open_ends44.py; estimate).
- The batch's own on-print share falls from 0.961 to 0.836.
- Of the 29 found blocks, 11 do not close (diag_closure.py):
  - 7 are outlines that are only roughly right (IoU 0.51-0.78);
  - 4 are real closure failures (a rail-corridor line, the paper edge).
- other plates: Batch, then abc with this step 4 (plates_check.py and plates_policy.py, plates/final/summary.json):
- 5 (100-ft downtown): blocks 62 to 64; editor lines 598 to 603; block faces at snap 1.5: 0 to 52; open ends 637 to 4; lines on the rail bins 17 to 11.
- 66 (200-ft residential): 105 to 106 blocks; 712 to 685 lines; faces 26 to 97; open ends 408 to 0; rail lines 9 to 6.
- 3 (rail yard and river): 38 to 44 blocks; 510 to 657 lines; faces 0 to 18; open ends 672 to 4; rail lines 155 to 166; small outlines 17 to 20.
- 64A (hillside): 14 to 18 blocks; 529 to 581 lines; faces 0 to 9; open ends 562 to 8; rail lines 53 to 71; largest outline 0.657 to 0.403 of the paper.
I looked at the overlays myself (plates/final/N_side_by_side.jpg and 5_crop_3500_2600.jpg):
- Alleys are split where the line network drew them, on 5 and 66 in particular. The market-house strip on 5 is now separate from block 30.
- On 64A the curved roads become straight bridges.
- In the yard on 3, rail tracks now carry bridges and orange lines. This is the known rail-as-block-line problem (VC-3), slightly busier.
- One overshoot on 5: a 400-px corner extension runs a side across a street the area map calls block. The batch had the same error, as a wavy edge.
- time: Outline step on 44: 24.6 s in the venv against 19.3 s. Plates: 5 16.8 to 19.5 s, 66 13.8 to 19.0 s, 3 14.0 to 17.7 s, 64A 15.8 to 25.8 s, 90 7.8 to 26.7 s. Measured on a machine at 100% CPU.

### variant abc + drop_nol (the two proposed diffs)

- what: Same outlines as abc. blocks_noguide.py step 4 also leaves out sides and bridges whose state is 'not on a line' (the review's pp-7: 90-96% wrong). Green and orange are otherwise as now (variants/step4_drop_nol.py, proposed/blocks_noguide.py). runs/proposed runs the redirected proposed outlines.py with this step 4 and gives identical numbers.
- plate 44: Measured, runs/abc+drop_nol and runs/proposed:
- PQ 0.5430 (A 0.5621, B 0.5231).
- Recall 0.6097 (A 0.618, B 0.5999).
- Precision 0.7596 (A 0.7405, B 0.7838). Green 0.8414, orange 0.342.
- Blocks closed: 6 at snap 10 and at snap 1.5 (A 4, B 2).
- Delete 33.1k px (141 lines), draw 70.2k px (145 lines). Open ends 261 (0.68 per line, against 1.23 for the batch).
- Estimated editor time about 39 min (open_ends44.py; estimate).
- Other step-4 policies on the same outlines (step4_policies.py, sweeps/policies.jsonl):
  - drop only bridges on no line: precision 0.724, 7 closed;
  - drop those longer than 120 px: precision 0.701, 11 closed;
  - green only: precision 0.841, recall 0.565, 3 closed.
- Note: bench44's 'intact rings' (33) does not see this step-4 filter, so it overstates intact rings for this variant.
- other plates: Batch, then this variant (plates_check.py):
- 5: editor lines 598 to 476; faces 0 to 16; open ends 637 to 216; rail lines 17 to 11.
- 66: 712 to 620; faces 26 to 74; open ends 408 to 117; rail lines 9 to 6.
- 3: 510 to 444; faces 0 to 3; open ends 672 to 379; rail lines 155 to 146.
- 64A: 529 to 442; faces 0 to 0; open ends 562 to 236; rail lines 53 to 37.
- PDF sheet 90 (plates/pdf_probe): blocks 1 to 41, editor lines 3 to 299, block faces 0 to 15.
  - The margin ring's sides are paper-edge sides, so none reach the editor.
  - One small piece lands in the KEY box.
- time: As abc.

### variant d: parameter sweep with fold-held-out selection

- what: Sweep 1, grid1: 60 settings on top of abc (sweep.py, sweeps/grid1.jsonl):
- SEED_B 10, 14 or 24; SEED_S 4 or 8; THR 127, 160 or 200; MK_CUT 3 or 6; MIN_AREA 6000 or 20000.
- Picked by PQ on one fold (ties by line F1, then closure), reported on the other (fold_select.py).
Sweep 2, rings1: 24 ring settings (RING_CORNER 120, 250 or 400; COLIN_ANG 4 or 8; COLIN_OFF 6 or 12; join re-slide 0 or 12), picked by blocks closed on the fold.
Sweep 3, probe2: street seeds on thin P<0.5 ridges (ridge 3) and line gaps bridged along straight lines (mk_close 80).
- plate 44: Held-out numbers (measured), fold_select_grid1_pq.json:
- Tune on A, test on B: chosen SEED_B 24, SEED_S 4, THR 127.
  - B: PQ 0.5419, against 0.5231 for the untuned abc and 0.3852 for the batch.
  - B: F1 0.619 against 0.640; closed 6 against 7.
  - Rank 5 of 60 on B.
- Tune on B, test on A: chosen SEED_B 14, SEED_S 8, THR 160.
  - A: PQ 0.5382, against 0.5621 untuned and 0.4737 batch.
  - A: F1 0.616 against 0.626; closed 9 against 11.
  - Rank 16 of 60 on A.
- So no constant change gains on both folds. By bench44's own rule (gain on both folds, about 0.03 PQ or more), keep SEED_B 14, SEED_S 8, THR 127.
Ring settings (fold_select_rings1+closed): both directions pick COLIN_ANG 4, COLIN_OFF 12, re-slide 12, RING_CORNER 400. Held-out: B 7 closed, A 11 closed, rank 1 of 24 both ways. These are the settings in the diff.
probe2:
- ridge seeds: PQ 0.546 (+0.003), closure 18 to 17;
- directional closing: PQ 0.536 (-0.007).
Neither is adopted.
merge_cues.py explains why constants cannot fix the remaining merges:
- Over 37 merged pairs of Ben blocks, the area map calls a median of only 21.5% of the gap ground street.
- The line network drew a median of 49.7% of the dividing sides (51.7% at P(line)>0.25).
- 9 pairs have under 30% of both, so no post-processing can split them.
- other plates: Not run on other plates: the tuned settings were not adopted.
- time: About 25-30 s per setting, 4 workers. grid1 took about 35 minutes on the loaded machine.

**Recommended:** Adopt diffs/outlines.py.diff: markers, green gate and closed rings, with outlines.py's current constants and the ring settings COLIN_OFF 12, re-slide 12, RING_CORNER 400 that fold selection picked both ways. Don't adopt any tuned SEED or THR change.

For step 4 there are two choices:

1. Safe default: also apply diffs/blocks_noguide.py.diff (drop 'not on a line'). Against the batch on 44 (measured):
   - PQ 0.431 to 0.543 (+0.112; fold A +0.088, fold B +0.138);
   - recall 0.532 to 0.610 (+7.8 points);
   - precision 0.748 to 0.760 (+1.2);
   - green precision 0.775 to 0.841;
   - draw length 80.1k to 70.2k px; delete length 32.5k to 33.1k px (+0.6k, about the same);
   - blocks closed 0 to 6; open ends 608 to 261.
   No headline number gets worse by more than that 0.6k px of delete length.

2. Closure first: apply only the outlines.py diff, step 4 unchanged. On 44:
   - PQ 0.543; 18 of 55 blocks closed; open ends 1;
   - recall 0.619 but precision 0.646, delete length 61.6k px;
   - estimated editor time about 34 min against about 39 min for option 1 and about 61.5 min for the batch (open_ends44.py, rough estimate).
   This is Ben's choice. The extra lines are orange and 5-13% right.

Gains below are measured on plate 44 only. Markers gain on both folds by more than 0.03 PQ, so by bench44's own rule that is a real gain. The ring and gate effects are in-sample on 44, but the ring settings held out both ways.

**Regressions:** Measured:
- Precision falls if step 4 is left unchanged: 0.748 to 0.646, delete length 32.5k to 61.6k px. Bridges that lie on no line are 5-13% right. The drop_nol step 4 avoids this but closes only 6 blocks instead of 18.
- The batch's own on-print share falls from 0.961 to 0.836 (0.829 for rings alone). This is not a quality score, but run_plates.json and N_blocks_ng.json will look worse.
- Green share falls by design: 64A 0.964 to 0.827, 3 0.970 to 0.902.
- Outline step time rises by about 15-60%: 44 19.3 to 24.6 s; 64A 15.8 to 25.8 s; 90 7.8 to 26.7 s.
- Rail yards: with step 4 unchanged, lines on the rail bins go up on 3 (155 to 166) and 64A (53 to 71). With drop_nol they go down (146, 37). Plate 3's yard gets more small outlines (17 to 20) and more bridges.
- Hillside 64A: curved roads become straight bridges and chords.
- On 5, a 400-px corner extension draws a side across a street that the area map calls block. The batch had the same error as a wavy edge.
- 12 merges remain on 44 and 26 of Ben's blocks are still missed. 9 merged pairs have almost no evidence in either map (merge_cues.py), so the rest needs the networks (out-of-fold area maps, alleys taught).
- Tuned constants do not transfer between folds (-0.024 PQ in one direction), so tuning on 44 alone is noise-level.

Risks not measured:
- No truth outside 44. The plate checks are indicators plus my own look at the overlays.
- If a printed lot line fully cuts a block seed, that block could be split. No split happened on 44 (gt_split 0 in every run).
- On PDF sheets, tracing blocks one by one brings back nested blocks. On 90 one piece lands in the KEY box. The margin mask and the KEY mask (visual-pdf) are still needed.
- bench44's 'intact rings' ignores the drop_nol filter.

Housekeeping:
- A timestamp file was touched in the system temp folder (/tmp/oq_start) to check that picks22_guided and streetmap were unchanged; both had 0 new files.
- I also stopped a background test run of the grid sweep (my own processes) and restarted it with a smaller grid.

**Diff:** C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/outline-quality/diffs/outlines.py.diff (183 lines) and C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/outline-quality/diffs/blocks_noguide.py.diff (25 lines, the optional drop_nol step 4). Both are unified diffs against tools/sanborn/unet/ with a/ and b/ paths. `git apply --check` reports that both apply cleanly; neither was applied. The full proposed files are in proposed/outlines.py and proposed/blocks_noguide.py.

**Files:** All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/outline-quality/. A second copy of every script is in _second_copy_scripts/.

Outline step and harness:
- outlines_oq.py: outlines.py with switches. With no switches it is outlines.py exactly.
- check_faith.py: writes faith_sys.json and faith_venv.json.
- bench44_copy.py: an unchanged copy of the bench44 harness, writing into runs/TAG/.
- outlines_copy.py and cache/decided_half.png: copied from bench44.

Variants:
- variants/v_a_markers.py, v_b_gate.py, v_c_rings.py, v_abc.py.
- variants/step4_drop_nol.py, step4_drop_nol_bridges.py.

Proposal:
- proposed/outlines.py and proposed/blocks_noguide.py.
- proposed/outlines_redirected.py, made by make_redirected.py. Its outlines.json is byte-identical to the abc variant.
- diffs/outlines.py.diff and diffs/blocks_noguide.py.diff.

Full bench runs (runs/<tag>/bench44.json, 44_bench.jpg, outlines.json):
- runs/batch_repro, a_markers, b_gate, c_rings, abc, abc+drop_nol, proposed.
- compare_runs.py writes compare_runs.json; open_ends44.py writes open_ends44.json.

Sweeps:
- sweep.py writes sweeps/single, rings1, probe2, grid1 and policies (.jsonl).
- show.py prints a sweep as a table.
- fold_select.py writes fold_select_grid1_pq.json and fold_select_rings1+closed.json (rings1 by closure).
- step4_policies.py: every step-4 policy on the same outlines.

Diagnostics:
- merge_cues.py writes merge_cues.json.
- analyse_sides.py and _probe_par.py.
- diag_closure.py writes runs/diag_closure/*.jpg.
- draw_sides.py.

Plate checks:
- plates_check.py and plates_policy.py write plates/final/summary.json, N_side_by_side.jpg and N_*_outlines/shown.json for 5, 66, 3 and 64A.
- crop_plate.py writes plates/final/5_crop_3500_2600.jpg.
- plates/pdf_probe/: plate 90.
- plates/try1/: an early run on 66.

### check (verdict: confirmed)

- **reason:** I re-ran every main plate-44 number for the baseline and the proposed change, using my own copies of the code and my own redirected scripts, and got the agent's figures exactly. Both diffs apply cleanly and the patched copies run. The gain holds on both folds. It also holds on a second, independent pair of maps for plate 44: the guided networks, which are also held out of training on 44. The new constants I left unswept change almost nothing. On 6 other plates I found no serious regressions, only the minor visual flaws below. The checks are complete, so the verdict is confirmed. The caveats below are about choices and side effects, not wrong numbers.

Caveats:
1. In the recommended version, step 4 drops sides that lie on no line. That removes most of the gain in closed blocks. Ben's blocks closed: 6 with the drop, 18 if step 4 keeps everything. Block quality of the faces the editor shows (PQ): 0.204 with the drop, 0.474 without.
2. Delete length rises slightly, from 32,545 to 33,107 px, although the number of lines to delete falls from 184 to 141.
3. tools/sanborn/unet/make_labels.py:57 and crop.py:29 also read the 'on print' sides of outlines.json. If outlines.py is rerun on a placed plate, their input changes. This was not evaluated. On the guided 44 maps, 'on print' length goes from 92.9k to 112.3k px.
4. In the patched blocks_noguide.py, the progress message no longer matches itself. Its count is now the gated green sides, but its percentage is still the ink-only share.
5. All ground truth is one plate. The other plates show indicators only.
- **corrected_numbers:** No corrections. All of these are MEASURED on plate 44 against Ben's street map and reproduce the agent's figures exactly. Each comes from bench44_vcopy.py (an unchanged copy of bench44.py), and the outline step ran in the networks' venv.

Baseline (current outlines.py, redirected by my redirect_outlines.py into current_outlines_redirected.py; runs/v_batch):
- PQ 0.4309 (fold A 0.4737, fold B 0.3852); 23 matched, 13 false, 13 merges.
- Recall 0.5316, precision 0.7475, green precision 0.7753.
- 0 blocks closed. Delete 32,545 px, draw 80,094 px. The batch's own on-print share is 0.961.
- Its outlines.json is byte-identical to bench44/runs/batch/outlines.json (sha 91b8c13104d336db).

Proposed, both diffs (patched/outlines_redirected.py with step4_patched.py; runs/v_proposed):
- PQ 0.5430 (A 0.5621, B 0.5231). On decided ground 0.5651. 29 matched, 8 false, 12 merges.
- Recall 0.6097 (A 0.618, B 0.5999). Precision 0.7596 (A 0.7405, B 0.7838).
- Green precision 0.8414, orange 0.342.
- Closed blocks: 6 (A 4, B 2) at snap 10 and also at snap 1.5.
- Delete 33,107 px (141 lines), draw 70,178 px (145 lines).
- Its outlines.json is byte-identical to the agent's runs/proposed and runs/abc (sha 7c2578516c9bc796).

Same outlines, step 4 unchanged ('abc'; runs/v_abc_keepall):
- PQ 0.5430. Recall 0.6194, precision 0.6462.
- 18 blocks closed (A 11, B 7). Delete 61,619 px, draw 68,051 px.

Open ends (MEASURED with my own code, open_ends_check.py): 608 for the batch, 261 proposed, 1 for abc. These match the agent's counts. The agent's editor-time minutes (61.5, 39, 34) are ESTIMATES. I did not re-derive them.

Extra checks (MEASURED, sens_summary.py and sens_summary.json):
- Guided maps on 44 (edge_v1 and lines_v2), current against proposed:
  - PQ 0.5918 to 0.6885 (A 0.5014 to 0.6090, B 0.6770 to 0.7621).
  - Recall 0.4109 to 0.5357, precision 0.7310 to 0.8441.
  - Delete 28,054 to 16,824 px, draw 112,965 to 83,226 px.
  - My guided 'current' run equals bench44/runs/guided exactly.
- Sensitivity to the constants the agent did not sweep:
  - MK_SEED_MIN 1000 or 4000: identical to the default (2000) on every number.
  - COLIN_GAP 125: PQ 0.5430, precision 0.7612, 4 blocks closed.
  - SNAP_JOIN 24: precision 0.7624, 6 blocks closed.
- Line tolerance (bench JSON, tol_sensitivity): the recall gain holds from 3 px (0.5072 to 0.5835) to 8 px (0.5434 to 0.6204).
- Block quality of the faces the editor shows (stage 4 PQ): batch 0.0, proposed 0.204, keep-all 0.474.
- Outline-step time on 44 (MEASURED, machine loaded): 14.4 s current, 17.7 s proposed.
- **diff_applies:** Yes. `patch -p4` applied outlines.py.diff and blocks_noguide.py.diff to fresh copies of tools/sanborn/unet/outlines.py and blocks_noguide.py cleanly, with no offsets or fuzz. The results are byte-identical to the agent's proposed/ files, and both parse.

- The patched outlines.py, redirected for output only, runs in the venv on 9 plates. On 44 it gives the numbers above.
- The patched blocks_noguide.py, redirected (stored maps instead of the networks, outputs to bng_run/), runs on 44, 5 and 43 with exit code 0. Its edges match the harness's step 4.
- I did not run the networks themselves. The diff does not touch them.
- **overfit_risk:** Low to moderate.

Why low:
- The gain holds on both folds of 44 (PQ A +0.088, B +0.138).
- It holds on a second, held-out pair of maps for the same plate (guided: PQ +0.097, with both folds up).
- It holds across line tolerances from 3 to 8 px.
- The changes are general rules. The new constants are either swept with fold-held-out selection (MK_CUT, the ring settings) or insensitive (MK_SEED_MIN 1000-4000 gives identical results; COLIN_GAP and SNAP_JOIN barely matter).

Why not none:
- Plate 44 is the only ground truth. The other plates show only proxies (faces, open ends) and pictures.
- The ring constants were picked for closure under a step 4 that the proposal does not use.
- Visible weak spots on other plates: rail yards (rail-as-block-line wedges and bridges, plate 3), curved hillside roads cut into straight pieces (64A), and on 400-ft plates the green gate turns most sides orange (93A: 84 to 34 green).
- **repo_clean:** Yes, as far as this experiment goes. `git status --short tools/sanborn` is empty.

- Tracked changes under data/sanborn: 8 modified 82A files dated 14 Nov 2026 and 6 deleted sbg/picks22/s22-82A_*.json. All of them predate this work and are not referenced by the experiment's scripts.
- No file in unet_data, picks22_guided, streetmap, cufp or tools/sanborn is newer than run_plates.json (10:44 today), except Ben's rail_ben.page_2026-11-21.json at 11:08, before the agent started.
- I wrote only inside bench_2026-11-21/verify-outline-quality/.
- **evidence:** Everything is in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-outline-quality/.

1. Re-run on plate 44:
   - I copied bench44.py as bench44_vcopy.py (cmp: identical) and wrote redirect_outlines.py, an I/O-only redirection that is independent of the agent's make_redirected.py.
   - runs/v_batch, runs/v_proposed and runs/v_abc_keepall have headline JSON equal to the agent's batch_repro, proposed, abc+drop_nol and abc runs.
2. Diffs:
   - `patch -p4` applied both diffs to copies in patched/ with no offset or fuzz. The results are byte-identical to outline-quality/proposed/outlines.py and blocks_noguide.py.
   - The patched outlines.py runs, redirected, on 44, 5, 66, 3, 64A, 90, 49, 93A and 8B (plates_rerun.py, plates_rerun.json).
   - My redirected current copy reproduces the batch's stored picks22_guided/22-N/outlines.json on all 8 non-44 plates.
   - My patched copy equals the agent's plates/final and pdf_probe variant outlines on 5, 66, 3, 64A and 90.
   - redirect_bng.py makes an I/O-redirected patched blocks_noguide.py. It reads the stored maps instead of running the networks, because steps 1-2 are not changed by the diff.
   - That copy ran on 44, 5 and 43 (rc 0) and still refuses 45 for having a guide. Its 44_edges.json equals the harness's step-4 output (401 edges). It writes bridges=169 into 44_blocks_ng.json.
3. Overfitting:
   - Fold gains: PQ +0.088 (A) and +0.138 (B). Recall and precision rise on both folds.
   - The change is rule-based: one watershed marker per seed piece cut by the detected lines, each block traced on its own, green only where the line network also runs, and closed rings.
   - The guided-map check above and the sensitivity runs (sens/README.txt) give the same picture.
   - Limits: there is only one truth plate. The ring constants were chosen for closure under the keep-everything step 4, not under the step 4 that is proposed.
4. Overlays. I looked at the agent's side-by-sides for 3, 64A, 66, 5 and 90, and made my own close-ups with crops.py (crops/*.jpg) for 5, 64A, 3, 66, 49 and 93A:
   - 66: cleaner closed tops.
   - 64A: both sides of Vineyard Place are now found; curves become straight pieces.
   - 5: one block corner is cleaner; a few cut-off corners are lost.
   - 3 (rail yard): a new false wedge where a 400-px corner extension joins the B&O line to the main track; more orange lines and bridges in the yard.
   - 49 (400 ft): regains the southern subdivision; fewer open ends.
   - 93A (400 ft): green sides fall from 84 to 34, moved to orange by the green gate.
   - 90: 1 block becomes 41.
   - Nothing catastrophic.
5. git status --short tools/sanborn is empty.
   - The only tracked data/sanborn changes are 82A files dated 14 Nov, plus deletions of sbg/picks22/s22-82A_*.json, which none of the agent's scripts reference. So they were not made by this experiment.
   - The only file in unet_data, picks22_guided, streetmap or cufp newer than the batch is Ben's rail_ben.page_2026-11-21.json (11:08, before the agent started).
   - Every write in the agent's scripts goes into its own folder.

## experiment: inference

I tested the network inference options for plate 44 against Ben's street map, using a copy of the bench44 harness. The scale options were also tried on the 400-ft batch plates, where there is no truth. All work was on the GPU (DirectML). No network was trained. Nothing in the repo was written: the hashes of unet.py, edgenet.py and blocks_noguide.py are unchanged, and no file under unet_data, picks22_guided, streetmap, cufp or tools changed after 12:05.

Faithfulness (measured, repro_batch44.py): the copied network code reproduces the batch's 44_pred_area_ng1.png and 44_lines_lines_ng1.png byte for byte on the GPU. The bench run 'batch' reproduces PQ 0.4309.

1. Flip and turn averaging (TTA) for the area network is the one clear gain. The area map is averaged over all 8 turns and flips.
   - On the batch's own tile grid: PQ 0.431 to 0.495.
   - Averaged over 6 equally valid tile grids: PQ 0.442 to 0.482, higher on all 6 grids; fold A +0.018, fold B +0.063.
   - Ben's interior lines found: 53.6% to 55.8% (higher on all 6 grids). Precision is unchanged (76.8% to 76.7%).
   - The 4-way set is unstable: +0.016 on average, and worse on one grid (-0.039).
   - Cost: about 6.4 s more per plate on the GPU.

2. These gained nothing on 44:
   - TTA for the line network (7 times slower).
   - Hann blending, on either network: area -0.005 PQ over 6 grids; lines give the same PQ and 0.8 points less precision.
   - Averaging the area map over 6 tile grids on top of TTA x8 (0.488 against 0.482).

3. The tile grid alone moves the bench's PQ (measured, noise_floor.py): standard deviation 0.015, range 0.430 to 0.470 over 6 grids. The batch's 0.431 is the second lowest. Any network-map change worth less than about 0.04 PQ cannot be judged from one run.

4. Scale normalisation as proposed (resample to the 200-ft size) fails on the ground truth.
   - 44 is a 100-ft plate. Run at the 200-ft size, the area network scores PQ 0.124; at 0.71 times, 0.352; at 1.41 and 2 times, 0.000. Averaging scales 1 and 0.5 gives 0.375.
   - The cause is pen width. Thickening every dark line on 44 by 2 px at its own scale gives PQ 0.029; thinning by 1 px gives 0.172, and by 2 px gives 0.000. The networks key on pen width as much as on street width.
   - Synthetic 400-ft 44 (shrunk to a quarter): as the batch runs it, PQ 0.000; enlarged x2, 0.108; enlarged x4, 0.439. This synthetic thins the pens too, so it says little about real 400-ft sheets.
   - On the 10 real 400-ft plates, plain x2 enlargement exports 50% more line length, but by eye about half of it is wrong (lot lines). Right length stays about the same, and wrong length triples.
   - x2 enlargement followed by a 3x3 max filter, which thins the pens back ('up2thin'), exports about the same length as the batch (+1%). By eye (estimate) about 90% of it is on a street side, against 77% for the batch: 18% more right length and 55% less wrong length. These eye checks were mine, not blind, with 24 to 44 samples per part.

Diffs (written, not applied; git apply --check passes):
- unet.py and edgenet.py get a tta option. tta=1 is checked to give byte-identical maps.
- blocks_noguide.py uses AREA_TTA = 8.
- A separate optional blocks_noguide diff adds up2thin for the 10 plates at 400 ft. It reproduces my up2thin maps exactly on 93A.

**Baseline:** The batch chain on plate 44: area_ng1 and lines_ng1 maps as stored in unet_data, run through the batch's outline step and step 4 and shown as the editor shows them, scored against streetmap/22-44.json. Source: bench44 (bench44/bench44.py, baselines.json). I re-ran it with an unchanged copy (inference/bench/bench44_copy.py) as tag 'batch' and got identical numbers.

All measured:
- PQ 0.4309 (SQ 0.8524, RQ 0.5055): 23 matched, 13 merges, 13 false. Decided ground: PQ 0.4545. Fold A 0.4737, fold B 0.3852.
- Interior recall 0.5316, precision 0.7475 (green 0.7753, orange 0.0704).
- Blocks closed: 0 of 55. Intact rings: 0. Delete 32,545 px, draw 80,094 px.

New baseline information (measured; noise_floor.py from summary44.json):
- The same batch settings on 6 equally valid tile grids give PQ mean 0.442, sd 0.015, range 0.430 to 0.470.
- Fold means: A 0.505, B 0.372.
- Recall mean 0.536, precision mean 0.768.

GPU time for the batch settings on 44 (repro_batch44.py and the first make_maps44.py run, at low load): area 1.2 s, lines 5.0 s. The batch's whole blocks step had a median of 14.5 s per plate, outline step included (run_plates.json).

Rail was not in scope.

### variant a_tta8: area net averaged over 8 turns and flips (RECOMMENDED)

- what: infer_lib.predict(tta=8) on the area net. Each 768 px tile is run in all 8 dihedral orientations, turned back, and P(block) averaged; tiling is as the repo (crop). The line net is run once on the new area map. Same as patched unet.predict_full(tta=8): test_patch.py gives max 1/255 difference and 0 changed decisions.
- plate 44: Measured, bench44_copy via run_bench44.py.
- Batch's own grid: PQ 0.4954 (was 0.4309), decided 0.5203. 26 matched, 11 merges, 10 false. Fold A 0.5251, fold B 0.4623.
- Lines: recall 0.5533, precision 0.7675 (green 0.7845). Delete 31.0k px, draw 81.8k px. 1 Ben block closed, 1 intact ring.
- Over 6 tile grids (noise_floor.py): PQ 0.482 against 0.442 (sd 0.025 against 0.015).
  - Paired gain +0.040 (min +0.018, max +0.064); higher on 6 of 6 grids.
  - Fold A +0.018 (higher on 4 of 6), fold B +0.063 (5 of 6).
  - Recall +0.022 (6 of 6); precision -0.000.
  - Matched 25.7 against 23.3; merges 11.7 against 12.8; false 10.2 against 12.3.
- Ben's blocks newly matched on the batch grid: 18, 42, 47. None lost.
- other plates: Measured: qa_plates.py, batch against atta8, on 5, 53, 60B, 66, 1B, 30, 90 and 21.
- Block share changes by 0.007 or less on every plate.
- Short pieces fall on all 8 (-6% to -30%).
- Editor length moves -4.6% to +2.9%.
- The line skeleton is 0.3% to 11% shorter.
- Plate 30: the largest area-net region grows from 26% to 45% of the map ground (open land joined).
- Plate 21: exported sides 212 to 156. By eye at overview scale, mostly lot-line pieces dropped.
- Overviews checked by eye: overlays/30_overview_atta8.jpg and 21_overview_atta8.jpg. They look the same or slightly cleaner.
- time: Measured on the GPU, plate 44 at low load: area 7.6 s against 1.2 s, so about +6.4 s per plate. Estimate: about +12 min over 109 plates.
Under the afternoon's CPU contention: patched code 11.0 s; 8 batch plates 5-20 s for both networks.

### variant a_tta4: area net, 4-way TTA (identity, h-flip, v-flip, transpose)

- what: The review's c_tta set.
- plate 44: Measured.
- Batch grid: PQ 0.4992 (A 0.5461, B 0.4502), 27 matched; recall 0.5561, precision 0.7618.
- Over 6 grids: mean PQ 0.458 (sd 0.039, range 0.395-0.499). Paired gain +0.016, worse on 1 grid (-0.039).
  - Fold A +0.027, fold B +0.003 (-0.080 on one grid).
  - Recall +0.018.
- Not stable: x8 is better on average and on spread.
- other plates: Not run.
- time: Area 4.0 s (GPU, 44).

### variant l_tta8: line net, 8-way TTA

- what: infer_lib.predict(tta=8) on the line net (1024 px tiles, 4 at a time), area map as in the batch.
- plate 44: Measured.
- Batch grid alone: PQ 0.4463 (A 0.4950, B 0.3931); recall 0.5321, precision 0.7503.
- With area TTA x8: PQ 0.4956 against 0.4954 without, recall 0.5517 against 0.5533.
- No gain. This agrees with the review's d_lines.
- other plates: Not run.
- time: Lines 32 s against 5.0 s (GPU, 44).

### variant Hann blending (a_hann, l_hann, both_hann_tta8)

- what: Overlapping tiles every T/2 px, each weighted by a 2-D Hann window, normalised by the summed weights. Area: tile 768. Lines: tile 1024.
- plate 44: Measured.
- Area, batch grid: PQ 0.4063.
- Area, 6 grids: mean 0.437; paired -0.005 (3 of 6 higher); fold A -0.011, fold B +0.001.
- Lines, batch grid: PQ 0.4306; recall 0.5277 against 0.5316; precision 0.7397 against 0.7475.
- Hann + TTA x8 on the area net: PQ 0.4374, against 0.4954 for TTA x8 alone.
- Both nets Hann + TTA x8: PQ 0.4260, recall 0.5651, precision 0.7694.
- No gain in PQ.
- other plates: Not run.
- time: Area 3.2 s; lines 14.1 s. With TTA x8: area 23 s, lines 102 s (GPU, 44).

### variant Tile-grid offsets (noise floor) and grid ensembles

- what: Both networks' tile grids moved by 5 offsets (make_maps44.py OFFS). Also the area map averaged over the 6 grids (grid6), with lines re-run.
- plate 44: Measured.
- Batch settings: PQ 0.4309, 0.4342, 0.4705, 0.4469, 0.4405, 0.4304 (sd 0.015).
- TTA x8: 0.4954, 0.4570, 0.5077, 0.5078, 0.4765, 0.4488.
- grid6 without TTA: PQ 0.4574. grid6 of the TTA x8 maps: PQ 0.4883, which adds nothing over TTA x8 alone (mean 0.482).
- other plates: Not run.
- time: Grid ensembles cost 6 times the area pass.

### variant Scale normalisation on 44 (a 100-ft plate)

- what: Area and/or line net run on the scan resampled by s, and maps resized back (infer_lib area_map/lines_map scale=s). Plate 44 is at 100 ft to the inch (census scale table, measured 101.1 ft/in); s = 0.5 is the 200-ft training size.
- plate 44: Measured.
- Area at s=0.5: PQ 0.124 (A 0.144, B 0.104), recall 0.249. Both nets at 0.5: PQ 0.124.
- Area at s=0.71: PQ 0.352.
- Area at 1.41: PQ 0.000. At 2: PQ 0.000. With 2-times TTA x4: 0.000.
- Area multi-scale mean (1, 0.5): PQ 0.375. Multi-scale (1, 2) with TTA x4: 0.031.
- Line net alone at 0.5: PQ 0.474 (A 0.481, B 0.466), but recall 0.500 against 0.532 and precision 0.729 against 0.748. Single grid, within the noise floor.
- With area TTA x4 + lines at 0.5: PQ 0.508, recall 0.528.
- Picture: pics/44_scale_tta_B.jpg. At 0.5 nearly every street is called block; at 2, building outlines become lines.
- other plates: Not run on other 100-ft plates. The truth plate rules it out.
- time: Area at 0.5 is about 0.5 s; at 2, 6 s.

### variant Pen-width probes on 44

- what: The same geometry, with every dark line made thicker (3x3 or 5x5 min filter) or thinner (2x2 or 3x3 max filter) before both nets. This separates pen width from street width, which resampling changes together.
- plate 44: Measured.
- Thicker by about 2 px: PQ 0.029. With TTA x8: 0.025.
- Thicker by about 4 px: PQ 0.000.
- Thinner by about 1 px: PQ 0.172. Thinner by about 2 px: PQ 0.000, and block share 0.989.
- The networks fail with a 1-2 px change of stroke width.
- other plates: This explains the 400-ft results below.
- time: As the batch.

### variant Synthetic 400-ft 44 (make_synth44.py)

- what: 44 shrunk to 0.25 (0.74 px/ft, as real 400-ft sheets) and run as a plate.
- native: as the batch would run it.
- up2: enlarged x2 to the 200-ft street width.
- up4: enlarged x4 back to 44's own scale.
Maps are resized to 44 for scoring ('back' = via the small plate's size; 'keep' = straight). Also 200-ft-equivalent 44 (0.5).
- plate 44: Measured.
- syn400 native: PQ 0.000, recall 0.009.
- syn400 up2: PQ 0.108, recall 0.234.
- syn400 up4: PQ 0.439 (A 0.472, B 0.402), recall 0.448.
- syn200 native: PQ 0.106.
- syn200 up2: PQ 0.461 (back) and 0.483 (keep).
- Caveat: shrinking also thins the pen lines, which a real 400-ft sheet does not. So this shows that 44 must be seen at its own pen and street size; it does not show what suits a real 400-ft sheet.
- other plates: 
- time: Networks: 2.4 s native, 5.9 s up2, 21 s up4.

### variant up2: real 400-ft plates enlarged x2 for both nets (make_maps_plates.py up2)

- what: Scan resampled x2 (INTER_CUBIC), both networks run, maps resized back. The outline step is visual-pdf's copy with ccomp + map mask on PDF sheets; on 93A and 93B it is the batch's.
- plate 44: Not applicable to 44 (see the scale rows).
- other plates: Plates 46-50, 92, 93A, 93B, 94, 95.
- Measured (qa_plates.py): exported sides 2,711 to 4,414; editor length 527.7k to 792.6k px; blocks 78 to 151; mean block share 0.934 to 0.907.
- Only 28% of up2's length is within 8 px of a batch side (overlap_settings.py).
- Estimated, by eye (sample_sides.py montages, pooled, eye_400ft.json):
  - shared length right 37/43; batch-only 23/33; up2-only 16/39 (mostly lot lines and building outlines).
  - Precision 77% to 54%. Right length 406k to 428k px, about the same; wrong length 3 times.
  - Overlays: overlays/47_*, 92_*, 95_*. Subdivision streets are lost and lot lines are added; rural roads are found more often.
- Rejected.
- time: Networks 10-237 s per sheet under heavy contention (median 98 s).

### variant up2thin: 400-ft plates enlarged x2, then pens thinned back with a 3x3 max filter (OPTIONAL, not on truth)

- what: As up2, but after resampling every dark line is thinned by about 2 px (cv2.dilate 3x3), so the street widths match the 200-ft training plates and the pens are close to their trained width. One pass of each net. The single setting PEN=3 was chosen beforehand and not tuned.
- plate 44: Cannot be scored on 44: there is no 400-ft truth.
- other plates: The 10 400-ft plates.
- Measured: exported sides 2,711 to 2,438; editor length 527.7k to 533.6k px; blocks 78 to 68; mean block share 0.934 to 0.959. 48% of each setting's length is shared.
- Estimated, by eye (eye_400ft_up2thin.json, not blind):
  - shared right 23/24; up2thin-only right 37/44 (84%); batch-only right 25/42 (60%).
  - Precision 77% to 90%. Right length 408k to 481k px (+18%); wrong length 123k to 55k px.
  - The difference between the unique parts is about 2.6 standard errors.
  - Overlay: overlays/47_crop_west3.jpg.
- Faithfulness: test_patch400.py shows the optional diff's run() reproduces these maps exactly on 93A, and the TTA x8 maps on 60B (max 1/255, 0 changed decisions).
- time: Networks 8-47 s per sheet, median 39 s, under contention. About 7 GB RAM on a PDF sheet.

**Recommended:** Adopt area-net TTA x8: diffs/unet.py.diff plus diffs/blocks_noguide.py.diff. diffs/edgenet.py.diff only adds an unused tta option and is optional.

Expected gain over the batch baseline on 44 (measured):
- PQ 0.431 to 0.495 on the batch's tile grid. Mean over 6 grids 0.442 to 0.482 (+0.040; higher on all 6). Fold A +0.018, fold B +0.063.
- Interior line recall +2.2 points, precision unchanged.
- Merges -1.1 and false blocks -2.1 on average.
- Blocks closed stay at 0-1 of 55: TTA does not fix closure, which is the outline step's problem (bench44 finding C1).
- Cost about +6.4 s per plate on the GPU (about +12 min for 109 plates, estimate).

Keep the scans at their own scale for 100-ft and 200-ft plates. Do not adopt Hann blending, line-net TTA, grid ensembles or plain x2 resampling.

For the 10 plates at 400 ft, diffs/blocks_noguide_with_400ft_option.py.diff adds up2thin. By eye (estimate, not truth) it raises precision from about 77% to 90% and right length by about 18%. I suggest Ben checks one 400-ft plate first (for example 47 or 95) and scores up2thin against it before switching it on.

Also change how the bench is used: score any network-map change over the 6 tile grids (make_maps44.py OFFS + noise_floor.py), because the grid alone moves PQ by sd 0.015.

For Ben's next retraining (estimate): the pen-width probes say the networks need stroke-width augmentation (random 1-2 px erode, dilate and blur) and scale augmentation. With those, the 100-ft, 200-ft and 400-ft plates could share one setting.

**Regressions:** TTA x8 (recommended):
- On 44 it was worse than the batch settings on fold A for 2 of 6 grids (down to -0.017) and on fold B for 1 of 6 (-0.026).
- Precision dropped on 3 of 6 grids (down to -0.037).
- Delete length rose by about 1.4k px on average.
- On batch plates (measured, no truth):
  - Plate 30: the largest area-net region grew from 26% to 45% of the map ground (two open-land regions joined).
  - Plate 21: 26% fewer exported sides, which by eye at overview scale were mostly lot-line pieces.
  - Plate 1B: editor length -4.6%.
  - The line skeleton is shorter on all 8 plates checked.
- TTA averages probabilities, so P(block) is less extreme. outlines.py's fixed 127 threshold and seed erosions were tuned on single-pass maps, and nothing was retuned.
- Only 44 has block truth, and 44 is a 100-ft plate. The gain on 200-ft and PDF plates is assumed, not measured.

Scale:
- Resampling 100-ft plates to the 200-ft size (the census C2 and review proposal) is harmful on the ground truth: PQ 0.43 to 0.12.
- Plain x2 on 400-ft plates triples wrong length (estimate).
- up2thin:
  - is judged by eye only, by me and not blind, on 24-44 samples per part;
  - raises block share (0.934 to 0.959) and lowers the block count (78 to 68);
  - was run without TTA, and the combination with TTA is untested;
  - treats the 200-ft insets on 46, 48, 92 and 94 like the main map (they become 100-ft-sized with thinned pens; untested);
  - leaves out plate 78's 400-ft inset on a 200-ft sheet;
  - needs about 7 GB of RAM and about 30 s more per sheet.

Faithfulness and timing:
- The patched predict_full(tta=1) changes the code path but is checked byte-identical on 44 (test_patch.py).
- Timing after about 12:25 was inflated: other agents held the CPU at 100%. Only the first make_maps44 run and repro_batch44 are low-load numbers.

**Diff:** C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/inference/diffs/. All diffs are unified against the current repo files and NOT applied. git apply --check passes for each, and the repo files' SHA-256 are unchanged.

- unet.py.diff: TTA table, turn/unturn and predict_full(..., tta=1).
- edgenet.py.diff: predict_full(..., tta=1), reusing unet's TTA.
- blocks_noguide.py.diff: AREA_TTA = 8 for the area net, recorded in N_blocks_ng.json. RECOMMENDED.
- blocks_noguide_with_400ft_option.py.diff: the same, plus FT400 / PEN = 3 up2thin for 46-50, 92, 93A, 93B, 94, 95, with one area pass there. OPTIONAL.

Patched full copies: inference/patched/ and inference/patched_400/.

**Files:** Everything is under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/inference/ (about 1.1 GB). A second copy of every script, the patches, the diffs and the eye-judgment files is in _second_copy_scripts/.

Core:
- infer_lib.py: copies of the repo's UNet, device, ink_image and predict_full, plus the tta, blend (crop/hann), scale, pen and offset options.
- repro_batch44.py: byte-identical check, logs/repro_batch44.json.

Plate 44:
- make_maps44.py: maps/<variant>/44_area.png, 44_lines.png, info.json.
- run_bench44.py: runs bench/bench44_copy.py (unchanged copy of bench44.py) with bench/outlines_copy.py. Writes bench/runs/<variant>/ and summary44.json.
- noise_floor.py: noise_floor.json.
- make_synth44.py: maps_synth/ and summary_synth.json.
- pic44.py: pics/44_scale_tta_B.jpg.

Batch plates:
- make_maps_plates.py: maps_plates/{up2,up2thin,atta8}/.
- qa_plates.py, using outlines_ccomp_mask_paths.py (visual-pdf's outline copy, taking map paths): qa/{batch,up2,up2thin,atta8}/<N>/ and summary.json.
- overlay_plates.py: overlays/ (47, 50, 92, 95 crops; 46-50, 92-95 overviews; 30 and 21 with atta8).
- sample_sides.py: samples/*.jpg and .json. By-eye judgments: samples/eye_400ft.json, eye_400ft_up2thin.json.
- overlap_settings.py: overlap/batch_vs_up2.json, batch_vs_up2thin.json.

Checks, timing, diffs and logs:
- timing_summary.py: timing.json.
- test_patch.py: logs/test_patch.json.
- test_patch400.py: logs/test_patch400_patched_400.json (scratch outputs in test_run/).
- patched/, patched_400/, diffs/.
- logs/.

### check (verdict: confirmed)

- **reason:** The recommended change holds up. Averaging the area network over all 8 turns and flips (TTA x8) gives the same plate-44 scores when I regenerate it. I made the maps myself, on the CPU, by running the patched repo code itself. They score exactly what the agent reported: PQ 0.4309 for the batch against 0.4954 with TTA x8. The 6 tile-grid results also rescore exactly (mean 0.442 to 0.482, higher on all 6 grids).

The diffs apply cleanly to copies of today's files. With tta=1 the patched code gives exactly the same output as the repo code. The 8-way average is exactly turn- and flip-invariant.

The change is general and rule-based: there are no tuned numbers and nothing specific to plate 44. Training already used all 8 turns and flips. On a single pass, turning a tile changes 5.5% of the answers, and that is the variation TTA removes.

Caveats:
- The gain is clear in fold B, but fold A's gain (+0.018, 4 of 6 grids, p about 0.11) cannot be told apart from tile-grid noise.
- Everything rests on one truth plate.
- On other plates there is no clear regression, only one small joined region on plate 30.
- If the networks ever run on the CPU, TTA x8 is expensive.
- **corrected_numbers:** No headline number needs correcting. All of these are measured by me:
- Baseline (stored batch maps through my copy of the harness): PQ 0.4309, SQ 0.8524, RQ 0.5055; 23 matched, 13 merges, 13 false. Decided ground 0.4545. Fold A 0.4737, fold B 0.3852. Recall 0.5316, precision 0.7475 (green 0.7753, orange 0.0704). 0 blocks closed, 0 intact rings. Delete 32,545 px, draw 80,094 px.
- TTA x8, maps made by me on the CPU with the patched repo code: PQ 0.4954, SQ 0.867, RQ 0.5714; 26 matched, 11 merges, 10 false. Decided ground 0.5203. Fold A 0.5251, fold B 0.4623. Recall 0.5533, precision 0.7675 (green 0.7845). 1 block closed, 1 intact ring. Delete 31,002 px, draw 81,824 px.
- Over 6 tile grids (verify_grid_stats.py):
  - PQ 0.4422 (sd 0.0152) to 0.4822 (sd 0.0255). Paired gain +0.0400 (sd 0.019), higher on 6 of 6, one-sided sign-flip p = 0.016. That is the smallest p 6 grids can give, and the 6 grids are all on one plate.
  - Fold A +0.0176, higher on 4 of 6, p 0.11: not separable from noise.
  - Fold B +0.0632, higher on 5 of 6, p 0.03.
  - Recall +0.0217 (6 of 6). Precision -0.0002 (3 of 6).
  - Merges -1.17 (fewer on 5 grids, the same on one). False blocks -2.17 (fewer on 5, the same on one).
  - Note: the TTA x8 spread across grids is larger, not smaller (sd 0.025 against 0.015).
- Small corrections to the report:
  - a) The 4-way set: logs/repro_batch44.json (12:08) records the 4th transform as (1, True), but infer_lib.py now says (3, True), the transpose. It was edited at 12:59, after the a_tta4 maps were made at about 12:16. So a_tta4 was probably run with the anti-transpose, not the transpose. This does not matter for the recommendation: neither 4-set is a closed group, and on one tile they leave 2.1% of answers changed by a turn.
  - b) The scale section says '0.5 is the 200-ft training size'. The census (census.csv, training_scale) lists 43 as a 100-ft training plate and 45, 80 and 82A as 200-ft. So the networks were taught both scales. This does not change any number.
  - c) The edgenet diff is optional, but it imports TTA, turn and unturn from unet. Applied without the unet diff, edgenet would fail to import.
- Time (measured, CPU, 8 threads, machine shared): the patched run() on 44 with TTA x8 took 564 s, of which the area net was about 7 min. On the CPU, TTA x8 costs about 8 times the area pass. I did not check the GPU time (+6.4 s); I may not use the GPU.
- **diff_applies:** Yes.
- Each diff applies to copies of today's repo files with no offsets or fuzz: unet.py.diff, edgenet.py.diff, blocks_noguide.py.diff and blocks_noguide_with_400ft_option.py.diff. Checked with GNU patch (dry run, then a real apply) in verify-inference/applytest/default and applytest/up400. git apply --check also passes in a folder with no repo.
- The patched copies are byte-identical to the agent's patched/ and patched_400/ files.
- The patched default copy runs: blocks_noguide imported as a module, with only _ws stubbed and U redirected; run('44', pred_only=True) on the CPU writes both maps in 564 s, and they match the agent's GPU maps (0 changed decisions).
- With tta=1 the patched code gives exactly the same output as the original on the CPU.
- I did not run the 400-ft variant's run() myself. The agent's test_patch400 log shows it reproduces its maps on 93A.
- Caveat: edgenet.py.diff must not be applied without unet.py.diff, because it imports TTA, turn and unturn from unet.
- **overfit_risk:** Low for the recommended change; moderate for any claim about its size.
- Why low: TTA x8 has no tuned parameters and uses nothing from plate 44. It averages the network over the 8 orientations it was trained with, and it is exactly invariant by construction (checked).
- Selection effect: about 30 variants were tried on 44. But x8 was chosen by its 6-grid mean, not by its batch-grid rank, where it was 4th. It is also the principled full set, so the winner's-curse risk is small.
- Size of the gain:
  - All evidence is one plate. The 6 grids are not independent plates.
  - Fold B carries the gain (+0.063, 5 of 6). Fold A's +0.018 (4 of 6, p about 0.11) is within the tile-grid noise (fold A sd 0.029).
  - The expected benefit elsewhere is better stated as 'probably small and positive' than as +0.04 PQ.
- Other plates (truth-free, 8 plates): block share changes by 0.007 or less and short pieces fall. By eye, the changes look the same or slightly cleaner, with one joined region on plate 30.
- The optional 400-ft up2thin diff has no ground truth at all, and its PEN=3 rests on the pen-width probes made on 44. It should stay optional until Ben checks a 400-ft plate.
- **repo_clean:** Clean as far as this experiment goes.
- `git status --short tools/sanborn` prints nothing, before my checks and after.
- The sha256 of unet.py, edgenet.py and blocks_noguide.py is unchanged from the start of my check.
- Tracked changes under data/sanborn: 14 files, all for plate 82A (cufp/82A/*.pkl/json, picks22_guided/22-82A/*, and six deleted sbg/picks22/s22-82A_*.json). The files still on disk are dated 14 Nov 2026, so the changes predate today's work; they did not come from this experiment.
- No file under unet_data, picks22_guided, streetmap, cufp or tools changed after 12:05. The agent's first file is from 12:06. The newest writes there are the batch (10:44) and Ben's rail page (11:08).
- No new __pycache__ under tools.
- My own outputs are only in data/sanborn/bench_2026-11-21/verify-inference/.
- **evidence:** All my files are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-inference/.

1. Harness:
   - bench/bench44.py and bench/outlines_copy.py are byte copies (same sha256) of bench44/bench44.py and bench44/outlines_copy.py. The agent's bench/ copies are identical too.
   - `diff` against tools/sanborn/unet/outlines.py shows that only the input/output lines differ.
   - The street map 22-44.json is unchanged since 18 Nov.

2. Baseline: bench/runs/batch/bench44.json (python bench44.py --tag batch) reproduces every headline number.

3. The agent's maps rescored (rescore_agent_maps.py, rescore.json, logs/rescore_grids.log): the batch grid with TTA x8, and the 5 moved grids under both settings. All 12 runs, the baseline included, match summary44.json exactly. That is 0 mismatches over 11 keys x 3 folds x 12 runs.

4. Independent regeneration (verify_maps_patched.py):
   - The diffs were applied with GNU patch to copies in applytest/default/.
   - The patched blocks_noguide.py was imported as a real module, which imports the patched unet.py and edgenet.py; only _ws was stubbed.
   - U was redirected to maps/p_tta8_cpu/, and run('44', pred_only=True) was called on the CPU.
   - Against the agent's GPU maps (logs/area_cpu_vs_gpu.txt): area max difference 1/255 on 0.0008% of pixels, lines max 2/255; 0 changed decisions on either map.
   - outlines.json is byte-identical to the agent's run. Score: bench/runs/p_tta8_cpu/bench44.json, logs/rescore_cpu.log.

5. Code checks (verify_tta1_identity.py, logs/tta1_identity.json, on a 2800 x 2400 crop of 44, CPU):
   - Patched unet.predict_full(tta=1): area output identical to the repo's original, and its edge output too. Same for edgenet.predict_full(tta=1).
   - One-tile test of the TTA loop: with x8, the max difference after a turn or a flip is 0.0. With x1, turning a tile changes 5.5% of the answers (max |dP| 0.83). With the 4-way set, 2.1%.

6. Grid maps (verify_offset_maps.py, logs/offset_maps.json): all 20 moved-grid maps line up best at shift (0, 0). Moving the grid alone changes 1.6-2.3% of the area answers, about as much as TTA x8 does (2.29%).

7. Diffs:
   - All four apply with no offset or fuzz: GNU patch --dry-run and then a real apply on copies; git apply --check in a folder with no repo (GIT_CEILING_DIRECTORIES).
   - My patched files are byte-identical to the agent's patched/ and patched_400/. All parse.

8. Other plates:
   - I looked at three of the agent's overlays: 30_overview_atta8.jpg, 21_overview_atta8.jpg and 47_crop_west3.jpg. At overview scale they are nearly the same.
   - My own close-up crops (verify_overlay_diff.py → pics/30_diff_*.jpg, pics/21_diff_*.jpg):
     - Plate 21: TTA x8 drops mostly lot-line and railway pieces and adds a real street side (Wocher Ave). Its area map clears Neeb Rd and fills block interiors.
     - Plate 30: sides added and dropped are mixed (some lot lines on both sides). The area changes mostly fill block interiors.
     - Unshared side length: plate 30, 12% of the batch's and 11% of TTA x8's; plate 21, 14% and 11%.
   - verify_region_join.py → pics/30_join_crop0.jpg: plate 30's largest region (26% to 45% of the ground) comes from 2 batch regions joined across one street corner at about (5355, 1203) full px. It is a small real regression in the area map, but the plate still exports 35 blocks against 34, and on 44 merges fell.

9. Optional 400-ft diff: I made my own blind count of two of the agent's montages.
   - up2thin_only_vs_batch_24_s9: I count 20 of 24 on a street side; the agent 20 of 23.
   - batch_only_vs_up2thin_24_s10: I count 13-14 of 24; the agent 13 of 21.
   - So the agent's eye checks look honest. They are still not on ground truth.

## experiment: rail-rules

I copied ink_bins.py and rail_tracks.py into data/sanborn/bench_2026-11-21/rail-rules/ and redirected every output. The copies reproduce the batch exactly: same bins on 44 and 1A, and the same tracks on all 107 batch plates (107 of 107 identical). Then I added three rule-based fixes and tested five candidates on plate 44. The first half of plate 44 chose each setting and the other half checked it (bench44's folds A and B). The proposal keeps three of them:
(1) ink_bins: find the printed KEY box and allow no rail inside it.
(2) rail_tracks: drop railroad that is short and stands alone. Tracks within 60 px of each other form a group, and a group under 600 px in total is dropped.
(3) rail_tracks: streetcar join reach goes from 150 to 350 px.
Two candidates were measured and rejected: a railroad gap join (no gain on 44 at any radius) and a stricter tick angle (costs 0.5-0.7 points of railroad recall on both halves, gains nothing).

Plate 44 run as a plate that was never placed (measured, final_scores.py):
- Railroad at 10 px: precision 97.9% -> 99.5%, recall unchanged at 98.4%, false tracks 3 -> 0.
- Streetcar at 30 px: recall 83.4% -> 88.6%, precision 100% -> 98.1%, pieces 13 -> 9, gaps 7 -> 4.
- The 250 px that lowers streetcar precision lies under the word AVENUE, where Ben's own track stops (checked by eye).

1A (measured): its 5 false railroad tracks, which sit on label text, are gone. Streetcar recall at 30 px goes 69.7% -> 77.7%; its precision lower bound falls 100% -> 89.2%, all of it bridges under street names (checked by eye).

Batch, 107 plates (measured, batch_tracks.py and batch_summary.py):
- The KEY was found on 37 plates with no false finds. Bins changed only inside the KEY boxes. The 38 KEY tracks the batch made on 32 plates are removed.
- Railroad tracks fall from 4,063 to 3,105.
- Streetcar pieces fall from 1,213 to 997, with 97k px of added length.
- Plates with no rail at all are unchanged.
By eye: 35 of 36 sampled drops were false, 35 of 36 of the extra group drops were false, and all 73 tracks on the 8 plates that lose all their railroad were hooks or text. 33 of 36 sampled points on the added streetcar length were real.

The diffs are written and NOT applied. A dry run with `patch` shows they apply cleanly.

**Baseline:** Batch rules (repo ink_bins.py sha de9b79144123 = the batch's 'rules' hash; rail_tracks.py sha 16a4c4ed). All reproduced and measured with my redirected copies (run_ink_bins.py --orig, run_tracks.py --orig): bins pixel-identical to rail/runs/44_nomap_bins.png, 44_map_bins.png, 1A_bins.png; tracks identical to the batch's unet_data/N_rail_rule.json on 107 of 107 batch plates (batch_tracks.py).
- Plate 44 as a never-placed plate (no street map, no label, no Ben tracks), against rail_ben.page_2026-11-21.json (28 tracks; rail_ben.json still holds 26). Scored with final_scores.py, which wraps the rail agent's score_rail_bench.py:
  - Railroad at 10 px: recall 98.4%, precision 97.9%, 3 false tracks (672 px). 19 found, 2 partial, 0 missed; 6 tracks broken in their interior.
  - Streetcar at 30 px: recall 83.4%, precision 100%. 4 found, 3 partial; 13 pieces, 7 gaps.
  - Folds (fold_score.py): fold A railroad P 97.7 / streetcar R 88.3; fold B railroad P 98.0 / streetcar R 76.8.
- Plate 44 as the batch ran it (with the street map): railroad 98.4 / 99.5; streetcar at 30 px 82.6 / 100.
- 1A: streetcar at 30 px recall 69.7%, precision lower bound 100%; 5 false railroad tracks (453 px) on label text.
- Batch, 107 plates without 44 and 1A (batch_summary.py):
  - 4,063 railroad tracks (3.36M px) and 1,213 streetcar tracks (945k px).
  - 38 rule tracks inside the printed KEY on 32 plates.
  - No railroad on 10 plates; no rail at all on 4 (54B, 64B, 82B, 83B).
  - The rail agent's by-eye precision estimate (not mine): railroad about 85%, streetcar about 96%.

### variant V1 KEY mask (ink_bins.py, proposed)

- what: key_box() finds the printed KEY on the plate. It uses the top of the KEY box (title plus the RAILROAD / TROLLEY / WATER PIPE / SEWER samples), cut at quarter size from the KEYs of sheets 19 and 86 at run time. It matches at quarter size with a blur of sigma 1 and scales 0.95 / 1.0 / 1.05, and calls it a KEY when the mean of the two templates' scores is 0.62 or more. The box is the template's full KEY height plus 20 px. Inside the box the railroad bin and the streetcar-row mask are cleared, so the sample ink is sorted as other ink. Because the template is only the top of the box, it also catches 1B's KEY, which the plate's cut edge cuts off.
- plate 44: No KEY is found on 44 (score 0.24) or on 1A, so their bins are pixel-identical to the batch's. No change on 44, both folds.
- other plates: Measured (key_scan_top.py, batch_bins.py, batch_tracks.py):
- Threshold margin: every real KEY scores 0.71 or more (lowest is plate 36); every other plate 0.54 or less.
- Found on 37 plates: the 32 PDF sheets plus 1B, 29, 34, 37 and 76. No false finds on the other 72.
- All 37 boxes are correct by eye (key/key_check_0..3.jpg).
- Compared with the batch's bins, 0 px differ outside the KEY boxes. Inside them, 57.7k px of railroad-bin ink and 59.7k px of streetcar-bin ink move to other bins.
- The 38 batch tracks inside a KEY (21 railroad, 17 streetcar, 32 plates) are all gone, and no rail track is left inside a KEY.
- Side effect: 3 tracks at the box edges change, about 80 px in all. One real track on 34 is shortened by 10 px where it runs into the KEY frame.
- time: key_box takes about 1.1-1.4 s per plate, plus 2.3 s on the first call to build the templates (measured). A whole ink_bins run is 26 s on 44 and about 55-70 s per PDF sheet on a shared CPU.

### variant V2 small-group railroad filter (rail_tracks.py drop_alone, proposed: group, 600 px / 60 px)

- what: After tracing, railroad tracks that lie within 60 px of one another are linked into groups. A group shorter than 600 px in total is dropped. This is a group version of the rail agent's F1, which looked at one track at a time.
- plate 44: Held-out sweep, sweep44.py (sweep/sweep44.txt). The grid had single and group forms, short 300-1200 px, near 30-150 px.
- Every setting from 300 to 900 px (and 1200 px with near 60 or more), in both forms, gives identical results on 44:
  - railroad at 10 px precision 97.9 -> 99.5;
  - fold A 97.7 -> 99.6;
  - fold B 98.0 -> 99.3;
  - recall stays 98.4 on the whole plate and both folds;
  - false tracks 3 -> 0 (2 in A, 1 in B).
- Single 1200/30 loses recall (fold B 98.4 -> 94.4).
- The pre-set tie-break (the setting nearest the batch wins) picked single 300/30 on both folds. That pick held on the other fold in each direction: B precision 98.0 -> 99.3, A 97.7 -> 99.6, no recall loss.
- So 44 cannot tell single from group, or 300 from 900 px. I chose group 600/60 on evidence from outside 44 (next column).
- With the street map, as the batch ran 44: no change (99.5% already).
- 1A (not used for choosing): group removes all 5 false text tracks; single 600/60 removes 0; single 300/30 removes 1.
- other plates: Measured counts (batch_tracks.py, batch_summary.py) and by-eye checks of random samples (sample/eye_labels.json):
- Group 600/60 drops 934 railroad tracks (150k px, 4.5% of railroad length) on 91 plates. Railroad tracks fall from 4,039 to 3,105 after the KEY change.
- Single 600/60 would drop 219 tracks (56k px). By eye, 35 of 36 sampled drops are false and 1 is unsure.
- The 715 extra tracks only the group form drops: 35 of 36 sampled are false, 1 unsure (60A, hatched double line at the paper edge).
- Single 300/30 (the tie-break pick): its 133 extra drops beyond single 600/60 are 34 of 36 false and 1 real (plate 52, a short piece between real tracks). That is worse than group.
- 8 plates lose all their railroad (14, 15B, 18A, 18B, 54A, 68, 7, 71). All 73 tracks on them are lot lines with hook marks, lot or house numbers, or lettering by eye (sample/lost_all_railroad.jpg).
- Plates with no rail at all are unchanged.
- time: Under 1 s per plate (not timed separately).

### variant V3 streetcar reach 350 px (rail_tracks.py TRACKS car_reach, was 150)

- what: Dashes are joined across gaps of up to 350 px. The direction and lateral tests are unchanged (25 degrees, 18 px).
- plate 44: Held-out sweep, sweep44.py:
- Fold A chose 500; fold B chose 350.
- B's pick (350), read on held-out A: streetcar F1 at 30 px 93.8 -> 96.4, recall 88.3 -> 93.0, precision stays 100.
- A's pick (500), read on held-out B: F1 86.9 -> 88.7, recall 76.8 -> 82.8, precision 100 -> 95.4.
- I took the smaller of the two picks.
Whole plate (final_scores.py):
- At 30 px: recall 83.4 -> 88.6, precision 100 -> 98.1, pieces 13 -> 9, gaps 7 -> 4, tracks broken inside 4 -> 3.
- At 10 px: recall 80.5 -> 86.6, precision 97.8.
- With the street map: recall 82.6 -> 87.8.
- Against the rail agent's scratch truth with Ben's 5 gaps under street names bridged: recall 75.3 -> 81.6 at 100% precision.
- The only stretch off Ben's tracks (250 px) is under the word AVENUE (explore/far_44_r350.jpg).
1A:
- At 30 px: recall 69.7 -> 77.7, found / partial / missed 5/4/1 -> 7/2/1, pieces 13 -> 8.
- Precision lower bound 100 -> 89.2. All 3 stretches off his checked tracks are under labels or street names (explore/far_1A_r350.jpg).
- other plates: Measured (batch_tracks.py):
- Streetcar pieces fall from 1,196 to 997, fewer on 72 plates.
- Streetcar length rises from 941k to 1,047k px; the length added off the batch's tracks is 97k px.
By eye (sample/car350_added.jpg): of 36 points sampled uniformly by length on the added length, 33 are real, 2 false (a row of lot numbers on 31, a join across a rail yard on 41) and 1 unsure.
- time: Negligible.

### variant Alternative: streetcar reach 500 (fold A's choice)

- what: As V3 with a 500 px reach.
- plate 44: - Whole plate at 30 px: recall 91.4, precision 95.9, pieces 7, gaps 3.
- Against the bridged truth: recall 86.1 at 100% precision.
- Fold B, held out: precision 95.4.
- 1A: recall 79.1, precision lower bound 80.0.
- The precision loss on 44 and 1A is all under street names up to 500 px; at 600 px a wrong diagonal join appears on 44 (explore/far_44_r600.jpg).
- other plates: - Measured: 864 pieces, 169k px added off the batch's tracks.
- By eye, on the length 500 adds beyond 350 (sample/car500_extra.jpg): 31 of 36 points real, 1 false, 4 unsure. Most real points lie under street names.
- Use 500 only if Ben wants streetcar tracks drawn through the names (finding R4).
- time: None

### variant Rejected: railroad gap join

- what: Join two free railroad ends within 10-90 px that face each other within 25 degrees. The code is kept in variants/rail_tracks_sweep.py.
- plate 44: - No radius changes the 6 tracks broken in their interior, on either fold.
- From 20 px up, railroad precision drops slightly (fold A 97.7 -> 97.5).
- Neither fold chose it. The two breaks at the paper crease (x about 5350) are side-by-side offsets of about 15 px, not gaps, so the rule cannot reach them.
- other plates: Not run.
- time: None

### variant Rejected: stricter tick angle (RAIL across 0.6 / 0.55 / 0.45, batch 0.7)

- what: ink_bins requires a tick's two stroke ends to lie more squarely across the line.
- plate 44: Measured (across44.py; the 0.55 and 0.45 bins are the rail agent's):
- 0.6: no change at all.
- 0.55: railroad recall at 10 px 98.4 -> 97.9 (fold A 97.8, fold B 98.0); with the filter, precision is unchanged at 99.4-99.5.
- 0.45: recall 97.7.
- 1A: no change; the 5 text tracks stay.
- other plates: Not rerun. The rail agent measured that it removes 37-82% of rule railroad on hook plates, but also about 1% of real yard track. The group filter now removes most of the short hook rows without this recall cost.
- time: None

**Recommended:** Adopt V1 + V2 + V3, exactly as in diffs/rail_rules.diff: KEY mask, small-group railroad filter (group, 600 px / 60 px) and streetcar reach 350.

Expected gain over the batch baseline:

Plate 44 run as never placed (measured, final_scores.py):
- Railroad precision at 10 px 97.9% -> 99.5%, recall unchanged at 98.4%, false tracks 3 -> 0.
- Streetcar recall at 30 px 83.4% -> 88.6%, precision 100% -> 98.1% (the 250 px lost is under the word AVENUE), pieces 13 -> 9.
- Streetcar F1 at 30 px 90.9 -> 93.1. Held out: fold A 93.8 -> 96.4; fold B 86.9 -> 88.7.

1A (measured):
- False railroad tracks 5 -> 0.
- Streetcar recall at 30 px 69.7% -> 77.7%, found tracks 5 -> 7.

Batch (measured counts, by-eye judgement):
- Railroad tracks for Ben to check fall from 4,063 to 3,105. About 97% of the 934 group drops looked false in the samples.
- The 38 KEY tracks on 32 plates are gone.
- Streetcar pieces fall from 1,213 to 997, with 97k px of mostly real added length.

Estimated, not measured: batch railroad precision by length rises from about 85% to about 89%. That is the rail agent's 85% sample, minus about 156k px of mostly false track that the KEY mask and the group filter remove.

Apply from the repo root with `git apply data/sanborn/bench_2026-11-21/rail-rules/diffs/rail_rules.diff` (the `patch` dry run passed), then re-run ink_bins and rail_tracks on the plates. Before keeping reach 350 rather than 500, ask Ben whether streetcar tracks should run on under street names (finding R4).

**Regressions:** - Streetcar precision against Ben's literal tracks falls:
  - 44: 100% -> 98.1% (fold B 95.4%);
  - 1A lower bound: 100% -> 89.2%.
  Every such stretch I looked at on 44 and 1A lies under a street name or label, where Ben's own tracks stop. If his convention stays "stop at names", he will trim those bridges. On the batch, 2 of 36 sampled added points were false: a row of lot numbers on 31, and a join across the rail yard on 41.
- The group filter can delete real short, isolated railroad: a spur cut by the plate edge, or a short siding far from other track. None of the 145 drops I looked at was real, and 2 were unsure (29 at a paper cut-out, 60A at the paper edge). As an estimate, perhaps up to about 3% of the 934 drops (up to about 25 tracks) are real.
- Plates with no railroad rise from 10 to 18: 14, 15B, 18A, 18B, 54A, 68, 7 and 71 now show none. By eye their 73 batch tracks were all false. A real track on such a plate would now be missed entirely.
- The KEY box padding (20 px) trimmed 10 px off one real track on 34 that runs into the KEY frame. 2 other tracks at the box edges changed by under 50 px.
- KEY detection depends on cufp/22-19.jpg and cufp/22-86.jpg existing; if either is missing, key_box returns None and the old behaviour returns. The threshold margin was measured on these 109 plates only.
- Plate 44's own errors had been seen before: the rail agent proposed 600/60 and 300-400 px after looking at them. The held-out folds settle only the reach. For the filter threshold, 44 cannot tell 300 px from 900 px, or single from group. That choice rests on 1A (5 false text tracks) and on the by-eye samples, each one look at 36 tiles.
- Not fixed:
  - railroad tracks broken at switches and at the paper crease (still 6 of 21 broken inside on 44);
  - the double-line siding (73%) and the crossover (66%);
  - hook rows longer than 600 px or near real track (the rail agent's 85% sample points mostly fell on longer tracks, so most false railroad length probably remains);
  - the streetcar bin's 15% loss under lettering;
  - untick-marked rail on 83B and 95;
  - 400-ft plates;
  - the KEY mask clears only rail bins, so the KEY's other sample symbols still go to the other bins.

**Diff:** C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/rail-rules/diffs/rail_rules.diff (both files, against the repo's tools/sanborn/unet/ink_bins.py sha de9b7914... and rail_tracks.py sha 16a4c4ed..., recorded in diffs/base_sha256.txt). Also per file: diffs/ink_bins.diff and diffs/rail_tracks.diff. NOT applied; `patch --dry-run -p1` from the repo root applies cleanly. Regenerate with make_diffs.sh.

**Files:** All in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/rail-rules/ (second copy of every script, the proposed files and the diffs in _second_copy/). Nothing was written anywhere else. A check after the runs shows no file in unet_data, picks22_guided, streetmap, cufp or tools changed, and both repo hashes are unchanged.

Proposed code and copies:
- proposed/ink_bins.py, proposed/rail_tracks.py: the diff targets.
- orig/: byte-identical copies of the repo files.
- variants/rail_tracks_sweep.py: the sweep version with the rejected railroad join.

Runners (outputs guarded so they can only write inside rail-rules):
- run_ink_bins.py: imports the module, refuses any write outside rail-rules, and has a --nomap option.
- run_tracks.py.
- batch_bins.py: KEY plates, compared with the batch's bins.

Scoring:
- score_rail_bench.py: an unchanged copy of the rail agent's scorer.
- fold_score.py: scores per fold, using bench44's folds A and B; check_fold_score.py shows 0 mismatches against the whole-plate scorer.
- sweep44.py: the held-out sweep; output in sweep/sweep44.txt and .json.
- final_scores.py: output in final/final_scores.json and .log, plus pictures final/44_nomap_*.jpg and final/1A_*.jpg.
- across44.py: output in across/.

Batch:
- batch_tracks.py: output in batch/tracks_compare.json, plus batch/tracks/N_rail_rule.json for all 107 plates.
- batch_summary.py: output in batch/summary.json.
- batch/N_bins.png: proposed bins for the 37 KEY plates; batch/bins_compare.json.

KEY:
- key_scan.py, key_scan_top.py: output in key/key_scan*.json and .jpg.
- key_check.py: output in key/key_check_0..3.jpg.

By-eye checks:
- sample_batch.py, montage.py, lost_all_view.py: output in sample/*.jpg.
- sample/eye_labels.json: my labels for every sample tile.
- false_stretches.py, explore_breaks.py: output in explore/.

### check (verdict: confirmed)

- **reason:** I re-ran every headline number for the three proposed rail-rule changes with my own copies of the code: the KEY mask, the small-group railroad filter (600 px / 60 px) and streetcar reach 350. That covers plate 44 run as never placed (whole plate and folds A/B), plate 44 with its street map, plate 1A, and all 107 batch plates. I used my own patched copies and my own runners, and scored twice: with the agent's scorer and with a separate one I wrote. Every number came out the same, give or take 0.1 point between the two scorers.

The diff applies cleanly to copies of the current repo files with both `patch -p1` and `git apply`. The patched copies match the agent's proposed/ files byte for byte, and they run. The KEY detector picks out the same 37 plates. Its scores on all 109 plates match the agent's to 3 decimals, with a wide margin: the lowest real KEY scores 0.714 and the highest non-KEY plate 0.538. Bins change only inside the KEY box (checked on 36, 1B and 34). Plate 25, which has no KEY, is unchanged.

Overfitting risk is low for the KEY mask and the railroad filter, and moderate for the exact reach value (details under overfit_risk). By eye I found no real track removed in the agent's overlays, in my 26-tile check on the 400-ft sheets, or on the 68 crop.

What I would flag:
(a) The streetcar precision loss is real, but every stretch I looked at lies under a street name. Whether those bridges count as right or wrong is Ben's convention to decide, which the agent already says.
(b) The report says 1A was "not used for choosing", yet the group-versus-single choice also cites 1A. The main evidence for that choice is the batch by-eye samples.
(c) The claim that batch railroad precision rises from about 85% to about 89% is an estimate built on the rail agent's earlier sample. I did not measure it.
(d) Applying the patch changes the ink_bins.py hash that run_plates.py uses to decide what to skip. A plain run_plates.py run would then redo every plate.
(e) Small robustness gap in key_box: if one template scan cannot be read, it quietly runs with one template or none.

The repo is untouched: no files changed in tools/sanborn, and the only tracked changes under data/sanborn are 82A files from 14 Nov, before this experiment.
- **corrected_numbers:** No corrections needed. Everything below was measured with my own runs.

Plate 44 as never placed, truth = rail_ben.page_2026-11-21.json (28 tracks):
- Railroad at 10 px: R 98.4 / P 97.9 -> 98.4 / 99.5; false tracks 3 (672 px) -> 0.
  - Fold A: P 97.7 -> 99.6. Fold B: P 98.0 -> 99.3.
  - Found / partial / missed: 19 / 2 / 0. Broken inside: 6, both before and after.
- Streetcar at 30 px: R 83.4 / P 100 -> 88.6 / 98.1; F1 90.9 -> 93.1.
  - Pieces 13 -> 9, gaps 7 -> 4, broken inside 4 -> 3.
  - Fold A: F1 93.8 -> 96.4 (R 88.3 -> 93.0, P 100). Fold B: F1 86.9 -> 88.7 (R 76.8 -> 82.8, P 100 -> 95.4).
- Streetcar at 10 px: R 80.5 -> 86.6, P 97.8.
- Reach 500 instead: R 91.4 / P 95.9. Reach 300: R 87.0 / P 100, the same whole-plate F1 (93.1) as 350.

Plate 44 with its street map: railroad 98.4 / 99.5 both ways; streetcar R 82.6 -> 87.8, P 100 -> 98.1.

Plate 1A:
- 5 false railroad tracks -> 0. The agent says 453 px; I get 454 px, a rounding difference.
- Streetcar at 30 px: R 69.7 -> 77.7, P (a lower bound) 100 -> 89.2. Found / partial / missed 5/4/1 -> 7/2/1.

Batch, 107 plates (vbatch_tracks.py):
- My orig copy reproduces the batch's tracks on 107 of 107 plates; my patched copy matches the agent's tracks on 107 of 107.
- Railroad: 4,063 tracks / 3.364M px -> 3,105 / 3.207M px (157k px removed).
- Streetcar: 1,213 / 945k px -> 997 / 1,047k px. Net +102k px; the agent's 97k is length added away from the batch's tracks, a different measure.
- Plates that lose all railroad: 14, 15B, 18A, 18B, 54A, 68, 7, 71. Plates with no rail at all (54B, 64B, 82B, 83B) are unchanged.

KEY detection: found on 37 plates, lowest real KEY 0.714 (plate 36), highest non-KEY plate 0.538 (plate 25).
- **diff_applies:** Yes.

- `patch -p1 --dry-run` and the real `patch -p1` apply cleanly to copies of the current tools/sanborn/unet/ink_bins.py (sha de9b7914...) and rail_tracks.py (sha 16a4c4ed...) in verify-rail-rules/applytest/.
- `git apply --check` and `git apply` also work on a second copy in applytest_git/, with the same result.
- The patched copies are byte-identical to rail-rules/proposed/.
- Both patched copies run:
  - ink_bins (via its --save path) on 44 (with and without the map), 1A, 36, 1B, 34 and 25.
  - rail_tracks as a command-line script in a sandbox folder with copied bins. Its run() output equals tracks().
- The repo's own files still have the base hashes.
- **overfit_risk:** Low for the KEY mask and the railroad filter; moderate for the exact streetcar reach.

- **KEY mask:** a fixed feature of the atlas. It finds nothing on 44 or 1A, so they cannot have shaped it. The 0.62 threshold was set by looking at all 109 batch plates, but the gap is wide (0.714 vs 0.538) and both templates must agree.
- **Group filter:** every setting from 300 to 900 px, in both the group and single forms, gives the same result on 44. So 44 did not choose the 600/60 setting; the batch eye samples did.
  - On 44 the gain rests on only 3 false tracks (2 in fold A, 1 in fold B). It holds in each fold.
  - Ben's new 314 px spur survives because it is linked to the main track.
  - The filter counts pixels, not feet, so it is stricter in ground terms on the 400-ft sheets. Even so, my 26-tile check there found no real track dropped.
  - Residual risk: a real short spur that stands alone, for example one cut off by the paper edge, would be dropped.
- **Streetcar reach:** the folds disagree on the value (A picked 500, B picked 350). Both held-out readings still improve: A 93.8 -> 96.4, B 86.9 -> 88.7. On the whole plate, reach 250, 300 and 350 all give F1 93.1, but only 350 costs precision. So 44 shows that a longer reach helps, but does not pin down 350.
  - 1A's precision is only a lower bound (Ben's rail there is incomplete), and its F1 is flat from 300 to 350.
  - The real question is Ben's convention for names printed over the track (finding R4).
- **repo_clean:** Yes, clean.

- `git status --short tools/sanborn` is empty. ink_bins.py and rail_tracks.py still have the base hashes (de9b7914..., 16a4c4ed...).
- Under data/sanborn the only tracked changes are 82A files (cufp/82A/*, picks22_guided/22-82A/*) with mtimes of 14 Nov, plus 6 deleted sbg/picks22/s22-82A_[a-f].json. Both predate this experiment.
- No file under data/sanborn, tools or docs outside bench_2026-11-21/ has changed since 12:00 today.
- rail_ben.json (26 tracks) and edges_ben.json still carry their 18 Nov mtimes.
- All my writes are inside bench_2026-11-21/verify-rail-rules/.
- **evidence:** All scripts and outputs are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/verify-rail-rules/:

- **vrun_ink_bins.py**: my own guarded runner for orig/ (a plain copy of the repo files) or patched/ (that copy with rail_rules.diff applied).
  - Bins for 44 (as never placed, and with the map) and 1A are pixel-identical between orig and patched (0 px differ).
  - They are also identical to rail-rules/runs/* and to the rail agent's rail/runs/* bins.
- **vscore44.py**: scores with their fold_score/score_rail_bench and with my own exact-distance scorer. Output: score/vscore44.log and score/vscore44.json.
  - My retraced tracks equal the agent's final/*_rail_rule.json for batch and proposed on 44 (with and without the map) and on 1A.
  - Ben's 314 px spur at (3766,2622)-(3464,2698) is covered 100% at 10 px both before and after. The filter keeps it because it is linked to the main track.
  - The 3 tracks dropped on 44 and the 5 on 1A have 0% of their length within 10 px of Ben's railroad.
- **vkey_scan.py** (keyscan/vkey_scan.json): 109 plates, my score function equals theirs on 109 of 109, and the patched key_box decision equals mean >= 0.62.
- **vkey_bins.py** (keyplates/): patched ink_bins re-run on 36, 1B, 34 and 25.
  - On 36, 1B and 34, 0 px differ from the batch's bins outside the KEY box, and the bins match the agent's batch/N_bins.png exactly.
  - Inside the box: 2,410, 3,824 and 1,212 rail px are cleared.
  - Plate 25 is identical to the batch.
  - By eye, 34_key.jpg and 1B_key.jpg show the boxes are right. On 34 a real track touching the frame is clipped by a few px.
- **sandbox_run/**: the patched rail_tracks.py run as a command-line script on copies of the bins. It writes the same tracks as tracks(); 4 s on plate 44.
- **vbatch_tracks.py** (vbatch/vbatch.json): the batch totals above.
- **Overlays I looked at myself**:
  - rail-rules/sample/drop_g_extra.jpg: 36 tiles, all lot lines with hook marks or number rows. Tile 25 on 60A is unclear.
  - sample/lost_all_railroad.jpg: all 73 look false.
  - sample/car350_added.jpg: mostly real joins through crossings and under names. Tile 9 (lot numbers, plate 31) and tile 10 (across a rail yard, plate 41) are false.
  - explore/far_44_r350.jpg: the 250 px is under the word AVENUE.
  - explore/far_1A_r350.jpg: under '15', AVENUE and ELM.
  - final/1A_batch.jpg vs final/1A_proposed.jpg: the false tracks on the BRANCH and SUBDIV'N lettering are gone.
- **My own checks**:
  - scale/drops_400ft.jpg (vscale_drops.py): all 26 filter drops on the 400-ft sheets 47, 49 and 50 are lot lines, dimension figures, the scale bar or the Sanborn lettering.
  - keyplates/68_road_crop.jpg: the dropped piece on 68 is a lot front line with dimension figures, not track.

## completeness critic

I'm the completeness critic. I re-ran the key plate-44 claims myself, on the CPU and only inside data/sanborn/bench_2026-11-21/critic/. Nothing was trained and nothing in the repo changed: no file newer than my start exists under tools/, unet_data, picks22_guided, streetmap, cufp or the other bench folders I checked, and the two repo files still have SHA bccc2b34 and 3700ff13. My copies reproduce the agents' headline numbers exactly: outline-quality PQ 0.543, outline-nesting recall 0.5465, and 44 resized to 200-ft size PQ 0.1242.

What is new from my checks (all measured on plate 44 unless stated):

1. **The marker gain is real but smaller than reported.** The inference agent made 6 equally valid tile grids of the same networks. Over those 6 grids, outline-quality's change (markers, green gate, rings) raises PQ by +0.068 on average (sd 0.029, range +0.035 to +0.112), and it gains on all 6. The reported +0.112 is the luckiest of the 6. Nearly all the PQ gain is in fold B (+0.111). Fold A gains only +0.029 and loses on 1 of 6 grids. The recall gain is very steady (+0.079, sd 0.005). Ben's delete length rises on every grid (+1.7k px).

2. **The two cheap fixes for merges do not add up.** Averaging the area network over 8 turns and flips gains +0.040 PQ on its own (6 of 6 grids). On top of the markers it gains nothing: -0.005, better on only 2 of 6 grids. Both fix the same merges.

3. **The proposed diffs cannot be applied together.** Each applies alone. outline-quality then outline-nesting fails every hunk in both files. outline-nesting then outline-quality fails 4 of 6 hunks in outlines.py. The inference blocks_noguide diff fails one hunk on top of either. So the combined pipeline has never been run.

4. **The markers do not help the 200-ft alleys.** On 60B and 66 they add 1 block each, while visual-cut counted about 27 missed alleys on 60B and at least 6 on 66. On one of the missed 60B alleys, which I looked at, the line network marks 1.4% of the strip and the area network calls 90% of it block. Neither network sees it, so no outline-step change can fix it.

5. **The biggest group has no held-out truth.** Plates at 200 ft hold 66% of the blocks exported on the unplaced plates and 53% of their ground. Plate 44 is a 100-ft plate. The census's 'ok' label for the 39 cut 200-ft plates is weak: 60B is labelled 'ok' but misses most of its alleys.

6. **One plate gives a wide range.** The batch's PQ on 44 has a 95% interval of 0.32-0.53 when Ben's blocks are resampled. The tile-grid spread is sd 0.015 for the whole plate and about 0.03 per fold. So bench44's rule ('+0.03 and both folds gain') is only about one standard deviation per fold.

**Second truth plate:** plate 90 (200-ft PDF sheet), checked completely, blocks and rail. It tops my candidate ranking. It tests the two big fixes that have no truth (the map mask and nested blocks: 1 to 45 blocks) and the 200-ft scale. It has enough blocks to score, rail with a KEY, water and open land, and curved streets. The job is about the size of 44.

**Retraining order:**
1. Seed, keep-best or EMA, frozen labels and no 255 squares, trained twice to measure how much one training differs from the next.
2. Scale and pen-width augmentation, with warps.
3. Relabel 1922 alleys on the training plates (not on the list, but needed for the alleys).
4. Out-of-fold area maps.
5. Hue last.

**Numbers**

MEASURED by me (scripts in data/sanborn/bench_2026-11-21/critic/):

Reproduction (run_grid.py and harness/bench44.py, an unchanged copy of bench44.py):
- outline-quality on the batch maps: PQ 0.543, recall 0.6097, precision 0.7596, green 0.8414, 6 blocks closed, delete 33,107 px, draw 70,178 px.
- outline-nesting on the batch maps: PQ 0.4309, recall 0.5465, precision 0.7518, delete 32,669 px, draw 77,429 px.
- 44 with the area net at the 200-ft size (a_s0.5): PQ 0.1242, 5 matched.
- Every dark line made 2 px thicker (pen_min3): PQ 0.0289, 1 matched.

Paired over the 6 tile grids (run_grid.py, then paired_stats.py, giving paired_stats.json). The baseline is the repo's outline step on each grid's maps (inference/bench/runs). Each line gives the mean change, its sd, and how many of the 6 grids gain.
- outline-quality against the repo step, tta1 grids:
  - PQ 0.442 to 0.511: +0.068, sd 0.029, range +0.035 to +0.112, 6 of 6.
  - Fold A +0.029 (5 of 6); fold B +0.111 (6 of 6).
  - Matched blocks +4.3 (6 of 6).
  - Recall +0.079 (sd 0.005, 6 of 6). Precision +0.008 (5 of 6). Green precision +0.060 (6 of 6).
  - Ben's blocks closed 0 to 5 (range 2-8).
  - Draw length -9.7k px; delete length +1.7k px (worse on 6 of 6).
- outline-nesting against the repo step, tta1 grids:
  - PQ +0.000 on every grid.
  - Recall +0.012 (6 of 6); precision +0.001.
  - Delete +395 px (worse on 6 of 6); draw -1.8k px.
- Area TTA x8 against tta1, repo step: PQ +0.040 (sd 0.019, 6 of 6; fold A 4 of 6); recall +0.022.
- outline-quality with TTA x8 against outline-quality without it: PQ -0.005 (2 of 6); recall +0.009 (6 of 6); green +0.013.
- outline-quality with TTA x8 against the repo step at tta1: PQ +0.063 (6 of 6).

Block bootstrap (paired_stats.py; 4,000 resamples of Ben's 55 blocks, false blocks held fixed, batch tile grid):
- Batch PQ 0.431, 95% interval 0.319-0.530.
- Change in PQ against the batch:
  - outline-quality: +0.113 (95% interval +0.057 to +0.181);
  - area TTA x8: +0.065 (+0.023 to +0.120);
  - outline-quality with TTA x8: +0.092 (+0.045 to +0.152);
  - guided chain: +0.161 (+0.034 to +0.295).

Diff check (diffcheck.sh, giving diffcheck_result.txt; on fresh copies of the repo files, SHA bccc2b34 / 3700ff13):
- Each of the 4 diffs applies alone.
- outline-quality then outline-nesting: 2 of 2 hunks fail in outlines.py and 2 of 2 in blocks_noguide.py.
- outline-nesting then outline-quality's outlines.py: 4 of 6 hunks fail.
- The inference blocks_noguide diff fails hunk 3 on top of either.

200-ft cut plates (plates_200ft.py, giving plates_200ft.json):
- My copy of the repo step reproduces the batch record: 60B 39 blocks / 267 sides; 66 105 / 766.
- outline-quality: 60B 40 blocks; 66 106 blocks.
- 60B missed alley in block 67 (x 2155, y 1150-1700): the line network marks 1.4% of the strip (P > 0.5), and the area network calls 89.8% of it block.

Group shares of the 104 unplaced plates (truth_candidates.py, from census.csv and outline-nesting/measure.csv). Shares of blocks after the nesting fix / of ground:
- cut 200 ft: 0.397 / 0.243;
- PDF 200 ft: 0.259 / 0.286;
- cut 100 ft: 0.319 / 0.063;
- PDF 400 ft: 0.022 / 0.383;
- cut 400 ft: 0.003 / 0.025.

Plate 90 (truth_candidates.py):
- Batch 1 block, 45 after the nesting fix; 455 editor lines.
- Largest block 18.5% of the map ground.
- Rule tracks: 19 railroad, 16 streetcar. KEY present. Tint 0.105.
- Ranking score 5.42; then 27 (5.22) and 23 (4.94); 30 is 4th (4.73).

Rail truth file (read-only check): rail_ben.json still holds 26 tracks, saved 18 Nov. rail_ben.page_2026-11-21.json holds 28, including 3 railroad pieces at the spur.

ESTIMATED / JUDGEMENT:
- The ranking weights in truth_candidates.py are my judgement.
- 'About the size of 44' for checking plate 90 is an estimate (45 blocks and 455 lines against 55 and 495).
- The retraining order is my reasoning from the measured numbers above, not a measurement.

### K1 [high] The marker gain on 44 is +0.07 PQ averaged over tile grids, not +0.11; almost all of it is in fold B

- **kind:** measurement
- **plates:** 44 (6 tile grids)
- **evidence:** run_grid.py and paired_stats.py. outline-quality against the repo outline step on the same maps, over the 6 tile grids the inference agent made:
- PQ +0.068 (sd 0.029, range +0.035 to +0.112), gaining on 6 of 6.
- The batch's grid gives +0.112, the largest of the 6.
- Fold A +0.029, gaining on 5 of 6; fold B +0.111.
- Recall +0.079 (sd 0.005). Green precision +0.060. Blocks closed 0 to 5 (range 2-8).
- Delete length +1.7k px, worse on all 6.
Block bootstrap on the batch grid: +0.113, 95% interval +0.057 to +0.181.
- **impact:** The expected PQ gain falls from +0.112 to +0.068. The fold-A gain is about one standard deviation of grid noise.
- **fix:** Adopt the markers; the gain is real on 44. Quote it as about +0.07 ± 0.03 PQ.

Change bench44's rule for judging a change on 44: run it on all 6 tile-grid map pairs (in inference/maps/{batch,off1-5}_tta1) and report:
- the mean paired gain and its sd;
- how many of the 6 grids gain, per fold.
The 6 runs take about 6 minutes on the CPU.
- **effort:** small

### K2 [high] Area TTA x8 and the markers do not stack

- **kind:** measurement
- **plates:** 44 (6 tile grids)
- **evidence:** paired_stats.py:
- TTA x8 alone: PQ +0.040 (6 of 6).
- On top of outline-quality: PQ -0.005 (better on only 2 of 6), recall +0.009 (6 of 6), green precision +0.013.
- outline-quality with TTA x8 against the repo step: PQ +0.063, the same as outline-quality alone (+0.068).
Both fix the same merges.
- **impact:** This avoids claiming about +0.04 PQ twice.
- **fix:** If the markers are adopted, make AREA_TTA = 8 in inference/diffs/blocks_noguide.py.diff optional, or drop it. It buys about 1 point of recall for about 6 times the area-net time. Do not count both gains.
- **effort:** trivial

### K3 [high] The outline-step proposals conflict as diffs; the combined pipeline was never run

- **kind:** failure-mode
- **plates:** all
- **evidence:** diffcheck.sh, giving diffcheck_result.txt, on fresh copies of the repo files:
- Each of the 4 diffs applies alone.
- outline-quality then outline-nesting: every hunk fails (2 of 2 in outlines.py, 2 of 2 in blocks_noguide.py).
- outline-nesting then outline-quality: 4 of 6 hunks fail.
- The inference blocks_noguide diff fails hunk 3 on top of either.
What each gives on PDF sheet 90:
- outline-quality alone: 41 blocks, with one piece in the KEY box;
- nesting plus the map mask: 45 blocks.
So the merge needs the map mask from one diff and the markers from the other. Nobody has measured the combination, apart from my outline-quality plus TTA check.
- **impact:** Without the merge none of the gains reaches Ben's editor.
- **fix:** Write one merged outlines.py and blocks_noguide.py:
- from outline-quality: markers, rings and the green gate;
- from outline-nesting: the map_area mask on PDF sheets, hole polygons with HOLE_PARENT, and the QA flags;
- step 4 with both filters;
- TTA optional.
Re-measure it on:
- the 6 grids of 44;
- the 104-plate counts (outline-nesting's measure.py);
- the overlays of 90, 30, 60B and 64A.
Run the outline step only (CPU). Ben approves before anything is written into unet_data, because that overwrites the batch's outputs.
- **effort:** medium (a day)

### K4 [high] Missed alleys at 200 ft have no fix: neither network sees them, so the markers cannot help

- **kind:** failure-mode
- **plates:** 60B, 66 measured; probably most of the 36 unplaced cut 200-ft plates (estimate)
- **evidence:** plates_200ft.py:
- outline-quality adds 1 block on 60B (39 to 40) and 1 on 66 (105 to 106).
- visual-cut counted by eye about 27 of about 30 mid-block alleys missed on 60B, and at least 6 on 66.
- On the missed alley in 60B block 67 (x 2155, y 1150-1700), the line network marks 1.4% of the strip (P > 0.5) and the area network calls 89.8% of it block (plates/60B_alley_67_scan_lines_area.jpg).
- At 200 ft a 10-ft alley is about 15 px at full size and 7 px at the area net's half size. SEED_S = 8 can never seed it.
- **impact:** On these plates alleys are the most common merge. Cut 200-ft plates hold about 40% of the blocks exported on unplaced plates.
- **fix:** No outline-step change can fix this. It needs the retraining items:
- relabel the 1922 alleys and streets that the training labels call block (review labels-5 / M4);
- then add a skeleton-recall loss on the street class;
- add pen and scale augmentation.
Measure it on a 200-ft truth plate (K6).
- **effort:** large (labels plus retraining)

### K5 [high] No held-out truth at 200 ft, the scale of 66% of the exported blocks; the census's 'ok' label is weak there

- **kind:** measurement
- **plates:** 63 plates at 200 ft (39 cut, 24 PDF)
- **evidence:** truth_candidates.py (census.csv plus outline-nesting/measure.csv). Shares of the 104 unplaced plates:
- 200-ft plates: 65.6% of blocks after the nesting fix, 52.9% of ground;
- 100-ft plates: 31.9% of blocks, 6.3% of ground.
Plate 44 is at 100 ft (3.0 px per ft). The 200-ft plates are at 1.5 px per ft, and only the training plates 45, 80 and 82A are at that scale.
The census judged 0 of 39 cut 200-ft plates bad, but 60B is labelled 'ok' and misses most of its alleys (K4).
- **impact:** Today the quality of most of the batch is unmeasured.
- **fix:** Make the second truth plate a 200-ft plate (K6). Until then, report every 44 result as '100-ft plate only'.
- **effort:** Ben's time

### K6 [high] Second ground-truth plate: 90, checked completely (blocks and rail), then a partial alley check on a cut 200-ft plate

- **kind:** proposal
- **plates:** 90 first; 60B or 66 (partial); a 400-ft district later
- **evidence:** truth_candidates.py ranking. 90 scores 5.42, ahead of 27 (5.22, cemetery mis-masked by map_area) and 23 (4.94). 30 is 4th (4.73) but has only 7 railroad and 2 streetcar rule tracks.
Plate 90:
- PDF sheet at 200 ft. The batch exported 1 block with 3 sides; nesting plus the map mask gives 45 blocks and 455 editor lines. The printed block numbers run to about 41.
- Largest block after the fix: 18.5% of the map ground.
- 19 railroad and 16 streetcar rule tracks, and a KEY.
- Mill Creek, the old canal bed and the fairground (water and open land).
- Curved streets and a circle.
- Tint 0.105, which is training-like.
The whole job is about the size of 44 (estimate).
- **impact:** This turns the PDF and 200-ft claims from counts and eye checks into measured numbers.
- **fix:** Ben checks plate 90 completely: blocks, street-side lines and rail, marked complete. Plate 90 then tests things no truth covers today:
- the PDF map mask and nested blocks;
- the 200-ft scale;
- the hole gate;
- the KEY mask for rail;
- outline-quality's straightening of curved streets;
- an out-of-sample plate for the rail rules.
On plate 90, Ben should also mark which ground he decided (open land, the fairground, the canal bed).
After that, a cheap partial check: one district of 60B or 66 with its alleys drawn, plus a polygon for the decided region.
Keep 44 and 90 out of all training. Taking Ben's checked 44 alleys into training (as VC-2 suggests) would destroy the benchmark.
- **effort:** about one 44-sized editor session (estimate)

### K7 [high] The scale advice conflicts; measurement says do not resample 100-ft plates, and plain x2 hurts 400-ft sheets

- **kind:** measurement
- **plates:** 44 measured; 10 plates at 400 ft by eye
- **evidence:** Advice that resamples:
- VC-2 and review M6 / critic-2: resample or resize to 200 ft;
- census C2 and pdf-4: x2 for 400-ft sheets, with outlines.py's constants scaled.
What was measured (I re-ran both with my harness copy):
- 44 with the area net at the 200-ft size: PQ 0.1242.
- Every dark line made 2 px thicker: PQ 0.0289.
- Inference agent: pen 2 px thinner (pen_max2) PQ 0.172; a synthetic 400-ft 44 run without resampling: PQ 0.000.
By eye, inference/overlap (estimates; the agent was not blind to the setting): on 400-ft sheets, plain x2 has precision about 0.54 against the batch's 0.77; x2 with the pen lines thinned back (up2thin), about 0.90.
- **impact:** This avoids applying the census and pdf-4 recommendation as written. The networks are very sensitive to how thick the pen lines are.
- **fix:** - Do not resample 100-ft or 200-ft plates.
- For 400-ft sheets, use up2thin only (maps resized back, outline constants unchanged), and only after Ben checks one 400-ft district.
- Insets at another scale need their own handling: inference's FT400 is per sheet, so the 200-ft insets on 46, 48, 92 and 94 would be resampled too.
- Put scale robustness into training (K12).
- **effort:** small

### K8 [medium] Batch failure modes that no diff implements

- **kind:** failure-mode
- **plates:** see list
- **evidence:** None of the four diffs contains code for any of these (I searched them for rail bins, water, acre limits, width tests and the editor's sheet outline):
1. Rail-yard sides exported as street sides (VC-3; on 44, 9.9k px of wrong lines, 0 right). Cheap: unet_data/N_bins.png already exists.
2. River, creek and canal called block (VC-4, pdf-7; 1B, 2, 3, 26A, 52, 19-23, 41, 42, 90, 95).
3. Open land called block, regions over 20 acres (pdf-6; 21, 24, 32, 41, 72-74, 78, 81, 88, 91).
4. Structures in wide streets, and slivers (VC-5, VC-8; 5, 53, 1A, 2, 3).
5. Street sides along the map edge dropped on PDF sheets (verify-outline-nesting: 201 lines, 64k px).
6. Curved hillside roads turned into straight chords by outline-quality (64A).
7. Insets at another scale (46, 48, 78, 92, 94).
8. The editor's sheet() draws the paper edge as street on PDF sheets.
9. Open corner gaps have a median of 159-190 px; the editor's Close-corners reaches 60 px.
10. map_area misses on 23, 27, 46 and 91; plate 24's png_alpha_s4 cuts off its inset.
11. Rail drawn without ticks (83B, 95); double-line sidings and switches.
- **impact:** These are the errors Ben will still edit after the proposed fixes.
- **fix:** Next in order:
1. In the merged outline step, demote or drop sides that lie more than 50% on rail bins 4/5. This is measured on 44 and nearly free.
2. A PDF-only flag, 'largest block over 50% of the map ground'.
3. An acre limit for exported blocks, decided once plate 90 has truth.
The rest are lower priority or need Ben's conventions (K14).
- **effort:** small to medium each

### K9 [medium] The nesting fix is small but consistent on 44; its big claims rest on counts

- **kind:** measurement
- **plates:** 44 (6 grids); 32 PDF sheets by count
- **evidence:** paired_stats.py over the 6 grids:
- PQ +0.000 on every grid;
- recall +0.012 (sd 0.006, 6 of 6);
- delete length +395 px (worse on 6 of 6);
- draw length -1.8k px.
Plate 44 has no nested regions, and the map mask never runs on a cut plate. The PDF gains (425 to 815 blocks on the 24 sheets at 200 ft) are counts and eye checks only.
- **impact:** This sets expectations: about +1 point of recall on cut plates; the PDF value is unproven.
- **fix:** Adopt it as part of the merge (K3). Score it on plate 90 once it has truth; that also decides HOLE_PARENT.
- **effort:** none beyond K3

### K10 [medium] A single plate is a wide yardstick; bench44's fold rule is about one standard deviation

- **kind:** measurement
- **plates:** 44
- **evidence:** - Block bootstrap of the batch's PQ (paired_stats.py): 0.431, 95% interval 0.319-0.530.
- Tile-grid spread (inference noise_floor.json, rechecked here): sd 0.015 for the whole plate, 0.029 for fold A and 0.027 for fold B.
- The folds differ by 0.089 (batch) and 0.176 (guided).
- Paired comparisons are much tighter (K1, K2).
Between-plate spread is unknown: there is only one truth plate.
- **impact:** This stops noise-level tuning on 44.
- **fix:** - Report paired gains over the 6 grids, plus the block bootstrap interval.
- Treat a fold-level gain under about 0.06 as unproven.
- Absolute PQ levels on 44 (for example 0.43 or 0.54) say little about the atlas until plate 90 exists.
- **effort:** trivial

### K11 [high] No one has measured how much a retrained network differs from one training run to the next

- **kind:** measurement
- **plates:** 44
- **evidence:** torch.manual_seed is never called (review #5). No one has trained the same recipe twice and scored both on 44. The tile-grid spread (sd 0.015 PQ) is only a lower bound on how much the score moves for reasons that have nothing to do with the change.
- **impact:** Without it, Ben cannot tell whether a retraining helped.
- **fix:** Make the first retraining a baseline:
- set the seeds, keep the best weights or use EMA, freeze the label targets, and remove the 255 squares;
- train it twice with two different seeds;
- score both on the 6 grids of 44.
That spread is the bar every later retraining must clear.
- **effort:** 2 area and 2 line trainings (Ben, GPU)

### K12 [medium] Suggested order of the retraining items

- **kind:** proposal
- **plates:** training plates 43, 45, 80, 82A; test on 44 and 90
- **evidence:** This order is my reasoning from these measured numbers:
- The networks are brittle to how thick the pen lines are: PQ 0.03-0.17 with lines 2 px thicker or thinner, and 0.12 at the 200-ft size (K7).
- 400-ft sheets are about 41% of the unplaced ground, and the networks fail there.
- Markers cannot fix the 200-ft alleys (K4), and the training labels call 1922 alleys block (review labels-5: 52.5% of the merged ground on 44).
- Out-of-fold area maps must be made with the final area recipe.
- Heavy tint showed no error type of its own (visual-cut). The census found only r = 0.44 between tint and the unsure share.
- area_ng1 and lines_ng1 already ended near their best weights.
- **impact:** It orders Ben's GPU time by measured need and by what each step depends on.
- **fix:** 1. Seed, EMA or keep-best, frozen targets, and no 255 squares, trained twice (K11). The 255-square fix is a bug fix and rides along.
2. Scale and pen-width augmentation (random resize about 0.5-2x, with pen width jittered by ±1-2 px), plus small warps. Test first without new truth on inference's synthetic 44 variants (make_synth44.py and the pen variants), where today's networks score 0.00-0.17 against 0.43 unchanged.
3. Not on the list, but needed: relabel the 1922 alleys, streets and rail ground on the training plates (Ben's time). Then add a skeleton-recall loss.
4. Out-of-fold area maps for the line network, made only after the area recipe is final; otherwise the 4 extra trainings are wasted.
5. Hue jitter last. It is free to bundle with step 2, but nothing can measure it until a tinted plate (5, 53 or 54A) has truth.
At prediction time: no Hann blending (the grid mean is 0.437 against 0.442), and no TTA once the markers are in (K2).
- **effort:** several overnight trainings

### K13 [medium] The training labels depend on outlines.py, so changing the outline step can silently change the next retraining

- **kind:** failure-mode
- **plates:** 43, 45, 80, 82A (training)
- **evidence:** verify-outline-quality, caveat 3:
- make_labels.py:57 and crop.py:29 read the 'on print' sides of outlines.json.
- With outline-quality's change, the 'on print' length on the guided 44 maps goes from 92.9k to 112.3k px.
- Nobody measured how this changes the labels on the training plates.
- **impact:** Otherwise a retraining could not be compared with the batch.
- **fix:** Freeze the current line targets, and write the target version into each model's json (review #4), before the outline step is rerun on any placed plate.
- **effort:** small

### K14 [medium] What Ben must decide or check next

- **kind:** proposal
- **plates:** 44, 90, all
- **evidence:** Pending items:
- rail_ben.json still holds 26 tracks, saved 18 Nov. The 28-track page copy, with the spur, has a note saying the save was blocked by a test hook Claude had left in the page. I found no such hook in tools/sanborn today, so I cannot confirm whether a new save would now go through.
- Open choices in the proposals: outline-quality's step 4 (drop sides on no line: precision 0.760, 6 blocks closed; or keep them: precision 0.646, 18 closed), and HOLE_PARENT.
- Conventions nobody has: whether 200-ft mid-block alleys are block sides, and how to treat open land on PDF sheets, streetcar track under street names, rail drawn without ticks, and rail ground (block or not).
- **impact:** These choices unblock the merge, the second truth plate and the next retraining.
- **fix:** 1. Save the 44 spur again, then check that rail_ben.json has 28 tracks.
2. Agree plate 90 as truth plate 2, kept out of training.
3. Give the conventions above, ideally before checking plate 90.
4. Choose the step-4 option.
5. Approve one merged outline-step rerun over the batch outputs (K3).
6. Approve the retraining order (K12).
- **effort:** Ben's time

### K15 [low] The rail numbers are training-set numbers; rail recall outside 44 and 1A is unknown

- **kind:** measurement
- **plates:** 44 (tuned on it), 1A (partial)
- **evidence:** The rail and rail-rules agents chose their settings (the 600/60 filter, streetcar reach 300-400) after looking at 44's errors. Batch-wide precision is estimated by eye: railroad about 85%, streetcar about 96%.
- **impact:** It gives an honest rail number.
- **fix:** Let plate 90's complete rail (19 railroad and 16 streetcar rule tracks today, plus the KEY) be the first plate the rail rules are scored on out of sample. Do not tune further on 44.
- **effort:** comes with K6
