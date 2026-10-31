# Code audit: Rail Profiles, the Python copy, Station 3D and the hub (31 October 2026)

Ben: "audit all of the code for the profile and 3D code. Is there anything that could be streamlined, improved, or
replaced with a better technique?" Three readers went through the code in parallel; spot-checked by hand.

Files: `data/profile/profiles.html` (3,250 lines, one script), `railsim/metro_profile.py` (1,716), `tools/station3d/sync.py`
(1,357), `context3d.py` (576), `harness.js` (109), `page/index.html` (1,121), `hub/hub.py`, `store.py`, `pipeline.py` (920).

## The one structural fault behind most of the rest

**The rules exist in three places and the build runs two browsers to read them.** The tunnel rules are written once in
the Profiles page (JS), copied by hand into `metro_profile.py` (Python, for tests and the run-time model), and Station 3D
gets them a third way: `sync.py` starts Chromium through Playwright, loads the Profiles page once per line and the Deck
page once, and samples `railAt / typeAt / tubeAt` every 5 m (`harness.js` 71-104). That is why a 3D build takes about
two minutes, why `DECK_EXPOSE` names 30 private functions of the Deck page and breaks on any rename, and why every rule
change this week had to be written twice and checked for parity.

**Better technique:** one rules engine. Pull the geometry and the tunnel engine out of `profiles.html` into a DOM-free
module (`profile_engine.js`: `vertices`, `design`, `railAt`, `pointType`, `solveTypes`, `defaultAlign`, the checks). The page
imports it; `sync.py` and the tests run it under plain Node (`node engine.js job.json`), no browser. `metro_profile.py`
shrinks to a thin wrapper (and railsim can read solved types exported per line into `hub/seed`). Builds go from minutes
to seconds, the parity test and `_js_round` / float32 tricks disappear, and a rule is written once. Large job, highest payoff.

## Profiles page (`profiles.html`)

Problems found
- The "what structure is this point" decision is written four times (`pointType` 1019, `base()` in `solveTypes` 1126,
  `kindAt` 1748, `openTypes` 1093) and has already drifted (`kindAt` lacks the covered-way and station-centre rules).
- The same helpers are re-written: cut a range out of a paint list (3 times), chainage to lon/lat (4), merge samples into
  ranges (8), station lookup by chainage (5 inlines beside `inStation` and `inPlatform`, with two different tolerances),
  the grade-limit smoothing loop (4).
- Expensive recomputation: `phaseAt` runs about five times per 2 m sample inside the solver; `typeAt` is called per pixel
  column in `draw()` and again per sub-sample; `crossingClearances()` runs five times per edit and rebuilds the other
  line's vertical curves each time; `curveGradeRanges()` runs in the checks and again every frame; a drag rebuilds `VERTS`
  on every pointer move, which empties every cache, so each frame re-solves the whole line.
- Caches are properties bolted onto arrays (`VERTS._types`, `verts._d`, `d._R`, ...) keyed by object identity; nothing
  states what a solve depends on. `SOLVING` and the `applyFill` / `solveTypes` order dependence are symptoms (the fill never
  sees the driven tube form).
- `draw()` is 440 lines mixing rules and drawing; `solveTypes` builds HTML-escaped flag text with the UI's unit state, so
  the engine cannot run without the UI.
- Dead code: `riverTubes(md)` ignores its argument; line 1957 has two identical branches; `yRangeFor(view, plotW)` never
  uses `plotW`; `settings.tubeCover` is read nowhere.
- Correctness: `fmtCh(1999.6)` prints "1+1000"; the `vertices` sort is not stable when two vertices share a chainage;
  `setAtMember` compares levels with `===` so a 4 mm difference propagates a save; platform membership uses `<= half`
  in one place and `< half + 2` in another; `autoType` silently falls back to the old per-point rule when the z it is
  given differs by more than 0.3 m; live sync can re-run the solver on a round-trip difference; no `aria-live` region.

Improvements (size, payoff)
1. Shared helpers and the dead code (small; fewer drift bugs, roughly 2x faster solve).
2. Declarative flags: `{kind, sev, c0, c1, data}`, text rendered in the UI (small; the engine frees itself from the UI).
3. Hoist the per-frame rule work out of `draw()`; skip the solve during a drag (small; smooth drags).
4. Precomputed arrays on the 2 m grid (`rail`, `grade`, `phase`, `type`, `struct`, `tube`) instead of per-sample functions
   (medium; removes most per-sample cost and simplifies every check).
5. One `derive(align, ground, settings, records)` pass per edit with an explicit key, replacing the identity caches,
   `SOLVING` and the `withLine` state swapping (medium).
