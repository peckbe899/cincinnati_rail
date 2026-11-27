# Ditto look-alikes: negative set (26 Nov 2026)

73 small windows (64 x 64 px), each centred on a tick-like mark that is NOT a ditto. Same format as ../truth
(`crops.json` with `target: "negative"`, `scope: "window"`: the whole window is scored and all its ink labelled;
`<id>_mask.png`, `<id>_words.json`, `annot/`). The mark is a word of kind `negative` (flag `neg:TYPE`); its ink is 1.
Any text in the window is labelled 2 as usual. All numbers MEASURED.

| type | marks | from |
|---|---|---|
| rail tick | 27 | plate 44, Ben's railroad tracks (picks22_guided/22-44/rail_ben.json, read only). Plate 5 has no railroad track in rail_ben.json. |
| dash | 37 | dashed and dotted lines, hatching, the thin dashed line beside the 44 streetcar track; 12 plates |
| hook | 7 | 1 drawn by the samplers; 6 = every hook mark in one drawn window (93A rank 3) |
| line end | 2 | ends of straight lines |

Plates: 44 (28), 93A (8), 3, 12, 57 (5 each), 86 (4), 19, 30, 90, 47, 48 (3 each), 60B (2), 64A (1). No sealed plate,
no window near H1-H4 or near a ditto truth word (60 px).

## How they were drawn

1. `scripts/neg_sample.py` (seeds `neg-SAMPLER-PLATE`): random rail crossings and streetcar points on 44 and 5 from
   Ben's tracks; random isolated thin pieces, dashes with a collinear partner, and skeleton ends of large pieces on 12
   plates. 235 draws, 124 candidates (`choose/candidates.json`, sheets `choose/sheet_*.png`).
2. Judged by eye on the scan: 25 kept, 2 of them dropped later on the labelling look (centre on text), so 23 (`choose/verdicts_v1.txt`). The isolated and line-end samplers drew mostly
   text, so
3. `scripts/neg_sample2.py` (seeds `neg2-...`): stricter samplers (single-run rail crossings, a bar inside a dashed
   line with partners on both sides, straight line ends). 1700 draws, 76 candidates, 44 kept (`verdicts_v2.txt`).
4. `scripts/neg_crops.py` makes the windows; hooks are added by hand boxes (all six in window 93A rank 3).


## Scores (scores/neg_*.json, scores/summary.txt)

Share of the look-alike mark ink called text (marks with half or more of their ink called text):

| | bin 8 | finder2 | finder3 |
|---|---|---|---|
| all 73 | 0.031 (3) | 0.051 (4) | 0.051 (4) |
| rail ticks 27 | 0.000 (0) | 0.003 (0) | 0.003 (0) |
| dashes 37 | 0.005 (1) | 0.022 (1) | 0.022 (1) |
| hooks 7 | 0.305 (2) | 0.439 (3) | 0.439 (3) |

Pictures: pics/methods/negatives_hit_01.png (every mark any method calls text) and negatives_sample_01.png.
Check pictures: check/N##_overview.png, check/negsheet_*.png, check/neg_text_check.png.
