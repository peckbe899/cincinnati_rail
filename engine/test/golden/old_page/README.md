# The old page's goldens (format `old_page/1`)

Everything the old Rail Profiles page (`data/profile/profiles.html`, 3,944 lines) computes for each of the 16 Metro
lines, Lines 10, 11 and 13 (no saved profile) included: one file per line, `<Line>.json.gz`, with `index.json`
listing each file's sha256 (of the JSON text), its size, its grid size and its issue count, and the sha256 of every
source the dump read. `load.ts` reads them; `engine/test/old_page.test.ts` checks that they load and hang together.
The port of the rest of the page's engine (`claude/hub_maps/engine_port_plan.md`) is compared against them, output by
output, within the tolerances of that plan's section 6.

These files are the old page's own answers on the seed. They are never edited by hand and never "fixed": where the
port is right and the old page wrong, the difference is classed (same, rule fix with its rule id, intended) in the
port's report, not changed here.

## How they were made

1. A scratch copy of the old hub and the page, outside the repository:

   ```sh
   P2=<scratch>/parity2
   mkdir -p $P2/old/hub $P2/old/data $P2/old/tools/station3d
   cp -r hub/hub.py hub/store.py hub/pipeline.py hub/seed hub/sites hub/static hub/README.md $P2/old/hub/
   cp -r data/profile $P2/old/data/
   cp -r tools/station3d/page $P2/old/tools/station3d/
   ```

2. The copy of `profiles.html` (and only the copy) gets one line, before its own `window.__api = {` hook: `window.__P
   = { S, METRO_ST, ERA, CANON, ..., sampleGround, ..., roadChecksNow, ... }`, which hands the IIFE's state, 44
   tables and globals and 138 functions to the harness. Nothing else in the page changes. The dump script writes it
   and refuses any file inside the repository:

   ```sh
   node engine/scripts/old_page_dump.mjs --patch $P2/old/data/profile/profiles.html
   ```

3. The old hub on the copy, with no pipeline:

   ```sh
   cd $P2/old && python3 hub/hub.py serve --port 8791 --no-auto --no-browser
   ```

   It seeds its own `hub/hub.db` from the copied `hub/seed`, so the page reads the 43 seed alignments, the structure
   record (`params/metro_structure`), the Chronology (`chronology/segments`, 556 segments), `params/station_platforms`,
   `station_complexes`, `station_access` and `approach_extra`, and the line files and `context/lines.json`.

