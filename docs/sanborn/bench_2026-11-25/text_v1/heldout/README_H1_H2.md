# Held-out text truth H1 and H2 (plate 90), 25 Nov 2026

Two new hand-checked text truth crops for the step 2 and step 3 gates. They are in the same format as the earlier truth (`text/inventory/truth/`, T1-T7), so the same scorer can read them.

**They are for the gate scorer only.** The finder and classifier builders must not open, score on or tune on these files.

## The crops

| crop | plate, scale | window x0,y0-x1,y1 (full px) | words | text px | don't care px | other ink px |
|---|---|---|---|---|---|---|
| H1 | 90, 200 ft (uncut sheet) | 5640,3950-7140,4950 | 225 | 64,315 | 4,186 | 108,712 |
| H2 | 90, 200 ft (uncut sheet) | 880,2100-2380,3100 | 365 | 101,953 | 6,488 | 117,637 |

All counts are measured, by `heldout-a/scripts/stats.py`, written to `heldout-a/stats.json`. Text is 37% (H1) and 46% (H2) of the scored ink (mask 1 or 2).

- **H1.** It holds:
  - the curved AVALON, WOODBINE and WILDWOOD, plus OAKMONT and DECAMP, both partial;
  - house numbers along Avalon, Woodbine and Oakmont (206, 216, 8128, 8135, 8122...);
  - the circle round PARK, block 30, with its curved 4"W.PIPE and 8"SEWER labels;
  - block numbers 30 and 19;
  - the spaced subdivision letters T. E. J. TAYLOR and J. HEIS...;
  - CHURCH twice, lot numbers, lot dimensions, a bearing (S.85°50'E), story heights and ditto marks.
- **H2.** It holds:
  - the straight CURZON and WISWELL, and AVENUE (vertical, partial);
  - house-number rows on both faces of both streets (8460-56, 8436-32-28, 8424-20...) with their ditto marks;
  - 4"W.PIPE and 8"SEWER twice;
  - blocks 8 and 10;
  - the heavy spaced letters of J. F. MILLS (F., M, I, L);
  - dense lot numbers, lot dimensions and story heights.
- **Words by kind** (measured):
  - H1: 85 lot dimensions, 54 lot numbers, 26 story heights, 21 house numbers, 11 owner letters, 6 pipe labels, 6 sewer labels, 5 street names, 5 ditto marks, 2 building names, 2 block numbers, 2 other (the P A R K letters);
  - H2: 152 lot numbers, 87 lot dimensions, 43 story heights, 36 house numbers, 34 ditto marks, 4 owner letters, 3 street names, 2 pipe labels, 2 sewer labels, 2 block numbers.
- **Flags** (measured):
  - H1: 18 unsure, 18 partial, 6 curved;
  - H2: 13 unsure, 22 partial.
- **Words touching a line:** 93 of 225 on H1 and 130 of 365 on H2 (`touches_line`).
- **Ink check** (measured): the mask's ink agrees with `unet_data/90_bins.png`'s ink on 99.97% of pixels (H1 0.99967, H2 0.99972). That is the same agreement as T1-T7. Only the ink layer of that file was compared; its bins were not read.

## Files

In `text_v1/heldout/`:
- **H1_mask.png and H2_mask.png:** 8-bit, the size of the window. The values are:
  - 0 = paper;
  - 1 = ink that is not text;
  - 2 = text ink;
  - 3 = don't care: ink a glyph shares with a line, and boxes set by hand.
- **H1_words.json and H2_words.json:** the same fields as T#_words.json:
  - `reading`, `kind`, `flags`, `angle`, `height`, `length`, `poly`, `aabb`;
  - `snapped`, `touches_line`, `text_px`, `annot_line`;
  - curved words also carry `path`, the typed centre line.

  The file also holds `win`, `plate`, `counts`, `boxes` (the hand fixes) and `held_out: true`.
- **crops_H1_H2.json:** the two windows and why they were chosen.

In `text_v1/heldout-a/` (the work, kept apart from the crops):
- **annot/H1.txt and annot/H2.txt:** the hand input. One line per word is its typed centre line, glyph height, reading, kind and flags. The other lines are hand fixes (EXCL, FORCE, CARE, CARELINE, EXCLLINE).
- **scripts/:**
  - `build_heldout.py`: builds the masks and words;
  - `tiles.py` and `view.py`: reading tiles;
  - `rot.py`: turns a window 90 degrees each way to read rotated words;
  - `cz.py`: a zoom of the mask beside the scan;
  - `missed.py`: lists the glyph-sized ink left outside every word box;
  - `stats.py`: the counts.
- **work/:**
  - the reading tiles, `H#_zoom_RC.jpg`;
  - the check tiles, `H#_check_RC.jpg`. Text is red, don't care yellow, other ink grey; text that runs well outside its box is orange; word boxes are magenta, numbered by annotation line;
  - `H#_missed_RC.jpg`: the left-over pieces in blue;
  - `H#_overview.jpg`: the mask at 0.6x;
  - the zooms used while reading.
- **out/:** a second copy of the four mask and words files.

To rebuild, run `python -B scripts/build_heldout.py H1 H2 --check` from `heldout-a`. It writes to `heldout/` and `heldout-a/out/`.

## How it was made

1. **Windows.** Both were chosen by looking at the scan only: the 1/8 thumbnail, then 0.33x and 0.6x views of plate 90.
   - H1 was put where Avalon, Woodbine and Wildwood curve, with block 30 and block 19 inside.
   - H2 was put across Curzon and Wiswell, where the 4"W.PIPE / 8"SEWER labels are.
   - No finder, words, shapes or bin 8 output was opened to choose the windows or make the masks.
2. **Ink.** Lab L < 140 on the paper mask (`cufp/90/png_alpha_s4.npy`), the rule of ink_bins.py.
3. **Reading.** Every word was read by eye on 1.5x tiles with a 50 px grid.
   - Every tile was read again on 2.5-3x zoom quadrants.
   - Doubtful words were read on 4-7x zooms, and rotated words in the 90-degree turned views.
   - Each word was typed as its centre line in reading order (angle 0 reads left to right, 90 downwards, -90 upwards), with its glyph height.
   - A curved word was typed as a polyline (PATH), and each of its segments is boxed on its own.
4. **Own component labelling and snap** (build_heldout.py, written for this; the rule is the same as the earlier truth, so the scores compare):
   - straight runs of max(41, 1.5 h) px or more, in any of 72 directions after a 3x3 closing, are line ink;
   - each typed box is snapped to the 8-connected pieces of the remaining ink that lie at least 70% inside it;
   - text is the ink in the snapped box that is not on, or within 2 px of, a straight run reaching out of the box;
   - line ink within 2 px of that text inside the box is don't care (3). This is the shared glyph-line ink.
   - For a figure drawn over a small building outline whose sides are under 41 px, a few words use a 36 px peel or a box typed tight (nosnap).
5. **By-eye correction, tile by tile, at 1.5x and 3-5x.** Every check tile of both crops (6 + 6) was looked at, and the doubtful places were zoomed to 3-5x beside the scan.
   - Hand fixes: H1 has 23 (9 EXCLLINE, 4 CARELINE, 3 EXCL, 1 FORCE, 6 CARE); H2 has 46 (10 EXCLLINE, 21 CARELINE, 5 EXCL, 2 FORCE, 8 CARE).
   - What they fixed:
     - sewer and pipe dashes that run under or over labels and house numbers;
     - building outlines through lot numbers and story figures;
     - a dashed park line through CHURCH;
     - hook marks after numbers;
     - two glyph strokes that happened to line up with a line and had been peeled.
6. **Completeness check** (missed.py). It lists every glyph-sized piece of non-line ink that is outside all word boxes and holds no text: 82 on H1 and 110 on H2. They are drawn in blue on `work/H#_missed_RC.jpg`, and every one was looked at.
   - On H1 this found one missed word, 90'. On H2, the partial 47 and 48 and the end of 8445 were found while checking the tiles.
   - All the other pieces are dashes, hook marks, building-outline stubs, the black dots and the pink circle on Avalon.

## Conventions used

Ben has not answered the conventions, so the plan's proposals are used as defaults:
- **Text:**
  - ditto marks and story heights;
  - pipe and sewer labels (kind `pipe` / `sewer`). They are not linked to their line in this truth;
  - primes, periods, °, ± and the hyphens of house-number ranges.
- **Not text (1 in this mask; code 5 in the hand-off scheme):**
  - the black dots and the pink circle on Avalon (hydrant or alarm marks);
  - manhole O marks, although none was seen in these windows;
  - hook marks (⊥, ⊢, the angled lot hooks);
  - sewer and pipe dashes, including the over- and under-bars on house numbers and labels;
  - dashed and partition lines inside buildings.

  These windows have no rail ticks.
- **Shared ink** where a block side, lot line or building outline runs through a number is 3 (don't care). The line keeps its own ink.
- **Spaced names** are boxed letter by letter with a `g:` flag: P A R K, T. E. J. TAYLOR, J. HEIS..., J. F. MILLS.

## Known limits and things to check

- **Unsure readings:** 18 words on H1 and 13 on H2 are flagged `unsure`. Readings should be scored without them, and without `partial`. The doubtful ones are:
  - H1:
    - 1½ by the church;
    - 39½ and 22.3;
    - 58 (or 68);
    - 8128 and 8125 on Woodbine;
    - the 30' and 1 near Avalon;
    - the hollow 68 and A;
    - HEIS.
  - H2:
    - 265 (or 255) on AVENUE;
    - 68 / 29 / 1 at the pink building;
    - 84.75;
    - 94.03';
    - 118;
    - 189;
    - F.
- **J. F. MILLS is read by inference.** The heavy letters F. (1310-1375, 2100-2150), M, I and L are spaced across the blocks. The name was read from their spacing and from the J. F. MILLS name north-east of the window. The "F." could be a hook mark; check it.
- **Hollow or dotted figures** are partly lighter than L 140, so only part of them is ink:
  - on H1, the A of TAYLOR, the 68 over lot 8 and an 8 by 94 are text, flagged unsure;
  - the dotted figures inside the building at lot 80 (H1, about 6985-7030, 4836-4876) are don't care.
- **Whole areas set to don't care** where glyphs and outlines cannot be told apart at the pixel:
  - the pink building at H2 2304-2356, 2122-2154;
  - the F-like mark in the lot-80 building;
  - the mark under 8"SEWER at H1 6672-6702, 4246-4266.
- **Building outlines.** Outlines shorter than 41 px that touch figures were handled by hand where they were seen. A few short stubs of 1-3 px may remain as text (estimate).
- **Word boxes.** Like T1-T7, no run boxes were used: every house number, ditto and lot number has its own box.
- **Time.** About 45 minutes of wall clock in all, 20:14 to 20:59 by the system clock (measured). That includes choosing the windows, reading, building, checking and this README. About half went to each crop (estimate).

## Held-out warning for the step 3 builder

Plate 90 is not wholly unseen by the earlier prototypes:
- `text/shapes/glyphs/90.npz` holds 28,965 glyph candidates of plate 90, and 2,433 of them have their centre inside H1 or H2 (1,103 and 1,330). This was counted after the masks were finished, from the centres only.
  - Any classifier fitted on the cluster labels must leave out the plate 90 glyphs inside these two windows, or all of plate 90.
  - This applies to the cluster labels, ben_label_sheet.json and Claude's round 1 and 2 labels.
- The words prototype was developed partly by looking at the curved names on 90 (Avalon, Woodbine). So H1 is not a clean held-out test for step 5.
- The finder was run on 90 and looked at by eye (verify unseen_windows.py), but no truth existed there. It was not scored or tuned on these windows.

## Scoring suggestion (as for T1-T7)

- **Pixels:** score on ink with mask 1 or 2, and leave 3 out.
- **Words:** count a word as found when 50% or more of its text pixels are found.
- **Readings:** compare against `reading`, leaving out the words flagged unsure or partial.
