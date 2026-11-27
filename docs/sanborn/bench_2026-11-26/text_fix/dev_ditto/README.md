# dev_ditto (26 Nov 2026): dev truth for ditto marks

- `truth/`: the targeted ditto truth, 51 crops, 200 ditto words on 20 plates. Read `truth/README.md` first.
- `negatives/`: 73 windows on tick-like marks that are not dittos (rail ticks, dashes, hooks, line ends). `negatives/README.md`.
- `scores/`: score_text.py runs (`ditto_<method>.json`, `neg_<method>.json`, `score_text_runs*.txt`) and
  `summary.txt` / `summary.json` (recall by scale, style and size; finder codes; negatives by type). `*_v1.*` = the
  first version of the truth (before the second pass).
- `scripts/`: everything used (see each docstring). Run from data/sanborn.
- `choose/`: the random windows (seeds, every draw, the 132 looked at and what each held).
- `runs/`: finder2 and finder3 run here (unchanged code) on the plates with no stored mask: 2 3 4 12 19 26A 48 57 64A
  74 86 94; `runs/cut/` holds each method's mask cut to every crop window (made after the truth was frozen).
- `pics/`: search views, candidate sheets, the second-pass sheets (`pairs/`), and `methods/` (scan | finder3 | finder2 |
  bin 8 for every ditto, and for every negative a method calls text).
- `truth_v1_frozen/`, `*.sha1`: the first version and checksums.
- `_second_copy/`: scripts, annotations, crops, words, masks, choose lists, verdicts, scores and READMEs.
