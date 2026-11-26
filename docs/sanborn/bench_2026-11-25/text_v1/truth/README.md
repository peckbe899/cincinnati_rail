# Text truth v2: 6 hand-checked crops (25 Nov 2026)

Truth for scoring the text-first stage. v2 is v1 (text/inventory/truth, the inventory agent's crops) with the errors the verify agent found fixed, Ben's proposed conventions applied, and every crop looked at again. Everything was decided by eye on the scan. Nothing in the repo was changed.

- **Held-out crops are not here.** The new held-out crops of step 1 are made and kept elsewhere; this folder holds only T1-T7, which the finder and the classifier may use.
- **The conventions are proposals.** Ben has not answered the conventions question yet (text_first.md section 9). v2 uses the plan's proposals as defaults (below). If Ben decides otherwise, the annotation files make the change a one-line edit per mark and a rebuild.

## The crops (crops.json, unchanged windows)

| crop | plate | window x0,y0-x1,y1 (full px) | words | runs / unsure / partial | text px | not-text px | don't care px |
|---|---|---|---|---|---|---|---|
| T1 | 44 | 1500,1500-3000,2500 | 240 | 0 / 25 / 24 | 112,290 | 128,849 | 5,647 |
| T2 | 44 | 2700,2500-4200,3500 | 145 | 0 / 16 / 17 | 59,274 | 81,499 | 2,643 |
| T3 | 44 | 9000,2400-10500,3400 | 70 | 0 / 4 / 6 | 52,552 | 72,011 | 2,507 |
| T4 | 1A | 2000,950-3500,1950 | 184 | 4 / 15 / 11 | 94,036 | 112,913 | 7,006 |
| T6 | 5 | 3900,1550-5400,2550 | 100 | 4 / 7 / 13 | 45,898 | 104,425 | 1,843 |
| T7 | 5 | 1700,3500-3200,4500 | 276 | 13 / 19 / 22 | 127,059 | 155,766 | 6,731 |
| all | | | 1,015 | | 491,109 | 655,463 | 26,377 |

v1 had 495,530 text px, 657,439 not-text px and 19,980 don't-care px (measured, truth-fix/scripts/changes.py).

## Files

- **T#_mask.png**: 8-bit, the size of the window. 0 = paper; 1 = ink that is not text; 2 = text ink; 3 = don't care.
- **Ink** is ink_bins.py's rule: Lab L < 140 of 255 on the paper mask (cufp/N/png_alpha_s4.npy), as in v1. The ink pixels are the same as v1's; only their class changed.
- **T#_words.json**: one entry per word, as in v1 (`reading`, `kind`, `flags`, `angle`, `height`, `length`, `poly`, `aabb`, `snapped`, `touches_line`, `text_px`, `annot_line`). `annot_line` is the line in the v2 annot/T#.txt. `boxes` lists every hand op, v2 ones included.
- **annot/T#.txt**: the hand input, v1's lines plus the v2 edits. Every v2 edit is marked: a `# v2:` comment above a changed word line, a v1 line kept as a `#` comment when it was dropped, and a `# ===== v2 fixes` section at the end with one op per line, each with its reason after `v2:`.
- **work/**: v1's reading tiles (T#_zoom_RC.jpg, scan only, unchanged) and the check tiles (T#_check_RC.jpg) rebuilt from v2: text red, don't care yellow, other ink grey, bin 8 on not-text ink green, word boxes magenta with their annotation line.
- **crops.json**: unchanged.
- How to rebuild: `cd data/sanborn/bench_2026-11-25/text_v1/truth-fix; python -B scripts/build_truth_v2.py T1 T2 T3 T4 T6 T7 [--check]`. With `--noshare` and the v1 annotations it gives v1's masks and words back exactly (0 pixels differ, all words equal; checked).

**Kinds and flags** are v1's: street, house, lotdim, lot, block, owner, bldg, story, pipe, sewer, rail, adj, ditto, other; flags partial, unsure, run, curved, nosnap, g:NAME (see the v1 README in text/inventory/truth/).

## What counts as text (v2)

The proposals of text_first.md section 9, used as defaults until Ben answers:

| | v2 class |
|---|---|
| letters, digits, ' " ° ± ½ & . - ( ), No., ditto marks, story heights | text (2) |
| pipe and sewer labels (6" W. PIPE, 12" SEWER) | text (2); the dashes of the pipe or sewer line beside them are not text |
| hydrant dots and circles, manhole and valve marks (circle with a cross, the bow-tie valve), hook marks, arrows, the X of stables, the asterisk mark | not text (1). In the hand-off codes these are 5 |
| rail ticks, streetcar dashes, lot, block, building, pipe and sewer lines and their dashes | not text (1) |
| ink a glyph shares with a line or another non-text mark it touches | don't care (3). In the hand-off codes this is 4 (shared: owned by the line for sorting, not scored in training) |

**The shared-ink rule (new in v2).** In every 8-connected ink piece that holds both text and not-text ink, the not-text ink within 2 px of text ink and the text ink within 2 px of not-text ink become don't care. Pieces that do not touch are left alone. So a block side running through a row of house numbers stays a side (its pixels are 1), and only the ink where the two touch is not scored. v1 already did this for long lines that leave the word box; v2 does it for every touch, including the ones the hand fixes created. On its own the rule moves 3,855 text px and 4,031 not-text px to don't care (measured, v1 annotations rebuilt with the rule: truth-fix/rebuild_share).

Changes this makes against v1's rules: hydrants were don't care on T7 and are now not text; the valve sign in 35" W. PIPE (T6) was don't care and is now not text (its period stays text); the circle-and-cross on the T4 alley sewer was text and is now not text.

## How v2 was made

1. **Copy and check the builder.** text/inventory/scripts/build_truth.py and common.py were copied to truth-fix/scripts/ (build_truth_v2.py, common.py; only the paths changed). Rebuilt from v1's annotations without the shared-ink rule, they reproduce v1's six masks with 0 differing pixels and identical words.
2. **New hand ops** in build_truth_v2.py, besides v1's EXCL, FORCE, CARE, CARELINE and CAREDIR:
   - `NOTTEXT x1 y1 x2 y2 w`: all ink in the strip is not text (a lot line inside a word box);
   - `FORCELINE x1 y1 x2 y2 w`: all ink in the strip is text (not used in the end);
   - `EXCLCIRC cx cy r`: all ink in the circle is not text (hydrants).
   Ops act in file order after the words, then the shared-ink rule. Line strips were placed with truth-fix/scripts/snapline.py (it snaps a typed segment onto the printed line) and checked on 4-6x zooms.
3. **The verify agent's list** (findings_full.md, skeptic section 4): all fixed; see the changes list (T1 block 14, 154, N, 150, the A corner; T4 119.10', the valve sign; T7 83', 28, 165, 82.66').
4. **Looking again.** Every crop was looked at at 1:1 in 750 x 500 tiles, scan beside truth (truth-fix/scripts/look.py; truth-fix/pics/tile_T#_rRcC.png). Two pointers chose where to zoom:
   - suspects.py: blobs where the finder and bin 8 BOTH disagree with the truth, 30 px or more (about 320 looked at on contact sheets, sheet.py);
   - blue_glyphs.py: glyph-sized pieces the truth calls not text that are not straight strokes (75 looked at). This one does not use the finder or bin 8.
   Every change was decided on 3-8x zooms of the scan (multizoom.py, look.py zoom).

## Changes from v1

118 changes (truth-fix/changes_v2_list.txt, made by changes.py from the two annotation folders; the machine-readable diff and the pixel moves are in truth-fix/changes_v2.json):

| | T1 | T2 | T3 | T4 | T6 | T7 | all |
|---|---|---|---|---|---|---|---|
| word line changed: box moved or grown (its glyphs were partly or wholly not text), or reading | 15 | 6 | 0 | 6 | 3 | 15 | 45 |
| (of these, reading changed) | (1) | | | (3) | | (1) | (5) |
| word added (a missed word, all not text in v1) | 0 | 2 | 0 | 0 | 0 | 1 | 3 |
| line ink in a word box made not text (NOTTEXT, EXCL) | 22 | 4 | 4 | 6 | 2 | 10 | 48 |
| glyph ink made text (FORCE) | 1 | 0 | 0 | 0 | 1 | 2 | 4 |
| marked don't care (CARE, CARELINE) | 4 | 0 | 1 | 2 | 0 | 0 | 7 |
| convention: symbol made not text (EXCL, EXCLCIRC) | 0 | 0 | 0 | 1 | 2 | 3 | 6 |
| v1 op dropped | 1 | 0 | 0 | 0 | 1 | 3 | 5 |

Pixels moved (measured, all six crops): 6,200 not text -> text; 5,871 text -> not text; 4,217 not text -> don't care; 5,090 text -> don't care; 2,570 don't care -> not text; 340 don't care -> text. So about 2.4% of v1's text pixels changed between text and not text, a little more than the verify agent's estimate of 1-2% (estimate).

Readings changed: T1 25.38 -> 6.93 (unsure; read at 8x); T4 23.6" -> 23'6" (twice) and 119.10" -> 119.10'; T7 1.65 -> 165 (unsure; no period visible).

The full list, crop by crop (coordinates are full-plate px; `[v1: ...] [v2: ...]` are the annotation lines):

### T1
- word "25'" (lotdim): box missed the prime  [v1: 1531 1640 1531 1603 16 | 25' | lotdim] [v2: 1537 1642 1535 1588 20 | 25' | lotdim]
- word '4149' (house): box missed the first 4  [v1: 1838 1598 1862 1660 20 | 4149 | house | curved g:4149-47] [v2: 1833 1576 1862 1660 20 | 4149 | house | curved g:4149-47]
- word '25.43' (lotdim): box missed the last glyph at the foot  [v1: 1848 1738 1849 1788 15 | 25.43 | lotdim | unsure] [v2: 1845 1732 1846 1804 16 | 25.43 | lotdim | unsure]
- word "25'" (lotdim): box (nothing to snap to) lay left of the glyphs; prime and right half were non-text  [v1: 1527 1858 1527 1826 18 | 25' | lotdim] [v2: 1538 1862 1537 1818 22 | 25' | lotdim]
- word '25.45' (lotdim): box missed the last glyph at the foot  [v1: 1848 1805 1849 1848 15 | 25.45 | lotdim] [v2: 1845 1807 1846 1867 16 | 25.45 | lotdim | unsure]
- word "16'" (lotdim): box missed the prime at the foot  [v1: 2045 1580 2062 1620 16 | 16' | lotdim | unsure] [v2: 2045 1578 2063 1632 16 | 16' | lotdim | unsure]
- word '202' (lot): box cut off the last 2  [v1: 2208 1729 2250 1729 28 | 202 | lot] [v2: 2208 1729 2276 1729 28 | 202 | lot]
- word '4127' (house): box cut off the top of the 7  [v1: 2890 1848 2890 1775 22 | 4127 | house] [v2: 2890 1848 2890 1757 22 | 4127 | house]
- word '6.93' (lotdim): box lay left of the number (93 was non-text); read 6.93 at 8x, still unsure  [v1: 1868 1868 1902 1868 18 | 25.38 | lotdim | unsure] [v2: 1862 1868 1922 1868 20 | 6.93 | lotdim | unsure]
- word '25.43' (lotdim): box cut off the right side of the glyphs  [v1: 2140 2152 2160 2205 15 | 25.43 | lotdim] [v2: 2143 2144 2165 2210 18 | 25.43 | lotdim]
- word '4120-22-24' (house): box covered only 4120-; -22-24 runs on up to y 1703  [v1: 2995 1902 2998 1815 22 | 4120-22-24 | house | partial unsure] [v2: 2994 1915 2994 1703 24 | 4120-22-24 | house | partial unsure]
- word 'L' (owner): box lay right of the L (the L was non-text and the building top was text)  [v1: 2432 2483 2470 2483 44 | L | owner | g:LANGLAND] [v2: 2396 2472 2434 2472 46 | L | owner | g:LANGLAND]
- word 'A' (owner): box cut off the foot of the left leg  [v1: 2515 2402 2550 2402 46 | A | owner | g:LANGLAND] [v2: 2512 2405 2550 2405 52 | A | owner | g:LANGLAND]
- word '150' (lot): box started 6 px right of the 1 of 150 (it was left as non-text); now from its left edge  [v1: 2435 2251 2475 2251 27 | 150 | lot] [v2: 2425 2251 2475 2251 27 | 150 | lot]
- removed: CARELINE 2400 2260 2520 2260 7 dashed building line through 150  (removed, the strip lay 4 px under the line and took the feet of 150 (the builder finds the solid line itself))
- word "29'" (lotdim): box cut off the right half of the 9  [v1: 2830 2512 2830 2480 16 | 29' | lotdim | partial] [v2: 2836 2514 2836 2476 26 | 29' | lotdim | partial]
- lot line above the 1 of block 14  [NOTTEXT 2512 2282 2516 2306 5]
- lot line through the 1 of block 14 (shared ink)  [CARELINE 2515 2306 2526 2358 5]
- lot line under the 1 of block 14  [NOTTEXT 2524 2356 2528 2372 5]
- the same lot line on through the box of A (LANGLAND)  [NOTTEXT 2528 2370 2542 2440 5]
- lot line above the 4 of block 14  [NOTTEXT 2551 2280 2554 2306 5]
- lot line along the stem of the 4 of block 14 (shared ink)  [CARELINE 2554 2306 2565 2358 5]
- lot line under the 4 of block 14  [NOTTEXT 2564 2356 2568 2380 5]
- building line and dashes over block 14  [NOTTEXT 2553 2304 2600 2304 5]
- lot line above 154  [NOTTEXT 2606 2285 2606 2313 5]
- lot line through the 4 of 154 (shared ink)  [CARELINE 2606 2313 2606 2345 5]
- lot line under 154, beside N  [NOTTEXT 2606 2345 2606 2373 5]
- lot line right of N  [NOTTEXT 2658 2290 2657 2373 5]
- lot line under block 14 and N  [NOTTEXT 2498 2371 2662 2368 7]
- lot-line corner above the A of LANGLAND  [EXCL 2905 2056 2956 2071]
- sewer dashes under 12" SEWER were text  [NOTTEXT 1660 1957 1730 1958 5]
- sewer dashes under 12" SEWER were text  [NOTTEXT 1730 1957 1800 1959 5]
- lot line through the box of 199 was text  [NOTTEXT 2350 1915 2422 1916 5]
- building line under 10 was text  [NOTTEXT 2836 1768 2872 1767 7]
- building top line in the box of 12.21 was text  [NOTTEXT 2138 2219 2168 2219 7]
- dashed lot line beside 59 was text  [NOTTEXT 2551 2192 2551 2252 6]
- dashed lot line right of 61 was text  [NOTTEXT 2762 2190 2762 2242 5]
- dashed lot line left of 61 was text  [NOTTEXT 2707 2192 2707 2242 5]
- dashed lot line through the 0 of 60 was text (the touch is shared)  [NOTTEXT 2667 2195 2667 2245 5]
- strokes of 6, 0, 0 in 1600 were taken as line ink (non-text)  [FORCE 1853 1888 1912 1910]
- dashed lot line beside the story 1 right of 153 was text  [NOTTEXT 2649 2258 2648 2305 4]
- diagonal lot line inside the box of 4134-32-30 was text  [NOTTEXT 2152 2295 2172 2393 5]
- long loop left of 4" W.PIPE, unknown mark (pipe end or symbol): don't care  [CARE 2133 2002 2190 2033]
### T2
- word '2' (story): box cut off the left and the foot of the 2  [v1: 2838 2665 2848 2665 20 | 2 | story] [v2: 2832 2674 2850 2674 22 | 2 | story]
- word "50'" (lotdim): box missed the prime  [v1: 2902 2763 2955 2763 36 | 50' | lotdim] [v2: 2900 2760 2958 2760 44 | 50' | lotdim]
- word "129'" (lotdim): box missed the prime  [v1: 3168 2595 3208 2595 18 | 129' | lotdim] [v2: 3166 2594 3222 2594 22 | 129' | lotdim]
- word 'R' (owner): box cut off the bowl of the R under the rail line  [v1: 3202 2808 3242 2808 42 | R | owner | g:?R'S unsure] [v2: 3204 2801 3248 2801 50 | R | owner | g:?R'S unsure]
- word '215' (lot): box was upright over 21 only; the 5 right of the lot line was non-text  [v1: 3011 3350 3011 3320 18 | 215 | lot | unsure] [v2: 2998 3342 3046 3335 26 | 215 | lot | unsure]
- word '218' (lot): box missed the 2  [v1: 2805 3442 2835 3442 26 | 218 | lot] [v2: 2783 3442 2835 3442 26 | 218 | lot]
- word "150'" (lotdim): added, a missed word that v1 left as non-text  [v2: 3166 2862 3204 2848 26 | 150' | lotdim]
- word '317' (lot): added, a missed word that v1 left as non-text  [v2: 2697 2915 2714 2915 30 | 317 | lot | partial]
- lot line under 28.95' and through CITY was text  [NOTTEXT 2757 3393 2902 3312 5]
- dashed lot line beside 60.07 was text  [NOTTEXT 2840 3420 2840 3480 4]
- dashed lot line through the box of AMERICAN was text  [NOTTEXT 3610 3150 3608 3220 5]
- vertical lot line between the I and T of CITY was text  [NOTTEXT 2839 3342 2839 3405 4]
### T3
- dash of a dashed line left of the 39 was text  [NOTTEXT 10268 2619 10305 2595 6]
- small dash left of the 39 was text  [EXCL 10248 2620 10264 2633]
- dash between the 3 and 9 of 39: hyphen or a dash of the corridor's dashed line, unsure  [CARE 10318 2634 10350 2656]
- diagonal lot line inside a word box was text  [NOTTEXT 9149 3062 9176 3127 5]
- building wall inside the box of the story 1 was text  [NOTTEXT 9213 3219 9231 3263 4]
### T4
- word "23'" (lotdim): box lay above the glyphs, which are turned about 25 degrees (all non-text)  [v1: 2460 1150 2492 1150 16 | 23' | lotdim] [v2: 2460 1162 2494 1178 18 | 23' | lotdim]
- word '23\'6"' (lotdim): box missed the 3 and 2 at the foot; the mark after 23 is a prime  [v1: 2132 1485 2132 1452 18 | 23.6" | lotdim] [v2: 2126 1518 2126 1450 20 | 23'6" | lotdim]
- word '23\'6"' (lotdim): the mark after 23 is a prime (as on the word above); box missed the 3 and 2 at the foot  [v1: 2130 1565 2130 1532 16 | 23.6" | lotdim] [v2: 2126 1597 2126 1528 20 | 23'6" | lotdim]
- word '18.72' (lotdim): box (nothing to snap to) lay above the number, which was non-text  [v1: 2465 1533 2502 1533 16 | 18.72 | lotdim] [v2: 2459 1549 2503 1549 20 | 18.72 | lotdim]
- word "119.10'" (lotdim): box missed the two 1s at the foot and the prime at the top (verify: 119.10' partly non-text); the mark is a prime  [v1: 2973 1712 2973 1655 18 | 119.10" | lotdim | unsure] [v2: 2966 1731 2966 1649 22 | 119.10' | lotdim | unsure]
- word "25'" (lotdim): box cut off the 5  [v1: 2963 1885 2963 1862 14 | 25' | lotdim] [v2: 2967 1913 2962 1876 22 | 25' | lotdim]
- circle-and-cross symbol on the alley sewer was text (verify: valve symbol); convention: not text  [EXCL 2419 1800 2446 1832]
- stem of the Y of ALLEY runs into the lot line (shared ink)  [CARE 2436 1481 2448 1491]
- lot line through D, I and V of SUBDIV'N was text (crossings become shared)  [NOTTEXT 2597 1372 2702 1368 6]
- dashed lot line left of 12' was text  [NOTTEXT 3275 1712 3275 1768 4]
- building wall below the last F of WOLFF was text  [NOTTEXT 2315 1532 2315 1582 5]
- lot line between 5 and 6 was text  [NOTTEXT 2517 1740 2517 1785 4]
- building line under 75.4' was text  [NOTTEXT 2716 1458 2748 1458 5]
- dash of the street line by McMICKEN was text  [NOTTEXT 3479 1792 3506 1811 5]
- the 2 of 18.72 lies along the triangle's diagonal: shared ink  [CARE 2490 1538 2506 1559]
### T6
- word '35"W.PIPE' (pipe): box stopped before PE (non-text)  [v1: 4258 1898 4428 1898 32 | 35"W.PIPE | pipe] [v2: 4258 1898 4478 1898 32 | 35"W.PIPE | pipe]
- removed: CARE 4330 1850 4372 1895 valve or hook symbol inside the pipe label  (convention: valve and hook marks are not text; replaced by the EXCL boxes in the v2 section)
- word "80'" (lotdim): box missed the prime  [v1: 3935 1982 3968 1982 20 | 80' | lotdim] [v2: 3933 1976 3976 1976 36 | 80' | lotdim]
- word '331' (lot): box cut off the last 1  [v1: 4348 1932 4382 1932 18 | 331 | lot] [v2: 4348 1932 4400 1932 20 | 331 | lot]
- valve symbol above the pipe line in 35" W. PIPE, not text (convention)  [EXCL 4334 1844 4388 1872]
- valve stem, cross and hook below the pipe line in 35" W. PIPE, not text (its hook was text)  [EXCL 4338 1872 4380 1912]
- the period of W. sits under the valve stem; it stays text  [FORCE 4346 1900 4355 1911]
- sewer line dashes beside 15" SEWER were text  [NOTTEXT 4220 1695 4219 1860 5]
- dashed lot line beside 87'6" was text  [NOTTEXT 4642 2040 4641 2200 4]
### T7
- word '536' (house): box cut off the 6  [v1: 1675 3595 1715 3595 22 | 536 | house | partial] [v2: 1675 3595 1747 3595 24 | 536 | house | partial]
- word "83'" (lotdim): box lay 10 px left of the glyphs, which were non-text (verify)  [v1: 1988 3858 1988 3822 14 | 83' | lotdim] [v2: 2002 3858 2001 3819 20 | 83' | lotdim]
- word '39"' (lotdim): box missed the double prime above  [v1: 2572 3570 2598 3570 16 | 39" | lotdim | unsure] [v2: 2571 3565 2601 3565 38 | 39" | lotdim | unsure]
- word '37' (lot): box cut off the left half of the 3  [v1: 2692 3811 2725 3811 28 | 37 | lot] [v2: 2674 3811 2725 3811 30 | 37 | lot]
- word '12"SEWER' (sewer): box covered SEWER only; the 12" below it was non-text  [v1: 2980 3790 2980 3685 22 | 12"SEWER | sewer] [v2: 2979 3838 2980 3685 22 | 12"SEWER | sewer]
- word "23'" (lotdim): box missed the 2  [v1: 2845 3725 2878 3725 18 | 23' | lotdim] [v2: 2820 3728 2870 3728 22 | 23' | lotdim]
- word "16½'" (lotdim): box cut off the half  [v1: 3032 3728 3058 3728 18 | 16½' | lotdim] [v2: 3032 3722 3076 3722 24 | 16½' | lotdim]
- word "82.66'" (lotdim): box missed the 8 at the foot and the prime at the top (verify)  [v1: 1713 3875 1713 3815 16 | 82.66' | lotdim | partial] [v2: 1716 3895 1714 3813 22 | 82.66' | lotdim | partial]
- word "82.66'" (lotdim): box missed the top 6 and the prime  [v1: 1718 4095 1718 4045 16 | 82.66' | lotdim] [v2: 1716 4096 1716 4021 22 | 82.66' | lotdim]
- word "20'" (lotdim): box missed the prime  [v1: 1688 4162 1715 4162 20 | 20' | lotdim | partial] [v2: 1688 4158 1716 4158 32 | 20' | lotdim | partial]
- word '165' (lotdim): no period is visible; read 165  [v1: 2136 3965 2136 3922 14 | 1.65 | lotdim | unsure] [v2: 2131 3965 2131 3922 18 | 165 | lotdim | unsure]
- word "28'" (lotdim): box missed the prime  [v1: 2295 4158 2325 4158 20 | 28' | lotdim] [v2: 2293 4155 2328 4155 32 | 28' | lotdim]
- word "90'" (lotdim): box lay left of the 9 and 0 (non-text)  [v1: 2712 4055 2712 4015 14 | 90' | lotdim] [v2: 2726 4063 2722 4018 26 | 90' | lotdim]
- word "43.74'" (lotdim): box cut off the 4 and the prime  [v1: 3032 4156 3095 4156 20 | 43.74' | lotdim] [v2: 3032 4157 3104 4157 32 | 43.74' | lotdim]
- word '12"SEWER' (sewer): box covered SEWER only; the 12" below it was non-text  [v1: 2980 4315 2980 4202 22 | 12"SEWER | sewer] [v2: 2981 4370 2980 4202 22 | 12"SEWER | sewer]
- lower left of the 8 of 28 inside the building corner was non-text (verify)  [FORCE 2118 3914 2126 3928]
- base of the 2 of the upper 82.66' was non-text (it touches the lot line)  [FORCE 1699 3856 1726 3884]
- hydrant between 504 and 500, not text (convention; its right third was text)  [EXCLCIRC 2833.5 3611 16]
- hydrant inside 521-19 17-515, not text (convention)  [EXCLCIRC 2415.5 4341 16]
- hydrant over 505-03-501, not text (convention; the CARE box also took the tops of 0 and 3)  [EXCLCIRC 2819 4323 15.5]
- building line along the top of block 28 was text  [NOTTEXT 2385 3874 2500 3871 5]
- building wall above the 8 of block 28 was text  [NOTTEXT 2472 3874 2472 3893 4]
- building line right of the 8 of block 28 was text  [NOTTEXT 2480 3921 2500 3921 5]
- building line left of the 8 of block 28 was text  [NOTTEXT 2440 3921 2450 3919 5]
- building wall inside LONGWORTH'S was text  [NOTTEXT 2350 3912 2350 3946 4]
- sewer line dashes beside SEWER (left) were text  [NOTTEXT 1808 4340 1807 4480 5]
- sewer line dashes beside SEWER (right) were text  [NOTTEXT 2990 3690 2990 3850 5]
- sewer line dashes along the house numbers were text  [NOTTEXT 2989 3850 2989 4000 5]
- sewer line dashes along the house numbers were text  [NOTTEXT 2989 4000 2987 4230 5]
- end of a building line at the first 2 of BLOCK 22 was text  [NOTTEXT 2600 3941 2625 3941 5]
- word '3' (story): added, a missed word that v1 left as non-text  [v2: 1878 4158 1896 4158 28 | 3 | story]
- removed: CARE 2815 3595 2842 3622 hydrant between 504 and 500  (convention: hydrants are not text (code 5); the CARE boxes below are replaced by EXCLCIRC in the v2 section)
- removed: CARE 2402 4322 2432 4355 hydrant inside 521-19 17-515  (convention: hydrants are not text (code 5); the CARE boxes below are replaced by EXCLCIRC in the v2 section)
- removed: CARE 2800 4312 2830 4348 hydrant over 505-03-501  (convention: hydrants are not text (code 5); the CARE boxes below are replaced by EXCLCIRC in the v2 section)

## Scoring: text_v1/code/score_text.py

```
cd data/sanborn
python -B bench_2026-11-25/text_v1/code/score_text.py MASK (--codes 2,3,4 | --binary) [--truth DIR] [--crops T1,T2] [--group NAME=T1,T2] [--out FILE.json]
```

- MASK is a PNG path with `{plate}` and/or `{crop}` in it; the mask is either plate-sized (the window is cut out) or crop-sized. `--codes` says which values are text (finder v1: 2,3,4; bin 8 of unet_data/N_bins.png: 8; the hand-off codes: 2,3), `--binary` takes any value above 0 as text. `--truth` defaults to this folder (v2).
- Scored on the ink the truth calls 1 or 2: precision, recall and F1 of text pixels (pools add tp, fp and fn over crops); non-text ink called text (fp over all truth-1 pixels, split into inside a word box grown 3 px and in the open); recall by word kind (the truth-2 pixels inside each word's box, summed by kind) and words found (half or more of their pixels); don't-care pixels skipped (how many, and how many the mask calls text); text called on paper; for code masks, a table of mask value against truth class.
- **It reproduces the verify agent exactly on v1** (measured; truth-fix/scores/reproduce_verify_v1.txt): tp, fp and fn are the same on all 6 crops for the finder and for bin 8 as verify/out/rescore_finder_out.json. Pooled: finder P 0.9486, R 0.8684, F1 0.9067; bin 8 P 0.8541, R 0.8465, F1 0.8502. Recall by kind also matches the verify report (finder / bin 8: street 0.81 / 0.985, house 0.88 / 0.965, block 0.64 / 0.85, adjoining sheet 0.28 / 0.92).
- A crop-sized binary mask gives the same numbers as the plate-sized code mask it was cut from (checked on T1 and T4).

**Baselines on v2** (measured, score_text.py; truth-fix/scores/v2truth_*.txt and .json):

| | v1 P / R / F1 | v2 P / R / F1 | non-text ink called text, v1 -> v2 |
|---|---|---|---|
| finder (codes 2,3,4), all 6 crops | 0.9486 / 0.8684 / 0.9067 | 0.9600 / 0.8804 / 0.9185 | 3.55% -> 2.75% |
| finder, T1-T3 (tuned on) | 0.9538 / 0.9059 / 0.9293 | 0.9711 / 0.9214 / 0.9456 | 3.49% -> 2.17% |
| finder, T4, T6, T7 | 0.9439 / 0.8368 / 0.8871 | 0.9500 / 0.8460 / 0.8950 | 3.59% -> 3.19% |
| bin 8, all 6 crops | 0.8541 / 0.8465 / 0.8502 | 0.8608 / 0.8546 / 0.8577 | 10.90% -> 10.36% |
| bin 8, T1-T3 | 0.8216 / 0.8986 / 0.8584 | 0.8324 / 0.9085 / 0.8688 | 15.52% -> 14.52% |
| bin 8, T4, T6, T7 | 0.8870 / 0.8026 / 0.8427 | 0.8894 / 0.8094 / 0.8475 | 7.38% -> 7.20% |

Recall by kind on v2, finder / bin 8 (pixels; words found in brackets are of the finder): street 0.81 / 0.99 (20/22), house 0.89 / 0.97 (96/98), block 0.72 / 0.89 (5/7), adjoining sheet 0.26 / 0.92 (0/1), lot 0.94 / 0.77, lotdim 0.91 / 0.79, story 0.94 / 0.71, ditto 0.75 / 0.47, owner 0.77 / 0.78, pipe 0.86 / 0.80, sewer 0.82 / 0.87, rail 0.90 / 0.97.

How much of the change is the shared-ink rule (measured, v1 annotations rebuilt with the rule only, truth-fix/scores/v1share_*.json): finder F1 0.9067 -> 0.9096, bin 8 0.8502 -> 0.8528. The hand fixes add the rest: finder -> 0.9185 (+0.0089), bin 8 -> 0.8577 (+0.0049).

## Known limits

- **The search leans towards the two methods.** Most fixes were found where the finder and bin 8 both disagreed with the truth. That raises both methods' scores a little, the finder's more (F1 +0.0089 from the fixes against +0.0049 for bin 8). Errors that both methods share are found only by the 1:1 look and by blue_glyphs.py, which does not use them; that is how the T4 18.72, T7 536, 16½, 43.74', the story 3 at 1878,4158 and the T2 215 were found late. Others of that sort may remain (estimate: a few hundred pixels per crop, under 1% of text px).
- **Thin errors are not seen at 1:1.** The 1:1 look catches whole glyphs and line pieces, not 1-2 px edges. The shared-ink rule covers most edge disagreements where text touches lines.
- **Unsure marks, each with a decision recorded in the annotation:** the dash between the 3 and 9 of the adjoining sheet number on T3 (don't care); a long loop left of 4" W.PIPE on T1 (don't care); the asterisk on T7 and the arrows on T7 (not text, as marks); the colon-like dots before some story figures on T1 (left not text: they line up with dashed lot lines).
- **Readings** flagged unsure (86 words) may still be wrong in a figure. Only the readings above were changed; the rest were not re-read.
- **Line stubs and dashed lines** inside word boxes that were not seen remain text; v2 fixed 48 such places.
- v1's known limits still hold: faint ink lighter than L 140 is in no class; run boxes cover whole rows of house numbers.

## Files of the fix (text_v1/truth-fix/)

- scripts/build_truth_v2.py, common.py: the builder (v1's, plus NOTTEXT, FORCELINE, EXCLCIRC and the shared-ink rule).
- scripts/snapline.py: snaps a typed line segment onto the printed line.
- scripts/look.py, multizoom.py: tiles and zooms, scan beside truth. scripts/suspects.py, sheet.py: where the finder and bin 8 both disagree. scripts/blue_glyphs.py: glyph-sized not-text pieces.
- scripts/changes.py: the v1 -> v2 diff (changes_v2.json, changes_v2_list.txt).
- scores/: the score_text.py runs on v1 and v2, and reproduce_verify_v1.txt.
- rebuild_v1/ (v1 rebuilt, identical), rebuild_noshare/, rebuild_share/ (v1 annotations with the shared-ink rule only).
- pics/: the tiles, sheets and zooms looked at.
- _second_copy/: a second copy of the scripts, the annotations and score_text.py.
