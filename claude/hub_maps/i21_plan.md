# I2.1 Close the loop: plan (hub_region, HEAD 0f562c4, 24 Nov 2026)

Scope note. Ben's latest message ("hold off on that until the rest of the hub is complete") is the hold recorded in
HEAD 0f562c4 on the 3D spec section 7 (the city around the lines). I2.1 is part of the rest of the hub, so this plan
goes ahead; nothing in it touches the 3D spec.

Read for this plan: claude/Hub_Region_Checklist.md I2.1 (and 2.1.6, 2.1.7, 2.1.14), claude/Hub_Region_Architecture.md
sections 5, 6, 9.19, 9.26, 9.31 and 11 item 1, claude/hub_maps/railsim.md; region/ext/profiles (inputs, jobs, router,
solve_input, rails), region/jobs (registry, plan, keys, hosts, scheduler, contract), region/live/service.py,
region/api/{app,live}.py, region/ground (compose, sample, layers, raster), region/ext/terrain, railsim (app, line,
dynamics, speed, horizontal, operations, dwell, rollingstock, metro, metro_profile, report), configs/metro/cin_line_6.yaml,
data/operations/cincinnati_metro.yaml, data/rollingstock/metro.yaml, tests/baseline (runtimes.json, README,
capture.py), tests/test_calibration.py, the line sheet (pane.ts, bands.ts, solved.ts, linepanel.ts, the engine worker)
and the old hub (hub/hub.py, hub/pipeline.py, hub/static, hub/sites, data/profile/profiles.html, hub/seed/roadmap).

## 0. Measured here (Linux container, scratch only; git status clean after every run)

| What | Result |
|---|---|
| Legacy `python -m railsim.metro configs/metro/cin_line_6.yaml --no-plots --out <scratch>` | 14.2 s wall, 3.9 s CPU; reproduces runtimes.json cin_line_6 exactly (37.52 / 37.34 min running, 52.00 / 51.81 min trip) |
| `build_route` (KMZ, network, fit, metro_profile) | 1.71 s |
| One direction `run_direction` (Simulator) | 0.151 s, both directions 0.30 s |
| `horizontal.fit_horizontal` on the hub's Line 6 section path (LocalProjection) | 0.71 s; drawn 29,539.6 m, fitted 29,554.9 m, 45 curves (legacy KMZ: drawn 29,524.0 m, fitted 29,525.2 m, 47 curves) |
| `speed.build_speed_profile` from a fit | 1 ms |
| region.ground sampling of the Line 6 path every 2 m in 1 km windows (`compose` + `sample_grid`) | 7.2 s at 2026 (first, zone caches cold), 1.1 s at 1930 (warm); no NaN; against the line file ground: mean -0.05 m, p95 of the absolute difference 2.07 m (2026), 2.52 m (1930) |
| Prototype: legacy geometry, baseline design, line-file station centres | running +0.50 % / +0.66 %, trip +0.35 % / +0.49 % |
| Prototype: hub section path fitted, baseline design (data/profile/alignments), line-file station centres, 33 stops | running -0.16 % / -0.28 %, trip -0.12 % / -0.19 %; worst station arrival 28.9 s (Fort Mitchell), worst relative 4.4 % (North Avondale, 14.2 s) |
| Prototype: hub path, Ben's design (hub/seed/alignments), his 2 removed stations restored (33 stops) | running +0.09 % / -0.12 %, trip +0.06 % / -0.07 %; worst arrival 27.3 s |
| Prototype: hub path, Ben's design as saved (31 stops: Greenlee and Lytle Park removed) | running -1.76 % / -1.83 %, trip -2.38 % / -2.42 %; worst arrival 99.1 s |

Station centres, line file (Deck stops) against the KMZ placemarks railsim projects (metres along the legacy fit):
Towne +60.5, Bond Hill +94.0, North Avondale +289.7, Forest +293.4, Oak -235.1, Times -60.2, Public Landing -18.2,
Eastside +73.9, Bullock -26.6, the other 24 within 4.3 m. Train CMCC_TYPE2005_10CAR is 146.0 m (10 cars).

Prototype scripts: /tmp/claude-0/-home-user-cincinnati-rail/388de07f-a9eb-500e-a913-639254f5ddc4/scratchpad/i21/t1.py to t5.py (not in the repo).

## 1. The contract

### 1.1 Modules

Lane ground (feature `terrain`, which already holds the ground layers):
- `region/ext/terrain/profile.py`: pure sampling of one section path: `[c, lon, lat]` to EPSG:26916 (pyproj), the
  section grid `c = i * step_m`, windows of 1,000 m (`compose(year, bbox + 10 m)` then `sample_grid`), so memory stays
  bounded on a 30 km line; `ground_files(year, timeline)` lists every file compose reads for that year (ledger, both
  bases, each present work's target, mode, part, delta, raster, zones, minus, years; the real timeline's riverworks
  delta).
- `region/ext/terrain/jobs.py`: `JOB_TYPES = [GROUND_PROFILE]`.
- `region/ext/profiles/inputs.py`, `solve_input.py`, `jobs.py`, `router.py`: the `ground.source` switch (section 2.7).

Lane railsim (new feature `region/ext/railsim/`, discovered like every feature: `region/jobs/registry.py` needs no
edit, `default_registry` picks up `JOB_TYPES`, `mount_features` mounts the router under `/api/v1/x/railsim`):
- `__init__.py`: the feature's doc.
- `contract.py`: pydantic models `RouteInput`, `RunResult`, `DraftIn`, `DraftOut`, contract names `route_input/0`,
  `run_result/0`; the router's `response_model`s, so openapi.json and the app's generated types carry them.
- `legacy.py`: the declared fallbacks (section 2): config stem of a route key (`Line_6` to `cin_line_6`, `Line_2b` to
  `cin_line_2b`, `CVG_Express` to `cvg_express`), the line config, the era file, the fleet and the rolling stock, each
  read through `ctx.file` in `plan` and handed to `run` as parsed dicts; the merged config (railsim's own
  `app.deep_merge`: program defaults < era overlay < line config) with the KMZ, `track`, `profile` and `analyzer`
  blocks dropped, so nothing downstream can reach a KMZ, a DEM or the network.
