# Code scrutiny: Rail Profiles, the Deck, Station 3D and the hub (6 November 2026)

Ben: "scrutinize the whole thing right now (rail profile, deck creation and 3D map) to see where the current code is
fine, and what could do it better or faster or simpler." Three readers went through the three tools function by
function with the same brief; this merges their findings with the 31 October audit. Line numbers: `profiles.html`
bare, `py:` for `railsim/metro_profile.py`, `deck:` for `hub/sites/deck/index.html`, `sync:` for
`tools/station3d/sync.py`, `page:` for `tools/station3d/page/index.html`.

## 1. The verdict

- **Keep and port (about a third):** the vertical geometry (PVIs, parabolic curves, level transitions), the ground
  layering, the canon and locks logic, the paint-misfit and fill-proposal maths, access and halls, road clearance,
  the design checks, the editing and undo model, the exports; in the Deck, the street, block and plot operations
  (`applyOps`, `rebuildPlots`, the constant-radius refit) and the station cards; in Station 3D, the camera, presets,
  cutaway, level filter, LOD, labels and downloads; in the hub, the versioned records with If-Match, the bounded
  history, the seed three-way merge, the single SSE connection through a worker.
- **Rewrite (about half):** the level solver, the phase and grade-limit lookups, the tunnel-method solver, the
  crossing clearances, the RER junction propagation, the drawing, the panels, save and live sync; the Deck's data
  loading, rendering, transit lines and platforms, edits and save, and the Deck tie; Station 3D's track matching,
  platforms and types, issues, snapshot format, mesh building and exaggeration; the hub server, the pipeline, the
  event payloads.
- **Drop:** the headless harness and every regex-exposed internal; `metro_profile.py`'s parity code (the
  `legacy_*` branches, `_js_round`, the `_stretch_types` copy); `station_access_report.py` as a third copy of the
  rules; the one-shot migration scripts (`deck_widen.py`, `metro_deck_segs.py`) once recorded; the `window.claude`
  shim and HTML injection; committing derived files.

Nothing in any of the three is worth replacing with an outside engine. The faults are structural (three copies of one
line, rules in four places, decisions per sample, keys made of names and coordinates, whole-document saves, browsers
as calculators), and structural faults are fixed by the model and the contract, not by a library.

## 2. Rail Profiles

