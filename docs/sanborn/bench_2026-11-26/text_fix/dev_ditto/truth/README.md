# Ditto marks: targeted dev truth (26 Nov 2026)

DEV truth for scoring how the text finders handle DITTO MARKS. 51 crops, 200 ditto words, on 20 plates that are not
sealed. Everything was decided by eye on the scan. No finder output and no bin 8 was looked at while choosing or
labelling, with one exception, which is described under "Second pass" below. Nothing in the repo or in text_v1 was changed.

All numbers are MEASURED unless marked (e).

## What is in the set

| scale | crops | ditto words | median text px per word |
|---|---|---|---|
| 100 ft (44, 1A, 3, 2, 4, 12, 57, 54A) | 15 | 42 | 47.5 |
| 200 ft (30, 90, 60B, 19, 26A, 64A, 74, 86) | 27 | 98 | 23 |
| 400 ft (47, 49, 93A, 48) | 9 | 60 | 17 |
| all | 51 | 200 | 23 |

- Style, by eye, by shape only: `pair` = two short ticks or dots side by side or one above the other (`=` or `:`),
  joined or not (143 words); `quote` = two slanted strokes like a printed `"` (41); `other` = a single tick, a blob or
  anything else (16).
- Tiny tick pairs (style pair, 30 text px or less): 111 words.
- 15 words are flagged `unsure` (it may not be a ditto, or the ink is too worn to be sure).
- Plates with no ditto in any looked-at window: 5, 94. (90 has only 3 dittos in its 6 windows.)

## Files

Same layout as text_v1/truth, so `text_v1/code/score_text.py` runs on it unchanged.

- `crops.json`: per crop `plate`, `win` [x0,y0,x1,y1], `scale_ft_per_inch`, `why`, `kind: "targeted"`, `target: "ditto"`,
  `scope_pad: 25`, and `drawn` (the seed, rank and draw number of the random window it is).
- `<id>_mask.png`: uint8, the size of the window. 0 paper, 1 ink that is not text, 2 text ink, 3 don't care.
- `<id>_words.json`: `words` lists every target ditto (kind `ditto`, reading `"`) and every other word inside the
  scope with its kind. Per word: `poly`, `aabb`, `text_px`, and for targets `target: true`, `ink_px`, `pieces`,
  `piece_px`, `style`. Also `scope` (the scored boxes) and `counts_in_scope`.
- `annot/<id>.txt`: the hand input. `check/`: the check pictures (below). `build.log`: the last build.
- `../truth_v1_frozen/`: the set as it was before scoring (42 crops, 172 dittos); `../truth_frozen_before_scoring.sha1`
  and `../truth_frozen_v2.sha1` are checksums of both versions.

## Conventions (Ben has not answered yet; these are the defaults)

- Ditto marks and story heights are text. Pipe and sewer labels are text.
- Hydrants, manholes, hooks, rail ticks, dashes of dashed lines, hatching, line stubs and specks are not text.
- A block side through a row of house numbers stays a side.
- Where text ink and line ink touch, the ink within 2 px of the contact is don't care (the v2 shared-ink rule).
- The SCOPE: each target word's axis box grown by 25 px. Inside the scope ALL ink is labelled (text 2, not text 1,
  don't care 3 only at contacts or where it truly cannot be told). Outside the scope all ink is 3.
- Primes and inch marks (`25'`, `12"`) are text but are NOT dittos; they belong to their figure's word.

## How the windows were chosen (scripts/choose_windows.py)

