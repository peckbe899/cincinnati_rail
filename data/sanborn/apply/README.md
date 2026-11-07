# Applying the 1922 plate models, 7 November 2026

Ben's ruling (7 November): `fwd_complete.pkl` for every plate but 37L and 37R, `fwd_local3.pkl` for those two; no refit. Run by `apply.py` (stages in its docstring), which routes the pipeline scripts in `tools/sanborn` to the new models without changing them.

## What was done

- **Inverse grids** (`inv/`, 2 m, world to plate pixel, from each new model): round trip at the controls within 0.4 px on every plate (`inv/report.json`; 37L/37R checked at their own controls, 0.2 px).
- **1904 crossings** re-matched to the 1922 positions (`cuf/x1904.py`, 86 frames): 360 of 830 matched, as before; median 1904-1922 offset 3.64 -> 3.56 m.
- **Re-bend**: all 86 frames bent onto 1922 solved again together (`cuf/tps1922.py`; `lph/tps.pkl`, `cuf/tps1922_report.json`).
- **Street sets**: the 16 plate sets (c22, c38 and the 14 numbered plates) taken out newest first and rebuilt in order, using Ben's current layout (`hub/seed/deck/layout.json`, copied to `dbread/deck/layout.json`). After each set's build its features got back their ids: streets 710 carried, 10 new; blocks 706 carried, 22 new. `basin.json` installed in `hub/sites/deck`.
- **Tiles**: `hub/sites/deck/tiles_22` re-composited tile by tile, plates in `cuf/plates.py` order, deepest inside its plate wins (196 tiles; one edge tile, 710656_4336640, no longer holds any plate). Out of git (the `.webp` tiles); index and overview in git.

## Ben's layout

Every id in his layout that the page had is still there, with the same name (0 missing, 0 renamed). Ten had no rebuilt counterpart and are kept as they were, with `kept_for_edit` set: each carries his own geometry or his deletion, which the page draws in its place:

- SR0018 Elland Avenue (c68): his edit del, into
- SR0051 Ridgeway Avenue (c68): his edit del, into
- SR0061 Vine Street (c68): his edit del, into
- SR0062 Vine Street (c68): his edit del, into
- SN0037 Norwood Avenue (c82A): his edit c, mg, w
- SN0037a Norwood Avenue (c82A): his edit c, del
- SO0009 Harris Avenue (c83A): his edit c
- SO0009a Harris Avenue (c83A): his edit c, del

