# Profiles engine and line data: map for the hub architects

Read only. Line numbers are bare for `data/profile/profiles.html` (3,944 lines, one IIFE script from 251 to 3944) and `py:` for `railsim/metro_profile.py` (2,309 lines).

## 1. Data on disk (shapes, counts)

**Line files.** There are 16 Metro lines in `data/profile/lines/*.json` (index.json lists them: 390.5 km, 436 stations). There are 30 RER files in `data/profile/rer/lines/`: the 25 in its index.json (5 trunks and 20 branches, 330.0 km, 146 stations) plus the legacy cores RER_1..5. Every file has `step_m` 2.0.
- Fields: `id`, `line`, `system`, `length_m`, `step_m`, `path` [[c, lon, lat]] (83 to 1,049 points), `stations`, `rivers` [{name, c0, c1}], `crossings`, `pieces`, `segs`, `route_chainage_m`, `color` (KML aabbggrr), `ground_note`, `src_flags` (always empty).
- `ground_dm`: int dm NAVD88. Range 1230 to 2861. null becomes NaN. One value per 2 m.
- `stations`: {name, c, ground, offset, lon, lat}. RER adds `trunk`. CVG adds `src`.
- `crossings` (216 on the Metro, all `kind: metro`): {c, wid, oc (the other line's chainage), kind, with}. Metro×RER crossings sit only on the RER file; `linkRerCrossings` (3395) merges them in.
- `pieces`: {name, id "System|Line|Piece", c0, c1, reversed, gap_before}.
- `segs` (the Deck tie): {piece "M-L1-714264-4343661", lines, pa, pb, fwd, u/v [E, N in EPSG:26916], c0, c1}.
- Metro files only: `ground_dm_lidar`.
- RER files add `letter`, `kind`, `short`, `service`, `opened`, `trunks`.
- CVG_Express adds `variant`, `opened` 1969 and `settings: {platform: 204.216}`, the only per-line settings overlay.
- Station key: the name, or `name#idx` (index in the line file) where a name repeats. The only case is Line_8 `Cincinnati State#2` and `#3`.

**Saved docs.** `hub/seed/alignments/*.json` holds 43 docs: 13 Metro (no Line_10, 11 or 13) and 30 RER. `serialize()` (3213-3229) writes them:
- `v`: 1
- `system`, `line`, `length_m`, `platform_m`
- `st`: {key: rail m}. 564 in total.
- `sg`: {key: platform grade in ‰, rising with chainage}. 149.
- `so`: {key: slide in m; platform centre = point + so; ±150 allowed, a larger slide is flagged, never clamped}. 109.
- `del`: [keys]. 6.
- `pvi`: [[c (0.1 m), z]]. 1,210.
- `ovr`: [[c0, c1, type]]. 122: cutcover 79, shield 26, elevated 7, deep 6, trough 3, atgrade 1. The legacy value 'bored' reads as 'shield'.
- `stt` (Metro): {key: cutcover|shield|deep|elevated}. 10.
- `tf` (Metro): [[c0, c1, twin|bore]]. 3.
- `shafts` (Metro): [c]. 0 used.
- `gnd`: [[[c, z]...]] lines. 6.
- `gapfill`: [keys]. 0.
- `mode` (RER): {key: under|surface}. 84 under, 129 surface.
- `ready` (true in none), `reframed`
- `route_chainage_m` (RER)
- Derived on save: `stations` [{name, c, point_c, rail, ground, depth, type}] and `summary` {km_by_type, max_grade_permille, grades_over_limit}, plus `updated`.

**Stale copies.** `data/profile/alignments/` (8 docs, saved 27 Oct to 2 Nov) and `data/profile/rer/alignments/` are older than hub/seed (Line_1: 10 vs 17 PVIs). `rer/metro_rails.json` is stale too (Line_1 Winton Hills 190.4 m vs 196.9 m in the seed). hub/seed wins.

**Records the engine reads.**
- `metro_structure.json`, also `hub/seed/params/metro_structure.json`. The seed adds a top-level `min_radius`.
  - `tubes` A/C/bore: inside, outside, rail_over_invert, spacing.
  - `box`: spacing 3.9, inside 7.9, roof_underside 4.0, below 1.0, top 4.6.
  - `island_box`: spacing 10.9, roof_underside 4.6.
  - `approach_m` 40.
  - `phases` 1/2/3/later: tube, cc_max, min_drive, deep_from, min_radius, grade_max, grade_straight, straight_warn, grade_curve, curve_radius, tbm, prefer.
  - `line_phase`, `piece_phase`, `grades`, `hall` {2.75, 0.6, 0.6}, `subway_streets` (3), `cost.cover_hard` 0.5, `portal_min_m` 100, `elevated_station.mezzanine_clear_m` 3.5, `open_clear_height` 4.57.
- Chronology: `chronology.json` (230 segments) vs `hub/seed/chronology/segments.json` (556).
  - `phase_years` [[1800, 1933, "1"], [1934, 1949, "2"], [1950, 1979, "3"], [1980, 2200, "later"]].
  - `segments` keyed `metro|Line_x|A|B` (names sorted) or `tri|A|B`, each {year, phase, src}.
  - `stations` keyed `sys|name`.
  - `chronology_lines.json`: 41 routes {id, sys, stations, segments}.
- `station_platforms.json`: {line: {key: side|island}}, 308 side and 128 island.
- `station_complexes.json`: `auto` 435 groups and `marked` 1, each {id, name, x, y, members [{sys, line, station, c, x, y}]}.
- `hub/seed/params/station_access.json`: Ben's {line: {key: {type, source}}}.
- `approach_extra.json`: {line: [{station, side, c, extra}]}, Lines 5 and 13 only.
- `context/lines.json` (207 KB, 44 lines):
  - `streets` [c0, c1, width, name, class] (522)
  - `roads` [c, c0, c1, width, name, class] (2,022)
  - `blocks` {n, l, k, st, c0, c1, p [[c, z]], b, t, o, pl, s, gaps} (47)
  - `add` and `cap` runs {i0, v[]} on the 2 m index (5 each)
- `rer/canon.json`:
  - `rivers`: Ohio (bed from the DEM, navigable), Licking, Little Miami (`bed_below_pool_m` 3, `in_covered_way`)
  - 14 lines with `modes`, `fixed` {abs}, `locked` [{c0, c1, st, pvi, ovr, src, by}] (9 lines) and `sections` (covered or deep)
  - No line uses `deck`, so `groundFor` (932) is a dead path today.
- `rer/links.json`: 5 `shared` {a, b, ca, cb, sign, pieces} and 17 `junctions` {id, p, members [{r, c, sign, st?}]} (47 members, 5 at stations).
- `rer/settings.json` and `settings.json`: page defaults with legacy key names; py `SETTINGS_KEYS` maps them.
- `network.json` (metro plans and river outlines), `rer/network.json` (adds rer) and `rer/repath_bd_trunk.json` are for drawing and the tie, not the solver.
- `station_types.json`, `station_access_rule.json`, `station_platform_default.json` and `tube_points.json` (2 MB) are outputs of the 3D build, not inputs.

## 2. Draft `SectionInput` (units in m and ‰)

```ts
type Key = string; type Type = 'elevated'|'atgrade'|'trough'|'cutcover'|'shield'|'deep'|'sunk';
interface SectionInput {
  route: { id; system:'metro'|'rer'; kind?:'line'|'trunk'|'branch'; opened?:number;
    length_m; step_m:2;                       // n = floor(L/step)+1, c_i = min(i*step, L)
    path:[c,lon,lat][]; pieces:{name,c0,c1}[]; // pieces feed phase via piece_phase
    stations:{key,name,idx,point_c,lon,lat,trunk?:boolean}[];
    rivers:{name,c0,c1}[]; crossings:{c,wid,oc,kind,with}[]; settingsOverlay?:Partial<Settings> };
  ground: { dem: Float32Array /*dm/10*/; add:{i0,v:number[]}[]; cap:{i0,v:number[]}[] };   // the finished ground is derived
  doc: { st:Record<Key,number>; sg:Record<Key,number>; so:Record<Key,number>; del:Key[];
    pvi:[c,z][]; ovr:[c0,c1,Type][]; stt:Record<Key,'cutcover'|'shield'|'deep'|'elevated'>;
    tf:[c0,c1,'twin'|'bore'][]; shafts:number[]; gnd:[c,z][][]; gapfill:Key[];
    mode?:Record<Key,'under'|'surface'>; ready:boolean;
    frame:{length_m; point_c:Record<Key,number>} } | null;   // reframe input; null means the solver default
  settings: Settings;  // see §5
  canon: { sections:{a,b,aIn?,bIn?,m:'shallow'|'deep'|'canal'|'covered'}[];
    fixed:Record<name,{abs?;off?;ref?}>; modes:Record<name,'under'|'surface'>;
    locked:{c0,c1,st:Record<name,number>,pvi:[c,z][],ovr:[c0,c1,Type][]}[];
    bridges:Record<river,{fixed?:true;clear?:number}>; decks:{pvi:[lon,lat,z][],piers:[lon,lat][]}[];
    rivers:Record<name,{bed_below_pool_m?;navigable?;in_covered_way?}> };
  era?: { shield:'tube'|'bore'; sgMax:number };   // ERA, hard-coded 1186-1192
  structure?: MetroStructure;                       // Metro only
  chronology: { phase_years; segments; stations; route? };
  stationParams: { platform:Record<Key,'side'|'island'>; access:Record<Key,{type;stages?}>;
    complexes:{line,station,sys,year}[][]; approachExtra:{station?,side,c,extra}[] };
  context: { streets; roads; blocks };
  neighbours: Record<wid,{length_m,platform_m,stations:{name,c,rail}[],sg,pvi,gnd?,ready?,streets?,solvedType?}>;
  links?: { junctions; shared };   // RER
}
```

## 3. Draft `SolvedSection`

```ts
interface SolvedSection {
  engine; inputHash; route; step_m:2; n;
  grid: { c; groundDem; groundReg; ground /*finished*/; surface /*pool over rivers*/; bed;
    rail: Float64Array; grade: Float32Array /*‰*/; type: Uint8Array; tube: ('A'|'C'|'bore'|null)[];
    part: (''|'a'|'S')[]; phase: ('1'|'2'|'3'|'later')[] };
  vertical: { dv:{c,z,kind:'ps'|'pe'|'x'|'pvi'|'end',i?,j?,gp?}[]; g:number[]; L:number[];
    short:{c,need,got,dg}[] };   // design() 750-802
  align;   // the normalised doc as arrays by station index: what the baseline `align` holds
  stations: {key,c,point_c,rail,ground,depth,type,role:'box'|'mined'|'open',platDef,
    platformCurve:{R,out,inn,level,gapfill,turns},
    access:{type,rule,source,year,phase,d,dHall,island,halls,passage,shaft,hallTop,mezz,flags},
    street}[];
  approaches: {station?,kind,side,shift,c,len,river?}[];
  bad: {why:'cover'|'box'|'roof',c0,c1,worst}[];
  misfits: {c0,c1,t,why,worst,si?}[];
  spans; bridges; riverBands:{name,c0,c1,ub,lb,low,nav}[];
  crossings; contextClearances; roads; drawn:{lines,runs};
  issues: {kind,sev:'error'|'warn'|'note',c,c0?,c1?,text,data?,fix?,clear?,propose?,ruleIds}[];
  summary: {km_by_type,maxG,maxGc,over,deepest,highest,sumps};
  doc;   // the serialize() body
}
```

Issue kinds today (ISS_CAT 2136 plus inline): Grade, Curve grade, Clearance, Context, Cover, Thin cover, River, Tunnel method, Low cover, Ground, Regrade, Tube form, Tube choice, Approach box, Canon, Painted, Unbuildable, Drawing, Platform curve, Platform grade, Platform slide, Platform overlap, Vertical curve, Drainage, Road, Access.

## 4. Engine map (function groups)

| Group | Lines |
|---|---|
| Constants, defaults, Metro `CANON` data | 256-329 (METRO_DEFAULTS 277, RER_DEFAULTS 286, CANON 293-323) |
| RER junctions and shared stretches | 330-444 (junctionsOf 337, levelAtMember 347, ensureJunctionPvis 375, copyStretch 388, propagateLinks 425) |
| Roads, access, halls | 445-584 (stationStreet 458, ACCESS 467, dHall 480, chrStationYear 483, complexOf 494, stationAccess 503-535, hallAt 536) |
| Utilities | 601-625 (pathAt 617 scans from the start, rangesOf 613, cutRange 615) |
| Ground layers | 636-712 (sampleGround 636, regradeGround 649, gnd 664-672, crossGround 674, drawnGround 686, rebuildGround 697, river, bed, surface 704-712) |
| Stations | 717-723 (baseStations, keyOf, deriveStations) |
| Vertical geometry | 725-828 (vertices 725, design 750, railAt 803, gradeAt 817, chords 828); `window.railProfile` 829-832 |
| Paints and selections | 833-862 (overrideAt, effOvr, sttFromDoc) |
| Canon and locks | 863-946 (chainLL 866, buildCanon 876, applyLocks 915, refAt 930, groundFor 932) |
| Viaducts and rivers | 948-1041 (viaductSpansNow 954, riverBridges 993, sunkBox 1007, riverBand 1017, madeBedAt 1032, canonAt 1041) |
| Structure, phase, tube, grade limits | 1052-1245 (METRO_ST 1052, applyMS 1065, chrSegments 1077, phaseAt 1091, metroTube 1108, gradeLimitAt 1142, sustainedGrade 1167, ERA 1186, structFor 1202, reqCover 1215, phaseRules 1239) |
| Point types | 1246-1334 (pointType 1246-1276, approachLen 1294, absorbShort 1299, openTypes 1319 for RER) |
| Tunnel-method solver | 1335-1604 (stretchTypes 1335, solveTypes 1360-1604) |
| Type lookup and misfits | 1605-1677 (autoType 1605, fitOf 1627, paintMisfits 1637, typeAt 1669) |
| Fill and drawn-ground checks | 1684-1754 (proposeFill touches the UI and undo at 1725) |
| Level solver and doc load | 1756-1897 (defaultAlign 1756-1807, surfacePvis 1810, reframeDoc 1839-1868, alignFromDoc 1869-1897) |
| Summary and checks | 1900-2178 (computeSummary 1900, radii 1952, curveAllowance 1975, platformCurve 2030, drawingFlags 2060, designChecks 2081-2135, allIssues 2143) |
| Crossings, context, roads | 2182-2275 (otherRail 2182, kindAt 2197, needSep 2212, context 2219, crossings 2235, memo 2253, roadChecksNow 2263) |
| Proposers (UI-bound) | regradeDrive 3601, solveCross 3693-3720 |
| Load and boot | selectLine 3352, withLine 3375 (swaps 21 S keys), boot 3905-3943 |

The model is cached on `VERTS._d`, `_types`, `_otypes` and `_fit`, keyed by object identity, and on `MODEL_V` and `memo`.

**Python port.** `load` py:258, `_align_from_doc` py:736, `design` py:919, `rail_grid` py:1010, `rail_at` py:1024, `_stretch_types` py:1357-1734, `type_at` py:1960, `summary` py:2202.
- `route_profile(mp, proj, h, grid=5.0)` (py:2235) projects each 5 m point of the fitted alignment `h` onto `path` for its chainage and returns `Profile(s, ground=surface_at, track=rail_at, grade=np.gradient (fraction), structure=STRUCTURE[type_at], True)`.
- STRUCTURE maps elevated to viaduct, atgrade to at-grade, trough to cut, cutcover to cut-and-cover, shield to shield, deep to deep-tube and sunk to sunk-box.
- `overlay_profile(prof, mp, proj, h, grid=5, tol=30, taper=400)` (py:2260) returns (Profile, share inside the core).
- Callers: `railsim/line.py:416-417` (Metro) and `442-443` (RER).

## 5. Globals and settings the engine reads

- **Settings, Metro** (277): maxGrade 50, platform 121.92, defDepth 7.62, elevAbove 3, coverBelow 3, deepBelow 18.29, shallowMax 12.19, deckDepth 1.5, poolFt 455, vcRadius 1500, vcMinLen 30.5, drainMin 3, curveK 800, stationMaxGrade 7.5, fillSlope 500, groundWarn 100, groundSustain 100, groundMax 150, sustainedLen 243.84, riverRoof 1.0, riverSink 5, riverRise 3, riverFlatTol 1, riverClearWater 3.66, riverCap 1, roadClearHighway 4.9, roadClearMajor 4.3, roadClearMinor 4.3.
- **Settings, RER** (286): maxGrade 35, platform 204.2, defDepth 12, deepBelow 25, shallowMax 18, deckDepth 2.0, vcRadius 3000, stationMaxGrade 2.5, sustainedLen 408.4. It adds envelope 6.6, boreCrown 7.5, invertDepth 1.0, surfStep 250, minCover 8.5 and tubeCover 3 (never read).
- **Settings sources**: `config/settings` and `config/settings_rer` in the db (no seed found), then localStorage, then the line overlay.
- **Global state**: `S.*` (data, L, step, ground, ground0, groundDem, groundReg, stations, rivers, crossings, align, canonSecs, canonFixed, canonModes, canonLocks, canonPiers, canonDeck, ctx, saved, defaultDocs, metroRails, rerData), `sys`, `settings`, `VERTS`, `MODEL_V`, `MODEL_SWAP`, `SOLVING`, `LAST_T`.
- **Records**: MS, CHR, CHR_LINES, ST_PLAT, ST_CPLX, ST_ACCESS, APX_EXTRA, CONTEXT, RER_CANON, RIVERS, LINKS, CANON, ERA.
- **Tables**: METRO_ST, OPEN_CLEAR {4.2, 5.8}, which MS overrides with 4.57.
- **Port differences**: py DEFAULTS has `minCover=2.0` for the Metro, which the page does not have. `settings.json`'s `structures_note` still describes the superseded "2.0 m over tubes above 140 m" rule. Metro canon `fixed` is {off|abs} on the page but bare numbers in py CANON.

## 6. Numeric literal clusters

About 2,520 numeric tokens in the script. By range:
- drawing 2276-2869: 609
- interaction and solvers 3405-3726: 236
- design checks 1950-2136: 221
- vertical geometry 717-862: 147
- solveTypes 1360-1604: 133
- exports 3727-3944: 160
- defaultAlign and reframe 1755-1898: 103
- fill 1684-1754: 94
- defaults and canon 251-329: 89

Tolerances in 251-2275: 0.5 ×34, 0.05 ×30, 1e-6 ×25, 0.005 ×17, 1e-9 ×7, 0.3 ×6 (528, 1607 autoType z-match, 1715), 0.02 ×5, 0.01 ×5.

Named literals:
- JTOL 0.6 (335), GND_W 15 (664), DECK_ON 5 (864)
- VIA_SPAN 25, VIA_CLEAR 7, RIVER_SPAN 120, GIRDER_MAX 40 (953); girder L/10+0.8, truss L/8 (987)
- BOX_COVER 0.6, SEP_GAP 0.5, BED_DEPTH 0.8 (1185), MIN_RUN 20 (1298), SLIDE_M 150 (1838)
- CAR_LEN 15.56, END_DOOR 5.4, PLAT_R 600/3000 (2008); DRAW {5, 2, 10, 10, 90, 5, 2} (2047)

Unnamed literals:
- pool()+1 means elevated over a river (1255, 1374, 2198)
- fallbacks: approach 40, min_drive 300, cover_hard 0.5, portal 100, radius 40, curve_radius 500, straight_radius 1000, mezzanine 3.5
- sample spacings: 10 m (1159, 1901, 1952 with h=4, 1989, 2118), 5 m (1168), 2 m (2033)
- 60 m drainage minimum (2107), 20 m range join, 300 m street search (1540), 400 m pier search (972), 150 m station match (397)
- regradeDrive's max(10, maxGrade−2) and 0.3 margin (3603-3606)

## 7. Walking skeleton: what to port first (path, chainage, vertical geometry, rail on a 2 m grid)

1. Utilities: clamp 602, pool 603, stationAt 611, rangesOf 613, cutRange 615, pathAt 617 (use cumulative length and bisect), chainLL 866.
2. Ground: sampleGround 636-643, regradeGround 649-657, gnd parse, level and norm 667-672, drawnGround 686-696 (crossGround 674 needs neighbours), riverAt, surfaceAt, bedOf, bedAt 704-710.
3. Stations: 717-723. Keep `name#idx` until platform ids exist.
4. Canon and locks: buildCanon 876-908, fixedLevel 909, lockAt and applyLocks 911-929.
5. Docs: reframeDoc 1839-1868, alignFromDoc 1869-1897, sttFromDoc 852.
6. Vertical geometry: vertices 725-746 (fix the comparator at 739), design 750-802, railAt 803-816, gradeAt 817-826.
7. Level solver for routes without a doc (Line_10, 11, 13) and missing keys: defaultAlign 1756-1807. It depends on riverTubes and riverBand 1017-1037, riverBridges 993, sunkBox 1007 (needs MS.box), alongShore 1015, canonAt 1041, inPlatform 3142, elevNeed 271. It also needs surfacePvis 1810 and ensureJunctionPvis 375 for the RER. Known faults: an O(N²) envelope, and a missing level silently becomes 0 m (1775).
8. Grid: rail[i] = railAt(min(i·2, L)) for i in 0..floor(L/2). This is the same as py `rail_grid` (py:1010).

## 8. Goldens (`tests/baseline/profiles/*.json`, 41 routes, 1.2 MB)

**Format.** {route, saved, c0: 0, step_m: 5, n = floor(L/5)+1 (all 41 match today's line lengths), rail_m[n] (3 decimals), type [[Type, count]] RLE, tube [[A|C|bore|null, count]] RLE, align}.

**Source.** Captured by `tests/baseline/capture.py` from the old hub's headless harness on Ben's 5 November work folder. That folder is not in the repo.

**What the samples are:**
- rail_m = railAt(c) at every 5 m.
- type = typeAt, which reads the 2 m solve at index Math.round(c/2) (JS rounds halves up) only when the rail is within 0.3 m. Otherwise it falls back to pointType. A port must reproduce this mapping.
- tube = tubeKeyAt: T.tube[i], else the phase tube. It is defined on every Metro sample and null on the RER.

**`align`** is the page's internal, normalised input after alignFromDoc, reframe, applyLocks and ensureJunctionPvis: arrays by station index, pvi as {c, z}, gnd as {c, z}.
- 20 routes match their hub/seed doc exactly.
- 18 differ in chainages only, because the page reframed them on load (RER_E_trunk by up to 260.9 m, RER_C_trunk by 32.7 m, Line_2b by 26.7 m, elevations equal).
- Locks and junction PVIs change some (RER_A_cumminsville: 11 PVIs in the seed, 3 in align; RER_C_cvg 11 vs 12).
- Line_10, 11 and 13 have no seed doc: their align is defaultAlign, so they golden-test the level solver.

**What a golden can compare:**
- (a) Input normalisation: seed doc to align.
- (b) Rail at 5 m within a tolerance.
- (c) Type and tube RLE.
- (d) `platforms.json` (430 records of platformCurve {name, c, R, out, inn, level, gapfill, turns}).
- (e) `approaches.json` (218 records of {c, kind, len, shift, side, station}).
- `issues.json` is 57 free-text strings, usable as a report only.
- `hub/seed/params/station_access_rule.json` (430 stations) and `station_platform_default.json` (408) are further outputs that could serve as goldens.

## What the new hub must support from this part

- One immutable record per route: a path with chainage (cumulative length, chainage from lon/lat), stations with stable platform ids (replacing `name#idx`), pieces and segs tied to Deck ids, rivers, crossings with the other route's chainage.
- Ground as layers on the 2 m grid per route and per year: DEM, Deck add/cap runs, Ben's drawn lines, other lines' drawn ground across their street. Built once per edit. Fed by `region.ground.sample(year, xy)`; the 1912 ground (lane B) is just another year.
- Every saved-doc field kept losslessly, including the platform-centre frame (`point_c`, `length_m`) so re-pathing (reframe) works: st, sg, so, del, pvi, ovr, stt, tf, shafts, gnd, gapfill, mode, ready.
- Canon as data, not code: Metro CANON 293-323 and ERA 1186-1192 are hard-coded today. This covers sections, fixed levels, modes, locks, bridges, decks by lon/lat, and river properties.
- The structure record, phases and chronology as versioned records the solve depends on, with the record version in the cache key.
- A pure solve on typed arrays: rail, grade, phase, type, tube, part, finished ground. Per-stretch method decisions with rule ids, approaches, bad, misfits, platform defaults, access per station, viaduct spans, river bands, clearances, roads, issues as data.
- Neighbour-aware solving: crossings and context blocks read the other route's solved arrays instead of re-deriving them (`kindAt` 2197). RER junctions and shared stretches become network constraints, not copy-on-save (`propagateLinks` 425).
- Per-system settings plus a per-line overlay (CVG platform 204.216), every literal from §6 either moved into the registry or deleted, and stale copies reconciled (data/profile/alignments, metro_rails, chronology, metro_structure, the py `minCover` 2.0).
- A golden harness on the 41 baseline routes: input normalisation, rail at 5 m, type and tube RLE with the JS rounding of 2 m to 5 m, platforms and approaches, with each difference classed same, rule fix with its id, or unexplained.
- A `route_profile` / `overlay_profile`-compatible adapter so railsim run times keep working until the contract replaces them: s, ground, track, grade as a fraction, railsim structure names.
- The proposers (defaultAlign, regradeDrive, solveCross, proposeFill) as engine functions that return edits, never touching UI or undo.
- Every Metro and RER route (16 Metro, 25 RER plus 5 legacy cores, about 720 km), with room for more eras, systems, settings sets and records without code changes.