| Group | Verdict | Action | Better, faster or simpler |
|---|---|---|---|
| Path and chainage (617, 866, 3809) | sound, slow: `pathAt` scans from the start every call, exports quadratic | port | cumulative-length array with binary search; `flatbush` for chainage from lon/lat |
| Ground layers (636-712) | sound, tangled (`S.ground0` aliasing 702, 1876) | port | one immutable `Float32Array` per layer, finished ground built once per edit; fed by `region.ground` |
| Vertical geometry (725-828) | sound; sort comparator not antisymmetric (739) | port | `rail[]` and `grade[]` once per design on the 2 m grid by a merge sweep |
| Level solver and defaults (1756-1869) | fragile: O(N²) envelope (1772), a missing level becomes 0 m silently (1775), nothing constrains the ground between stations, infeasibility unreported | rewrite | forward/backward sweep for the envelope; then an LP/QP proposer over the grid (cover, clearance, river bands, grade, vertical curves as constraints; OSQP or HiGHS) |
| Canon, locks, rivers (293-323, 876-1037) | sound, data in code (Metro canon hard-coded at 293) | port logic, move data | canon to records; per-sample canon and river index arrays |
| Phase, tube, grade limits (1076-1245) | fragile: linear scans per call (1091-1106); `gradeLimitAt` circular on `typeAt` (1149); `sustainedGrade` nested sampling (1171) | rewrite | `phase[]`, `limit[]` arrays; sustained grade from prefix sums |
| Tunnel-method solver (1246-1605) | right shape since 4 Nov, still fragile: four point-type rules that disagree (1255, 1378, 2201, 1631), pass order still decides (method chosen 1494 before approaches 1444 and `absorbShort` 1528), about 25 distinct thresholds and 200 numeric literals in 1360-1604 | rewrite from the registry, 4 Nov code as reference | typed arrays, segment by anchors, one pure decision per stretch with rule ids, then a constraint check; flags as data `{kind, sev, c0, c1, data}` |
| Paint misfits, fill (1627-1753) | sound (two-sweep slope envelope 1701); UI and undo inside the engine (1725) | port | Visvalingam within the 0.3 m band; engine never touches the UI |
| Access, halls (462-541) | sound; recomputed per 10 m sample (2121) | port | memoise per station per model |
| Road clearance (445-461, 2263) | sound; linear `.find` per sample inside the solver (1369) | port | street id per 2 m sample |
| Context and crossing clearances (2182-2246) | fragile: `kindAt` re-derives the other line's structure from depth | rewrite | read the other line's solved type array |
| Design checks (1900-2160) | sound, tangled; 3-point radii on KMZ corners (1952) | port | run on the arrays; `fitRadius` by least squares; radii from the horizontal alignment once it exists |
| RER junctions and shared stretches (330-444) | fragile: `===` on levels (356), global swapping (409), conflicts swallowed (440) | rewrite | junctions as equality constraints, shared stretches as nodes in one network solve |
| Drawing (2276-2869) | sound, slow: `railAt` + `typeAt` + `structFor` per pixel column (2457), `madeBedAt` per pixel (2488) | rewrite | draw from arrays with per-column min/max; static layers on an offscreen canvas |
| Panels (2870-3134) | tangled: full `innerHTML` rebuild and full summary per change | rewrite | render flag data (Preact or lit-html); `aria-live` |
| Editing, undo (3135-3192) | sound | port | as is |
| Save, load, live sync (3193-3404) | fragile: any saved alignment re-solves every RER default (3264); six listeners each run `changed()`; `withLine` swaps 22 globals (3375) | rewrite | one engine instance per line, no globals; results keyed by input hash; debounced events |
| Interaction, `regradeDrive`, `solveCross` (3405-3726) | mixed: monotone-chain hull correct (3653), margin bumped heuristically (3672); `solveCross` greedy and order-dependent (3709) | rewrite the solvers, keep the UI | both become constraints in the proposer |
| Exports (3777-3944) | sound | port | the Node-run engine exports the per-line arrays |

**`metro_profile.py`:** the `legacy_*` branches, `_js_round`, the float32 casts and the whole `_stretch_types` copy
exist only for parity (py:269-2046 in places); `route_profile` and `overlay_profile` (py:2235, 2260) are the only
path into run times and are kept as the adapter until the contract replaces them; `rail_grid` (py:1010) is the one
vectorised piece worth keeping as an example.

**Hotspots:** a full re-solve on every edit and every remote event (3141, 3264); `draw()` per frame per pixel; drag
clears every cache per pointer move (3453) and falls back to the old per-point rule when the rail moves over 0.3 m
(1607); `sustainedGrade` windows × samples (1167); Python per-sample loops (py:1255, 2205, 2250).

**What an engineer's tool has that this doesn't:** a horizontal alignment (arcs, spirals, cant, design speed; radii
today come from 3-point circles on drawn corners); a profile proposer (nothing optimises under cover, clearance,
grade and vertical-curve constraints; Regrade and Solve crossings are local patches); quantities (no cut, fill, box
or bore volumes since the cost model was removed); vertical curves by speed (K-values, comfort); crossings checked at
one chainage with no skew; named alternatives compared side by side; constraints reported as binding.

## 3. The Deck