SR0018 and SR0051 were already listed twice on the page before the apply; they still are (SR0017's duplicate is gone).

### His streets whose base line moved, largest first

Every one of them carries his own line (`c`) or his deletion (`del`), so none of them moves on the page: the move is in the base line underneath.

| Id | Street | Set | Mean move m | Max move m | His edit |
|---|---|---|---|---|---|
| SY0021 | Floral Avenue | c76 | 0.28 | 28.21 | c, mg, w, wv |
| SO0017 | Pine Street | c83A | 0.66 | 15.62 | c |
| SR0017 | Elland Avenue | c68 | 3.02 | 13.79 | c, mg |
| SN0035 | Montgomery Pike | c82A | 0.66 | 12.86 | del, into |
| SN0053 | Wesley Avenue | c82A | 0.8 | 12.01 | c |
| SY0041 | Montgomery Road | c76 | 0.52 | 11.09 | c |
| SK0030 | Ludlow Avenue | c38 | 2.31 | 11.03 | c |
| SK0051 | Vine Street | c38 | 3.39 | 9.69 | c, k |
| SK0011 | Evanswood Place | c38 | 2.2 | 9.04 | c |
| ST0003 | Billings Street | c69 | 0.95 | 8.46 | c |
| SY0022 | Forest Avenue | c76 | 0.68 | 6.2 | del, into |
| SP0013 | Bethesda Avenue | c66 | 2.73 | 6.2 | c |
| SN0043 | Sherman Avenue | c82A | 0.74 | 5.95 | c |
| SX0045 | Victory Boulevard | c75 | 1.57 | 4.84 | c |
| SO0016 | Park Avenue | c83A | 2.14 | 4.81 | c, jo, w |
| SO0011 | Kenilworth Avenue | c83A | 1.85 | 4.68 | c, jo |
| SK0020 | Interwood Avenue | c38 | 1.77 | 4.24 | c, mg |
| SO0014 | Norwood Avenue | c83A | 0.28 | 3.9 | del, into |
| SC0015 | Joselin Avenue | c22 | 1.54 | 3.81 | c |
| SN0031 | Marion Avenue | c82A | 0.51 | 3.32 | c |
| SX0050 | Woodburn Avenue | c75 | 1.51 | 2.89 | del, into |
| SN0044 | Smith Road | c82A | 0.99 | 2.62 | c, mg |
| ST0049 | Woodburn Avenue | c69 | 0.79 | 2.62 | c, mg |
| SN0034 | Montgomery Avenue | c82A | 0.78 | 2.54 | c, mg, w |
| SN0022 | Lafayette Avenue | c82A | 0.9 | 2.34 | c |
| SN0038 | Park Avenue | c82A | 0.95 | 2.21 | del |
| SY0047 | Smith Road | c76 | 0.98 | 2.19 | del, into |
| SN0013 | Floral Avenue | c82A | 0.76 | 2.1 | del, into |
| SN0030 | Maple Avenue | c82A | 0.39 | 2.1 | c |
| SN0012 | Elm Avenue | c82A | 0.21 | 2.02 | c |
| SR0019 | Elland Circle | c68 | 0.99 | 1.84 | c, w |
| SN0045 | Station Avenue | c82A | 0.59 | 1.51 | c |
| SN0010 | Crown Street | c82A | 0.47 | 1.43 | c |
| SO0001 | Ash Street | c83A | 0.59 | 1.36 | c |
| SN0014 | Foraker Avenue | c82A | 0.32 | 1.36 | c |
| SC0021 | Riddle Road | c22 | 0.64 | 1.3 | c |
| SO0007 | Forest Avenue | c83A | 0.37 | 1.24 | c, mg |
| SO0019 | Robertson Road | c83A | 0.22 | 1.1 | c |
| SM0252 | Vine Street | ma | 0.16 | 1.0 | del, into |
| SO0008 | Harper Avenue | c83A | 0.27 | 0.95 | c |
| SR0002 | Albany Avenue | c68 | 0.22 | 0.81 | c |

## Seams (`reports/2026-11-07_seams_applied`, against `reports/2026-11-06_seams`)

| | n | Median m | 90% m | Max m | Over 10 m | Over 20 m |
|---|---|---|---|---|---|---|
| Plate-plate, before | 146 | 2.88 | 12.75 | 30.01 | 19 | 9 |
| Plate-plate, after | 146 | 1.57 | 5.83 | 29.33 | 8 | 3 |
| Plate-1904, before | 556 | 0.4 | 7.75 | 35.09 | 51 | 25 |
| Plate-1904, after | 556 | 0.46 | 7.41 | 32.13 | 47 | 23 |

| Seam | Before median / max m | After median / max m |
|---|---|---|
| 37L/37R (12 crossings) | 6.0 / 27.44 | 1.29 / 5.19 |
| 33/34R (1) | 25.58 | 10.05 |
| 34R/38 (2) | 21.19 / 21.84 | 4.85 / 5.79 |

## Deck check (full zoom, 1922 layer alone)

- 37L/37R, the gutter at Geringer Street: lot lines, numbers and the pipe line run straight across; no step seen.
- 33/34R, Marshall Avenue at Garrard: a step remains. Garrard on 33 sits about 8 m west of Garrard on 34R, matching the 10 m left on this seam.
- 34R/38, Vermont Avenue: continuous.

## Not done here

- `hub/sites/deck/tiles_n` (the 1904 frames as the page draws them) and the street sets built from the 1904 frames were not re-rendered or rebuilt after the re-bend: outside this ruling's scope. Until they are, the 1904 layer shows the frames where the previous bend put them.
- `plots.json` did not change.
- Derived inputs the builders need and the repo does not carry were recreated: the scans' alpha masks (`cufp/<N>/png_alpha_s4.npy`, `cuf38/png_alpha_s4.npy`, as `cufp/prep.py` makes them; not in git, 60 MB).
