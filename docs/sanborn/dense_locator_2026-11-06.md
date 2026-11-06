# Dense controls for the 1922 plates: the automatic locator (6 November 2026)

Ben's first ruling of 6 November asked for every 1922 plate to be fitted by thin-plate spline on dense, automatically
located controls: every OSM crossing of two unchanged streets, found on the scan the way the 1912 rebuild found its
controls (`ground/1912/rebuild/controls.py`, corridor fit). This note is what came of it. The locator did not work on
the Sanborn plates, and the plates hold fewer crossings than the plan assumed. Ben's second ruling (rule 12 in
`RULES.md`) replaces it: every plate is fitted on the complete set of named crossings, each read by hand.

The draft locator is kept at `tools/sanborn/dense/locate.py` (not used by anything).

## How many crossings there are

OSM crossings of two or more differently named streets (highway primary to residential, from the same five extracts
`cufp/fit.py` reads, crossings of the same names within 5 m merged) whose position under the plate's current model
falls inside the plate's mapped area (and on the page side of the fold on the halves). Realigned and renamed streets are
counted apart, as rule 3 lists them. "Hand picks" is the number of controls in the plate's current model.

| Plate | On the plate | Realigned | Renamed | Eligible | Hand picks | km² |
|---|---|---|---|---|---|---|
| 22-34L | 23 | 0 | 0 | 23 | 16 | 1.77 |
| 22-37L | 47 | 13 | 0 | 34 | 20 | 1.84 |
| 22-37R | 28 | 7 | 0 | 21 | 15 | 1.78 |
| 22-34R | 59 | 0 | 0 | 59 | 49 | 1.77 |
| 22-16R | 23 | 0 | 0 | 23 | 15 | 0.44 |
| 22-35N | 61 | 8 | 0 | 53 | 30 | 2.90 |
| 22-38 | 97 | 10 | 0 | 87 | 63 | 3.01 |
| 22-66 | 153 | 0 | 0 | 153 | 96 | 3.05 |
| 22-67 | 128 | 0 | 17 | 111 | 70 | 2.98 |
| 22-68 | 109 | 2 | 0 | 107 | 68 | 3.24 |
| 22-69 | 98 | 0 | 19 | 79 | 43 | 3.24 |
| 22-70 | 102 | 0 | 21 | 81 | 74 | 3.11 |
| 22-82A | 131 | 5 | 16 | 110 | 94 | 3.10 |
| 22-83A | 58 | 0 | 4 | 54 | 40 | 1.70 |
| 22-75 | 86 | 0 | 12 | 74 | 47 | 3.15 |
| 22-76 | 158 | 5 | 23 | 130 | 117 | 3.02 |
| 22-26A | 73 | 0 | 10 | 63 | 49 | 3.13 |
| 22-26B | 30 | 0 | 0 | 30 | 11 | 0.91 |
| 22-29 | 85 | 0 | 3 | 82 | 72 | 2.55 |
| 22-31 | 59 | 0 | 5 | 54 | 31 | 2.92 |
| 22-33 | 84 | 0 | 1 | 83 | 62 | 2.74 |
| **All 21** | **1,692** | **50** | **131** | **1,511** | **1,082** | |

So a plate has 21 to 153 eligible crossings (72 on average), not several hundred, and the hand picks already cover
about 72% of them. Renamed streets were left out of "eligible" here because the first ruling said so; rule 3 aliases
them, so they count again under rule 12.

## The four versions tried, on plate 22-66

Plate 22-66 (Corryville, 153 eligible crossings, 96 hand picks). Each version was scored against the hand picks it shares
crossings with: the distance in metres between the located crossing and the hand pick. The baseline is the plate's
current model with no image work at all: per street, its prediction lies 0.66 m (median) from the hand pick, 70% within
1 m, 9 of 179 street arms over 3 m (the model was fitted to these picks, so this flatters it, but any locator has to beat
it to be worth using).

