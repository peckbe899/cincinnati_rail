# Cincinnati Rail hub

The Mill Creek Deck, the Rail Profiles, Station 3D and the Chronology as four views of one local database. Change one and the others follow:

- **Deck** (plan): rights of way, tracks, platforms, streets. Saving it runs the **Deck tie**: every RER route and Metro line is rebuilt on the Deck's pieces and every platform put at its Deck platform's centre (`tools/rer_deck_routes.py`). Saved profiles, crossings, the networks, the Metro rails table and the Profiles context move with them.
- **Rail Profiles** (levels): reads the tied routes, saves its profiles and settings in the same database.
- **Station 3D**: rebuilt from the two (`tools/station3d/sync.py`, both editors run headless on the hub's records) after either changes. Open 3D views redraw on their own.
- **Chronology** (`/chronology/`): the opening year and phase of every Metro and TRI segment (between two neighbouring stations) and station, on a map of the lines; colour by phase or year, the network as of a year, unset segments dashed. Click a station, then another on the same line, to select the segments between (shift-click adds, Alt-drag boxes). There are no order rules (Ben, 29 October: parts of a line are built before others, the RER runs on old railroad rights of way, the central tunnels come last): any segment may open in any year. A station opens with its earliest track unless its own year is set (a later one is listed as infill); TRI track shared by several routes is one segment; the panel lists orphans (entries whose stations are gone) and what is not set. **Lines** in the panel turn each line on or off (remembered in the browser). **Undo** and **Redo** (Ctrl+Z, Ctrl+Shift+Z) step through the changes made in the page; **Reset** (in the panel of a selected segment or station, one button per line) puts a line's segments and stations back to the starting record (`data/profile/chronology.json`), undoable. The phase of each stretch sets its tunnel: the Profiles read it live (a band under the profile; click it to open the segment here), and the 3D build and the Deck follow. Record `chronology/segments` (default `data/profile/chronology.json`), routes from `tools/chronology.py` (`data/profile/chronology_lines.json`, rebuilt by each Deck tie); shared logic in `hub/static/chronology_rules.js`.
- **Station access** (`/access/`): each Metro station's access type at opening from the rules (`params/station_access_rule`, written by the 3D job from `tools/station_access_report.py`) or your choice, and the later stages proposed from the lines opening there, accepted or added here (`params/station_access`, read by the Rail Profiles). Stations that are one station under different names: give them one label in the Deck's station card ("One station with"); the 3D build groups same-name stations within 150 m on its own (`params/station_complexes`).
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

`hub/hub.db` is not in git. `python hub/hub.py export` (or the Export button) writes every record but the 3D snapshot to `hub/seed/` as JSON; commit that. The export also refreshes the repo copies of the files the pipeline derives (`data/deck/rer_routes.geojson`, `hub/sites/deck/viaducts.json`, `data/profile/station_platforms.json`, `data/profile/approach_extra.json`); between exports the pipeline keeps them under `hub/work/` (not in git), so a run never dirties the working tree (31 October). A new database is seeded from `hub/seed/` on first start (the first start also builds the 3D snapshot). The seed holds the artifacts' records as of 2026-10-27 (Deck layout version 2463, 38 saved profiles) and the roadmap.

**Changes made by a Claude session reach your hub through `hub/seed`.** After `git pull`, start the hub as usual: on start it takes in the seed. A record you have not changed since your hub last took in (or exported) the seed is replaced by the new one; one you changed and the session did not is kept; one changed on both sides is merged edit by edit (the Deck layout's streets, blocks and stations, a profile's fields), and where you both changed the same edit, yours is kept and it is listed as a conflict, with the seed's version in `hub/work/seed_conflicts/`. What was taken in shows on the hub page as a `seed` run (records kept as yours are listed once), and the Deck or 3D update runs after it. Export before you pull, as always, so your own changes are in git too.

## The artifacts

The claude.ai artifacts are retired (Ben): do not publish to them or write their databases. The hub and this repository are where the design lives.

## Checks

```
python -m pytest tests/test_hub.py
node hub/test_hub.js            # with the hub running: the four views load on it, a change reaches an open view live (a Chronology phase reaches the Profiles)
```

## Chronology timeline

The Chronology's **Timeline (.md)** button downloads every set opening in date order (by decade, year and month) as Markdown. Each Export also writes it to `data/profile/chronology_timeline.md` (`tools/chronology_timeline.js`). Segments and stations take an optional month.

## Platforms both ways (Ben, 29 October)

The Deck and the Profiles move platforms both ways. A platform slid in the Profiles (on a station whose platform is drawn on the Deck) is written into the Deck layout as that platform's offset along its line; the Deck tie then puts the station at the moved platform and clears the slide (`tools/platform_tie.py`, the `platform_tie` job, run on every profile save before anything else). A platform moved on the Deck moves the station in the Profiles, as before. Where both moved the same platform, the more recent save wins; the hub keeps each platform's offset as of the last time the two agreed (`params/platform_sync`) to tell which side moved it. A slide on a station with no platform on the Deck stays in the profile. The Deck caps a slide at 150 m (or half the platform); a longer one is held there and noted in the run's log.
