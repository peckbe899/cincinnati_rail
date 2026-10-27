# Station 3D

The 3D station page and the sync that feeds it, as set out in `claude/Station_3D_Brief.md`. Phases 1 (sync) and 2 (the page) are built for the whole region the Mill Creek Deck draws lines over; station design (phase 3) and the checks (phase 4) are not started.

- Page: https://claude.ai/artifact/MxbB1bnkqwZYxCbbEsHQZA (source `page/index.html`).
- Its database:
  - `snapshots/region` (the snapshot's summary, rules, issues and the list of its parts) and `snapshots/region/parts/<key>-<n>` (lines, tracks, unlevelled, stations, platforms, streets, blocks, ground), written by the sync;
  - `views/*` (named views, shared);
  - `data/users/<id>/camera_region` (each viewer's camera and station).

## Why a sync

A page can read only its own database, so the Rail Profiles editor and the Mill Creek Deck can't be read from the 3D page. A Claude session copies their state across instead. The editors are only read; the harness drops every write they try.

## Files

- `harness.js`: runs both editors headless (Playwright) from their published files, with a stand-in for `claude.use('db')` that serves the saved records.
  - Profiles: loads each line by its hash (`#Line_1`), then samples `railProfile.railAt(c)` and `typeAt(c)` along the whole line (every 5 m), and reads `align()` and `platforms()`.
  - Deck: opened with `?debug`, with jsts 2.12.1 served locally (`npm pack jsts@2.12.1` unpacked into `cache/jsts/`) and the same `window.__D` hook as `design/platform_track/extract/deck_headless.py`. Its own GeoJSON export is captured from the downloads stand-in (streets, blocks, platform rings), and `design/platform_track/extract/extract.js` runs as is for every track pair and every station's stops (type, bands, track offsets, Ben's settings).
- `sync.py`: the region snapshot. `cache/snapshot.json` plus the database documents in `cache/db_out/`.
  - Region: the Deck's rendered-line limits (its Region button), E 699,000-736,900, N 4,320,800-4,347,000 (UTM 16N). Coordinates are metres from the Fountain Square model's reference point: x east, y north (true), z elevation (as the editors). Point lists are integer deltas.
  - Lines: every Profiles line inside the region, rail level and structure type every 5 m.
  - Tracks: each Deck track is matched to its Profiles line (within 30 m) and gets that line's rail level by chainage, with its offset from the line. Deck track with no Profiles line nearby is kept as `unlevelled` and drawn dashed on the ground.
  - A stretch where a line runs on another line's tracks (TRI D on the A/D pair) is marked shared and drawn as rail only.
  - Platforms: the Deck's rings at the Profiles rail level. A platform on a shared pair (RER A/D, B C E ...) serves every line on it, at the level of the saved Profiles line, first in letter order. The Union Terminal TRI box's three islands are tied to A and B (north), D (centre) and B and A (south).
  - Stations: each Deck station with its stops, merged with the Profiles stations on the same lines (same name within 400 m, or any within 150 m); Profiles stations with no Deck station are kept and noted.
  - Ground: a 200 m grid averaged from the Profiles ground along every line, filled out to 1.6 km from the lines.
  - Issues: unsaved alignments, Deck track and platforms with no Profiles line, Deck spacing against the Profiles structure, TRI tubes that can't fit the Deck's 4.5 m spacing, Union Terminal cross-platform levels.
  - `--skip-harness` reuses `cache/harness_out.json`.
- `context3d.py`: the other systems at Union Terminal (CUT) and Norwood Central, called by `sync.py`. See "CUT and Norwood Central structures" below.
- `test_page.js`: renders the page locally from `cache/snapshot.json` (the page falls back to it when there is no database) and screenshots the region, the presets, Union Terminal, dark theme and phone width.
- `test_context.js`: close views of the CUT and Norwood Central structures (`node test_context.js OUTDIR [snapshot.json] [view,view]`).
- `cache/`: downloads and outputs, not committed.

## Running a sync (a Claude session)

1. Fetch the editors' published files with the Artifact tool (`action: read`, `paths`, `out_dir` = `tools/station3d/cache/profiles` and `.../deck`). The Profiles page needs `index.html` and every `lines/`, `rer/` and `network.json` file; the Deck needs `index.html` and its JSON files (tiles are not needed).
2. Fetch the saved records with ArtifactData (`out_dir` = `tools/station3d/cache/db/profiles_db` for collection `alignments` and `config`, `.../deck_db` for `deck/layout`).
3. Write `cache/versions.json` with the versions those reads reported (optional, kept in the snapshot's `sources`).
4. `python3 sync.py` (needs numpy and node with Playwright; about a minute). It prints the Fountain Square levels, counts, part sizes and the issues.
5. Write the parts in `cache/db_out/` under `snapshots/region/parts` (ArtifactData batches of four: a document holds at most 256 KiB, a batch 1 MiB; pin existing ones to their version), delete parts whose names are no longer in the list, then write `meta.json` as `snapshots/region` last. Open pages redraw on their own.

Scheduled runs have not been tried.

## Rules and assumptions in the snapshot

- Platform lengths (Ben, 2026-10-26): Metro 400 ft (121.92 m), TRI 670 ft (204.216 m). The Deck already draws these; the Profiles editor's RER default of 200 m is not used.
- Levels are always the Profiles editor's current values. Clashes in unfinished alignments are drawn as they are.
- A line with no saved alignment is drawn from the editor's built-in defaults and listed as an issue.
- Structure heights from the Profiles editor; track positions and spacing from the Deck. Box walls (2.3 m Metro, 3.25 m TRI outside the outer track), the TRI tube diameter (8.5 m) and the platform height are assumptions, listed on the page under Data: neither editor sets them.

## CUT and Norwood Central structures (2026-10-26)

Ben asked for the CUT underground box, the viaducts and the CUT and Norwood platforms to be drawn here, with the dives and the street-cut levels. `context3d.py` builds them from `data/deck` (the Mill Creek Deck's tracks, structures, deck and norwood files) using the same definitions as the Rail Profiles context (`tools/make_profile_context.py`, `build()`), so the two tools agree. The snapshot gains:

- `context`, items of four types:
  - `struct`: a plan outline (with holes) and, at each outline point, the rail level (`z`) and the finished ground (`g`); `k` is the kind, `b` and `t` the depth below and height above the rail. The page draws:
    - box (the lower level box, the lower-pair tunnel, the south throats, the intercity and C&O tunnels, the Union Terminal TRI box): closed, invert to roof;
    - viaduct and bridge (the CUT platform deck, the approach viaduct, the north arch viaduct, the intercity and C&O viaducts, the TRIMET C&O viaduct, the river bridges, the Ludlow underbridge): the deck, arch underside to rail;
    - trough and cut (the lower-pair open cut from Bank to Findlay, the intercity and C&O troughs, the Norwood Central cut and trench): floor and retaining walls up to the ground;
    - fill (the north trunk fill): the embankment to the track bed.
  - `pier`: a viaduct pier every 20 m along the longest track on it, from the finished ground to the arch underside (arches to the street, no footing check).
  - `rail`: the APEx, lower-level, ORR, Transvalley and Norwood tracks at the level of the structure they run in. A track outside every structure is added to `unlevelled`.
  - `plat`: the APEx (160.3 m), lower (144.0 m) and Norwood (178.0 m) platforms, tops 1.0 m above the rail.
- `gtiles`: finished ground at 10 m in 400 m tiles (aligned to the 200 m grid) round every structure and re-grade: the map 3 ground, plus the Deck's street re-grades (W 8th and Horne humps, Findlay +2.0 m, Bank -2.0 m), capped at the floors of the open cuts. The page uses them for the ground, the streets and the blocks.
- `ctx` in the meta: the tile size, counts, sources and rules.

The page has a "Other systems at CUT and Norwood Central" switch, legend rows, an "Other systems here (Deck)" list in the station panel, and labels on the structures.

Rulings (Ben, 2026-10-26):

1. One Union Terminal TRI box level for RER-1, 2 and 4, the Profiles level (135.7 m).
2. RER-2 and RER-4 on the north viaduct (their Profiles levels).
3. The Norwood ORR, Transvalley and APEx tracks are fixed context; the Metro and TRI levels are set in the Rail Profiles editor.
4. Arches drawn to the street, no footing check, for now.
5. The Deck's street re-grades are finished ground.
6. Lower-pair levels from the Deck's dive figures until the Deck publishes a level per point.

Drawing values: pier spacing 20 m and thickness 2 m; TRI box walls 5.0 m outside the islands.

The Deck snapshot in `data/deck` is version 1793028977-4bc6 (layout 2461). When the Deck changes, refresh `data/deck` from its published files before syncing.
