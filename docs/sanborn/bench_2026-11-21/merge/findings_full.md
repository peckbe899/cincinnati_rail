# The merged outline step and street binning: every report in full (21 November 2026)

Ben: "Yes, merge it", then "I've corrected 90's rail, but the streets are not being binned at all". One implementer wrote the change in data/sanborn/bench_2026-11-21/merge/staged/, four checks (plate 44, all 104 plates, by eye, code review) looked at it, the implementer fixed what they found, and a final check re-ran it. Applied as staged.diff. Paths below are in data/sanborn/bench_2026-11-21/merge/ (not in git); the scripts are copied beside this file.

## final check

### verdict

ready-with-caveats

### reason

I re-ran everything from fresh copies, using both the original harness and the staged one. Every number in the report came back the same. All 6 tile grids gave the same outlines as the implementer's, and so did all 8 batch plates. Plate 44 improves on all 6 grids: PQ +0.068 and recall +0.089. The bins on 44 put 93.9% of all ink in the same bin as Ben's map does.

On plate 90 the streets are now binned. Block line goes from 0 to 627,840 px, and 'not sorted' from 2.43M to 164k px. Until the new outline step has run, sorting 90 gives exactly today's bins, with 0 px different.

I re-checked each main finding from the earlier reviewers, and each is fixed. Nothing in the repo changed: the tool hashes are the same, no files under tools, unet_data, picks22_guided, streetmap, cufp or configs are newer, and 90 still has no edges_ben.json.

The caveats are about the order of steps and a few known gaps, not bugs. The main one: run_plates.py 90 must run before Ben saves any line edit on 90.

### numbers

All measured in this check unless marked as an estimate. Scripts and outputs are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-final/ (scripts/ and the JSON files beside them).

PLATE 44, batch grid (scripts/run_orig.py with the original harness copied to orig/; staged harness run into staged_runs/):
- Repo step: PQ 0.4309; 23 of 55 matched; 13 merges; recall 0.5316; precision 0.7475; green 0.7753; 0 closed; delete 32,545 px; draw 80,094 px. This equals the batch baseline exactly.
- Merged step: PQ 0.543 (fold A 0.5621, fold B 0.5231); 29 matched; 12 merges; 8 false blocks; recall 0.6214; precision 0.8226; green 0.8737; orange 0.4655; 5 of Ben's blocks closed; delete 21,632 px; draw 67,851 px.
- Both harnesses agree on every headline key except intact rings: 6 with the staged harness, 37 with the original one, whose old rule overcounts. My own recount (scripts/rail_rings44.py) gives 6, 2, 9, 7, 6 and 5 on the six grids, the same as the staged harness.

PLATE 44, 6 grids paired (scripts/paired.py into paired.json; base = my own runs of the repo step with the original harness):
- Mean PQ goes from 0.442 to 0.511 (sd 0.029).
- PQ +0.068 (sd 0.029), higher on 6 of 6 grids, t95 +0.038 to +0.099.
  - Fold A +0.029, higher on 5 of 6, t95 -0.010 to +0.068: not clear of the grid noise.
  - Fold B +0.111, higher on 6 of 6.
- Recall +0.089 (6 of 6); precision +0.066; green +0.092.
- Matched +4.3; false blocks -1.5 (lower on 5 grids, higher on 1).
- Closed blocks: 0 to 4.8.
- Delete -8.6k px and draw -11.5k px, both lower on 6 of 6.
- The original and staged harnesses give the same paired gains. Outlines, N_edges and shown lines are byte-identical between the two harnesses and to the implementer's final__gridK runs.
- Rail-yard sides (scripts/rail_rings44.py): the shown lines lying mostly on the railroad bin go from 32 (9.9k px) with the repo step to 0.

BINS ON 44 (scripts/run_ink.py, then scripts/bins44_cmp.py into bins44_cmp.json):
- The applied ink_bins with Ben's map equals the repo's 44_bins.png (0 px differ).
- Sorted from the merged step, batch grid. The first share is how much of Ben's-map bin lands in the same bin; the second is how much of the new bin Ben's map agrees with.
  - all ink 93.92% (95.89% on decided ground);
  - block line 74.83%, then 85.04%;
  - lot line 94.64%, then 85.98%;
  - building outline 99.25%, then 94.55%;
  - water pipe 92.74%, then 92.42%;
  - sewer 94.28%, then 87.01%;
  - 'not sorted' 0 px.
- Over the 6 grids: all ink 93.86% (sd 0.10, 93.74-94.01); block line 74.70%; lot line 94.61%; pipe 92.53%; sewer 93.01%; building outline 99.37%.
- No lines and no ground, as the batch sorted: 62.35% of all ink.
- Caution: the reference is itself rule-based.
- Rail, rules alone, scored against the 28-track page file (scripts/rail44.py; my own scorer with score_rail.py's tolerances, so not the rail agent's exact numbers):
  - railroad found 98.85% at 98.6% precision with the merged ground, the same as with Ben's map;
  - with no ground: 96.9% precision.
- Placed plates 43, 45 and 80, sorted by the applied rules: 0 px differ from the repo bins.

8 BATCH PLATES (scripts/run_plates8.py: the applied blocks_noguide N --outlines-only --out, venv, CPU; then scripts/measure8.py into measure8.json):
- All 8 exited 0.
- outlines.json, N_edges.json, mapground and blockmask are byte-identical to the implementer's plates_final, and every count equals batch104_final.json.
- Per plate: blocks / holes / N_edges lines / editor lines / green / on-rail dropped. In brackets: the batch's N_edges lines and the suspect flags.

| Plate | Kind | Blocks | Holes | N_edges lines | Editor lines | Green | On rail | Notes |
|---|---|---|---|---|---|---|---|---|
| 90 | PDF 200 ft | 55 | 1 | 430 (156.6k px) | 413 | 349 | 19 | batch 3; 72 sides on the map edge left out |
| 30 | PDF 200 ft | 33 | 0 | 402 | 385 | 337 | 8 | batch 9 |
| 47 | PDF 400 ft | 14 | 0 | 160 | 153 | 116 | 0 | batch 11; suspect: Q1 47%, Q2, Q3 |
| 1B | cut 100 ft, rail yard | 41 | 0 | 353 | 328 | 239 | 128 | batch 598 |
| 60B | cut 200 ft | 40 | 0 | 217 | 214 | 211 | 0 | batch 267 |
| 5 | cut 100 ft | 64 | 10 | 537 | 511 | 430 | 1 | batch 683 |
| 26A | cut 200 ft, river | 48 | 1 | 357 | 347 | 313 | 74 | batch 514 |
| 2 | cut 100 ft | 45 | 0 | 365 | 350 | 273 | 90 | batch 529; suspect: Q2 |

- Lines whose middle lies within 40 px inside the map-ground edge (scripts/edge3.py): 90 has 3 (324 px), 30 has 3, 47 has 5. Round 1 had 29, 20 and 28.
- Time for the outline step: 9.5-46.7 s per plate. This was measured with other runs going at the same time, so it is inflated.

BINS ON 90 (scripts/run_ink.py into bins90/):
- From the merged step (ground 'nets', version ce51ccd485b6): block line 627,840; lot line 1,086,885; building 232,200; railroad 202,954; streetcar 214,026; water pipe 473,113; sewer 84,794; text 1,982,457; not sorted 163,541 px.
- As the repo is now, before the outline step: 0 px differ from today's 90_bins.png, and it prints 'Run blocks_noguide.py 90 --outlines-only first'.

DRY RUN of a plain run_plates.py on the real state (scripts/dryrun.py, read only):
- 104 plates get outline + bins, 90 included. 43, 44, 45, 80 and 82A get nothing.
- Rules hash 79b850d72a95; outline version ce51ccd485b6.

ESTIMATE, not measured: a full run_plates.py over the 104 plates runs one plate after another, about 1.5-2.5 h.

### diff_applies

Yes.
- I applied staged.diff to fresh copies of the repo's 5 changed files. It gives 23 files, all byte-identical to merge/staged/: the 6 changed text files, map_area.py, bench44.py, scale_table.json, the 6 info.json files and the 9 templates.
- I applied it with core.autocrlf=false. The repo marks tools/sanborn as -text (git ls-files --eol shows attr/-text), so git converts no line endings there.
- A first try in a bare git init, which uses the global autocrlf=true, gave CRLF files that differ. That cannot happen in the real repo.
- `git apply --check` passes on the real repo.
- The 12 tile-grid PNGs are not in the diff. The staged copies are byte-identical to inference/maps/{batch,off1..off5_tta1}, so they must be copied by hand for `bench44.py --grids`.
- The diff's outline version, ce51ccd485b6, matches the version recorded on every run.

### remaining

Nothing blocks the merge. These are caveats.

1. Order on plate 90 (operational, the most important). Right after applying the diff, run `python tools\sanborn\unet\run_plates.py 90` (or the full run), before Ben saves any line edit on 90.
   - Once picks22_guided/22-90/edges_ben.json exists, blocks_noguide.py (staged, line 121) writes the new step into unet_data/90_new/.
   - ink_bins.py (staged, line 424) then finds no version in 90's own N_outlines.json and sorts with ground 'none' again: the streets would stay unbinned.

2. The editor's sheet outline on uncut sheets is the paper's edge, not a street. This comes from edit_server.sheet() and was there before the diff.
   - On 90 it is 20 lines (35.3k px), all off the map ground.
   - The far side of the outermost streets is also left out as paper_edge, by the map-edge rule chosen from v-eye (staged outlines.py:309-317).
   - On 90, Ben will delete the first and draw the second.

3. The original bench44 harness counts intact rings with its old rule (bench_2026-11-21/bench44/bench44.py:443-451): 37-41 against the true 2-9. Use the staged tools/sanborn/unet/bench44.py for that key.

4. Plate 44 caveats:
   - The fold A PQ gain (+0.029, t95 -0.010 to +0.068) is within the grid noise.
   - The merged step's PQ varies about twice as much between tile grids as the repo step's (sd 0.029 against 0.015).
   - False blocks rose on 1 of the 6 grids.

5. Minor nits:
   - Staged ink_bins.py:402 does not upper-case N, unlike outlines.py:127 and blocks_noguide.py:147. It works on Windows, but a lower-case id keeps its case in N_bins.json.
   - Staged map_area.py is the only staged text file with CRLF line endings. This is harmless.

