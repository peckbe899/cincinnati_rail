# Cincinnati Rail hub

The Mill Creek Deck, the Rail Profiles, Station 3D and the Chronology as four views of one local database. Change one and the others follow:

- **Deck** (plan): rights of way, tracks, platforms, streets. Saving it runs the **Deck tie**: every RER route and Metro line is rebuilt on the Deck's pieces and every platform put at its Deck platform's centre (`tools/rer_deck_routes.py`). Saved profiles, crossings, the networks, the Metro rails table and the Profiles context move with them.
- **Rail Profiles** (levels): reads the tied routes, saves its profiles and settings in the same database.
- **Station 3D**: rebuilt from the two (`tools/station3d/sync.py`, both editors run headless on the hub's records) after either changes. Open 3D views redraw on their own.
- **Chronology** (`/chronology/`): the opening year and phase of every Metro and TRI segment (between two neighbouring stations) and station, on a map of the lines; colour by phase or year, the network as of a year, unset segments dashed. Click a station, then another on the same line, to select the segments between (shift-click adds, Alt-drag boxes). The order rules (outward from each line's core never older; a station no earlier than its track, later is infill; TRI track shared by several routes is one segment) refuse an edit that breaks them, offer to push outer segments to a newer year, and list rule breaks, orphans (entries whose stations are gone) and what is not set. The phase of each stretch sets its tunnel: the Profiles read it live (a band under the profile; click it to open the segment here), and the 3D build and the Deck follow. Record `chronology/segments` (default `data/profile/chronology.json`), routes from `tools/chronology.py` (`data/profile/chronology_lines.json`, rebuilt by each Deck tie); rules in `hub/static/chronology_rules.js`.
- **Hub page** (`/`): the pipeline's runs and logs, the shared parameters as each view has them (and where they differ), the roadmap, and export.

Only you, only on your machine: no hosting, no logins.

## Start

```
pip install -e ".[hub]"                 # numpy, shapely, pyproj, rasterio ...
npm install && npx playwright install chromium
python hub/hub.py                       # opens http://localhost:8765
```

The views: `/deck/`, `/profiles/` (a line by hash, `/profiles/#Line_8`), `/3d/`, `/chronology/` (a segment by hash). A bar at the bottom of each has a Home button (the hub page), moves between the views and shows when the pipeline is updating; a page whose data files changed (the Profiles after a Deck tie) offers a reload.

Options: `--port`, `--no-auto` (run the pipeline only from the hub page), `--no-browser`, `--db PATH`.

## How it fits together

- `hub/hub.py`: the server (Python standard library). Serves the three pages with `static/shim.js` in place of the artifact runtime (`window.claude`): the pages are the published ones, unchanged; their database calls go to the hub, and changes come back live over server-sent events. Their CDN libraries are served from `static/vendor`, so it works offline.
- `hub/store.py`: the database, `hub/hub.db` (SQLite). Records are addressed as the pages address them: `deck/layout`, `alignments/<line>`, `config/settings`, `config/settings_rer`, `snapshots/region` and its parts, `views/*`, plus the hub's own `params/registry`, `roadmap/*`, `params/metro_structure` (the Metro structure gauge: tubes by building phase, box, island, grades; read live by the Deck, the Profiles and the 3D build; edited on the hub page; default `data/profile/metro_structure.json`) and `params/station_types` (the Profiles structure type at each Metro station, written by each 3D build; the Deck's island default), `params/tube_points` (the bored tube along each Metro line every 50 m, written by each 3D build; the Deck's track spacing) and `chronology/segments` (the Chronology). Each write gets a version; the last 50 versions of each record are kept (`/api/history?p=`, `/api/restore?p=&v=`).
- `hub/pipeline.py`: what runs on a change. `deck/layout` -> Deck tie -> 3D; `alignments/*`, `config/*`, `params/metro_structure`, `chronology/segments` -> 3D (and once more if the station types change, so the Deck's platforms follow). Runs are queued and coalesced (a burst of saves is one run); the 3D rebuild takes about two minutes. The work folder `hub/work/` is laid out as the sync's cache, with the hub's records as the editors' databases.
- Derived files the tie writes are the repo's own: `data/deck/rer_routes.geojson`, `data/profile/**`. Commit them as before.
- `hub/sites/deck/`: the Deck page and its data files (from the published Deck, version 1793128963-c39d, without the 0.25 m imagery tiles; the overviews are there). The Profiles page is `data/profile/profiles.html`, the 3D page `tools/station3d/page/index.html`.

## Records in git

`hub/hub.db` is not in git. `python hub/hub.py export` (or the Export button) writes every record but the 3D snapshot to `hub/seed/` as JSON; commit that. A new database is seeded from `hub/seed/` on first start (the first start also builds the 3D snapshot). The seed holds the artifacts' records as of 2026-10-27 (Deck layout version 2463, 38 saved profiles) and the roadmap.

## The artifacts

The claude.ai artifacts are not updated by the hub: from now on the hub is where the design lives. To show the work there again, a Claude session can publish the repo's files and write `hub/seed` records to an artifact's database.

## Checks

```
python -m pytest tests/test_hub.py
node hub/test_hub.js            # with the hub running: the four views load on it, a change reaches an open view live (a Chronology phase reaches the Profiles)
```