| Group | Verdict | Action | Better, faster or simpler |
|---|---|---|---|
| Data loading (deck:2784-2810) | poor: 11.8 MB JSON (2.8 MB gzipped) in a waterfall, 32,464 plots decoded and replayed with JSTS on the main thread, JSTS from a CDN | rewrite | one manifest, parallel fetches; vector layers as PMTiles or FlatGeobuf read for the view; plots as tiles; first paint under 1 MB |
| Canvas rendering (deck:1406-1629) | poor: full redraw per frame, `getBoundingClientRect` per vertex (365), `feats()` scans 5,600 features about 30 times a frame (828), basin streets stroked twice uncull | rewrite | MapLibre: raster source for the Sanborn sheets, vector sources for the rest, a GeoJSON layer for the thing being edited; 10 to 100× less work per frame |
| Street, block, plot editor (deck:412-574, 814, 1030-1197, 2359-2598) | fair logic, poor host: JSTS on the main thread, O(n²) block joining (1164), caches cleared wholesale (1194), widths keyed by vertex index (898-913), no snapping | port the logic, rewrite the host | `applyOps`, `rebuildPlots`, `FA` in a DOM-free module in a Web Worker; rbush for hit-testing and snapping; widths by distance along the line |
| Transit lines and platforms (deck:592-766) | fragile: line ids carry coordinates, station keys carry names and coordinates (669), all Metro lines redrawn from settings on every tick (727), caches keyed on a global `S.ver` | rewrite | lines as sections with ids and chainage; platforms as `{lineId, s0, s1, type}`; caches per line |
| Slides (`so`) | two key schemes for one platform (Profiles `name#i`, Deck `stations[key].s[pid].o`) | rewrite | one platform id shared by both |
| Station cards and params (deck:2160-2205, 2813-2823) | acceptable; default type by `name#` prefix (716); `pickAll` linear over every street (1944) | port | bind to ids; spatial index |
| Edits, undo, merge, save (deck:2474-2521) | fragile: whole 325 KB document per save (2488), undo as 200 whole JSON strings, conflict replaces the other side's `plotOps` wholesale (2519), live updates ignored while unsaved | rewrite | append-only operations with ids (JSON patches), inverse ops for undo, per-record versions; saves under 1 KB |
| Deck tie (`pipeline.py:56`, `harness.js`, `rer_deck_routes.py`) | poor: a street edit triggers it; Chromium boots the whole page; a 22-27 MB export to keep six layers (`pipeline.py:223`); 1 m brute-force projection (262); writes git-tracked `data/profile/**` (258); Windows bug `fn.split('/')` (665) so junction points never update there | rewrite | shared geometry under Node or Python, no browser; trigger only on `transit` or `stations` changes; `line_locate_point`; derived output to `hub/work` only |
| Platform tie (`platform_tie.py:78-147`) | fair; keys carry coordinates (122) | port | key on the platform id |
| Profile context (`make_profile_context.py`) | mixed sources, name keys (110-138) | port | one versioned base |
| Viaduct parts, chronology routes | acceptable; name keys | port | ids |
| `deck_widen.py`, `metro_deck_segs.py` | migrations never recorded | drop after recording | versioned migrations |

**Hotspots:** opening (12 MB, the replay, 2.75 MB of overviews on by default); every frame; every drag tick (`S.ver++`
throws away every line's geometry); every save (whole document, then Chromium, then the export, then the brute
force, then rewrites into git); the plot rebuild (O(n²), wholesale cache clearing).

**Fragile:** keys made of names and coordinates (`metro:Syacmore:715445:4331182` carries its own typo; fixing the
name orphans Ben's settings); plot ids that depend on replay order (`X~a`, `X.1`), so a street edit that cuts a plot
differently renames its pieces; whole-document saves; two drifting copies of the base files (`hub/sites/deck/context.json`
against `data/deck/context.json`); the regex hook.

**Must survive unchanged:** street ids (`S…`, `SB…`, `SM…`, `SV…`), block ids, plot ids with their suffix grammar,
every field of Ben's layout (`streets c,k,w,wv,ov,jo,n,del,into,mg`; `blocks t,n,u,lk,arc`; `transit c,k`;
`stations s.{pid}.{t,o},del,complex`; `plots u,n`; `plotOps m,s,d,r,f`), the Sanborn layers (basin 5,204 features,
sheets 386, plots 32,464 with 2,842 labels, the rasters). How: freeze the base files as a hashed "base v1"; write the
alias table (old key to id) once; port `applyOps` and `rebuildPlots` unchanged into a module; a golden test replays
the seed layout through the old page once and the new module and compares ids and geometry hashes.

