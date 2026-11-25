# Text truth: 6 hand-checked crops (25 Nov 2026)

Made for scoring a text-first stage. These are data notes for the scorers. Everything was read by eye and checked crop by crop.

## The crops (crops.json)

| crop | plate | window x0,y0-x1,y1 (full px) | words | of them runs / unsure / partial | text px | don't care px |
|---|---|---|---|---|---|---|
| T1 | 44 | 1500,1500-3000,2500 | 240 | 0 / 24 / 24 | 114,134 | 2,227 |
| T2 | 44 | 2700,2500-4200,3500 | 143 | 0 / 16 / 16 | 59,211 | 1,953 |
| T3 | 44 | 9000,2400-10500,3400 | 70 | 0 / 4 / 6 | 53,037 | 2,038 |
| T4 | 1A | 2000,950-3500,1950 | 184 | 4 / 15 / 11 | 94,869 | 5,556 |
| T6 | 5 | 3900,1550-5400,2550 | 100 | 4 / 7 / 13 | 46,646 | 1,471 |
| T7 | 5 | 1700,3500-3200,4500 | 275 | 13 / 19 / 22 | 127,633 | 6,735 |

- Every crop has lettering, lines and rail. T1 has the Hamilton Ave streetcar. T2 has the Vandalia and B&O railroad with its ticks. T3 has the Ludlow Ave railroad and streetcar and sheet number 39. T4 has the McMicken streetcar. T6 and T7 have the Eighth St and Sixth St streetcars.
- T7 has the George St and Sixth St house-number rows written against the block lines (the false-rail case of the rail5 report).
- A 7th crop (plate 1A, 0,1200-1500,2200) was planned and not annotated.

## Files

- **T#_mask.png**: 8-bit, the size of the window. The values are:
  - 0 = paper;
  - 1 = ink that is not text;
  - 2 = text ink;
  - 3 = don't care: ink a glyph shares with a line crossing or touching it, and boxes set by hand.
- **Ink** is ink_bins.py's rule: Lab L < 140 of 255 on the paper mask (cufp/N/png_alpha_s4.npy). The mask's ink agrees with unet_data/N_bins.png's ink on 99.97-99.99% of pixels (bin8_eval.py).
- **T#_words.json**: one entry per word, with:
  - `reading`;
  - `kind`;
  - `flags`;
  - `angle`: the reading direction in degrees, in image coordinates with y down. 0 reads left to right, 90 reads downwards, -90 reads upwards;
  - `height` and `length` of the snapped box;
  - `poly`: the 4 corners, in full-plate px;
  - `aabb`;
  - `touches_line`: the glyph ink is joined to a straight line that runs out of the box;
  - `text_px`;
  - `annot_line`: the line of annot/T#.txt it came from.
- **annot/T#.txt**: the hand input. build_truth.py's docstring gives the format.
- **work/**: the reading tiles (T#_zoom_RC.jpg, 1.5x with a 50 px grid) and the check tiles (T#_check_RC.jpg). On the check tiles:
  - text is red;
  - don't care is yellow;
  - other ink is grey;
  - ink that bin 8 calls text and the truth does not is green;
  - word boxes are magenta, numbered by annotation line.

**Kinds**

| kind | what it covers |
|---|---|
| street | street, avenue, alley and court names |
| house | house numbers |
| lotdim | lot dimensions, bearings, areas |
| lot | auditor's and actual lot numbers |
| block | block numbers |
| owner | owner, estate, subdivision and firm names |
| bldg | building names |
| story | story heights and the figures inside buildings |
| pipe | water-pipe labels |
| sewer | sewer labels |
| rail | railroad names |
| adj | adjoining sheet numbers |
| ditto | ditto marks |
| other | anything else |

**Flags**

| flag | meaning |
|---|---|
| partial | cut by the window edge |
| unsure | the reading or the place is doubtful |
| run | a row of house numbers along one block face, boxed as one word: the reading lists the numbers in order |
| curved | the word follows a curve |
| nosnap | the box was kept as typed |
| g:NAME | spaced letters of one name, boxed letter by letter |

## How it was made

1. **Reading.** Every word was read by eye on the 1.5x tiles, with 2.5-3x zooms where unsure. Its centre line (x1 y1 x2 y2, in reading order) and its glyph height were typed. Placing is to about 10 px.
2. **Snap** (build_truth.py). Straight runs of at least max(41, 1.5 h) px are taken out of the ink, with 2 px of their ragged edge (line_mask, after a 3x3 closing). The box is then fitted to the remaining pieces that lie at least 70% inside the typed box grown by 0.15 h + 3-4 px. A side can grow by that margin and shrink by at most 0.25 h along or 0.2 h across, so a glyph joined to a short line is not cut off.
3. **Mask.** Text = ink in the snapped box (grown 1.5 px) that is not on a straight run reaching out of the box.
   - Line ink within 2 px of glyph ink inside the box becomes don't care.
   - Hand fixes:
     - EXCL (not text);
     - FORCE;
     - CARE;
     - CARELINE: dashed lines through glyphs;
     - CAREDIR: rail, streetcar and street lines through big glyphs, such as 39, AVENUE, VANDALIA and W. McMICKEN.
4. **Checking.** Every check tile of every crop (53 tiles with paper) was looked at, at 1.5x or, for 16 of them, in 0.6x montages of four.
   - Most were looked at after the last rebuild. The rest were looked at before the last small fixes of their crop.
   - Wrong boxes, missed glyphs and red line pieces were corrected, and the crop rebuilt.
   - T1 took five builds; the others took two to four.

## What counts as text

**Text:**
- letters and digits;
- primes and double primes (25', 6");
- ° ± ½ & and periods;
- the hyphens of ranges (4149-47);
- parentheses;
- ditto marks;
- story-height figures;
- No.

**Not text:**
- hook marks on lot lines;
- hydrant dots and fire-alarm circles;
- the X of stables;
- the valve sign inside "35" W. PIPE" (set to don't care);
- rail ticks;
- lot, block, building, pipe and sewer lines and their dashes;
- streetcar dashes.

**Spaced names** inside rail corridors, such as V A N D A L I A R. R. and the B&O letters, are boxed letter by letter. One box along the corridor would take the ticks as text.

## Known limits

- Faint glyph parts lighter than L 140 are not ink, so they are in no class. One ditto mark on T1 is wholly below the threshold and was dropped.
- Readings flagged unsure (85 words) may be wrong in a digit. Some T2 corridor letters are read as printed although they do not spell the expected name: the second E, the lone N.
- Line stubs shorter than the glyphs and lying wholly inside a box remain text where they were not seen at 1.5x. The worst cases were fixed with EXCL and CARE.
- Run boxes (21 words) cover dense house-number rows and columns. Their readings list the numbers, but the single numbers have no boxes of their own.

## Scoring suggestion

- **Pixels:** score on ink with mask 1 or 2, and leave 3 out.
- **Words:** take the share of each word's text pixels that is found, and count a word as found at 50% or more.
- **Readings:** compare against `reading`, and leave out the words flagged unsure, partial or run.
- **Baseline.** ink_bins' bin 8 on these crops (measure/bin8_eval.json):
  - precision 0.854;
  - recall 0.846;
  - F1 0.850.
