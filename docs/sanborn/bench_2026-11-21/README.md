# Sanborn 1922 batch: how it did, and what to change next (21 November 2026)

Ben, 21 November 2026, after the batch (`run_plates.py`, 109 plates) finished:
- "The 44 plate is the ground-truth."
- "What steps do you think we should take next to improve the code now that the batch is finished? It would also be
  good for you to look at how the batch did, in order to improve on that, since that's the benchmark."

How the work was done:
- 14 agents.
- Five measured: a plate-44 benchmark, a census of all 109 plates, two visual audits, and rail.
- Four tried fixes against that benchmark, each re-run by a second agent: all four confirmed. A critic then looked for
  gaps.
- Nothing in `tools/` or the batch outputs was changed, and nothing was trained. The proposed changes are unified
  diffs, not applied.
- I re-ran the two headline plate-44 numbers myself, and got PQ 0.4309 for the batch and 0.5430 for the outline
  change.

Where things are:
- Full results: `findings_full.md`.
- Scripts, diffs and key tables: this folder, under the agents' folder names.
- Everything, pictures included (3.9 GB): `data/sanborn/bench_2026-11-21/` (not in git).

## The benchmark: plate 44 (100 ft to the inch)

`bench44/bench44.py` runs the batch's own chain on plate 44: area_ng1 and lines_ng1, the outline step, step 4, and
the editor's clean() and sheet(). It scores what the line editor would show against `streetmap/22-44.json`. A
faithfulness check reproduces the stored guided outlines byte for byte. Each score is also given for two folds of the
plate (A and B).

| | batch | guided nets (reference) |
|---|---|---|
| Blocks right (PQ, IoU > 0.5) | 0.431: 23 of 55, 13 false; all 32 misses are merges | 0.592: 35 of 55 |
| Ben's interior lines found (by length) | 53% | 41% |
| Shown lines that are right | 75% (green 78%, orange 7%) | 73% |
| Ben's blocks closed by the shown lines | 0 of 55 | 0 |
| To delete / to draw | 184 lines (32.5k px) / 164 lines (80.1k px) | 28.1k / 113.0k px |
| The batch's own "on a printed line" | 96% | 87% |

Where the loss is:
- With Ben's blocks as the area map and the batch's line map, PQ is 0.94: all 55 blocks found, no merges.
- With the batch's area map and Ben's lines as the line map, PQ is 0.56.
- So the merges come from the **area network**. It calls narrow streets and alleys block, and then no street seed
  lies between the two blocks.
- The outline step's own losses are smaller, but it is why nothing closes: step 4 drops 1,619 short pieces, so no
  outline stays a ring.

How precise these numbers are:
- One plate is a wide yardstick. Resampling Ben's blocks puts the batch's PQ at 0.32-0.53 (95%).
- Choosing another tile grid moves PQ by sd 0.015, and by about 0.03 within a fold.
- Compare changes as paired gains over the 6 tile grids (`inference/maps`), not as single numbers.

## The whole batch (census of 109 plates; no truth outside 44)

- **Scale:** 36 plates are at 100 ft to the inch, 63 at 200 and 10 at 400. The scale was read from the printed
  notes, and 23 placements agree within 2%.
  - **Correction to the 21 Nov review:** 43 and 44 are 100-ft plates. The training set is 43 at 100 ft plus 45, 80
    and 82A at 200 ft.
  - The table is `census/scale/scale_table.json`. Insets at another scale are on 46, 48, 78, 92 and 94.
- **Bad or poor plates, by eye:** 27 of them, which is 25% of the plates and 56% of the ground area.
  - 22 of the 32 uncut PDF sheets, and all 10 plates at 400 ft.
  - Only 3 small pieces among the cut 100-ft plates (8B, 15B, 55B).
  - The batch recorded all 109 as done, with no errors.
- **On the 200-ft PDF sheets the networks mostly worked; the outline step threw it away.** On sheet 90 they traced
  nearly every street, and the editor got 3 lines. 15 sheets keep less than 25% of what the line network drew.
- **400-ft sheets:** the area network misses most streets.
- **Cut 200-ft plates** look "ok" in the census, but on 60B about 27 of about 30 mid-block alleys are missed. Neither
  network sees them: the line network marks 1.4% of one such alley and the area network calls 90% of it block.
- **Other failures:**
  - 432 margin lines on the PDF sheets;
  - 38 rail tracks inside the printed KEY on 32 plates;
  - lines along rail yards (on 44: 32 lines, none right; 24% of the editor lines on 1B);
  - the Ohio River and wharves inside one block (1B, 2, 3, 26A, 52);
  - open land called block on the PDF sheets.
