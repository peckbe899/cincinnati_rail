# Platform and track design, and the 3D model

The Mill Creek Deck's platform and track design, read straight from the page, and combined with the Rail Profiles page into 3D tracks. State as of 2026-10-26.

- Deck: version of 2026-10-26 15:36 UTC, layout 2461.
- Profiles: version of 15:57 UTC, saved alignments as of 17:25 UTC.

The findings and decisions are in `Platform_Track_Design_Brief.md` (also the project doc `claude/Platform_Track_Design_Brief.md`).

## What you need

- `pip install -r requirements.txt`.
- Chromium for Playwright (preinstalled in Claude's workspace; elsewhere, `playwright install chromium`).
- jsts 2.12.1, because the Deck page loads it from a CDN: `npm install jsts@2.12.1`.
- The editors' published files and databases, fetched in a Claude session:
  - Deck page and files: Artifact read of https://claude.ai/artifact/L81dVQSV8THSWai2LhZhcv. The files used are deck.json, context.json, sheets.json, tiles_n/index.json, relief.json, tracks.json, structures.json, hwy.json, norwood.json, airport.json and basin.json.
  - Deck layout: ArtifactData get, collection `deck`, document `layout`.
  - Profiles page and files: Artifact read of https://claude.ai/artifact/A5XH4264dpWHdPdDKZgDsG: lines/, rer/lines/, network.json, rer/canon.json, rer/network.json, rer/metro_rails.json.
  - Profiles alignments: ArtifactData list, collection `alignments`, with out_dir.

## Run

```
python3 extract/deck_headless.py DECK_HTML DECK_FILES deck/layout.json node_modules/jsts/dist/jsts.min.js data/deck_extract.json
python3 extract/profiles_headless.py PROFILES_HTML PROFILES_FILES alignments/ data/profiles_extract.json 5
python3 extract/summarise.py data/deck_extract.json DECK_FILES .
python3 extract/combine3d.py data/deck_extract.json data/profiles_extract.json PROFILES_FILES DECK_FILES .
python3 extract/render3d.py . data/deck_extract.json DECK_FILES data/profiles_extract.json PROFILES_FILES
```

- `combine3d.py` writes `data/_tracks3d.pkl` for `render3d.py`. It is a working file, not in the package.
- Coordinates are UTM zone 16N metres (EPSG:32616), as in both editors; levels are metres NAVD88.
- Nothing is written back to either page.

## Files

| Path | What |
|---|---|
| `extract/deck_headless.py`, `extract/extract.js` | the Deck page run headless with a stand-in database; reads stops, platforms, bored runs and every drawn track through the page's own functions |
| `extract/profiles_headless.py` | the Profiles page run headless; samples `railAt` and `typeAt` every 5 m on all 21 lines |
| `extract/summarise.py` | `data/stations_platforms.csv`, `data/lines.csv`, `data/areas/*.geojson`, and the plans of Fountain Square, CUT and Norwood Central |
| `extract/combine3d.py` | a rail level on every Deck track: Profiles levels for Metro and TRI, the Deck's own level marks for APEx, the lower level, the north trunk and the rest; `data/system3d.geojson`, `data/platforms3d.csv`, `data/conflicts.csv`, `data/coverage.json` |
| `extract/render3d.py` | `plans/north_trunk_long_section.png`, `plans/north_viaduct_sections.png`, `plans/cut_3d.png`, `plans/fountain_square_3d.png`, `plans/north_trunk_3d.png` |
| `data/` | the extracts and outputs listed above |
| `plans/` | the drawings |
