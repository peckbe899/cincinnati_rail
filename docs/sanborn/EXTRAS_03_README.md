# extras_03

Recovered 6 November 2026 for the two scripts asked for: `arcs/fitarcs.py` and `deck/xs.py`. Neither original survives: the Topography workspace was reset, and neither was in extras_01 or extras_02.

## What is here

- `arcs/fitarcs_deck_port.js`: the curve fitter as it runs in the Mill Creek Deck page (artifact L81dVQSV8THSWai2LhZhcv, version 1793213425-9636, `index.html` lines 412-579, copied unchanged). The log says this port follows the same rules as `fitarcs.py` and gives identical results on all 39 lines (Relief_Maps_Log 10ze.2 and 10ze.6). `FA.fit(points)` runs on its own, in the browser or in Node (`require('./arcs/fitarcs_deck_port.js').FA`). Input: a list of [E, N] points in metres. Output: `{verts, k, curves}`, where `k` gives a control point for each curved piece. `fitSource()` is included only for reference; it needs the page's `vertsOf` and `ctrlOf` helpers.

## Not recovered

- `arcs/fitarcs.py` (14,820 bytes, 15 October): the Python original that `transit/build_transit.py` and `rer1023/apply.py` used.
- `arcs/fitarcs.js` (14,407 bytes): the workspace's own JS file. The page block may differ from it in wrapping.
- `deck/xs.py` (749 bytes, 10 October, 18:09) and its output `deck/xs_v1.json`: no copy exists anywhere. They belong with the 10 October deck georeferencing scripts (Relief_Maps_Log 10k, most likely).