- **Rail** (rules re-run alone, scored against Ben's 28 tracks on 44):
  - Railroad: 98.4% of his length found. Precision is 99.5% when the plate is run as the batch ran it, and 97.9% when
    run as an unplaced plate (3 false tracks).
  - Streetcar: 80% found, at 100% precision.
  - These are in-sample numbers, because the rules were tuned on 44.
  - Batch-wide, by eye: railroad about 85% right (misses are hook-marked lot lines and text), streetcar about 96%.

## Next steps, in order

### 1. One merged outline step (code only, CPU, no retraining)

Two measured changes, each confirmed by a second agent. As diffs they conflict, so they must be merged by hand and
measured again.

**From `outline-quality`:**
- **One watershed marker per block.** PQ 0.431 → 0.543 on the batch's tile grid, or +0.07 ± 0.03 averaged over 6
  grids. Most of the gain is in fold B.
- **Green only where the line network agrees.** Green precision rises from 78% to 84%.
- **Closed rings:** collinear sides joined and corners extended.
- **Results on 44** (option 1, also dropping sides on no line):
  - lines found 53% → 61%, shown lines right 75% → 76%;
  - 6 of Ben's blocks close, against 0;
  - draw length 80k → 70k px; delete length about the same.
- **Ben's choice:** option 2 keeps those sides. Then 18 blocks close, but only 65% of shown lines are right, and the
  delete length doubles.

**From `outline-nesting`:**
- **Nested blocks and street holes:** RETR_TREE, with a hole gate.
- **Map mask on the PDF sheets:** the KEY, title, scale notes and bars, compass roses and inset frames are masked by
  `visual-pdf/map_area.py`. It is right on 28 of 32 sheets; it fails on 23, 27, 46 and 91.
- **A "suspect" flag in the batch record:** 25 → 14 plates.
- **Results:**
  - 24 PDF sheets at 200 ft: blocks 425 → 815; sheets with 5 or fewer blocks 11 → 0; margin lines 365 → 77.
  - Plate 44 is unchanged, apart from +1.5 points of line recall.
  - The 400-ft sheets still fail.

**To add while merging:**
- Demote sides that lie on the rail bins (cheap: `N_bins.png` already exists).
- Keep street sides along the map edge of the PDF sheets. Today's mask drops 201 of them (64k px).
- Freeze the training targets first: `make_labels.py` reads `outlines.json`, so changing the outline step changes the
  next retraining.

Then rerun the outline step alone over the batch's saved maps. This overwrites N_edges.json and the outlines, so it
needs Ben's OK.

### 2. Rail rules (`rail-rules/diffs/rail_rules.diff`)

The diff adds three rules:
- a KEY mask;
- dropping isolated railroad groups under 600 px;
- a streetcar join reach of 350 px.

Results:
- **Plate 44, run as unplaced:** railroad precision 97.9% → 99.5% at the same recall, with no false tracks left.
  Streetcar found 83% → 89%, with precision 100% → 98%.
- **Plate 1A:** its 5 false railroad tracks are gone.
- **Batch:** railroad tracks 4,063 → 3,105. About 97% of those dropped looked false by eye.

**Ben's call:** should a streetcar track carry on under a printed street name? All of the precision loss is there.

### 3. Ben: the second truth plate, and conventions

- Save the 44 spur. `rail_ben.json` still has 26 tracks.
- **Check plate 90 completely, blocks and rail.** It is a 200-ft PDF sheet: the batch gave it 1 block, and the fixes
  give 45.
  - It is the first test of the map mask, nesting, the 200-ft scale and the rail rules out of sample.
  - It is about the size of 44.
  - Keep 44 and 90 out of training.
- **Conventions to decide:**
  - Are 200-ft mid-block alleys block sides?
  - How should open land, the river and rail ground be treated on PDF sheets?
  - Should streetcar track run under printed names?
  - What about rail drawn without ticks (83B, 95)?

### 4. Retraining (Ben runs it), in this order

1. Make training reproducible:
   - seed torch;
   - keep the best weights, or use EMA;
   - freeze the targets;
   - stop pasting 255 squares into the blank guide.
   Then **train twice** with two seeds to measure how much two runs differ. That spread is the bar every later change
   must clear.
2. Pen-width and scale augmentation, with small warps. The networks are brittle on 44:
   - every line 2 px thicker: PQ 0.03;
   - 2 px thinner: 0.17;
   - resized to the 200-ft size: 0.12.
3. Relabel the 1922 alleys and streets that today's parcels call block on the training plates (Ben's time). Then add
   a skeleton-recall loss. This is the only route to the missed 200-ft alleys.
4. Out-of-fold area maps for the line network, made after the area recipe is final.
5. Hue jitter, last.

### Measured and not recommended

- Resizing 100-ft plates to the 200-ft size: PQ 0.43 → 0.12.
- Plain ×2 enlargement of 400-ft sheets: wrong length triples.
  - For 400-ft sheets, "up2thin" (×2, then pens thinned back) looked about 90% right by eye, against 77%. Try it only
    after Ben checks one 400-ft district.
- Hann tile blending, and test-time augmentation on the line network.
- Area-net test-time augmentation (8 flips and turns) gains +0.04 PQ on its own, but nothing on top of the markers.
  Leave it optional.
