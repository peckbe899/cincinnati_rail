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
- `test_page.js`: renders the page locally from `cache/snapshot.json` (the page falls back to it when there is no database) and screenshots the region, the presets, Union Terminal, dark theme and phone width.
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
