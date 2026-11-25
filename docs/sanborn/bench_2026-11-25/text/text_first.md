# Text-first stage: the plan

25 Nov 2026, for Ben. This is a plan only. Nothing in the repo was changed, nothing was downloaded, nothing was trained.

- **(m)** means measured. The script that made the number is named. Paths are under `data/sanborn/bench_2026-11-25/text/`.
- **(e)** means an estimate.

## In short

- **Text goes first.** Every later stage gets a text mask and leaves that ink alone: ink sorting, rail, pipe and sewer rules, the line and block nets, and the outline step.
- **The mask can be built now with no download.** The rule-based finder already beats today's bin 8 (m):
  - F1 0.907 against 0.850 on the 6 hand-checked crops;
  - it calls 0.2% of your line ink text, where bin 8 calls 6.7%;
  - with it, plate 5's false railroad tracks go from 23 to 3.
- **Its weak spot is big lettering** (m). Recall on street names is 0.81 (bin 8: 0.985) and on block numbers 0.64 (bin 8: 0.85). That is the first fix.
- **Reading is the harder half** (m):
  - today's reader gets 32% of held-out numbers on plate 44 exactly right;
  - for numbers touching a line it gets 8%;
  - the checks by code catch 99% of simulated one-digit misreads of house numbers, but they need a reader that is right most of the time first.
- **Effort** (e). No download is needed. Your labelling is about 1.5-2 hours. Claude's work is about 8.5-10 days in 9 steps, each ending at a gate where you see the numbers.

## 1. Order in the pipeline

```
scan -> ink (L < 140)
  -> TEXT STAGE
     a. set aside straight line ink (a straight 61 px line fits it); it stays line ink, never text
     b. find the characters in the rest: character or not a character   -> TEXT MASK handed on here
     c. group the characters into words, with direction (level, turned, along a curve)
     d. read the words
     e. check the readings by code                                      -> WORD TABLE handed on here
  -> ink sorting: bins 1-7 on the ink that is left; bin 8 = the text mask
  -> rail rules: text cannot be ties or rails
  -> pipe and sewer rules: a label names the line beside it
  -> line and block nets: unchanged for now; text is used to drop false lines (next round: text as hard negatives)
  -> outline step: blocks; later, street names and house numbers give each block face its name and side
```

- Step (a) comes first inside the text stage because it is the only way to unhook a number from the line it touches. A block line through a row of house numbers stays a line.
- The mask is handed on after (b). It does not wait for the reading. A word that cannot be read is still text.

## 2. What can be built now, with no download

It uses only what is installed: the system python with cv2, numpy, scipy and scikit-image, and the fonts in C:/Windows/Fonts. Each part exists as a prototype in the bench folder.

