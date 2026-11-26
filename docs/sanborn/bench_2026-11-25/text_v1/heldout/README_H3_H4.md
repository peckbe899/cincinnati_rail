# Held-out text truth H3 (plate 47) and H4 (plate 54A), 25 Nov 2026

Two new hand-checked text truth crops for the step 2 and step 3 gates. They use the same format as the earlier truth (`text/inventory/truth/`, T1-T7), so the same scorer can read them.

**They are for the gate scorer only.** The finder and classifier builders must not open, score on or tune on these files.

## The crops

| crop | plate, scale | window x0,y0-x1,y1 (full px) | words | text px | don't care px | other ink px |
|---|---|---|---|---|---|---|
| H3 | 47, 400 ft (PDF sheet) | 7040,4560-8540,5560 | 194 | 37,724 | 22,689 | 54,996 |
| H4 | 54A, 100 ft (cut piece, heavy pink tint) | 7190,3950-8690,4950 | 204 | 65,101 | 2,956 | 112,573 |

All counts are measured by `heldout-b/scripts/stats.py` and written to `heldout-b/stats.json`. Text is 41% (H3) and 37% (H4) of the scored ink (mask 1 or 2).

- **The windows were chosen by looking at the scans only.** No finder, words, shapes or other prototype output was opened, and none of Ben's truth (street map, rail, lines) was used.
- **H3.** It holds:
  - the Bustard Moore's subdivision twice: BUSTARD MOORE'S OF LOT 6 (upper) and BUSTARD MOORE'S (lower, diagonal);
  - CHAS. BROWN'S SUB OF L. 3 (partial), C. H. & EMMA ZORN and SUB OF LOT 7 in spaced letters;
  - dense rotated lot numbers, plain and in brackets ((28) to (32), 33-37, 19-27, 26½), and rotated lot dimensions along the lot lines;
  - street names FYFFE and AVE. (Fyffe Ave), SAFFER, KAVANAUGH and SCHMANN (partial);
  - small framed buildings with story figures (12 tight boxes);
  - the spaced letters of ELIZA and ISAAC (2 and 4 letters in the window), [2], block 27 (partial);
  - a rotated 6"W.PIPE label on its line, and 752.72', 19.51 AC.;
  - large empty lots crossed by long lines, to test false text on lines.
- **H4.** It holds:
  - DANDRIDGE with house numbers on both block faces (500 to 540-42 and 501 to 539-41-43);
  - the north face of the street below (500-02 to 538-40-42) and the word STREET;
  - NOAH (an alley) and block 36, with the alley line and a lot line through the 36;
  - 12"SEWER twice, 6"W.PIPE and 35"W.PIPE;
  - lot numbers 126-205 (189 turned, with a leader arrow), 49 story heights, 33 ditto marks and 19 lot dimensions.
- **Words by kind** (measured):
  - H3: 71 lot dimensions, 64 lot numbers, 29 owner letters or words, 12 story heights, 6 ditto marks, 5 street names, 5 other, 1 block number, 1 pipe label;
  - H4: 53 lot numbers, 49 story heights, 41 house numbers, 33 ditto marks, 19 lot dimensions, 3 street names, 2 sewer labels, 2 pipe labels, 1 block number, 1 other.
- **Flags** (measured):
  - H3: 114 unsure, 12 partial, 12 tight, 29 spaced-letter groups (g:);
  - H4: 4 unsure, 14 partial.
- **Words touching a line** (`touches_line`, measured): 105 of 194 on H3 and 64 of 204 on H4.
- **Ink check** (measured): the mask's ink agrees with the ink layer of `unet_data/N_bins.png` on 99.91% (H3) and 99.98% (H4) of pixels. Only ink against paper was compared; the bins were not read.

## Files

All in `data/sanborn/bench_2026-11-25/text_v1/heldout/`:
- `H3_mask.png`, `H4_mask.png`: 8-bit, 1500 x 1000, the size of the window. 0 paper, 1 ink that is not text, 2 text ink, 3 don't care.
- `H3_words.json`, `H4_words.json`: the same fields as `T#_words.json`: reading, kind, flags, angle, height, length, poly, aabb, touches_line, text_px, annot_line, snapped. The top level also has crop, plate, win, why, scale_ft, mask_values, counts and the hand fixes (`boxes`).
- `H3_annot.txt`, `H4_annot.txt`: the hand annotation the masks are built from.
- `crops_H3_H4.json`: the two windows.

The work is in `text_v1/heldout-b/`:
- `scripts/`: `hcommon.py` (ink and windows), `build_h.py` (the builder), `view.py`, `tiles.py`, `zc.py` (picture tools), `suspects.py` (sheet of glyph-sized non-text pieces), `stats.py`.
- `annot/H3.txt`, `annot/H4.txt`: the working annotations.
- `work/`: reading zooms (`H3_z_RC.jpg` at 4x, `H4_read_RC.jpg` at 2x), check tiles (`H*_check_RC.jpg`), suspect sheets.
- `_second_copy/`: a copy of the scripts, annotations and the delivered files.

Rebuild with `python -B build_h.py H3 --check 250 200 3` and `python -B build_h.py H4 --check 375 250 2` from `heldout-b/scripts/`. It uses the system python (cv2, numpy, scipy) and takes about 6 s per crop.

## How they were made

