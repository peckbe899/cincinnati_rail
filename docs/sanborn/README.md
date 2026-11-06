# Sanborn pipeline in the repo

The scripts and data that made the Deck's Sanborn layers (1904 basin and north sheets, the 1922 plates, the 1912 survey) and the other Deck page files, moved here from the Topography conversation's workspace (export of 31 October 2026, `Maps/Topography_Export`, all 19 zips including `extras_01` and `extras_02`) on 6 November 2026.

Ben's ruling (6 November): nothing is re-derived. The Deck's `basin.json`, `plots.json`, `sheets.json` and the current street and plot ids are frozen as they are. This move changed no output and ran no build.

## Layout (migration plan section 3)

| Where | What |
|---|---|
| `tools/sanborn/<workspace path>` | every script (.py, .sh, .js), at its workspace path (`cuf/x1904.py`, `sbg/fit/build.py`, ...) |
| `data/sanborn/<workspace path>` | every other file: picks (`sbg/picks`, `picks22`, `picks12`), per-plate config (`cufp/config.json`, `cuf_cw/config.json`, `cufp/strips.json`), exclusions and removals (`*removed*.json`, `sbg/basin_1912_rejected.json`), fix lists (`sbg/osmchk/corrections.json`, `pick_fix.json`, `cuts.json`, `additions.json`), plate footprints and boundary lines (`area*.json`, `basin/aoi.json`), seeds (`cufp/<N>/png2tif.json`, `cuf/ben_georef.json`), frame lists (`lph/sheets_*.json`, `cuf_cw/frames_*`), forward models and transforms (`fwd.pkl`, `matches.json`, `lph/tf*.json`, `tps*.pkl`), reports, the page database snapshots (`dbread*/`), the `deckpage/*_vNN.json` copies scripts read, and the generators' data |
| `data/sanborn/manifest.json` | every file above by path, size and sha256 with its category, and every scan the scripts read on Ben's machine (`python tools/sanborn/manifest.py check` stops on a changed scan) |
| `data/sanborn/reports/` | reports, one folder per run: `2026-11-06_seams` (seam report, the plates' own models), `2026-11-06_joint` (the joint refit of the 1922 plates: per-plate before/after, ties, the Part 3 check), `2026-11-06_seams_joint` (seam report on the joint models) |
| `tools/sanborn/joint/` | the joint refit (`solve.py`) and its models' reader (`jointlib.py`). The new models sit beside the old ones (`cufp/<N>/fwd_joint.pkl`, `cuf_cw/<half>/fwd_joint.pkl`, `cuf38/fwd38_joint.pkl`, `cuf/joint35N.pkl`); nothing reads them but `jointlib.py` and `seams.py --joint`, so the page is unchanged |
| `docs/sanborn/` | this file, the migration plan, `RULES.md` (plan section 7), `PROCESS_1922.md` (the 1922 plate method, from `cufp/`), `Relief_Maps_Log.md` (the history), `export/` (the export's README, MANIFEST.csv and TREE.txt), `workspace_notes/` (the workspace's other notes: `sbg/INSTRUCTIONS*.md`, `lph/RESUME.md`, ...) |
| `configs/sanborn_paths.json` | Ben's local folders, and what each old `/mnt/user-data/...` path stands for |

Code and data keep the workspace's relative paths, so the scripts find everything as before; nothing was renamed or regrouped. Splitting the data into the plan's `models/` and `reports/` folders would mean rewriting the scripts' paths, which waits for the rebuild (plan section 4).

The inverse grids (`model.npz`, `model38.npz`, 95 MB) are on disk under `data/sanborn` but not in git (`data/sanborn/.gitignore`; the plan has them rebuilt by the fit). The copies are in `Maps/Topography_Export/1922_inverse_01..05.zip`.

## Gaps in the export

Modules the scripts import that were not exported (found by checking every script's imports against `export/TREE.txt`):

- `sbg/names.py` (street-name keys `key`, `base`, `key2`; imported by 33 scripts, among them `cuf/x1904.py`, `sbg/fit/add_ext.py`, the plate builds): added from `Maps/Basin_Street_Map/sanborn1904_scripts.zip`, whose copy has the size and time the workspace tree lists (1743 bytes, 11 October 21:42).
- Lost for good (`EXTRAS_03_README.md`: the Topography workspace was reset, and no copy exists anywhere): `arcs/fitarcs.py` (14820 bytes, 15 October; imported by `rer1023/apply.py` and `transit/build_transit.py`), the workspace's `arcs/fitarcs.js` (14407 bytes), and `deck/xs.py` (749 bytes, 10 October; imported by `lph/solve_all.py`) with its output `deck/xs_v1.json`. Those three scripts cannot run as they are.
- The surviving curve fitter is the Deck page's `FA.fit`: `tools/sanborn/arcs/fitarcs_deck_port.js` (from `extras_03.zip`, 6 November) is the page's block copied unchanged, and it is line for line the same as `hub/sites/deck/index.html` lines 412-579. The log (10ze.2, 10ze.6) says it follows `fitarcs.py`'s rules and gave identical results on all 39 lines. `FA.fit(points)` runs on its own in Node (`require('./tools/sanborn/arcs/fitarcs_deck_port.js').FA`): [E, N] points in, `{verts, k, curves}` out.

`cvg/_gp_C.json` and `cvg/_gp_c.json` differ only in case, which Windows cannot hold side by side: the first is `cvg/_gp_C_upper.json` (no script names either).

## How the paths were repointed

- The workspace root (`SP` / `S` = `/tmp/claude-0/-home-claude/9669db83-.../scratchpad/`) is now `_ws.DATA` (`data/sanborn/`). Where the scripts used it for another script (`sys.path.insert(0, SP + 'cuf')`, `exec(open(SP + 'trunk2/lud6.py')...)`, `runpy`, `spec_from_file_location`), it is `_ws.CODE` (`tools/sanborn/`). The sbg scripts that found data beside themselves (`HERE`) take `_ws.data_dir(...)` and keep their code folders on `sys.path`.
- `/mnt/user-data/uploads/...` and `/mnt/user-data/outputs/...` go through `_ws.ext(...)`, which maps them by `configs/sanborn_paths.json` "mnt" (Ben's scans: `Maps/Sanborn`, `Historic_Topo`, `CS2/New Sanborn/PNG` and `GeoTIFF`). The data files that hold such paths (`cufp/config.json` "png", `sbg/fit/sizes.json`) are unchanged; the scripts map them when they read them.
- Each converted script starts with two lines that import `tools/sanborn/_ws.py`. Shell scripts take `T` (tools/sanborn) and `D` (data/sanborn) the same way.
- Data files are byte for byte the export's. Scripts and notes differ only in these paths; `manifest.json` gives the export's sha256 beside each changed file.

## Running a script

As in the workspace, scripts run with the data root as the working directory:

```
cd data/sanborn
python ../../tools/sanborn/cuf/x1904.py 107,108
```

`python tools/sanborn/_ws.py` prints the roots and checks every mapped folder exists. Before any build: `python tools/sanborn/manifest.py check` (and rule 10: export the hub first).

The command table and rebuild order in `export/README.md` hold as written with this layout (`python3 cuf/build22.py` becomes `python ../../tools/sanborn/cuf/build22.py` from `data/sanborn`). Not to be run until the rebuild is planned: `cuf/tiles22_add.py`, `sbg/fit/build.py`, `sbg/fit/add_ext.py` and every plate fit.