- `horizontal.py`: the fit of the section path (railsim's `horizontal.fit_horizontal` with `app.curve_design_from`,
  LocalProjection around the path as railsim does), a vectorised windowed projection of every section sample onto the
  fit (the `c` to `s` map), curvature on the grid. Interim rule until 2.1.14 (checklist lean (b): fit from the
  polyline first).
- `assemble.py`: pure: RouteInput from the gathered records and the upstream outputs.
- `adapter.py`: pure: RouteInput plus the merged config, era and train to railsim's own objects
  (`horizontal.HorizontalAlignment`, `profile.Profile` with railsim structure names from `metro_profile.STRUCTURE`,
  `speed.build_speed_profile`, `line.StationInfo`, `line.Route`), then `Route.track_data(2.0)`, `app.run_direction`,
  `app.apply_padding` and the fields of `app.summary_dict`. It replaces `build_route` only; it never calls `app.main`,
  `build_route`, `elevation`, `kml`, `report` or `MetroProfile.load`, and writes nothing.
- `attribution.py`: the phase split per leg (from the trace, no re-run) and the marginal re-runs.
- `jobs.py`: `JOB_TYPES = [ROUTE_HORIZONTAL, ROUTE_ASSEMBLE, RAILSIM_RUN, RAILSIM_ATTRIBUTION]`.
- `draft.py`: `DraftRunner`: one warm worker of its own (`region.jobs.hosts.ProcessHost(1)`, imported, not changed),
  an LRU of 32 answers keyed by content hash, newest wins per (client, section).
- `router.py`: a callable taking the `Hub` and returning the `APIRouter` (so the draft runner is closed with the hub).
- `sources.py`: `SOURCES` for doctor (`configs/metro`, `data/operations`, `data/rollingstock`).

Engine: no change. railsim: no change (read and imported only). region/ground: no change (imported only).

### 1.2 Job types

Hosts as section 6 of the spec: `process` for every railsim and ground job (pure Python and numpy, held by the
interpreter lock), `thread` for the assemble (numpy interpolation, a few ms). Every railsim job's `code_files`
include `repo://railsim` (the folder: all 6,997 lines, the "railsim source hash") and the lane's own modules.