1. **Reading.** Every word was read by eye on 2x (H4) or 4x (H3) tiles of the scan with a 10 or 50 px grid, and 5-10x zooms where unsure. Its centre line (from the first glyph's leading edge to the last glyph's trailing edge, in reading order) and glyph height were typed into `annot/H#.txt`.
2. **Own component labelling** (`build_h.py`, written for this task):
   - Ink is the ink_bins rule: Lab L < 140 on the paper mask (`cufp/N/png_alpha_s4.npy`).
   - The typed box is first corrected from the free glyph pieces near it: their median across, their height, their extent along. Specks, thin long pieces (dashes, line bits, a lone 1), and words with too little free ink keep the typed place.
   - Each 8-connected ink piece with 70% or more of its pixels in the word box (grown by 0.15 h + 3-4 px) is a glyph piece and is text. A piece with less is shared with a longer line, and only its part inside the box is considered.
   - **Line ink is never text.** Inside the box, ink on a straight run of max(31, 1.5 h) px that reaches at least 8 px out of the box is line ink, grown by 2 px for its ragged edge. A broken or dotted line also counts: a run at least twice that long and at most 5 px thick, with breaks of up to 6 px bridged along its direction. A straight stroke wholly inside the box (a long italic diagonal) is not a line.
   - Line ink within 2 px of glyph ink, and small crumbs left in the box, are don't care (3): this is the shared ink.
3. **By-eye correction at 1:1, tile by tile.** Every check tile was looked at: 16 for H4 at 2x and 30 for H3 at 3x. On them text is red, don't care yellow, other ink grey, and glyph-sized non-text pieces cyan. The doubtful spots were also looked at in 5-8x zooms beside the scan.
   - Wrong places were fixed with NOT, TEXT, CARE boxes and NOTS, TEXTS, CARES strips, applied after the words. There are 30 fixes on H4 and 23 on H3; each has a note in the annotation.
   - The suspect sheets were looked at for both crops:
     - H4: 4 of its 5 sheets (76 of 100 pieces). All are dashes, line ends and specks.
     - H3: 2 of its 11 sheets (48 of 252 pieces). Two missed rotated numbers were found and added; the rest were broken line pieces.
   - The 8 near-empty H3 tiles were looked at in a half-scale montage (`work/H3_check_montage_sparse.jpg`).
   - H4 took about 10 builds and H3 about 8.

## Conventions

Ben has not answered the plan's convention questions, so the plan's proposals are used as defaults:
- ditto marks and story heights are text;
- hydrant dots, hook marks and rail ticks are not text (1). The leader arrow of 189 (H4) is joined to its 1 and was set to don't care (3);
- a block side or lot line through a number stays a line. Shared ink is 3: ink sorting gives it to the line, and training does not score it;
- pipe and sewer labels are text. The sewer dashes under the 12"SEWER labels are line (NOTS strips).

Also:
- the underlines and building frames round story figures are line;
- parentheses, brackets, primes and the ½ are text;
- the word STREET on H4 is the second half of a name printed off the window; it is kind street with its reading as printed.

## Don't care set by hand

This matters for H3. Its don't care is 19.7% of the ink (H4: 1.6%). Of H3's 22,689 don't-care px, 18,855 come from hand CARE boxes, 73,598 px² in all; the rest is shared ink. These are places where glyphs and dotted lot lines run together so closely that a 1:1 call cannot be defended:
- the dense block of narrow lots south of Schmann St (8343-8540, 5391-5560);
- the cluster of small framed buildings and figures by Kavanaugh and Geo. McCormack St (7040-7180, 5440-5560);
- the Fyffe Ave corner (7040-7106, 4758-4836);
- lot numbers 19 and 21 (7232-7305, 5155-5208);
- the rotated dimensions of lots 19-26 (7275-7400, 5262-5350);
- (32) and 33 across two lot lines (7345-7420, 4700-4735);
- small figures in the teal band above Saffer.

The words there (lots 19 and 21, four rotated dimensions and the 4 run rows of the dense block) were taken out of the word list. The scorer leaves 3 out, so these regions count neither way.

## Known limits

- **H3 readings are weak.** 114 of its 194 words are flagged unsure, mostly small rotated lot dimensions 9-12 px tall written along dotted lines, and some sub-lot figures. Their ink is text either way; their readings are best guesses. Only 72 H3 words are unflagged (H4: 188).
- **SAFFER** (H3) is squeezed between two street lines and was set by a hand TEXTS strip; its letter ends where they touch the lines may be a few px off.
- **Glyph and line separation is to about 2 px.** Where a glyph lies along a line (the 3 of 163 on H4, the 6 of LOT 6 on H3), the overlap was set to don't care by hand.
- **Tiny words.** 5 words have under 20 text px in the window: 3 on H3 and 2 on H4. They are small ditto marks and slivers of partial words at the edge, such as the H4 house numbers below y 4950.
- **Few big-lettering words.** Street names: 5 (H3) and 3 (H4). Block numbers: 1 each. With H1 and H2 the four held-out crops have 16 street-name words and 6 block numbers, so a recall of 0.95 on these kinds rests on few words.
- **Not all H3 suspects were reviewed.** 204 of 252 suspect pieces on H3 were not looked at one by one, though every check tile was. Missed glyphs may remain among them. **Estimate, not measured:** under 1% of H3 text px.

## Scoring suggestion

The same as T1-T7:
- **Pixels:** score on ink with mask 1 or 2, and leave 3 out.
- **Words:** a word is found when 50% or more of its text px are found.
- **Readings:** compare against `reading`, and leave out words flagged unsure, partial or run.
- **Kinds:** for recall by kind, H3 adds lot numbers and dimensions at 400 ft; H4 adds house numbers and ditto marks at 100 ft on a heavy tint.
