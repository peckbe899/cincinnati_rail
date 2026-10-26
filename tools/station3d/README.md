# Station 3D

The 3D station page and the sync that feeds it, as set out in `claude/Station_3D_Brief.md`. Phases 1 (sync) and 2 (the page) are built for Fountain Square; station design (phase 3) and the checks (phase 4) are not started.

- Page: https://claude.ai/artifact/MxbB1bnkqwZYxCbbEsHQZA (source `page/index.html`).
- Its database: `snapshots/<area>` and `snapshots/<area>/parts/{lines,deck}` (written by the sync), `views/*` (named views, shared), `data/users/<id>/camera_<area>` (each viewer's camera).

## Why a sync

A page can read only its own database, so the Rail Profiles editor and the Mill Creek Deck can't be read from the 3D page. A Claude session copies their state across instead. The editors are only read; the harness drops every write they try.

## Files

- `harness.js`: runs both editors headless (Playwright) from their published files, with a stand-in for `claude.use('db')` that serves the saved records.
  - Profiles: loads each line by its hash (`#Line_1`), then samples `railProfile.railAt(c)` and `typeAt(c)` every 2 m, and reads `align()` and `platforms()`.
  - Deck: opened with `?debug`; its own GeoJSON export is captured from the downloads stand-in.
- `sync.py`: picks the lines within 400 m, runs the harness and writes `cache/snapshot.json` plus the database documents in `cache/db_out/`.
  - Coordinates are metres from the station origin: x east, y north (true), z elevation (as the editors).
  - Lines carry their plan, rail level, ground and structure type; platforms carry the Deck's plan and the Profiles rail level at their centre.
- `test_page.js`: renders the page locally from `cache/snapshot.json` (the page falls back to it when there is no database) and screenshots each preset.
- `cache/`: downloads and outputs, not committed.

## Running a sync (a Claude session)

1. Fetch the editors' published files with the Artifact tool (`action: read`, `paths`, `out_dir` = `tools/station3d/cache/profiles` and `.../deck`). The Profiles page needs `index.html` and every `lines/`, `rer/` and `network.json` file; the Deck needs `index.html` and its JSON files (tiles are not needed).
2. Fetch the saved records with ArtifactData (`out_dir` = `tools/station3d/cache/db/profiles_db` for collection `alignments` and `config`, `.../deck_db` for `deck/layout`).
3. Write `cache/versions.json` with the versions those reads reported (optional, kept in the snapshot's `sources`).
4. `python3 sync.py` (needs numpy and node with Playwright). It prints each line's rail level at the station and any issues.
5. Write `cache/db_out/{lines,deck,meta}.json` to the page with one ArtifactData batch: the two parts under `snapshots/fountain_square/parts`, then `meta` as `snapshots/fountain_square`, each pinned to the version it has. Open pages redraw on their own.

Scheduled runs have not been tried.

## Rules and assumptions in the snapshot

- Platform lengths (Ben, 2026-10-26): Metro 400 ft (121.92 m), TRI 670 ft (204.216 m). The Deck already draws these; the Profiles editor's RER default of 200 m is not used.
- Levels are always the Profiles editor's current values. Clashes in unfinished alignments are drawn as they are.
- A line with no saved alignment (Line 7, RER-4 today) is drawn from the editor's built-in defaults and listed as an issue.
- Structure heights from the Profiles editor; widths, tube spacing and platform height are assumptions, listed on the page under Data.
- The ground is a plane fitted to the Profiles ground samples inside the area (about 2 m rms at Fountain Square).