**Orphaned files (no generator in the repo):** `deck.json`, `basin.json`, `plots.json`, `sheets.json`,
`context.json`, `tracks.json`, `structures.json`, `hwy.json`, `norwood.json`, `yard.json`, `relief.*`, the tile sets
(the generators named in the Sanborn chat are in the Topography export, not the repo). These are inputs now; they
freeze as base v1.

## 4. Station 3D and the hub

| Group | Verdict | Action | Better, faster or simpler |
|---|---|---|---|
| Harness (`harness.js`) | poor: a Chromium context per line, a fixed 1 s wait before reading (76), `railAt/typeAt/tubeAt` every 5 m in the page (about 144,000 calls per build), the Deck regex-patched with 30 private names | drop | the engine under Node over solved 2 m arrays; minutes to seconds |
| Line sampling and cache (sync:374-442) | fair idea, dead expression reads every overlay (407), the Deck always reruns (430) | keep the idea | content-addressed solve per section as a record |
| Track-to-line matching, interlining (sync:675-909) | poor: exists only because Deck paths and Profiles paths differ; nested closures, the index built twice, three `near()` calls per sample, a silent 0.5 m fold-back guard (722) | rewrite | one plan geometry per line; matching becomes an id join; the 120, 60 and 30 m tolerances disappear |
| Platforms, types, defaults (sync:917-1475) | poor: `metro_tube` `argmin` over the whole line per sample (140, called at 1177, 1246, 1475: O(n²)); first-platform-wins (1167); spacing fallback written twice | rewrite | solved section per chainage from the engine; checks as flags |
| Context (`context3d.py:260-566`) | fair geometry, slow: `finished()` lambda per point (293-305) | port | vectorised `finished()`; one cached glTF per structure |
| Ground tiles (`context3d.py:569`) | fair, slow for the same reason | rewrite | `region.ground` COGs or a heightmap per tile served with Range |
| Issues (sync throughout) | poor: free text with `[:6]` truncation, not filterable, not locatable | rewrite | typed `{kind, sev, line, c0, c1, data}`, clickable to a camera position |
| Snapshot format (sync:204-222, 445-532) | poor: JSON inside a JSON string (514), 200 KB parts for a limit that no longer exists, validation checks key presence only | rewrite | a typed schema; one GLB per section plus a small index; ETag and gzip |
| Page mesh builders (page:248-645) | fair: merge by colour good; `groundAt` Map lookup per vertex (207-226); one `ExtrudeGeometry` per platform (541); box helpers copied three times | rewrite | server-built GLB per section; `BatchedMesh`/`InstancedMesh` for piers, columns, equipment |
| Arcade (page:979-1105) | good design; triangle soup rebuilt on camera moves (1125) | port | bay and pier kits as instanced geometry, built once per face run |
| Clipping, cutaway (page:190, 754, 1112) | good, cheap | keep | add stencil caps so cut solids read as solid |
| Camera, views, labels (page:158-166, 774-828) | good: true-bearing presets, double-click recentre, saved views | port | labels as an SDF atlas |
| Exaggeration (page:759-767) | poor: full dispose and rebuild per slider step | rewrite | vertex shader `y = g + (z − g)·k` with ground as an attribute; zero rebuild |
| Hub server (`hub.py:141-286`) | fair: `no-store` on everything including three.js (156), no Range, ETag or gzip, whole file read into memory, path containment by string prefix (204, so `/hub/../hub.db` is reachable), PATCH and DELETE without If-Match (257-267) | rewrite | FastAPI: ETag and Range on static, SSE, If-Match on every write, real containment |
| Store (`store.py:20-278`) | good core: `set` with `if_version` correct (58), merge bases fall back saved base → history → git (219) | port | per-record versions on smaller records (one per street, block, station), so the merge is per record |
| Pipeline (`pipeline.py:56-327`) | poor: database copied to files every run (165), the Deck booted twice (221 and sync:430), 3d can run twice (318), snapshot written before params (271) | rewrite | one in-process derive graph keyed by input hashes, outputs in one transaction |
| Live updates (`events_worker.js`, `shim.js:51-72`) | good worker; every event refetches the whole collection (shim:56), a new snapshot refetches all 39 parts (page:1134) | keep the worker, rewrite payloads | events carry `{path, version, changed sections}`; fetch only changed GLBs |

