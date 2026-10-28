# Station 3D

The 3D station page and the sync that feeds it, as set out in `claude/Station_3D_Brief.md`. Phases 1 (sync) and 2 (the page) are built for the whole region the Mill Creek Deck draws lines over; station design (phase 3) and the checks (phase 4) are not started.

- Page: `page/index.html`, served by the hub at `/3d/` (the old claude.ai artifact is retired).
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
  - Tracks: each Deck track is matched to its own Profiles line (within 120 m: the Deck and the Profiles paths differ by up to 60 m in places) and gets that line's rail level by chainage. The chainage must run one way along a track; points that step back (past the line's end, or onto another stretch of the line) are left unlevelled, so no track folds back on itself.
  - Plan from the Deck (Ben, 2026-10-27; since the routes were tied to the Deck's pieces the same day, only for a line that is not tied, CVG Express: a tied line's path is the Deck's own line, and the middle of the Deck's tracks pulled it to one side at stations such as Rivercenter West): where a line has its own Deck tracks, its centre is moved to their middle (smoothed over 40 m, tapering back to the Profiles path over 150 m past their ends), its stations move with it, and the tracks' offsets are taken from the moved centre. So the structure and the rails are drawn on the Deck's tracks, with the Profiles levels. Fold-backs left in a Profiles path where the Deck has no track are listed as issues.
  - Rails centred on the line (Ben, 2026-10-27: "the rail should be always centered for all lines"; "unbroken between tube and cut-and-cover"): each line's two tracks are drawn at plus and minus half the spacing its Profiles structure needs, from the Deck's rules: Metro twin tubes 8.0 m, Metro box, single bore, open and viaduct 3.9 m, TRI 4.5 m, TRI bored tubes 9.5 m (two 8.5 m tubes 1 m apart), and at an island platform the island's width plus its edges (Metro 10.9 m, TRI 14.5 m). Changes taper over the Deck's 40 m, so the rails run unbroken through every change of structure. Platforms are drawn on these tracks at their place along the line with the Profiles platform length (the Union Terminal box keeps the Deck's three islands). A line counts as running on another line's track only along 100 m or more. The Deck's own track spacing is still checked against the Profiles structure (the issues list).
  - Deck track with no Profiles line (mostly past the end of the Profiles cores, out to the region's edge) is kept as `unlevelled` with its lines' colours and drawn on the ground in them (striped for several lines; dashed grey for none).
  - Interlined pairs (Ben, 2026-10-27): a Deck pair carrying several lines ('RER A/D', 'B D', 'B C E') is levelled from the line most of it follows and lists the others (`with`, those within 60 m of it). The page draws it once, rails and structure striped every 30 m in each line's colour (`interline`, `stripe_m` and each line sample's `il`); the other lines draw nothing within 60 m of it. Where their Profiles levels differ by more than 1 m it is an issue (D's editor defaults against A and B).
  - Elsewhere a stretch where a line runs on another line's tracks is marked shared and drawn as rail only.
  - Platforms: the Deck's rings at the Profiles rail level. A platform on a shared pair (RER A/D, B C E ...) serves every line on it, at the level of the saved Profiles line, first in letter order. The Union Terminal TRI box's three islands are tied to A and B (north), D (centre) and B and A (south).
  - Stations: each Deck station with its stops, merged with the Profiles stations on the same lines (same name within 400 m, or any within 150 m); Profiles stations with no Deck station are kept and noted.
  - Ground: a 200 m grid averaged from the Profiles ground along every line, filled out to 1.6 km from the lines.
  - Issues: unsaved alignments, Deck track and platforms with no Profiles line, Deck spacing against the Profiles structure, TRI tubes that can't fit the Deck's 4.5 m spacing, Union Terminal cross-platform levels.
  - `--skip-harness` reuses `cache/harness_out.json`.
  - Repo data the editor does not have yet (both listed as issues):
    - `REPO_PROFILES`: RER-4's profile (`data/profile/rer/alignments/RER_4.json`, the upper deck), served to the editor as if saved while it has no saved RER-4.
    - `REPATH`: RER-2 and RER-4 re-pathed onto the Deck's B/D route (`data/profile/rer/repath_bd_trunk.json`). While the published editor still has the old paths, the sync serves the repo's line files to the harness in their place (`overlay`) and moves the saved profiles made on the old paths with the chainage map (`override_docs`). It stops once the editor is republished with the new paths (done 2026-10-27, editor version 34).
- `context3d.py`: the other systems at Union Terminal (CUT) and Norwood Central, called by `sync.py`. See "CUT and Norwood Central structures" below.
- `test_page.js`: renders the page locally from `cache/snapshot.json` (the page falls back to it when there is no database) and screenshots the region, the presets, Union Terminal, dark theme and phone width.
- `test_context.js`: close views of the CUT and Norwood Central structures (the fan at Gest, the W 8th arch, the Cardinal crossing among them) (`node test_context.js OUTDIR [snapshot.json] [view,view]`).
- `cache/`: downloads and outputs, not committed.

## Running a sync (a Claude session)

RETIRED: the claude.ai artifacts are no longer used (see `CLAUDE.md`). The hub runs the sync (`hub/pipeline.py`, job 3d); the steps below are history. Do not fetch from or write to any artifact.

1. Fetch the editors' published files with the Artifact tool (`action: read`, `paths`, `out_dir` = `tools/station3d/cache/profiles` and `.../deck`). The Profiles page needs `index.html` and every `lines/`, `rer/` and `network.json` file; the Deck needs `index.html` and its JSON files (tiles are not needed).
2. Fetch the saved records with ArtifactData (`out_dir` = `tools/station3d/cache/db/profiles_db` for collection `alignments` and `config`, `.../deck_db` for `deck/layout`).
3. Write `cache/versions.json` with the versions those reads reported (optional, kept in the snapshot's `sources`).
4. `python3 sync.py` (needs numpy and node with Playwright; about a minute). It prints the Fountain Square levels, counts, part sizes and the issues. It also checks every RER route and Metro line against the live Deck (`tools/rer_deck_routes.py`: path within 0.5 m of the Deck's pieces, each platform at its Deck platform's centre) and lists any that are off; fetch `alignments` fresh first, since the platform check reads the saved slides.
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
    - structure types at CUT (Ben, 2026-10-26; `st`, as the Profiles context): embankment (`fill`: the fan from W 9th to W Liberty, the north trunk fill, the intercity and C&O descents), solid to the track bed and cut open at each street; arch viaduct (`arch`: the south approach to the Cardinal crossing, the north arch viaduct), solid between the streets; normal viaduct (`viaduct`: the rest, and the Indianapolis and D upper deck): the deck, underside to rail; bridge (river bridges, the Ludlow underbridge);
    - trough and cut (the lower-pair open cut from Bank to Findlay, the intercity and C&O troughs, the Norwood Central cut and trench): floor and retaining walls up to the ground.
  - `span`: over each street opening, a flat bridge (embankment), or on the arch viaducts a true arch (streets up to 11.9 m wide) or a girder bridge 2.0 m deep hidden behind the arch fascia (Ben, 2026-10-28), drawn along the street.
  - `arcade` (Ben, 2026-10-28): each long face of the arch viaducts (APEx lower deck only, not the Indianapolis and D upper deck): the face line, rail, finished ground, width across, and its stretches `[u0, u1, kind, name]`, a street opening (`arch` or `girder`) or a block's stretch (`blind`, `shops` or `open`, from the Deck's per-block switch, `edits.blocks[id].arc`, exported as `arcade`). A block switched open carves a girder bridge through the structure. The page draws the arcade within 450 m of the view's centre when zoomed in (Show: Arcade): ashlar walls, piers 2.4 m on the building lines with granite plinths (roundels and flutes on the end piers), bays fitted to about 18.3 m, two-band archivolts, keystones with fan rays, corbels and cornice, bronze railing, glazed shopfronts, masonry catenary pylons on every fourth pier with a lattice girder to mid-deck (the middle masts wait for the 6.0 m APEx-side gaps). Style from Ben's mockup via the Viaduct Arcade 3D model.
  - `blind`: blind-arch outlines every 10 m on the faces of the descent embankments.
  - `pier`: piers every 25 m on normal viaducts only, from the finished ground to the underside (no footing check); the upper deck's piers stand on the lower deck.
  - `rail`: the APEx, lower-level, ORR, Transvalley and Norwood tracks at the level of the structure they run in. Past the structures (Ben, 2026-10-27: off the bridges into Ludlow and to the region's edge) each track runs from the structure end at no more than its system's grade (APEx 2.5%, lower level 1.5%, Transvalley 3%) to the ground smoothed over 150 m; the Deck's tunnel tracks 15 m under it; over water at least 20 m above the Ohio pool. Drawing values; `est` marks those points. Nothing is left dashed.
  - `plat`: the APEx (160.3 m), lower (144.0 m) and Norwood (178.0 m) platforms, tops 1.0 m above the rail.
- `gtiles`: finished ground at 10 m in 400 m tiles (aligned to the 200 m grid) round every structure and re-grade: the map 3 ground, plus the Deck's street re-grades (W 8th and Horne humps, Findlay +2.0 m, Bank -2.0 m), capped at the floors of the open cuts. The page uses them for the ground, the streets and the blocks.
- `ctx` in the meta: the tile size, counts, sources and rules.

The page has a "Other systems at CUT and Norwood Central" switch, legend rows, an "Other systems here (Deck)" list in the station panel, and labels on the structures.

Rulings (Ben, 2026-10-26):

1. One Union Terminal TRI box level for RER-1, 2 and 4, the Profiles level (135.7 m).
2. RER-2 and RER-4 on the north viaduct (their Profiles levels).
3. The Norwood ORR, Transvalley and APEx tracks are fixed context; the Metro and TRI levels are set in the Rail Profiles editor.
4. No footing check, for now.
5. The Deck's street re-grades are finished ground.
6. Lower-pair levels from the Deck's dive figures until the Deck publishes a level per point.

Drawing values: pier spacing 25 m and thickness 2 m; blind arches every 10 m; TRI box walls 5.0 m outside the islands.

Later rulings (Ben, 2026-10-27): the structure types above; the Indianapolis APEx pair and RER D on an upper deck at the minimum height over the lower deck (174.5 m, 7.9 m over its highest rail), held to the hillside, then the Floridian hillside tunnel at a constant grade to the portal (about 186 m); RER D tied to it (`data/profile/rer/alignments/RER_4.json`); B and D from the trunk to Union Terminal on the Deck's route; interlined pairs drawn once, striped. See `data/profile/README.md`.

The Deck snapshot in `data/deck` is version 1793028977-4bc6 (layout 2461). When the Deck changes, refresh `data/deck` from its published files before syncing.

## Metro structure and tunnel equipment (2026-10-28)

- Structures and rail spacing come from the shared Metro structure record (hub `params/metro_structure`, else `data/profile/metro_structure.json`): bored stretches take the tube of the phase their drawn piece was built in (type A, the 9.0 m double-track bore, type C; snapshot types `shield~A` and so on); boxes 9.1 m outside. Spacing narrows only inside a box, never in a tube.
- The snapshot's `approach` lists side platforms on bored stretches, the boxes islands on the bore need, and approaches that do not fit; `station_types` gives the Profiles type at each Metro station (the Deck's island default).
- Tunnel equipment is drawn by the page within about 500 m of the view's centre when zoomed in, on five switches under Show, at the positions of Ben's box and tube cutaways (claude/Metro_Structure_Gauge_Handoff.md section 3.5).


## Track geometry in tunnels and station approaches (Ben, 2026-10-28)

- Each Metro track is offset from the line's centreline by half its construction's spacing (box and bore 3.90 m, type A 8.74 m, type C 9.14 m, islands 10.90 m). Bored tubes always run at their spacing; platforms are straight.
- The approach belongs to the station: a cut-and-cover station meeting bored tubes keeps its box (the Rail Profiles type) until the tracks reach the tubes' spacing; a box meeting tubes away from a station likewise; a bored station's approach is bored. Length max(approach_m, sqrt(4 x min_radius x shift per track)); the record's `min_radius` is a drawing value (150 m) until Ben sets it.
- The sync draws each change as one S-ease (two equal reverse curves) over the editor's approach (`approaches` in the harness output); other changes (portals, phase changes) hold the wider spacing and ease into the narrower side.
- `track_geometry` in the snapshot and the issues: approaches under the minimum radius (the S-ease's reverse curves on the centreline's curvature, or the single arc each track takes where the approach runs into a curve), side-platform stations meeting tubes, the boxes made longer, and approach boxes not inside the street (box outside = track centres + 4.0 m; streets from the Deck, `context/lines.json`).