6. Not re-measured by me:
   - the PLAIN_KEEP comparison (the implementer's measurement, reason for not adopting);
   - the 104-plate totals;
   - plate 82A's bins.
   I checked 8 plates, and 43, 45 and 80 plus 44's reference sorting.

The earlier reviewers' findings, re-checked (each one now fixed):
- v-code HIGH, plate 90 sorted before the rerun: the bins equal today's, 0 px differ.
- Missing template: the step stops with exit 1, a FileNotFoundError naming key.png, and an empty output folder.
- Option slips in blocks_noguide, outlines, ink_bins and run_plates: exit 2 or 1, and nothing changed (guard_tests.json, on a fake data tree).
- Placed plates: the dry run plans nothing for them, the bins are unchanged, and outlines.py refuses without --force.
- Edited plates: the new step goes to N_new/ and the plate's own files are unchanged. With edges_ben.json but no N_edges.json, the plate's files are written normally.
- v-eye map edge: 3-5 lines per sheet against round 1's 20-29.
- Q1 under the system python: the same outlines and the same Q1 (0.983 on 60B, 0.474 on 47).
- Lower-case ids in the block step: the same outputs.
- bench44: the cache is keyed by sha and WMAX; the default run folder is in the temp folder; split_args keeps backslashes.
- Rail-yard sides on 44: 0 shown.


## implementer, final report

### summary

I fixed the bugs the four checks found, in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged/, and regenerated C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged.diff.

The diff now carries every staged file except the 12 tile-grid map PNGs, including the 9 map_area templates as binary patches. Applied to fresh copies, it gives all 23 files byte for byte, and `git apply --check` passes on the real repo. Nothing in the repo changed: the seven tool hashes are as given, no file under tools/sanborn, unet_data, picks22_guided, streetmap, cufp or configs is newer than my start, and 90 still has no edges_ben.json.

What changed, all measured:
- **Plate 90 between applying the diff and the rerun (v-code's HIGH finding).** Ink sorting now takes block lines and ground only from an outline step whose N_outlines.json has a version. None of the batch's 109 outline files has one. On 90 as the repo is now, the sorting gives exactly today's 90_bins.png (0 px differ) and tells you to run the outline step first. Before this fix it turned 2.43M px into lot line.
- **Map edge on uncut sheets (v-eye).** I went back to outline-nesting's rule: every side along the map-ground edge is left out. On the 32 PDF sheets, lines lying within 40 px inside that edge fell from 1,014 (262k px) to 137 (25.8k px); outline-nesting had 105.
- **Placed plates (v-batch).** A plain run_plates.py now does nothing on 43, 44, 45, 80 and 82A. The new rules sort all five exactly as the repo's bins (0 px differ).
- **Plates Ben has edited.** The outline step goes to unet_data/N_new/, so his lines and the outlines that made them stay together.
- **Smaller fixes:**
  - missing templates now stop the step;
  - templates and ink_bins.py now count in the outline version, and edit_server's clean() and sheet() in the rules hash;
  - typos in options stop the scripts;
  - Q1 now gives the same result under the system python;
  - in bench44: the intact-ring count, the cache and the default run folder;
  - Windows paths in --outline-args;
  - lower-case plate ids.
- **Not adopted.** v-batch suggested keeping blocks whose outline cannot be closed into a ring. Measured, that is worse on 44 (PQ -0.007, 3 more false blocks), and by eye only 5 of 30 sampled lines it adds are street sides.

**Plate 44.** The outlines are byte-identical to round 1 on all 6 tile grids and on the guided maps:
- batch grid: PQ 0.543 (batch 0.431); recall 0.621; precision 0.823;
- 6 grids against the repo step: PQ +0.068 (6 of 6 grids), recall +0.089;
- bins: 93.9% of all ink lands in the same bin as with Ben's map.

**Plate 90.** The new step gives 55 blocks, 1 hole, 430 lines (413 shown in the editor) and 349 green. Block line goes from 0 to 627,840 px, and 'not sorted' from 2.43M to 164k px.

90's N_edges.json is not rewritten. That happens only when Ben runs run_plates.py, and it should happen before he opens 90 in the line editor.

### staged_files

All files are under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged/ and mirror the repo. "Staged" gives the start of each file's sha256. Round 1's text is kept in merge/impl/r2/staged_round1/.

1. tools/sanborn/unet/outlines.py. It replaces the repo file (sha bccc2b34); staged 5bb16cb3376c039c.
   - Kept from round 1:
     - one watershed marker per block (MK_CUT 3, MK_SEED_MIN 2000), each block traced on its own;
     - closed rings (RING_CORNER 400, COLIN_ANG 4, COLIN_OFF 12, COLIN_GAP 250, SNAP_JOIN 12);
     - the green gate;
     - street holes (RETR_CCOMP, hole=True, holes first, HOLE_PARENT 3);
     - the 'on rail' pass;
     - the QA flags Q1, Q2, Q3, Q5;
     - 'version';
     - the placed-plate guard;
     - --area-png, --lines-png, --out, --bins-png and --hole-parent.
   - New in round 2:
     - **Map edge.** On an uncut sheet, every side along the edge of the map ground is paper_edge, which is outline-nesting's rule. The 'fixed' mask is gone.
     - **map_area failures.** An import error, a missing template or a failure in map_area now stops the step (exit 1) before anything is written.
     - **Q5.** It is raised only when map ground is found on less than 5% of the paper (the paper is then used), or on less than 30% or more than 97%. The 32 PDF sheets measure 42-84%, so no sheet is newly flagged.
     - **Write order.** N_mapground.png is written first (a stale one is deleted when no map ground is found). N_outlines.json is written last, through tmp + replace.
     - **Rail source.** The rail test uses N_bins.png's railroad only if ground_from is 'map' or 'label', or 'nets' with an outline_version equal to this step's version. Otherwise it runs the rule.
     - **Q1 thinning.** thin() is a numpy Zhang-Suen thinning, used when cv2.ximgproc is missing; it gives the same pixels.
     - **Plate ids.** N is upper-cased, so a scale lookup with '1a' works.
     - **Guard for edited plates.** It refuses to write picks22_guided/22-N/outlines.json on a plate that has edges_ben.json and N_edges.json, unless --force.
     - **Unclosed rings.** PLAIN_KEEP = False, with an option --plain keep|drop for the bench and an 'open_outlines' count.
     - **Docstring.** The usage line names the venv, and there are dated notes with the measurements.

2. tools/sanborn/unet/blocks_noguide.py. It replaces sha 3700ff13; staged 9ea3efc55c008bb3.
   - Kept from round 1: step4() can be imported without torch; it drops short, paper_edge, 'not on a line' and 'on rail'. outline_version(), --outlines-only and --out are kept.
   - New in round 2:
     - argparse: an unknown option exits 2 before anything runs, and --out=DIR works;
     - VERSION_FILES also covers ink_bins.py and the 9 templates;
     - protected(N): on a plate with edges_ben.json AND N_edges.json, steps 3 and 4 write into unet_data/N_new/ and the plate's own files stay. This replaces N_edges.new.json. A plate with edges_ben.json but no N_edges.json is written normally;
     - plate ids are upper-cased;
     - N_blocks_ng.json 'edges_file' is a path under data/sanborn.

3. tools/sanborn/unet/map_area.py. New; staged 2205f7997899a070. It is the bench's file. _tpl() now raises FileNotFoundError naming every missing or unreadable template, and the docstring is updated.

4. tools/sanborn/unet/templates/*.png. New: 9 files (key, title, bar200, bar400, bar400b, note200a, note200b, note400a, rose). They are byte-identical to visual-pdf/templates and are now in the diff as git binary patches.

5. tools/sanborn/unet/ink_bins.py. It replaces sha de9b7914; staged 3b461d0676888bb1.
   - Kept from round 1: the fallback (lines from street_map.editor_lines with Ben's edits; ground from block_ground of outlines.json; N_mapground.png), ben_masks() and ben_railroad(), and made_from.
   - New in round 2:
     - 'nets' is used only when the outline step's N_outlines.json has a 'version'. Otherwise it prints "Run blocks_noguide.py N --outlines-only first" and sorts as before (ground_from 'none');
     - a note is printed when the version is older than today's;
     - N_bins.json gains 'outline_version', and made_from gains 'outline step';
     - check_args(): an unknown option or a stray argument stops it. The test options (--no-map, --edges, --outlines, --unsure, --no-ben, --rail, --car) need --save, and --json needs --save.

6. tools/sanborn/unet/street_map.py. It replaces sha 41d33506; staged 7bb57f09ad7e6ba8. Unchanged from round 1: editor_lines() is shared with ink_bins.

7. tools/sanborn/unet/run_plates.py. It replaces sha 2c6ee4a9; staged c64eea6514c31d14.
   - Kept from round 1: the order (prepare, block step, ink sorting, tracks), plan(), bins_from() and --list.
   - New in round 2:
     - rules_hash() covers ink_bins.py, street_map.py, rail_tracks.py, and the source of edit_server.py's sheet() and clean(), read with ast (the editor is not imported);
     - bins_from adds N_outlines.json;
     - LEGACY_RULES {'de9b79144123'} with legacy_ok(): a placed plate sorted by the old rules is up to date unless its street map, label, rail_ben.json or edges_ben.json is newer than its N_bins.png;
     - an unknown option stops it, and nothing runs.

8. tools/sanborn/unet/bench44.py. New; staged 6c9a5a123c411269. Kept from round 1: the port of bench44 that runs the real outlines.py and step 4, plus --grids, --paired, --keep-unlined and --rail-show. New in round 2:
   - intact rings now use the step 4 in use (its rule, or the --step4 hook's) and count block outlines only, not holes;
   - the decided-ground cache is keyed by the street map's sha and WMAX, and written through tmp + os.replace;
   - the default --runs is <temp>/sanborn_bench44_runs/, outside the repo;
   - --outline-args is split Windows-style (split_args keeps backslashes).

9. data/sanborn/scale_table.json. New, unchanged from round 1 (identical to census/scale/scale_table.json).

10. data/sanborn/bench44_maps/grid0..grid5/. The six info.json files are in the diff. The 12 PNGs (44_area.png, 44_lines.png; 47 MB together) are not; they are byte-identical to inference/maps/{batch,off1..5}_tta1 and need the copy step under how_to_run.

### diff_path

C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged.diff

### numbers_44

Everything here is measured. Scripts are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/impl/r2/scripts/ and outputs in merge/impl/r2/. Bench runs use the staged bench44.py through run_bench.sh; the runs are in r2/bench44_runs/. The outline version is ce51ccd485b6.

**Same as round 1.** The final outlines.json and 44_edges.json are byte-identical to round 1's on the batch grid, on all 6 tile grids and on the guided maps (cmp). Plate 44 is a cut plate, so neither the map-edge rule nor the dropped unclosed rings touch it.

**Batch grid** (bench_final_batch.json):
- Blocks: PQ 0.543 (fold A 0.5621, fold B 0.5231); 29 matched, 12 merges, 8 false blocks.
- Ben's interior lines found: 0.6214 (A 0.6304, B 0.6107).
- Shown lines that are right: 0.8226 (A 0.8108, B 0.8373); green 0.8737; orange 0.4655.
- 5 of Ben's 55 blocks close (A 3, B 2). Intact rings: 6. The old rule in bench44 reported 37; my recount with step 4 also gives 6.
- Ben's delete length 21,632 px; draw length 67,851 px.
- The outline step took 20.4 s, run while other jobs were running.
- For comparison, the batch had 0.4309 / 0.5316 / 0.7475 / 0 closed / 32,545 / 80,094, and outline-quality (A) alone had 0.543 / 0.6097 / 0.7596 / 6 closed / 33,107 / 70,178.

**Six grids, paired** (paired44.py final; base = inference/bench/runs per grid; A = critic/harness/runs/oq__grid). The t95 ranges are computed intervals over the 6 grids, not measurements.
- Against the repo step:
  - PQ +0.068 (sd 0.029, higher on 6 of 6, t95 +0.038 to +0.099); fold A +0.029 (5 of 6, t95 -0.010 to +0.068, so not clear of the grid noise); fold B +0.111 (6 of 6).
  - Recall +0.089 (sd 0.009, 6 of 6); fold A +0.083, fold B +0.096.
  - Precision +0.066 (6 of 6); green +0.092.
  - Matched blocks +4.3; false blocks -1.5.
  - Closed blocks 0 to 4.8 (range 2-8).
  - Delete -8.6k px and draw -11.5k px, both lower on 6 of 6.
  - Mean PQ 0.442 to 0.511 (sd over the grids 0.029).
- Against A alone:
  - PQ, matched and false blocks: +0.000 on every grid.
  - Recall +0.010 (6 of 6); precision +0.058 (6 of 6); green +0.032.
  - Closed -0.17 (one grid lost 1).
  - Delete -10.3k px and draw -1.8k px (6 of 6).
- Against round 1: +0.000 on every key, on every grid.
- Intact rings, corrected rule: 5.8 (sd 2.3, range 2-9). v-44 reported 39.2 with the old rule.

**Guided maps** (edge_v1 + lines_v2): PQ 0.6885 (A 0.609, B 0.7621); recall 0.5357; precision 0.8508; green 0.9066; 5 closed; intact 4; delete 15,875 px; draw 83,226 px.

**Unclosed rings kept (PLAIN_KEEP), not adopted** (paired44.py keep against final, 6 grids):
- PQ -0.0072 (lower on 4 grids, same on 2); false blocks +1.3; precision -0.0014 (lower on 6); recall +0.0004; delete +262 px.
- On the batch grid: PQ 0.5259, 11 false blocks, delete 22,172 px.
- On 44 such outlines add 5 lines, of which 1 lies on Ben's map.

**Ink bins on 44** (bins44.py final_batch final into bins44_final_batch.json; the reference is the staged ink_bins with Ben's map):
- The reference equals the repo's unet_data/44_bins.png pixel for pixel.
- Fallback from the merged step (batch grid). The first share is how much of the reference bin lands in the same bin; the second is how much of the fallback's bin the reference agrees with.
  - all ink: 93.92% (95.89% on Ben's decided ground);
  - block line: 74.83%, then 85.04%;
  - lot line: 94.64%, then 85.98%;
  - building outline: 99.25%, then 94.55%;
  - water pipe: 92.74%, then 92.42%;
  - sewer: 94.28%, then 87.01%;
  - 'not sorted' 85k px goes to 0.
  - On decided ground: block line 79.95%, lot line 97.37%, pipe 96.51%, sewer 96.49%.
  - These bins are pixel-identical to round 1's. So the rail check is unchanged and was not rerun: railroad 98.43% found at 99.45% within 10 px, no false track; streetcar 80.5%; scored against rail_ben.page_2026-11-21.json (28 tracks).
- Over the 6 grids: all ink 93.86% (sd 0.10, 93.74-94.01); block line 74.70% (74.15-75.18); lot line 94.61%; pipe 92.53%; sewer 93.01% (91.26-94.28); building outline 99.37%.
- No lines and no ground (what the batch did): 62.35% of all ink.
- The batch's own 44 outlines (no version) are now refused (ground 'none'), with the same 62.35%. The rule works as intended.
- Caution: the reference is itself rule-based. Only its block-line bin comes from Ben's lines.

**Placed plates** (placed5.py into placed5.json): the staged ink_bins with the map or label, on 43, 44, 45, 80 and 82A, equals the repo's N_bins.png on all five (0 px differ).

### numbers_batch

These are the 104 unplaced plates, through the real path: the staged blocks_noguide.py N --outlines-only --out r2/plates_final/N/ (venv, CPU, 6 at a time) on the batch's saved maps and bins.
- Script: batch104.py run final, then measure final; outputs batch104_final.json and batch104_final_summary.json.
- 104 of 104 exited 0, and every plate has version ce51ccd485b6.
- Each N_edges.json equals step 4 of its outlines.json (asserted).

**Totals for all 104.** Each line reads batch / outline-nesting (B) / round 1 / round 2. Everything is measured.
- Blocks: 2,698 / 3,143 / 3,465 / 3,465. Holes: - / 415 / 267 / 267.
- Step-4 lines (= N_edges.json): 38,539 (10.94M px) / 43,964 (12.19M) / 34,946 (13.45M) / 34,052 (13.21M).
- Editor lines (edit_server.clean): 34,859 / 39,863 / 33,296 (13.41M px) / 32,432 (13.17M px).
- Median green share by count: 0.957 / 0.965 / 0.813 / 0.831. Green now also needs the line network, so this is not like for like.
- Lines within 150 px of the paper edge: 3,770 / 3,426 / 2,638 / 2,565.
- Round 2 only:
  - 'on rail' sides dropped: 1,663 (356k px);
  - 'not on a line' sides dropped: 10,693;
  - bridging sides: 12,487, counting every bridge, including those step 4 leaves out;
  - paper_edge sides: 3,543.
- Suspect flags:
  - round 2: 14 plates: 2 (Q2), 3 (Q1 59%), 15B (Q1), 41 (Q2), and the ten 400-ft plates 46, 47, 48, 49, 50, 92, 93A, 93B, 94, 95 (Q3; 47 also Q1 47% and Q2). This is the same list as round 1.
  - The batch census flagged 25 plates and B flagged 14.

**By group** (round 2 against round 1):
- Cut 100 ft (34 plates) and cut 200 ft (36 plates): identical to round 1.
  - 100 ft: 1,108 blocks, 11,017 lines (4.60M px), 10,394 editor lines.
  - 200 ft: 1,335 blocks, 12,925 lines (5.02M px), 12,397 editor lines.
- PDF 200 ft (24 plates): 924 blocks, 8 holes.
  - Lines 8,755 (3.21M px), against round 1's 9,394 (3.38M), B's 10,421 (2.91M) and the batch's 6,841 (1.99M).
  - Editor lines 8,350; green median 0.830 (round 1 0.773).
- 400 ft (10 plates): 98 blocks; lines 1,355 (381k px) against round 1's 1,610 (446k).

**Lines along the map edge, PDF sheets** (edge_pdf.py final into edge_pdf_final.json): lines whose middle lies within 40 px inside the map-ground edge.
- All 32 PDF sheets: round 2 137 (25.8k px, 86 orange); round 1 1,014 (262k px); B 105 (15.6k px).
- The five sheets v-eye checked by eye (90, 30, 23, 21, 47): round 2 20 (3.9k px); round 1 190 (43.7k); B 8 (2.3k).

**Fewer blocks than the batch** (by design, as in round 1): 10, 15B, 18B, 26A, 54A, 60A, 85A. No plate has fewer blocks than round 1.

**Unclosed rings** (the measurement for the not-adopted change):
- Kept with PLAIN_KEEP (open_sample.py keep): 280 outlines (195 blocks, 85 holes) on 83 plates; step 4 would show 226 more lines (26.4k px, 153 green).
- My eye estimate on 30 sampled lines (open_verdicts.json; seed 0, weighted by length):
  - all 30: 5 street sides, 5 unsure, 20 wrong (lot lines, pipes, tracks);
  - hole lines: 0 right, 2 unsure, 12 wrong;
  - block lines: 5 right, 3 unsure, 8 wrong.

**Plate 90** (plates_final/90): 55 blocks and 1 hole.
- 430 step-4 lines (156.6k px), 413 editor lines, 349 green.
- 19 rail sides dropped, using Ben's 37 tracks.
- Not suspect.
- 72 sides along the map edge are left out. Round 1 had 456 lines (161.3k px) and 438 editor lines.
- Picture: r2/pics/90_final_vs_round1.jpg. Round 1's lines are light blue underneath.

**Time:** the outline step's own median is 38.8 s per plate, max 77.9 s (90: 50 s); 706 s wall for all 104 at 6 at a time. These were taken with the 6-grid bench running beside, so they are inflated; v-batch measured round 1 alone at a median of 22.7 s. Under the system python, plates 3, 5 and 60B took 28.9, 28.1 and 7.5 s, against 41.2, 41.6 and 12.1 s under the venv at the same time.

**Ink bins, before and after** (bins12.py into bins12.json). Before = the repo's N_bins.json; after = the staged ink_bins fed the round-2 block step's files. Values in px.

Plate 90:
| bin | before | after | round 1 |
|---|---|---|---|
| block line | 0 | 627,840 | 650,637 |
| lot line | 0 | 1,086,885 | 1,081,385 |
| water pipe | 0 | 473,113 | 460,706 |
| sewer | 0 | 84,794 | 84,823 |
| not sorted | 2,428,935 | 163,541 | 163,297 |
| building outline | 259,304 | 232,200 | |
| railroad | 209,112 | 202,954 | 202,954 |
| streetcar | 214,310 | 214,026 | |
| text and numbers | 1,956,592 | 1,982,457 | |

- The remaining 'not sorted' is the margin and KEY, off the map ground.
- The block-line drop against round 1 is the map-edge lines no longer exported. By v-eye's sample those were mostly banks and city limits; some of that ink now sorts as water pipe.

Other plates:
- 30: block line 0 to 654,791; not sorted 2,652,299 to 177,675.
- 79: block line 0 to 1,132,677; not sorted 3,684,740 to 223,218.
- 47 (400 ft): block line 0 to 149,288 (round 1 177,822); railroad 26,540 to 0.
- Identical to round 1 (cut plates): 60B, 64A, 26A, 5, 1B, 1A, 3, 93A. For example, on 5: block line 0 to 1,151,581, not sorted 2,189,500 to 0, railroad 81,635 to 29,381.

**Plate 90 as the repo is now** (bins90/90_asis.*): staged ink_bins 90 refuses the batch's outlines, prints the command to run, and gives ground 'none'. The result equals today's unet_data/90_bins.png (0 px differ), where v-code had measured 2.43M px of lot line before the fix.

**run_plates dry run** (dryrun2.py into dryrun2.json): the staged run_plates over the repo's scripts, against the real run_plates.json.
- 104 plates: outline + bins (outline step 'not recorded -> ce51ccd485b6'; rules de9b79144123 -> 79b850d72a95).
- The 5 placed plates: nothing.
- The networks are never planned.
- A second pass, after the recorded run, plans nothing.

### choices

Each choice below was decided by a measurement.

1. **Map edge on uncut sheets: outline-nesting's rule.** Every side along the map-ground edge is paper_edge.
   - By eye (v-eye), 4 of 36 sampled lines in that band were streets, 29 wrong. Of the 5 green ones, 1 was a street, so keeping only green ones would not help (verdicts.json crossed with samples/edge.json).
   - The round-1 rule never brought back the far side of the outermost street (20 of 250).
   - Measured result: lines within 40 px inside the edge on the 32 sheets, 1,014 (262k px) to 137 (25.8k px).

2. **Unclosed rings: blocks whose ring cannot be closed are left out (PLAIN_KEEP False).** This is the check's suggested fix, measured and not adopted.
   - Keeping them as plain outlines on 44: PQ -0.0072 over 6 grids (lower on 4, never higher), false blocks +1.3, precision -0.0014 (6 of 6), recall +0.0004.
   - On 44, 1 of their 5 lines lies on Ben's map.
   - On the 104 plates, by eye 5 of 30 sampled lines are street sides, and 0 of 14 hole lines.
   - The option stays for the bench (--plain keep).

3. **When the ink sorting trusts the outline step's outlines: when they have a version, not only when the version is today's.**
   - The batch's 109 N_outlines.json files have no version (counted), so the broken outlines are refused (on 90: 0 px differ from today's bins).
   - Requiring today's version would empty the bins of every plate after any edit to the code, until the outline step is rerun. That is Ben's "streets are not being binned" complaint again.
   - It would also break plates Ben has edited, which deliberately keep an older outline step.
   - An older version prints a note.

4. **Which bins the outline step's rail test reads.** Only bins sorted from Ben's map or the old label, or from the same outline version. Otherwise it runs the rule itself. Tested in the fake data tree on a copy of 64A (52 rail sides): the rule run in the step, and the bins' railroad of the same version, give byte-identical outlines.json (guard2.py T10).

5. **Placed plates under the new rules (LEGACY_RULES).** They are skipped, not re-sorted. The new rules give 0 px difference on all five (placed5.py), so a re-sort would only cost 40-58 s per plate and rewrite N_bins.json. They are still re-sorted when one of their inputs is newer than their bins.

6. **Plates Ben has edited.** The whole outline step goes to unet_data/N_new/, rather than only N_edges.new.json. Otherwise the ink sorting would mix the old lines with new ground, as v-batch measured on 5: block line 1,031,105 against 1,151,581 px.
   - This applies only when N_edges.json exists. Without it, his edits can only be lines he drew or sheet-edge lines, keyed to nothing of the step.
   - Tested in guard2.py: T1 (files unchanged, N_new written), T2, and T4 (outlines.py run by hand is refused).

7. **Missing templates: a hard error, not Q5.** A sheet traced without its map ground puts the margin and KEY into blocks. Without templates, 90 gave 41 blocks instead of 55 and exit 0 (v-code).
   - Now the step exits 1 and writes nothing (guard2.py T8). With the templates it runs normally (T9).
   - Q5 is kept for map ground found but outside 30-97% of the paper; none of the 32 sheets is (map_area_check: 42-84%).

8. **Q1 thinning: a numpy Zhang-Suen when ximgproc is missing.**
   - Identical pixels to cv2.ximgproc.thinning on 9 plates (thin_check.py).
   - Identical outlines.json and Q1 under the system python on 3, 5 and 60B; plate 3 keeps its Q1 flag (q1sys.py).

9. **What triggers reruns.**
   - Outline version: also covers ink_bins.py (railroad() and block_ground() run inside the step) and the templates.
   - Rules hash: covers only the source of edit_server's sheet() and clean(), not the whole file, so editor UI changes do not re-sort 109 plates.

10. **Options checking.** blocks_noguide uses argparse, so a typo exits 2 (guard2 T5) and --out=DIR works (T6). ink_bins and run_plates check their options too (T7).

11. **bench44.**
   - Intact rings follow the step 4 in use and count block outlines only. On 44 that gives 6, the same as v-code's recount (the old rule gave 37).
   - The cache key is sha16(streetmap)+WMAX, and the new cache equals the old one (0 px).
   - The default runs folder is the system temp folder.
   - --outline-args keeps Windows backslashes (tested on C:\Users\... paths).

12. **Kept from round 1, on the measurements already in the task:** HOLE_PARENT 3, RAIL_DROP True, KEEP_UNLINED False, and the ring and marker settings.

### how_to_run

These commands are run from the repo root, C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D. In PowerShell use backslashes for the tools path.

1. **Apply the diff.**
   - `git apply data/sanborn/bench_2026-11-21/merge/staged.diff`
   - Applied to the real repo with `git apply --check`, it passes for all 23 files. tools/sanborn and data/sanborn are -text, so autocrlf does not matter.

2. **Copy the 12 tile-grid maps.** They are not in the diff. In PowerShell:
   - `foreach ($k in 0..5) { Copy-Item data\sanborn\bench_2026-11-21\merge\staged\data\sanborn\bench44_maps\grid$k\44_*.png data\sanborn\bench44_maps\grid$k\ }`
   - git apply has already made the folders with their info.json.

3. **Check what would run.** `python tools\sanborn\unet\run_plates.py --list`
   - It should list 104 plates with "outline (outline step not recorded -> ce51ccd485b6); bins (rules de9b79144123 -> 79b850d72a95)", and the five placed plates as up to date.
   - If any of outlines.py, blocks_noguide.py, map_area.py, ink_bins.py or the templates is edited after applying, the outline version changes. If ink_bins.py, street_map.py, rail_tracks.py, or edit_server.py's sheet() or clean() is edited, the rules hash changes.

4. **Plate 90 first.** Do this before Ben opens 90 in the line editor; if it is open, reload the page afterwards. `python tools\sanborn\unet\run_plates.py 90`. That runs three steps:
   - blocks_noguide.py 90 --outlines-only under the venv. It writes unet_data/90_edges.json, 90_outlines.json, 90_outlines.jpg, 90_blockmask.png, 90_blocks_ng.json, 90_mapground.png and picks22_guided/22-90/outlines.json. Measured here: 50 s under load.
   - ink_bins.py 90, writing 90_bins.png and 90_bins.json (about 40 s).
   - rail_tracks.py 90, writing 90_rail_rule.json.

5. **Then the rest.** `python tools\sanborn\unet\run_plates.py`
   - It runs the same three steps on the other 103 unplaced plates.
   - It never runs the networks (their maps exist and netid matches).
   - It does nothing on 43, 44, 45, 80 and 82A.
   - Estimate, not measured end to end: about 1-1.5 min per plate, so roughly 2 h.

6. **Outline step alone, by hand:**
   - `cd data\sanborn`
   - `..\..\tools\sanborn\unet\.venv\Scripts\python.exe ..\..\tools\sanborn\unet\blocks_noguide.py N --outlines-only [--out DIR]`
   - On a plate with edges_ben.json and N_edges.json, the output goes to unet_data\N_new\.

7. **The bench:**
   - `cd data\sanborn`
   - `python ..\..\tools\sanborn\unet\bench44.py --tag merged [--runs DIR]`
   - `python ..\..\tools\sanborn\unet\bench44.py --grids bench44_maps --tag merged --jobs 3 [--paired "OTHER\{grid}\bench44.json"]`
   - Runs go to <temp>\sanborn_bench44_runs\ unless --runs is given.

What I ran, every output redirected into merge/impl/r2 (CPU, python -B, the shim _ws). Scripts are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/impl/r2/scripts/, with a second copy in r2/_second_copy/:
- `sh run_bench.sh --tag final_batch` (also final_guided, and --grids staged/data/sanborn/bench44_maps --tag final), then `python -B paired44.py final keep`;
- `python -B batch104.py run final` and `measure final`;
- `python -B bins44.py run|score final_batch final`;
- `python -B bins12.py`;
- `python -B edge_pdf.py final`;
- `python -B open_sample.py keep 30`;
- `python -B placed5.py`, `guard2.py`, `dryrun2.py`, `thin_check.py` (venv), `q1sys.py`, `make_diff.py` and `safety.py`.

### open_issues

1. **Editor race (v-code 6) is not fixed in code.** edit_server.py is unchanged. If the outline step rewrites N_edges.json while Ben has the plate open and unsaved, his first save is keyed to the old lines.
   - For 90: run run_plates.py 90 before he opens it, or have him reload the page afterwards.
   - A real fix needs /data to return a hash of N_edges.json and the page to send it back with /save. That is a change to Ben's editor, which I did not make.
2. **Plate 90 still has known wrong lines inside the map.** They need Ben's check:
   - short pieces on the CITY LIMITS dash-dot line inside the bottom avenue (where v-eye's wrong block-line samples were);
   - the lot-line pocket hole in block 15 (3 sides, 554 px);
   - bridges and chords v-eye noted.
   - The south side of the bottom avenue, along the map edge, is not exported.
3. **The far side of the outermost street on uncut sheets is still missing.** For example, about 14k px on 21 against A (v-eye). With the margin masked, no block lies beyond it. outline-nesting has the same gap.
4. **The rail drop also removes some real lines.** On 44 it removes block 18's Vandalia side (426 px, 75% on Ben's map). Front St on 3 is unsure. The measured net effect is positive (precision +0.058 on 6 of 6 grids).
5. **Shared with A, not addressed:**
   - the chord at the sharp bend on 64A;
   - ring-corner spurs and a gasometer chord;
   - 7 of 24 sampled bridges wrong (v-eye);
   - Zimmer Ave's north side on 30;
   - 4 blocks lost where the seed is under MK_SEED_MIN (18B x3, 85A).
6. **Unclosed rings stay out.** 280 such outlines (195 blocks, 85 holes) on 83 plates are left out, and a few real street sides go with them (by eye 5 of 30 sampled lines; 18B's left edge per v-batch).
7. **Plate 47 (400 ft):** after sorting with blocks its railroad bin falls from 26,540 to 0 px. Not looked at.
8. **The 12 tile-grid PNGs (47 MB) are a copy step**, not part of the diff. Whether they belong in git is Ben's choice.
9. **Timing numbers were taken with other jobs running beside them.** The run_plates total of about 2 h is an estimate.
10. **Limits of the numbers:**
    - The rail rules were tuned on 44, so the 44 rail numbers are in-sample.
    - The bins reference is rule-based; only its block-line bin is Ben's.
    - bench44's PQ ignores holes.
    - Every by-eye figure is an estimate from small samples (open_verdicts.json is mine; edge, bridge and hole samples are v-eye's).
11. **The run_plates rerun is Ben's to start.** It rewrites N_edges.json, outlines.json and the bins on the 104 unplaced plates, 90 included. None of them has edges_ben.json today. After that, Ben's edits on 90 are protected by the N_new/ guard.


## implementer, first report

### summary

I wrote the merged outline step and the street-binning fallback as complete files in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged/. All seven code files and the scale table are staged, and C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged.diff reproduces every staged non-PNG file byte for byte when applied to fresh copies of the repo files. Nothing in tools/, unet_data, picks22_guided, streetmap or cufp changed: the six repo hashes are as given, and no file there is newer than my start. There was one slip, described under open issues; I moved the file back.

Plate 44, measured on the batch's maps:
- Blocks: PQ 0.543, the same as outline-quality (A) alone; the batch had 0.431.
- Ben's interior lines found: 62.1% (A alone 61.0%, batch 53.2%).
- Shown lines that are right: 82.3% (A 76.0%, batch 74.8%); green 87.4%.
- Ben's delete length is 21.6k px (A 33.1k); draw length 67.9k px (A 70.2k).
- 5 of Ben's 55 blocks close (A 6).
- Over the 6 tile grids: PQ is identical to A on every grid. Recall gains +0.010 on 6 of 6 grids and precision +0.058 on 6 of 6.
- Against the repo's outline step: PQ +0.068 (sd 0.029, 6 of 6), recall +0.089 (6 of 6).

Most of the precision gain comes from dropping sides that lie on railroad ink. On 44 those 34 sides are 2.7% on Ben's lines, and on the yard plates 1B, 3, 2 and 41 they are yard tracks by eye.

Ben's report about plate 90 ("the streets are not being binned at all") is fixed in the staged ink_bins.py. A plate without his street map now takes its block lines from what the line editor shows of N_edges.json, with his edits, and its ground from the networks' blocks.
- On 90: block line 0 to 651k px, lot line 0 to 1.08M, water pipe 0 to 461k, sewer 0 to 85k, 'not sorted' 2.43M to 163k (the margin and KEY).
- On 44, against the sort with his map: 93.9% of all ink lands in the same bin. Block line 74.8%, lot line 94.6%, water pipe 92.7%, sewer 94.3%, building outline 99.3%.
- Railroad against his 28 tracks is the same as with his map: 98.4% found at 99.5% precision, no false track.

run_plates.py now runs the block step before the ink sorting. A dry run against the real data shows that a plain run would redo on the 104 unplaced plates only the outline step plus the ink sorting and tracks, and never the networks.

The map-edge fix was done as specified, but measured it does not bring back the lines outline-nesting lost. Those lines are the far side of the outermost street, and once the margin is masked no block lies beyond them. Of 250 such batch lines, 20 come back. The cause is shown and a next step is proposed under open issues.

Plate 90's N_edges.json is not rewritten yet. That needs Ben's OK, before he starts editing 90.

### staged_files

All under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged/, mirroring the repo:

1. tools/sanborn/unet/outlines.py (replaces the file at sha bccc2b34). I reused the earlier implementer's draft and finished it.
   - Kept: one watershed marker per block (MK_CUT 3, MK_SEED_MIN 2000), each block traced on its own; the rings (RING_CORNER 400, COLIN_ANG 4, COLIN_OFF 12, COLIN_GAP 250, SNAP_JOIN 12) and bridges; the green gate, with 'on print only'.
   - Holes: each block is traced with RETR_CCOMP. Holes of MIN_AREA or more become hole polygons (hole=True), listed first, gated by HOLE_PARENT = 3.
   - PDF sheets: map_area mask. A side is paper_edge only along the paper's edge band or along the furniture and frames map_area found.
   - QA flag: Q1 (step-4 length against the line network's skeleton), Q2 (nesting in the union mask), Q3 (from data/sanborn/scale_table.json only), Q5.
   - New 'on rail' second pass; the railroad source rules are under choices.
   - New options: --area-png, --lines-png, --out, --bins-png, --hole-parent.
   - Guard: refuses to overwrite a placed plate's outlines.json unless --force, and says why.
   - N_outlines.json gains 'version' (blocks_noguide.outline_version()), 'rail' and 'seconds'.
   - New outputs: N_mapground.png (1/8 size, PDF sheets only, read by ink_bins) and, with --out only, N_blockinst.png.
   - The docstring holds the dated notes quoting Ben.

2. tools/sanborn/unet/blocks_noguide.py (replaces sha 3700ff13).
   - step4(polys, keep_unlined, rail_drop) can be imported without torch: the torch, unet and edgenet imports are inside predict() and __main__.
   - Step 4 drops short, paper_edge, 'not on a line' (KEEP_UNLINED = False) and 'on rail' (RAIL_DROP = True).
   - outline_version(): a 12-character hash of outlines.py, blocks_noguide.py and map_area.py.
   - New --outlines-only (saved maps; steps 3 and 4 only). I also added --out DIR, which was not asked for: it is my test path.
   - N_blocks_ng.json gains holes, bridges, on_rail, rail, suspect, suspect_why, qa, version and edges_file. The printed line gains holes, bridges, rail and SUSPECT with the reasons.
   - Guard: on a plate with picks22_guided/22-N/edges_ben.json it writes unet_data/N_edges.new.json instead of N_edges.json and prints why.

3. tools/sanborn/unet/map_area.py: new, a copy of visual-pdf/map_area.py. Only the docstring changed, and its command line now needs --out, so it never writes beside the code.

4. tools/sanborn/unet/templates/*.png: new, the 9 bench templates. They are byte-identical to visual-pdf/templates and are not in the diff, because they are PNGs.

5. tools/sanborn/unet/ink_bins.py (replaces sha de9b7914).
   - Fallback for plates without Ben's street map and without a guide: lines from street_map.editor_lines(N_edges.json, edges_ben.json); block ground from block_ground(outlines.json), with holes cut out and nested blocks refilled.
   - Street ground is the rest of the paper; on PDF sheets, off the map ground (N_mapground.png) is 'not known'. The UNSURE option exists but is off.
   - New ben_masks() and ben_railroad(): Ben's-track handling factored out, with the same results, so outlines.py can use it too.
   - New options: --no-map, --edges, --outlines, --json, --unsure. --save still writes no N_bins.json.
   - N_bins.json gains a plain note (the networks' guess, not Ben's map, with the files named), ground_from, and made_from (each input file with its sha256).

6. tools/sanborn/unet/street_map.py (replaces sha 41d33506): the one shared function editor_lines() (the editor's lines with Ben's edits). main() calls it and otherwise does what it did. On 44 it gives back all 359 lines of Ben's saved street map exactly.

7. tools/sanborn/unet/run_plates.py (replaces sha 2c6ee4a9).
   - New order: prepare, blocks (blocks_noguide.py, or --outlines-only), ink_bins, rail_tracks.
   - Per-step redo rules: plan() and bins_from(). The record gains outline, rules (now a hash of ink_bins.py, street_map.py and rail_tracks.py), bins_from, block_line_px, not_sorted_px and ground_from.
   - --list prints every plate's steps and why.
   - The docstring is rewritten with the dated quotes.

8. tools/sanborn/unet/bench44.py: new, a port of bench44/bench44.py.
   - It runs the real outlines.py (--area-png, --lines-png, --out), the real step 4 and edit_server's clean() and sheet().
   - Runs go under data/sanborn/bench44_runs/ (option --runs), and the decided-ground cache is kept there.
   - The venv runs the outline step by default.
   - New: --grids DIR (with --jobs and --paired) gives the mean and sd of every headline score; --outline-args, --keep-unlined and --rail-show.
   - The --outlines and --step4 hooks are kept. Scores, JSON keys and folds are unchanged.

9. data/sanborn/scale_table.json: new, identical to census/scale/scale_table.json.

10. data/sanborn/bench44_maps/grid0..grid5/ (44_area.png, 44_lines.png, info.json): new, the 6 tta1 grids. The PNGs are byte-identical to inference/maps/{batch,off1..5}_tta1 and are not in the diff; the info.json files are.

### diff_path

C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/staged.diff

### numbers_44

All measured unless marked. Scripts are in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/impl/scripts/ and outputs in impl/. Bench runs use the staged tools bench44.py through run_bench.sh; the table is impl/bench44_final.json.

**Faithfulness of the port**
- With the old outline step (bench44/outlines_copy.py) and the old step 4 hooked in, every section of bench44.json equals bench44/runs/batch (PQ 0.4309, recall 0.5316, precision 0.7475, delete 32,545 px, draw 80,094 px).

**Batch grid, merged step**
- PQ 0.543 (fold A 0.5621, B 0.5231); 29 matched, 12 merges.
- Recall 0.6214 (A 0.6304, B 0.6107); precision 0.8226 (A 0.8108, B 0.8373); green 0.8737; orange 0.4655.
- Closed 5 (A 3, B 2); delete 21,632 px; draw 67,851 px.
- For comparison, A alone: 0.543 / 0.6097 / 0.7596 / green 0.8414 / closed 6 / delete 33,107 / draw 70,178. The batch: 0.4309 / 0.5316 / 0.7475 / 0.7753 / 0 / 32,545 / 80,094.
- Without the rail test (blank bins): recall 0.6223, precision 0.7629, green 0.8437, closed 6, delete 33,107, draw 67,851. So the street holes alone, against A, give recall +1.3 points, precision +0.3, draw -2.3k px.

**The 'on rail' sides on 44**
- The rail source makes no difference: Ben's 44_bins.png, the unplaced-run bins (rail/runs/44_nomap_bins.png) and the railroad rule run in the step itself all give identical headlines (33 or 34 on-rail sides).
- How right they are (rail_sides44.py, rail_sides44.json): 34 sides, 11,728 px, 2.7% of their length on Ben's lines. Of them, 11 would have been green and are 0% right.
- The result barely moves over a tolerance of 2 to 5 px and a share of 0.3 to 0.7 (2.7% or 1.6% right). All of them lie on bin 4; none on the streetcar bin.
- Shown orange instead of dropped: precision 0.7625, recall 0.6230, delete 33,107.
- Option 2 (KEEP_UNLINED): precision 0.6905, recall 0.6304, 16 closed, delete 50,698. With the rail sides also shown: 0.6485, 18 closed, 62,173.

**Six grids, paired** (paired44.py, paired44_merged.json; base = inference/bench/runs per grid; A = critic/harness/runs/oq__grid)
- Merged against the repo step:
  - PQ +0.068 (sd 0.029, 6 of 6); fold A +0.029 (5 of 6); fold B +0.111 (6 of 6).
  - Recall +0.089 (sd 0.009, 6 of 6); precision +0.066 (6 of 6); green +0.092.
  - Closed 0 to 4.8 (2 to 8); delete -8.6k px (lower on 6 of 6); draw -11.5k px.
  - Mean PQ 0.442 to 0.511 (sd over the grids 0.029).
- Merged against A alone:
  - PQ +0.000 on every grid (identical).
  - Recall +0.010 (sd 0.004, 6 of 6; A +0.011, B +0.010); precision +0.058 (6 of 6); green +0.032.
  - Closed -0.17 (one grid 1 fewer); delete -10.3k px (6 of 6); draw -1.8k px (6 of 6).
- So it is at least as good as A on PQ and recall on every grid.

**Guided maps** (44_pred_edge_v1 + 44_lines_lines_v2)
- PQ 0.6885 (A 0.609, B 0.7621); recall 0.5357; precision 0.8508; green 0.9066; closed 5; delete 15,875; draw 83,226.
- A alone on the same maps: 0.6885 / 0.5357 / 0.8441 / 0.9029 / 5 / 16,824 / 83,226. The repo step: 0.5918 / 0.4109 / 0.7310.

**HOLE_PARENT** (hole_sweep.sh, hole_table.py, hole_sweep.json)
- Fold A: 1.5 to 4 are identical and best (recall 0.6304, precision 0.8108, delete 13,073). 0 gives 0.7893 and 15,224; 6 or 10 give 0.7989 and 14,245.
- Fold B: 2 to 4 are identical (recall 0.6107, precision 0.8373); 1.5 loses recall (0.6030, draw +729 px); 0 gives precision 0.8324.
- Chosen: 3 (4 holes kept, 13 gated on 44).

**Ink bins on 44** (bins44.py, bins44.json)
- The staged ink_bins with Ben's map reproduces the batch's 44_bins.png pixel for pixel.
- Fallback fed the merged step's 44 output (--no-map --edges --outlines):
  - all ink 93.9% in the same bin (95.9% on Ben's decided ground);
  - block line 74.8% (to lot line 12.2%, building outline 6.9%, text 3.3%, pipe 2.8%);
  - lot line 94.6% (to block line 3.0%);
  - building outline 99.3%;
  - water pipe 92.7% (to block line 6.4%);
  - sewer 94.3% (to lot line 5.2%);
  - text 98.6%; railroad and streetcar 100% (same rail input);
  - the reference's 85k px 'not sorted' becomes mostly lot line (70%).
  - On decided ground: block line 80.0%, lot line 97.4%, pipe 96.5%, sewer 96.5%.
- Fallback fed the batch's own 44 lines (bench44/runs/batch): all ink 92.8%; block line 67.0%, lot line 93.4%, pipe 93.1%, sewer 94.4%, building outline 99.3%. So the outline-step gain shows here as block line 67.0% to 74.8%.
- No lines and no ground (what the batch did on unplaced plates): block line, lot line, pipe and sewer 0%; all ink 62.4%.
- UNSURE bands, all worse than off: 64-191 gives 93.1%, 96-160 gives 93.6%, 32-224 gives 92.0%.

**Rail check** (--no-ben; the rail agent's rail_tracks_copy.py and score_rail_bench.py against rail_ben.page_2026-11-21.json, 28 tracks)
- With Ben's map: railroad 98.43% found, 99.45% precise at 10 px, 0 false tracks; streetcar 79.8% / 100%.
- With the fallback ground: railroad identical (98.43% / 99.45%, 0 false); streetcar 80.5% / 100% (30 px: 83.4%).
- With no ground: railroad 98.43% / 97.85%, 3 false tracks (672 px).
- These are in-sample: the rules were tuned on 44.

**Time**
- Outline step on 44 alone: 11.4 s (timing.json).

### numbers_batch

The 104 unplaced plates, outlines only from the batch's saved maps and the batch's N_bins (batch104.py, run 6 at a time; batch104.json, batch104_summary.json). 0 failures, 626 s wall in all. Each group reads batch, then outline-nesting's final, then merged.

**Cut 100 ft (34 plates)**
- Blocks 1,000 / 1,003 / 1,108; holes - / 256 / 182.
- Step-4 lines 14,823 / 15,573 / 11,017; their length 4.14M / 4.26M / 4.60M px.
- Editor lines 13,161 / 13,846 / 10,394; median green share by count 0.962 / 0.962 / 0.832.
- Lines within 150 px of the paper edge: 845 / 846 / 562.
- On rail (merged) 700 sides, 160k px; bridges 4,694.
- Suspect: 8B 15B / 8B 15B / 2 3 15B.

**Cut 200 ft (36 plates)**
- Blocks 1,245 / 1,247 / 1,335; holes - / 76 / 49.
- Lines 16,172 / 16,329 / 12,925; length 4.66M / 4.68M / 5.02M.
- Editor lines 14,778 / 14,931 / 12,397; green 0.966 / 0.966 / 0.845.
- Edge lines 2,433 / 2,434 / 1,891; on rail 645 sides, 127k px.
- Suspect: none in all three.

**PDF 200 ft (24 sheets)**
- Blocks 425 / 815 / 924; holes - / 19 / 8.
- Lines 6,841 / 10,421 / 9,394; length 1.99M / 2.91M / 3.38M.
- Editor lines 6,278 / 9,549 / 8,968; green 0.942 / 0.975 / 0.773.
- Edge lines 365 / 77 / 121; sheets with 5 or fewer blocks 11 / 0 / 0; on rail 310 sides, 67k px.
- Suspect: 13 sheets / 41 74 / 41.

**400 ft (10 plates)**
- Blocks 28 / 78 / 98; holes - / 64 / 28.
- Lines 703 / 1,641 / 1,610; length 158k / 335k / 446k.
- Editor lines 642 / 1,537 / 1,537; green 0.877 / 0.942 / 0.538.
- Plates with 5 or fewer blocks 9 / 4 / 3; all 10 suspect in all three.

**All 104 plates**
- Blocks 2,698 / 3,143 / 3,465.
- Side length 10.94M / 12.19M / 13.45M px.
- Editor lines 34,859 / 39,863 / 33,296: fewer but longer, because the rings join collinear pieces.

**Suspect list (merged)**
- 2 3 15B 41 46 47 48 49 50 92 93A 93B 94 95 (14 plates).
- Against outline-nesting:
  - 8B (Q1 is now 0.687) and 74 (now 0 nested) are cleared;
  - 2 is newly flagged (Q2, 2 nested), and so is 3 (Q1 59%, after the yard sides are dropped).

**Rail demotion**
- 1,667 sides, 356k px: 2.6% of side length. Mostly on the yards: 1B 128, 3 136, 2 90, 41 77.
- By eye (rail_crops.py, impl/rail_crops/*_crop*.jpg) they are yard tracks.
- Plate 5: the batch's bins put 11 real block sides on the rail (5 by the railroad bin, 6 by the streetcar bin). Run with the blocks, the rule puts 1.

**Plate 90 itself**
- Batch: 1 block, 3 lines.
- Merged: 55 blocks, 1 hole, 456 step-4 lines, 438 editor lines, 357 green, 19 rail sides dropped (using Ben's tracks); not suspect.

**Map-edge fix** (24 PDF sheets at 200 ft; pdf_edge.py, pdf_edge.json, pdf_edge/*.jpg, pdf_edge_lost.py)
- Map masks are identical to outline-nesting's cached masks on all 24 sheets.
- Lines within 40 px inside the map edge: merged 817 (203k px) against outline-nesting's 196 (26k px).
- Merged's sides in that band, by state:
  - 'on print only' 657 (169k px);
  - 'on print' 159 (34k px);
  - 'not on a line' 1,058 (292k px, dropped by step 4);
  - on rail 10.
- The batch lines outline-nesting lost in that band: 250 lines, 83.7k px. The merged step has 20 of them back (3.7k px).
- Merged against outline-nesting overall:
  - kept and new: 700 lines (187k px) in the edge band, 1,367 (270k px) on the map, 11 (3.6k px) off it;
  - lost: 48 (6.8k px) in the edge band and 790 (124k px) on the map.

**Bins before and after** (bins_sample.py, bins_sample.json; staged blocks_noguide.py --outlines-only --out, then staged ink_bins.py)

| plate | block line | lot line | water pipe | sewer | not sorted | railroad |
|---|---|---|---|---|---|---|
| 90 | 0 to 650,637 | 0 to 1,081,385 | 0 to 460,706 | 0 to 84,823 | 2,428,935 to 163,297 | 209,112 to 202,954 |
| 5 | 0 to 1,151,581 | 0 to 631,003 | 0 to 976,454 | 0 to 189,171 | 2,189,500 to 0 | 81,635 to 29,381 |
| 66 | 0 to 1,506,075 | 0 to 1,760,242 | 0 to 888,086 | 0 to 142,483 | 4,011,418 to 0 | 67,497 to 37,959 |
| 3 | 0 to 610,831 | 0 to 1,094,900 | 0 to 593,176 | 0 to 92,188 | 2,192,392 to 0 | 1,659,270 to 1,645,496 |
| 30 | 0 to 667,304 | 0 to 1,328,843 | 0 to 396,627 | 0 to 72,566 | 2,652,299 to 177,525 | 67,792 to 66,443 |
| 60B | 0 to 364,811 | 0 to 436,187 | 0 to 58,325 | 0 to 3,408 | 842,971 to 0 | 0 |
| 64A | 0 to 625,967 | 0 to 1,633,164 | 0 to 341,403 | 0 to 56,667 | 2,611,361 to 0 | 780,359 to 770,171 |

- On 90, building outline goes 259,304 to 232,200 and streetcar 214,310 to 214,026.
- Plate 90's 'before' is the editor-button run of 14:09 with his rail.
- On 5, building outline falls from 3.83M to 3.06M px: block lines take part of it.
- On 90 I looked at the overview and 3 full-resolution crops myself (bins_sample/90_overview.jpg and 90_crop_*.jpg). Block sides are green, lot lines inside blocks light blue, and the labelled pipes and sewers navy and teal; curved streets around the circle are right. Wrong: street stubs beyond the last blocks (south of Carthage Ave) come out as water pipe.

**Time per plate** (timing.json, one at a time)
- 44: 11.4 s (its bins are usable).
- 66: 21.9 s with the railroad rule run in the step, 11.2 s once the new bins exist (byte-identical outlines).
- 90 (PDF): 28.4 s. 47: 26.6 s.
- In the 6-at-a-time run the medians were 33 s (cut) and 48 s (PDF 200 ft), inflated by the parallel load.

### choices

1. Base: I started from the earlier draft. Its markers, rings, gate, RETR_CCOMP holes and map_area 'fixed' mask match A and B. I rewrote the rail test as a second pass and added the CLI, the guards, step 4 imported from blocks_noguide, N_mapground.png and the counts.

2. HOLE_PARENT = 3. Fold A is flat and best from 1.5 to 4; fold B confirms 2 to 4 and rejects 1.5. 3 is the middle of the plateau and is outline-nesting's value (hole_sweep.json).

3. Rail demotion. 'On rail' means more than 50% of the side within 3 px of railroad ink (bin 4 only).
   - Insensitive on 44 for a tolerance of 2 to 5 px and a share of 0.3 to 0.7 (rail_sides44.json).
   - Streetcar is excluded: 0 sides on 44, and on 5 the streetcar bin lay along 6 real block sides.
   - Source of the railroad ink:
     - The ink sorting's bin 4 when its N_bins.json says it was sorted with a block ground ('ground_from': map, nets or label; for the old format, no 'NO STREET MAP' or an old label).
     - Otherwise ink_bins.railroad() is run in the step on the step's own block ground, with Ben's rail_ben.json tracks through the shared ben_masks() and ben_railroad().
   - Why: the 21 Nov batch's bins on unplaced plates were sorted with no blocks, and they demoted 5 real green block sides on 5 (11 counting the streetcar bin); the rule run on the blocks demotes 1.
   - On a fresh, never-sorted plate this is exactly what the ink sorting will put in bin 4. On 66 both routes give byte-identical outlines.json.
   - Cost: 10-20 s per plate until the plate is re-sorted.

4. RAIL_DROP = True. Dropping takes precision 0.7629 to 0.8226 and delete 33.1k to 21.6k px, for -0.1 point of recall. Showing them orange does not help (0.7625). By eye they are yard tracks on 1B, 3, 2 and 41.

5. KEEP_UNLINED = False (option 1), as the task fixed it. Option 2 is measured above.

6. Ink-bins fallback.
   - Order: Ben's street map, then the networks' block step (plates without a guide, or --no-map/--edges/--outlines), then the old label as before (placed plates 43, 45, 80, 82A).
   - Ben's edges_ben.json is applied only to the plate's own N_edges.json: a file given by --edges is not keyed to his edits.
   - The orange lines count, because the editor shows them.
   - UNSURE is off: every band tried is worse on 44.
   - Off-map ground on PDF sheets is 'not known'.

7. Q1 uses the step-4 length, the census's own definition (its editor_len was the N_edges.json length). Q2 counts nesting in the union mask.

8. The scale table is read as tools/sanborn/unet/../../../data/sanborn/scale_table.json, which is the repo's data/sanborn/scale_table.json. That is the same repo-relative style run_plates.py uses, not _ws.DATA: it also lets the staged tree find its own copy in tests. There is no bench-folder fallback.

9. Rules hash = ink_bins.py + street_map.py + rail_tracks.py, because the shared line function is part of the sorting. edit_server.py is left out, so UI edits do not re-sort everything.

10. bench44 runs the real edit_server clean() and sheet() instead of copies. The port was proven faithful as described.

11. The map-edge fix is implemented exactly as specified. It was measured, and it does not recover the far-side lines (see open issues). I did not add an unmeasured mechanism for them.

### how_to_run

**Applying** (Ben's step; nothing was applied)
From the repo root:
```
git apply data/sanborn/bench_2026-11-21/merge/staged.diff
```
Then copy the PNGs, which are not in the diff:
- merge/staged/tools/sanborn/unet/templates/*.png to tools/sanborn/unet/templates/
- merge/staged/data/sanborn/bench44_maps/gridK/44_area.png and 44_lines.png to data/sanborn/bench44_maps/gridK/ (K = 0..5)
Run the commands below from data/sanborn, or from the repo root for run_plates.

**The rerun through run_plates.py**
- `python tools\sanborn\unet\run_plates.py --list` prints each plate's steps and why, and writes nothing.
- `python tools\sanborn\unet\run_plates.py` (or with plate numbers) runs them.
- What a plain run redoes, as the dry run showed (impl/scripts/dryrun_run_plates.py, impl/dryrun_run_plates.txt; nothing was written):
  - on all 104 unplaced plates: 'outline' (blocks_noguide.py N --outlines-only), then 'bins' (ink_bins.py, then rail_tracks.py);
  - on 43, 44, 45, 80 and 82A: 'bins' only, because the rules hash changed;
  - 'nets' on 0 plates. The networks run again only if they are retrained or a plate's maps are missing.
- Time is an estimate, not measured as a whole: about 25 s outline plus about 45 s ink and tracks per plate, so about 2 h for 109 plates.
- It overwrites unet_data/N_edges.json, N_bins.* and N_rail_rule.json and picks22_guided/22-N/outlines.json of the 104 plates (not 90's N_edges.json if Ben has edited it by then). That needs Ben's OK.

**Outlines only, one plate**
- `..\..\tools\sanborn\unet\.venv\Scripts\python.exe ..\..\tools\sanborn\unet\blocks_noguide.py 90 --outlines-only`. Add `--out DIR` to look without writing to the repo.
- Or the outline step alone: `python ..\..\tools\sanborn\unet\outlines.py 90 area_ng1 lines_ng1 --out DIR`.

**Ink sorting test**
`python ../../tools/sanborn/unet/ink_bins.py 44 --no-map --edges RUN/44_edges.json --outlines RUN/outlines.json --save OUT.png --json OUT.json`

**The bench**
- One run: `python ../../tools/sanborn/unet/bench44.py --tag merged`. Runs go to data/sanborn/bench44_runs/; the venv runs the outline step.
- Every grid: `python ../../tools/sanborn/unet/bench44.py --grids bench44_maps --tag merged --jobs 3`.
- Other runs: `--area/--lines` for the guided maps; `--outline-args="--hole-parent 2"`, `--keep-unlined`, `--rail-show`.

**What I ran** (from the staged tree)
- impl/scripts/run_bench.sh: the staged bench44.py with the shim _ws and --runs impl/bench44_runs.
- common.py: the PYTHONPATH shim, -B, and the guard that outputs stay in merge/impl.
- Also batch104.py, bins44.py, bins_sample.py, pdf_edge.py, paired44.py, hole_sweep.sh, rail_sides44.py, guard_test.py, street_map_check.py, dryrun_run_plates.py and make_diff.py.

### open_issues

1. Map edge on PDF sheets: the far side of the outermost street (for example Madison Rd's north side on 79; picture impl/pdf_edge/79_lost_crop0.jpg) is still missing. The batch had it only as a side of the margin it called block. With the margin masked, no block lies beyond it: 250 lines (83.7k px) on the 24 sheets, 20 back. A likely fix is the off-map ground as its own watershed marker, keeping its ring's sides that lie on ink. It needs care with the outlines.json format (bench44, ink_bins.block_ground) and is not implemented.

2. Street stubs beyond the last blocks at a map edge (90, south of Carthage Ave) are sorted as water pipe, because nothing tells the sorting they are block lines there.

3. The edges_ben guard protects only N_edges.json. outlines.json is still rewritten, so on such a plate the bins would take lines from the old N_edges.json with Ben's edits but ground from the new outlines. No unplaced plate has edges_ben.json yet. Before Ben starts on 90, rerun 90 (run_plates.py 90) so its N_edges.json is the merged one (55 blocks, 438 lines). That overwrites the batch's 90 outputs and needs his OK.

4. QA changes:
   - 8B, a bad small piece in the census, is no longer flagged: Q1 is 0.687 now that the rings add length.
   - 74 is cleared (0 nested).
   - 2 (Q2) and 3 (Q1 59%, after the yard sides are dropped) are newly flagged.
   - The thresholds are the census's and in-sample.

5. Fewer holes (267 against outline-nesting's 415 on these plates): with each block traced on its own, a street ringed by several blocks is not a hole of any of them. Its sides are those blocks' own sides.

6. The railroad rule run inside the outline step adds 10-20 s per plate until a plate is re-sorted by the new ink_bins. On 41, one short avenue side across a switch was dropped by eye.

7. All truth is plate 44 (100 ft); every other number is a count or an eye check. The 44 rail numbers are in-sample.

8. The plate seconds in batch104 were measured 6 at a time and are inflated. The whole-run time for run_plates is an estimate.

9. bench44's --faith is meaningful only with the old outline step hooked in through --outlines.

10. Ben's git has core.autocrlf=true. The apply check was byte-exact with core.autocrlf=false; an in-repo `git apply` follows his git's line-end settings. The bench44_maps info.json files have CRLF line ends, as copied.

11. Slip: at 14:34:57 my rail_sides44.py imported the staged bench44 as a module. Its load_truth() cached decided_half.png in the tool's default runs folder, data/sanborn/bench44_runs/cache/, which is outside my folder. I moved that file to impl/stray_moved_back/ (it equals my own cache) and removed the two empty folders. Nothing else was written outside merge/: the repo hashes are unchanged and no file under tools/, unet_data, picks22_guided, streetmap or cufp is newer than my start.

12. A second copy of my scripts, the staged code and the diff is in impl/_second_copy/.


## check: v-44

v-44 report: an independent check of the staged merge on plate 44 (21 Nov 2026)

Everything is in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-44/. All runs were on the CPU and nothing was trained. Every number below is measured unless I mark it as an interval or an estimate.

VERDICT
I reproduced every plate-44 number the implementer gave for the outline step, the bins and the rail, exactly, with my own hooks and scripts.
- The two harnesses agree. On 11 run pairs, the original bench44.py (with my hooks) and the staged bench44.py give the same value for all 1,555 numbers per run. outlines.json, 44_edges.json and 44_shown.json are byte-identical, and so is the decided-ground mask (0 px differ).
- The merged step leaves A's blocks unchanged. Block IoUs and false blocks are identical to A alone on all 6 grids. All of its gain over A is in the lines:
  - precision +0.058, which comes from the rail demotion;
  - recall +0.010, which comes from the street holes.
- The map-edge code never runs on 44 (map_ground 'paper' in all 7 runs), so it cannot be measured here.
- The fallback ink sorting fixes the "streets not binned" problem on 44, and the rail rules did not get worse.

SETUP
- harness/bench44.py and harness/outlines_copy.py are cmp-identical copies of bench44/bench44.py and bench44/outlines_copy.py, with cache/decided_half.png copied beside them.
- hooks/outlines_staged.py runs the staged outlines.py with --area-png, --lines-png and --out RUN_DIR under the venv with -B.
- hooks/step4_staged.py loads the staged blocks_noguide.step4 by path, with variants railshow, norail and keepunlined.
- hooks/step4_A.py and hooks/step4_repo.py check their filter line against outline-quality/proposed and the repo's blocks_noguide.py.
- shim/_ws.py has no _mirror(), and scripts/launch.py pre-imports it before the staged ink_bins, so the repo's _ws.py is never imported.
- The runner is scripts/run_bench.py; the outputs are in harness/runs/TAG/ and runs_index.json.

1. OUTLINE STEP ON 44 (original harness; run_bench.py, then analyze44.py into analyze44.json)

Batch grid (all / fold A / fold B):

| | PQ | recall | precision | green | closed | delete px | draw px |
|---|---|---|---|---|---|---|---|
| Repo step (batch) | 0.4309 / 0.4737 / 0.3852 | 0.5316 | 0.7475 | 0.7753 | 0 | 32,545 | 80,094 |
| A alone | 0.5430 / 0.5621 / 0.5231 | 0.6097 | 0.7596 | 0.8414 | 6 | 33,107 | 70,178 |
| Merged | 0.5430 / 0.5621 / 0.5231 | 0.6214 (A 0.6304, B 0.6107) | 0.8226 (A 0.8108, B 0.8373) | 0.8737 | 5 (A 3, B 2) | 21,632 | 67,851 |

- Merged also: 29 matched (repo step 23), 12 merges (13), 8 false blocks (13); orange 0.4655.
- The repo-step and A-alone rows reproduce the batch baseline and outline-quality's result exactly.

Six grids, paired, merged minus the repo step (mean, sd, grids that gain, t interval over the 6 grids):
- PQ 0.442 to 0.511: +0.068 (sd 0.029), 6 of 6, interval +0.038 to +0.099.
  - Fold A +0.029 (sd 0.037), 5 of 6, interval -0.010 to +0.068. The fold-A gain is not clear of the grid noise.
  - Fold B +0.111 (sd 0.051), 6 of 6.
- Recall +0.089 (sd 0.009), 6 of 6; fold A +0.083, fold B +0.096.
- Precision +0.066, 6 of 6 (fold A +0.062, fold B +0.070); green +0.092.
- Matched blocks +4.3; merges -0.7.
- Blocks closed 0 to 4.8 (range 2-8); intact rings 0 to 39.2.
- Delete -8.6k px and draw -11.5k px, both lower on 6 of 6. A alone made delete worse on 6 of 6 (+1.7k).

Bootstrap of the PQ change, merged minus the repo step (4,000 resamples of Ben's 55 blocks, paired; these are computed intervals, not measurements):
- Batch grid: +0.112.
  - With the false blocks held fixed, 95% interval +0.057 to +0.181.
  - With each false block resampled together with its nearest block, +0.044 to +0.190.
- Mean over the 6 grids: +0.068.
  - Blocks resampled: +0.037 to +0.107.
  - Grids resampled too: +0.031 to +0.120.
- The repo step's own PQ interval on the batch grid is 0.319-0.530.

Merged against A alone, 6 grids:
- PQ, matched blocks, merges and false blocks all +0.000 on every grid and fold.
- Recall +0.010 (sd 0.004), 6 of 6, on both folds.
- Precision +0.058, 6 of 6; green +0.032.
- Closed -0.17 (one grid lost 1); intact rings +4.8.
- Delete -10.3k px and draw -1.8k px, both on 6 of 6.

Guided maps (edge_v1 + lines_v2):

| | PQ (A / B) | recall | precision | green | closed | delete px | draw px |
|---|---|---|---|---|---|---|---|
| Repo step | 0.5918 (0.5014 / 0.677) | 0.4109 | 0.7310 | 0.8435 | 0 | 28,054 | 112,965 |
| A alone | 0.6885 | 0.5357 | 0.8441 | 0.9029 | 5 | 16,824 | 83,226 |
| Merged | 0.6885 (0.609 / 0.7621) | 0.5357 | 0.8508 | 0.9066 | 5 | 15,875 | 83,226 |

Switching parts off (6-grid paired changes against merged, unless marked):
- **Holes off** (--hole-parent 1e-9):
  - PQ unchanged; recall -0.011, 6 of 6, both folds;
  - precision -0.001; draw +1.8k px; intact rings -4.8.
  - This variant gives A's draw length exactly.
  - Every hole kept (HOLE_PARENT 0, batch grid only) is worse: precision 0.8226 to 0.8084 and delete 21.6k to 24.2k px.
  - The harness paints blocks over their holes, so its PQ cannot see them. With the holes cut out of the raster (sides44.py), PQ is 0.5434 against 0.5430.
- **Rail test off** (norail):
  - precision -0.057, 6 of 6, both folds (A -0.058, B -0.054); green -0.031;
  - recall +0.0006; closed +0.17; delete +10.6k px.
  - Blank bins on the batch grid gives the same as norail: 0.6223 / 0.7629 / 6 closed / 33,107 delete.
  - Against A, norail's precision is only +0.0015, so almost all of the merged precision gain is the rail drop.
- **Rail shown orange instead of dropped** (railshow): precision -0.057, delete +10.7k px, recall +0.0009.
- **Rail from the rule alone, without Ben's tracks** (railrule): identical to merged on every grid apart from one grid (-21 px delete; 33 rather than 34 on-rail sides on the batch grid). So on 44 the drop does not depend on Ben's tracks. It is still in-sample, because the rail rules were tuned on 44.
- **On-rail sides on the batch grid** (sides44.py): 34 sides, 11,728 px, 2.7% of their length on Ben's lines.
  - 11 would have been green; they are 4,464 px and 0.0% on his lines.
  - Over the other grids, 21-41 such sides, 0.3-2.7% on his lines.
- **Hole sides on the batch grid:** the 8 'on print' sides (2,447 px) are 96% on his lines; the 8 'not on a line' sides (553 px) are dropped by step 4.
- **Option 2** (KEEP_UNLINED):
  - closed 4.8 to 15.0; precision 0.833 to 0.697; delete +29.5k px; recall +0.008.
  - On the batch grid: 0.6905 / 16 closed / 50,698 delete.
- **Map-edge handling:** not measurable on 44, a cut plate (map_ground 'paper'). Plate 90 counts only, no truth (p90.py into p90.json):
  - The staged step gives 55 blocks, 1 hole, 456 step-4 lines (161k px), 357 green, 438 editor lines and 19 rail sides. This matches the implementer.
  - With outline-nesting's rule (every side along the map edge paper_edge) the same 426 lines are kept inside the map, but within 40 px of the edge 4 lines (547 px) against 30 (5.3k px, 12 green).
  - With no map mask: 41 blocks, 295 lines, and Q2 flags 32 nested regions.
  - Whether the extra edge lines are right needs Ben's check of 90.

2. BINS ON 44 (staged ink_bins.py with --save/--json into bins/; bins44.py into bins44.json)

Faithfulness:
- The staged ink_bins with Ben's street map, the repo's ink_bins.py and unet_data/44_bins.png are identical pixel for pixel. The same holds with --no-ben.

Fallback (--no-map, fed the merged step's 44 edges and outlines, batch grid) against the reference with Ben's map:
- All ink in the same bin: 93.92% (95.89% on Ben's decided ground).
- Each bin below gives the share of the reference's px the fallback puts in the same bin, then the share of the fallback's own bin the reference agrees with:
  - block line: 74.8%, then 85.0%. The rest goes to lot line 12.2%, building outline 6.9%, text 3.3% and water pipe 2.8%. On decided ground: 80.0% and 94.2%.
  - lot line: 94.6%, then 86.0% (3.0% goes to block line).
  - building outline: 99.25%, then 94.6%.
  - water pipe: 92.7%, then 92.4% (6.4% goes to block line).
  - sewer: 94.3%, then 87.0% (5.2% goes to lot line).
  - text: 98.6%.
  - railroad and streetcar: 100%, because Ben's rail_ben.json (26 tracks, complete) decides them in both runs.
  - 'not sorted' falls from 85,074 px to 0. Its ground was unknown in the reference, and 70% of it becomes lot line.
- The fallback fed by each of the 6 grids' merged output:
  - all ink 93.86% (sd 0.10, range 93.73-94.01);
  - block line 74.7% (74.2-75.2);
  - lot line 94.6%; pipe 92.5%; sewer 93.0% (91.3-94.3); building outline 99.4%.

Other inputs:
- Fallback fed the repo step's (batch chain's) 44 output:
  - all ink 92.82%;
  - block line 67.0%; lot line 93.4%; pipe 93.1%; sewer 94.4%; building outline 99.3%.
- No lines and no ground (what the batch did on unplaced plates):
  - all ink 62.35%;
  - block line, lot line, pipe and sewer 0%;
  - 'not sorted' takes 99.5% of the reference's 'not sorted' and everything those four bins should have held.

Caution: the reference is itself a rule-based guess. Only its block-line bin comes from Ben's lines, so agreement in bins 2-9 is not correctness.

3. RAIL AGAINST BEN'S 28 TRACKS (rail_ben.page_2026-11-21.json: 21 railroad, 7 streetcar; rail_ben.json still has 26)

rail44.py traces with rail/rail_tracks_copy.py and scores with rail/score_rail_bench.py into rail44.json and rail/. The rules alone (--no-ben), at 10 px:

| Ground | railroad found | railroad precise | false tracks | false px | streetcar found (10 / 30 px) | streetcar precise |
|---|---|---|---|---|---|---|
| Ben's map (staged = repo) | 98.43% | 99.45% | 0 | 228 | 79.8% / 82.6% | 100% |
| Fallback from the merged step | 98.43% | 99.45% | 0 | 228 | 80.5% / 83.4% | 100% |
| Fallback from the batch chain | 98.43% | 99.45% | 0 | 228 | 80.5% / 83.4% | 100% |
| No ground | 98.43% | 97.85% | 3 (672 px) | 900 | 80.5% / 83.4% | 100% |

- So the rail rules are not worse with the fallback ground. They are the same as with Ben's map, slightly better on streetcar, and better than no ground.
- With Ben's tracks used (as the editor runs it): all runs are identical. The railroad bin covers 99.55% of his 28-track railroad within 10 px, with 0 px far from his tracks.
- These numbers are in-sample, because the rules were tuned on 44.

DIFFERENCES FROM THE IMPLEMENTER
None in the numbers. The only step I could not repeat was the implementer's run of blocks_noguide.py --outlines-only on 44: it returns early because 44 has a guide. I ran the staged outlines.py directly plus the staged step4(), which is the path the task asked for.

SAFETY
- The sha256 of every tools/sanborn/unet/*.py, streetmap/22-44.json, picks22_guided/22-44 and 22-90 json file, unet_data/44_* and 90_*, and cufp/44/* is unchanged (repo_hashes_*.txt).
- No file newer than my start stamp exists in tools, unet_data, picks22_guided, streetmap, cufp, configs, staged, impl or bench44 (after_check_newer.txt lists only the merge folder itself and other verifiers' folders).
- No __pycache__ was written in staged.
- A second copy of my scripts, hooks, shim and ablation copies is in _second_copy/.

FILES (all under the v-44 folder above)
- Scripts: scripts/run_bench.py, analyze44.py, agree44.py, sides44.py, bins44.py, rail44.py, p90.py, launch.py.
- Hooks: hooks/outlines_staged.py, step4_staged.py, step4_A.py, step4_repo.py, common.py.
- Ablation copies of the staged outlines.py (one-line edits): abl/railrule_noben/, abl/noholes_code/ (unused), abl/edge_as_nesting/, abl/no_mapmask/.
- Results: runs_index.json, analyze44.json, agree44.json, sides44.json, bins44.json, rail44.json, p90.json.
- Run folders: harness/runs/<chain>__<grid>/ for chains base, A, merged, noholes, norail, railshow, railrule and keepunl, plus hp0__batch and blankbins__batch. Grids are batch and off1..5_tta1, plus guided for base, A and merged.
- Staged-harness runs: staged_runs/. Plate 90 runs: p90/.

## check: v-batch

v-batch: I ran the staged merge on all 104 unplaced plates with no failures. Two things need attention. First, a plain run_plates.py run would redo the ink sorting and tracks on the 5 placed plates, so check 4 fails as you worded it, although the results come out identical. Second, the merged step drops whole blocks whose traced outline has fewer than 3 sides: 326 blocks on 81 plates, and some carry real street lines. Nothing in the repo changed (checked at the end, details below).

All numbers are measured unless I mark them "by eye" or "estimate". Everything is under C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-batch/; scripts are in scripts/.

**How I ran it**
- run104.py runs the staged blocks_noguide.py N --outlines-only --out plates/N/ under the venv, with cwd data/sanborn. This is the path run_plates.py takes.
- Settings: 6 plates at a time, python -B, PYTHONDONTWRITEBYTECODE, and a shim _ws.py so nothing gets made under data/sanborn.
- All 104 plates exited 0.
- My outlines.json is byte-identical to the implementer's impl/plates run on all 104 plates, and the version is 1aecfd64ac3e everywhere.
- measure104.py recounted the batch and B. Both match outline-nesting/measure.csv exactly (0 mismatches). Every batch N_edges.json equals step 4 of its outlines.json.

## 1. Counts (measure104.py → measure104.json, summary104.json)

Each cell reads batch / B / merged. "Editor" means edit_server.clean() lines, with their length in brackets.

| group | blocks | holes | step-4 sides | editor lines | green share, median by count | suspect |
|---|---|---|---|---|---|---|
| cut 100 ft (34) | 1,000 / 1,003 / 1,108 | 0 / 256 / 182 | 14,823 / 15,573 / 11,017 | 13,161 (4.14M) / 13,846 (4.26M) / 10,394 (4.58M px) | 0.962 / 0.962 / 0.832 | 8B 15B / 8B 15B / 2 3 15B |
| cut 200 ft (36) | 1,245 / 1,247 / 1,335 | 0 / 76 / 49 | 16,172 / 16,329 / 12,925 | 14,778 (4.66M) / 14,931 (4.69M) / 12,397 (5.02M) | 0.966 / 0.966 / 0.845 | none in all three |
| PDF 200 ft (24) | 425 / 815 / 924 | 0 / 19 / 8 | 6,841 / 10,421 / 9,394 | 6,278 (1.99M) / 9,549 (2.91M) / 8,968 (3.37M) | 0.942 / 0.975 / 0.773 | 13 sheets / 41 74 / 41 |
| 400 ft (10) | 28 / 78 / 98 | 0 / 64 / 28 | 703 / 1,641 / 1,610 | 642 (0.16M) / 1,537 (0.33M) / 1,537 (0.44M) | 0.877 / 0.942 / 0.538 | all 10 in all three |
| all 104 | 2,698 / 3,143 / 3,465 | 0 / 415 / 267 | 38,539 / 43,964 / 34,946 | 34,859 (10.95M) / 39,863 (12.19M) / 33,296 (13.41M) | 0.957 / 0.965 / 0.813 | 25 / 14 / 14 |

**Green share:** it is not like for like. In the merged step, green also needs the line network to have drawn the line, so the drop is by design.

**Suspect flags:**
- The batch itself has no flag; its column is the census flag.
- The 13 PDF sheets the census flags for the batch are 22, 23, 27, 30, 41, 72, 73, 74, 78, 81, 88, 90 and 91.
- Merged flags and why:
  - 2: Q2, 2 nested regions.
  - 3: Q1, 59%.
  - 15B: Q1, 60%.
  - 41: Q2, 3 nested.
  - 46, 47, 48, 49, 50, 92, 93A, 93B, 94, 95: Q3, 400 ft. 47 also has Q1 56% and Q2 3 nested; 94 also has Q1 50% and Q2 8 nested.
- Against B: 8B is cleared (Q1 is now 0.687) and 74 is cleared (now 0 nested). 2 and 3 are newly flagged. 48 loses its Q1.

**Seconds per plate:**
- **Batch:** median 14.5 s for the whole block step (networks, outline step and step 4; from the "| N s" in run_plates.json).
- **B:** median 22.0 s for its outline step.
- **Merged, in my 6-at-a-time run:** median 60.2 s, max 109 s, 1,105 s wall for all 104. The machine was at 100% CPU from other jobs, so this is inflated.
- **Merged, one at a time on a quiet machine** (timing.py, 8 plates, outputs identical to the main run): median 22.7 s, range 4.8–30.7 s. The table shows merged against B on the same plates; merged is about as fast as B.

| plate | merged | B |
|---|---|---|
| 5 | 22.2 s | 24.8 s |
| 1B | 23.1 s | 23.7 s |
| 60B | 6.1 s | 9.0 s |
| 66 | 21.2 s | 24.1 s |
| 90 | 27.8 s | 23.4 s |
| 79 | 30.7 s | 35.6 s |
| 47 | 26.2 s | 27.7 s |
| 93A | 4.8 s | 4.6 s |

**Plate 90:** merged gives 55 blocks, 1 hole, 456 step-4 sides, 438 editor lines, 357 green and 19 'on rail' sides dropped (using Ben's tracks). The batch had 1 block and 3 lines; B had 45 blocks and 455 editor lines.

## 2. Plates with FEWER editor lines or blocks (fewer.py, lostcheck.py → fewer.json, lostcheck.json, fewer_table.csv)

96 of 104 plates have fewer of something. The 8 that don't: 19, 22, 47, 48, 64B, 74, 94, 95. fewer_table.csv has one row per plate with the numbers and a reason code.

**Fewer editor lines: 78 plates against the batch, 93 against B.** The shown length is higher on all but 5 of them. In total the merged step shows 33,296 lines and 13.41M px, against the batch's 34,859 lines and 10.95M px.

- **Step 4's new drops ("D"):** 69 plates against the batch (73 counting the 4 with lower shown length below), 79 against B (84 counting the 5).
  - With the 'not on a line' and 'on rail' sides kept, the merged step would show at least as many lines as the other run. Over all 104 plates that would be 46,919 lines (15.98M px).
  - Step 4 drops 12,152 'not on a line' sides (2.22M px) and 1,667 'on rail' sides (356k px).
- **Rings join collinear pieces ("J"):**
  - Against the batch: 12, 15A, 60B, 66, 82B.
  - Against B, those 5 plus 28, 67, 68, 69.
  - On these the merged step has fewer lines even with every side kept, but at least as much length.
- **Less length shown** (only these plates):

| plate | merged shown | batch / B shown | 'on rail' dropped | 'not on a line' dropped |
|---|---|---|---|---|
| 1B | 120.5k px | 138.3k | 128 sides, 33.5k px | 230 sides, 36.8k px |
| 2 | 131.9k | 139.0k / 140.2k | 90, 18.2k | 194, 38.1k |
| 3 | 124.8k | 139.5k / 142.4k | 136, 27.7k | 210, 30.8k |
| 9 | 95.7k | 99.0k / 99.6k | 79, 16.9k | 144, 27.1k |
| 50 (vs B only) | 17.9k | 23.5k (B) | 0 | 96, 26.0k |

  - 1B, 2 and 3 are the rail-yard plates.
  - On 9 (by eye, pics/9.jpg and pics/9_0_1800.jpg):
    - The 'on rail' drops run along the C.L.&N. right of way.
    - Some real east-side Garrard Ave pieces that the batch had green are also lost, where the merged block outline cuts across the street and is 'not on a line'.
  - On 50 (400 ft) the dropped sides are mostly imagined ones on blank paper (pics/50.jpg).

**Fewer blocks: 7 plates against the batch, 10 against B.**

| plate | change in blocks | against |
|---|---|---|
| 10 | −1 | both |
| 15B | −1 | both |
| 18B | −7 | both |
| 26A | −1 | both |
| 54A | −1 | both |
| 60A | −2 | both |
| 85A | −1 | both |
| 21 | −1 | B |
| 30 | −1 | B |
| 92 | −1 | B |

I checked every block the merged step lost. The 27 lost against the batch and the 37 lost against B split into two mechanisms:

- **Traced and then thrown away (a new defect): 23 of 27 against the batch, 31 of 37 against B.**
  - The merged step did make these blocks: they are in N_blockinst.png.
  - Then straighten() turned each outline into fewer than 2 'line' pieces. Every piece was under 60 px (MINLEN), or under 130 px (CUT) and not on ink. straighten() returned None, so the whole outline was dropped at outlines.py:259–260 (`if not sides or len(sides) < 3: continue`). Any side that was right goes with it.
  - The batch's step kept such polygons with their short pieces.
  - A debug copy (debug/outlines_dbg.py, run with --out) confirms this on 10 and 18B. The piece lengths are recorded there.
  - Across all 104 plates, 326 block instances on 81 plates are dropped this way, about 6.2M px of block ground (dropped_at_tracing.json). Most: 2 (15), 13 (13), 6 (12), 72 (12).
  - On 44 with the batch maps, 5 blocks and 3 holes are dropped. None overlaps any of Ben's 55 closed blocks, so the plate-44 PQ cannot see this.
  - By eye (pics/10_*.jpg, pics/18B_0_1900.jpg):
    - On 10 the lost blocks are false ones in street junctions, so losing them does no harm.
    - On 18B they are slivers at the left edge of the sheet. Real street lines go with them: the far side of Park, Woods and Burnet, which the batch had green.
- **No merged block at that spot: the other 4 of 27 against the batch, 6 of 37 against B** (18B ×3 and 85A; plus 30 ×2 and 92 against B).
  - The block seed, once cut by the detected lines, gives pieces of about 728–2,196 px by my estimate, at or under MK_SEED_MIN of 2,000. So no marker, or the watershed took the ground.
- In every case, none of the lost blocks was joined into a neighbouring block.

**Suggested fix (not measured):** when straighten() leaves fewer than 3 sides, keep the block as its plain approxPolyDP polygon, with short pieces marked 'short' as before. Then re-bench on 44.

## 3. Ink sorting fallback on 12 plates (bins12.py → bins/N_bins.png and .json, bins12.json)

- **How it ran:** system python, through run_ink.py (which imports the shim _ws first). Options: --edges plates/N/N_edges.json --outlines plates/N/outlines.json --save bins/ --json. None of these plates has edges_ben.json.
- **Before** is the repo's unet_data/N_bins.json. For 90 that is the 14:09 editor-button run with Ben's rail.
- **After** is a ground of 'nets' on every plate.
- Each cell reads before → after, in px.

| plate | block line | lot line | building outline | railroad | water pipe | sewer | not sorted |
|---|---|---|---|---|---|---|---|
| 90 PDF 200 | 0 → 650,637 | 0 → 1,081,385 | 259,304 → 232,200 | 209,112 → 202,954 | 0 → 460,706 | 0 → 84,823 | 2,428,935 → 163,297 |
| 30 PDF 200 | 0 → 667,304 | 0 → 1,328,843 | 227,719 → 210,626 | 67,792 → 66,443 | 0 → 396,627 | 0 → 72,566 | 2,652,299 → 177,525 |
| 79 PDF 200 | 0 → 1,158,654 | 0 → 1,703,592 | 539,130 → 448,742 | 139,106 → 131,898 | 0 → 532,106 | 0 → 101,535 | 3,684,740 → 222,557 |
| 60B cut 200 | 0 → 364,811 | 0 → 436,187 | 91,107 → 61,700 | 0 → 0 | 0 → 58,325 | 0 → 3,408 | 842,971 → 0 |
| 64A cut 200 | 0 → 625,967 | 0 → 1,633,164 | 293,807 → 255,127 | 780,359 → 770,171 | 0 → 341,403 | 0 → 56,667 | 2,611,361 → 0 |
| 26A cut 200 | 0 → 631,909 | 0 → 1,240,249 | 544,602 → 468,397 | 541,060 → 519,903 | 0 → 397,244 | 0 → 104,450 | 2,293,728 → 0 |
| 5 cut 100 | 0 → 1,151,581 | 0 → 631,003 | 3,826,157 → 3,060,348 | 81,635 → 29,381 | 0 → 976,454 | 0 → 189,171 | 2,189,500 → 0 |
| 1B cut 100 | 0 → 621,973 | 0 → 787,858 | 1,329,834 → 1,104,284 | 1,398,360 → 1,355,629 | 0 → 667,715 | 0 → 98,417 | 1,918,282 → 0 |
| 1A cut 100 | 0 → 286,021 | 0 → 179,407 | 737,772 → 583,823 | 4,849 → 2,177 | 0 → 221,520 | 0 → 16,082 | 566,834 → 0 |
| 3 cut 100 | 0 → 610,831 | 0 → 1,094,900 | 1,091,967 → 899,063 | 1,659,270 → 1,645,496 | 0 → 593,176 | 0 → 92,188 | 2,192,392 → 0 |
| 47 400 | 0 → 177,822 | 0 → 1,441,797 | 70,745 → 70,233 | 26,540 → 0 | 0 → 199,624 | 0 → 22,375 | 2,006,520 → 177,231 |
| 93A 400 | 0 → 91,042 | 0 → 212,083 | 30,691 → 23,901 | 0 → 0 | 0 → 36,719 | 0 → 6,946 | 337,337 → 0 |

- **Not sorted:**
  - Only the uncut sheets keep any 'not sorted' (90, 30, 79, 47). It is their margin and KEY, which are off the map ground and so 'not known'.
  - On 90 the old 'not sorted' ink went (k px): lot line 1,076, block line 559, water pipe 451, sewer 84, text 95; 163 stayed.
- **Building outline drops on every plate:** block lines are taken first, so a building front that lies on a block line now counts as block line.
- **Railroad changes:** on 5 the railroad bin falls 81,635 → 29,381, and on 47 it falls 26,540 → 0.
- Each run took 6–32 s.
- **Matches the implementer:** 90, 30, 60B, 5, 3 and 64A give exactly the implementer's numbers.

## 4. Staged run_plates.py in a sandbox (setup_sandbox.py, sandbox_add.py)

**The sandbox:**
- sandbox/ is a small copy of the repo: the staged code, the repo's rail_tracks, edit_server, unet and edgenet, the real configs, and per plate the real small files.
- The scans, maps and bins are real only for the plates I actually ran. The rest are empty placeholders.
- The models are copied with their file times.
- It has its own new venv, whose .pth reads the repo venv's site-packages. torch_directml is stubbed out so the networks can only use the CPU.
- No links into the repo were made.

**--list over all 109 plates** (logs/sandbox_list1.txt):
- Rules 2af7755e4c0f, outline step 1aecfd64ac3e.
- Outline step on 103 plates, networks on 1 (15B, whose maps I removed in the sandbox), bins on 109.
- The networks never run where the maps exist.
- No new PDF plates to prepare: 32 uncut, as before.

**FAIL against "nothing on 43, 44, 45, 80, 82A":**
- Each placed plate gets "bins (rules de9b79144123 -> 2af7755e4c0f)", so ink_bins.py and rail_tracks.py run on all five. The rules hash changed, and it now also covers street_map.py and rail_tracks.py.
- I ran those five for real in the sandbox:
  - outlines.json and N_edges.json were untouched.
  - N_bins.png is pixel-identical on all five (0 px differ), and the rail tracks are identical.
  - N_bins.json gains 'ground_from' and 'made_from' and a longer note.
  - The run_plates.json record is rewritten.
  - Cost: 40–58 s per plate.
- So it is harmless but not "nothing". Options:
  - accept it;
  - set those five records' 'rules' to the new hash once;
  - in plan(), skip the ink sorting on a plate with a guide when bins_from is unchanged.

**Real run on 9 plates** (logs/sandbox_run1.txt): 5, 15B, 43, 44, 45, 60B, 80, 82A, 90.
- **60B and 90:** outline step, then bins, then tracks. N_edges.json and outlines.json are identical to my main run. A plain run rewrites 90's N_edges.json, because it has no edges_ben.json yet; that still needs Ben's OK.
- **5, with a test edges_ben.json** ({"lines": []}, not Ben's): the guard works.
  - N_edges.json is unchanged (sha c36a05d5716369d8). The new lines went to 5_edges.new.json, identical to my main run's.
  - But outlines.json is still rewritten. The ink sorting then mixes the OLD lines with the NEW block ground: block line 1,031,105 px, against 1,151,581 from the new lines.
  - Low priority for now, but it applies to any plate Ben has edited when the outline step changes.
- **15B, maps missing:**
  - The run re-ran the networks (CPU here, 153 s), then the outline step, bins and tracks.
  - The CPU maps are within 2/255 of the batch's GPU maps, with no pixel crossing 0.5. The outline output is identical.
- **Second --list:** 9 of 9 up to date, so a repeat run does nothing.

## Repo safety

- No file under tools/sanborn (venv included), unet_data, picks22_guided, streetmap, cufp or configs is newer than my start stamp.
- No new folders under data/sanborn.
- No __pycache__ in staged/.
- The repo hashes are unchanged: outlines bccc2b34, blocks_noguide 3700ff13, ink_bins de9b7914, street_map 41d33506, run_plates 2c6ee4a9, rail_tracks 16a4c4ed, edit_server f24a99a6.

## Files (all under …/merge/v-batch/)

- measure104.json, summary104.json
- fewer.json, fewer_table.csv, lostcheck.json, dropped_at_tracing.json
- bins12.json and bins/
- timing.json
- plates/N/ (all outputs), logs/
- sandbox/ (logs/sandbox_list1.txt, sandbox_list2.txt, sandbox_run1.txt)
- debug/outlines_dbg.py (a debug copy, run only with --out) and debug/{10,18B,44}.json
- pics/9.jpg, 9_0_1800.jpg, 50.jpg, 10_400_150.jpg, 10_8350_6150.jpg, 18B_0_1900.jpg, 3_outlines_small.jpg
- scripts: common.py, run104.py, measure104.py, fewer.py, lostcheck.py, fewer_table.py, bins12.py, run_ink.py, setup_sandbox.py, sandbox_add.py, timing.py, pic.py

## check: v-eye

## Plate 90 needs fixes before its N_edges.json is rewritten

**Short answer.** The staged merge does fix what Ben reported on 90: its streets are now sorted into bins (counts and samples in section 3). It also does well on rail yards and street holes. But it brings back one thing outline-nesting (B) had removed. On the uncut PDF sheets, the map's own edge is exported again as orange lines, and by eye most of those are river and creek banks, city-limit lines and property lines, not streets. Plate 90 gets about 5k px of these along Mill Creek, plus the CITY LIMITS line exported as a block line, and these lines would then land in Ben's editor.

Everything is in `C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-eye/` (below: `v-eye/`). Scripts are in `v-eye/scripts/`, with a second copy in `v-eye/_second_copy_scripts/`. My eye verdicts are in `v-eye/verdicts.json` (made by `scripts/verdicts.py`).

**Nothing in the repo changed.**
- The six repo tool hashes are unchanged: outlines bccc2b34, blocks_noguide 3700ff13, ink_bins de9b7914, street_map 41d33506, run_plates 2c6ee4a9, rail_tracks 16a4c4ed.
- No file in tools/sanborn, unet_data, picks22_guided, streetmap, cufp or merge/staged is newer than my start stamp.
- One risk I avoided: the staged ink_bins fallback imports the repo's edit_server, which would load the repo's `_ws.py`, and that creates folders under data/sanborn when imported. I ran ink_bins through `scripts/run_ink.py`, which loads the shim `_ws` first and refuses any output outside `v-eye/`. A real `run_plates.py` run would take the repo `_ws` path; that is harmless if the folders already exist.

## 1. The runs (measured)

- **Merged step.** `scripts/run_all.py` ran the staged `blocks_noguide.py --outlines-only --out` on 90, 30, 23, 47, 21, 60B, 64A, 1B, 3 and 5. Plate 44 refuses that path because it has a guide, so it ran the staged `outlines.py --out`. Venv, CPU, -B. Outputs are in `v-eye/runs/merged/N/`.
- **Same as the implementer's.** outlines.json is byte-identical to `merge/impl/plates/N` and `impl/bng/N` on all 10 plates that have one.
- **A (outline-quality).** I ran `outline-quality/proposed/outlines_redirected.py` into `v-eye/runs/A/N/`. It is byte-identical to the stored A outputs for 3, 5, 64A, 90 and 60B.
- **60B: merged is identical to A**, byte for byte.
- **Per-plate results for the merged step.**

| Plate | Blocks | Holes | Lines shown | Green | Bridges | Sides dropped on rail | Suspect |
|---|---|---|---|---|---|---|---|
| 90 | 55 | 1 | 456 | 357 | 31 | 19 | |
| 30 | 33 | 0 | 418 | | | 8 | |
| 23 | 24 | 0 | 465 | | | 23 | |
| 47 | 14 | 0 | 184 | | | 0 | Q1, Q2, Q3 |
| 21 | 8 | 0 | 216 | | | 2 | |
| 60B | 40 | 0 | 217 | | | 0 | |
| 64A | 18 | 0 | 417 | | | 52 | |
| 1B | 41 | 0 | 353 | | | 128 | |
| 3 | 44 | 0 | 331 | | | 136 | Q1 |
| 5 | 64 | 10 | 537 | | | 1 | |
| 44 | 37 | 4 | 376 | | | 34 | |

## 2. Overlays, crops and what I judged

**Overlays** are made by `scripts/views.py thumbs`. The conventions are the same as outline-nesting's thumbs:
- green = on print, orange = other shown lines, cyan = hole sides;
- grey hatching = off the map ground, red = outline of a block covering more than 30% of the map;
- white text header with the counts.

I added two marks: thin magenta for a merged side dropped as 'on rail', and in the crops, thin dark red for a side dropped as 'not on a line' plus a black core in bridging sides.

- `v-eye/thumbs/N.jpg`: batch on top, merged below.
- `v-eye/thumbs/N_4.jpg`: batch | A over B | merged. I looked at all 11 of these.

**Crops** are full resolution, 2 x 2 (batch, A / B, merged), in `v-eye/crops/` (`scripts/crops_list.py`). I looked at:
- 1B_rail_a, 1B_rail_b, 3_rail_a, 3_rail_b, 44_rail_a, 64A_rail_a;
- 90_edge_a, 90_edge_b, 23_edge_a;
- 21_lost_a, 3_lost_b, 30_lost_a, 5_lost_a;
- 64A_hill_a, 64A_hill_b.

The other crops in that folder were made but not looked at one by one; random samples covered their topics.

**Random samples** are in `v-eye/samples/` (`scripts/sample_sides.py`, seed 0, drawn uniformly by length, plates other than 44). These are estimates by eye.

**Masked areas** (measured, then by eye)
- The merged step's map ground is pixel-identical to `visual-pdf/maparea_check` on 90, 30, 23, 21 and 47.
- By eye it is right on 90 and 30: margin, KEY, compass rose and title are masked.
- 23 has the known failure: the two panels are joined, and the Ohio River between them counts as map.
- On 21 and 47 the map edge follows river banks and property lines.

**Street sides along the map edge of the PDF sheets: a regression against B.**
- On the 5 sheets, the merged step shows 191 lines (44.6k px) within 40 px inside the map edge. Of these, 185 (43.7k px) are not in B, and 164 are orange (measured, ad-hoc check from `v-eye/scripts`).
- By sheet: 90 5.1k px, 30 3.5k, 23 15.0k, 21 11.8k, 47 9.2k.
- By eye, 36 sampled lines (`samples/edge_0..5.jpg`):

| Verdict | Lines |
|---|---|
| Real street sides | 4 |
| Unsure | 3 |
| Wrong | 29 |
| of the wrong: river or creek banks | 18 |
| of the wrong: city-limit lines | 5 |
| of the wrong: property or map-limit lines | 5 |
| of the wrong: one chord across open ground | 1 |

- So the 'not paper_edge along the plain map edge' change mostly adds banks and limit lines, not streets.
- It did not bring back the far side of the outermost road on 21: 14k px are lost against A and the batch (`crops/21_lost_a.jpg`). This is the known open defect.

**Rail-yard demotion: right almost everywhere.**
- 342 sides (77.9k px) are dropped on the 10 plates other than 44.
- By eye, 36 samples (`samples/rail_0..5.jpg`): 34 are tracks, so dropping them is right. 2 are unsure: lot 16's edge against the yard on 3, and the right-of-way edge by the canal on 64A.
- Large yards on 1B, 3 and 64A are now cleanly left out (`crops/1B_rail_a.jpg`, `1B_rail_b`, `3_rail_a`, `3_rail_b`, `64A_rail_a`).
- **It can still lose a real block line next to a track.** On 44 the only drop that lies on Ben's lines is block 18's side along the Vandalia right of way: 426 px, 75% on his map (`crops/44_rail_a.jpg`; `lost.py`). The track's ticks reach within 3 px of that line.
- Unsure case on 3: the south edge of Front Street along the Public Landing is drawn as a track and is dropped (`crops/3_lost_b.jpg`).
- Some yard tracks stay green, as they did in all four outputs (`crops/3_rail_b.jpg`).

**Bridges and rings**
- By eye, 24 sampled bridges (`samples/bridges_0..3.jpg`): 16 right (gaps filled on street sides), 7 wrong, 1 unsure.
- The wrong ones:
  - 2 'far' bridges cutting across a street or along a right of way;
  - a corner chord across the mouth of a side street;
  - 2 on tracks;
  - one on a pipe line;
  - one on a creek bank.
- Measured on 44 (`sides_stats.py`): 4,551 px of bridges, 3,085 px of them on Ben's lines (68%).
- **Ring artifacts shared with A:**
  - short green spurs along lot lines at ring corners (`crops/21_lost_a.jpg`);
  - block 49's east side snapped to the lot line between lots 48 and 49 on 5 (`crops/5_lost_a.jpg`);
  - a V-shaped chord across a gasometer on 1B (`crops/1B_rail_b.jpg`).
- Grid blocks on 90 and 60B close as rings by eye. Gaps remain where a side was dropped as 'not on a line'.

**Hole sides: mostly alleys and courts**
- By eye, 24 samples, from plates 5 and 90 (`samples/holes_0..3.jpg`): 18 right (Bailey Ct, Olympia Ct, L'Hommedieu, Thorpe, Andrews, Ross, Starry Alley), 5 wrong, 1 unsure.
- The 5 wrong:
  - 3 are 90's only hole, which is a lot-line pocket in block 15 (554 px);
  - 1 closes the mouth of Bailey Ct at Pugh;
  - 1 is a lot line on 5.
- Measured on 44: hole sides 2,447 px, 2,394 of them on Ben's map (98%).

**Hillside chords on 64A**
- Gentle curves are followed by short straight pieces, about 15-20 px off at the bends (Vineyard Place, `crops/64A_hill_a.jpg`).
- At a sharp bend it goes wrong: the east side of the street running north from Wine Press is one straight orange side, about 50 px off the printed curve at its south end. The corner to Wine Press is dropped as 'not on a line' (`crops/64A_hill_b.jpg`).
- The batch and B followed that curve in short green pieces. This is shared with A.

## 3. Ink-bins fallback (`--save`, on 90, 60B and 5)

`scripts/run_ink.py` runs the staged ink_bins.py with `--edges runs/merged/N/N_edges.json --outlines runs/merged/N/outlines.json`. Outputs are in `v-eye/bins/`.

**Counts, measured, before (unet_data/N_bins.json) and after.** These equal the implementer's.

| Bin | 90 | 60B | 5 |
|---|---|---|---|
| Block line | 0 → 650,637 | 0 → 364,811 | 0 → 1,151,581 |
| Lot line | 0 → 1,081,385 | 0 → 436,187 | 0 → 631,003 |
| Water pipe | 0 → 460,706 | 0 → 58,325 | 0 → 976,454 |
| Sewer | 0 → 84,823 | 0 → 3,408 | 0 → 189,171 |
| Not sorted | 2,428,935 → 163,297 | 842,971 → 0 | 2,189,500 → 0 |
| Building outline | | | 3,826,157 → 3,060,348 |

**Drawings** use ink_bins.COL (`scripts/bins_view.py`):
- `bins/90_thumb.jpg`, `60B_thumb.jpg`, `5_thumb.jpg`: before | after.
- `bins/90_crop_grid.jpg`, `bins/60B_crop_alleys.jpg`: full size.
- On 90's grid, the after view has block lines green along both sides of the streets, lot lines blue inside the blocks, and pipes and sewers in the streets.

**Eye count.** 9 random pixels per bin per plate, uniform over the bin's pixels, 108 in all (`bins/samples/*.jpg`, seed 1). These are estimates.

| Bin | 90 | 60B | 5 | All |
|---|---|---|---|---|
| Block line on a street side | 7/9 | 9/9 | 9/9 | 25/27 |
| Lot line inside a block | 7/9 (1 unsure) | 7/9 | 5/9 (1 unsure) | 19/27 (6 wrong, 2 unsure) |
| Water pipe in a street | 4/9 | 9/9 | 9/9 | 22/27 |
| Sewer in a street | 9/9 | 2/9 | 9/9 | 20/27 |

Why the wrong ones are wrong:
- **Block line, 90:** both wrong samples are on the CITY LIMITS line, which the block step exported.
- **Lot line:** 2 are 60B mid-block alley sides (the alley convention is still open); on 5, a pipe line in an alley, an alley side and a block side; on 90, Muscogee's street side.
- **Water pipe, 90:** street sides the block step did not export, the canal/right-of-way line, and a label stroke. Wherever a street side is missing from N_edges.json, the street ground beside it puts it in water pipe.
- **Sewer, 60B:** that bin is only 3,408 px, mostly the cut sheet edge and bits of block lines.

Also seen: the large block numbers 34 and 35 on 90 now sort as lot line (`bins/90_crop_grid.jpg`). One side of Linneman St on 60B, which the block step missed, sorts as lot line (`bins/60B_crop_alleys.jpg`).

## 4. Regressions

Line comparisons are measured by `scripts/lost.py` (output `v-eye/lost.json`): a line counts as lost when less than half of it lies within 8 px of a merged line. The batch side of the comparison is picks22_guided/22-N/outlines.json, which is what unet_data/N_outlines.jpg draws.

**Against B (outline-nesting)**
1. **Map-edge lines on the PDF sheets**, as above: 43.7k px new against B, by eye mostly wrong. Crops: `crops/90_edge_a.jpg` (Mill Creek bank), `crops/23_edge_a.jpg` (city limits), `samples/edge_*.jpg`.
2. **Plate 30: Zimmer Ave's north side is lost** (378 px, green in B). The merged block spans the avenue: `crops/30_lost_a.jpg`. A has the same loss.
3. **Plate 44 against Ben's map:** lost 1,271 px of B's lines that lie on his map (10 lines: 'not on a line' drops plus the rail drop). Gained 10,308 px on his map, and 4,590 px off it, mostly bridges.
4. **Other plates, lost px against B by cause:**

| Plate | Lost px | Dropped on rail | Dropped 'not on a line' |
|---|---|---|---|
| 1B | 37.8k | 29.2k | 6.8k |
| 3 | 31.9k | 23.3k | 4.3k |
| 64A | 10.7k | 6.4k | 3.7k |
| 23 | 6.9k | | |
| 5 | 6.0k | | |

   The rail part is tracks by sample.
5. **Ring and bridge artifacts and the 64A chord** from section 2: `crops/5_lost_a.jpg`, `crops/1B_rail_b.jpg`, `crops/64A_hill_b.jpg`, `samples/bridges_0.jpg` #3, `samples/bridges_2.jpg` #17.

**Against A (outline-quality alone)**
1. **Rail drop on 44:** block 18's Vandalia side, 426 px (`crops/44_rail_a.jpg`). This is the only loss against A on Ben's lines (320 px on his map).
2. **Plate 21:** 14.0k px lost, the outermost road's far side, now masked off (`crops/21_lost_a.jpg`).
3. **Plate 47:** 1.2k px lost near the paper edge. Not looked at.
4. **90's lot-line pocket hole**, 554 px (`samples/holes_0.jpg` #2, #3).
5. **Edge-band lines:** A had no map mask at all, so these are not new against A.

On 90, 30 and 23, everything else lost against A is rail drops: 5.3k, 1.2k and 3.9k px, tracks by sample.

**Against the batch**
1. **Plate 21:** 15.5k px lost (13.3k of it the masked outer road; `crops/21_lost_a.jpg`).
2. **Rail drops:** 1B 29.2k, 3 23.3k, 64A 6.4k px. Right by sample, except the yard-edge cases and Front St on 3 (`crops/3_lost_b.jpg`).
3. **64A's sharp bend** is now a chord where the batch followed the curve (`crops/64A_hill_b.jpg`).
4. **Plate 44:** lost 1,078 px on Ben's map and gained 12,702 px on it.

On 44, the share of shown line length that lies on Ben's map is batch 76.1%, A 77.6%, B 76.5%, merged 84.0% (`lost.py`, 8 px).

## Notes for the decision
- **Plate 90, if its N_edges.json were rewritten now.** It would carry:
  - the Mill Creek bank as orange lines;
  - the CITY LIMITS line in the south-east;
  - one lot-line hole in block 15;
  - a far bridge across an avenue and a corner chord.

  The south side of the bottom street between Ridgeway Rd and Laurel Ave is still missing (`crops/90_edge_b.jpg`).
- **Implementer's map-edge claim.** They wrote that a street along the map border is kept (e.g. Ruth Ave on 79). On the 5 sheets I checked, about 4 in 36 lines in that band are streets. I did not check 79.
- **Every 'by eye' number is an estimate** from small samples. The sample sizes are given above.

## check: v-code

v-code review of merge/staged/ against the repo (21 Nov 2026). Everything I wrote is in C:/Users/peckb/Documents/_Personal/_Cincinnati Rail/3D/data/sanborn/bench_2026-11-21/merge/v-code/. Nothing in tools/, unet_data, picks22_guided, streetmap or cufp changed: the five repo hashes are still bccc2b34, 3700ff13, de9b7914, 41d33506 and 2c6ee4a9, and no file under those folders is newer than my start stamp.

All staged runs used a review shim (v-code/shim: _ws with no _mirror, plus a sitecustomize that records peak memory) and -B. The working folder was data/sanborn, and every output was redirected into v-code/runs/. Tests that had to write the way a real run does were done in a fake data tree, v-code/fake/data, through v-code/shim_fake.

FINDINGS (most severe first)

1. HIGH: ink sorting trusts any outlines.json, including the batch's broken ones. This affects plate 90 itself.
   - Where: ink_bins.py:393-396 and 405-408. The 'nets' source is taken whenever unet_data/N_edges.json and picks22_guided/22-N/outlines.json exist, whatever outline step made them.
   - Failing case (measured, batch_i.sh tag i90_asis): the staged ink_bins.py on 90 with the repo's files as they are now (the batch's outline step: 1 block, 3 lines).
     - block line 19 px, lot line 2,432,109, water pipe 404, sewer 0;
     - 5,078,524 of 5,079,178 ink px are on 'block' ground (the margin bug);
     - N_bins.json says ground_from 'nets'.
   - This is exactly what the editor's bins button (edit_server /runbins) would give on 90, and on all 104 unplaced plates, between applying the diff and the outline step being rerun. The implementer left that rerun waiting for Ben's OK on 90.
   - Knock-on: outlines.py:277 then treats those bins as 'sorted with a block ground' and uses their railroad bin instead of running the rule.
   - Fix:
     - In ink_bins, use 'nets' only when the outline step's N_outlines.json (od + N_outlines.json) has a 'version' equal to blocks_noguide.outline_version(). That import is cheap and needs no torch.
     - Otherwise fall back to 'none' and print "run blocks_noguide.py N --outlines-only first".
     - Write the outline version into N_bins.json made_from, and have outlines.py:277 require it.
     - Alternatively, edit_server's /runbins could run the outline step first when it is stale.

2. MEDIUM-HIGH: without its templates, the outline step on uncut sheets runs and exits 0, and adding the templates later never triggers a redo.
   - Where: outlines.py:130-137 (Q5, then carry on) and blocks_noguide.py:57 (VERSION_FILES).
   - staged.diff does not carry templates/*.png (binary).
   - Failing case (measured: a copy without templates in v-code/notpl, run on 90, runs/o90_notpl.out):
     - KeyError 'key', so Q5 is flagged, plus 'Q2 32 block regions';
     - 41 blocks instead of 55; the editor gets 0.636 of the line length;
     - exit 0, so blocks_noguide writes N_edges.json;
     - the version is still 1aecfd64ac3e, identical to the run with templates, so run_plates records it and never redoes the 24 PDF sheets once the templates arrive.
   - Also:
     - outlines.py:133 sets alpha, ma_flags and mask8 before fixed is computed. A failure on lines 134-135 leaves the margin masked but every map-edge side marked paper_edge, while the Q5 text says "not masked".
     - On failure a stale N_mapground.png is left for ink_bins.
     - outline_version() also omits ink_bins.py, whose railroad() and block_ground() run inside the outline step.
     - run_plates.py:60 RULES omits edit_server.py, whose clean() and sheet() make the block lines.
   - Fix:
     - On a 'pdf' sheet, make a missing template or an import error a hard error (non-zero exit). Keep Q5 for map_area running but finding nothing.
     - Add templates/*.png and ink_bins.py to VERSION_FILES, and edit_server.py to RULES.
     - Assign alpha, fixed and mask8 together, only after everything has succeeded.
     - Ship the PNGs with git diff --binary or an explicit copy step.

3. MEDIUM: bench44's 'intact_rings' headline score is wrong for the merged step 4.
   - Where: bench44.py:444-447. ring_state counts a ring as kept unless a side is 'short' or paper_edge, but the merged step 4 also drops 'not on a line' and 'on rail'.
   - Failing case (measured, intact_check.py on impl/bench44_runs):
     - merged_batch: headline 37 intact, actually 6;
     - merged_guided: 48, actually 4.
   - Fix: decide 'kept' with the same rule step4() uses, following the --keep-unlined and --rail-show flags. Holes are also counted as 'outlines'.

4. MEDIUM: options that are not recognised are silently ignored, and the run then writes into the repo.
   - blocks_noguide.py:131-133:
     - `--out=DIR` is not seen. Measured in the fake tree: N_edges.json, outlines.json, N_outlines.*, N_blockmask and N_blocks_ng were written into the data tree and nothing into DIR.
     - A typo such as `--outline-only` would rerun the networks and overwrite the maps.
   - ink_bins.py:516-522: the test options (--no-map, --edges, --outlines, --unsure) without --save write the plate's real N_bins.png and N_bins.json. Measured in the fake tree with --no-map. outlines.py then trusts that ground_from.
   - Fix: use argparse in blocks_noguide and reject unknown '--' options. In ink_bins, refuse to write N_bins.* when a test option is given without --save.

5. LOW-MEDIUM: Q1 is skipped silently under system python.
   - Where: outlines.py:312-318.
   - Measured: staged outlines.py on 5 under cv2 4.13 and 5.0 (runs/o5sys against o5b) gives an identical outlines.json and blockinst. But under system python qa.Q1 is 'not computed' and suspect stays False.
   - Plate 3's only flag is Q1 (59%), so it would be cleared.
   - The docstring's own usage line (outlines.py:4) says `python`.
   - Fix: add a fallback thinning (numpy or cv2), or add 'Q1 not computed' to suspect_why, and change the usage line to the venv.

6. LOW-MEDIUM: an editor race on Ben-edited lines that the guard does not cover.
   - The edges_ben guard keys on the file existing. edit_server keeps /data/N's lines in the open page and /save keys edits to them (repo edit_server.py:134-139 and 177-182).
   - If the block step rewrites N_edges.json while Ben has 90 open but has not saved yet, his first save is keyed to the old lines.
   - Fix: /data returns a hash of N_edges.json, and /save refuses when it has changed. In the meantime, rewrite 90 before he opens it and have him reload.

7. LOW: the outline step can rerun on every run.
   - Where: run_plates.py:157 together with blocks_noguide.py:117-119.
   - A plate with edges_ben.json but no N_edges.json (lines drawn on a plate opened only from its bins) gets N_edges.new.json, and plan() sees N_edges.json still missing. Result: 'outline' on every run.
   - Fix: also accept edges_ben.json or N_edges.new.json there.

8. LOW: the bench44 decided-ground cache.
   - Where: bench44.py:147-166.
   - The cache is not keyed by the street map's sha or by WMAX, so it goes stale if 44's map is saved again.
   - It is written without tmp + replace, while `--grids --jobs 3` children reach it at about the same time.
   - The default --runs is data/sanborn/bench44_runs/, inside the repo and not gitignored. The implementer's stray decided_half.png came from this.
   - Fix: key the cache by sha16(streetmap)+WMAX, write tmp then os.replace, and default --runs outside data/sanborn.

9. LOW: Windows paths in --outline-args lose their backslashes.
   - Where: bench44.py:336. shlex.split in POSIX mode turns `C:\Users\..\44_bins.png` into `C:Users..44_bins.png`.
   - outlines.py then finds no bins and runs the rule without saying why.
   - Fix: shlex.split(s, posix=False), or document forward slashes.

10. LOW: the scale lookup is case-sensitive but the disk is not.
    - Where: outlines.py:315.
    - `outlines.py 1a ...` finds every file on Windows but gives a false Q3 'scale not recorded'. '1A' and '93B' (400 ft) are found correctly, and run_plates upper-cases plate ids.
    - Fix: .get(N.upper()).

CHECKED AND OK (all measured; the script that made each number is named)
- The diff applies (cmp.py, folder fresh/):
  - git apply to fresh copies of the five repo files, in an isolated repo with core.autocrlf off, gives every staged non-PNG file byte for byte.
  - In the real repo, tools/sanborn is attr -text, so the system autocrlf=true does not change line endings.
  - The 9 templates equal visual-pdf/templates. Maps grid1-5 equal off1-5_tta1; grid0 equals inference/maps/batch, which equals unet_data/44_*_ng1.
- Tracing order: holes first, then blocks by nesting depth. The kinds[] index stays in step with the sides; markers are 2..n and instances 1..K. The mix split never triggers, because watershed labels are never 4-adjacent.
- Duplicate lines: dups.py on 90, 5 and the 44 runs found 0 lines on top of each other in what the editor shows (clean() merges them).
- Holes: holes_check.py found hole polygons lying 0-26% on watershed block ground.
- Readers of outlines.json:
  - make_labels.py:57 and crop.py:25 use only 'on print'. Since the green gate, 'on print only' and 'on rail' sides drop out of their hints; this matters only for placed plates, and the placed-plate guard holds.
  - step 4 drops paper_edge, 'not on a line' and 'on rail', and keeps holes and bridges.
  - The bench's PQ raster paints each block over its holes, so PQ ignores holes.
  - ink_bins.block_ground cuts the holes out.
  - edit_server, street_map and fixcrops see only N_edges.json (green and orange).
- Guards (fake tree):
  - outlines.py on a placed plate exits 1 with the file unchanged; --force passes the guard.
  - The edges_ben guard writes 8B_edges.new.json and leaves the N_edges.json hash unchanged.
- blocks_noguide imports with torch, unet and edgenet blocked. outline_version is 1aecfd64ac3e under both pythons.
- street_map.py: in sm44_old and sm44_new, the repo script and the staged script give a streetmap/22-44.json byte-identical to each other and to the repo file (sha256 eb6d691659dc8f0e). The pictures are identical too.
- ink_bins:
  - Repo and staged code on 44 (map) and 43 (label) give pixel-identical bins (runs/reg).
  - The fallback on 90 from the staged block step (batch_b.sh, then batch_i.sh tag i90) gives block line 650,637, lot line 1,081,385, water pipe 460,706, sewer 84,823, not sorted 163,297, railroad 202,954.
  - On 5: block line 1,151,581, lot line 631,003, water pipe 976,454, sewer 189,171, not sorted 0, railroad 29,381.
  - Both match the implementer's table exactly.
  - Fake 8B: Ben's edits are applied (the deleted line leaves bin 1; the added line gives 408 px). With no outlines.json or no N_edges.json it falls back cleanly to ground_from 'none'.
- Plate 90's block step: 55 blocks, 1 hole, 456 step-4 lines, 438 lines shown in the editor, 19 rail sides, not suspect. Block-line ink near the paper's edge: 3 px (edge_bins.py).
- The railroad rule is pixel-identical under cv2 4.13 and 5.0: 5 gives 29,381 px and 3 gives 1,645,496 px (rr_cv.py).
- run_plates plan() against the real run_plates.json (dryrun.py):
  - 104 plates get 'outline + bins' and 5 get 'bins'. The networks are never planned (netid matches).
  - A second pass plans nothing, so there is no loop.
  - The networks rerun only if a .pt file's mtime changes (unchanged logic) or with --redo, which also rewrites N_edges.json on every plate without edges_ben.
- Memory (peak commit, shim atexit):
  - outline step: 90 6.72 GB, 48 6.77, 3 6.06, 5 5.79;
  - the old step on 90 (bench44/outlines_copy.py, run alone): 6.8 GB, so no regression;
  - ink_bins: 90 4.95 GB, 5 4.46 GB;
  - the machine has 63 GB.
- Timing: plate 5's outline step took 18.3 s alone with known bins. The railroad rule alone took 13.5 s. Other timings were taken with runs in parallel and are not reliable.

Scripts and outputs in v-code/: batch_o.sh, batch_b.sh, batch_i.sh, dryrun.py, intact_check.py, dups.py, holes_check.py, rr_cv.py, edge_bins.py, cmp.py; folders runs/, fake/, notpl/, sm44_old/, sm44_new/, fresh/; peak memory in peak.jsonl and peak_old.jsonl.