1. 22 plates (the task's list): 100 ft 44 5 1A 3 54A 2 4 12 57; 200 ft 90 30 60B 19 26A 64A 74 86; 400 ft 47 49 93A 94 48.
2. Per plate, window corners drawn uniformly with `random.Random('ditto-' + plate)`; a 400 x 300 window is kept when it
   is 99% or more on the paper mask, BUILT-UP (3% or more building colour at 1/4 size: Lab a* more than 5 above the
   plate's median, or b* more than 7 above), INKED (2.5% or more ink), does not overlap H1-H4 (grown 25 px) and does
   not overlap an earlier kept window. The first 30 kept windows per plate, in draw order, are in
   `choose/windows.json`; every draw and its verdict in `choose/windows_all.json`.
   - The ink rule was added after the first look: plate 90 rank 4 and plate 86 rank 2 were bare paper whose yellowed
     edge passed as building colour. Same seeds and order; the earlier list is `choose/windows_v1.json`.
3. Ranks 1-6 of every plate were looked at, in order: 132 windows (100 ft 54, 200 ft 48, 400 ft 30).
   51 of them hold dittos and became crops DD01-DD51. The full list with counts is `choose/looked.json`.
4. In each window EVERY ditto mark was taken, whatever it looked like. Windows were read at 2.5-3.5x with a 20 px grid
   (pics/search/w_*.jpg, wp_*.jpg), and unclear marks at 5-8x (pics/cand/*.png, pics/z_*.png).

## Second pass (completeness)

After the eye pass and after the first scoring, three scan-only rules listed marks the eye pass might have missed,
in the same 132 windows:
- `scripts/pairfind.py`: isolated pairs of small pieces (3-60 px each, box side 12 or less, 3-14 px apart, joint box
  16 px or less, no other ink within 4 px): 73 pairs (pics/pairs/sheet_*.png).
- a looser pair rule (pieces 3-30 px, 3-10 px apart, no other ink within 2 px): 109 pairs; and isolated single pieces of
  12-60 px on the 200 and 400 ft plates: 150 (pics/pairs/p2_*.png; the rules are in scripts/pass2_sheets.py).
Every listed mark was judged by eye on the scan. 28 more dittos were found (10 at 100 ft, 3 at 200 ft, 15 at 400 ft):
9 new crops (DD43-DD51) and 9 words added to DD17, DD29, DD33, DD39 and DD41. So the eye pass missed 28 of 200 (14%).
More may remain (e: a few per cent, mostly single ticks at 100 ft, where the single-piece list was not reviewed).

The exception to "no finder output": the second pass was done after I had scored the first version and seen the
finders' pictures. The rules that listed candidates read only the scan, every listed mark was judged, and none was
kept or dropped because of what a finder does. The first version is kept in `../truth_v1_frozen` and its scores in
`../scores/*_v1.json`; on it the finders' ditto recall is the same within 0.01 (0.493 px, 63/172 words; final set
0.500 px, 73/200).

## How the masks were built (scripts/build_dd.py)

An adapted copy of text_v1/truth-fix/scripts/build_truth_v2.py (with copies of common.py and snapline.py):
- Same word snap, line rule, hand ops (EXCL, FORCE, CARE, CAREDIR, CARELINE, NOTTEXT, FORCELINE, EXCLCIRC) and
  shared-ink rule as truth v2.
- New: `B x0 y0 x1 y1 | reading | kind [| flags]` gives a word by its axis box (inclusive pixel corners). The ink in the
  box grown by 1 px is the word's ink, less line ink that reaches outside the box. Dittos use tight boxes read off the
  piece list of the scan (scripts/cand.py, scripts/pieces.py).
- New: the scope (above), `target` and `nontarget` flags, `style:` flags, and `kind: negative` for the negative set.
- Neighbouring words in the scope were labelled with scripts/scope.py and scripts/cluster.py (every ink piece in the
  scope not covered by a word box is listed and shown numbered; each was named by eye as a word or left not text).

## Checks (pictures kept in check/)

- `DD##_zoom.png`: every target at 6x, scan left and truth right (text red, not text blue, don't care orange).
- `DD##_overview.png`: the whole window at 2.5x, scan above and truth below, scope bright, outside scope grey.
- `DD##_scope.png`, `DD##_clusters.png`: the labelling aids. `targets_01-05.png`, `pass2_01-02.png`: all targets on
  contact sheets at 5x, scan beside truth.
- Every target was looked at at 5-6x beside the scan. Fixes made on that look: a hyphen on 64A taken for a ditto
  (DD27, now a `nontarget` house word), missed neighbour words (GILSEY on DD05, 318 on DD03, the house numbers on DD27),
  a dashed line through 7/15 (DD03), worn lot figures fused with lot lines made don't care (DD38, DD51).

## Scores (for reference; scores/summary.txt, scores/ditto_*.json)

Ditto recall, pixels (words found = half or more of the word's text px called text):

| | bin 8 | finder2 | finder3 |
|---|---|---|---|
| all 200 | 0.777 (172 words) | 0.500 (73) | 0.500 (73) |
| 100 ft, 42 | 0.590 (26) | 0.823 (34) | 0.823 (34) |
| 200 ft, 98 | 0.889 (90) | 0.390 (33) | 0.390 (33) |
| 400 ft, 60 | 0.902 (56) | 0.092 (6) | 0.092 (6) |
| tiny tick pairs, 111 | 0.922 (105) | 0.260 (24) | 0.260 (24) |
| quote style, 41 | 0.619 (29) | 0.707 (25) | 0.707 (25) |

Finder2 codes on ditto text px: other ink (5) 48%, text by context (3) 45%, text sure (2) 4%, line (1) 2%.
At 400 ft 82% is code 5. finder3 gives exactly the same ditto pixels as finder2.

## Known limits

- The windows are random, but whether a window holds dittos is not: dittos cluster in rows of lots, so a few windows
  give many words (30: 33 words; 48: 30; DD42 alone 17). Per-plate weights are uneven.
- `unsure` words (15) and `partial` words cut by the window edge are included in the scores.
- Some 400 ft rows (47, 93A) are worn: figures fused with lot lines were made don't care, not text.
- Faint marks lighter than the ink threshold (L 140) have no ink and cannot be labelled (e.g. 64A 2905,3994).