4. The dump, from the repository root (Node 22 and the repository's Playwright, nothing else):

   ```sh
   node engine/scripts/old_page_dump.mjs --url http://localhost:8791/profiles/ --out engine/test/golden/old_page
   ```

   `--lines Line_6,Line_2b` dumps some lines only; `--plain` writes `.json` instead of `.json.gz`. A full run takes
   about 20 s. Stop the hub after it.

`index.json` `sources.page_sha256` is the sha256 of the page as served, less the hub's shim tag and the harness
line; the test checks that it equals the repository's `data/profile/profiles.html`, so a dump from an edited page
fails. Two runs give the same bytes (checked on Line 6 before and after other lines).

## What each file holds

Chainage `c_i = min(i * step, L)`, step 2 m, `n = floor(L / 2) + 1`. The rail, grade and the two limit lines on the
grid are rounded to 0.1 mm (1e-4); the ground is exact (the DEM as the line file's decimetres, the other layers'
runs as the page's single-precision values, so a port fed from them makes every threshold fall the same way), as
are the 10 m radii and curve allowances; everything else is as the page computed it. The line file's ground has
one sample more than the grid on most lines (`sampleGround` clamps to the last). NaN and the infinities are written `"__NaN__"`, `"__Inf__"`,
`"__-Inf__"` and restored by `load.ts`. Categorical lists are run-length `[[value, count], ...]` (`unrle()`); ground
layers are the DEM in full plus, for each layer above it, the runs where it differs from the one under it
(`ground()`).

| Member | The page's function (profiles.html line) |
|---|---|
| `settings`, `era`, `canon_record` | the effective settings with the line overlay (585), `ERA[id]` (1186), `CANON[id]` (293) |
| `align` | `S.align` after `alignFromDoc` (1869), `changed()` (3141): locks, junction PVIs |
| `stations[]` | per live station: key, point, centre, rail, sg, so, stt, `refAt` (930), ground, surface, `typeAt`, the solver's role and platform default, `platKind`, `phaseAt`, `chrStationYear` (483), `sgMaxFor`, `stationAccess` (503), `platformCurve` (2030), `stationStreet` (458) |
| `grid.rail`, `grid.grade` | `railAt`, `gradeAt` (803, 817), per mille |
| `grid.type` | `typeAt(c, railAt(c))` (1669) |
| `grid.solved` | `stretchTypes()` (1335): `t`, `tube`, `part` ('a' approach, 'S' station), and that its `z` is the rail |
| `grid.tube_key`, `phase`, `point`, `ovr`, `canon`, `lock`, `tf`, `station` | `tubeKeyAt` (1119), `phaseAt` (1091), `pointType` (1246; `cls:C/E/B`, a `*` for a station sample), `overrideAt` (833), `canonAt` (1041), `lockAt` (911), `tubeFormAt` (1124), `stationAt` (611) |
| `grid.grade_limit` | `gradeLimitAt` (1142) as `lim|warn` |
| `grid.struct`, `limit_tube`, `limit_box` | `structFor(type, c)` (1202) as `k|below|top`; the legal band's two dashed lines (2525-2532) |
| `grid.ground` | `S.groundDem` (`dem_dm`), `S.groundReg` (regraded, 649), `S.ground` (finished, 686-702), `surfaceAt` (706), `bedAt` (710), `madeBedAt` (1032) |
| `ten.radii`, `ten.allowance` | `radii` (1952) and `curveAllowance` (1975) on the 10 m grid (radius null where straight) |
| `solve` | `stretchTypes()`: `bad`, `platDef`, `stRole`, `shafts`, `flags` (every Tunnel method, Painted, Tube form, Approach box, Low cover flag), `approaches` |
| `eff_ovr`, `chr_segments`, `canon` | `effOvr` (837), `chrSegments` (1077), `S.canonSecs`, `canonFixed`, `canonModes`, `canonLocks`, `canonPiers`, `canonDeck` (876) |
| `rivers`, `sunk_box`, `river_bridges` | each river with `bedOf`, `navigable`, `alongShore`, `bridgeOf`, `riverBand` (1017); `sunkBox` (1007); `riverBridges` (993) |
| `viaduct_spans`, `misfits` | `viaductSpansNow` (954), `paintMisfits` (1637) |
| `crossings` | `crossingClearancesNow` (2235), each with the neighbour doc it read: `saved` (the other line's saved profile), `default` (RER), `metro_rails` (the stale `rer/metro_rails.json`, for crossings with Lines 10, 11 and 13) |
| `context`, `roads` | `contextClearancesNow` (2219, the block as its index in the line's context), `roadChecksNow` (2263) |
| `gnd_cross`, `gnd_checks`, `drawing`, `curve_grade`, `design` | `S.gndCross` (674), `gndChecks` (1731), `drawingFlags` (2060), `curveGradeRangesNow` (1987), `designChecks` (2081) |
| `summary` | `computeSummary` (1900) |
| `issues[]` | `allIssues(summary)` (2143): kind, severity, c, text (and plain text), fix, clear, propose, and two members the page does not keep: `src`, the list and index it came from in this dump (`issues_src_ok` says the order matched), and `c0`, `c1` with `range_from` (`source`: from that list; `platform`: c plus or minus half a platform; `text`: the "from 1+145 to 1+205" of the text, whole metres; `point`: c alone) |
| `levels.default_align` | `defaultAlign(null, [], align.stt)` (1756) on the live, slid stations: what `alignFromDoc` takes before the saved levels, the level solver for every line |
| `levels.reframe` | `reframeDoc` (1839) on a copy of the saved doc: `changed`, and the mapped pvi, ovr, tf, shafts, gnd, so (Line 2b is the one Metro line it changes) |
| `levels.propose_fill` | `proposeFill(c0, c1)` (1684) for every issue that offers it: the message and the drawn line it adds; each is undone at once (dirty flag cleared, drawn ground put back), so nothing is saved |
| `levels.reset` | `alignFromDoc(null)`: Reset this line |

## Known faults of the old page the dump keeps

- Each "is a mined station inside a cut-and-cover stretch" flag is pushed once per 2 m sample of the platform (61
  copies for a 121.92 m platform): 1,154 stretch flags on the 16 lines, 674 distinct.
- Crossings with Lines 10, 11 and 13 read `rer/metro_rails.json`, which is stale (35 crossings).
- The seed docs' derived `stations[].type` differs from the page's own type today on 29 of 351 stations: the dump,
  not the seed's derived fields, is the golden.