6. Module split (engine / model / UI) and Node tests of the engine on the saved lines (large; see above).
7. Accessibility: status announcements, severity not by colour alone (small).

## The Python copy (`metro_profile.py`)

Problems found
- `rail_at` (824) is called once per 2 m sample inside Python loops and loops over every vertical curve with numpy masks
  each time: about 2 million tiny numpy calls per line, 9 s per solve. `_phase_at`, `river_at`, `in_station`,
  `override_at`, `canon_at` are linear scans per sample.
- Duplicates: 13 functions mirror the editor; inside the file the "station is one type" rule is written three times,
  `base()` repeats half of `_point_type`, the sliver pass is a copy of `_absorb_short`.
- Legacy paths kept only to replay the 6 October parity fixture: `legacy_structures`, `minCover_override`,
  `trough_override`, `ERA`, the `METRO_ST` fallbacks. Unused: `river_tubes(md)`, `made_bed_at`, settings `clearMin`,
  `tubeCover`, `minBoredCover_m`.
- Caches keyed by `id()` of arrays, omitting paints and settings; `struct_for` reads `self._types["tube"]` without checking
  its key, so results can depend on call order.
- Samples are dicts with string keys and sentinels; nothing checks spelling.
- Correctness: a station with no ground gets level 0.0 m silently (`default_align` 520, 560); `_chr_segments` always reads
  the repo's `chronology_lines.json` even with `records="hub"`; `_sample` clamps beyond the array instead of nan; `summary`
  degrades silently to the old rule when the solve is stale.

Improvements
1. Vectorise: compute the rail once per design over the whole grid with `np.searchsorted`, then index (small to medium;
   about 10x faster tests and tools). Do first.
2. Fix the cache keys with a version counter (small). Remove the legacy flags once the parity fixture is regenerated (small).
3. Dataclasses and enums for samples and flags (medium); split `_stretch_types` into named steps (medium).
4. Then replace it with the shared engine (large).

## Station 3D and the hub

Problems found
- Two headless browsers per build (above); `harness.js` never fails on a page error, so a crashed page can yield stale
  samples or a 60 s timeout; the Deck hook regex-patches the page source.
- `sync.py main()` is 985 lines with nested closures, reused names (`pieces`, `plats`, `L`, `tracks`), and module globals
  (`MS`, `CHR`, `STATIONS`, `PIECES`, `TUBE_AT`) that `load_ms` mutates; nothing in it runs in isolation.
- Geometry duplicated a third and fourth time: tube/box dicts in `sync.py`, the editor and the 3D page; half-spacing rules
  in the Deck page and again in `sync.py`.
- Size: `harness_out.json` 27 MB, `deck_live.geojson` 22 MB rewritten every run, snapshot 7.5 MB in 39 parts, all
  downloaded and rebuilt on every page load; the exaggeration slider rebuilds every mesh.
- The hub: `Store.update` reads then writes outside a lock (two concurrent saves can lose one); `platform_tie` ignores a
  failed versioned write; `Store.emit` swallows listener exceptions; `Pipeline.sh` keeps only the last 6,000 characters of
  a log, so a traceback can be lost; `job_3d` writes the snapshot before the params, so a mid-run failure leaves them apart.
- Derived files written into git on every run (`rer_routes.geojson`, `station_platforms.json`, `approach_extra.json`,
  `viaducts.json`, `metro_rails.json`, the context): the source of this week's blocked pulls and seed conflicts.
- Correctness: `metro_phase` only imports because `main()` mutates `sys.path`; `locate` can match the wrong leg at a sharp
  bend and the fold-back guard drops points silently; `plat_type` keeps the first platform seen for a station name.

Improvements
1. Lock `Store.update`, honour `if_version`, fail the build on a page error, keep whole logs (small; stops silent data
   loss). Do first.
2. Stop committing derived files: write them to `hub/work/` or hub records and generate repo copies in `prepare()` (small).
3. A snapshot schema and a `sync.py --check` mode that validates without writing (small).
4. Per-line cache keyed by a content hash of its inputs, so unchanged lines are not re-sampled (small to medium).
5. Split `main()` into steps with typed inputs and no globals (medium; unlocks tests and caching).
6. Incremental parts and page group rebuilds; instanced meshes for piers and arches; exaggeration by a matrix, not a
   rebuild (medium).
7. The shared rules engine removes the browsers from the build altogether (large).

## Suggested order

1. Cheap and safe, this week: the hub locks and failure handling; derived files out of git; shared helpers and dead code
   in the page; vectorised rail in Python; cache keys.
2. Medium: precomputed grids and one derive pass in the page; split `sync.py` and `_stretch_types`; schema and `--check`;
   per-line cache.
3. Large, when there is time: the single engine module, Node tests, and the Python copy reduced to a wrapper.