**Where the 143 s build goes:** 41 line loads in Chromium with fixed sleeps and 144,000 per-sample calls; the Deck
booted twice; `station_access_report.py` re-solving every Metro line in Python (about 9 s each) against stale repo
profiles (it reads `hub/seed/alignments` with no `--seed`, `pipeline.py:294`); the O(n²) Python loops; a 7.5 MB
snapshot re-fetched whole with `no-store` and rebuilt from scratch.

**Duplicated in four places:** structure sizes (`METRO_ST`, `RER_ST`, `OPEN_ST` sync:49-58 against 1052, 1202, 1007
and `context3d.py:516`); half-spacing rules (deck:609-668, sync:1105-1113, 1130, 1184, page:492); the TRI box wall
(5.0 m `context3d.py:514` against 3.25 + 1.75 sync:67); platform height (sync:43, `context3d.py:46`, the structure
record); `enc`/`dec`, `on_line`/`projectOn`, `resample`/`densify`; structure-type names in four vocabularies; station
grouping thresholds 150, 400, 600 and 800 m in different files.

**Tests:** `tests/test_hub.py` covers the store and the trigger table; nothing tests the sync steps or the page;
`hub/test_hub.js` needs a live hub and fixed sleeps.

## 5. What this changes in the plan (added to the checklist)

1. **Arrays, not functions.** Every engine quantity (`rail`, `grade`, `phase`, `type`, `struct`, `tube`, `street`,
   `canon`, `river`) is a typed array on the 2 m grid computed once per edit; drawing, checks and exports index them.
   This is the single biggest speed change and it also removes the four disagreeing point-type rules.
2. **A horizontal alignment** as real geometry in the model (arcs, spirals, cant, design speed), with the plan strip
   editable by R and spiral length, radii and speed limits derived, the KMZ polyline kept only for import.
3. **A profile proposer** (LP/QP over the grid: station levels, cover, clearances, river bands, grade and vertical
   curve limits as constraints; cut, fill, box and bore as cost) beside the solver, never overriding Ben; Regrade and
   Solve crossings become constraints in it. Options: OSQP (QP), HiGHS (LP/MIP), or a dynamic-programming sweep.
4. **Quantities** from the ground model and the structure solve, so the cost measure is real and checkable.
5. **Flags as data** with rule ids everywhere; no UI text in any engine.
6. **The Deck's editor logic ported unchanged into a Web Worker**, its rendering moved to MapLibre, its layout saved as
   append-only operations with ids, its base files frozen as base v1 with an alias table and a golden replay test.
7. **One platform id** shared by the Deck, the Profiles and the model; one section id per line; no key that carries
   a name or a coordinate.
8. **Station 3D rebuilt from GLBs per section** built server-side once and cached; exaggeration in the shader; the
   camera, presets, cutaway, level filter and exports kept.
9. **The hub server rewritten** (Range, ETag, SSE, If-Match on every write, real containment); the store's versioned
   records and seed merge kept on smaller records; the pipeline replaced by the derive graph; events carry payloads.
10. **Two bugs to log now:** the Windows `fn.split('/')` in `rer_deck_routes.py:665` (junction points never update on
    Ben's machine), and `station_access_report.py` reporting on stale repo profiles. Both go away with the rewrite;
    the first is worth a one-line fix in the old hub if Ben keeps using the tie meanwhile.
