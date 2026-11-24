# Retraining the block U-nets on more plates: preparation reports (23-24 November 2026)

Ben: "1A is done. let's try training on a number of them. you should choose them by complexity and size, with what you think are enough plates to teach the U-net sufficiently". Paths are in data/sanborn/bench_2026-11-23/train/ (not in git); scripts are copied beside this file.

## final report

### summary

The data folder has been rebuilt and checked. The staged code fixes every real problem the three reviews found and passes its tests. The baseline evaluation reproduces the known plate-44 numbers exactly. Nothing has been trained for real.

Nothing was written into tools/, unet_data, picks22_guided, streetmap or cufp: no file there is newer than the start of this work, and `git status tools/` is clean. edges_ben.json and rail_ben.json were not touched. Plates 44 and 90 are not in the data folder, and the trainers refuse them.

**Three changes to the plan. Please confirm or reverse them.**

1. **In V2, the line net's 7th input is "no area map" (128) on the pseudo plates.**
   - The leak review was right. On a pseudo plate, the line target was made from the very map that is its area_in.png, so the answer can be read off that input: drawing a line wherever the map crosses 0.5 scores precision 1.000 there, against 0.54–0.73 on the labelled plates.
   - The fix is a new trainer option, `edgenet.py --area-blank pseudo`, which the driver passes for V2's line net only. The data folder is unchanged.
   - I measured the review's other option, changing the labels instead (ch7_relax.py, 4 plates). It could make only 10–25% of the crossing pixels "not a line", so most of the leak would stay.
   - The cost: the line net now sees "no area map" in about 57% of its V2 crops. It may lean less on the area map, and V1 against V2 will show whether that hurts.
   - V1 is not affected.
2. **Plate 58 is added as an 11th pseudo plate, a low-tint 100-ft residential plate.**
   - The census shows 15 of the batch's other 34 plates at 100 ft have a tint under 0.30, and none of them was among the ten pseudo plates.
   - The labels review suggested swapping 89 for 58. I added 58 instead, so the second PDF sheet (89) stays in.
   - I looked at 58's overlay and two zoomed views and found nothing that needed a hand mask.
   - Each pseudo plate's weight is now 5/11 (0.454545), so labelled and pseudo crops stay about 1:1.
   - The case for 58 rests on the batch, but the review raised it by comparing tints with plate 44.
3. **A rule for what ships, written into the driver before the run** (the leak review's finding 3). Plate 44 decides only two things:
   - V2 is preferred over V1 only if it beats V1 for both seeds, and the mean difference is bigger than the seed-to-seed spread. Otherwise V1 is kept, as the simpler of the two.
   - That pair replaces area_ng1 + lines_ng1 only if its gain over them is above 0 for both seeds and bigger than that same spread on average.
   - The seed is chosen on the 1A validation region, never on 44.
   - summary.md applies the rule by itself once all four pairs are evaluated. Plate 90 stays as the untouched final check.

**What else was fixed:**
- **eval_v2.py:**
  - a Windows clash when parallel runs write the same cache file: the first baseline run now goes alone, and each run folder's cache is copied in before the parallel runs start;
  - a baseline run is reused only if the code and Ben's street map are unchanged;
  - its result file is written whole or not at all;
  - `torch.load(weights_only=False)` is stated outright;
  - it checks that `python` can load scipy and shapely before it starts.
- **train_v2.py:**
  - one failed step no longer ends the whole run;
  - a half-written result file no longer crashes a restart;
  - a finished model is reused only if its seed, plates, weights and `--area-blank` match;
  - the summary copes with missing values;
  - 1A is scored against train_v2/1A/streetmap.json and valmask.png, not Ben's live file.
- **Both trainers:**
  - model files and their records are written whole or not at all;
  - a `--data` run can never write into unet_data;
  - `--val-every` must be 1 or more;
  - the best checkpoint is compared on its unrounded score;
  - meta.json is now checked against the manifest;
  - the model record also holds the manifest's content hash.
- **bench_plate.py:** 1A now gets the "watershed regions" stage that was missing from its scores.

**Where a review was wrong, or I did not act:**
- The labels review's cheap option (leave the area net's edge target untaught on pseudo plates) is not done. That third output is written by `unet.predict` and read by nothing in the batch pipeline (grep). The main output is taught the same merges on the same pixels.
- Plate 79's grey curved band ("435") is drawn as water, with a grey wash and a heavy outline. So its "not a line" pixels fit Ben's rule that a creek edge is not a street side. This is my judgement by eye.
- The trainers still score the 1A validation ground from a crop of it. The model record now says so, along with the review's measured effect: about 0.01 in IoU street.

**GPU check.** The same seed run twice on the GPU gives bit-identical weights for both networks.

### files

Everything is under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/.

**THE DATA FOLDER** (train_v2/, 186 MB): 16 plate folders and manifest.json.
- manifest.json sha256 60e89074…; content_sha256 59175f67….
- All meta.json files were made by the same make_labels_v2.py (sha256 1a20f2fa…).
- The 15 plates of round 1 are byte-identical in every data file (compare_build.json). Only meta.json and the manifest changed. Plate 58 is new.