1. **The 1912 method as written.** Long dark strokes (lettering and dashes removed as strokes under 20 m), distance from
   every pixel to the nearest stroke, the crossing's OSM centre lines slid over +-15 m to the shift where the mean
   distance under them peaks; kept if one candidate (second peak under 0.80 of the best), at least 80% of the samples
   1 m or more from a stroke, and pinned. Result: **0 of 153 kept** (91 two candidates, 49 best at the edge of the
   search, 7 not pinned, 5 low confidence). With the thresholds opened, the matches sat about 6 m (median) from the hand
   picks, 2-17 m in a sample of 26.
2. **A whole-crossing template.** Each street as two edge lines that stop at the other street's corridor (the block
   corners), the corridor interiors scored as paper, each street's width searched over 6-30 m. Thresholds opened:
   150 located, **6.7 m median, 14.5 m at 90%** (87 shared with hand picks). Adding a block-side band (content just
   outside each edge) and moving the interior penalty to colour: 5.7-8.9 m median, 13.5-15.9 m at 90%, over five
   weightings.
3. **The street network as large paper regions.** Paper (neither black ink nor colour), the block outlines sealed,
   split into connected regions; regions 80 m or longer taken as streets, closed over pipes and lettering; then the 1912
   centring score on that mask. Thresholds opened: 93 located (53 more had their best at the edge of the search),
   **6.4 m median, 12.7 m at 90%** (59 shared).
4. **Profiles across each street.** For each street arm, the scan straightened along the OSM line (10-45 m from the
   crossing) and summed along the street, then the corridor read from the profile. Tested on the 179 street arms at hand
   picks:
   - the widest pair of strong lines with paper between: **4.2-6.2 m median**, 13-25% within 1 m;
   - lines typed as block edges by block content (lot lines across, colour) on one side only: at the strictest
     setting 23 of 179 found, 0.54 m median but 7 of the 23 over 3 m; looser, 95 found, 1.8 m median, 44 over 3 m;
   - the street as a valley in ink-and-colour density, centred between the half-height edges: at best 87 of 179 found,
     **1.5 m median, 27 over 3 m**.

None comes near the baseline, and none keeps its gross errors (over 3 m) under a few per cent, so a TPS fitted on them
would be pulled off by them. Part 2 was not run on any of them.

## Why a Sanborn street defeats a 1912-style matcher

The 1912 topographic sheets draw a street as two black lines with nothing between them, and the blocks as empty paper
(contours are brown and filtered out). A corridor fit there is well posed: the open space between the lines is the
street. A 1922 Sanborn plate draws the opposite way round:

- **The street is full of linework.** Water mains are solid lines along the street, near but not at its middle, labelled
  `6" W. PIPE`; sewers are dashed lines beside them (`12" SEWER`); house numbers are printed along both block lines,
  inside the street; the street name is lettered down the middle. A centring score sees the pipe as an edge, and the
  best fit is half the street, the open band between one block line and the pipe (seen on Eden Avenue at Daniels
  Street: a 9 m corridor chosen for a 20 m street, 6 m off).
- **The blocks are often open paper.** Yards and vacant lots are blank except for thin lot lines, so the distance to
  the nearest line is often larger inside a block than in the street. On plate 66 the street centres scored lower
  than the yards beside them.
- **Lines parallel to the street are everywhere.** Block lines, building walls, rear lot lines, pipes and the
  coloured fire-limit bands all run along the street, so pairs of lines at plausible street widths are found on both
  sides of the true corridor.
- **Lettering looks like lot lines.** Street names and house numbers in the corridor give the same short cross-strokes
  as lot lines in a block, so "block content" cannot be told from "street with lettering" by ink alone. Colour helps
  only where the block has buildings.
- **Some streets carry long straight index lines** (the key-map division lines) through their middle.

A reader, human or agent, sorts these out at a glance from the printed words and the drawing's conventions. A matcher
working on ink and colour would need those conventions taught to it, plate by plate, and checked against the hand picks,
which would then no longer be an independent check.
