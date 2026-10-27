# Cincinnati Rail hub

The Mill Creek Deck, the Rail Profiles and Station 3D as three views of one local database. Change one and the others follow:

- **Deck** (plan): rights of way, tracks, platforms, streets. Saving it runs the **Deck tie**: every RER route and Metro line is rebuilt on the Deck's pieces and every platform put at its Deck platform's centre (`tools/rer_deck_routes.py`). Saved profiles, crossings, the networks, the Metro rails table and the Profiles context move with them.
- **Rail Profiles** (levels): reads the tied routes, saves its profiles and settings in the same database.
- **Station 3D**: rebuilt from the two (`tools/station3d/sync.py`, both editors run headless on the hub's records) after either changes. Open 3D views redraw on their own.
- **Hub page** (`/`): the pipeline's runs and logs, the shared parameters as each view has them (and where they differ), the roadmap, and export.

Only you, only on your machine: no hosting, no logins.

## Start

```
pip install -e ".[hub]"                 # numpy, shapely, pyproj, rasterio ...
npm install && npx playwright install chromium
python hub/hub.py                       # opens http://localhost:8765
```

The views: `/deck/`, `/profiles/` (a line by hash, `/profiles/#Line_8`), `/3d/`. A bar at the bottom of each moves between them and shows when the pipeline is updating; a page whose data files changed (the Profiles after a Deck tie) offers a reload.

Options: `--port`, `--no-auto` (run the pipeline only from the hub page), `--no-browser`, `--db PATH`.

## How it fits together

- `hub/hub.py`: the server (Python standard library). Serves the three pages with `static/shim.js` in place of the artifact runtime (`window.claude`): the pages are the published ones, unchanged; their database calls go to the hub, and changes come back live over server-sent events. Their CDN libraries are served from `static/vendor`, so it works offline.
- `hub/store.py`: the database, `hub/hub.db` (SQLite). Records are addressed as the pages address them: `deck/layout`, `alignments/<line>`, `config/settings`, `config/settings_rer`, `snapshots/region` and its parts, `views/*`, plus the hub's own `params/registry`, `roadmap/*`. Each write gets a version; the last 50 versions of each record are kept (`/api/history?p=`, `/api/restore?p=&v=`).
- `hub/pipeline.py`: what runs on a change. `deck/layout` -> Deck tie -> 3D; `alignments/*`, `config/*` -> 3D. Runs are queued and coalesced (a burst of saves is one run); the 3D rebuild takes about two minutes. The work folder `hub/work/` is laid out as the sync's cache, with the hub's records as the editors' databases.
- Derived files the tie writes are the repo's own: `data/deck/rer_routes.geojson`, `data/profile/**`. Commit them as before.
- `hub/sites/deck/`: the Deck page and its data files (from the published Deck, version 1793128963-c39d, without the 0.25 m imagery tiles; the overviews are there). The Profiles page is `data/profile/profiles.html`, the 3D page `tools/station3d/page/index.html`.

## Records in git

`hub/hub.db` is not in git. `python hub/hub.py export` (or the Export button) writes every record but the 3D snapshot to `hub/seed/` as JSON; commit that. A new database is seeded from `hub/seed/` on first start (the first start also builds the 3D snapshot). The seed holds the artifacts' records as of 2026-10-27 (Deck layout version 2463, 38 saved profiles) and the roadmap.

## The artifacts

The claude.ai artifacts are not updated by the hub: from now on the hub is where the design lives. To show the work there again, a Claude session can publish the repo's files and write `hub/seed` records to an artifact's database.

## Checks

```
python -m pytest tests/test_hub.py
node hub/test_hub.js            # with the hub running: the three views load on it, a change reaches an open view live
```