| Type | Scope | Host | Priority (type) | Timeout | Axes | Key inputs (refs) |
|---|---|---|---|---|---|---|
| `ground.profile@1` | section | process | 6 | 120 s | year, timeline | `rec:<section>` (path, length_m, step_m); `file:` every file `ground_files(year, timeline)` names (`tier://ground_1912_real/canon_1912_ground_dm.vrt` and its two tifs, `tier://ground_2026/map3_profile_dem_dm.vrt` and its four tifs and water mask, `repo://ground/works_ledger.json`, `repo://ground/works/...` and `repo://ground/zones/...` per work present); code: this module, `profile.py`, `repo://region/ground` |
| `route.horizontal@1` | section | process | 3 | 60 s | none | `rec:<section>` (path, length_m, scale); `file:repo://configs/metro/<stem>.yaml` (geometry block); the `railsim.geometry.*` params once registered; code: railsim, `horizontal.py` |
| `route.assemble@1` | route | thread | 3 | 30 s | none | `rec:<route>`; `rec:section?parent=<route>`; per section `rec:profile?parent=`, `rec:stop?parent=`, `rec:platform?parent=`; `job:profiles.solve_section/<section>` (rail_m, grid), `job:profiles.solve_structure/<section>` (type_runs), `job:route.horizontal/<section>`; `param:settings.platform@<section>`; `file:repo://configs/metro/<stem>.yaml` (station classes, psd defaults, service terminals); code: railsim, `assemble.py`, `legacy.py` |
| `railsim.run@1` | route | process | 3 | 60 s | year | `job:route.assemble/<route>`; `file:repo://data/operations/<system>.yaml` (eras, fleet, default_year), `file:repo://data/rollingstock/metro.yaml`, `file:repo://configs/metro/<stem>.yaml` (train, load, padding, restrictions, throat, terminal approach, zones, reference, turnback); the `railsim.*` params once registered; code: railsim, `adapter.py`, `legacy.py`, `contract.py` |
| `railsim.attribution@1` | route | process | 9 | 180 s | year | the same reads as `railsim.run` (its `plan` calls run's), plus `job:railsim.run/<route>` (early cutoff: an unchanged run output reruns nothing); code: as run plus `attribution.py` |

Notes on the keys:
- Year: `ctx.axis("year")`. `year=None` (the present) resolves to the era file's `default_year` (2026) for railsim and to
  `region.ground.layers.PRESENT` (2026) for the ground; the resolved year is in `meta`, never in a key twice. Month is
  not read (eras and works are dated by year). Timeline: only `ground.profile` reads it; railsim has no timeline.
- A scope's record is read first (`ctx.read("route", id)`, `ctx.read("section", id)`), so `check_contract`'s scope
  probe passes.
- Scope is the route while every Metro route has one section; `route.assemble` raises `Invalid` for a route with
  more than one section (as `route_doc` does). When services become records (I2.4) the scope becomes the service and
  the versions go to 2.
- A param that is not registered yet raises `NotFound` and records no `param:` dependency; the value then comes from
  the file the plan already read through `ctx.file`, so the key still names what was read. When Ben registers the
  param, the param import invalidates every result with a `param:` dependency (all of these have
  `settings.platform` or another), so the jobs plan again and pick it up.
- Early cutoff: a paint, a tube form, a station access or a note that leaves the rail, the tunnel flags and the stops
  as they were gives `route.assemble` the same output hash, and `railsim.run` is not run. A re-save runs nothing.

### 1.3 RouteInput (`route_input/0`: `route.assemble` meta and arrays; values illustrative)

```json
{
  "contract": "route_input/0",
  "route_id": "01K...", "route_key": "Line_6", "name": "Line 6", "system": "metro", "config": "cin_line_6",
  "sections": [{"section_id": "01K...", "dir": 1, "c0_m": 0.0, "c1_m": 29539.6, "s0_m": 0.0, "s1_m": 29554.9}],
  "grid": {"c0": 0.0, "step_m": 2.0, "n": 14778},
  "length_m": 29554.9,
  "scale": 0.99984,
  "curves": [{"s_ts": 812.0, "s_sc": 842.0, "s_cs": 990.4, "s_st": 1020.4, "c_ts": 811.6, "c_st": 1019.8,
              "radius_m": 420.0, "spiral_m": 30.0, "cant_m": 0.11, "deflection_rad": 0.41, "direction": "L"}],
  "structures": [{"s0_m": 0.0, "s1_m": 640.0, "c0_m": 0.0, "c1_m": 640.0, "type": "cutcover",
                  "railsim": "cut-and-cover", "tunnel": true}],
  "stops": [{"platform_id": "01K...", "name": "Towne", "c_m": 60.5, "s_m": 60.4, "platform_m": 121.92,
             "class": "terminal", "class_source": "terminal", "psd": false, "terminal": true, "removed": false,
             "reverse": false}],
  "removed": [{"platform_id": "01K...", "name": "Greenlee", "c_m": 3116.2, "why": "removed on the profile"}],
  "restrictions": [{"s0_m": 0.0, "s1_m": 0.0, "v_ms": 0.0, "reason": "posted", "rule": null}],
  "operating_zones": [], "neutral_sections": [], "supply_zones": [],
  "sources": {"rail": "profiles.solve_section", "types": "profiles.solve_structure",
              "curves": "fitted to the section path", "stations": "records",
              "classes": "configs/metro/cin_line_6.yaml"},
  "warnings": []
}
```

Arrays on the run grid (`s = i * 2 m` along the fit, `meta.grid`): `s_m` f8, `c_m` f8 (section chainage at each run
sample), `rail_z_m` f8 (the solved rail at `c_m`), `curvature_per_m` f8 (absolute, spirals included), `tunnel` u1,
`type` u1 (index into elevated, atgrade, trough, cutcover, shield, deep, sunk). `restrictions` holds only the fixed
ones (config restrictions, terminal approaches, throats, through and passing limits; none on Line 6); curve limits are
made in `railsim.run` because they depend on the train (cant deficiency, tilt, top speed).

### 1.4 RunResult (`run_result/0`: `railsim.run` meta and arrays; the draft answers the same shape; values illustrative, the Bond Hill row is the baseline's)

```json
{
  "contract": "run_result/0",
  "route_id": "01K...", "route_key": "Line_6", "config": "cin_line_6",
  "year": 2026, "year_source": "default_year",
  "era": {"name": "CBTC driverless with on-board attendant (GoA3 / DTO)", "goa": 3, "years": [2020, 2100],
          "signalling": "cbtc"},
  "train": {"key": "CMCC_TYPE2005_10CAR", "name": "CMCC Type 2005 (10 x 48 ft, AC traction)", "cars": 10,
            "length_m": 146.0, "load_factor": 0.5, "mass_t": 0.0, "rail_condition": "dry", "max_kmh": 99.8},
  "padding": {"percent": 3.0, "final_leg_s": 0.0},
  "directions": [
    {"dir": 1, "label": "Towne to Beechgrove", "from": "Towne", "to": "Beechgrove",
     "distance_m": 29447.0, "stops": 31,
     "running_s": 2251.2, "dwell_s": 868.8, "trip_s": 3120.0, "scheduled_s": 3187.2,
     "average_kmh": 34.0, "max_kmh": 85.9, "energy_traction_kwh": 1105.4, "energy_regen_kwh": 430.1,
     "stations": [
       {"platform_id": "01K...", "name": "Towne", "c_m": 60.5, "s_m": 133.4, "km": 0.0,
        "arrive_s": 0.0, "depart_s": 0.0, "dwell_s": 0.0, "scheduled_arrive_s": 0.0, "leg": null},
       {"platform_id": "01K...", "name": "Bond Hill", "c_m": 1084.2, "s_m": 1123.4, "km": 0.99,
        "arrive_s": 67.8, "depart_s": 112.8, "dwell_s": 45.0, "scheduled_arrive_s": 69.8,
        "leg": {"run_s": 67.8, "vmax_kmh": 85.3, "accel_s": 31.0, "cruise_s": 12.4, "coast_s": 0.0, "brake_s": 24.4}}]},
    {"dir": -1, "label": "Beechgrove to Towne", "...": "the same members"}
  ],
  "round_trip_s": 6360.0, "turnback_s": [0.0, 0.0],
  "speed_zones": [{"c0_m": 0.0, "c1_m": 2865.0, "kmh": 88.5, "reason": "line speed", "rule": null}],
  "curves": [{"c0_m": 811.6, "c1_m": 1019.8, "radius_m": 420.0, "spiral_m": 30.0, "limit_kmh": 64.4}],
  "grid": {"c0": 0.0, "step_m": 10.0, "n": 2955},
  "warnings": ["Line 6: 1 grade over 50 per mille"],
  "sources": {"era": "data/operations/cincinnati_metro.yaml", "train": "data/rollingstock/metro.yaml",
              "classes": "configs/metro/cin_line_6.yaml", "curves": "fitted to the section path"}
}
```

Arrays: on the section grid of `meta.grid` (10 m, so the result event's `changed` ranges are in Ben's chainage):
`limit_ms`, `v_fwd_ms`, `v_rev_ms` (the front's speed as it passes each sample, NaN where the train never is),
`t_fwd_s`, `t_rev_s` (when the front passes it). Traces as 2-D arrays (left out of `changed`): `trace_fwd`,
`trace_rev`, shape [n, 4] f4 (t s, c m, v m/s, a m/s2), every simulator step (about 11,300 rows each on Line 6).
Times are unrounded in the result (rounding is the sheet's); outputs are deterministic, so equal inputs give an equal
`output_hash`.

`railsim.attribution` meta:

```json
{"directions": [{"dir": 1,
  "zones": [{"c0_m": 811.6, "c1_m": 1019.8, "reason": "curve R=420 m", "rule": null, "limit_kmh": 64.4, "lost_s": 6.2}],
  "grades_s": 14.0, "tunnel_drag_s": 9.5, "dwell_s": 868.8}]}
```

Each zone's `lost_s` is the run with that zone lifted to the line speed, less the run as it is; `grades_s` is the
run on a level rail less the run; `tunnel_drag_s` the run with every tunnel flag off less the run. About 40 zones on
Line 6, 0.15 s per direction each: about 13 s of one process slot, checked against `rt.cancelled()` between re-runs.

### 1.5 API routes (`/api/v1`)

Saved runs use the generic routes, nothing new:
- `POST /compute {type: "railsim.run", scope: <route id>, view, priority, watch_s}` and
  `POST /compute {type: "railsim.attribution", ...}`: `{key, state, job}`;
- `GET /results?type=railsim.run&scope=<route>&view=<token>`, `GET /results/{key}` (the RunResult in `meta`),
  `GET /results/{key}/a/v_fwd_ms` (and the others; `X-Dtype`, `X-Shape`);
- `POST /live/focus {type: "railsim.run", scope, view, priority}`.
- Ground: `POST /compute {type: "ground.profile", scope: <section>}` and `GET /results/{key}/a/ground_m`; no route of
  its own, so lane ground does not touch openapi.json.

New, in `region/ext/railsim/router.py`:

`POST /x/railsim/sections/{section_id}/draft?layer&year&month&tl` (write headers as every POST: `X-CR-Client`, JSON):

```json
{
  "section_input": {"contract": "section_input/0", "section_id": "01K...", "length_m": 29539.6, "step_m": 2.0,
                    "stations": [{"platform_id": "01K...", "order": 0, "c_m": 60.5, "level_m": 159.9,
                                  "grade_permille": 0}],
                    "pvi": [{"c_m": 357.0, "z_m": 168.5}], "params": {}, "...": "SectionInput v0 of the draft"},
  "type_runs": [["cutcover", 0.0, 640.0], ["shield", 640.0, 3697.9]],
  "edit_rev": 41
}
```

- `section_input` is what the sheet already builds for its worker (`model.ts localInput` of the draft: the live
  stations with their slides, the draft's PVIs and levels). The server solves it with `vertical.rail@1` on its engine
  (Line 6 under 20 ms) so the rail is the hub's rule, not the browser's word.
- `type_runs` is the draft's `section.solve@1` answer when the sheet has one for this edit; absent or null, the saved
  `profiles.solve_structure` types are used and the answer says `"types": "saved"`.
- The server takes the newest ok `route.assemble` and `route.horizontal` results of the route in the view (a cache
  read, never a plan, as `rails.warm_view` does), lays the draft's rail, tunnel flags and stops on them (a platform
  missing from `stations` is removed; a removed terminal stays a stop, as railsim did), and runs the same
  `adapter.run_route` as `railsim.run` in the draft worker.

Answers:
- `200 DraftOut`: the RunResult above plus `{"draft": true, "key": "<sha256>", "cached": false, "ms": 380,
  "types": "draft|saved", "base": {"assemble": "<key>", "run": "<railsim.run key or null>"}, "edit_rev": 41}`.
  `key = sha256(canonical_json({code hash of railsim.run, its file hashes, year, the draft RouteInput's content
  hash}))`: the same draft twice is one run (LRU hit, `cached: true`); a draft equal to the saved records gives the
  saved run's numbers exactly (a test).
- `409 problem code "superseded"`: a newer draft from the same client for the same section arrived while this one
  waited (at most one running and one waiting per client and section).
- `409 problem code "pending"`: the route has no `route.assemble` or `route.horizontal` result yet; the sheet asks
  again on the next `result` event of either.
- `422`: a SectionInput for another section, or of another length or step than the section's.

`GET /x/railsim/routes/{route_id}/input?layer&year&month&tl`: the warm RouteInput (meta, and the arrays as lists),
or `409 pending`. Never plans. For tests, Ben and the sheet's readout of curves.

### 1.6 SSE events the sheet listens to

No new event type:
- `result` with `type` `railsim.run` (and `railsim.attribution` when the table's "where the time goes" is open),
  `scope` the route id, `view` the sheet's token, `changed` in section chainage (from the 10 m grid arrays): read the
  meta and the three speed arrays again;
- `result` with `type` `route.assemble` or `route.horizontal`: a draft that answered `pending` is sent again;
- `job` with those types: `queued` or `running` (with `msg` "forward" or "reverse") puts the band's "updating" mark
  on; `error` shows the job's message in the band header;
- `pending` (live): the sheet's re-solving mark already lists watched goals, railsim ones included;
- `record` on the section's profile, stops, platforms or params: the sheet's existing re-reads; the run follows
  through the scheduler.
Draft answers come back in the HTTP answer only.

### 1.7 Scheduling

- The rail first. The sheet already asks `profiles.solve_section` at 0 (focused) or 1 (open). It asks
  `railsim.run` at 2 (focused) or 3 (open), with the same `watch_s` (600 s) and `/live/focus` on focus changes, and 9
  when the pane closes. Upstream jobs inherit the asking priority (scheduler line 704), so the run's
  `solve_structure` never goes ahead of the rail.
- `railsim.attribution` is asked at 4 only while the table's "where the time goes" is open; there is no background
  goal for it.
- No background goals for railsim in I2.1: a run exists because a pane shows it (idle CPU stays at the watcher's).
  A background goal per Metro route at 7 is a later option, listed in section 5.
- Never during a drag. Saved runs follow saves, and the sheet never saves during a drag. Drafts: the sheet posts
  only when no editing drag is on, the full solve of the current edit revision has landed (it gives `type_runs`),
  and 300 ms have passed since the last edit; a newer edit aborts the request in flight (AbortController) and the
  server drops a waiting one (`superseded`). A draft that equals the saved records is not posted: the saved run is
  shown.
- Supersession of saved runs is the scheduler's (one pending job per goal, newest key wins; a superseded process
  job is killed after 1 s).
- Drafts never take the scheduler's two process slots: the draft worker is its own (spawned on the first draft,
  warm after, `max_tasks_per_child` 200, idle at 0 % CPU, retired with the hub).
- Budgets (lane railsim, `tests/railsim/test_budget.py`, slow, warn-only on CI like tests/perf): `railsim.run` Line 6
  both directions in a warm worker under 1.0 s; `route.assemble` under 200 ms; `route.horizontal` under 1.5 s;
  `ground.profile` Line 6 under 15 s cold, 3 s warm; a saved PVI edit to the `railsim.run` result event under 10 s
  (target 3 s); a draft under 1.5 s warm. Lane sheet: PVI drag released to new trip time on the band under 10 s
  (target 2 s), and no draft request between pointer down and pointer up.

## 2. Where each railsim input comes from

| Input | I2.1 source in the hub | Declared fallback (file, read through `ctx.file`) | Later |
|---|---|---|---|
| Route and its sections, direction | `route` and `section` records (one section per Metro route); forward is rising chainage | service terminals of `configs/metro/<stem>.yaml` only check the order and name the labels | services as records (I2.4) |
| Stations and platforms | `stop` and `platform` records in stop order; centre = stop `c` + the profile's slide `so`; removed = the profile's `del`; a removed terminal stays a stop (railsim's `_apply_profile_stations`) | none | |
| Platform length (stop marker) | param `settings.platform` (121.92 m), scoped to the section | | per platform with era standards |
| Dwell class per station | none in the records yet | `stations.info.<name>.class` and `stations.defaults` of the line config (Line 6: 12 transfer stations, the rest standard; the two ends terminal) | a platform field or a service stop pattern (I2.4); a check lists where the station complexes disagree with the config |
| PSD per station | none | `stations.defaults.psd` and `info.<name>.psd`; the era's `psd_lines` | records (I2.4) |
| Era and default train for the year | the view's year (axis); present = `default_year` | `data/operations/cincinnati_metro.yaml` (`load_era`: eras, overlay, fleet); `configs/metro/<stem>.yaml` `year`, `train`, `load_factor` | `era` records exist as a kind with no importer; the chronology and operations import (I2.4) |
| Rolling stock | | `data/rollingstock/metro.yaml` (parsed in `plan`, `rollingstock.train_from_dict` in `run`) | records (I2.4) |
| Driver, signalling, dwell model, padding | | railsim/metro.py `DEFAULTS` (code) < era overlay < line config | params and era records |
| Restrictions, throats, terminal approach, supply, zones, neutral sections | none on any `cin_line_*` config; names map to hub stations, `at` latitude and longitude project onto the section path; a KMZ segment-name `match` is refused with an issue | the line config | restriction records with rule ids |
| Curves and curvature | `route.horizontal`: railsim's `fit_horizontal` on the section's drawn path (records), the fit's curves (R, spiral, cant, deflection) and curvature on the grid | geometry block of the line config and metro `DEFAULTS` | horizontal alignment as geometry (2.1.14) |
| Curve speed limits | `speed.build_speed_profile` on the fit, in `railsim.run` (train dependent) | speed block of config and `DEFAULTS` | |
| Rail level and grade | `profiles.solve_section` rail_m (Ben's saved profile, or the default design for Lines 10, 11, 13, as the sheet draws it) | | |
| Tunnel flags | `profiles.solve_structure` `type_runs`: cutcover, shield, deep and sunk are tunnels (railsim's `TUNNEL_STRUCTURES` through `metro_profile.STRUCTURE`) | | |
| Ground | not read by the run (the rail is designed); it reaches the run only through the structure solve's types | the line-file `ground_profile` records while `ground.source` is `line_file` (2.7) | |
| Reference times, turnback, headway | | line config `reference`, `turnback_min`, `service.headway_min` | services (I2.4) |

### 2.7 `ground.source`

- `ground.profile@1` always samples region.ground for the section at the view's year and timeline. Whether the
  profiles' consumers read it is the param `ground.source`: `line_file` (the `ground_profile` record, the ground Ben's
  designs and the old page were made on) or `region` (the `ground.profile` result). The other source fills any sample
  the chosen one lacks, and the input says so.
- Consumers: `station_input` (its `section.ground`), `section_solve_input` (`dem`), the router's
  `GET /sections/{id}/input`, `/stations` and `/solve`. In jobs, `ground.source = region` makes the plan
  `ctx.need("ground.profile", sid)` and leave `ground_from` in the input; `run` lays the upstream arrays in (as
  `design_from` does today). The router reads the warm result (a cache read, as `rails.warm_view`), and while there is
  none it answers with the line-file ground and an `X-CR-Ground: line_file (region pending)` header.
- Proposed value until Ben rules: `line_file`. Reason: the golden diffs (41 of 41 routes), the station facts parity
  and every sheet Ben has checked were made on it; at `line_file` every output stays byte for byte (keys change once
  for the new param dependency; early cutoff stops the chain). `region` is one param edit (main, or a scenario first).
- `profiles.solve_section` (`vertical.rail@1`) reads no ground and is untouched.

## 3. Known differences from the baseline, and how each is classed

Classes: `same` (within the tolerance), `design` (Ben's records differ from what the baseline ran on; names the
record and fields), `geometry` (the hub's geometry differs from the KMZ's; names the stretch or station and the
metres), `rule` (a hub rule differs, with its rule id), `unexplained` (must be zero).

| # | Difference | Size on Line 6 | Class |
|---|---|---|---|
| D1 | The baseline's design: runtimes.json was captured with `configs/metro/cin_line_6.yaml`, whose `analyzer.alignment` is `data/profile/alignments/Line_6.json` (26 Oct: no stations removed, 9 PVIs, all past 21.7 km, no platform grades). The hub reads Ben's saved profile (old hub seed, 1 Nov: Greenlee and Lytle Park removed, many PVIs, platform grades, 4 paints). The survey's "saved-profile mismatch" finding | Ben's design with the 2 stations restored: +0.09 % / -0.12 % running | design (profile record: pvi, st, sg, ovr) |
| D2 | Stations: the baseline runs 33 stations; the hub sheet has 31 live and 2 removed (profile `del`) | -1.8 % running, -2.4 % trip, up to 99 s per station | design (profile record: del) |
| D3 | Horizontal: railsim fits the KMZ folder `Cincinnati Metro/Line 6` (29,524.0 m drawn, 47 curves); the hub fits the section path from the line file (29,539.6 m, 45 curves) | -0.16 % / -0.28 % running with the baseline design | geometry (rule `run.horizontal.fit_from_drawn_path`, interim) |
| D4 | Station centres: KMZ placemarks projected onto the fit against the Deck stops (`stop.c` + slide) | up to 293 m (North Avondale, Forest, Oak); the main cause of per-station differences (worst 28.9 s) | geometry (station, metres) |
| D5 | Stop marker: railsim used its default platform 150 m; the hub uses `settings.platform` 121.92 m. With a 146 m train the marker is the train's half length either way (the 5 m short only applies to a platform over the train plus 10 m) | under 2 m per stop | same |
| D6 | Rail: metro_profile's port of the page on a 5 m grid projected onto the fit, against the engine's `vertical.rail@1` on the section's 2 m grid (equal to the page within 0.5 mm on 41 routes) | small; shows only through D1 | same, else design |
| D7 | Tunnel flags: `metro_profile.type_at` against `section.solve@1` `type_runs` | to measure in G2; tunnel drag factor 2.0 on this train | same, else rule (with the structure rule id) |
| D8 | Chainage basis: railsim's local tangent plane (ground metres) against the section's grid:26916 chainage (scale 0.99984, about 5 m on 29.5 km) | under 0.02 % | same |
| D9 | Era and train: both 2026, GoA3 CBTC, CMCC_TYPE2005_10CAR, load 0.5, dry | none | same |
| D10 | Warnings: the baseline's "1 grade over 50 per mille" came from metro_profile's summary; the hub's from the solve's flags | text only | same |
| D11 | Ground: the run does not read it (D7 only, through the types) | none at `line_file` | same |

The gate, as three tests in `tests/railsim/test_parity.py` (lane railsim):
- G1 adapter identity: the legacy Route built by `railsim.line.build_route` in the test (the KMZ is read there as the
  reference, never by the hub) is turned into a RouteInput and run through `adapter.run_route`: every summary number
  and every station's arrival equal to runtimes.json within 0.05 s (rounding). Proves the RouteInput to TrackData path,
  stops, dwell, padding and the summary fields.
- G2 hub geometry on the baseline's design: the hub's Line 6 records in a test scenario layer whose profile is the
  baseline's alignment (`data/profile/alignments/Line_6.json` as the profile body), the full job chain
  (solve_section, solve_structure, horizontal, assemble, run): running and trip times within 1 % in both directions
  (measured in the prototype: -0.16 % / -0.28 % and -0.12 % / -0.19 %), and every station's arrival within 1 % of
  that direction's baseline trip time (31.2 s and 31.1 s; prototype worst 28.9 s). Each station also over 1 % of its
  own arrival is listed with its D4 metres (prototype: 6 and 8 stations, all near the start of a direction).
- G3 Ben's records in main: the chain on main is reported, and each difference must class: restoring his two removed
  stations in a scratch scenario must bring the run inside G2's tolerances (prototype: +0.09 % / -0.12 %); then D1 and
  D2 explain the rest and `unexplained` is zero.

For the lead to confirm: on main as Ben has it, Line 6 cannot be within 1 % of runtimes.json, because the baseline
predates his removal of Greenlee and Lytle Park (-1.8 % running, -2.4 % trip). The proposal is that the gate's 1 % is
met by G2 (and G3 with the two stations restored), and that a per-station arrival is held to 1 % of the trip time,
not 1 % of its own arrival (which fails at the first stations of each direction on D4 alone, and even on the legacy
geometry: 3.7 s is 2.4 % of Brightleaf's 131.8 s). The capture could also be refreshed on Ben's design
(`tests/baseline/capture.py --runtimes metro` with configs pointing at hub/seed), but tests/baseline is read only here.

## 4. Run-time display: old hub parity and the new band and table

### 4.1 What the old hub shows (searched hub/ for runtime, run time, railsim, summary.json, speed, trip, running)

The old hub shows no run times. hub/hub.py serves the Deck, the Profiles page (data/profile/profiles.html),
Chronology and Access; hub/pipeline.py never runs railsim; hub/static has no run-time panel; no page reads
summary.json. railsim appears only in five roadmap records, all `todo`. What Ben has seen is railsim's own output.
The parity baseline is therefore railsim's outputs plus what the old hub and its roadmap promise:

1. Profiles page, Remove station (profiles.html 3055): "Leave this station out of the profile and the run times;
   restore it from the Stations list". A removed station leaves the run; railsim keeps the two terminals.
2. A slid platform moves the stop by the same distance (railsim `_apply_profile_stations`).
3. Run header per direction: "<first> -> <last>", train name, load factor, mass, rail condition, era name and year.
4. Station table per direction: Station, km, run (the leg, m:ss), dwell (s), arr (m:ss), dep (m:ss), sched (padded,
   m:ss), ref and diff (the config's reference minutes, when given), vmax of the leg (mph).
5. Direction summary: running min + dwell min = trip min; scheduled (padded) min; average km/h; traction energy kWh.
6. Round trip: scheduled both ways plus turnback at each end; trains needed at a headway when one is given.
7. Warnings: grades over the limit, train not cleared for a curve (min_curve_radius), a station far from the track,
   ground source failures.
8. summary.json: per direction distance_km, stops, running_time_min, dwell_total_min, trip_time_min,
   scheduled_time_min, average_speed_kmh, max_speed_kmh, energy_traction_kwh, energy_regen_kwh, and per station
   name, km, arrive_s, depart_s, dwell_s, scheduled_arrive_s; curves (47: radius, spiral, start and end km, segment,
   sketch, position); speed zones (40: from and to km, mph, km/h).
9. stations_<dir>.csv (station, km, arrive_s, depart_s, dwell_s, scheduled_arrive_s) and trace_<dir>.csv (t_s, s_m,
   v_kmh, a_ms2).
10. profile_<dir>.png: speed against distance with the posted limit (stepped) and the train's speed, a line and a name
    at each station, the trip minutes in the title; elevation (ground and track); grade (%).
11. alignment.kmz: the fitted alignment coloured by speed limit (red slow to green fast).
12. Eco allowance line (padding distribution eco) and Monte Carlo p50, p85, p95 (`--monte-carlo N`).
13. Roadmap r23 "Run times on the Profiles": under each profile the speed curve and the run time between stations,
    with the speed restrictions (curves, grades, turnouts) marked, so a regrade or a station move shows its effect
    at once.
14. Roadmap r19 "Railsim tab": per line and direction, rolling stock and driver per era, dwell by station type,
    results kept as hub records so the Profiles and the map can show them.

Carried in I2.1: 1 to 10, 13, 14 (per era through the view's year). Kept as data only: the eco block (no Metro
config uses it). Not carried yet: 11 (the map's job, with the KMZ export later), Monte Carlo (12).

### 4.2 The run-time band (`runtime`, a strip band under the structure strip, about 110 px)

- x: the sheet's chainage axis. y: speed from 0 to 1.1 times the highest limit, km/h, or mph when the sheet is in
  feet; ticks every 20 km/h (10 mph).
- The posted limit as a stepped grey line; a curve's limit carries its reason in the readout.
- Forward speed solid in the rail colour, back speed dashed in a second colour; a toggle Both, Forward, Back in the
  band header (kept for the session).
- A thin line at each live station, aligned with the platform bars; removed stations as faint dashed lines with no
  leg times.
- Leg times (run, m:ss) in the middle of each leg, forward above the curves, back below, thinned at whole-line view as
  the other labels are.
- Header at the left: "Towne to Beechgrove 52:00 (running 37:31, dwell 14:29); back 51:49", followed by the era and
  train in short ("2026, GoA3, Type 2005").
- A draft: the draft's curves drawn, the saved run's under them faint, and a change chip after each trip time
  ("+0:12"); "draft" in the header. While a run or draft is pending: "updating" in the header and the curves dimmed;
  never blank.
- Hover readout rows: speed forward and back at the cursor, the limit and its reason ("curve R=420 m", "line speed"),
  the times the front passes.
- Marks for the tests: `{kind: "run", dir, trip_s, running_s, draft}` and one `{kind: "leg", from, to, run_s}` per
  leg drawn.

### 4.3 The run-time table (a card in the line panel, "Run times")

- Two column groups, Forward and Back (or one at a time below 1000 px, with the band's toggle).
- One row per stop: Station, km, Run (m:ss), Dwell (s), Arrive, Depart, Scheduled, Vmax (km/h or mph). Removed
  stations in grey, "removed", no times.
- Totals: running, dwell, trip, scheduled, average speed, top speed, traction and regenerated energy (kWh); round trip
  with the turnback at each end.
- With a draft: Arrive and the totals show the draft, and a Change column against the saved run.
- "Where the time goes" (folded by default): per leg the seconds accelerating, cruising, coasting and braking (from
  the run, free); per restriction the seconds it costs, largest first, then grades and tunnel drag (from
  `railsim.attribution`, asked only while this is open).
- A sources line in plain words: "Era 2026: CBTC driverless (GoA3). Train: CMCC Type 2005. Station classes from the
  Line 6 config. Curves fitted to the drawn path."
- Warnings as a list under it.
- Interactions: a row click moves the sheet to that station; hovering a row lights its leg on the band and back;
  "Export CSV" writes both directions as stations_<dir>.csv did (exports.ts).

## 5. Params and rule ids not in rules/registry.yaml (for Ben)

Params (each read with its fallback until registered; the fallback's file is in the key):

| Path | Proposed value | Unit | Today in |
|---|---|---|---|
| `ground.source` | line_file (line_file or region) | enum | new |
| `ground.sample_window_m` | 1000 | m | new (ground.profile's compose windows) |
| `railsim.load_factor` | 0.5 | ratio | railsim/metro.py DEFAULTS |
| `railsim.rail_condition` | dry | enum | railsim/app.py |
| `railsim.grid_m` | 2.0 | m | railsim/app.py run_direction |
| `railsim.stop_position` | far_end | enum | railsim/app.py |
| `railsim.stop_short_m` | 5.0 | m | railsim/app.py _stops_for |
| `railsim.reversal_min_s` | 240 | s | railsim/app.py |
| `railsim.padding.percent` | 3.0 | percent | railsim/metro.py DEFAULTS |
| `railsim.padding.final_leg_s` | 0 | s | railsim/metro.py DEFAULTS |
| `railsim.geometry.line_speed` | 55 | mph | every configs/metro/cin_line_*.yaml |
| `railsim.geometry.max_cant` | 6.0 | in | DEFAULTS |
| `railsim.geometry.design_cant_deficiency` | 3.0 | in | DEFAULTS |
| `railsim.geometry.min_spiral_m`, `min_reverse_tangent_m`, `min_radius_m`, `group_dev_tol_m`, `corner_offset_tol_m`, `simplify_tol_m` | 20, 30, 25, 10, 30, 3 | m | DEFAULTS and app.curve_design_from |
| `railsim.speed.cant_deficiency` | 3.0 | in | DEFAULTS |
| `railsim.speed.increment` | 5 | mph | DEFAULTS |
| `railsim.speed.min_zone_m` | 150 | m | DEFAULTS |
| `railsim.speed.max_deficiency_rate` | 55 | mm/s | DEFAULTS |
| `railsim.driver.ato_margin` | 2 | mph | railsim/metro.py make_driver |
| `railsim.driver.dt_s` | 0.2 | s | railsim/metro.py make_driver |
| `railsim.background` | false | bool | new: a background railsim.run goal per Metro route at priority 7 |

Not params: eras, fleet, dwell model per era, door times and station dwell classes belong to the era, rolling stock
and service records of I2.4; until then the files are the declared fallbacks.

Rule ids (new domain proposed: `run`; Ben names it):
- `run.station.removed_leaves_service`: a removed station leaves the run; the two terminals stay.
- `run.station.slide_moves_stop`: a slid platform moves its stop by the slide.
- `run.stop.far_end_marker`: the head stops 5 m short of the platform's far end when the platform is over the train
  plus 10 m, else at the train's half length past the centre.
- `run.curve.speed_from_radius_cant_spiral`: the curve limit from R, cant, spiral and deflection, quantised to the
  increment, zones shorter than min_zone merged.
- `run.tunnel.drag_by_structure`: cut and cover, shield, deep tube and sunk box run with the train's tunnel drag.
- `run.padding.uniform_percent`: scheduled time is running time plus the padding percent on every leg plus the final
  leg seconds.
- `run.dwell.door_cycle_by_class`: dwell is the door cycle by station class and era (with PSD overhead).
- `run.era.by_year`: the era covering the year sets the overlay; the default train is the latest fleet entry at or
  before it.
- `run.horizontal.fit_from_drawn_path`: interim, curves fitted to the section's drawn path until 2.1.14.
- `ground.source.declared`: which ground the profiles read; the other fills its gaps, and the input says so.
- `ground.profile.by_year`: the section's ground is region.ground at the view's year and timeline; the present is 2026.

## 6. Build lanes and file ownership

No file is owned by two lanes. Read-only for every lane: railsim/, region/ground/, hub/, data/, design/,
rules/registry.yaml, tests/test_hub.py, tests/baseline/, engine/, configs/ (read through `ctx.file` only).
The lead owns region/README.md, claude/Hub_Region_Checklist.md, claude/Hub_Region_Architecture.md,
tests/known_failures.txt, and commits.

### Lane "ground" (ground.profile and the ground.source switch)

Owns:
- `region/ext/terrain/profile.py` (new), `region/ext/terrain/jobs.py` (new), `region/ext/terrain/__init__.py` (doc).
- `region/ext/profiles/inputs.py`, `region/ext/profiles/solve_input.py`, `region/ext/profiles/jobs.py`,
  `region/ext/profiles/router.py` (the `ground.source` switch, `ground_from`, the warm read; nothing else).
- `tests/terrain/__init__.py`, `tests/terrain/test_ground_profile.py`, `tests/profiles/test_ground_source.py` (new).
Tests first: the job type contract (`check_contract`: stable key, determinism, no writes); the key holds the year and
timeline axes and every file `ground_files` names, and a changed works file plans it again; a 1930 view and a 2026 view
give two keys and the 1930 one leaves the later works out (`meta.skipped`); Line 6 sampled against the line file
(p95 within 3 m; the line file is map 3 ground); no NaN on any Metro section; windows equal a single compose on a
short section; `ground.source = line_file` leaves every profiles output byte for byte and the golden diff and station
facts tests green; `ground.source = region` in a scenario feeds `ground.profile` into station facts and the whole
solve and the router (with the header while pending); the sampler writes nothing (repo tree and var snapshot).
Suites: `pytest tests/terrain tests/profiles tests/live tests/jobs`, `test_ground.py`.
Does not touch openapi.json (no new route).

### Lane "railsim" (adapter, jobs, API, parity)

Owns:
- `region/ext/railsim/` (all of it: `__init__.py`, `contract.py`, `legacy.py`, `horizontal.py`, `assemble.py`,
  `adapter.py`, `attribution.py`, `jobs.py`, `draft.py`, `router.py`, `sources.py`).
- `region/api/openapi.json` and `app/src/api/gen/*` (regenerated once its router is in: `python -m region.api.openapi
  --write`, then `npm run gen:api -w app`; both drift tests, `tests/api/test_serve.py::test_openapi_drift` and
  `app/test/unit/api_drift.test.ts`, must pass; the only lane that regenerates). openapi.json is built from
  `create_app(None, None, None)`, so the router factory must build its routes when the Hub has no store, jobs or
  engine (the draft route answers 409 `pending` then).
- Shared Python files if one has to change: `region/jobs/registry.py`, `region/jobs/scheduler.py`,
  `region/jobs/hosts.py`, `region/live/*`, `region/api/*` (none is expected to: features are discovered, upstreams
  inherit priority, the process host is imported as it is).
- `tests/railsim/` (new): `conftest.py`, `test_adapter.py` (G1), `test_jobs.py`, `test_parity.py` (G2, G3),
  `test_draft.py`, `test_side_effects.py`, `test_budget.py`.
Tests first: G1 to G3 (section 3); each job type passes `check_contract` on the real Line 6 records; a PVI edit
changes `route.assemble` and `railsim.run` keys and a paint that leaves rail and tunnels unchanged stops at
`route.assemble` (early cutoff); a re-save runs nothing; the 1930 view runs the 1916 to 1985 era and the Type 1925
train; a changed `repo://railsim` source or data/operations file makes new keys; side effects: during a run sockets
refuse to connect, and the repo tree, `data/elevation_cache`, `output/` and `var` (less the cache) are unchanged; the
draft of the saved state equals the saved run exactly; two equal drafts are one run (`cached`); a newer draft answers
the older `superseded`; `pending` before the assemble exists; the drift test (tests/api) green after regeneration;
the live budgets (`tests/live`) green with a sheet's `railsim.run` goal watched.
Suites: `pytest tests/railsim tests/jobs tests/live tests/api tests/profiles tests/test_calibration.py`.

### Lane "sheet" (band, table, drafts, e2e)

Owns:
- `app/src/plugins/line-sheet/runs.ts` (new: saved run through `compute` and result events, drafts with the gating
  of 1.7, attribution on demand, the RunResult types as a local stub until the generated ones land),
  `app/src/plugins/line-sheet/runtime_band.ts` (new), `app/src/plugins/line-sheet/runtable.ts` (new).
- `app/src/plugins/line-sheet/pane.ts`, `bands.ts` (the band in `BANDS`), `linepanel.ts` (the card),
  `exports.ts` (CSV), `app/src/core/plugin.ts` (`BandData.run`), `app/src/core/units.ts` (speed km/h or mph,
  durations m:ss), `app/src/api/client.ts` (`railsimDraft`, `railsimInput`).
- `app/test/unit/sheet_runtime.test.ts` (new), `app/test/unit/fixtures/run_result_line6.json` (new),
  `app/test/unit/fake_hub.ts` (the draft route and the railsim results), `app/e2e/runtime.spec.ts` (new).
Tests first: the band draws both directions, leg labels and the header from the fixture (marks); a draft is never
posted during a drag, only after the full solve of the same edit and 300 ms; a newer edit aborts the older request;
the draft equal to the saved records posts nothing; feet shows mph; the table's totals equal the fixture; the e2e:
open Line 6, release a PVI drag, the band's trip time changes within 10 s, Save, the saved run arrives over SSE and
equals the draft, Ctrl+Z goes back to the saved numbers with no new run, and after 5 s idle the page makes no
requests; the existing e2e (live.spec.ts, speed.spec.ts, sheet.spec.ts) green.
Suites: `npm test`, `npm run e2e`, typecheck and lint as CI runs them, `npm run check:size`.

### How the lanes wait

- The contract in section 1 is frozen for the three lanes; a change goes through the lead.
- Lane sheet starts at once on the fixture (`run_result_line6.json`, written from section 1.4 and checked against the
  legacy summary numbers) and `fake_hub.ts`; its `runs.ts` stub types are swapped for `app/src/api/gen` once lane
  railsim has regenerated them (one import line). Its e2e waits for lane railsim's router and jobs.
- Lane railsim does not wait for lane ground: at `ground.source = line_file` the run reads no new ground. G2 and G3
  run on the line-file ground.
- Lane ground does not wait for anyone; its `ground.source = region` test runs the profiles jobs only.
- Order of landing for the lead: ground and railsim (either order), then the regenerated openapi.json and gen, then
  sheet. The lead runs the gate from a clean copy: the three parity tests, the e2e, the live budgets, idle CPU.