| part | prototype | what it does |
|---|---|---|
| a + b. character finder | finder/scripts/finder.py | Rules only:<br>- peels off straight lines;<br>- sorts the pieces by shape: glyph, stroke, dot, blob, dash;<br>- keeps a figure 1 or a ditto mark when it is beside a glyph.<br>Takes 7-76 s per plate (m, 9 plates). |
| b. character or not | shapes/scripts/classify.py | A nearest-match reader on glyphs labelled by cluster, with a junk class. |
| c. words and direction | words/scripts/run_words.py | Groups glyphs along a fitted line or curve, finds which way up they are, and straightens each word into a strip. |
| d. reading | shapes/scripts/read.py | Reads each glyph against labelled glyphs and cuts touching figures apart. The model was fitted on Claude's cluster labels from plates 1A, 5, 3, 90 and 94, never 44. |
| e. checks | checks/code/*.py | House numbers, lot widths, pipe labels, street names. |

### What it does today (measured)

**Finding text.** Scored by verify/scripts/rescore_finder.py against the 6 truth crops: T1-T3 on 44, T4 on 1A, T6-T7 on 5.

| | precision | recall | F1 |
|---|---|---|---|
| bin 8 today | 0.854 | 0.847 | 0.850 |
| finder, all 6 crops | 0.949 | 0.868 | 0.907 |
| finder, the 3 crops it was not tuned on (T4, T6, T7) | 0.944 | 0.837 | 0.887 (bin 8: 0.843) |

- Non-text ink called text: finder 3.6%, bin 8 10.9% (rescore_finder.py).
- Your line ink on 44 called text (verify masks_vs_ben44.py, finder measure.py):
  - finder 0.21%;
  - bin 8 6.7% when ink sorting uses your street map, 16.3% without it.
- Your lines are cut at 0.35% of points by the finder and at 8.1% by bin 8.
- Recall by kind, finder against bin 8:

  | kind | finder | bin 8 |
  |---|---|---|
  | lot numbers | 0.93 | 0.76 |
  | lot dimensions | 0.91 | 0.79 |
  | story heights | 0.94 | 0.71 |
  | ditto marks | 0.75 | 0.47 |
  | street names | 0.81 | 0.985 |
  | house numbers | 0.88 | 0.965 |
  | block numbers | 0.64 | 0.85 |

  The finder is better on the first four and worse on the last three. Big letters with straight stems are taken as line ink.
- Plates outside the truth were looked at by eye only (verify unseen_windows.py):
  - the 100 and 200 ft plates look like the truth crops;
  - the 400 ft plate 47 is poor: rotated lot numbers are missed and lot-line pieces are called text.

**Effect on the later stages.** These use the finder's mask, which uses no truth (verify rail_recheck.py and lines_recheck.py).

| what | before → with the mask |
|---|---|
| plate 5 false railroad tracks | 23 → 3. The 3 left are lot lines with hook marks, not text. |
| plate 44 railroad recall | 0.982 → 0.969 (one track goes from found to partial), 0 false tracks |
| plate 44 streetcar | 0.797 → 0.817 |
| plate 5 streetcar | 0.776 → 0.805, with 1 false track added |
| false editor lines, baseline nets | 99.5 → 91.2 |
| false editor lines, V2S1 pair | 147.8 → 117.2 |

- PQ moves by less than 0.008.
- Masks built with your truth showed bigger gains on 44, but they do not carry over to other plates. Built without your truth, they drop 44's railroad recall to 0.55. **The mask must never use truth.**

**Grouping into words** (words/scripts/measure.py and summarize.py).
- With the finder's mask, words were grouped exactly right on 60% (T6) and 56% (T7) of the words. These are the 2 crops not seen during development.
- Most errors are words split in two: 18 splits on T6 and 60 on T7.
- The direction is right for 75-85% of words with 2 or more glyphs.
- On 44 it used your street map as context. That has to be replaced by context made from the scan alone.

**Reading.** Tested on 271 numbers on 44 that the inventory agent read by eye; the model never saw plate 44 (verify read_truth44.py).

| numbers | exactly right |
|---|---|
| all | 86 of 271 (32%) |
| story heights | 52% |
| lot numbers | 39% |
| house numbers | 19% |
| lot dimensions | 16% |
| free of lines | 38% |
| touching a line | 5 of 60 (8%) |

- Single figures are 50% right. Of the figures it does read, 71% are right.
- Fitted with 44's own glyphs, the same reader gets 34%. So the glyph classifier is not the limit. What limits it is cutting glyphs off lines, turning words upright, and splitting touching figures.
- On clean, upright digits the classifier does well:
  - 0.91 from synthetic font glyphs alone, on 113 hand-read digits (research font_test.py);
  - 0.95-0.98 agreement with the cluster labels with 50 labelled glyphs per character (shapes learning_curve.py).
- Letters:
  - the reader knows only 10 capitals: A C E L M N P R T W;
  - the font reader got 15 of 16 letters of KNOWLTON and BLUE ROCK (shapes eval_faces.py), which is too few to rate it.

### Targets for the gates (proposed)

- **Mask:**
  - F1 0.92 or more on new held-out crops;
  - recall of street names and block numbers 0.95 or more;
  - 0.5% or less of your line ink called text.
- **Reading before checks:** 70% of numbers exactly right (now 32%).
- **After checks:**
  - 60% or more of all numbers accepted, with 2% or fewer of the accepted ones wrong;
  - street names matched to the list on 90% of named streets.

## 3. Downloads

None is needed for the build.

**Recommendation:** approve nothing now. Decide at the gate after step 2 (finding) and step 6 (reading). If you want one independent check of the mask now, CRAFT is the one.

| | what | from | size | licence | what it adds over the no-download route | advice |
|---|---|---|---|---|---|---|
| 1 | CRAFT text detector weights, craft_mlt_25k.pth | clovaai/CRAFT-pytorch README on GitHub (links to Google Drive) | about 79 MiB / 83 MB, to check | code MIT; weights to confirm | A per-character heat map that copes with spaced, curved and rotated words. It is a second opinion where the finder is weak: street names, block numbers, 400 ft plates. Its layers run on the AMD GPU (m). Not tried on Sanborn. | yes, if step 2 misses its street-name target |
| 2 | PP-OCRv3 DB text detector, ONNX: text_detection_en_ppocrv3_2023may.onnx | huggingface.co/opencv/opencv_zoo | 2.42 MB | Apache-2.0 | Word boxes through the cv2 already installed, with no new package. It was trained on photos and documents and may miss 1-3 px strokes (e). | only as a cheap cross-check |
| 3 | PARSeq word reader | github.com/baudm/parseq releases | about 95 MB, plus the pip packages timm and pytorch-lightning | code Apache-2.0; weights licence not stated | Reads whole words. It would need fine-tuning on synthetic Sanborn words, which is training and needs your OK. Runs on DirectML (m). | only if reading stays under about 70% after step 6 |
| 4 | Tesseract 5 | UB Mannheim Windows installer | about 50 MB, plus 4-15 MB of language data | Apache-2.0 | A CPU line reader with character whitelists. It needs level lines and will be weak on italic hand lettering without retraining (e). | no |
| 5 | mapKurator, Spotter-v2, PALETTE, the MapText winners, TextFuseNet, TrOCR, PaddlePaddle, SynthMap+ (38.8 GB) | | large | Spotter-v2 is non-commercial | Built for Linux and CUDA; never saw Sanborn lettering. | no |

The opencv_zoo CRNN reader (33.8 MB, Apache-2.0) reads only 0-9 and a-z, so it would lose ' " . and -. Not recommended.

## 4. What you would label

It is all done on picture sheets: Claude proposes, you confirm or correct. The times are estimates.

| job | what | time |
|---|---|---|
| conventions | short answers to the questions in section 9 | 10 min |
| truth fixes | about 10 spots the checker found wrong on T1, T4 and T7 (verify/pics/truth_*.jpg, zoom_*.jpg) | 10 min |
| digit clusters | The round-2 sheets: shapes/montage2/, 400 rows of 26 glyphs, recorded in shapes/labels/ben_label_sheet.json.<br>For each row, write the character, 'junk', 'pair', or leave it blank if the row is mixed.<br>Claude has proposed labels for 261 of the 850 rows. | 30-45 min |
| letter and mark clusters | A new sheet, made after the words are turned upright, of about 150 rows:<br>- capitals;<br>- the marks ' " . - &;<br>- junk: hooks, ticks, hydrant dots, dashes. | 20-30 min |
| strings | Either spot-check Claude's reading of 2 new held-out crops (about 300 words), or type the house numbers of 6 block faces on 2 new plates. | 20-30 min |
| total | | about 1.5-2 h |

- **Why this is enough.** Agreement with the cluster labels rises with the number of labelled glyphs per character, and is flat after 100 (shapes learning_curve.py):

  | glyphs per character | agreement |
  |---|---|
  | 3 | 0.80 |
  | 10 | 0.90 |
  | 20 | 0.94 |
  | 50 | 0.95-0.98 |
- **The 'junk' rows matter as much as the digits.** They are the 'not a character' class the mask needs.
- **You do not need to type street names.** The repo already holds them:
  - streetmap/22-44.json;
  - picks22_reads on 8 plates, each read twice;
  - a list of 4,775 names built from the repo (checks/data/name_list.json).

## 5. Checks by code

There are two kinds of check.

**Checks on shape, for the mask.** They run before the hand-off and are small new code.
- A row of evenly spaced, equal strokes along a line is a dashed line, not 1s. The finder already does this.
- A lone thin stroke 12-45 px long inside a building, or beside other figures, is a figure 1 (a story height). Alone on a lot line, it is a dash.
- A group that reads as junk whichever way round it is turned becomes 'not sure'.
- No text pixel may sit on line ink (guarantee 1 in section 6).

**Checks on the reading, for the word table.** The prototypes are in checks/code/. They were tested on numbers read by eye, with misreads simulated by swapping one digit for a look-alike.

**House numbers** (hn_checks.py; 168 labels on 44, 45 and 5)
- What is checked:
  - the format, such as 1424-22-20;
  - odd and even numbers on opposite sides;
  - numbers rising or falling along the side;
  - a straight-line fit of number against feet along the street;
  - one hundred per block;
  - agreement with the opposite side;
  - numbers carrying on across cross streets and onto the adjoining plate.
- Result:
  - 166 of the 168 true labels pass; the 2 that fail (Lingo 1353 and 1351) really are printed out of sequence;
  - 1,318 of 1,331 simulated one-digit misreads are caught (99.0%) and 1,275 are corrected (95.8%).

**Lot widths** (frontage_check.py; 3 block faces)
- What is checked: the printed lot widths add up to the face length measured on the scan.
- Result:
  - the true widths fit on all 3 faces: 2 close within 1.9-2.5 ft, and on the third one lot width is unprinted;
  - misreads that change a width by 5 ft or more: 59 of 94 flagged (63%);
  - smaller misreads: 13 of 51 flagged.

**Pipe and sewer labels** (pipe_check.py; 16 labels)
- What is checked:
  - the format 6" W. PIPE, 6" W.P. or 12" SEWER, with a usual diameter;
  - the line beside the label is of the label's kind;
  - one diameter along a street.
- Result:

  | test | caught |
  |---|---|
  | kind swapped | 13 of 16 |
  | label moved across the street | 31 of 32 |
  | diameter misread | 39 of 52 |

- False alarms: 3 of the 16 true labels.

**Street names** (name_checks.py)
- What is checked: the read name matches the name list, and the same name appears on both adjoining plates.
- Result:
  - the list covers 72.9% of the read names exactly and another 17.7% with a different suffix or an old name; 7.0% are missing;
  - a read with one wrong letter finds the right name 98.8% of the time, and one with a dropped letter 88.6%;
  - crossings read on two adjoining plates agree 91.5% (193 of 211).

**All checks together** (confidence.py)
- Each reading is accepted, flagged or rejected.
- With 5%, 15% and 30% random misreads, the share of accepted readings that are wrong is 0.30%, 0.39% and 1.08%.

**Caveat from the verify agent.** These misreads were simulated and random. The real reader today misreads about 68% of numbers, and in patterns (rotated or touching numbers). The checks will be refitted on the real reader's mistakes in step 7.

**Still to build:**
- block numbers unique on a plate and the same on the adjoining plate;
- lot numbers in sequence;
- story heights 1-6 inside a building;
- dimension formats: 25', 126.84', bearings such as N 22° 30' W;
- adjoining sheet numbers that match the sheet list.

A failed check flags a reading. It never takes the word out of the mask.

## 6. The text mask hand-off

**Two files per plate.**

N_text.png has one code per pixel:

| code | meaning |
|---|---|
| 0 | paper |
| 1 | line ink, never text |
| 2 | text, sure |
| 3 | text by context: figure 1s, ditto marks, dots taken in by a glyph |
| 4 | shared ink, where a glyph touches a line; both own it |
| 5 | other ink, not text: dashes, ticks, hooks, hydrant dots, specks |

N_words.json holds every word with its outline, direction, kind, reading, check results and confidence. Pipe and sewer labels are linked to the line they name, and street names to their street.

**What the mask must guarantee around numbers touching lines**
1. **Line ink is never masked.**
   - A pixel that a straight 61 px line fits stays line ink, even where a number touches or crosses it.
   - Limit: at most 0.5% of your checked line ink called text, and no checked line broken.
   - Now (m, finder measure.py): 0.21% on 44 and 0.13% on 1A, with lines cut at 0.35% and 0.22% of points.
2. **The number is cut off at the line's edge.**
   - The line keeps its full width, and the glyph keeps its strokes up to it.
   - The ink they share (within 2 px) is code 4: ink sorting gives it to the line, training does not score it, and the reader adds it back to read the glyph.
3. **No truth is used.** The mask is made from the scan alone, without your street map, rail or lines, so it behaves the same on plates you have not checked.
4. **Unsure ink is marked, not hidden.** Code 3 lets each stage choose:
   - ink sorting removes codes 2 and 3;
   - the rail rules also keep 3 px around them clear;
   - training weights code 3 lower than code 2.
5. **Every version is scored before use.** It is checked on the truth crops (F1, recall by kind, your line ink) and on rail and lines before any stage takes it.

**How each stage uses it**
- Ink sorting sorts only the ink that is not code 2 or 3. Bin 8 becomes the mask.
- In the rail rules, masked ink cannot be ties or rails.
- In the pipe and sewer rules, a label gives its line the kind and the diameter.
- The line and block nets are unchanged for now. An editor line that runs mostly over text, and not over line ink, is dropped.
- In the outline step, later, street names and house numbers name each block face and its side.

These are repo changes. They will be tried on copies in the bench folder first, and go into the repo only when you say so.

## 7. The next training round: numbers as hard negatives

This happens when you say go, not before. It follows the diagnosis (docs/sanborn/bench_2026-11-25/diag/findings_full.md, labels section).

**Today:**
- numbers are taught as negatives at the ordinary ink weight, about 3;
- 67-100% of the 2-9 px band beside a line is not scored;
- in V2, 39% of the numbers near lines were not scored at all.

**Proposal:**
- The line net learns text ink (codes 2 and 3) as negative everywhere on the paper, including the band beside the lines: weight 10 within 40 px of a line, 6 beyond.
- Shared ink (code 4) and ink within 2 px of a true line are not scored, so a block side through a row of numbers stays a side.
- The same no-truth mask is used on every training plate, so training and use see the same thing.

**Static estimate, not a forecast of PQ.** The share of today's false line response that would carry a negative weight:

| plate | today | with the proposal |
|---|---|---|
| 1A, held-out region | 50-75% | 80-89% |
| 5 | 0-64% | 78% |
| 44 | 28-62% | 44-70% |

**Watch at every evaluation:**
- the line net's mean P on numbers within 40 px of a street: baseline 0.049, V2S1 0.079;
- how many editor false lines run mostly through numbers: baseline 25, the new pairs 40-53.

**Optional, with your OK:** extra negatives made by drawing number rows in the 5 best fonts and pasting them 5-40 px beside real lines.

## 8. Steps in order

Claude days are estimates. Each step ends at a gate where you see the numbers before the next step starts.

| # | step | Claude | you | gate |
|---|---|---|---|---|
| 1 | Bench: fix the truth errors found, and add 2 held-out truth crops on plates never tuned on (for example 90 at 100 ft and 47 at 400 ft). | 0.5 day | 10 min | |
| 2 | Finder v2: stop big lettering (street names, block numbers) becoming line ink, and fix the 400 ft plates. | 1 day | | the mask targets in section 2 |
| 3 | Character-or-not classifier from your checked clusters, synthetic font glyphs and a junk class. Fitted on the CPU in seconds. | 1 day | 50-75 min (the sheets) | F1 and recall by kind on the held-out crops |
| 4 | Hand-off v1: run ink sorting, the rail rules and the line bench with the mask on 44, 5 and 1A. This uses copies, not the repo. | 1 day | | rail and lines no worse anywhere; then you decide on the repo change |
| 5 | Words: fix split words, and use context from the scan instead of your street map. | 1 day | | 75% of words grouped exactly on the held-out crops |
| 6 | Reading:<br>- turn words upright;<br>- cut them off lines and add back the shared ink;<br>- split touching figures;<br>- read letters from fonts plus the name list. | 2-3 days | 20-30 min (strings) | 70% of numbers right before the checks |
| 7 | Checks: wire them to the reader, refit them on its real mistakes, and add the block, lot-number, story and dimension checks. | 1-1.5 days | | 2% or fewer wrong among the accepted |
| 8 | All 109 plates: about 2-3 h of machine time (e), with a review sheet per plate. | 0.5 day | spot-check | only with your sign-off |
| 9 | Training labels with numbers as hard negatives (section 7). | 0.5 day | | training only when you say go |
| | total | about 8.5-10 days | about 1.5-2 h | |

Steps 1-4 deliver the mask and its gains without any reading. Steps 5-7 deliver the readings.

## 9. Decisions for you

1. **Which marks count as text?** Candidates: hydrant circles, the 'O' manhole marks, ditto marks, story heights inside buildings, hook marks.
   - Proposal: ditto marks and story heights are text; hydrants, manholes and hooks are not (code 5).
2. **Pipe and sewer labels.** Should they be masked as text and linked to the line they name? Proposal: yes.
3. **A block side running through a row of house numbers.** Is it still a side? This is round 2's question 3, and it sets the 2 px protection. Proposal: yes.
4. **House numbers in 1922 Cincinnati.** Are odd and even always on opposite sides, numbered by hundred-blocks, stepping by 2, with ranges like 1424-22-20?
   - The checks assume so, and 166 of 168 hand reads fit.
5. **Downloads.** Proposal: none now; reconsider CRAFT after step 2.
6. **Go-ahead** for steps 1-4.

## Where the numbers come from

All are under `data/sanborn/bench_2026-11-25/text/` unless the path says otherwise.

**Finding**
- finder/scripts/finder.py, finder/scripts/measure.py
- verify/scripts/rescore_finder.py, masks_vs_ben44.py, unseen_windows.py
- inventory/scripts/bin8_eval.py

**Effect**
- verify/scripts/rail_recheck.py, bench_finder_mask.py, lines_recheck.py
- effect/code/rail_summary.py

**Words**
- words/scripts/run_words.py, measure.py, summarize.py (out/summary_final.json)

**Reading**
- shapes/scripts/read.py, eval_faces.py, learning_curve.py
- verify/scripts/read_truth44.py
- research/scripts/font_test.py

**Checks**
- checks/code/hn_checks.py, frontage_check.py, pipe_check.py, name_checks.py, confidence.py, build_namelist.py

**Training**
- docs/sanborn/bench_2026-11-25/diag/findings_full.md
- the scripts in data/sanborn/bench_2026-11-25/diag/ben-labels/scripts/

**Downloads:** research/out/options_ranked.json, and the sources listed in the research report.