**STAGED CODE** (bench_2026-11-23/train/staged/tools/sanborn/unet/):
- unet.py: atomic writes, `--out` guard (never unet_data), `--val-every` check, unrounded best score, meta.json checked against the manifest, content sha recorded, val_scope note.
- edgenet.py: the same fixes, plus `--area-blank SOURCES|PLATES`.
- eval_v2.py: cache-race fix, code record for reusing baseline runs, atomic write, weights_only, Python pre-check, the 1A region labelled "not a test".
- bench_plate.py: stage 1 (watershed regions) on 1A.
- make_labels_v2.py: docstring fix only (manifest hashes).
- train_v2.py: rewritten driver (non-fatal steps, safe restart, model checks, pinned 1A truth and region, 58, weights 5/11, `--area-blank pseudo` for V2's line net, the shipping rule).

**DIFF** (bench_2026-11-23/train/staged.diff): 2,227 lines, sha256 4d43a630…, the 6 staged files against HEAD 017ce0c. `make_diff.sh` showed it applies to fresh copies with both git apply and patch, giving the staged files byte for byte, and that `git apply --check` on the repo passes (nothing applied).

**MY FOLDER** (bench_2026-11-23/train/integrate/round2/):
- integrator_edits_round2.diff: this round's changes to the staged files. orig_staged/ holds round 1's staged files and round 1's staged.diff.
- scripts/:
  - build_train_v2.sh;
  - compare_build.py;
  - check_data.py;
  - ch7_relax.py;
  - test_cli2.py;
  - test_driver2.py;
  - cpu_test.py;
  - repeat_gpu.sh;
  - repeat_compare.py;
  - edits_diff.sh.
- Results:
  - build_train_v2.log, verify_train_v2.json;
  - compare_build.json, check_data.json;
  - ch7_relax.json;
  - test_cli2.json, test_driver2.json;
  - cpu_test/cpu_test.json;
  - repeat/repeat_compare.json.
- driver_mini/ and driver_mini.log:
  - the 40-iteration GPU driver test (baseline + V2S1);
  - eval/baseline/eval_v2.json is the re-run baseline evaluation;
  - eval/runs_baseline44/ holds the six baseline plate-44 runs, now with code records.
- Other folders:
  - driver_mini_rerun.log (the restart test);
  - driver_dry.log (the dry run);
  - pics/58.jpg and the two 58 zooms;
  - test58/ (the test build of 58);
  - train_v2_round1/ (round 1's manifest and meta files).
- _second_copy/: the scripts, the six staged files, staged.diff, integrator_edits_round2.diff, hand_masks.json and the new manifest.
- Throwaway: repeat/ (356 MB), driver_mini/models (part of its 459 MB) and cpu_test/ (119 MB) hold test checkpoints and can be deleted.
- train_v2 has no second copy: build_train_v2.sh rebuilt it byte-identically in 7 min.

### numbers

Measured on 24 Nov unless marked as an estimate.

**1. The data folder** (build_train_v2.sh, 7 min 17 s; tallied from check_data.json):

| Source | Plates | Taught, half-size px | Acres | Line +/−, full-size px |
|---|---|---|---|---|
| label | 4 (43, 45, 80, 82A) | 52.43 M | 1,633 | 4.08 M / 198.7 M |
| map | 1 (1A) | 3.15 M (validation part 1.18 M) | 32 | 0.35 M / 11.8 M |
| pseudo | 11 | 99.35 M | 2,365 | 11.06 M / 316.8 M |

Taught M half-size px per pseudo plate:

| Plate | 5 | 54A | 53 | 7 | 51 | 58 | 66 | 68 | 76 | 79 | 89 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Taught | 10.29 | 10.29 | 9.16 | 8.00 | 6.70 | 10.74 | 10.52 | 8.72 | 9.89 | 9.30 | 5.73 |

Plate 58 (meta.json): 386 green lines and 69 alley pairs found. Nothing was dropped by the size cap, and it has no KEY box and no hand mask.

**2. Checks.**
- verify_train_v2.json: on 43, 45, 80 and 82A, all 7 arrays equal today's loaders.
- compare_build.json:
  - all data files of the 15 round-1 plates are unchanged;
  - no manifest mismatch, content_sha256 is right;
  - 44 and 90 are absent.
- check_data.json: none of 50,000 area-net crops and 50,000 line-net crops touches 1A's validation ground. The area crops reach x = 1420 half px, where it starts. The line crops stop at 2838 full px; it starts at 2841.
- cpu_test.json:
  - with `--area-blank`, plate 58's 7th input is 128 everywhere, against a mean of 183.1 without it; scan and target are identical;
  - blanking a plate that has validation pixels is refused;
  - meta.json is now checked against the manifest (in_manifest true);
  - no .tmp files are left behind.
- test_driver2.json:
  - a finished model with another seed, plates, weights, manifest or `--area-blank` stops the run with a "move aside" message;
  - a cut-off result file counts as not finished;
  - a failed training or evaluation does not stop the run, which ends with exit code 1;
  - the shipping rule was checked on 4 made-up cases.
- test_cli2.json: 16 cases. The old train_noguide commands parse as before; `--val-every 0` and `--out` inside unet_data are refused.
- ch7_relax.json: share of area-map 0.5-crossing pixels that a label-side fix could make "not a line" at all: 5: 25%, 54A: 17%, 66: 10%, 79: 22%.
- repeat_compare.json: same seed twice on the GPU (RX 7900 XTX), 30 iterations on 1A + 43. Largest weight difference 0.0 for both networks; the crops and validation history are identical. Seed 2 against seed 1 differs by 0.34 (area) and 0.33 (lines). The line net with seed 1 still draws nothing at 30–40 iterations (F1 0), as in round 1's smoke test; this is an early-training effect.

**3. Smoke test** (driver_mini, all 16 plates, V2 weights, seed 1, 40 iterations, GPU; figures from the model jsons):

| | Area net | Line net |
|---|---|---|
| Plates held in memory | 3.12 GB | 5.67 GB |
| Peak working set | 4.67 GB | 7.67 GB |
| Peak private (mostly DirectML) | 9.80 GB | 13.34 GB |
| Seconds per iteration | 0.687 | 0.713 |
| Validation check | 0.28 s | 0.91 s |
| Load | about 15 s (estimate) | 20.0 s |
| Whole step | 0.7 min | 0.9 min |
| Crops, labelled : pseudo | 162 : 158 | 129 : 111 |

- In the line net, all 11 pseudo plates were blanked.
- Restart test: a second run skipped every step in about 1 s.

**4. Baseline evaluation** (eval_v2 on area_ng1 + lines_ng1, fresh baseline runs; driver_mini/eval/baseline/eval_v2.json, 3.7 min):
- The maps are identical to bench44_maps on all 6 grids.
- Plate 44 PQ by grid: 0.543 (grid 0, the batch grid), 0.5125, 0.5208, 0.5327, 0.4893, 0.4652.
- 6-grid mean 0.5106, sd 0.0288. Both known numbers (0.511 and 0.543) are reproduced.
- Other 6-grid means: recall_interior 0.6256, precision 0.8333, merges 12.17, false blocks 10.83, Ben's blocks closed 4.83, PQ_decided 0.5381.
- 1A validation region, 9 blocks (not a test): PQ 0.0928, recall_interior 0.6629, precision 0.8872 (1 matched, 3 merges, 6 false). bench_plate now scores all 5 stages on 1A.
- The V2S1 evaluation reused all 6 baseline runs ("same code").

**5. Label quality** (from the reviews; the label code is unchanged this round):
- Pseudo labels against Ben's maps:

| | Block precision | Street precision | Ben's blocks joined across alleys |
|---|---|---|---|
| 1A, whole plate | 99.3% | 98.5% | 8 of 21 |
| 1A, validation area | 99.5% | 99.4% | – |
| 44, with the cap | 98.3% | 99.7% | 11 of 55 |

- Line positives within 3 px of Ben's lines: 83.6% on 1A, 80.3% on 44.
- 1.9% of Ben's lines have a "not a line" pixel within 2 px.
- The thresholds were tuned on 1A, so the 1A figures are optimistic.
- Plate 58 has no truth; it was checked by eye only.

**6. GPU time for the full run** (estimate, from the smoke test):
- area net: 4000 × 0.69 s ≈ 46 min; line net: 4000 × 0.71 s ≈ 47.5 min; loading and checks under 1 min each;
- 8 networks ≈ 6.3 h;
- evaluations: baseline 3.7 min measured; the others 2.0–2.2 min with real models (measured in round 1; the 4.2 min here came from 40-iteration models that made 744 false blocks);
- total about 6.5 h.

### how_to_run

1. **Apply the staged code.** You or the orchestrator, after review, from the repo folder (3D), in PowerShell:
   `git apply data\sanborn\bench_2026-11-23\train\staged.diff`
   Then commit it on hub_region, so every model json names a commit and not "uncommitted changes".
2. **Check the plan without running anything:**
   `python tools\sanborn\unet\train_v2.py --dry-run`
   It should print 13 commands: the baseline evaluation, then for V1S1, V2S1, V1S2 and V2S2 two trainings and one evaluation each.
3. **Start the run** (about 6.5 h of GPU):
   `python tools\sanborn\unet\train_v2.py`
   - Optional: add `--baseline-runs data\sanborn\bench_2026-11-23\train\integrate\round2\driver_mini\eval\runs_baseline44` to reuse the six baseline runs (they carry a code record) and save about 1.5 minutes.
   - Output goes to data\sanborn\train_v2_runs\: models\, eval\<STEP>\eval_v2.json, logs\, train_v2.log, summary.json and summary.md.
   - The table and the rule's decision are in summary.md, rewritten after every step.
4. **If it stops or a step fails,** run the same command again. Only what is not finished is redone; a training cut off part way restarts from the beginning.
5. **Other useful forms:**
   - `--only V1S1` (steps: baseline, V1S1, V2S1, V1S2, V2S2, comma-separated);
   - `--summary` (rewrite the table only).
   The driver starts the venv by itself. Every evaluation scores 1A against train_v2\1A\streetmap.json and valmask.png.

### open_issues

1. **Please confirm or reverse the three changes:**
   - `--area-blank pseudo` for V2's line net;
   - plate 58 added, with pseudo weight 5/11;
   - the shipping rule.
   Two round-1 decisions also still stand: 1A's validation region is everything right of Elm Street, and the seven hand masks.
2. **Possible cost of `--area-blank`:** the line net now sees "no area map" in about 57% of its V2 crops (estimate). It may lean less on the area map, which is always there in use. Only V1 against V2 will show this.
3. **Known limits of the pseudo labels, unchanged:**
   - they teach alley merges: 11 of Ben's 55 blocks on 44 and 8 of 21 on 1A are joined;
   - Ben's lines along missed alleys are taught as "not a line";
   - rail and canal lines stay as positives in the line targets;
   - open land under the size cap is taught as block, a convention Ben has not set;
   - confidence filtering keeps the easy ground;
   - some lot lines are taught as block lines.
   V2 may make the joins worse; V1 against V2 over two seeds is the test.
4. **Not done (the code review's suggestion):** an extra evaluation row with area_ng1's maps feeding the new line net, which would separate the two networks' effects. It would add about 2 minutes per evaluation.
5. **Not done:** the area net's edge target on pseudo plates was left as it is. Nothing in the batch reads that third output.
6. **The 1A region numbers are not a test:** the checkpoints are chosen there, the pseudo-label thresholds were tuned on 1A, and one block moves its PQ by about 0.1. Plate 44's numbers for the pair that ships will be slightly optimistic, because 44 chooses between V1, V2 and keeping the batch pair. Plate 90, once Ben checks its lines, is the untouched check.
7. **If the best checkpoint turns out to be the last one,** 4,000 iterations may be too few.
8. **Housekeeping:** test checkpoints in integrate/round2/repeat (356 MB), driver_mini/models and cpu_test (119 MB), plus review-leak/seed (356 MB), can be deleted when you are ready.


## integrator, first report

### summary

The data folder is built and checked, the driver is written and tested, and the baseline evaluation reproduces the known plate-44 numbers. Nothing has been trained for real. Nothing was written into tools/, unet_data, picks22_guided, streetmap or cufp: no file there is newer than the start of this work, and git status for tools/ is clean.

**The data folder.** data/sanborn/train_v2/ has 15 plates:
- the four labelled plates (43, 45, 80, 82A), loaded through the new folder and checked pixel for pixel against today's loaders: all 7 arrays are equal on all four;
- 1A from Ben's check;
- the ten selected pseudo plates (5, 54A, 53, 7, 51, 66, 68, 76, 79, 89).

Plates 44 and 90 are not in it, and no 1A validation pixel can be trained on: none of 50,000 sampled crops per network touched it.

**Three changes I made to the plan. Please confirm or reverse them.**
1. **1A's validation area is everything right of Elm Street (x >= 1420 half px), not the image's right-hand quarter.** Both earlier agents found the quarter thin: 10% of 1A's paper and 1 of Ben's 21 blocks. The ground right of Elm Street holds 35% of the paper and 9 blocks, and no block is cut. The cost is that only about 65% of 1A is trained on, not 75%.
2. **Three rules added to the pseudo labels, plus a size cap on blocks.**
   - The printed KEY box is not taught. This matters on cut plate 76, where nothing else masked it.
   - On the PDF sheets, no line is taught off the map ground.
   - Block is taught only in blocks no bigger than the big blocks on the labelled plates (16.97 acres at 100 ft, 35.46 at 200 ft). This drops 51's river landing, 68's Zoo, 76's KEY plus Duck Creek ground, and the largest open tracts on 79 and 89.
3. **Seven hand masks on five plates, from looking at the overlays.** Each box is recorded in each plate's meta.json:
   - 51: the Suspension Bridge approach, taught as one block across three streets.
   - 53: the Central Parkway median, taught block. Ben's own 1A map makes Central Parkway street.
   - 5: the Garfield Place median, and the Sixth Street market house in the middle of the street.
   - 79 and 89: blank paper beyond the mapped area, taught block.

**Problems I saw but did not fix:**
- Open land and estates under the size cap are still taught as block (79's cemetery and tracts, 89's estates, 68's large lots). Labelled plate 43 does the same today with its cemetery and creek, so this matches the current labels. Ben has not set that convention.
- Narrow streets and alleys inside merged blocks are still taught as block (for example on 54A). This is the known limit: pseudo labels repeat the networks' alley merges.
- 53's abandoned Canal Basin is left taught as block.
- Some lot lines are taught as block lines. Earlier measurement put pseudo line precision at about 80%.

**Crop mix and iterations.** In the V2 runs each pseudo plate gets weight 0.5, so labelled and pseudo crops come 1:1. In the smoke test that came out at 159 against 161 crops. I kept 4,000 iterations per network: that keeps V1 and V2 on equal compute, and every pseudo plate still gets about 1,600 crops. If the best checkpoint turns out to be the last one, more iterations may help.

**A fix to someone else's staged code.** bench_plate.py failed when its two runs wrote the same cache file at the same time (a Windows "access denied"). It now tolerates that. I also changed eval_v2.py's printed label from "validation quarter" to "validation region".

The driver (staged as tools/sanborn/unet/train_v2.py) runs the baseline evaluation, then V1 and V2 with seed 1, then both with seed 2, with an evaluation after each pair. It writes a log and a summary table after every step. A rerun skips what is finished: a 20-iteration test of the baseline and V1 seed-1 steps ran end to end, and a second run skipped every step in 1 s.

**Estimated GPU time for the full run: about 6.5 hours.** Each of the 8 trainings is about 47 minutes (measured 0.67 to 0.72 s per iteration), and the five evaluations take about 12 minutes together.

### files

Everything is under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/.

**THE DATA FOLDER** (train_v2/, 173 MB): 15 plate folders and manifest.json.
- manifest.json sha256 1b9c5fc5…; content_sha256 c847a936….
- Each folder has img.jpg, label.png, edge.png, lines.png, area_in.png and meta.json. 1A also has valmask.png and streetmap.json.

**STAGED CODE** (bench_2026-11-23/train/staged/tools/sanborn/unet/):
- unet.py and edgenet.py: the trainer agent's versions, unchanged by me.
- eval_v2.py: the trainer agent's, with wording changes only ("validation region" for "validation quarter").
- bench_plate.py: the trainer agent's, plus the fix for the clash when two runs write the same cache file.
- make_labels_v2.py: the label agent's, plus my changes:
  - `--val-x` for map plates;
  - the block size cap (`--cap`, on by default);
  - the KEY box from census/rail_key.json;
  - no lines taught off the map ground;
  - `--mask FILE` for hand masks;
  - compare mode uses the map folder's valmask.png.
- train_v2.py: the new driver.

**DIFFS:**
- bench_2026-11-23/train/staged.diff: all six staged files against the repo's HEAD, with a/ b/ paths (sha256 47342752…).

**MY FOLDER** (bench_2026-11-23/train/integrate/):
- integrator_edits.diff: my changes to the other agents' staged files. orig_staged/ holds their originals.
- hand_masks.json: the 7 hand-mask boxes and the reason for each.
- pics/: one overlay per plate (15) and _hand_masks_check.jpg.
- test/: the test builds and zoomed pictures I used to find the problems.
- Build and check outputs:
  - build_train_v2.log;
  - verify_train_v2.json;
  - check_data.json;
  - val_options.json: the three 1A cuts compared.
- smoke/: the 40-iteration smoke models, their jsons and logs.
- baseline_ng1/ and baseline_ng1.log: the baseline evaluation, with eval_v2.json and the six baseline plate-44 runs (runs_baseline44/), which later evaluations can reuse.
- driver_mini/ and driver_mini.log: the 20-iteration driver test. driver_dry/ is the dry-run log.
- scripts/:
  - build_train_v2.sh;
  - check_data.py;
  - overlay.py;
  - region.py;
  - val_options.py;
  - make_diff.sh.
- _second_copy/: a second copy of the scripts, hand_masks.json, integrator_edits.diff, the six staged files and staged.diff.

### numbers

All measured on 23–24 Nov unless marked as an estimate.

**1. The data folder.** Script: build_train_v2.sh, which runs make_labels_v2.py under the venv. The build took 6 min 56 s. Taught pixels (tallied from check_data.json):

| Source | Plates | Taught, half-size px | Acres | Line +/−, full-size px |
|---|---|---|---|---|
| label | 4 | 52.43 M | 1,633 | 4.08 M / 198.7 M |
| map (1A) | 1 | 3.15 M (training part 1.97 M, validation part 1.18 M) | 32 | 0.35 M / 11.8 M |
| pseudo | 10 | 88.61 M | 2,256 | 10.02 M / 282.2 M |

Taught half-size px per pseudo plate: 5: 10.29 M, 54A: 10.29 M, 53: 9.16 M, 7: 8.00 M, 51: 6.70 M, 66: 10.52 M, 68: 8.72 M, 76: 9.89 M, 79: 9.30 M, 89: 5.73 M.

Effect of my rules (make_labels_v2.py counts in meta.json), in half-size px:
- Block dropped by the size cap: 51: 3.26 M, 68: 1.42 M, 76: 2.50 M, 79: 2.83 M, 89: 4.83 M.
- Taken out by the hand masks: 79: 0.10 M, 89: 0.41 M, 53: 0.05 M.

**2. Checks.**
- make_labels_v2.py verify (verify_train_v2.json): on 43, 45, 80 and 82A, all 7 arrays equal today's loaders.
- check_data.py (check_data.json):
  - 44 and 90 are absent from the folders and the manifest;
  - all manifest sha256s match, and content_sha256 is right;
  - 50,000 area-net crops and 50,000 line-net crops on 1A: 0 touch the validation area. The area crops reach exactly x = 1420, where it starts. The line crops stop at 2838; it starts at 2841.
- 1A validation area (val_options.py on the label agent's 1A labels): x >= 1420 half px. It holds 35.0% of the paper and 9 of Ben's 21 blocks, with none cut. Taught there: 758,812 block px, 420,798 street px, and 123,863 positive / 4.41 M negative line px. For comparison, the image quarter holds 9.9% of the paper and 1 block; the paper quarter 25% and 6 blocks, with 3 cut.
- Pseudo labels against Ben's map on 1A (make_labels_v2.py compare, test/compare_1A.json):
  - whole plate: block precision 99.41%, street 98.38%, coverage 58.9%. These equal the label agent's figures, so the build is faithful.
  - inside the new validation area: block 99.48%, street 99.45%.
  - The thresholds were tuned on 1A, so these are optimistic.

**3. Smoke tests.** All 15 plates loaded, V2 weights, seed 1, 40 iterations, on the GPU. Figures from the model jsons and logs in smoke/.

| | Area net | Line net |
|---|---|---|
| Plates held in memory | 2.91 GB | 5.29 GB |
| Peak working set | 4.49 GB | 7.29 GB |
| Peak private (mostly DirectML) | 9.62 GB | 12.96 GB |
| Seconds per iteration | 0.671–0.696 | 0.689–0.715 |
| Validation check | 0.27 s | 0.86–0.89 s |
| Load | about 14 s (estimate: 42 s wall minus 28 s training) | 19.6 s (measured) |
| Crops drawn, labelled : pseudo | 159 : 161 | 131 : 109 |

**4. GPU time** (estimate, from the smoke tests):
- each network: 4,000 × 0.69–0.71 s ≈ 46–47 min, plus about 0.5 min of loading and checks;
- 8 networks ≈ 6.3 h;
- evaluations: measured at 2.0–2.2 min each when the baseline runs are reused, 3.4 min the first time;
- total about 6.5 h.

**5. Baseline evaluation.** eval_v2.py on area_ng1 + lines_ng1, 6 grids, baseline_ng1/eval_v2.json, 203 s.
- The maps are identical to bench44_maps on all 6 grids.
- Plate 44 PQ by grid: 0.543 (grid 0, the batch grid; reproduces 0.543), 0.5125, 0.5208, 0.5327, 0.4893, 0.4652.
- 6-grid mean 0.5106, sd 0.0288 (reproduces 0.511).
- Other 6-grid means: recall_interior 0.6256, precision 0.8333, merges 12.17, false blocks 10.83, Ben's blocks closed 4.83.
- 1A validation area (9 blocks): PQ 0.0928, recall_interior 0.6629, precision 0.8872.
- 1A outside that area: PQ 0.3043. Whole 1A: PQ 0.2103.

**6. Driver test** (train_v2.py, 20 iterations, baseline + V1 seed 1; driver_mini.log): 299 s wall. The second run skipped every step in 1 s. Its PQ of 0 only shows that the chain runs.

**7. staged.diff** (make_diff.sh): 1,977 lines.
- `git apply` and `patch -p1` on fresh copies of HEAD both succeed. The result equals the staged files byte for byte (6 files).
- `git apply --check` on the repo passes; nothing was applied.

### how_to_run

From the repo folder (3D), in PowerShell.

1. Apply the staged code. Either:
   `git apply data/sanborn/bench_2026-11-23/train/staged.diff`
   or copy the six files from data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/ into tools/sanborn/unet/. Both give the same bytes; tools/sanborn has no line-ending conversion.

2. Check the steps without running anything:
   `python tools\sanborn\unet\train_v2.py --dry-run`

3. Run everything (about 6.5 hours):
   `python tools\sanborn\unet\train_v2.py`
   - To reuse the six baseline plate-44 runs already made, add:
     `--baseline-runs data\sanborn\bench_2026-11-23\train\integrate\baseline_ng1\runs_baseline44`
   - Outputs go to data\sanborn\train_v2_runs\: models\, eval\<step>\eval_v2.json, logs\, train_v2.log, summary.md and summary.json.
   - If the run is interrupted, run the same command again: finished steps are skipped.
   - `--only V2S1` runs one step. `--summary` rewrites the table from what is there.

4. To rebuild the data folder (only if the labels change):
   `sh data/sanborn/bench_2026-11-23/train/integrate/scripts/build_train_v2.sh`
   This changes the manifest sha256, and the driver then refuses models trained on the old data until they are moved aside.

5. The models land in train_v2_runs\models, not unet_data\models. To use a variant in the batch, copy its NAME.pt as area_ng2.pt or lines_ng2.pt.

### open_issues

1. **The 1A validation area is right of Elm Street, not the image quarter. Confirm or reverse.** It is 35% of the paper with 9 of Ben's blocks, against 10% and 1 block. The checkpoints are chosen there. Ben's 1A lines began as the batch's lines, so the baseline starts ahead on 1A.

2. **1A's crop weight is 1.0, like each labelled plate.** Its training part is only 1.97 M taught px, against 10–17 M on each labelled plate. So each 1A pixel is seen about 6 times as often as a pixel on 43 (estimate). I kept this on purpose: 1A is the only plate with Ben's own alleys, and it is the heaviest tint at 100 ft. A lower weight, such as 0.3, is the alternative.

3. **The hand masks were chosen by eye on quarter-size overlays (7 boxes on 5 plates).** There may be errors I missed.
   - Blank paper inside the map ground of the PDF sheets is taught as block wherever the merged step drew a block over it. I masked it only where I saw it, on 79 and 89; there is no general rule for it.
   - 53's abandoned Canal Basin is still taught as block.

4. **Conventions Ben has not settled are still taught as the networks see them.**
   - Open land, estates, cemeteries and the creek are taught as block on the pseudo plates (below the size cap) and also on labelled plate 43.
   - Rail ground is mostly not taught.
   - The pseudo labels repeat the alley and narrow-street merges (the 21 Nov limit and confirmation-bias risk). Only Ben's checks can teach those.

5. **The line net's 7th input is in sample on 43, 45, 80 and 82A** (area_ng1 was trained on them). It is out of sample on 1A and the pseudo plates.

6. **4,000 iterations is kept for every network.** If V2's best checkpoint is its last one, try more iterations.

7. **Same-seed repeatability on the line net under DirectML is untested.** The trainer agent checked it only for the area net, over 30 iterations. That spread between seeds is the bar the V1 and V2 difference must clear, so it matters.

8. **Nothing has been trained for real.** The 20-iteration models only prove the chain runs. These folders are scratch and can be deleted: integrate/driver_mini (426 MB), smoke/ (119 MB) and test/ (165 MB).


## plate selection

### summary

I chose K = 10 pseudo-label plates: five at 100 ft (5, 54A, 53, 7, 51), three cut plates at 200 ft (66, 68, 76) and two PDF sheets at 200 ft (79, 89). Six reserves are listed in case one is swapped: 67, 4, 12, 28, 11 and 60B.

I looked at every unplaced plate's merged-step overlay, with each block tinted in its own colour (26 contact sheets). For the shortlist I also looked closely at the area net's confident pixels beside the overlay. The ten are the cleanest outputs of each kind that a pseudo label can teach without teaching errors:
- tinted dense downtown at 100 ft (the benchmark's scale);
- tinted 200-ft grids;
- diagonal grids;
- PDF sheets: no PDF sheet is in training today;
- KEY boxes and large lettering.

After V2 the training set has 7 plates at 100 ft and 8 at 200 ft. The tint range grows from 0.15-0.20 (plus 1A at 0.75) to 0.20-0.65.

Three findings from Ben's 1A check change how the integrator should build the data. Nothing in tools/, unet_data, picks22_guided or streetmap was written.
- **The pseudo-label filter must keep "block" only inside the merged step's blocks.** area_ng1 calls the Ohio River and the public landing on 51 confident block. It does the same to the paper margins on 79 and 89. The map-ground mask and the KEY boxes (census/rail_key.json) must also be cut out.
- **1A's right-hand image quarter is a poor validation area.** It holds only 9.9% of 1A's paper and 1 of Ben's 21 blocks. A cut at x = 3358 full px instead holds 25% of the paper and 6 blocks.
- **The trainers pick plates evenly** (unet.py:116, edgenet.py:93). With 5 labelled and 10 pseudo plates, two-thirds of crops would be pseudo. Mix labelled and pseudo crops 1:1 instead.

Also measured on 1A, the only plate whose truth may be looked at here (44 was not used):
- The area net's confident pixels are 98.7% right on the ground Ben closed into blocks.
- Its errors are exactly the alleys: 1.1% of Ben's street ground is confidently called block.
- The line net misses those alleys too. A 12 px band around its lines catches only 4.5% of the errors.

So pseudo labels will add tint, PDF and lettering variety, but they will re-teach the alley merges. This backs the 21 Nov review's advice to be wary of self-training the line net.

Files are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-23/train/select/:
- selection.json: the integrator's input;
- plates.json and plates.csv;
- pseudo_area.json and pseudo_area_strict.json;
- load_cost.json;
- ben1a.json, ben1a_lines.json and val1a.json;
- views/sheet_01..26.jpg and views/one_*.jpg;
- the scripts that made them.

### plates

[
 {
  "plate": "5",
  "kind": "dense downtown, 100 ft, tint 0.49, cut plate (72.0 MP)",
  "scale_ft": 100,
  "why": "The cleanest 100-ft output in the batch: 64 blocks, each printed block its own region, CBD alleys. 100 ft is the benchmark's scale, and only 43 (and now 1A) are in training at it.",
  "risk": "Alleys the nets never see stay taught as block."
 },
 {
  "plate": "54A",
  "kind": "dense downtown (north Over-the-Rhine), 100 ft, heavy tint 0.65, cut plate (75.6 MP)",
  "scale_ft": 100,
  "why": "Tint 0.65, against 0.15-0.20 on the labelled plates. Many alleys come out as confident street. The merged blocks are right apart from a few joins at the top.",
  "risk": "Heavy tint is where the area net is least sure, so a confident error there gets taught."
 },
 {
  "plate": "53",
  "kind": "dense downtown + rail fan + diagonal district, 100 ft, tint 0.59 (77.6 MP)",
  "scale_ft": 100,
  "why": "CBD grid, the Eggleston/Broadway diagonal blocks, a rail fan at Court St, and large lettering.",
  "risk": "The rail fan comes out as one region, and Ben has not decided the rail-ground rule."
 },
 {
  "plate": "7",
  "kind": "dense West End with mid-block alleys, 100 ft, tint 0.50 (58.3 MP)",
  "scale_ft": 100,
  "why": "A clean grid: 26 mid-block alleys were found as street holes.",
  "risk": "Alleys that were not found stay taught as block."
 },
 {
  "plate": "51",
  "kind": "downtown riverfront and wharves, 100 ft, tint 0.56 (76.8 MP)",
  "scale_ft": 100,
  "why": "Tinted downtown, and the river kind handled safely: the merged step puts no block on the river.",
  "risk": "area_ng1 calls the river and the public landing CONFIDENT BLOCK. Block must be kept only inside merged blocks, or the river is taught as block. A few joins in the middle."
 },
 {
  "plate": "66",
  "kind": "dense 200-ft grid, tint 0.31, cut plate (71.6 MP)",
  "scale_ft": 200,
  "why": "106 blocks, the most of any plate, each found on its own. More tint than 45, 80 and 82A.",
  "risk": "200-ft mid-block alleys are missed and taught as block, the same limit as today's labels."
 },
 {
  "plate": "68",
  "kind": "200-ft grid + Zoo + irregular north edge, tint 0.54 (75.7 MP)",
  "scale_ft": 200,
  "why": "Heavy tint at 200 ft. The Zoo is one large real block. Mixed grid and irregular streets.",
  "risk": "A few large joins at the top. The strict size cap drops 11% of the ground."
 },
 {
  "plate": "76",
  "kind": "200-ft diagonal grid + KEY + Duck Creek industry, tint 0.20 (74.2 MP)",
  "scale_ft": 200,
  "why": "98 blocks on two crossing grids. A KEY box is printed inside the map, which tests the masking.",
  "risk": "The KEY and the industrial ground form one merged block. Mask the KEY box (census/rail_key.json) and drop the big blocks (14% of ground under the strict cap)."
 },
 {
  "plate": "79",
  "kind": "PDF sheet, 200 ft, 94 blocks (83.3 MP)",
  "scale_ft": 200,
  "why": "The best PDF-sheet output. No PDF sheet is in training (90 stays out). It brings the PDF scan colour, margins, KEY and lettering.",
  "risk": "The margins are confident block: mask them with N_mapground.png. Some joins on the left."
 },
 {
  "plate": "89",
  "kind": "PDF sheet, 200 ft, same-scale inset, estates/open land (82.6 MP)",
  "scale_ft": 200,
  "why": "A second PDF sheet, with an inset, large estates with unbuilt subdivisions, and a clean grid on the right half.",
  "risk": "The weakest of the ten. Estate regions merge across roads, so the strict cap drops 36% of the ground. Swap it first if needed (reserve 67)."
 }
]

### excluded

Every one of the 109 plates is in exactly one group; select.py checks this.
- **Rule:** 44 (the benchmark) and 90 (planned second truth plate).
- **Already labelled:** 43, 45, 80, 82A. 1A is Ben's check.
- **400 ft (10 plates):** 46, 47, 48, 49, 50, 92, 93A, 93B, 94, 95. I looked at all ten: the area net calls nearly the whole sheet block. Under a strict filter, 93B and 95 would teach 0.11 and 0.03 M half px.
- **Flagged suspect by the merged step, and broken by eye:** 2, 3, 41. On 2 and 3 the rail yards and riverfront are one region; on 41 the rail yards are.
- **Small pieces under 11 MP:** 8B, 15B (also suspect), 54B, 55B, 64B, 82B, 83B.
- **River or wharves inside a block:** 1B, 26A, 52, 59A, 59B, 60A, 21, 23.
- **Rail yards joined into blocks:** 13, 37, 40.
- **Open land or hillside joined across roads over most of the plate:** 25, 26B, 31, 35, 39, 61, 64A, 65, 70, 71, 75, 85A, and the PDF sheets 19, 22, 24, 27, 30, 32, 73, 74, 81, 88.
- **Inset at another scale (400 ft):** 78.
- **KEY inside a block, plus large joins:** 29, 34.
- **Large joins across streets over a big share of the plate:** 6, 9, 10, 14, 15A, 16, 17, 55A, 56, 57, 62, 63.
- **Fair but not needed** (their kind is already covered by a better plate), including the reserves: 4, 11, 12, 8A, 58, 18A, 18B, 28, 67, 85B, 60B, 83A, 84, 38, 69, 33, 87, 20, 36, 42, 72, 77, 86, 91.

**Kinds left uncovered on purpose:** hillsides, open land, the river itself, rail-yard ground and 400-ft sheets. Their pseudo labels are wrong where it matters, so only Ben's checks can teach them.

### how_many

**K = 10.** Most of the figures below are estimates, not measurements.
- **Labelled area against today:** the four labelled plates teach 52.4 M half-size px, or 1,633 acres (measured from N_label.png). With a sketch of the confidence filter, the ten teach about 93-105 M half px, or 2,360-2,750 acres (estimate). That is already 1.8-2.0 times today's pixels. At a 1:1 crop mix, more pseudo area only adds passes over the same kinds. 1A's three-quarters adds about 3.4 M half px, or about 34 acres (estimate).
- **Coverage of each kind:**
  - Scale mix after V2: 100 ft has 43, 1A and five new plates; 200 ft has 45, 80, 82A and five new plates. The batch is 36:63 at 100:200, and the benchmark is at 100 ft.
  - PDF sheets go from 0 to 2.
  - Six plates above tint 0.45 are added; the labelled plates are at 0.15-0.20, plus 1A at 0.75.
  - KEY boxes and lettering appear on 76, 79 and 89.
  - The next-best plates (67, 4, 12, 28, 11) repeat kinds already in. The plates that would add new kinds have bad pseudo labels.
- **RAM:** the line-net loader holds 12.0 bytes per full-size px, not 7 (measured): x is 7 bytes, the target 1, and the float32 weights 4. A whole PDF sheet is 0.93 GB.
  - Labelled + 1A: 309 MP, about 3.5 GiB. The ten: 748 MP, about 8.4 GiB. Together about 11.8 GiB, plus about 0.9 GB extra while a plate loads (estimate from the measured bytes per px).
  - The area net needs about 2.7 GiB (estimate).
  - That fits in the 33 GB free. K = 20 would need about 20 GiB: possible, but tight beside torch.
- **Loading time:** 0.5-2.1 s per plate (measured), so about 30 s per run.
- **GPU:** iterations are fixed, so the 2 variants x 2 seeds still cost about 6 h (4 pairs x 1.5 h) whatever K is.
- **Crops per plate:** the line net draws 24,000 crops of 448 px (4,000 x 6). At a 1:1 mix and K = 10, each pseudo plate gets about 1,200 crops, about 3 passes over a 75 MP plate (estimate). K = 20 would fall to about 1.6 passes. The area net still gets about 25 passes per plate.
- **Risk:** each plate beyond these brings more joins, river or open land into the labels.

### check_next

The ranking is by training value: what pseudo labels cannot teach, and how few edits Ben's check would need. 90 stays Ben's planned test plate; it is a benchmark, not training. If Ben checks any of the ten, it leaves the pseudo list and a reserve (67, 4, 12, 28) takes its place.
1. **7 (100 ft):** mid-block alleys are the main loss on 44 (all 32 misses there are joins). Pseudo labels cannot teach them: on 1A the line net misses them too. 7 has the densest alley grid and a clean output, so the check is quick.
2. **54A (100 ft):** heavy tint 0.65 next to 1A's 0.75, with three times 1A's ground (75.6 against 24.3 MP). A clean output, so few edits.
3. **60B (200 ft):** the case where 27 of about 30 mid-block alleys were missed. It is small (18.9 MP, 40 blocks), so it is the quickest check. Do it once Ben decides whether 200-ft alleys are block sides.
4. **79 (PDF sheet, 200 ft):** the only way to teach the PDF-sheet look with true labels, since 90 stays out. 94 blocks.
5. **51 (100 ft):** settles the river and wharf rule on a tinted downtown plate.
6. **5 (100 ft):** CBD, 64 blocks with alleys, and a clean output.

### numbers

Every number below names the script that made it. All scripts are in data/sanborn/bench_2026-11-23/train/select/.

**Measured**
- Labelled today: 52.44 M half px, 1,632.7 acres (pseudo_area.py; acres use the census px_per_ft).
  - 43: 16.57 M, 169.1 acres; 45: 11.97 M, 488.5 acres; 80: 10.23 M, 417.3 acres; 82A: 13.67 M, 557.8 acres.
- Pixel sizes from the JPEG headers (measure.py): the ten selected total 747.7 MP; labelled + 1A total 309.3 MP. A PDF sheet is 83.3 MP, a cut plate about 72-78 MP.
- Line-net loader (load_cost.py):
  - 12.0 bytes per full px; 0.93 GB for 79, 0.80 GB for 66.
  - Load 2.1 s (79), 1.8 s (66), 1.7 s (5), 0.5 s (60B).
  - First-load peak working set 1.82 GB.
- 1A against Ben's check (ben1a.py, ben1a.py --split): 21 blocks, 151 editor lines after his edits.
  - Confident area pixels: 62.6% of the paper; 91.5% right overall.
  - Leaving out the two big pieces Ben left unclosed (169,673 half px): 98.66% right, and 1.14% of his street ground is called confident block.
  - The merged step's blocks score PQ 0.21 against Ben's (5 of 21 found, 10 false).
  - Merged-mask pixel accuracy is 0.856.
- A band around lines_ng1 on 1A (ben1a_lines.py) catches 0.7% of the alley errors at 4 px, 2.3% at 8 px and 4.5% at 12 px. At 12 px it also blanks 6.8% of correct block.
- 1A validation area (val1a.py):
  - Right-hand image quarter: 9.9% of the paper, 1 of 21 blocks by centroid.
  - Cut at x = 3358 full px instead: 25% of the paper, 6 blocks by centroid, 3 blocks crossed by the cut.
- Confident share of the ground, per plate (measure.py): for example 5: 0.70, 54A: 0.75, 66: 0.82, 79: 0.78.
- The merged step's suspect flags (run_plates.json and N_blocks_ng.json): 2, 3, 15B, 41 and all ten 400-ft plates.

**Estimates**
- The ten, under a sketch of the filter (pseudo_area.py; the integrator's filter decides the real figure):
  - lenient cap: 104.8 M half px, 2,751 acres;
  - strict cap (98th percentile of label block size: 17.0 acres at 100 ft, 35.5 acres at 200 ft): 93.3 M half px, 2,362 acres.
- RAM at 12 bytes per px (select.py): line net about 3.46 GiB labelled + 1A, about 8.36 GiB for the ten; area net about 2.71 GiB.
- Crop passes: from the trainers' constants (4,000 iterations; 6 crops of 448 px and 8 crops of 384 px per step) at a 1:1 mix.
- GPU: about 6 h for 4 pairs, the plan's 1.5 h per pair, not re-measured.


## label maker

### summary

I wrote the label maker make_labels_v2.py and staged it. Nothing in the repo changed, nothing went into tools/, unet_data, picks22_guided, streetmap or cufp, and data/sanborn/train_v2/ was not created. I tested every mode in my own folder.

- 'label' (43, 45, 80, 82A): img/label/edge/area_in are copied byte for byte. lines.png is edgenet.load's t, made by the same code. The 'verify' mode loads each plate through the new folder and through unet.load, unet.load_edge and edgenet.load (blank guide, area_ng1). All 7 arrays are equal pixel for pixel on all four plates. Their area_in is in sample, and meta.json says so.
- 'map' (1A, and 44 for test only): builds Ben's street map with street_map.editor_lines and street_map.py's closing. For 44 it rebuilds streetmap/22-44.json exactly (lines, blocks, open ends and counts all equal).
  - Area label: his closed faces = 1 (block). Street = 0, found by rays from his lines on the non-block side, up to the next of his lines, a block or the paper edge (130 ft at most; only 20 ft where nothing is met). Where neither side is a closed block, a side counts as street only if it meets a parallel line of his (within 12°). Everything else is 255, with a 1 px band at every block edge as make_labels.py does.
  - Line target: his printed and drawn lines are positive. Sheet-edge lines are 255. Negatives use edgenet's 3 px line and GAP rules on the taught ground, plus an 11 px strip along each line he marked wrong.
  - valmask is the right-hand quarter.
- 'pseudo': labels from the merged batch outputs, kept only where confident. Thresholds tuned on 1A only: hi 0.95, lo 0.05, d 8, ds 6 (half-size px); ms 12, mr 6, mu 4 (full-size px); tl 0.1; plus two new rules on the line negatives: none within 20 ft of the paper edge, and none along long straight ink lines (80 ft or more) inside block ground. There is also an alley-strip test: two parallel long ink lines 8-45 ft apart, no building tint between, no line right across the strip, and the strip runs across the block. It works partly (see open issues).
- 'compare' gives the noise numbers. A format check runs on every plate folder before its meta.json is written. Guards refuse 44 and 90 in train_v2, and refuse the pipeline folders.

The pseudo labels are fairly clean where they teach anything. On 44 (not used for tuning): block precision 97.6%, street precision 99.7%, positive-line precision 80.6%, and 2.0% of Ben's line length is wrongly taught as negative. The main noise is merged streets and alleys taught as block, and open land taught as block. That open land is ground Ben's map leaves undecided, so it cannot be scored.

### files

All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-23/train/

STAGED (to review and apply):
- staged/tools/sanborn/unet/make_labels_v2.py: the label maker. Modes: label, map, pseudo, verify, compare. The docstring has the format, the rules, the units of every threshold, and a LOADING section with the exact recipe trainers must use to get today's arrays. It finds the repo by walking up from the file, so it runs from the staging folder or from tools/.

TEST OUTPUTS (my folder labels/):
- labels/out/: what train_v2 would hold for the five fixed plates: 43, 45, 80, 82A ('label') and 1A ('map', with valmask.png and streetmap.json), plus manifest.json (content_sha256 a760084d...).
- labels/test44/map/44 and labels/test44/pseudo/44: plate 44, test only, never in train_v2. Pictures: 44_errors.jpg, 44_pseudo_vs_ben.jpg, 44_map_viz.jpg.
- labels/batch44/: the merged outline step (tools outlines.py --out) run on the batch's 44 maps. outlines.json and 44_edges.json are byte-identical to bench_2026-11-21/merge/impl/bench44_runs/merged_batch.
- labels/pseudo1A/1A: 1A's pseudo labels for the comparison, with 1A_pseudo_vs_ben.jpg and 1A_errors.jpg.
- labels/smoke/60B and labels/smoke/30: pseudo smoke tests on a 200-ft cut plate and a 200-ft PDF sheet, with pictures.
- labels/verify_label_plates.json, compare_1A.json, compare_44.json, build_run.log.
- labels/tune/: tune.py (stages alley, area, lines, joint, final), alley_grid.py, alley_onoff.py, bigx.py, errors_viz.py, alley_debug.py and their JSON results (1A_area.json, 1A_lines.json, 1A_joint.json, 1A_alley_grid.json, 1A_alley_onoff.json, bigx.json). All on 1A only, except bigx.json, which also runs 60B and 30 (not 44).
- labels/explore/: look-around scripts (sm_check.py, along.py, viz.py, benlines_viz.py, benlines_list.py, errors_folders.py, step4_44.py) and pictures.
- labels/_second_copy/: a second copy of every script above, including make_labels_v2.py.

### numbers

All MEASURED unless marked. Pixels are half size for the area and full size for lines.

1. Proof for the four labelled plates (make_labels_v2.py verify, labels/verify_label_plates.json): 43, 45, 80, 82A each have unet.load x, unet.load label, load_edge weights, load_edge target, edgenet.load x, t and weights all equal (shape, dtype, every pixel). Line positives / negatives: 43 932,895 / 63,465,736; 45 1,230,588 / 44,586,888; 80 765,032 / 38,903,353; 82A 1,149,688 / 51,743,444.
   - img.jpg remake (one-off inline check): 80_img.jpg rebuilt by resize INTER_AREA + JPEG 92 is byte-identical in both cv2 4.13 and cv2 5.0.

2. Map labels (make_labels_v2.py map):
   - 44 street map = streetmap/22-44.json (lines, blocks, open_ends, counts all equal).
   - 1A street map: 151 lines (70 printed, 69 drawn, 12 sheet edge), 21 closed blocks, 24 open ends (20 at the sheet edge).
   - 1A area label: block 1,985,609, street 1,167,956, of 3,722,664 paper px. Validation quarter: 204,396 block and 126,197 street px.
   - 1A line target: 354,163 positive, 11,785,485 negative.
   - 44: block 5,703,051, street 3,388,311; 924,255 positive and 34,334,882 negative line px.

3. Pseudo against Ben's map. 1A is where the thresholds were TUNED, so its numbers are optimistic. 44 is a REPORT (make_labels_v2.py compare; compare_1A.json, compare_44.json):

| | 1A whole | 44 whole |
|---|---|---|
| Area: precision of taught block | 99.41% | 97.57% |
| Area: precision of taught street | 98.38% | 99.69% |
| Coverage of the ground Ben decided | 58.9% | 64.2% |
| (of which block / street) | 73.5% / 32.9% | 80.4% / 33.6% |
| Pseudo-taught px that lie in ground Ben left undecided | 12.8% | 42.7% |
| Lines: precision of positives (within 3 px of his printed/drawn lines) | 84.1% | 80.6% |
| Ben's line length taught positive | 52.0% | 53.1% |
| Ben's lines wrongly taught negative | 1.58% | 2.00% |
| (printed / drawn) | 0.28% / 3.6% | 1.56% / 4.54% |
| Ben's lines left 255 | 46.4% | 44.9% |
| Pseudo negatives that the map also calls negative | 99.9% | 99.9% |
| Share of the map's negatives the pseudo teaches | 49.5% | 53.0% |

   - The 42.7% undecided ground on 44 is the open land (creek, rail, canal): ground Ben's map does not score, and the pseudo labels mostly call it block.
   - 1A validation quarter: block precision 100% (108k px), street precision 98.4%, coverage 47.1%, Ben's lines wrongly negative 0.48% of 6,291 px.
   - 44 errors (errors_folders.py): 114,334 px false block, mostly merged streets and alleys and the canal bank; 3,552 px false street; 3,797 px of Ben's line length taught negative.

4. Tuning record (1A only; tune.py):
   - The first settings (hi 0.9, lo 0.1, d 12, no alley rule, no paper-edge or long-line rule) gave block precision 98.2%, street precision 98.2%, coverage 72.3%, and Ben's lines wrongly negative 11.8% (drawn lines 26%).
   - Area grid of 300 settings: hi is the main lever (block precision 96.1% at 0.5, 99.2% at 0.98). d barely matters. lo trades street precision against coverage.
     - Note: 1A_area.json was made before the map's parallel-line rule was added. With the final map, the final settings measure 99.41% block precision instead of 98.8%.
   - Line sweeps:
     - tl and ms barely matter, because the line net's answer is near all-or-nothing (explore/along.py): on 1A its maximum within 3 px exceeds 127 on 77% of Ben's printed lines and 41% of his drawn lines, and is 3/255 or less on 14% and 48%.
     - The real levers are mu, the paper-edge margin (20 ft) and the long-line rule (80 ft). Together they take the wrongly-negative share from 6.1% to 1.6%, while the share of the map's negatives taught falls from 57% to 49.5%.
   - Alley strips (alley_onoff.py): 22 strips on 1A; 67% of their area is Ben's street, 16% his block. With the final thresholds they raise block precision from 99.23% to 99.41% and cost 3.7 points of coverage; the line numbers do not change. With the crossing test off: 38 strips, 35% on Ben's block.
   - bigx (off by default; bigx.py): on 1A, bigx 3 cuts coverage from 58.9% to 49.1% with no precision gain. It removes 88% of the pseudo block on PDF sheet 30 and 19% on 60B.

5. Timing: building every test folder took 87 s (4 label plates, 2 map plates, 4 pseudo plates, verify, 2 compares; build_run.log). The 44 outline step took 12.7 s.

### how_to_run

After the staged file is copied to tools/sanborn/unet/make_labels_v2.py:

  cd data/sanborn
  $PY = ../../tools/sanborn/unet/.venv/Scripts/python.exe
  $PY -B ../../tools/sanborn/unet/make_labels_v2.py label 43 45 80 82A          (writes train_v2/43 ... and manifest.json)
  $PY -B ../../tools/sanborn/unet/make_labels_v2.py map 1A
  $PY -B ../../tools/sanborn/unet/make_labels_v2.py pseudo N1 N2 ...            (the K chosen batch plates; prints a WARNING for suspect or 400-ft plates)
  $PY -B -W ignore ../../tools/sanborn/unet/make_labels_v2.py verify 43 45 80 82A --json train_v2/verify.json   (exit 1 if any array differs)

Options:
- --out DIR writes anywhere except train_v2 for 44 and 90, and never into unet_data, picks22_guided, streetmap or cufp.
- The pseudo thresholds can be overridden: --hi --lo --d --ds --tl --ms --mr --mu --me --ll --gmin --bigx --no-alley. The defaults are the tuned ones.

44 test (never into train_v2), as I ran it:
  $PY -B ../../tools/sanborn/unet/outlines.py 44 area_ng1 lines_ng1 --area-png unet_data/44_pred_area_ng1.png --lines-png unet_data/44_lines_lines_ng1.png --out DIR44
  then blocks_noguide.step4 on DIR44/outlines.json written as DIR44/44_edges.json (labels/explore/step4_44.py)
  $PY -B make_labels_v2.py map 44 --out T/map ; $PY -B make_labels_v2.py pseudo 44 --out T/pseudo --outlines DIR44/outlines.json --edges DIR44/44_edges.json
  $PY -B make_labels_v2.py compare 44 --pseudo T/pseudo --map T/map --json T/compare_44.json

Trainers must load the folder as the LOADING section of the docstring says. That is exactly what verify does:
- area net input: img.jpg flipped to RGB, plus two blank guide channels.
- line net input: the scan cufp/22-N.jpg, edgenet.ink_image, two blank channels, and area_in.png resized LINEAR to full size.
- line target: lines.png as t; the per-pixel weights stay computed in the trainer as today.
- valmask is half size; resize it NEAREST for the line net.

### open_issues

1. The pseudo labels repeat the networks' merges.
   - Most false block on both plates is in streets and alleys that the networks merged into a block. 44 is a held-out report; 1A was the tuning plate, so its numbers are optimistic.
   - The alley-strip test only catches double-line alleys that pass all its tests. On 1A it misses:
     - Lurch St and Tiernan alley (one of them is only partly found);
     - Fenwick alley (its big lettering trips the crossing test);
     - Cylmer alley (a shed is drawn across it);
     - Colby alley.
   - Single missed street sides are only protected in the line target, by the long-line rule; in the area label they stay block.
   - This is the confirmation-bias limit from M7, and the 200-ft mid-block alleys are only partly addressed.
2. Open land is taught as block.
   - On 44, 42.7% of the pseudo-taught ground lies where Ben's map is undecided (creek, rail corridors, canal, farm tracts), and the pseudo calls most of it block. It cannot be scored.
   - Whether open land is block is one of Ben's unsettled conventions. The bigx option (off) removes big polygons, but on PDF sheets it drops most of the block (88% on plate 30).
   - Plate choice should avoid open-land-heavy and suspect sheets.
3. The long-line rule (80 ft) removes long lot lines and rear lot lines inside blocks from the line negatives. The share of the map's negatives that is taught falls by about 6 points on 1A. Pipe and sewer lines in the streets stay negative.
4. Ben has not checked the map labels' street ground; I constructed it with rays from his lines.
   - Settings: 130 ft at most, 20 ft where nothing is met beyond, parallel pairing within 12°.
   - Unclosed blocks are untaught; 1A block 17 is one.
   - The 11 px strip along each line he marked wrong is taught as negative even outside the decided ground.
   - Faces narrower than 60 px would be untaught; there are none on 1A or 44.
5. 1A's validation quarter is small: 204k block px, 126k street px and 6,291 px of Ben's line length. Checkpoint choice on it will be noisy; 44's right quarter has none of Ben's blocks (irrelevant, since 44 is test only).
6. The thresholds were tuned on one 100-ft plate. d, ds, ms, mr and mu are in pixels and do not scale with the plate's scale; the paper-edge margin, the long-line rule and the alley widths are in feet. 200-ft behaviour was checked only by eye, on 60B and on 30 (a PDF sheet with its map ground, outside the KEY and margin). No 400-ft plate was tried.
7. edge.png for pseudo plates is the green lines and for map plates Ben's printed and drawn lines, so the area net's third output is taught from them. Positive-line precision is 84% on 1A (tuning plate) and 81% on 44.
8. I did not write train_v2/. The integrator should run the label/map/pseudo/verify commands, keep 44 and 90 out (the script refuses them), and record manifest.json's content_sha256 in the model json.
9. The area_in.png of 43, 45, 80 and 82A is in sample (area_ng1 was trained on them), as the plan says; 1A's and the pseudo plates' are the batch's own maps (out of sample).


## trainers and evaluation

### summary

The two trainers, the evaluation script and a plate scorer are staged and smoke-tested on the GPU. Nothing has been trained for real, and nothing in tools/, unet_data, streetmap or picks22_guided was written (checked: no file there is newer than the start of my work, and git status for tools/ is clean).

What the trainers do now:
- **unet.py and edgenet.py** take `--data DIR`, `--seed S`, `--weights N=w,...`, `--out DIR` and `--val-every K` (default 250).
- **With `--data`**, each trainer:
  - scores the validation pixels (valmask.png) every 250 iterations;
  - saves NAME.pt as the best checkpoint (area net by iou_street, then accuracy; line net by F1) and NAME_last.pt as the last;
  - never draws a training crop that touches a validation pixel (it draws again);
  - refuses plates 44 and 90.
- **`--no-guide` fix:** no guide shift and no 255 squares. `--legacy-noguide` brings back the 21 Nov recipe.
- **Model json** records the seed, manifest sha256, git commit, the trainer file's sha256, every plate with its source, weight and file sha256s, the crops drawn per plate, the best iteration, the val history and memory.
- **Line-net memory:** each plate is stored as one 5-byte-per-pixel uint8 array instead of 12 bytes per pixel. The ink image and the weights are rebuilt per crop and are pixel-identical to today's.
- **Without the new options**, the old path still runs: 10-iteration check on copies of plate 80 in my folder. Two deliberate changes there: the `--no-guide` fix, and an unknown option is now an error instead of being read as a plate.

What eval_v2.py and bench_plate.py do:
- **eval_v2.py** predicts both maps the way blocks_noguide does, on 44's 6 tile grids (the offsets from make_maps44.py) and on 1A.
- It runs the real bench44 `--grids`, paired with baseline runs on data/sanborn/bench44_maps. It reuses a baseline run when the map's sha matches.
- It scores 1A's validation region for the new pair and for the batch's own 1A maps, and writes everything to one output folder.
- **bench_plate.py** wraps bench44 rather than copying it. The plate, the truth file and a region mask (fold A = inside the region) replace the 44 settings, and bench44's scoring code runs unchanged.
- `bench_plate.py --make-truth` builds a street map the way street_map.py does, into any folder. It reproduces streetmap/22-44.json byte for byte, so I used it to make 1A's truth (151 lines, 21 blocks) in my folder.

Two findings you need before training:
1. **The 1A right-hand quarter is a thin validation area.** It is 24% paper and holds 1 of Ben's 21 blocks (by centroid) and 9% of the interior line length (6.3k of 71k px). Block scores there mean nothing, and checkpoint choice on it will be noisy. The select agent has measured an alternative cut at x = 0.583 W (25% of the paper, 6 blocks, 3 blocks cut by the line). The trainers take any valmask.png, so this is your call.
2. **The 1A truth favours the baseline.** Ben made it by editing the batch's (area_ng1 + lines_ng1) lines, so every line he left alone is exactly the baseline's. On 1A the baseline starts ahead on line position.

### files

Staged code (C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-23/train/staged/tools/sanborn/unet/):
- unet.py: the area trainer with --data, --seed, --weights, --out, --val-every, keep-best, the --no-guide fix and the model-json records. It also holds the shared helpers: sha256, git state, manifest reader, integral-image crop test, memory probe.
- edgenet.py: the line trainer, the same options, the 5-byte-per-pixel plate store (pack, build), keep-best by pooled F1.
- eval_v2.py: the end-to-end evaluation described in the summary; writes OUT/eval_v2.json.
- bench_plate.py: the bench44 wrapper for any plate, truth file and region; also --make-truth N OUT.json.
- (make_labels_v2.py in that folder belongs to another agent, not me.)

My folder (C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-23/train/trainer/):
- staged_copy/: second copy of my 4 staged files (sha256: unet ac2df592c394b2da, edgenet 8eea6f0f946eb21a, eval_v2 c8c40319e11ee7c7, bench_plate 53a3703f53a87943).
- diffs/unet.diff, diffs/edgenet.diff: the staged trainers against the repo files. unet_repo_orig.py and edgenet_repo_orig.py are copies of the originals.
- make_testdata.py and testdata/: the TEST data folder, with a manifest.
  - 80 is copied byte for byte from unet_data; its lines.png is what the repo's edgenet.load builds; valmask = right quarter.
  - 1A is a crude stand-in pseudo plate (area_ng1 > 0.95 or < 0.05; empty edge.png; Ben's lines as the line target; right quarter as valmask). Not training labels.
- check_equal.py and check_equal.json: old loaders against the --data loaders, and 50,000 sampled crops against the valmask.
- memtest.py and memtest.json: the 20-largest-plate memory test.
- legacy_check.py and legacy_check.json, legacy_data/: the old path on copies of plate 80's files.
- truth_check/: 22-44.json (byte-identical to the streetmap file), 22-1A.json (Ben's 1A truth), 1A_valmask.png (right quarter).
- bench_check/: base__grid0 and base__grid3 (bench44 on the baseline maps, reusable as --baseline-runs), wrap44 (the wrapper on 44), batch_1A.
- smoke/: the smoke models, jsons and logs. eval_smoke/ and eval_faith_ng1/: the two eval_v2 runs.

### numbers

All measured on 23 Nov unless marked as an estimate. GPU: AMD RX 7900 XTX through DirectML.

Correctness:
- check_equal.py, plate 80, today's loaders against the --data loaders, pixel for pixel:
  - area net: 5-channel input, label, edge weights and edge target all equal;
  - line net: all 7 input channels, the target and the weights equal over the whole plate;
  - 20 random 448 px windows built alone equal the whole-plate build.
- check_equal.py, crops: 50,000 crops per sampler on 80 and 1A, 0 touching a validation pixel. Area crops reach exactly the validation edge (x 2160 and 3485). Line crops stop 3 px short (4318 against 4321; 6968 against 6971).
- Seed (smoke runs a1 and a2, area net, seed 1, 30 iterations): identical losses and val scores, weights differ by 0.0. The line net was not repeated with the same seed.
- bench_plate.py --make-truth 44 equals streetmap/22-44.json byte for byte (sha256 eb6d6916...).
- bench_plate on 44 with no region against bench44 on grid0: identical outlines.json, headline, line, workload, sheet and stage scores (PQ 0.543).
- eval_v2.py with area_ng1 + lines_ng1, grids 0 and 3:
  - maps identical to bench44_maps grid0 and grid3, and to the batch's 1A maps;
  - every paired gain 0.0;
  - PQ 0.5378 (sd 0.0073) over these 2 grids.
- legacy_check.py: the old path trains 10 iterations of each net. Its quarter hold-out on 80 scores 2,371,107 px, the same as the test valmask.

Speed (smoke logs, train_s_per_iter excludes validation):
- area net: 0.68 to 0.77 s per iteration; validation of two quarters 0.45 s;
- line net: 0.70 to 0.72 s per iteration; validation 1.56 s;
- for comparison, area_ng1 and lines_ng1 took 46.4 and 46.3 min for 4000 iterations, about 0.70 s per iteration including validation on 44 (their model jsons).

Memory:
- Smoke runs, peak working set: area 1.9 GB, line 2.7 GB. Private bytes are 7.0 and 8.4 GB, mostly DirectML's commit, not plate data.
- memtest.py, the 20 largest plates (1,666 Mpx, mostly 83 Mpx PDF sheets, worst case):
  - line store 8.33 GB, working set 8.5 GB (peak 8.85 GB), loaded in 15.3 s;
  - today's loader would hold 20.0 GB for the same plates;
  - the area store on top adds 4.58 GB (working set 13.1 GB).
- Estimate: a 20-plate line training uses about 11 GB working set (store plus about 2.3 GB overhead) and about 16 to 17 GB private commit. That is within the 25 GB budget.

eval_v2 timings:
- smoke (grid0 and 1A): 58 s;
- faithfulness run (2 grids, one new baseline run): 103 s; maps 1.3 + 5.0 s GPU per grid; bench44 about 30 s per grid on CPU; 1A scoring 11.6 s.
- Estimates: a 6-grid evaluation takes about 4 to 5 min (about 1.5 min more the first time, for the baseline runs). A 4000-iteration training takes about 45 to 50 min per net, so V1 and V2 with 2 seeds (8 trainings) take about 6.5 h of GPU.

1A truth (bench_plate.py --make-truth, then bench_plate.py):
- 151 lines, 21 blocks.
- By x quarter: blocks 5 / 7 / 8 / 1; paper share 0.87 / 0.75 / 0.59 / 0.24.
- Batch maps (ng1) on the right quarter: recall_interior 0.7315, precision 0.7594, PQ 0 (its one block is split). Whole plate: PQ 0.2103, recall 0.6145, precision 0.8585.

The smoke models' scores (PQ 0 on 44; they call 99.75% of it block) only show that the chain runs. They say nothing about the recipe.

### how_to_run

After the staged files are copied into tools/sanborn/unet/, from data/sanborn in PowerShell:

$VPY = "..\..\tools\sanborn\unet\.venv\Scripts\python.exe"

V1, seed 1 (no pseudo plates; 1A uses its valmask.png):
  & $VPY -B ..\..\tools\sanborn\unet\unet.py train area_ng2_v1_s1 --data train_v2 43 45 80 82A 1A --seed 1 --iters 4000 --out bench_2026-11-23\train\models
  & $VPY -B ..\..\tools\sanborn\unet\edgenet.py train lines_ng2_v1_s1 --data train_v2 43 45 80 82A 1A --seed 1 --iters 4000 --out bench_2026-11-23\train\models

V2: the same command with the pseudo plates added to the plate list, plus for example --weights P1=0.5,P2=0.5. Leaving out the plate list trains on every plate in the manifest.

Evaluate a pair:
  & $VPY -B ..\..\tools\sanborn\unet\eval_v2.py --area-model bench_2026-11-23\train\models\area_ng2_v1_s1.pt --lines-model bench_2026-11-23\train\models\lines_ng2_v1_s1.pt --out bench_2026-11-23\train\eval\v1_s1 --baseline-runs bench_2026-11-23\train\eval\baseline44
- Use one shared --baseline-runs folder, so the baseline is run once.
- 1A's truth: pass --truth-1a, or eval_v2 makes it from Ben's edits.
- 1A's region: --region-1a, else train_v2/1A/valmask.png, else the right-hand quarter.

Running the staged copies before they are applied: set PYTHONPATH to "<repo>\tools\sanborn;<repo>\tools\sanborn\unet" so _ws and bench44 are found, as all my tests did.

Tests (in my folder, venv python with -B): make_testdata.py, check_equal.py, memtest.py, legacy_check.py.

### open_issues

1. The 1A right-hand quarter is a thin validation area: 1 of 21 blocks, 24% paper, 9% of the interior line length. Checkpoint choice on it will be noisy and 1A block scores there are meaningless. The select agent's alternative cut is at x = 0.583 W (25% of the paper, 6 blocks, 3 blocks cut by the line). Your call or Ben's; the code takes any valmask.png.
2. The 1A truth comes from Ben editing the baseline's lines, so the baseline is favoured on 1A. Fold B of 1A (outside the region) is in sample for the v2 networks.
3. The line net is validated with area_in.png (the ng1 area map) as its 7th input, but in use it gets the v2 area map. So its checkpoint choice does not see the v2 area net. For 43, 45, 80 and 82A, area_in is in sample (their own N_pred_area_ng1.png).
4. Manifest format my reader accepts:
   - {"plates": {N: {"source": ..., "files": {name: sha256 or {"sha256": ...}}}}}, or plates as a list of {"plate": N, ...};
   - a file whose sha256 disagrees with the manifest stops training;
   - a file the manifest does not list is recorded as in_manifest false.
   The integrator should match this. meta.json: source, area_in, and the scale as scale_ft_per_inch, ft_per_inch or scale.
5. An empty or missing edge.png means the area net's third output (edge drawing) is not taught on that plate: weights 1, target 255. Pseudo plates add nothing to that output.
6. Two recipe differences from 21 Nov:
   - with --data, each crop picks its plate first, so the default is an equal share of crops per plate (realised counts are in the model json); before, the share depended on how many crops each plate rejected;
   - the --no-guide fix changes the random draws of the old --no-guide path. --legacy-noguide restores them.
7. The same-seed check covers the area net over 30 iterations only. It is not known whether 4000 DirectML iterations stay identical, so the two-seed spread is still needed.
8. Not tested: the real train_v2 folder (it does not exist yet), a full training run, a 6-grid evaluation of a real model, and the area and line nets training at the same time on the GPU.
9. bench44 --grids scores every grid folder it finds. eval_v2 refuses an --out whose maps44 holds grids from an earlier run; use a new --out per evaluation.


## review: leak

## review-leak: leakage and evaluation check of train_v2

**Verdict.** Plates 44 and 90 cannot reach training. No training crop can touch 1A's validation ground. The driver chooses checkpoints on that ground and nowhere else. eval_v2 reproduces the known numbers exactly. The seeds work, at least on the CPU. The 7th channel is the file the plan names.

I found one real problem the plan missed (finding 1). There are also two cautions about how the results should be read (findings 2 and 3).

Everything below was measured unless I mark it as an estimate. I did not use the GPU. I wrote only into `data/sanborn/bench_2026-11-23/train/review-leak/`. `git status tools/` is clean, and no file in unet_data, picks22_guided, streetmap or cufp is newer than the integrator's check_data.json.

### Findings, most serious first

**1. On the pseudo plates, the line net's target can be read straight off its 7th input. This is new, and it only affects V2.**
- Scripts: `scripts/channel7_boundary.py` and `scripts/channel7_shortcut.py`.
- Where area_in crosses 0.5 on the ten pseudo plates, **0.00%** of those pixels are taught as "not a line", and 0.00% are within 3 px of a "not a line" pixel. The rest are either line (12–42%) or not scored.
- On the labelled plates the same pixels are taught "not a line" 22–40% of the time (43: 37%, 45: 22%, 80: 27%, 82A: 40%), and 40% on 1A's training part.
- Test rule: "draw a line wherever area_in crosses 0.5, within 3 px". Scored against the line targets:

| Plates | Precision | Recall |
|---|---|---|
| Pseudo (all ten) | 1.000 | 0.65–0.79 |
| Labelled 43, 45, 80, 82A | 0.54–0.73 | 0.55–0.63 |
| 1A | 0.48 | 0.46 |

- **Cause:** make_labels_v2 keeps pseudo "not a line" pixels at least mu px away from ground the area label leaves untaught. The area label is untaught within d=8 / ds=6 px of every outline edge and wherever area_ng1 is between 0.05 and 0.95. That covers every 0.5 crossing.
- **Effect:** in V2, half the line-net crops never penalise drawing along the 7th channel's edge. This is target leakage: the input already contains the answer.
  - That area_in is out of sample for area_ng1's training does not help, because the pseudo targets were built from that same map.
  - On 44 the 7th channel will be the new area net's map, and its edges are real non-lines 30–40% of the time.
  - The likely result is more false lines wherever the area net is wrong. That would be a V2-only confirmation-bias path, on top of the one the plan already names. This effect is my estimate; it has not been measured.
- **Options, for a decision:**
  - Feed 128 (meaning "no area map") as the 7th channel on pseudo crops, either with a trainer flag or by leaving out area_in.png for those plates. The trainer already uses 128 when the file is missing, and on 15% of crops anyway. Changing the data folder changes the manifest sha256.
  - Or allow "not a line" pixels up to the 0.5 crossing wherever lines_ng1 was quiet.

**2. 1A's validation numbers are not untouched. Do not use them to compare V1, V2 and the baseline.**
- The same validation pixels choose the best of 16 checkpoints per network (every 250 of 4,000 iterations), so the chosen checkpoint's score there is biased upward.
- The pseudo-label thresholds were tuned on the whole of 1A, including what is now the validation ground (35% of the paper). See `labels/tune/tune.py`, which compares against the whole-plate map labels.
- The ground holds only 9 of Ben's blocks. The baseline's PQ of 0.0928 is 1 block matched, so a single block moves PQ by roughly 0.08–0.10 (estimate).
- Only 44 is untouched.

**3. The rule for picking which pair to ship is not set.**
- The driver chooses nothing on 44. But how_to_run then says "copy its NAME.pt as area_ng2.pt". If that choice among the 4 runs is made on 44's PQ, 44 stops being untouched for the pair that ships. The effect is mild with 4 candidates, but real.
- Suggestion: write the rule down before the run, for example "V2 only if its paired gain on 44 beats the seed-to-seed spread for both seeds". Keep plate 90 as the final untouched check once Ben has checked its lines.

**4. Earlier uses of 44: indirect, none new, recorded for completeness.**
- area_ng1 and lines_ng1 were trained with 44 as validation. It was only watched: the old trainers save the last checkpoint, which I checked in the repo code.
- The merged outline step was accepted on 44's numbers (0.431 to 0.543), and the pseudo labels are that step's output.
- The plate selection used 44's error pattern (100 ft, alleys).
- The label agent did report pseudo-label quality on 44, but did not tune on it:
  - tune.py asserts "1A only";
  - `tune/compare_44_before_bigx_param.json` is byte-identical to `compare_44.json`;
  - the bigx option it was added before defaults to off;
  - the block size cap leaves 44 out (pseudo_area.py line 57).

**5. 43 and 45 share sheet-join strips with 44. Negligible.**
- Script: `footprints.py` and `overlap44_blocks.py`, using the placements' world grids.
- 43 covers 1.6% of 44's paper and 45 covers 3.9%.
- Only 373 of 62,257 points on a 2 m grid inside Ben's 44 blocks (0.6%) lie on 43's or 45's paper. Only 26 of those (0.04%) are taught as block there; the rest are taught street. This was already the case for area_ng1/lines_ng1.

**6. No training plate shows 44's or 90's ground.**
- Script: `image_overlap3.py` (SIFT feature matching on the scans).
- Each training plate scores 4–7 matching points against 44 or 90. A 10% strip of the same sheet scores 3,529 (44) and 1,715 (90); a middle third at half scale scores 550 and 761. Note these controls are the test sheet itself, so a different printing of the same ground would score lower.
- An earlier pass found 119–228 matches between 90 and 89, 79 and 76. Those were the printed KEY legend, which is the same on every sheet (`overlap_pics/90_vs_89.jpg`). That pass is superseded.

**7. Crops cannot reach 1A's validation ground.**
- Script: `crop_leak.py`, calling the staged code's own functions.
- Area net:
  - 616,512 crop positions (every x, every 7th row) and 400,000 random draws (seeds 1 and 2): none touch it.
  - The farthest crop ends at x=1420 (half size); the validation ground starts at 1420.
- Line net:
  - 15,795 positions and 200,000 draws: none touch it.
  - The farthest crop ends at full-size column 2838; the validation ground starts at 2841.
  - The one-pixel safety margin held in 12,000 random small-mask tests (0 misses).
- Indirect effects of the validation ground on training data:
  - the edge weight map changes by at most 0.0002;
  - the edge target does not change;
  - none of Ben's 21 blocks crosses the cut.
- valmask.png is a clean half-plane, and only 1A has one.

**8. Seeds are applied, on the CPU.**
- Script: `seed_test.py`. It runs the staged train_data for 2 iterations on 1A, with the device forced to the CPU.
- Same seed: identical weights (largest difference 0.0) and identical validation history, for both networks.
- Seed 2 against seed 1: weights differ by up to 0.34 (area net) and 0.32 (line net).
- The model json records the seed, the manifest sha256 (1b9c5fc5…), git commit 017ce0c and the trainer's sha256. The git commit does not identify the staged code until it is committed; the trainer's sha256 does.
- On the GPU, only the area net's repeatability has been shown (by the trainer agent, over 30 iterations). The line net's is still untested. Suggestion: run a 30-iteration line-net pair with the same seed twice before the 6.5 h run.

**9. eval_v2 reproduces the known numbers.**
- Per-grid PQ is identical to `bench_2026-11-21/merge/impl/bench44_runs/merged_grids.json`: 0.543, 0.5125, 0.5208, 0.5327, 0.4893, 0.4652; mean 0.5106, sd 0.0288. Recall, precision, merges and false blocks are identical too.
- The 6 baseline maps are byte-identical to bench44_maps (sha256), and grid 0 is the batch's own unet_data/44 maps.
- My own reruns:
  - bench44.py on grid 0: PQ 0.543, recall 0.6214, precision 0.8226, merges 12, false blocks 8.
  - bench_plate.py on the batch's 1A maps: validation ground PQ 0.0928 (1 of 9 blocks matched, 3 merges, 6 false), outside it 0.3043, whole plate 0.2103.

**10. The 7th channel is what the plan says.**
- area_in.png is byte-identical to unet_data/N_pred_area_ng1.png on all 15 plates.
- Recomputed from area_ng1.pt on the CPU for 1A and plate 7: largest difference 1/255, on 0.001% of pixels, with no block/street decision changed.
- area_ng1 was trained on 82A, 80, 43 and 45 (with 44 as validation). So area_in is in sample on those four, as their meta.json says, and out of sample on 1A and the ten pseudo plates (but see finding 1).
- eval_v2 feeds the new area net's map into the line net.
- By design, the line nets choose their checkpoint with area_ng1's 1A map as the 7th input, but are evaluated with the new area net's map.
- The in-sample maps on the four labelled plates fit the true lines better than at deployment: the area_in-crossing rule scores F1 0.61 on them against 0.47 on 1A. This was already true for lines_ng1.

**11. Guards.**
- Script: `guards_and_area_in.py`.
- The staged trainers refuse 44, 44:val, 90, 90:val, mixed lists, and a data folder that contains a 44 plate (`labels/test44/map`).
- Script: `data_checks.py`. The data folder:
  - holds 15 plates, with no 44 or 90 by name, image hash or scan hash;
  - has no full.jpg, so the line net reads cufp/22-N.jpg;
  - has all manifest sha256s matching, and content_sha256 recomputes correctly.

**12. Small fix: pin 1A's truth.**
- The baseline step builds the 1A truth from the live edges_ben.json. Today that file is unchanged since the labels were made (7adfecdd…), and the truth equals train_v2/1A/streetmap.json (6089ada1…).
- If Ben edits 1A before the run, or a step is run with `--only` before the baseline, the truth would differ from the labels the checkpoints were chosen on.
- Fix: pass `--truth-1a train_v2/1A/streetmap.json` in the driver.

### Files
All under `C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-23/train/review-leak/`:
- `scripts/`: 13 scripts. There is a second copy in `_second_copy/scripts/`.
- Results:
  - channel7_boundary.json, channel7_shortcut.json
  - crop_leak.json
  - seed/seed_test.json
  - data_checks.json
  - guards_and_area_in.json, area_in_recompute.json
  - footprints.json, overlap44_blocks.json
  - image_overlap3.json (and the superseded image_overlap.json and image_overlap2.json)
  - overlap_pics/
- Reruns: bench44_runs/rl_grid0/bench44.json and bench1A_runs/rl_batch1A/bench_plate.json.
- driver_dry.log: the staged driver's dry-run commands. It shows no 44/90, --seed 1/2, and V2 weights of 0.5.
- `seed/` holds 356 MB of throwaway test checkpoints (.pt). They can be deleted.

## review: labels

## Label review (review-labels): summary

**Verdict.** The data folder loads exactly as today's inputs do. 1A's map labels are right. The pseudo labels are about as precise per pixel as earlier reported: 98–99% for block and street on both 1A and 44. Per-pixel precision hides the real weakness, though. On plate 44 the pseudo labels still join 11 of Ben's 55 blocks across alleys and narrow streets, and they teach the sides of those missed alleys as "not a line". That is the same error that costs PQ on 44. The selection is sensible for size and complexity, with one gap: it has no low-tint 100-ft residential plate like 44.

Nothing was written outside `bench_2026-11-23/train/review-labels/`. There are no new files in tools/, unet_data, picks22_guided, streetmap, cufp or train_v2, no new `__pycache__`, and `git status tools/` is clean. No GPU was used.

### 1. Do 43, 45, 80 and 82A load through train_v2 exactly as today? Yes (measured)

**Scripts:** `scripts/load_hashes.py` (two processes) and `compare_hashes.py`, giving `load_compare.json`.
- **Today's loaders:** `tools/sanborn/unet` `unet.load` + `load_edge`, and `edgenet.load` with NOGUIDE and `AREA=area_ng1`.
- **New loaders:** the staged trainers' own code, `unet.load_data` and `edgenet.load_data` + `build`, on the real train_v2. The integrator's check went through make_labels_v2.py's copy of the formulas instead.

**Result: `all_equal: true`.** On all 4 plates the following are equal (sha256 of the bytes, plus shape and dtype):
- area net: x, label, edge weights, edge target;
- line net: x, target, weights;
- each of the 7 line-net channels;
- 40 random 496-px line-net windows per plate, built by `build()` and compared with slices of today's arrays.

`bytes_check.json` adds:
- img, label, edge and area_in are byte-identical to the unet_data files;
- the manifest sha256 values match all 15 plates, and content_sha256 is right;
- 44 and 90 are absent.

### 2. Pseudo-label precision, recomputed independently (measured)

**Script:** `scripts/score_pseudo.py`. It reads Ben's street maps directly: `streetmap/22-44.json`, and `train_v2/1A/streetmap.json` for 1A. It does not use make_labels_v2's street rays.
- **Block:** Ben's closed faces at least 60 px across.
- **Street:** ground between two of his lines that face each other (within 15° of parallel) no more than 130 ft apart, plus narrow faces.
- **Undecided:** everything else.
- A 2-px band at block edges is not scored.

**Pseudo labels used:** rebuilt with the final staged make_labels_v2.py (sha b94bc870…) by `scripts/build_pseudo_1A_44.sh`, into `review-labels/pseudo/`.
- 1A is byte-identical to the integrator's test build.
- 44 uses the integrator's baseline merged-step run on the batch grid (base__grid0).

| | 1A whole | 1A validation area (x ≥ 1420) | 44, with the cap (as train_v2) | 44, no cap |
|---|---|---|---|---|
| Block precision | 99.3% | 99.5% | 98.3% | 96.9% |
| Street precision | 98.5% | 99.4% | 99.7% | 99.7% |
| Pseudo block lying on ground Ben's map leaves undecided | 10.2% | 0% | 18.6% | 46.8% |
| Ben's alleys and narrow streets (≤ 40 ft): taught block / street | 3.5% / 15.8% | 4.9% / 14.7% | 4.5% / 28.5% | 8.7% / 28.5% |
| Ben's wider streets taught block | 0.4% | 0% | 1.8% | 3.2% |
| Ben's blocks joined into one pseudo-block piece | 8 of 21 (3 pieces) | 4 of 9 (2 pieces) | 11 of 55 (4 pieces) | 11 of 55 |
| Line positives within 3 px / 6 px of Ben's lines | 83.6% / 90.4% | 88.8% / 95.4% | 80.3% / 87.4% | same |
| Ben's lines: positive / negative within 2 px / not taught (255) | 52.0% / 1.9% / 46.4% | 55.4% / 0.8% / 44.2% | 53.1% / 1.9% / 45.3% | 53.1% / 2.4% / 44.9% |

**How these compare with the earlier figures:**
- **1A:** earlier 99.41% block and 98.38% street; mine 99.26% and 98.46%. They agree.
- **44:** the labels agent's 97.6% / 99.7% was measured before the cap existed. The cap is what train_v2 uses, and it lifts block precision to 98.3%. It removes 4.54 M half-size px of block on 44 (44% of its block label).
- **1A lines are optimistic:** Ben's 1A lines began as the batch's lines.

**Where the errors are (measured):**
- **Joins across alleys.** Pixel precision stays high because alleys are thin. The joins are what costs PQ.
- **Alley sides in the line target.** Script: `scripts/alley_sides.py`, giving `alley_44.json`. On 44, 3.3% of the length of Ben's alley-side lines has a negative within 2 px, against 1.0% for his other lines. 11.9% of alley-side length lies inside taught block.
- **The area net's edge target.** Script: `scripts/edge_target_check.py`. On 44, 8.5% of Ben's line length is taught "no edge" (target 0), and 36% is untaught. On 1A's pseudo labels the figure is 8.1%. This is 4.5 times the line net's figure. The likely cause is that only green lines are positive and every other taught pixel is 0.
- **Positives more than 6 px from any of Ben's lines.** On 44 this is 75.5k px, 12% of positives:
  - 31.8k px in his streets, 9.0k inside his blocks, 34.7k on undecided ground;
  - by eye in `pics/44_far_positives.jpg`, mostly along the railroads, the Spring Grove Avenue rail, the Miami & Erie canal bed and the Mill Creek ground;
  - this is the known rail-line failure, carried into the targets.

**1A's map labels**, run through the same scorer (`score_1A_maplabels.json`):
- block and street precision 100%;
- Ben's lines 99.98% positive, with none negative within 2 px;
- 96.9% of his blocks and 86.1% of his street ground are taught.

### 3. Full-resolution crops (900 × 700 full px; by eye)

Crops are in `crops/`, made by `scripts/viz.py`. Each has the area label on the left and the line target on the right.

**1A map labels** (4 random crops): right.
- Blocks are Ben's blocks.
- Cylmer Alley and the other alleys are taught street.
- His lines are positive with untaught margins.
- Lot lines, tracks and pipe labels are negative.
- The unclosed block west of Central Parkway is untaught.
- The one doubtful case is Ben's call: a 30-ft double-line passage inside the J.A.S. block, which he did not draw, is taught block and negative.

**Pseudo plates 5, 7, 54A, 66, 76 and 79** (2 random crops each), plus two crops on 44.

Mostly right:
- Taught block and street sit in the right places.
- Street is taught only as bands along streets.
- On 7, the mid-block alley found by the networks is handled well: sides positive, middle untaught.
- On 66, a diagonal 20-ft right-of-way is left untaught by the long-line rule, as intended.
- Lot lines are mostly untaught because of the line-net margin, so negatives are mainly blank paper and buildings.

Wrongly taught:
- **Alleys taught as block, with their printed sides as negatives:**
  - 5: Habig alley (`ps5_0`);
  - 54A: the "ALLEY" at the upper left (`ps54A_0`);
  - 66: a dashed ALLEY (`ps66_0`);
  - 44, Lingo/Kendall (`ps44_lingo`): one block piece across 3 of Ben's blocks, with his alley lines negative;
  - 44, the 25-ft diagonal alley at block 30 (`ps44_diag`): its upper half is taught block with negative sides; the alley test caught the lower half.
- **A false positive along a streetcar track** in a street on 5 (`ps5_1`).
- **On PDF sheet 79**, Laurel Cemetery and open lot 90 are taught block, with negatives throughout. That is Ben's unsettled convention, and it matches 43. Also on 79, a grey curved band ("435") has its outline taught negative on one side. I cannot tell whether it is a creek or a road; if it is a road, those negatives are wrong.

### 4. Is the selection sensible for "complexity and size"? Yes, with one gap (judgment, with census figures)

**Size:**
- All ten are full plates of 58–83 MP, with 5.7–10.5 M taught half-size px each.
- Together that is 88.6 M px, against 54.4 M for the labelled plates plus 1A.
- With weight 0.5 they get about half the crops.

**Complexity:** the spread is good.
- downtown alleys: 5, 7, 53, 54A;
- heavy tint: 54A at 0.65, 53 at 0.59, 51 at 0.56, 68 at 0.54;
- the riverfront: 51;
- diagonal grids and a KEY: 76;
- a dense 200-ft grid: 66;
- PDF sheets: 79 and 89.

The exclusions follow the 21 Nov findings: 400-ft sheets, suspect plates, river inside a block, rail yards joined, open land joined.

**The gap.** Plate 44 has a tint of 0.255. Every selected 100-ft plate has a tint of 0.49–0.65. Only 43 (0.197) teaches the low-tint 100-ft look.

**Suggestion (not measured on PQ):** swap 89 for 58.
- 89 is the weakest of the ten: 36% of its ground is dropped.
- 58 is 100 ft with tint 0.27, 56 blocks and 6 holes, and 11.17 M taught half-size px. It has no big blocks under the strict cap. In `select/views/sheet_07.jpg` it shows mostly one colour per block.

**On the number of plates:** 10 is enough. More pseudo plates cannot teach the missed alleys and would add more of the same bias.

### Open issues for the plan
1. **V2 may make the joins worse, not better.** The pseudo labels teach joins on about 1 in 5 of Ben's blocks (on 44), missed-alley sides as negatives, and 8.5% of block lines as "no edge" for the area net. Only the V1 against V2 comparison over two seeds can show whether that hurts.
2. **Cheap option, untested.** On pseudo plates, leave the area net's edge target untaught (255) except on the green lines. Its 8.5% wrong "no edge" is the largest wrong-negative figure I measured.
3. **Rail and canal lines stay as positives** in the pseudo line targets. Plates 53, 76 and 51 are likely to carry more of them (estimate, not measured).
4. **Confidence filtering picks the easy ground.** The cap removes 44% of 44's block label but nothing on 5, 54A, 53, 7 or 66. So the pseudo labels come from the plates and places where the networks already do well.

### Files
Everything is under `C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-23/train/review-labels/`:
- **scripts/:** `load_hashes.py`, `compare_hashes.py`, `score_pseudo.py`, `alley_sides.py`, `edge_target_check.py`, `viz.py`, `build_pseudo_1A_44.sh`
- **Load checks:** `load_today.json`, `load_staged.json`, `load_compare.json`, `bytes_check.json`
- **Pseudo labels:** `pseudo/` (1A and 44, with the cap); `pseudo_nocap/` (44 without the cap); `build_pseudo.log`
- **Scores:**
  - `score_1A.json`, `score_44.json`, `score_44_nocap.json`, `score_1A_maplabels.json`, plus their `.log` files and `*_truth.jpg` pictures;
  - `summary_scores.json`;
  - `alley_44.json`, `alley_1A_pseudo.json`, `alley_1A_map.json`
- **pics/:**
  - overviews: `1A_pseudo_over.jpg`, `44_pseudo_over.jpg` (red = block taught on Ben's street, magenta = street taught on his block);
  - `44_far_positives.jpg`;
  - `1A_truth_nar.jpg` (debug)
- **crops/:**
  - 1A map labels: `map1A_0`–`map1A_3`;
  - pseudo plates: `ps5_0`/`1`, `ps7_0`/`1`, `ps54A_0`/`1`, `ps66_0`/`1`, `ps76_0`/`1`, `ps79_0`/`1`;
  - plate 44: `ps44_lingo`, `ps44_diag`
- **_second_copy/:** the scripts and the key JSONs

## review: code

REVIEW-CODE: adversarial review of data/sanborn/bench_2026-11-23/train/staged/ (staged.diff against HEAD 017ce0c)

SUMMARY
I found no bug that teaches on 44 or 90, trains on 1A's validation pixels, or breaks train_noguide.py. Seeds, keep-best, crop sampling and the manifest check all work on the CPU. The real risks are in running the job overnight:
- a Windows file clash in eval_v2's parallel bench44 runs;
- a driver that stops the whole run when one eval fails;
- a resume that crashes on a half-written json.
Each finding below gives its place and a fix, most serious first. I used no GPU. Every test ran on the CPU under the venv, and I wrote only into data/sanborn/bench_2026-11-23/train/review-code/. Nothing in tools/, unet_data, picks22_guided, streetmap, cufp, train_v2 or staged/ is newer than the start of this work, and git status for tools/ is clean.

FINDINGS

1. MEDIUM. eval_v2.py:145-156: parallel bench44 runs can fail on the shared cache file on Windows.
- What happens: bench44.py:169 (a repo file, not patched) writes the decided-ground cache with a bare os.replace. eval_v2 starts bench44 3 at a time on an empty cache folder:
  - the baseline runs into BR, at the baseline step;
  - `bench44 --grids` into a new OUT/runs44, at every eval.
- Evidence (measured; race_test.json; inline test, system python): os.replace onto a PNG that another process was reading with cv2.imread failed 15 times out of 40 with "[WinError 5] Access is denied". This is the error the integrator fixed in bench_plate.py only.
- Effect: one failure ends eval_v2, and train_v2.py:94 then stops the driver. The remaining trainings, hours of them, never run.
- How often: not measured. The integrator's four parallel bench44 groups passed.
- Fix, in eval_v2 only, with bench44 untouched:
  - In the 44 block, run base() alone for the first grid that is not reused, then the rest in the pool.
  - Before the `bench44 --grids` call, seed the cache:
    `os.makedirs(OUT+'runs44/cache', exist_ok=True); [shutil.copyfile(f, OUT+'runs44/cache/'+os.path.basename(f)) for f in glob.glob(BR+'cache/decided_half_*.png') if not os.path.exists(OUT+'runs44/cache/'+os.path.basename(f))]`
  - The file name is keyed by the 44 street map's sha256 and WMAX, so the copy is the same file.

2. MEDIUM. train_v2.py:94: any failed step ends the whole run.
- An eval takes 2-4 minutes. Its failure, from finding 1 or a passing GPU fault, loses up to about 5 hours of trainings still to come.
- Fix: give run() a fatal flag.
  - For eval steps, log the failure and go on to the next training.
  - Name the failed steps at the end and exit 1.
  - A rerun redoes only those evals, because eval_done is false for them.

3. MEDIUM-LOW. train_v2.py:107 and :116: a half-written json crashes the resume.
- The trainers rewrite NAME.json at every check with a plain open and json.dump (unet.py:387, edgenet.py:253). eval_v2 does the same once (eval_v2.py:192).
- If the process is killed during a write, the rerun raises JSONDecodeError instead of training again.
- Measured: test_driver.json, cases "truncated_json" and "eval_truncated_json".
- Fix:
  - In model_done and eval_done, `try: d = json.load(...) except ValueError: return False`.
  - In both trainers' save_json and in eval_v2, write NAME.json.tmp and then os.replace it, retrying briefly on PermissionError.

4. LOW-MEDIUM. train_v2.py:104-110: model_done checks only the iterations and the manifest.
- It does not check the seed, the plates or the weights.
- Measured: a json with seed 9 and other argv counts as done (test_driver.json, "other_seed_or_plates_in_json": true).
- Effect: if PSEUDO, PSEUDO_W or LABELLED is changed after a run in the same OUT, the old models are reused without a word.
- Fix:
  - Compare d['seed'] with the step's seed.
  - Compare [p['spec'] for p in d['plates']] with the step's plate list.
  - Compare {p['plate']: p['weight']} with the step's weights.
  - On a mismatch, sys.exit with "move aside", as for the manifest.

5. LOW-MEDIUM. The 1A truth and region can drift from the training data (train_v2.py:201 and :219-220; eval_v2.py:171-175).
- Today the baseline step builds the truth from the live picks22_guided/22-1A/edges_ben.json, and the region is fixed to data/sanborn/train_v2/1A/valmask.png whatever --data says.
- Today the two agree: the made truth has the same sha256 as train_v2/1A/streetmap.json (6089ada1…, measured).
- They stop agreeing if:
  - Ben edits 1A before or during the run;
  - the baseline step is skipped (`--only`), so each eval makes its own truth.
- Fix: pass `--truth-1a <DATA>/1A/streetmap.json --region-1a <DATA>/1A/valmask.png` to every eval, the baseline's included. Both files are in the manifest.

6. LOW. unet.py:466 and edgenet.py:312: with --data and no --out, models go to unet_data/models with no overwrite guard.
- For example, `unet.py train area_ng1 --data ...` would overwrite the batch's model.
- The driver always passes --out, so the plan never does this.
- Fix: refuse when OUT/NAME.pt already exists, unless --force is given, or make data/sanborn/train_v2_runs/models the default.

7. LOW. unet.py:234-243 (manifest_sha): meta.json is never checked against the manifest.
- The manifest keeps meta.json's hash as entry['meta_sha256'], not under 'files'. So the trainers record "in_manifest": false for meta.json (integrate/driver_mini/models/lines_v2a_s1.json).
- make_labels_v2.py's docstring says content_sha256 is "the hash the trainers record". In fact they record the sha256 of the manifest file (unet.py:224).
- Fix:
  - In manifest_sha, `if fname == 'meta.json' and entry.get('meta_sha256'): return entry['meta_sha256']`;
  - and either correct the docstring or record both hashes.

8. LOW. train_v2.py:153-155: summary() raises a TypeError when an eval has no paired gain (or no 44 PQ).
- Measured: test_driver.json, "summary_without_paired".
- Fix: leave None values out of the means.

9. LOW (information). The trainers score validation on a crop of the validation area, not on the whole plate (unet.py:361-363, edgenet.py:229-232). eval_v2 and the batch predict the whole plate.
- Measured on 1A with area_ng1 and lines_ng1 on the CPU (test_valcontext.json, test_valcontext.py):

| | Crop of the validation area | Whole plate |
|---|---|---|
| Area net, IoU street | 0.8548 | 0.8465 |
| Line net, F1 | 0.7083 | 0.7070 |

- 2.2% of the area decisions differ between the two. They differ across the whole region, only 1.5% within its first 200 px, so the cause is where the tiles fall, not the missing context.
- So the validation numbers in the model json are not the region numbers eval_v2 reports. Checkpoints less than about 0.01 IoU street apart are within this tiling noise.
- Fix (optional): predict the whole plate and score only the validation pixels. That is about 3 times the check time (estimate). Or keep the crop and say so in the json.

10. LOW. On 1A, bench_plate drops one stage of the scores.
- bench44.py:419 looks for RUN/44_blockinst.png, but the outline step on 1A writes 1A_blockinst.png. So 1A's bench_plate.json has no '1_watershed_regions' stage.
- Measured: integrate/baseline_ng1/runs1A/v2_1A/bench_plate.json lists stages 0, 2, 3 and 4 only.
- The headline scores use stage 2 and are not affected.
- Fix, in bench_plate.setup: wrap B.run_outline_step so that after the step it copies {plate}_blockinst.png and {plate}_blockmask.png to the 44_ names in a.run. main() looks the function up by its global name, so the wrapper is used.

11. LOW. eval_v2.py:149: a baseline run is reused when its two map sha256s match, and nothing else is checked.
- The bench44 and outlines.py code and Ben's 44 street map are not checked. An old --baseline-runs folder could be paired with runs made by newer code.
- Fix: also require m['outlines_py_sha'] to equal the current outlines.py's sha. Also check that BR/cache has decided_half_<current streetmap sha>_260.png, or record bench44.py's own sha.

12. NITS.
- `--val-every 0` divides by zero at unet.py:408 and edgenet.py:275. Fix: refuse values under 1.
- unet.py:415 compares the new key, unrounded, with the stored best, which is rounded to 6 places. A tie within 5e-7 can replace the best. Fix: keep the unrounded key.
- eval_v2.py:72-73 uses torch.load without weights_only. That is fine on torch 2.4.1, but would break on torch 2.6 or later for area_ng1.pt, which was saved as DirectML tensors.

UNTESTED, NEEDS THE GPU
Same-seed repeatability on DirectML is still unchecked for both nets. On the CPU the same seed gives byte-identical weights. Before the full run, someone allowed on the GPU should train each net twice for 30 iterations with the same seed (about 2 minutes). That spread is the bar the V1 against V2 difference has to clear.

DESIGN NOTES, NOT CODE BUGS
- The line net is trained and its checkpoint chosen with area_ng1's map as its 7th input. eval_v2 feeds it the new area net's map. One extra eval row would separate the two nets' effects: area_ng1's 44 maps with the new line net.
- Picking V1 or V2 by their plate-44 PQ makes 44 decide that one choice. Report the 1A region next to it.

CHECKED AND FOUND RIGHT (measured unless marked)
- Command lines (test_cli.py, test_cli.json):
  - train_noguide.py's three commands, and predict with --no-guide and --area, parse into the same train/predict calls as before.
  - --data reaches train_data with the seed, the weights (upper-cased) and --out.
  - Unknown options, `--iters=20`, and --seed without --data are refused.
- Old training path (by reading the diff): without --no-guide, training is the same code and the same random draws as before. Only --no-guide changes: no guide moves and no 255 squares, so the random stream differs from area_ng1's run, as documented.
- CPU training, test_train.py on a small data folder cut from train_v2 (testdata/; T1 from 1A with its validation edge inside, T2 and T3 from 43; area net 30 iterations, line net 20, checks every 5):
  - the same seed twice gives identical NAME.pt and NAME_last.pt for both nets, and seed 2 gives different ones;
  - NAME.pt re-scored equals the best history entry, which is the first maximum, and NAME_last.pt equals the last entry;
  - the model json holds the seed, the manifest sha256, the git commit and branch, and the device.
- Validation pixels are never trained on:
  - in the training runs, no crop touched them: 154 area crops (nearest gap 1 px) and 54 line crops (nearest 22 px);
  - in the sampler test, none of 1,600 area crops or 800 line crops touched them;
  - area crops may end exactly at the region's first column, as the integrator found.
- Sampler (test_train.py, a 1-conv stand-in network, weights 1 : 0.5 : 0.5):
  - area net shares 0.504 / 0.263 / 0.234;
  - line net shares 0.512 / 0.230 / 0.258;
  - expected 0.5 / 0.25 / 0.25.
- Driver resume (test_driver.py, test_driver.json):
  - a finished model is skipped;
  - a cut-off one, or one without _last.pt, is trained again;
  - another manifest stops with the "move aside" message;
  - eval_done follows the model sha256s.
- Windows: 'python' started from the venv finds C:\Users\peckb\AppData\Local\Programs\Python\Python312\python.exe (the system python, which has scipy and shapely). That is also the venv's base, so it only works by luck on another machine. bench44 runs from eval_v2 work.
- Baseline faithfulness, rechecked from integrate/baseline_ng1/eval_v2.json: on all 6 grids the new run equals the baseline run (PQ 0.543, 0.5125, 0.5208, 0.5327, 0.4893, 0.4652), the paired gain is 0, and the 1A region PQ is 0.0928 for both.

FILES (all under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-23/train/review-code/)
- scripts/:
  - test_cli.py;
  - make_testdata.py;
  - test_train.py (area | lines | sampler);
  - test_driver.py;
  - test_valcontext.py.
- Second copy of the scripts: _second_copy/scripts/.
- Results:
  - test_cli.json;
  - test_train_area.json, test_train_lines.json, test_train_sampler.json;
  - test_driver.json;
  - test_valcontext.json;
  - race_test.json.
- testdata/ (2 MB): the small data folder in train_v2 format.
- driver_test/: the driver's output from the stubbed run.
- The test weights (356 MB) were deleted. Their hashes are in the test_train_*.json files.
