# The hub's 3D view: spec

Status: draft for Ben, 22 Nov 2026. Branch `hub_region`. Sources: the nine pages in `design/3d_artifacts/`, `claude/Hub_Region_Architecture.md`, checklist items 2.0.12, 2.0.13, 2.3.4, 2.5.4, 2.5.5 and 2.5.6, the 6 Nov rulings (checklist section 5), and scrutiny section 4. No repository file was changed while writing this. Section 7 (buildings) was added on 24 Nov 2026, after Ben's rulings of 23 and 24 Nov.

Ben's aim: the hub's 3D view looks like these pages. Every bridge, viaduct, tunnel and station on every line and in every era is drawn from the model, and it moves when the design changes.

Abbreviations for the source pages (all in `design/3d_artifacts/`):

| Short | File |
|---|---|
| R | `Cincinnati_River_Bridges_3D.html`. Byte-identical to `design/river_bridges/Cincinnati_River_Bridges.html`. Holds the C&O block (lines 122-854) and the CS block (lines 857-1208, `TM` at 858, `buildCS` 860-1208). |
| S | `Cincinnati_Southern_Bridge_3D.html` |
| C | `C_and_O_Bridge_1927_3D.html`. An earlier copy of R's C&O block, with line numbers about 33 lower. |
| W | `Cincinnati_Western_Viaduct_3D.html` |
| A | `Viaduct_Arcade_3D.html` |
| MB | `Metro_Box_Cutaway.html` |
| MT | `Metro_Tube_Cutaway.html` |
| MS | `Metro_Tube_and_Box_Sections.html`. Nine static SVG plates (A to I), no script. |
| ST | `Station_3D.html`. An older copy of `tools/station3d/page/index.html`. The hub copy adds `bridgeParts()` (line 321) and already routes `truss` to the rectangle branch of `profilesFor` (279). |

---

## 1. The look

The nine pages fall into three groups:
- **The structure pages (R, S, C, W, A, MB, MT).** Realistic, matte and true to scale.
- **The diagram page (ST).** Translucent solids in line colours over a see-through ground, with 1 px line work.
- **The drawing page (MS).** SVG section plates.

Ben named the artifacts as the end goal, so the structure look is the default, called **Model mode**. The ST look stays as a second mode, called **Diagram mode**, because it is still the best way to read stacked levels at an interchange. Both modes use the same geometry. Only the materials change.

### 1.1 Background, sky and dark mode

- **Background.** A flat `scene.background` from the CSS variable `--scene`, with no sky dome and no fog:
  - light #dfe6e9 (R, S, C);
  - dark #1f292e.
- **Where the pages disagree.** W and A use #dfe7ec and #1e2a30. MB and MT use #e9eef0 and #1b252a. ST uses `--view` #dfe3de and #101514.
  - R wins, because it is the combined bridge page and three of the pages share its values.
- **Dark mode.** Only the background and the DOM labels follow the theme (all pages agree). Materials do not change with the theme.
- **Where the values live.** Both background values are params: `look.scene.light` and `look.scene.dark`.

### 1.2 Lights

| Light | Value | Source |
|---|---|---|
| Hemisphere | sky #f2f4f5, ground #6d6a60, 0.85 | R, S, C |
| Sun | #fff4e2, 0.9. Default direction: from the west-north-west, elevation about 44°. R puts the sun at (−900, 900, 1900) aimed at (−400, 0, 1100) in the C&O frame, which is a bearing of about 288°. C's sun is at about 282° and 40°, and S's at about 334° and 45°. All three are backlit drawing choices, not the real sun at Cincinnati. | R |
| Fill | #e6edf5, 0.2, from roughly opposite the sun. Only when shadows are off. | W (A: #e8eef5 at 0.32) |

- **Where the pages disagree.**
  - W and A have no shadows. They use weaker lights (W: hemisphere 0.6 and sun 0.55; A: 0.78 and 0.6) plus a fill.
  - MB and MT have no shadows and **no fill**: a hemisphere (#ffffff over #8a8f94) at 0.85 and a white sun at 0.55.
  - ST uses a hemisphere at 0.75, a sun at 0.55, and a fill at 0.25 from below.
- **Shadows win.** The bridge pages read best, and soft long shadows under decks and trusses are a large part of why.
- **Shadow settings.**
  - PCF soft shadows.
  - Bias −0.0006 and normalBias 0.6, as in R. S and C set no bias. S's deck and tower face show shadow acne in `sb_v-deck.png`. S also uses a 2048² map over 1000 × 720 m.
  - Fit the shadow camera to the view frustum each time the camera settles. At region scale, use cascaded shadow maps (three's CSM addon) so texels stay under 0.25 m within 500 m of the target.
  - One 4096² map over 4.8 × 4.0 km is too coarse (R: about 1.2 m per texel).
- **Interior views.** Inside a box or a tube (camera below ground and inside a structure), switch shadows off and use the MB and MT rig: hemisphere 0.85 plus sun 0.55, no fill.

### 1.3 Materials

- **Model mode.** `MeshLambertMaterial` throughout, as all seven structure pages do.
  - The only exception is MB and MT, which draw their distance-marker plates as `MeshBasicMaterial` with canvas text.
  - There are no PBR materials or environment maps.
  - Emissive is used only for lamps (signal aspects, tunnel lights, blue lights) and lit shopfronts.
- **Diagram mode.** One material per line in the line's KML colour: `MeshStandardMaterial`, roughness 0.7, flat-shaded, double-sided.
  - Opacity 0.45 by default, with a slider from 0.1 to 1.
  - depthWrite only at 0.95 and above.
  - Platforms are opaque and coloured by system, not by line: Metro grey #a3a69f and RER pink #e08aab. They darken by ×0.84 for each 8 m below ground, up to 4 steps (ST 168 and 482-496).
- **Two values per material** (main and secondary, wall and trim). This is what gives the R, S and C pages depth without textures. Keep it.
- **Textures.** Only small procedural canvas textures, generated in the app (not shipped in GLBs), with UVs in metres:
  - Ashlar: one 2.4 × 1.2 m tile holding two 0.6 m courses of 1.2 m stones laid half-bond (A `ashlar` 128-136, W `ashlarT` 139-146, ST `ashlarTex`).
  - 1930s concrete: speckle, one joint line per 8 m tile, and 1 m lift lines on the deco variant only (W `concrete` 131-138). This is not board-marked.
  - Windows (L1) and brick courses (L2), for buildings only (section 7).
  - Steel, Metro concrete and ballast stay flat colour.

The palette is a `look.materials` param group: one entry per material id, holding hex, opacity, side and texture. Where pages disagree on one role, the table names the winner.

| Material id | Hex | Source and notes |
|---|---|---|
| steel.grey, steel.grey_d | #70777b, #5a6064 | R 242 (C&O; the facts table says "drawing value (not ruled)"). Kept as the default steel. |
| steel.green, steel.green_d | #88a898, #6d8c7d | R 950 (CS, Hohenzollern pale green) |
| steel.dark | #3f4a54 | W 148-154 (APEx-era girders and tied arch) |
| steel.arch1933 | #55605a | W (`steelA`) |
| stone.cream, stone.cream_d, stone.cream_t | #dcd4c0, #c6bda7, #e9e3d3 | R CS towers and approach piers |
| stone.pier_old, stone.pier_new, stone.pier_cap | #b3ab9b, #c6bfae, #d3cdbe | R C&O piers: the old pier and its extension. pier_new is also R's wall stone for the trough, climb, viaduct piers, abutments and Kentucky walls. pier_cap is also R's platform stone. |
| stone.quay, stone.quay_t, grille | #d3c9b2, #e2dac7, #2e2b27 | R Embankment (`embS`, `embT`, `grille`) |
| stone.ashlar_warm (base/joint) | #dcc7a0 / #bfa77e | A and the ST arcade. Recess #c9b58e / #ad9670 (ST). Soffit #cdb891 / #b19a72 (A; its `vault()` is never called). |
| stone.ashlar_grey | #c9c5ba / #a7a296 | W, the 1913-1920 masonry. Trim #d6d2c7. |
| stone.trim, trim_d, groove | #d6bf94, #c9b083, #8f7a58 | A |
| pylon | #d3bc90 | A catenary pylons |
| granite, bronze | #4b4f53, #5b4a33 | A |
| glass_lit | #33434b, emissive #4a3010 | A shopfronts |
| deco, deco_d, deco_t, flute | #d9ceb3 (lines #c2b594), #c9bc9c, #e4dabf, #9a8d70 | W, the 1933 concrete |
| apex, apex_d | #c8cdcf (lines #b3b9bc), #aeb4b7 | W, modern concrete. Grey against the warm 1930s cream: this contrast is the era cue. |
| concrete.bridge | #a9a59c | R, S decks and approach slabs |
| metro.concrete, metro.concrete_d, metro.slab, metro.steel | #b9c3c7, #9aa6ab, #aeb7bb, #5b6670 | MB 135-140 (concrete_d is the base slab and end face) |
| iron, ring_joint, walkway, handrail | #6d7883, #3b444b, #c2c9cc, #4c565e | MT 135-140 (MT's invert fill and bench walls use metro.slab #aeb7bb) |
| ballast | #8a857b | R, S, C, W. A's #8c877d loses. |
| rail | #34383b | R, S, C, W. A's #3a3d40 and MB and MT's #30363a lose. |
| sleeper.timber, sleeper.concrete | #8a6a45, #9a978f | MB and MT (timber), A (concrete) |
| third_rail | #c8692c | MB, MT, ST |
| fill, emb | #8f8a7c, #8e9375 (double-sided) | R |
| ground | #9fa48c | R, S, C. W drapes a street-map texture instead; its `ground` material is unused. A's #a9a596 and ST's #c9c2a8 lose. |
| water | #5b7780, opacity 0.88 | R, S, C |
| road, pave, kerb | #5d6062, #a39d8f, #9c978c | road and pave R. kerb is defined in A but unused. A's streets use asphalt #4a4d50 and walk #a8a294. |
| canopy, building | #a7abab, #b9a68a | R |
| void, slit, door | #15191b, #26241f, #3a3631 | W (void), R C&O (slit), R CS (door) |
| fence | #4a3a2c, opacity 0.4, double-sided, no depthWrite | R CS, S |
| mast, wire | #59636a, #2c3236 | A, W (wire), ST (mast lines) |
| equipment.* | signal #1d2a30; lamps red #d23b2a (emissive #551008), amber #e5a51d, green #2fae5a (emissive #0d3a1d); trip #e0b23a; cbtc #2f8f55; pipe #b8352a; blue light #2f64c9 (emissive #16306a); lamp #ffe9a8 (emissive #ffd36a); cable #3a4246; drain #2b3a48 | MB 135-140, ST 906-913 |
| car, car_under, car_window | #dfe7ec, #46525a, #2a3a44 | MB, MT |
| xpassage, fire_door | #c9d0d3 at 0.55, #b8352a | MT |
| highlight.rerc | #ffce00, opacity 0.5, no depthWrite | R, S: the RER C covered way (`tube`) and, at 0.45, its line marked on the ground (`rerc`). Used for the see-through focus line. |

**Steel colour** is a field on the bridge record (`steel_mat`), not a constant. R marks C&O grey "not ruled", so it stays a param until Ben rules it.

### 1.4 Ground and water

- **Ground.**
  - Opaque #9fa48c, Lambert, receiving shadows.
  - Heights come from `region.ground` for the view's year and timeline. Map 3 canon replaces the pages' TER, RIV and grid blobs.
- **See-through toggle**, from R, S and C, and the default in the station workspace:
  - ground opacity 0.35, depthWrite off;
  - water hidden.
  - ST's ground-opacity slider (0 to 1, default 0.25) is kept as the slider.
- **Water.**
  - A surface at 139.62 m for every year (6 Nov ruling), #5b7780 at 0.88.
  - Drawn only where the ground is below river + 0.5 m, as R already does for its outer river mesh (R 748).
  - R's full-rectangle plane under the detailed ground (R 721-722) z-fights near the banks, so it is not ported.
- **Streets, blocks and plots.**
  - Draped as a texture from the map's tile layers. This is W's method: a 0.5 m/px street map (2784 × 2480 px) on the 4 m heightfield.
  - Lots stay draped. Buildings are drawn in 3D from `building` records (section 7).
  - ST's ribbons and flat block polygons lose, because they z-fight and cost draw calls.

### 1.5 Edges and line work

- **No edges, outlines or line work in Model mode.** The seven structure pages agree: silhouettes come from members drawn at real size.
  - Chords 1.6 to 3.2 m (C&O 1.6 × 1.8 and 2.0 × 2.6; CS 1.9 × 2.2 and 2.4 × 3.2).
  - Diagonals 0.8 to 0.9 m.
  - Hangers 0.45 to 0.55 m.
  - Handrails 0.07 to 0.08 m.
- **ST draws 1 px `LineSegments`** for rails, catenary masts, truss webs (hub copy), blind arches, arcade railings and girders, and tunnel equipment runs.
- **Exceptions in the hub.**
  - Rails in Diagram mode stay 1 px lines in the line colour, as in ST.
  - The selected record gets a screen-space outline.

### 1.6 Labels

- **Look**, shared by R, S, C, W, A, MB and MT:
  - HTML leader tags;
  - JetBrains Mono 500 at 11 px, `--ink` on a `--sheet` background with a 1 px `--rule` border;
  - a 1 × 10 px `--muted` leader, `translate(-50%, -100%)`.
- **Where the pages disagree.** ST uses canvas sprites: Barlow Semi Condensed 600 at 26 px, on a white (0.88) rounded pill, with a line-colour bar on line labels. Scrutiny suggested an SDF atlas.
  - The DOM look wins.
- **The faults the pages share are fixed:**
  - **Distance culling per label class:** 75 m for equipment (MB, MT), 170 m for detail (A), 6 km camera distance for station names (ST, which also shows only the nearest 45). R, S, C and W do not cull.
  - **A screen-space collision pass**, so lower-priority labels hide. Priority order: station, structure, element.
  - **An occlusion test** against a depth readback of the label anchor every settled frame, so labels hidden by solid geometry fade.
  - **A pool** of at most 80 live label nodes.
- **Line labels** carry the rail level, as ST does ("Line 1 · rail 159.15 m").
- **Fonts** are bundled with the app. The pages loaded Google Fonts and must work offline.
  - Archivo for titles and JetBrains Mono for figures (the structure pages' pair; ST used Barlow Semi Condensed and IBM Plex Mono), unless the app shell rules other fonts.

### 1.7 Camera, frame and controls

- **Frame.** three x = E − E0, y = NAVD88 m, three z = −(N − N0), in EPSG:26916.
  - (E0, N0) is a fixed region origin: the Fountain Square reference, converted from ST's EPSG:32616 origin (lon −84.5125, lat 39.1018; E 715101.96, N 4331019.51).
  - Each GLB carries its own node translation, held as float64 in extras. This keeps vertices as float32 near zero.
  - There is no DATUM offset. The pages disagree, so none wins: 130 in R, S and C; 150 in W and A; the local ground at the station in ST; the rail at 0 in MB and MT.
- **Camera.**
  - Perspective, fov 40, as in the seven structure pages. ST's 35 loses.
  - Near 0.3 (A; ST uses 0.5, MB and MT 0.1), far 120,000 (ST), with a logarithmic depth buffer (ST). The view must run from inside a tube to the whole region.
- **Controls.** OrbitControls with damping 0.08 (ST uses 0.12), plus these from ST:
  - polar angle 0 to π, so the camera can look from below;
  - screen-space panning;
  - distance 5 to 60,000 m;
  - double-click to recentre on a ray hit.
- **Preset kinds:**
  1. **Bearing presets around a target**, from ST: Plan 0/89.5°, Iso 19/26° (ST's "Republic iso"), SE 139/12°, SW 229/32° (the default), SSW 204/28°, From below 19/−22°, and Whole region (0/89.5° at 1.35 × the region box).
     - Distance 620 m (Plan 900 m).
     - Bearings are corrected for grid convergence: about 1.57° at Fountain Square in UTM zone 16. ST's frame is plain UTM (E − E0, N − N0; the snapshot's `frame_turn_deg` −11 is unused), so its "true bearings" are grid bearings.
  2. **Record presets.** A bridge, structure or station record carries `views[]`, as [eye, target] in its own frame. The pages' presets: R's 2 + 14 + 5, W's 7, A's 7, and 5 each in MB and MT.
     - They are converted to 26916 at import.
     - They show as a button row when the record is selected.
- **Saved views.** Saved views and the per-user camera use the legacy `camera` and `view` kinds.
- **Rendering.** Render on demand only: on input, a load, or a param change. All eight 3D pages run a continuous `requestAnimationFrame` loop, and R re-renders its 4096² shadow map every idle frame.

### 1.8 Exaggeration

- **The pages.** None of the seven structure pages exaggerates. ST spreads levels from ×1 to ×6 in steps of 0.25.
- **Default.** Exaggeration is 1. Model mode is true scale.
- **Formula.** `y' = g + (y − g)·k`, where g is the local ground at the vertex. The ground stays true, and depth below and height above are stretched together. This is ST's `Yp`.
  - It runs in the vertex shader (2.5.5), not by rebuilding as ST does.
- **Station workspace.** Offers 1, 2, 3 and 6.
- **Below-ground only** (an option): a switch clamps k to 1 where y > g. Viaducts then keep their shape while the station stack spreads.

### 1.9 Cutaways

- **Two methods**, both kept:
  1. **Cut windows built into the geometry.** This is the MB and MT look, and the default for tunnels in Model mode:
     - the box's near wall is cut to 2.0 m over the rail and the roof removed;
     - the tube's (and the bore's) upper near sector is removed (angles −0.25 to 2.05 rad);
     - the last 40 m of the 250 m model is kept whole for context.
     - The window is a parameter of the tunnel component (`cut`).
  2. **Clipping planes** (ST): cut away above a level (slider 120 to 190 m, ST 701-702), and the near half through the target, normal to the horizontal view direction (ST 1059-1062).
     - **New:** a section plane at a chainage, normal to the path. ST has no such plane.
     - **New: stencil caps**, so cut solids read as solid (2.5.5). The cap colour is the material's darker value. ST has no caps, so its cut solids look hollow.

---

## 2. The component library

### 2.1 Where it lives and what it returns

- **Package.** `engine/src/mesh/`. It is pure TypeScript, has no DOM, and does not import three.js.
- **Where it runs:**
  - in the Node sidecar, for the server's GLB job;
  - in the app's engine Web Worker (`app/src/engine/worker.ts`), for draft edits.
- **Engine methods.** Exposed as `mesh.section@1`, `mesh.structure@1`, `mesh.bridge@1` and `mesh.station@1`.
- **Input contract.** `mesh_input/0` (zod), built by Python from records. As with `vertical.rail`, the engine never reads records.
- **Units.** Metres, degrees, and months since year 0.

Shared output types:

```ts
type MatId = string;                       // a key of look.materials, e.g. "steel.green"
interface Part {                           // one material bucket; becomes one BufferGeometry group
  mat: MatId; pos: Float32Array; nrm: Float32Array; uv?: Float32Array; idx: Uint32Array;
  el: Uint16Array;                         // per-vertex element index into Mesh3.elements (picking, eras)
  g?: Float32Array;                        // per-vertex local ground (exaggeration)
}
interface InstanceSet { mat: MatId; proto: Part; xf: Float32Array /* 16 per instance */; el: Uint16Array }
interface Element { rec: string; path?: string /* e.g. "/piers/3" */; open?: number; close?: number; c0?: number; c1?: number }
interface Mesh3 { parts: Part[]; inst: InstanceSet[]; elements: Element[]; bounds: [number, number, number, number, number, number] }
```

- **In the app.** `toObject3D(mesh)` builds one `BufferGeometry` per Mesh3, with one `addGroup(start, count, matIndex)` per material id and one `InstancedMesh` per InstanceSet.
- **In the sidecar.** `toGlb(mesh)` writes glTF 2.0 with:
  - one primitive per material, with the material named by id;
  - `EXT_mesh_gpu_instancing`;
  - custom attributes `_EL` and `_G`.
  - Writer: `@gltf-transform/core`, which is pure and works in both Node and the browser.
- **Merging.** Parts are merged by material, which keeps draw calls per section in the tens.
  - R, S and C draw one call per material (R: 34).
  - MB and MT add one mesh per box (128 and 151 draw calls), which is not the pattern to copy.
- **Instancing.** Repeats are instanced: piers of one size, columns, sleepers, ring joints, equipment and catenary portals.

### 2.2 Frames and kernel functions (used by every group)

| Function | Parameters | Output | Ported from |
|---|---|---|---|
| `pathFrame(path, rail, opts)` | path: 26916 LineString; rail: the solved `rail_m` array on the 2 m grid; `bank: false` | `at(c) → {E, N, z_rail, t, n}` by bisection | R `mkPath` 398-408; C 365; W `clAt` 159, `makeFrame` 405; ST `sweepData` 249 (plan tangent). Port the engine's `geom/path.ts`; no new path code. |
| `rigidFrame(E0, N0, az_deg, z0)` | | a local frame: x along, z across | R's C&O frame is implicit (no constant in the page). Derive it from the Bridge Spans KMZ C&O line: midpoint, az 166.358°. R `TM` 858 (CS); W E0/N0 (DATA, line 111). |
| `warp(mesh, frame)` | maps local (u along, v up, w across) to world | Mesh3 | W per-vertex warp 614-617; A `faceM` 203 |
| `beam(mat, a, b, w, h)` | w across (m), h depth (m) | an oriented box | R 260-264 and 964-969; S 212; C 227 |
| `box(mat, x0, x1, y0, y1, z0, z1)` | | an axis box | R 265; S 218; MB 143 |
| `camber(x, L, cam_m = 0.25, ca = 1.0)` | | inverted catenary offset | R 269 (CS cam 0.5, 979); S 227 |
| `cbox(mat, x0, x1, …, stations)` | stations: 45 over the main span (C&O, R 270), 65 over the span (CS, R 980) | a box split to follow the camber | R 272-279, 981-987; S 229 |
| `prism(mat, ring2d, y0, y1)` | | a vertical extrusion of a plan polygon, holes allowed | R `prismShape` 347; C 314; A 288; W `extrude` 414 |
| `sweep(mat, profile[[w, v]] \| fn(i), frame, c0, c1, step = 2)` | closed or open | a swept solid with end caps | ST 249-263; W `solid` 190 (offset rows `[d, zb, zt]`); MT `extrude` 153-157 (straight case) |
| `skewBox(mat, frame, c0, c1, w0, w1, zb, zt, skew_k)` | | a box between skewed lines | W `boxAt` 202 |
| `archCurve(span, rise, springing, n = 17)` | segmental, or semicircular when rise ≥ span/2 | a polyline | S `archPath` 281; A `arc` 212; W `intr` 208; ST `shapeOf` 989 |
| `wallWithOpenings(outline, holes[], thick)` | | an extruded wall | S `rectShape`, `arcade`, `wallX`, `wallZ` 285-295; R 1037-1047 |
| `instances(proto, xforms)` | | InstanceSet | MB `inst` 144-147; MT 149; A sleepers 398 |
| `annulusSector(r0, r1, a0, a1, segs = 72)` | | a profile ring for `sweep` | MT `shell` 159-162 |

### 2.3 Bridges

All bridges are built in the bridge's `rigidFrame`. x runs along the span line from abutment to abutment, centred at the midpoint (Ohio negative). z runs downstream. y is relative to the carried rail.

| Function | Parameters (units, defaults) | Material ids | Ported from |
|---|---|---|---|
| `parkerSideSpan` | L m; panels 13; ds1 12.5 m (first panel); smax 19 m (midspan); ds 13 m (at the pier); diagonal pattern pratt_to_mid; chord 1.6 × 1.8 m; diagonal 0.8; vertical 0.9; weight k 1.0 (1.35 for a shared rib); sloped end posts true | steel, steel_d | R `parkerH` 155, ribs 285-314; C 127, 252-281 |
| `trussArchSpan` (two-hinged, deck tie) | L m; panels 22; hinge_below_rail 7.0 m; rise from Ludendorff's ratio (28.5/156.21 of the arch span: upper-chord crown 38.1 m over the rail on the C&O); crown_depth DC 7 m (so the lower-chord crown is 31.1 m above the rail); exponent NE 4 (the upper chord swoops to the side-span top); lower chord 2.0 × 2.6; upper 1.6 × 1.8; diagonals 0.8; verticals 0.9; hangers 0.45 only where the chord is above the deck; tie 3.0 deep × 1.4 | steel, steel_d | R `aU`, `aLow`, `aTop` 148-149, 285-314; C 120-121 |
| `spandrelBracedArch` (Hell Gate) | L 402.23 m; panels 32; planes ±11 m; hinge_below_rail 9.0; crown depth DC 12; top at towers ZT0 = hinge + 43 m; exponent 8; lower chord 2.4 × 3.2; upper 1.9 × 2.2; Warren diagonals 0.9, crossed in the two crown panels; mid-height strut where panel depth > 22 m; verticals 1.1; hangers 0.55; walkway handrails on the upper chord | steel, steel_d | R 884-885, 989-1010; S 237-258 |
| `tiedArch` | L m; rise L/6.5; hanger step about 5 m (n = round(L/5)); skewed ends from the pier skew lines; deck tie 3.0 deep | steel.dark | W 651-666 |
| `halfThroughArch` (two-rib steel) | L 108.9 m; rib depth 2.4; parabolic; its own springings per rib; floor beams about every 10.5 m; hangers where the rib is above the floor, posts where it is below; wind bracing where it clears the lower trains | steel.arch1933 | W 473-521 |
| `lateralBracing` | panel points; clear envelope rail + 7.2 m (C&O) or 7.5 m (CS); top struts and X; bottom laterals; lower-chord bracing only where it clears the envelope (CS: also below the floor near the towers, with cross frames) | steel_d | R 316-341, 1011-1025; S 261-273 |
| `portalBracing` | end posts; lattice with knee braces | steel_d | R 319-325 |
| `floorSystem` | panel points; cross girders 0.8 × 1.8 (C&O) or 1.0 × 1.8 (CS); stringers 0.44 × 1.6 at ±0.9 m per track; bottom laterals | steel_d | R 335-340, 380, 1027, 1159; S 275 |
| `bearing` | kind: box (C&O, R 343-344) or pin (CS); pin r 0.9, 4.2 long; shoe a 4-sided frustum (r 1.6 at the top, 3.2 at the foot); seat box 5.2 × 0.6 | steel, steel_d | R 1131-1136; S 379-384 |
| `plateGirderSpan` | L m; girder offsets[] m; girder 1.1 × 2.6; slab 0.4 | steel, concrete.bridge | R `deck` 425-431; S approaches 386-401 (girders 1.4 × 3.0 at the truss planes); A `bridge` 312 (girders every 1.5 m, 1.1 deep) |
| `throughGirderSpan` | L; edge girder 0.9 × 2.7; floor slab 0.9 at the soffit (KY ub 1.5 rail to soffit) | steel, concrete.bridge | R 579-581, 658-661 (Kentucky street spans) |
| `continuousGirder` (APEx upper deck) | run c0..c1 from frame to frame; constant depth GD 1.7 m, deepened per run in proportion to its longest bay over 35 m; at most 45 m (GLIM) between frames; on the inner lines and edges | steel.dark | W 590-648. (The haunched 1933 girders, cubic from hm to hh, belong to `bentViaduct`: W `gird()` 221.) |
| `roundEndedPier` | x m; zA, zB (plan ends); r 6 m; halves {upstream: pier_old, downstream: pier_new}; coping 0.6 m wider, 1 m thick; base at bed − 2 m | stone.pier_* | R `halfPier` 349-361; C 316-328 |
| `masonryPier` (approach) | x; 5 m along; width 2·planes + 4; batter 0; cap 6.2 m, 1.2 deep | stone.cream, stone.cream_t | R 1146-1147; S 386-401 |
| `abutment` | length 10 m (C&O; CS Kentucky 6 m); width; to ground − 2 | stone.pier_new, stone.pier_cap (C&O); stone.cream (CS) | R 364-371, 1152; C 331-338 |
| `hellGateTower` | tw 32 m; td 51.7 m; th 63.7 m; batter 1/7 (inner face plumb); portal half-width 9.8 m, crown th/4 above the floor underside; footway arches 4.4 m; cap style deco (band, 3 setbacks and a top, fluting at 2.2 m, stepped corner piers, stepped pylons); doors bool | stone.cream, _d, _t, door | R `tower` 1048-1128; S 296-376 |
| `bridgeDeck` | track offsets[] m (C&O ±2.25 about 0 and −15.2; CS −6.75, −2.25, 2.25, 6.75); slab; stringers; parapet rails 1.1 (CS) | concrete.bridge, ballast, rail | R 375-382, 1155-1161; S 403-409 |
| `footway` | side; width 3.0 m (CS) or 1.6 m (C&O, two handrails, posts every 3 m); fence mesh panels with posts every 2.5 m; brackets | fence, steel_d | R 384-389, 1165-1191; S 413-439 (`rail2`) |
| `stairFlight` | risers 24; riser 1/6 m; going 0.3 m; width | stone.cream | S 427-430. Fix: R and S stop the loop at 24 risers (4 m) or at the ground, so on a lower bank the flight ends in the air. |
| `trussSpanSimple` (L&N) | L; depth from `truss_depth_per_span` 0.125; panels about 12 m; chords 0.8 × 0.9; webs | steel | `tools/station3d/page/index.html` `bridgeParts()` 321 (webs as lines). ST's older `profilesFor` (280-281) sends `truss` to the tube branch with no `od`, which gives NaN; the hub copy already fixed this (279). |

Composite: `bridge(rec)` composes these from a `bridge` record. Twin bridges on shared piers (C&O) are three rib planes with the middle one shared, at k 1.35.

### 2.4 Viaducts and arcades

These are swept along `pathFrame`. Every vertical value is relative to the carried rail.

| Function | Parameters | Material ids | Ported from |
|---|---|---|---|
| `supportLayout` | c0, c1; spacing 25 m; skip streets crossed at skew ≥ 25°; or an explicit list | (layout only) | R `pierList` 432-441; C 399 |
| `bayFit` | run length; target bay 18.3 m; piers 2.0-4.0 m (the result in A's stretch is bays of 16.5 to 19.3 m) | (layout only) | A `fit` 345; ST `ARCD` 926 |
| `streetOpenings` | street paths; rule: open where rail − ground ≥ 6.2 m (R); width = street width/sin(angle) + 3 m (R) or width·hypot(k, 1) (A) | (layout) | R 459-461; A `OP` 165-172 |
| `girderViaduct` | supports; girders 1.1 × 2.6 at offsets; slab 0.4; width = tracks + 2·margin; HW 6.45 for a pair; a quad track shares piers 2HW + 9.6 wide | concrete.bridge, steel, stone.pier_new | R 425-431, 475-488 |
| `bentViaduct` (1933 deco) | bents [{c, skew_k, cols_m[] (−8, −3.1, 7.6, 12.5), cw 1.4, capD, single}]; spans [{a, b, kind, crown, hm, hh}] with haunched girders cubic from hm (mid) to hh (support); flutes on the edge columns; two-step capitals; parapet 1.1 m; string course | deco, deco_d, deco_t, flute | W `buildRun` 215-345, `gird` 221, `stub` 347, `stubC` 355, `plinthC` 362 |
| `hammerheadPier` | single pillar 4.0 × 2.4; cap | deco, deco_t | W 219, `capZo` 227, 293-298 |
| `portalFrame` (upper deck on stubs) | legs 1.2 × 1.2 on 1930s stubs or plinths; frame GD deep from each leg to just past the inner lines, stepping up to a shallow member over the tracks below; drop a frame when a leg is within 3.2 m of a track below | apex, apex_d | W 579-620 |
| `masonryArchViaduct` (1913-1920) | spans [{c0, c1, springing, crown}]; ring bands; keystones; impost course; parapet | stone.ashlar_grey | W `mason` 427-461 |
| `arcadeFacade` | side; arches [{u0, u1, crown, rise}]; H cornice; piers [{u, w, emblem}]; block state shops, blind or open; ring bands 0.45 and 0.62 m; keystone with 3 grooves; voussoir fans; dentils every 1.05 m; granite plinth 0.9 m; cornice 0.55; railing posts every 2.5 m; recess 0.4 m (blind, shops) or 1.2 m (open) (ST 1014; A's frame instead stands 0.25 m proud of the fill wall) | stone.ashlar_warm, trim, trim_d, groove, granite, bronze, glass_lit | A `facade` 220-277; ST `arcRun` 944-1052 |
| `arcadeViaduct` | face runs from the structure's edges; fill to rail − 0.5, or open bays with `plateGirderSpan` behind spandrel-only fascias at street openings; soffit | as above plus the soffit ashlar | A `build` 334-504; `layout` 324 |
| `blindArcadeWall` (embanked climb) | walls 0.9 m thick from ground − 1 to rail + 0.4; fill; blind arches of half-width 3.4 m, height ≤ 9 m, every 10 m where the wall is over 4.5 m high. R draws these as flat decals 0.02 m proud of the face; the hub builds them as real recesses (0.4 m, as ST's arcade). | stone.pier_new, fill, blind arch #8f8778 | R 463-474, 587-592; C 430-441 |
| `embankmentSlope` | slope 1:1.5; toe from ground | emb | R 665-677; C 632-644 |
| `trough` | walls 0.8 m to ground + 1; floor slab 0.4 | stone.pier_new (walls), concrete.bridge (floor) | R 453-457; C 420-424 |
| `portalHeadwall` | an arched hole per track, 4.8 m wide (half-width 2.4), springing rail + 4; headwall 1.6 m thick to max(ground + 1.5, rail + 8.5) with a 0.6 m coping; dark slit behind (R). W: one flat-topped opening 8.9 m wide to rail + 6.4. Neither page has wing walls (new). | stone.pier_old, stone.pier_cap, slit (R); deco, deco_t, void (W) | R 444-451; W 537-544 |
| `catenaryPortal` | every 4th pier (about 86 m); pylon 9.6 m with band, cap and roundel; lattice girders at rail + 7.7 and 8.6 m; middle masts in the 6.0 m gaps; contact wire 6.4 and messenger 7.3 | pylon, stone.trim, steel, mast, wire | A 399-439; ST masts 570-586, arcade catenary 1037-1050 |
| `trackRun` | offsets[] m; ballast 3.2 × 0.45 (R; A 3.6 × 0.3, W 3.2 × 0.55); rails 0.07 × 0.17 at ±0.7175 (A, MB, MT; R and W use ±0.75); sleepers 0.28 × 0.16 × 2.6 every 0.65 m, instanced (A; MB and MT timber 0.2 × 0.13 × 2.4 every 0.6 m) | ballast, rail, sleeper | R `track` 415-424; W `railLine` 547, `track` 561; A 382-398 |
| `parapet` | height 1.1 m above deck top; coping | by style | W, A |

### 2.5 Tunnels

MB and MT build these as straight extrusions. Here they are swept along `pathFrame`. The section profile is defined once and used by both the 3D sweep and the 2D section pane (the MS plates).

| Function | Parameters (defaults from `metro_structure` params) | Material ids | Ported from |
|---|---|---|---|
| `boxSection` (double-track box) | inside 7.9 m; roof underside 4.0; top 4.6; below 1.0; walls 0.6; base slab 0.55; track slab 0.23; columns 0.25 × 4.22 every 1.524 m (instanced); roof beams 0.18 × 0.34 × 7.9 (instanced); track centres ±1.95; cut window {near_wall_top 2.0, roof off} | metro.concrete, metro.concrete_d, metro.slab, metro.steel | MB 151-161 |
| `twinBox` and `stationBox` | n tracks, margins (`box_margin` Metro 2.6 in the snapshot, page default 2.3; RER 3.25); island box 14.9 m inside with an 8.0 m island at 1.12 m | metro.concrete | ST `build` 434-470; MS plate G |
| `coveredWay` | box 10 × 7.8 m, 22 × 8.6 m at stations (platform 204.2 m) | metro.concrete (the R and S pages draw it as the translucent RER C highlight) | R 764-776; S 441-456 (RER C) |
| `tubeSection` | type A: R 2.55, lining 0.20 iron, rings 0.508 m, bench walls with inner face 1.60 m from the track centre, top 0.9. Type C: R 2.70, lining 0.25 concrete, rings 1.5 m, centre offset 0.17 m outward, walkway at HW + 0.15 = 1.5725 m, top 1.12, handrail 2.12. Both: rail 0.70 over the invert; invert fill top −0.30 (A) or −0.22 (C); cut window angles −0.25 to 2.05 rad | iron or metro.concrete, metro.slab, walkway, handrail | MT `tube` 213-256; `shell` 159-162; `segBelow` 165-169; `bench` 170-175 |
| `twinTube` | centres 8.74 m (A) or 9.14 m (C) | as above | MT `STR.A` 262-275, `STR.C` 276-289 |
| `doubleTrackBore` | R 4.3; lining 0.2 cast iron, rings 0.508; rail 2.30 over the invert; tracks ±1.95; bench walls ±(1.95 + 1.6), top 0.9; invert fill top −0.30 | iron, metro.slab | MT `STR.B` 290-318 |
| `ringJoints` | ring pitch; style torus (near), shader stripes (far) | ring_joint | MT `rings` 176-180. The tori cost about 400k triangles for type A (MT renders 414k in all), so beyond 50 m use a UV-stripe shader on the lining. |
| `crossPassage` | between the tube skins; 2.0 × 2.2 m; floor at bench (A 0.9) or walkway (C 1.12) level; doors 1.2 × 2.0; cuts an opening in both linings; for type C, on the walkway side | metro.concrete, fire_door | MT 257-260. Fix: MT cuts neither lining, for either type, and puts the type C passage between the tubes on the third-rail side, where there is no walkway. |
| `cutAndCover` | `boxSection` plus backfill to ground and cover 0.6 m; the excavation drawn only in a section cut | metro.concrete, fill | MB plus the snapshot's `struct` (cutcover `{below 1.0, top 4.6, cover 0.6, width 9.1}`) |
| `tunnelPortal` | as `portalHeadwall`, with retaining wings | stone or concrete | R 444-451; W 537-544 |
| `equipmentKit` | tunnel type box, A, C or bore; EQPOS [u from the track centre, + toward the outer side; h over the rail] per item; spacings: lights 18, transponders 100, radio 300 (phase 150), signals 250 plus platform ends, hose 61, blue lights 250 (phase 125), markers 100, intrusion detection on the last 100 m into each platform, sumps at rail low points, shafts 3 × 3 m at station ends (a second 8 m on for tubes deeper than 20 m), cross passages 200 | equipment.* | MB 164-220; MT 183-253; ST `EQPOS` 807-816 (hub copy 860-869), placement 840-913 |
| `train` | cars 4 × 19.9 m at 20.3 m pitch; body 2.845 wide × 2.4 high; bogies at ±7.1 m. Floor and roof heights come from the `car` param (1.12, 3.66), not MB's 0.95 and 3.595. | car, car_under, car_window | MB 221-230; MT 197-205 |

Cutaway: `cut` is a parameter on each tunnel function: none, near_wall, upper_near, or `{keep_from_c}`. Clipping planes with stencil caps stay for the general view.

### 2.6 Stations

Only some of these come from the pages: R draws platforms, canopies and a building; S draws stairs; ST draws boxes, platforms and shafts. **Lift, hall, passage and entrance are new.** No page draws them, so they are sized from `station_element` records and the Fountain Square model (`fs_model.py`, 2.5.1).

| Function | Parameters | Material ids | Ported from |
|---|---|---|---|
| `platformSlab` | outline (or c0, c1, offset, width); top above rail (1.0 m RER and intercity, 1.12 m Metro, from the param per system); edge coping | concrete.bridge or metro.slab (R uses stone.pier_cap) | ST 482-496; R 629-632. Fix: ST makes one ExtrudeGeometry per platform. |
| `canopy` | outline; underside 5.4 m over the rail (4.4 m over a 1.0 m platform), 0.3 thick; columns 0.4 square about every 12.5 m | canopy, steel | R 632-636 |
| `stationBuilding` | outline; height (R: to rail + 9.0, cap 0.6); roof | building | R 638 |
| `hall` (concourse) | outline; floor z; ceiling; columns | metro.concrete | new |
| `stair` | path; width; risers; landings | concrete | S stairs; new for general use |
| `escalator`, `lift` | path or point; width; rise; shaft size | steel, glass | new |
| `passage` | path; width 3.0; height 2.6 | metro.concrete | new |
| `entrance` | point and heading; kiosk or headhouse; stair down | stone or glass | new |
| `ventShaft` | 3 × 3 m; from the rail to the ground; a second shaft 8 m on for depth > 20 m (tubes) | metro.concrete_d | ST 896-898, 911 |

### 2.7 Ground and water

| Function | Parameters | Material ids | Ported from |
|---|---|---|---|
| `terrainTile` | tile bbox; step (5 m near, 10 m, 200 m far); heights from `region.ground` (year, timeline); skirts; draped texture | ground | R 703-723; W 377-387; ST `groundAt` 209 |
| `waterSurface` | level 139.62; mask where ground < level + 0.5 | water | R 726-758 |
| `quayTerrace` (the Embankment) | bank polyline; river wall from 137.5 to quay + 0.35; quay 12 m at 142.0; terrace wall to 151.8 with string course 148.3-148.75; pilasters every 12 m; grilles 4.8 × 4.4 in alternate bays; balustrade (balusters at 0.55 opacity); terrace to 52 m | stone.quay, stone.quay_t, pave, grille | R 777-825 (`face`, `cap`) |
| `streetSurface` | street polygon and levels; road 0.04 m and walks 0.16 m over the ground (a 0.12 m kerb, A); R lays roads 0.12 m over the street level | road, pave, kerb | R 692-697; A 446-478 |
| `lotMass` | replaced by section 7: `building` records drawn by `mesh.building@1` | | 2.3.11 |

**Earthworks are not meshed here.** The trough cut, the made ground over the tunnel and the street re-grades change `region.ground` itself through earthwork records, so every pane sees the same ground. R edits the heightfield per vertex (708-717), and that is not ported.

---

## 3. Records

### 3.1 Rules for every component

1. **Levels belong to profiles** (one owner, 9.25).
   - A structure stores heights relative to the rail of a carried section (`*_below_rail_m`, `*_above_rail_m`) or to the ground (`*_above_ground_m`).
   - It never stores an absolute rail level.
   - The only absolute levels allowed are tied to the river or a datum: the 139.62 river, the 142.0 quay and the 151.8 terrace.
   - Every page bakes in levels (`RAIL` constants, `RT`, `KY`, `cl.ur/lr`, `railAt`). Those become checks, not inputs.
2. **Plan positions** come from section paths in EPSG:26916, with chainage `grid:26916`, or from the record's own 26916 geometry.
3. **Sizes and rules** come from `param` records in the registry, with rule ids. "Drawing value" entries in the facts tables become params with `status: drawing_value`. "Ben, <date>" entries become `ruling` refs.
4. **Eras.**
   - Each record and sub-element carries `open` and `close` partial dates (9.16).
   - A record's `phase` names its era of work. Example: W's 1933 lower deck against the APEx-era upper deck.

### 3.2 Component to record

| Component | Driven by | Fields read |
|---|---|---|
| `pathFrame` | `section` (existing) plus the solved `vertical.rail` result | path, length_m, scale; `rail_m` array; `profile.ovr`, `profile.tf` (types) |
| `trackRun` | `track` (existing, **v2 needed**) | c0, c1, tracks, **offsets_m[] (new)**, **ease_m (new)** |
| `boxSection`, `tubeSection`, `twinTube`, `doubleTrackBore`, `cutAndCover` | `profile.ovr` and `profile.tf` ranges (existing), plus params `metro_structure.box.*`, `.tubes.{A,C,bore}`, `.car` and `.envelope` (existing), and `line_phase` and `piece_phase` (existing; they pick A, C or bore) | **New params:** wall 0.6, base slab 0.55, track slab 0.23, rib 0.18 × 0.34, sleeper pitch 0.6, gauge 1.435, third-rail section, ring width 0.508 and 1.5, bench offset and top, walkway offset and top, invert fill tops |
| `equipmentKit` | **new params** `metro_structure.equipment.{box,A,C,bore}` (EQPOS) and `.spacing.*` (MS plate I); sumps from `rail_m` low points; shafts from `profile.shafts` (existing) | |
| `crossPassage` | **new kind or sub-array** `structure.cross_passages[{c}]` on twin-tube ranges, at most 244 m apart (rule) | |
| `coveredWay`, `trough`, `girderViaduct`, `bentViaduct`, `masonryArchViaduct`, `arcadeViaduct`, `blindArcadeWall`, `embankmentSlope`, `portalHeadwall`, `portalFrame`, `continuousGirder`, `tiedArch`, `halfThroughArch` | **new kind `structure`** | see 3.3 |
| bridge components | **new kind `bridge`** | see 3.3 |
| `catenaryPortal` | **new params** `catenary.*` (spacing 86 m, pylon style, heights); masts placed by rule on the structure | |
| `platformSlab` | `platform` (existing, **v2 needed**) | side, length_m, **width_m**, **height_above_rail_m** (null takes the system param), **outline** (null derives it from the stop c, offsets and length) |
| `canopy`, `stationBuilding`, `hall`, `stair`, `escalator`, `lift`, `passage`, `entrance`, `ventShaft`, `stationBox` | **new kind `station_element`** | see 3.3 |
| `terrainTile`, `waterSurface` | `region.ground` (existing) and `ground_layer` (9.15) | year, timeline |
| `quayTerrace` | **new kind `earthwork`** (for the ground) plus a `structure` with form `quay_wall` (for the masonry) | |
| `streetSurface` | streets of 2.3.8 to 2.3.10; until then **new kind `context_feature`** | polygon, levels[], lower_m, clearance_m |
| buildings (`mesh.building@1`) | **new kinds `building`, `building_style`, `site` and `envelope`** | see section 7 |
| look | **new param group `look.*`** | materials, scene, lights, labels, presets |

### 3.3 New kinds and new fields

Feature folder `region/ext/structures/`: kinds `structure`, `bridge`, `station_element`, `earthwork` and `context_feature`.

#### `structure` (merge unit `field`; sub-arrays keyed by id)

**Geometry and columns.** Geometry is none when the structure lies on a section. It is a Polygon footprint for a context structure such as CUT. Columns: name, parent = /section, c0, c1, phase, and the open/close interval columns.

| Field | Meaning |
|---|---|
| section, c0, c1 | the host range |
| carries[] | `{section, c0, c1}` for the other sections on the same deck: the C&O quad track, the ten tracks on the north arch viaduct |
| level_from | the section whose rail sets the deck level; default the host |
| form | enum below |
| variant | e.g. `tube_A`, `irt1904`, `deco_1933` |
| edges | `{left_m, right_m}`, or a table `[{c, left_m, right_m}]` (A's `edges`); default tracks ± margin param |
| deck | `{formation_m 0.6, depth_m, parapet_m 1.1}` |
| supports | `{rule: {spacing_m 25, skip_skew_deg 25}}` or `[{id, c, skew_deg, kind pier/bent/pillar/stub, cols_m[], cap_m, single, open, close}]` |
| spans[] | `{id, c0, c1, kind girder/arch/steel_arch/tied_arch/through_girder/plate_girder/continuous, depth_m, haunch_m, crown_below_rail_m, springing_above_ground_m, street, open, close}` |
| openings[] | `{id, street, c, skew_deg, width_m, headroom_m}` |
| blocks[] | `{id, c0, c1, state shops/blind/open}`: the arcade's per-block switch (A 507-515) |
| cross_passages[] | `{id, c}` |
| style | a `look.style.*` param path (`arcade_classical`, `deco_1933`, `apex_grey`, `masonry_1913`, `irt_box`, `bridge_masonry`) |
| cut | display default: none, near_wall, upper_near |
| bridge | ref, when form is `bridge` |
| rulings[], views[], attrs | |

**Form enum:**
- tunnels: box, twin_box, station_box, island_box, tube, twin_tube, bore, cut_cover, covered_way, portal;
- open: trough, retained_cut, embankment, wall_embankment;
- elevated: girder_viaduct, bent_viaduct, masonry_arch_viaduct, arcade_viaduct, ramp_viaduct, bridge;
- other: quay_wall.

**Validation.** A new registry rule, `struct.walls_below_track`:
- For each carried section at each 2 m step, the solid's top must be at or below rail − formation.
- Parapets may reach rail + parapet_m, and only outside the kinematic envelope.
- A section that is not carried but passes through the footprint must keep its envelope (rail − formation to rail + 5.5 m) clear of the solid.
- A breach is an `error` flag with a rule id, shown in the issues pane and as a red band in the 3D view.

#### `bridge` (geometry LineString: the span line in 26916, abutment to abutment; the frame is derived as the midpoint plus the azimuth)

| Field | Meaning |
|---|---|
| name, form | form: ludendorff_twin, spandrel_braced_arch, parker_through, truss_arch, tied_arch, half_through_arch, plate_girder, lattice_truss |
| carries[] | `{section, offset_m}`: tracks or pairs and their offset from the span line (C&O pairs at 0 and −15.2) |
| planes[] | `{offset_m, weight}` (C&O 7.6, −7.6 and −22.8 with the middle at 1.35; CS ±11) |
| spans[] | `{x0_m, x1_m, type parker_through/truss_arch_tied/spandrel_arch/plate_girder, panels}` |
| arch | `{hinge_below_rail_m, crown_low_m (rel. rail), crown_depth_m, top_at_towers_m, exponent, panels, diag warren/pratt}` |
| side | `{ds1_m, smax_m, ds_m, panels}` |
| camber | `{cam_m, ca}` |
| piers[] | `{id, x_m, shape round_ended/rect, r_m, halves [mat, mat], coping_m, base: bed − 2}` |
| towers | `{style hellgate_deco, tw_m, td_m, th_m, batter, portal_ratio, cap_m, doors}` |
| approaches | `{span_m 30, pier style, end: abutment where the ground meets the deck}`. Fix: R caps each CS approach at 12 spans and puts an abutment only at the Kentucky end, so the Ohio approach can end in the air (R 1141, 1152). |
| footways[], abutment `{length_m 10}`, steel_mat, facts[] `{key, value, ruling or param}`, views[] | |

Two records come from R: the C&O and the CS. The L&N comes from the hub's `bridgeParts()` data (the snapshot's Line_1 `bridges`, "L&N bridge truss spans", piers at 16384.5, 16537.5, 16598.5, 16661.5, 16722.5 and 16780.4).

#### `station_element` (geometry Polygon, LineString or Point in 26916)

| Field | Meaning |
|---|---|
| station | ref |
| element | platform_slab, canopy, hall, concourse, stair, escalator, lift, passage, entrance, shaft, building, box |
| base | `{ref: the rail of a section or platform, or the ground, or an element; z0_m, z1_m}` (relative) |
| connects[] | element refs: the walking graph of 2.5.1 |
| attrs | width, risers, capacity, headroom |
| open, close | |

#### Smaller kinds and new fields

- **`track` v2.** Adds `offsets_m[]` (one per track, signed, positive to the left of the chainage direction) and `ease_m`. Fans and turnouts come later as nodes (2.2.3).
- **`platform` v2.** Adds `width_m`, `height_above_rail_m` and `outline`.
- **`earthwork`.** Forms: pad, corridor, quay_terrace, trough_cut, made_ground, street_regrade. Each has a geometry and a template `[[offset_m, height_m]]` or params, plus years.
  - It feeds the `region.ground` compositor, which already has a parametric Pad and Corridor (2.0.2).
- **`context_feature`.** For streets with levels, until the street model of 2.3.10 exists. It is then migrated into that model.

### 3.4 Importers (hard-coded page data to records)

`import.artifacts_3d` reads the `artifacts_3d` tier (`configs/hub_paths.json`) and `design/3d_artifacts/`. It has one sub-importer per page. Each runs dry, then applies into the layer `import:artifacts_3d`, and Ben promotes the results through the review queue.

**How the data is read.**
- The embedded blobs are single-line JSON (`TER`, `RT`, `KY`, `RIV`, `RC3`, `EMB` in R; `DATA` in W and A) and are parsed by name. A blob may be followed by more code on the same line, so it is read with a raw JSON decode, not a whole-line parse.
- Scalar constants are listed in the importer with their source line, as `param` records with `status: drawing_value`.

**What each page gives:**

1. **R, with C and S as cross-checks.**
   - **Frames.**
     - **C&O frame.** It is not stored in R. Derive it from the Bridge Spans KMZ C&O line: origin E 714526.441, N 4329830.902 (midpoint; L 473.46, az 166.358°); x̂ = (0.235861, −0.971787) toward Kentucky; z downstream = (−0.971787, −0.235861) in (E, N). Mapping (x, z) to (E, N) has determinant −1, the same handedness as three's usual x = E, z = −N. RT's portal then lands about 1.6 km west and 1.0 km north of the bridge, which checks.
     - **CS frame.** `TM` is a pure rotation of +26.30° plus the offset (−1168.371, 1738.455) into the C&O frame.
     - Both are converted to 26916 (option (a) of 2.0.12).
   - **Records written:**
     - bridge records for the C&O and the CS;
     - structures on the C&O N/E and S/W sections: trough 0-170, wall_embankment 170-740, girder_viaduct quad 740-1570.9 with shared piers, the two curve viaducts, and the bridge range;
     - in Kentucky: girder_viaduct to arc0 460, then blind-arcade walls with fill (wall_embankment) from 460 through the station outline, through-girder street spans (ub 1.5), and embankment at 1:1.5;
     - the covered way on RER C;
     - Covington Union as a station with two island platforms (304.8 × 7.0 m, 1.0 m over the rail), and its canopies and building as station_elements;
     - 7 Kentucky streets as context_feature, with Ben's levels and `lower` (Pike-Russell 0.468 m, W 8th 0.082 m);
     - earthworks for the Embankment, the trough cut and the made ground.
   - **Levels.** `RT` rail follows the Mill Creek Deck's C&O pair (144.6 to 148.2 in the trough, the climb to 160.3) and then the 165.3 ruling. `KY` rail follows Ben's Cincinnati-Covington KMZ line. Both are written as a comparison array (`attrs.reference_rail`) and a check job, not as PVIs. PVIs go in only if Ben rules these levels canon.
   - **Ground.** TER and RIV are not imported, because map 3 holds them. A test compares them to `region.ground` within 0.1 m.
   - **Facts.** The facts-table rows become `facts[]` with ruling or param refs. This meets slice 0's exit: "the bridges reproduce the page's facts table from records".
2. **W.**
   - E0 711716 and N0 4336277 are explicit in `DATA`.
   - bandE, bandJ, bandW and bandN, and the curves (spur, red1, red2), become structures with bents and spans. The Western Hills masonry (`wh`, 65 spans) becomes its own structure.
   - The masonry gets open dates 1913-1920. The 1933 and today elements get theirs (1933; the APEx phase).
   - `cl.ur` and `cl.lr` become checks against the APEx, RER D and R5 profiles.
   - PB 138 (a fixed pier bottom) becomes "to ground − 2 m".
3. **A.**
   - The frame is straightened: x along the viaduct and z across, with D0 60 and D1 660. The importer maps x to c on the north arch viaduct's host section, matching D0-D1 against the Deck chainage, with offsets per track.
   - `edges` become the structure's edge table, openings become street refs, and the block states become `blocks[]`.
   - `railAt = ground + 7.4` is dropped. It becomes the check "headroom ≥ 7.4 − deck depth".
4. **MB and MT.** Params only: the literals listed in 3.2 and EQPOS.
   - Two disagreements go to Ben as open rulings:
     - The signal side. The box page puts the signal on the outer wall, with the trip stop by the inner rail. The handoff (`Metro_Structure_Gauge_Handoff.md`, section 3, item 5) puts the signal on the same side as the trip stop.
     - Signal heights: 2.45 (A), 3.05 (C) and 2.6 m (bore) in MT, against 2.4 in MB and the handoff.
   - Fixes applied in the params: the type C cross passage moves to the walkway side and cuts the linings; the car floor and roof follow `car`.
5. **ST and the hub snapshot.**
   - Context items from `context3d.py` and `hub/work/snapshot.json`: 27 structs, 42 spans, 206 piers, 20 arcade runs, 53 blind arches, 50 masts, 18 platforms (and 159 rail runs). They become structure records with footprints.
   - `snap.struct` becomes params, which removes the structure sizes duplicated in four places (scrutiny section 4).
6. **MS.** Nothing is imported. The SVG is the drawing reference for the section pane, which draws from the same tunnel profiles.

### 3.5 The 6 Nov rulings in records

1. **North of Northside.** RER B follows the north arch viaduct's deck.
   - The record "North arch viaduct" (form arcade_viaduct) lists RER B in `carries[]` over that range.
   - `level_from` is the deck's governing trunk.
   - The engine raises a constraint flag `structure.rail_mismatch` when RER B's rail departs from the deck rail by more than 0.05 m. The line sheet shows the deck as a fixed band.
   - The old straight grade goes.
2. **South of Camp Washington.** RER B leaves on its own `structure`, form ramp_viaduct (girder_viaduct by default), from the leave point to a `portal`, then runs in a tunnel to the junction with RER A.
   - The importer splits ST's arch-viaduct footprint where RER B's trough runs inside it.
   - ST shows the fault today: the viaduct's solid stands over the RER B trough (rail 151.64 m at "Straight"), roughly 13 m above its rails (`st3d_09`).
3. **The C&O and intercity viaduct.** Same rule: walls below the track, enforced by `struct.walls_below_track` above.
4. **Coverage.** An invariant test runs the rule over every structure, every carried and crossing section, and every era.

---

## 4. How it plugs into the hub

### 4.1 App plugins and shared code

**`app/src/plugins/view3d/`** is the 3D pane.

```ts
export default {
  id: "view3d",
  panes: [{ id: "view3d", title: "3D", accepts: sel => sel.kind in GEOMETRIC_KINDS, mount }],
  commands: [presets, cut, exaggeration, mode (Model/Diagram), seeThrough, labels],
  urlParams: [{ key: "cam" /* E,N,z,az,el,dist */ }, { key: "k" }, { key: "cut" }, { key: "m3" /* mode */ }],
} satisfies Plugin;
```

**`app/src/plugins/station/`** is the station workspace (2.5.4). It has three panes over one station selection:
- a plan per level;
- a section, drawn from the same tunnel and station profiles as MS;
- 3D: the same scene module scoped to the station, with the level filter and the spread-levels presets.

**Shared modules in `app/src/three/`:**

| Module | Does |
|---|---|
| `scene.ts` | renderer, render on demand, log depth |
| `look.ts` | builds materials from `look.*` params. A palette edit needs no rebuild. |
| `load.ts` | GLTFLoader plus meshopt |
| `exag.ts` | the exaggeration shader chunk |
| `cut.ts` | clipping planes and stencil caps |
| `labels.ts` | the label overlay |
| `pick.ts` | picking |
| `presets.ts` | camera presets |

three.js is bundled from npm: the current release, ESM, with addons. There is no CDN.
- The seven structure pages load r128 from cdnjs and jsdelivr, and ST loads r147 from jsdelivr. Both use `examples/js`, which was removed in r148.
- The old hub serves r147 from `hub/static/vendor` by rewriting the CDN URLs (`hub.py` `VENDOR`).
- The app's `check:size` budget covers three.

### 4.2 Geometry: a server GLB per section, the worker for drafts

- **Server.** Job type `glb.section` (already listed in architecture section 6). It runs in the `engine` host and calls `mesh.*`.
  - **Scope:** one section chunk of about 500 m of chainage, one structure, one bridge, or one station.
  - **Key:** `in` holds the structure and section record hashes, the `vertical.rail` output_hash, the `param:look.*` and `param:metro_structure.*` values, the ground tile hashes, and `engine_build`. The axes are year and timeline only where the ground is in the GLB.
  - **Output:** a content-addressed GLB blob in `var/cache/blobs/` (9.18), served with ETag and Range by a new blob route (to add; today only `/api/v1/data/{tier}/{path}` serves files, `region/api/files.py`).
  - **Invalidation:** a PVI edit invalidates only the chunks whose rail changed. The result event carries the `changed` chainage ranges, and the pane refetches only those GLBs (scrutiny: "fetch only changed GLBs").
- **Index endpoint.** `/api/v1/view3d/index?bbox&layer&year&lod` lists `{scope, bbox, lod, hash}`, so the pane loads only what is in view.
- **Worker.** While Ben drags a PVI or edits a structure field, the app's engine worker runs the same `mesh.*` on the draft input and swaps the touched chunk within 100 ms. The server GLB replaces it when SSE confirms the save.
- **GLB contents:**
  - one primitive per material id;
  - `EXT_mesh_gpu_instancing` for piers, columns, sleepers, ring joints, equipment and portals;
  - attributes `_EL` (element index) and `_G` (local ground);
  - extras holding the element table (record id, sub-path, open, close, c0, c1) and the node origin in float64.

### 4.3 Levels of detail

| LOD | Distance | Content |
|---|---|---|
| L0 massing | over 2 km, and Whole region | decks as slabs, piers as boxes, tubes as 16-gons, boxes as rectangles, bridges as chord envelopes. Built for the whole region at start. This is ST's look. |
| L1 structure | 300 m to 2 km | all members, piers, arches, towers and walls; no ornament or equipment; rails as lines |
| L2 detail | under 300 m | ornament (ring bands, keystones, dentils, shopfronts, fluting); rails and sleepers; equipment within 500 m (ST `EQ_R`, only when the camera is within 1800 m, `EQ_ZOOM`); the arcade within 450 m (`ARC_R`); ring joints within 50 m |

**Budgets**, as warn-only tests (`tests/perf`):
- under 300 draw calls;
- under 3 M visible triangles;
- 0 fps at idle;
- first frame of a station view under 2 s on Ben's machine.

The pages measured (headless Chromium on SwiftShader):

| Page | Triangles | Draw calls |
|---|---|---|
| R | 2.39 M | 34 |
| C | 704k | 17 |
| S | 280k | 15 |
| W | 745k (660k drawn in the default view) | 77 meshes, 42 calls in the default view |
| A | 219k | 29 |
| MT (type A) | 414k | 151 |
| MB | 18k | 128 |
| ST | 3.48 M rendered (drafting harness, not re-measured) | 156 |

### 4.4 Exaggeration in the vertex shader

- **Where.** `onBeforeCompile` on every material, including the depth and shadow materials.
- **Shader.** `transformed.y = _G + (transformed.y - _G) * uK;`. The normal's y is divided by uK and renormalised.
- **CPU side.** Labels, picking and camera targets apply the same transform.
- **No rebuild.** ST disposes and rebuilds the whole scene for each slider step (after a 200 ms debounce).
- **Clipping** is evaluated after the transform.

### 4.5 The era slider

- **What it reads.** The view's year and month (URL `year`, `tl`).
- **Each element** carries open and close months in the GLB element table. A per-instance or per-vertex `_ERA` attribute plus a uniform `uInstant` lets the shader discard whatever is not open.
- **Moving the slider** needs no rebuild. W's 1933/today toggle (which shows and hides groups) becomes the general case.
- **Ground** differs by year, so ground tiles are keyed by year and timeline.
- **An undated record** shows only at the present (9.16).

### 4.6 Picking and selection

- **Picking.** A raycast on the settled frame, with a BVH per GLB (three-mesh-bvh). It reads `_EL` and returns `{rec, path}`, for example `structure:01K…` with `/piers/3`.
- **Selection** goes to the host (`sel=` in the URL). The inspector opens the record at that sub-path, and the line sheet jumps to its chainage.
- **Selecting in another pane** outlines that record's meshes in 3D.
- **Double-click** recentres (ST). A flag in the issues pane flies the camera to its chainage.

---

## 5. Verification

1. **Reference screenshots** are the visual target. They live in `design/3d_artifacts/reference/<page>/<view>.png` (list below), with a `poses.json` per page holding the eye, target, fov, viewport and harness settings.
   - All were made with headless Chromium on SwiftShader, at deviceScaleFactor 1.
   - three r128 and r147 came from `npm pack`, because the CDNs were blocked.
   - Google Fonts was aborted, so fallback fonts show.
   - They should be re-shot once on Ben's machine, with the real fonts, if he wants exact text.
2. **Side-by-side parity per component.** This is the line sheet's rule (2.1.5): every difference is classed as same, rule fix with an id, or unexplained, and there must be zero unexplained before a component is done. Each check has three parts:
   - The hub renders the component from records at the reference pose, in the page's frame converted to 26916, with the same light preset.
   - A Playwright test writes a side-by-side image and an SSIM score. SSIM is warn-only; the classing is the gate.
   - Numeric parity against the page's own numbers, within 1 mm:
     - C&O: L 473.46; spans 129.8, 208.9 and 134.8; rail 165.3; hinge 158.3.
     - CS: L 402.23; hinges 155.0; crown 239.6; rail 164.0.
     - Box: inside 7.9, top 4.6.
     - Tubes: A 5.1 and 5.5; C 5.4 and 5.9.
     - Arcade: bays 16.5 to 19.3; headroom.
   - Known page faults are classed "rule fix" with an id. They are not copied:
     - the CS Ohio approach in the air;
     - flat decals;
     - the cross passages (wrong side for type C, no openings for either type);
     - the train heights;
     - the truss NaN (ST copy only);
     - labels showing through walls.
3. **Unit tests** (vitest, `engine/test/mesh/`):
   - **Counts.** C&O panels per rib 13 + 22 + 13, on 3 ribs. CS 32 panels on 2 planes. Box columns: 164 over 250 m (MB, from 0.76 m at 1.524 m pitch). Ring joints by pitch.
   - **Bounds.** For example, the CS crown at hinge + rise to 1 mm, and a box from rail − 1.0 to rail + 4.6.
   - **Watertight.** Every edge is shared by exactly two triangles. This applies to every solid that a clip plane may cut: boxes, tube shells, piers, decks, walls and towers. Stencil caps need it.
   - **Normals** point outward.
   - **No NaN.**
   - **Determinism.** The same input gives a byte-identical GLB twice.
   - **Triangle budget** per component.
   - **Placement.** A sweep on a curved path keeps the profile normal to the plan tangent.
4. **Model invariants.**
   - `struct.walls_below_track` runs over every line and era.
   - Every structure's carried section exists and covers c0 to c1.
   - Every bridge's carried rail at the abutments matches the approach structure.
5. **App e2e.**
   - The 3D pane loads offline.
   - A PVI edit moves the box within 1 s.
   - Picking a pier selects its structure.
   - The era slider hides the APEx upper deck at 1933.

---

## 6. Order of work

The current order is kept: increment 2 starts with I2.1 (closing the loop to run times), then I2.2 (engine ports), I2.3 and I2.4. The 3D work fits into the existing slices as follows.

| When | 3D work |
|---|---|
| **Step 0, after the I2.1 gate.** Small; it proves the path and blocks nothing. | **The box section from records.** Draw the Line 1 cut-and-cover ranges as `boxSection`. It needs no new kind: it uses the section path, the `profile.ovr` cutcover ranges, the solved `rail_m` from `profiles.solve_section`, and the existing `metro_structure.box.*` params. Pieces: `engine/src/mesh/` with `pathFrame`, `sweep`, `boxSection`, `instances` and `toGlb`; the job `glb.section`; the `view3d` pane with the `look` params, presets and picking. **Gate:** the poses of `mbox_v-section.png` and `mbox_v-over.png` match by class; a Line 1 PVI edit moves the box in the pane over SSE; picking the box selects the profile's ovr range. |
| Step 1, with 2.0.12 and 2.0.13 (architecture section 11, step 5) | Kinds `structure` and `bridge`, and `track` v2. The `artifacts_3d` importer for R. One Parker side span from the C&O `bridge` record as the first bridge component, then the whole C&O and CS bridges. The facts tables from records (slice 0 exit). The `struct.walls_below_track` rule, and the north arch viaduct and ramp viaduct records per the 6 Nov ruling. |
| Slice 1 (2.1.x) | Tube types A, C and bore from `profile.tf` and phases. The equipment kit from params. The section pane for the line sheet's section view. |
| Slice 3 (2.3.4, 2.3.3) | Structures region-wide: girder, bent and masonry viaducts (W), the arcade (A), trough, embankment and portals. The era slider in 3D. Earthworks drawn on the map and seen in 3D. LOD L0 for the whole region. |
| Slice 5 (2.5.1, 2.5.4, 2.5.5, 2.5.6) | `station_element`, `platform` v2, the station workspace (plan per level, section, 3D), stencil caps, the spread-levels presets, and exports (PNG, glTF). The old 3D page retired. |
| Slice 7 (2.7.1, 2.7.2) | glTF and KMZ export with structures; performance budgets as tests. |

### Open rulings for Ben

1. Signal side: the outer wall (box page) or the trip-stop side (handoff section 3, item 5).
2. C&O steel colour (grey is marked "not ruled").
3. Are R's `RT` and `KY` levels canon for the C&O pairs and the Covington line, or only a reference?
4. ~~The default mode for the region view.~~ Ruled by Ben, 23 Nov 2026: **Model** is the default. The tunnels are already diagrammed; stations get the same treatment (their own Diagram drawings), so Diagram stays a mode, not the default.
5. The host section and chainage basis for the arcade's straightened frame.
6. Buildings and the city around the lines: the open questions in 7.12.

---

## 7. The city around the lines

Every building in the 3D city is one record of a new kind, `building`. That holds for a building that stands today, one that was demolished, and one of Ben's proposals. Only the inputs differ by provenance. Every value of every building can be changed by Ben in his own layers. One pure engine method, `mesh.building@1`, turns any record into Model-look geometry, and it re-meshes one building at a time. A second kind, `building_style`, holds the style catalogue. A third, `site`, clears an area for a year and a timeline. This section replaces the `lotMass` row in 2.7 and proposes to close checklist 2.3.11 (lean (c), one record for the map and for 3D, now with roofs), for Ben to rule.

Status: **proposed, not ruled**, except the rulings in 7.1. **On hold** until the rest of the hub is complete (Ben, 24 Nov 2026). Values marked *drawing value* are starting numbers for Ben to rule on. Facts marked *unconfirmed* have not been checked against their source.

### 7.1 Ben's rulings

**23 Nov 2026**
1. **No Google and no Apple data.**
   - So: no Photorealistic 3D Tiles, no Street View, no Google Open Buildings.
   - Overture buildings are left out too, because Overture merges Google Open Buildings in places.
   - `tools/overture_extract.py` already uses Overture for rail and water. Those themes are to be checked for Google-derived sources.
2. **The Model look only.** There is no image-model or illustrated layer. Lost and proposed buildings come out of the same generator and palette as real ones (1.3).
3. **Real buildings get roof shapes from lidar.**
4. **The whole metro is the end goal.** Start downtown.
5. **Large data lives on Ben's machine**, not in git.
6. **A method for buildings that are not in the real world:** the demolished West End, new buildings on downtown parking lots, and the like.

**24 Nov 2026**, in Ben's words: "The buildings should be able to be modified (height, footprint, type (residential, commercial, industrial), architectural style (based on age, material, etc.), and other things)".

What this means here:
- **Every building is editable**, real ones included.
- **A measured building keeps its lidar solid** until Ben changes something the measured solid cannot show (7.6, step 2). It is then drawn by the generator from its parameters. The measured original stays underneath, in the import layer, and one action brings it back.
- **Edits live in Ben's layers** (main or a scenario), never in import layers. They follow the hub's rules: copy-up versions, the three-way rebase that never overrides Ben (Architecture 9.11), drafts with undo, Enter saves.
- **Always live.** A building edit re-meshes only that building, within the budgets in 7.9. No edit reruns lidar, roofer or a district job.
- **Style is a first-class parameter set** (7.5): a catalogue whose defaults follow from era, material and use, which Ben can override per building.
- **Type is the building's use:** residential, commercial, industrial, mixed, civic (and institutional), religious, transport, parking, other.
- **"Other things"** include at least: stories and floor heights, roof form and pitch, setbacks, podium and tower, material and colour, ground-floor shopfront, year built and demolished, name and address, notes, and provenance.
- **Every value shows its source** in the app, as the line sheet's station panel does.

### 7.2 What the repository holds today

Corrections to earlier notes. Question 1 in 7.12 follows from them.
- **There is no 1912 Sanborn** in the repo or in `data/sanborn/manifest.json`. The repo's "1912" is the City Topographic Survey (`ground/1912/`), which gives ground levels, not buildings.
- **1904.**
  - 381 frames (365 sheets) of vols. 1-6 are placed (`hub/sites/deck/sheets.json`). Some sheets are split panels (13a and 13b, 161i and 161m), and 223 and 224 appear twice.
  - The joint fit (Relief_Maps_Log 10n.4) covers 154 sheets of vols. 1-3 in 161 frames. Its residuals: ties median 0.63 m (p90 1.8), OSM corners median 1.05 m (p90 3.4), frame medians up to 3.9 m.
  - The deck frames (vols. 1, 3, 5 and 6) and 223 and 224 were refitted in 10t.6-10t.7, with the Lower Price Hill spline in 10t.8.
  - Vols. 4-6 and the rest of vol. 2 were placed later by other fits (10t, 10zzb, 10zzq), and the Northside frames were bent onto the 1922 splines in 10zzy.16. Their accuracy is not restated here.
  - Vol. 2 carries later paste-overs: 1920s buildings and Central Parkway (10n.2).
- **1922.**
  - Five frames are tiled (16R, 34L, 34R, 37L, 37R), all north of N 4,333,500. They were refitted by thin-plate spline in 10zzy.16 (`data/sanborn/cuf_cw/<half>/model.npz`). Plates 35N and 38 are also on the 1922 layer (`tools/sanborn/cuf/plates.py`).
  - Affine fits from October exist for vol. 1 halves 3, 6, 26 and 29 (10t.4, `data/sanborn/lph/tf22_aff.json`) and 31 and 33L (10u.4, `lph/tf22_cw.json`). They are not tiled and predate the thin-plate rule (`docs/sanborn/RULES.md` rule 12). 16L and 35L have splines (10zzy.16) but are not on the layer.
  - The guided plates are 43, 44, 45, 80 and 82A, all north of N 4,336,600. Plate 44 is Northside and Cumminsville.
- **The West End.**
  - A box E 713,000-714,300 / N 4,331,300-4,332,800 holds 286 blocks (by centroid, `hub/sites/deck/basin.json`), all from the 1904 Sanborn, on 41 frames (27 of vol. 1, 14 of vol. 3). It holds no 1922 block.
  - Of the 1922 vol. 1 sheets that reach the Mill Creek side (10k.1: 3, 6, 9, 16, 29, 31, 33), 16R is tiled, 16L has a spline, and 3, 6, 29, 31 and 33L have affine fits (10t.4, 10u.4). Sheet 9 has picks only (10t.3). All of them must be fitted by spline (rule 12) and tiled before 1904-1922 linking can run there.
- **No building outlines, stories or materials have been read off any Sanborn yet.**
  - The 1904 label readers were told to skip construction codes, on grey crops at 4 px/m (`docs/sanborn/workspace_notes/plots/labels/INSTRUCTIONS.md`).
  - Ben rejected the generated lots on 15 Oct (10zg.4).
  - So the lost-building path below is a new trace-and-read pass, checked sheet by sheet.
- **Nothing for buildings exists in code**: no kind, no params, no mesh code, no tiers for lidar, footprints or models.

### 7.3 Sources per provenance

`origin.source` takes one of four values. Each has its own inputs and its own import layer or authoring path.

**measured (standing today)**
- **Footprints.** `tools/buildings/cagis_fetch.py`, modelled on `tools/sanborn/guided/parcels.py`.
  - It pages the CAGIS / City of Cincinnati building-footprint layer per 1 km cell (`inSR`/`outSR` 26916). *Unconfirmed:* about 300,000 footprints with estimated heights and stories, mostly from 2011 imagery.
  - It keeps the stable id, estimated height, stories, survey year, and name and address where the layer has them.
  - *Unconfirmed:* the service URL (`parcels.py` only knows `COUNTYWIDE/Cadastral/MapServer/0`), the field names, whether ids are stable across releases, and the terms.
  - It writes tier `bldg_footprints`: GeoJSONSeq per cell (no new dependency; FlatGeobuf would need pyogrio), `MANIFEST.csv` with sha256, and `STATUS.json`, the same handshake as tier `ground_1912_real` (`ground/1912/rebuild/manifest.py`, `status.py`; declared in `configs/hub_paths.json`).
- **Parcels.** `tools/buildings/parcels_fetch.py` pages CAGIS `COUNTYWIDE/Cadastral/MapServer/0` per 1 km cell, as `tools/sanborn/guided/parcels.py` does per plate, into tier `parcels` (same handshake). Parcels carry the auditor join (dates, land use), the Sites list and parcel snapping. *Unconfirmed:* which auditor fields the layer or a second service carries.
  - Importer `buildings_real@1` writes `import:bldg_real` with `method: cagis_extrude` until the cell has lidar. This gives downtown LoD1 blocks early.
- **Lidar.** `tools/buildings/lidar/` holds `fetch.py`, `pdal_cell.json` and `run_cells.py`. It is lane B tooling, like `ground/1912/rebuild/`.
  - Check Ben's own data first: he already holds USGS DEMs and LiDAR (checklist 2.0.14), and `ground/2026` is what the works ledger calls "today's LiDAR". Whether either is a classified point cloud recent enough for roofs is *unconfirmed*.
  - Otherwise, USGS 3DEP for Ohio (project name, years and coverage *unconfirmed*; public domain). Prefer PDAL `readers.ept` on the USGS public EPT bucket per cell, if the project is there (*unconfirmed*), over storing LAZ.
  - Before B2, `fetch.py --survey` prints the class histogram, CRS, vertical units and geoid of one tile per cell. The CRS and units (possibly State Plane feet) are *unconfirmed*.
  - PDAL reprojects to EPSG:26916 and NAVD88. The geoid step is applied once and recorded in the manifest. It writes a 0.5 m DTM COG, used for checks only (7.8).
  - The USGS base specification does not require class 6. If a project has no class 6, building points are class 1 points inside the buffered footprint, at least 2 m above the DTM, with a planarity filter for trees.
- **Matching 2011 footprints to 2020-23 points.** Footprints from 2011 orthos lean on tall buildings, and rows may be one merged polygon.
  - Per footprint, `run_cells.py` first fits a 2D shift that best covers the building points and records it in `measured.shift_m`.
  - The shift is never written to the geometry, so it never conflicts with Ben's revisions (7.4, "Merge"). `bldg.resolve` draws the CAGIS footprint moved by the shift, unless Ben set a footprint.
  - A shift over 1.5 m is a Review item.
  - A footprint with several roof-height clusters along party lines is flagged "merged row?" for a split.
- **Roofs.** roofer runs per cell as an external CLI and writes CityJSONSeq LoD1.2, 1.3 and 2.2, with per-building stats (h_50p, h_70p, RMSE, point count).
  - roofer runs in WSL2 or Docker. `run_cells.py` translates tier roots (`C:\…` to `/mnt/c/…`) and records the roofer version and container digest in `MANIFEST.csv`. PDAL comes from conda-forge on Windows.
  - *Unconfirmed:* roofer's licence.
  - The live hub watches `STATUS.json` and re-imports changed cells (9.31). Their records gain a `measured.solid` and flip to `method: cagis_lidar_roofer`.
  - If roofer fails on a building, it falls back to LoD1.2 from h_70p with a flat roof, plus a Review item.
- **Change since 2011.** The same run raises Review items. None of them acts by itself. They are off until class 6, or the substitute above, is validated on the pilot.
  - A footprint with almost no building points: "gone since 2011?".
  - A building-point cluster over 30 m² outside every footprint: a candidate footprint (alpha shape, then rectangle regularisation), `method: lidar_new`.
  - CAGIS and lidar heights more than 3 m apart. The lidar height wins.
- **Dates.** The Hamilton County Auditor's year built per parcel, joined through the parcel (*unconfirmed* as a public field).
  - The auditor's year is often a placeholder for old buildings, such as a blanket 1900.
  - Where a Sanborn match says "standing by 1904", the Sanborn date wins, and `date_basis` says why.
- **Outside Hamilton County** (metro growth):
  - each county's own footprints (Boone, Kenton, Campbell, Butler, Warren, Clermont), or else footprints from building points;
  - OSM (on Ben's disk) or Microsoft footprints only if Ben allows them (7.12);
  - Kentucky lidar from KyFromAbove, not 3DEP Ohio.
- **CAGIS geometry stays out of git** until its terms are checked (B0a gate, 7.11). Git holds ids and aliases only. See 7.4, "Seeds".

**historic (lost buildings, the West End first)**
- **Editions:** 1904 and 1922 (7.2). In the West End only 1904 is placed today.
- **Footprints.** `tools/sanborn/bldg/trace.py`.
  - It segments the building fills by colour at the scan's native resolution, with a colour calibration per sheet against the legend and against known samples. Aged paper and yellow frame fills are close in tone.
  - It splits the fills along the skeleton of the outline ink, so party walls become shared edges. Polygons come from the fill regions, not from the outline ink.
  - `tools/sanborn/unet/ink_bins.py` cannot be reused as it stands. It is a 1922-plate tool whose inputs (a street map, a placed plate's label, or the `blocks_noguide.py` outlines) do not exist for 1904 sheets. It finds only pink and yellow fills, and a party wall between two brick houses falls in its bin 3 (building outline), not bin 2 (lot line).
  - It places the polygons through the existing frame fits: the 1904 fits (10n.4, 10t.6-10t.7, the Lower Price Hill spline `lph/tps.pkl` of 10t.8, 10zzb, 10zzq and the 10zzy.16 bends) and the 1922 splines (10zzy.16 for the tiled halves, rule 12 for the guided plates). A 1922 sheet with only an affine fit is refitted by spline first.
  - Traces are clipped to their `basin.json` block. Duplicates across sheet overlaps are removed by the 10n.9 "deepest frame" rule.
  - Ink is traced, never generated. That is the lesson of 10zg.4.
  - Ben's plate 44 ground truth (`data/sanborn/streetmap/22-44.json`, `picks22_guided/22-44/edges_ben.json`, `rail_ben.json`) holds his 55 blocks, street sides and rail, not building outlines. It tests block clipping, not footprints.
  - The first footprint gate is a new hand-checked set: a few blocks outlined twice, independently, on plate 44 and on one 1904 sheet, and accepted by Ben. The 99.3% building-outline figure in `ink_bins.py` compares two binnings, and is not a footprint accuracy.
- **Material** comes from the fill colour, read against each edition's legend sheet (*to check against the legend*): pink brick, yellow frame, blue stone, brown fireproof, grey iron.
- **Stories and codes.** A new reader pass, `docs/sanborn/workspace_notes/bldg/INSTRUCTIONS.md`, reads exactly what the label readers were told to skip.
  - It works on native-resolution colour crops, 60 m square: 1904 CHPL about 11.4 px/m and LOC about 20 px/m; 1922 plates 5.2 px/m (200 ft to the inch) or 10.2 px/m (100 ft) (10t.4).
  - What it reads: the stories numerals (1, 2, 2½, 3), D (dwelling), S (store), F (flat), B (basement), named uses (Ch., Sch., Wareho., Mfg., Saloon), skylights and roof notes.
  - Each reading is assigned to the polygon under it. Two independent reads per building must agree, as `docs/sanborn/RULES.md` rule 12 asks of hand picks.
  - Each sheet then becomes one Review item, with the crop under the outlines. Nothing counts as checked until Ben accepts the sheet.
  - Roof form is not printed on a Sanborn. A historic roof is `inferred` from style and half-stories unless a photo fixes it.
- **Output:** small vectors in git under `data/sanborn/buildings/<edition>/<sheet>.geojson`. Importer `buildings_sanborn@1` writes `import:bldg_sanborn`.
- **Linking.**
  - Within each block, the traces are first aligned rigidly to the CAGIS footprints of surviving buildings (ICP), and lost neighbours move with them. Control in the West End is weak: the joint fit used 167 corners of demolished streets from the 1912 layer at sigma 6 m (10n.4), and that layer was itself off OSM by up to 4.5 m before a per-sheet correction left 2.3-2.7 m MAD (10m.4).
  - Then IoU of at least 0.6, or a Hausdorff distance under 2 m, proposes `same_as` in Review, and Ben confirms. One merged CAGIS row can match several Sanborn houses.
  - 1904 to 1922: a match with the same stories makes one record with a longer life. Otherwise the 1904 record closes `circa` between the editions and a new one opens.
  - This makes each OTR survivor one object across eras, so it is not drawn twice.
- **Photos** are public-domain library collections Ben clears, or his own. They attach as `evidence` to fix stories, roofs and cornices. No photo goes into the look.
- **Lots.** `hub/sites/deck/plots.json` is not used for footprints, because Ben rejected it. Its use labels (`u0`) may help choose a use.

**proposed (Ben's designs)**
- Authored `building` records in main, a scenario or a proposal layer. Most start from a use and a style and are fitted into an `envelope` (7.4).
- **Candidate parking sites.** Job `bldg.sites@1` lists surface-parking parcels, from the auditor land-use codes (*unconfirmed*) plus paved parcels with no building points. It is a pick list and never builds anything.
- **From `import:deck`** (Architecture 11, item 7):
  - Only the palace and the Deck's building blocks come in, as canon `envelope`s (timeline canon, opened by 1913) carrying their block type as a use and style hint. deck.json has 274 blocks of type building today. Ben's block types from `hub/seed/deck/layout.json` come with them: today 3 landmark and 1 worship among 56 block edits; the page also offers tower, civic, school, hospital and industrial (`BLOCK_TYPES`).
  - Station buildings stay `station_element`s with element `building` (3.3): the Deck's `cut_building` (Union Terminal) and `cut_headhouse`, the Norwood station building and the airport terminals.

**model (hand-made landmarks)**
- A glTF or GLB file that Ben saves in the read-only tier `models3d`. The record holds `tier://models3d/<file>` and its sha256. The hub never writes a tier.
- The record keeps its parametric fields as the fallback when the tier is missing, for example in a cloud session.
- Materials are mapped onto `look.materials` slots and drawn as Lambert. The model's own colours and textures are dropped, so landmarks keep the Model look.
- A `model` record behaves as a measured solid (7.6, step 2). Identity, use, dates and slot colours edit live. A massing edit switches it to the generator, and **Back to model** is the one action that restores it.

### 7.4 Records

New feature folder **`region/ext/buildings/`**: `__init__.py`, `kinds/`, `importers.py`, `sources.py`, `validators.py` and `jobs.py` (the layout of `region/ext/terrain/` and `region/ext/profiles/`), plus `styles/` and `rules/`.
- It sits beside the planned `region/ext/structures/` (3.3), which holds the rail structures, station elements, earthworks and context features. A station's own building stays a `station_element`.
- All plan geometry is EPSG:26916, and every level is relative (3.1 rule 1).

#### How a value is set, and where its source comes from

- **Two kinds of field.**
  - *Import blocks* (`measured`, `read`, `attrs`, `origin`, `confidence`) are written only by import runs. Ben never edits them. Authored records write their own `origin` and `confidence`.
  - *Ben's fields* (everything else, except geometry) are null in an import revision. A value there is Ben's (or the author's, for a proposal). Null means "follow the sources".
  - Ben's fields that are objects (`floor_h_m`, `roof`, `colour`, `facade`) are partial: each key resolves on its own, and a null key means "follow the sources" for that key.
  - `checked {by, date} | null` is a top-level field of Ben's. Accept sets it. Authored records set it to their author on creation.
  - `evidence[]` is Ben's. Import evidence lives in `measured.evidence[]` and `read.evidence[]`. The card shows the union.
  - So an Accept, or a photo Ben adds, never collides with the next import run at the merge unit.
  - Geometry is written by the import. Ben's footprint is his revision's geometry where it differs from the import revision below.
- **Resolution order, per value:** Ben's field (or the author's), then lidar, then CAGIS and the auditor, then `read` (Sanborn), then the envelope (proposed buildings), then the Deck hint, then the style, then the use, then the global param. The seed varies a value only inside the style's `vary` range, and never a value Ben set.
- **The resolver** returns each value with its source: `{v, src, ref, rule}`, where src is one of ben, author, lidar, cagis, auditor, sanborn, envelope, deck, style, use, rule, param or seed. For ben and author, the changeset's `by` and date are shown.
  - The values and sources of one building are the engine method `bldg.values@1` (pure TS, in `engine/src/mesh/`). It reads the record, the import revision below, the styles in use and `style_defaults.yaml`.
  - The app worker runs it for drafts, so a keystroke never waits on the server.
  - The cell job `bldg.resolve@1` (7.8) calls the same method through the engine sidecar, and adds what needs neighbours and sites: dates, derived closes, edges and the element table. One implementation, so the draft and the saved building cannot drift apart.
- **The card shows it** as the line sheet's station panel does (`app/src/plugins/line-sheet/panel.ts`): label, value, the source in words with a rule chip, and a "was" note while a draft differs. A value Ben set carries a reset mark. Examples:
  - "18.4 m, lidar 2022 (h_70p, RMSE 0.21 m)";
  - "4 stories, Sanborn 1904 vol. 1 sheet 27, read";
  - "Italianate rowhouse, from era, material and use (rule bldg.style.default)";
  - "3.4 m, Italianate rowhouse default";
  - "6 stories, Ben, 24 Nov 2026".
- **Merge.** The merge unit is the field (Architecture 9.11).
  - A re-import that changes only import blocks or fields Ben did not set merges as a `rebase` changeset.
  - A change to a field he set is a Review conflict. His revision stays on read.
  - Any footprint change below one of his revisions is a conflict (9.11), even where his revision kept the import's footprint (a rename, a restyle, a Reset all). A CAGIS re-release would flood Review that way. So Review groups these per cell, with one action, "Take the new footprints where you kept the old one", which writes one changeset.
  - `parts[]` is keyed by `id`, as `structure` sub-arrays are (3.3).

#### `building` (geometry Polygon or MultiPolygon in 26916, the footprint at ground; `dates: open /opened, close /closed, timeline /timeline`; merge unit `field`, rebase auto)

| Field | Values | How Ben edits it | Source when Ben has not set it |
|---|---|---|---|
| geometry | the footprint | drag vertices on the map; add or remove a vertex; draw | CAGIS, `lidar_new` or a Sanborn trace |
| name, address | text; address may be a list | type | `measured` (CAGIS, auditor; *unconfirmed*) or `read` (Sanborn names and house numbers) |
| notes | text | type | none |
| use | `residential \| commercial \| industrial \| mixed \| civic \| religious \| transport \| parking \| other` | pick | Sanborn codes, auditor land use, the Deck use (below), else `other` |
| use_detail | text: school, hospital, brewery, saloon, station | type | as read |
| style | a `building_style` slug | pick from the catalogue (7.5) | rule `bldg.style.default` from era, material, use, stories and plan |
| opened, closed | partial dates: year built and year demolished, with `opened_q`, `closed_q` (`exact \| before \| after \| circa \| assumed`) and `date_basis` | type, or "Set to view year" | Sanborn presence, auditor year built, a site, `replaces` (7.8) |
| timeline | `canon \| real \| null` (null is both, as `region/ext/rules/kinds/era.yaml`) | pick | null, or the redevelopment rule (7.8) |
| stories | number, halves allowed (2.5) | type, Up and Down; or drag in 3D | CAGIS stories, lidar height over floor heights, Sanborn numeral, style |
| basement | bool | tick | Sanborn B, else style |
| floor_h_m | `{ground, upper}` | type | style, then `bldg.floor_h.*` |
| height_m | wall top above the base (eave or parapet) | type, or drag the top face in 3D | lidar h_70p per part, else stories × floor heights |
| roof | `{form, pitch_deg, ridge_az_deg, overhang_m, parapet_m, dormers}` (the style's roof keys); forms `flat \| parapet \| shed \| gable \| hip \| mansard \| gambrel \| sawtooth \| monitor \| pyramid \| spire \| dome` | pick form; type pitch | the measured solid as drawn; `measured.roof` as the starting values; style |
| parts[] | `{id, ring (null = the footprint), on: ground \| part:<id> \| rec:<structure id>, setback_m, stepbacks[{above_story, depth_m, faces: street \| all}], stories, floor_h_m, height_m, roof, material, use, facade}`; a null `use` or `facade` follows the building | Add tower, Add setback, Add wing; drag in 3D | measured LoD1.3 levels, else one part. The card shows GFA per use |
| material | `brick \| frame \| stone \| iron \| concrete \| steel_glass \| metal \| mixed` | pick | Sanborn fill colour, style |
| colour | `{main, secondary, trim, roof}` (the style's palette slots), each a `look.materials` id or a hex | pick | the style palette, drawn by seed |
| facade | `{grammar, ground: shopfront \| stoop \| blank \| arcade \| lobby \| loading \| open, shopfront_h_m, bay_m, piers, string_courses, base, window {kind, w_m, h_m, hood, sill}, cornice {kind, h_m, proj_m}, ornament 0-3, plan_form, front_edges[]}` (the style's facade keys, 7.5) | pick and type; Shopfront tick | style, then use (commercial gets a shopfront) |
| massing | `auto \| generated` | "Draw from parameters"; "Back to measured" ("Back to model") | auto: the measured solid where one exists and no massing field is set (7.6) |
| seed | integer | Re-roll | from the id hash |
| envelope | an `envelope` id | pick | none |
| origin | `{source: measured \| historic \| proposed \| model, method: cagis_extrude \| cagis_lidar_roofer \| lidar_new \| sanborn_trace \| frontage_fill \| authored \| gltf, ref, run}` | never (import or author) | the import or the author |
| checked | `{by, date} \| null` | Accept sets it | null for imports; the author for authored records |
| confidence | `{footprint, height, roof, material, date, style}`, each `traced \| read \| inferred \| invented` | none: a value Ben sets shows "set by Ben" | the import |
| evidence[] | `{kind: sanborn_1904 \| sanborn_1922 \| photo \| aerial \| auditor \| cagis \| lidar \| other, ref, date, note}` | add, remove | none; import evidence is in `measured.evidence[]` and `read.evidence[]`, and the card shows the union |
| same_as[] | building, `station_element` or `structure` ids: the same physical thing in another source | confirm in Review | linking (7.3) |
| replaces[] | building ids this one succeeds | "Replaces...", then click | none |
| lots[] | lot or parcel refs (a reference, not ownership) | pick | none |
| model | `{file: tier://models3d/<file>, sha256, anchor {E, N, z \| on_ground, az_deg, scale}, mat_map}` | gizmo (7.7 D) | none |
| measured | `{name, address, height_cagis_m, stories, survey_year, year_built, year_built_q, land_use, parcel, eave_m, h_50p, h_70p, rmse_m, n_pts, shift_m, levels[], roof {form, pitch_deg, ridge_az_deg}, solid: tier://bldg_lidar/<cell file>#<id>, cell_sha, evidence[]}`; `year_built` and `land_use` are the auditor's, joined through `parcel` | never (import only) | |
| read | `{edition, sheet, stories, codes[], fill, uses[], names[], crop, evidence[]}` | never (import only) | |
| attrs | raw source fields; `fill_key` for frontage fills | never | |

- **Use from the Deck codes** (`hub/sites/deck/index.html`, USES): r residential, m mixed, c commercial, i industrial, w religious, v civic, s civic (school), l civic (landmark), p parking. k (park) and o (open) are not building uses.
- **One record per building per life.** A rebuild is a new record. The old one gets `closed`, and the new one lists it in `replaces`.
  - **Split at this year** in the card makes an alteration the same way. On historic and proposed buildings the record closes at the view year, and a copy opens then with `replaces` set. Ben then changes the copy (two floors added, a cornice removed).
  - On a measured building the copy is the earlier life instead: it keeps the original `opened` and closes at the view year. The measured record opens at the view year with `replaces` set to the copy. So the present life keeps its CAGIS link, its lidar solid and its re-import merges.
- **A tombstone is only for a wrong trace**, because it hides the record in every year. Demolition is `closed`, `replaces` or a `site`.

#### `building_style` (no geometry; seeded from `region/ext/buildings/styles/<slug>.yaml` by importer `bldg_styles@1`; merge unit `field`, rebase auto)

The style catalogue. Its fields and starter set are in 7.5. Styles are data: a new style is a YAML file, or a record Ben authors. Ben's change to a style is a revision in the view's layer (main or a scenario), as for any record. A YAML update to a style Ben touched merges field by field. Only a new facade grammar needs code.

#### `site` (geometry Polygon; `dates: open /opened, close /closed, timeline /timeline`; merge unit `field`, rebase auto)

- Fields: name, timeline (`canon | real | null`), opened, closed, `mode: clear | keep`, `members[]` (building ids allowed inside), `rule: overlap>=0.5` (default) or `centroid`, `cause: urban_renewal | highway | parking | fire | flood | infill | other`, `redevelopment_timeline: real | null`, reason, evidence[].
- Meaning: from `opened`, the site hides every building that is mostly inside its polygon, opened before the site, and is not a member. Buildings that open later show; they are the redevelopment.
- Sites are for area clearances. A single replacement uses `replaces[]` on the new building (7.8).
- **Seeds**, all `timeline: real`, with dates from Ben (*unconfirmed*): the Kenyon-Barr phases, the I-75 and Mill Creek expressway take, Queensgate, Fort Washington Way, Laurel Homes (about 1938), Lincoln Court (about 1942), and the Union Terminal site and approaches (1929-33).
- **Works as implicit canon sites.** Dated canon works in `ground/works_ledger.json` can act this way. Downtown that means `mill_creek_deck` (by 1913) and `canon_interstates` (1940-1965, per stretch once the tracker's 4A-4D dates exist). The river and Lunken works (`ohio_embankment_1912`, `ohio_embankment_rest`, `ky_terraces`, `lunken_levees`, `lunken_airfield_lift`; 1903-1941) apply where they cover built land.
  - Today those works are rasters. Each needs a vectorised footprint in `ground/zones/works_footprints.geojson`, made once by a lane B script and checked by Ben.
  - `real_works_removed` is not a site. It is land that canon never built highways on (`apply: none`). Its footprints are already vectors: `ground/zones/zones_real_works_canon_removes.geojson` (16 polygons, the `minus` of `real_works_kept`). Measured buildings standing on them (the stadiums, Fort Washington Way) get timeline `real` (7.8).
  - The real timeline's ground after 1912 is only `real_works_kept` (the dated zones of `ground/zones/zones_post1912_works.geojson`, 7.8). It carries no clearance of buildings. So every real clearance is an explicit `site` record.

#### `envelope` (geometry Polygon: the lot union it governs; merge unit `field`, rebase auto)

- Fields: `build_to_m`, `street_wall {min_m, max_m}`, `stepback {above_m, depth_m}`, `max_height_m`, `tower {max_floorplate_m2, min_spacing_m, min_setback_m}`, `far_max`, `ground_floor_active`, `parking: none | podium | wrapped | below`, `use_hint`, `style_hint`, rule ids.
- Presets are params `bldg.envelope.<preset>.*`: `dd_a_core`, `otr_infill`, `west_end_rebuild`, `deck_frontage`. They are Ben's rules, not the zoning code, unless he rules otherwise (7.12).
- An envelope guides; it never clips. A building that breaks its envelope is a Review item, and the card shows GFA and FAR.

#### Validators (`region/ext/buildings/validators.py`)

- `bldg.walls_by_rail`: no building may intersect a structure's solid (the arcade, the viaducts), or the kinematic envelope that 3.3's planned rule `struct.walls_below_track` keeps clear (rail − formation to rail + 5.5 m). A conflict is a Review item, never a silent cut.
- `bldg.envelope` (above).
- `bldg.overlap`: two buildings open in the same year and timeline that overlap by more than 15% is a Review item.
- `bldg.ring`: the ring is valid and has no slivers.
- `bldg.era`: the style's era against `opened`. A warning only.
- `bldg.fit`: on a measured massing, stories × floor heights more than one floor away from the measured height is a note on the card, not an error (7.6).

#### Store change

- A `timeline` column on `rec`, by a migration under `region/model/migrations/`.
- `dates.timeline` in `region/kinds/_meta.schema.json`. Today `dates` allows only `open` and `close`, and `columns` only name, system, parent, c0, c1, ord and phase.
- The SQL clause in `region/model/query.py` (`x.timeline IS NULL OR x.timeline = ?`), next to the `open_lo` and `close_lo` test, and the same test in `Store._list_tag`. Tests for both paths.
- `Store._list_tag` (a list as of a tag) reads every revision of the kind from `rec_hist` (`layers.as_of_rows`) and tests bboxes in Python. `rec_rtree` indexes only current `rec` rows, so tag views of 300,000 buildings need their own prefilter (rtree ids first, then the history).
- Search (Ctrl+K) filters only the promoted `name` column (`x.name LIKE`). Search by address needs a new promoted column or a search index, a `_meta.schema.json` change like `timeline`.
- The store does not know site-derived closes. Building lists by year (the map's Buildings layer, the card's derived close, search) come from `bldg.resolve` output, not from `/k/building`.

#### Layers and id namespaces (`region/ids/namespaces.yaml`, the next free epochs)

| Namespace | Epoch | Layer | Key |
|---|---|---|---|
| `bldg_real` | 2020-01-05 | `import:bldg_real` | `cagis:<id>`, `lidar:<cell>:<n>` |
| `bldg_sanborn` | 2020-01-06 | `import:bldg_sanborn` | `1904:v<vol>:s<sheet>:<n>`, `1922:p<plate>:<n>` |
| `bldg_styles` | 2020-01-07 | `import:bldg_styles` | style slug |

- **Ledgers.** Ids are deterministic (sha256 of namespace:key), so the `bldg_real` ledger (300,000 to 1 M lines) can be rebuilt. The proposal: keep it in the hub's data folder beside region.db, and keep only the aliases (merges, splits, CAGIS re-releases) in git as `region/ids/bldg_real.tsv`. This bends the ledger rule and needs Ben's ruling (7.12).
- `bldg_sanborn` and `bldg_styles` keep normal ledgers.
- **Authored records** get random ULIDs (Architecture 9.17). Frontage fills carry `attrs.fill_key = <block>:<face>:<n>`, so a repeated fill is found and offered as an update.
- **main:** Ben's checks and edits to real and historic buildings, canon buildings, canon sites, model records, style edits and frontage fills.
- **Scenarios** have bare slugs (`cbd-infill-a`, as `fs-stacked`) and exist only on Ben's machine. **Proposals** (`proposal:cbd-infill`) are seeded to `region/seed/proposals/<name>/` (for `proposal:cbd-infill`, `region/seed/proposals/cbd-infill/`), which is how a cloud session hands work to Ben.
- **Imports** are never seeded. They are rebuilt from the tiers and the Sanborn vectors.
- **Seeds.** Copy-up is at record grain, so any edit Ben makes to a measured building would put the whole record, CAGIS footprint included, into `region/seed/main/`. Apply to selection on tens of thousands of buildings would then grow git past ruling 5.
  - So seed export writes, for every `building` revision whose base is in an import layer, the changed fields only, with geometry left out when it equals the base. The import puts the base back. This is the rule whatever the CAGIS terms say, and it changes seed export (9.29).
  - The CAGIS terms stay a B0a gate for any footprint Ben draws from CAGIS geometry.

#### Params (`rules/registry.yaml`, status `drawing_value`: a new value, as 3.1 proposes; registry params carry `recorded` or `literal_in_code` today)

- `bldg.floor_h.{ground_commercial 4.6, ground_res 3.8, upper_19c 3.4, upper_modern 3.2, office_1920 3.9}`.
- `bldg.skirt_m` 0.5, `bldg.parapet_m`, `bldg.facade_min_wall_m`.
- `bldg.roof.flat_max_deg` 5, `bldg.roof.fit_rmse_max_m` 0.5, `bldg.sanborn.half_story_pitch_deg`.
- `bldg.before_floor_year` 1850: a building known only as "standing by 1904" opens here (7.8).
- `bldg.undated_past: hide | show`: a measured building with no date. `show` departs from 9.16 and needs Ben's ruling.
- `bldg.fill.street_wall_depth_m` 14.
- `bldg.lod.*`, `bldg.budget.*` and `bldg.cache_gb` (7.9, 7.10).
- New `look.materials`, each with a main and a secondary value (1.3: "Two values per material. Keep it."). Secondaries are *drawing values*, main × 0.82 until set, except where given:
  - brick: `brick.red` #9c5a44 / #7d4636, `brick.buff` #b89a74, `brick.dark` #6e4a3c;
  - other walls: `frame.white` #d8d2c4, `frame.grey` #a8a39a, `stone.limestone` #c9c0aa, `glass.curtain` #52636b; the 1930s and modern concrete reuse 1.3's `deco` and `apex`;
  - roofs: `roof.tar` #4b4846, `roof.slate` #4e5458, `roof.tin` #7b7f80, `roof.copper` #5f8a78.
- A hex colour Ben picks gets its secondary the same way, unless he gives both.
- `building` #b9a68a stays as the fallback.

### 7.5 The style catalogue

A style is a full set of drawing parameters. A building's style is Ben's pick, or else the default from era, material and use.

**Fields of a `building_style`:**
- slug, title, `era [first, last]` (a guide for the default rule, and a warning only), `uses[]` and `materials[]` it fits, a reference note.
- **Massing defaults:** stories range, `floor_h_m {ground, upper}`, plan form (`row | detached | corner | slab | tower_on_podium | shed`), frontage and depth range.
- **Roof:** form and pitch; dormers yes or no.
- **Facade:** grammar (`rowhouse, commercial, loft, industrial, civic, church, slab, curtain, garage, none`), bay width, piers (none, plain, brick, rusticated), string courses, base (plain, rusticated, granite).
- **Windows:** kind (`flat | segmental | round | pointed | ribbon | curtain | steel_sash | none`), width and height, hood (`none | bracketed | pediment | label | lintel`), sill.
- **Cornice:** kind (`bracketed | modillion | corbel_table | parapet | coping | stepped_crown | none`), height, projection.
- **Ground floor:** `shopfront | stoop | blank | arcade | lobby | loading | open`, and its height.
- **Palette:** slots `main, secondary, trim, roof`, each a weighted list of `look.materials` ids.
- **Ornament** 0-3 (what L2 draws), and per-param `{default, min, max, vary}`.
- `sanborn_match`: the codes the style answers to, used by `region/ext/buildings/rules/infer_sanborn.yaml`.

**Per-building overrides.** Every style parameter can be overridden per building. The building's `facade`, `roof` and `colour` objects have the same keys as the style's (`grammar`, `piers`, `string_courses`, `base`, `window {kind, w_m, h_m, hood, sill}`, `cornice`, `ornament`, `plan_form`, `roof {…, dormers}`, the palette slots). A null key follows the style. The reset mark nulls one key.

**Starter catalogue** (*drawing values*; era ranges are rough and *unconfirmed*; Ben to add, cut and rename):

| Slug | Era | Typical | Roof | Cornice and windows |
|---|---|---|---|---|
| `federal_greek_revival` | 1815-1855 | brick, 2-3 stories, row or detached | gable, low pitch | plain frieze; flat stone lintels |
| `italianate_row` | 1850-1890 | brick, 3-4 stories, 6-8 m frontage, rear ell | shed behind a parapet | bracketed; tall segmental windows with hoods |
| `italianate_commercial` | 1855-1895 | brick or stone over an iron shopfront, 3-5 stories | flat | bracketed; arched windows in bays |
| `second_empire` | 1865-1885 | brick or stone | mansard with dormers | bracketed; pedimented hoods |
| `queen_anne` | 1880-1905 | brick or frame, detached or corner | gables, a turret | small; varied windows, bays |
| `romanesque` | 1880-1900 | stone or brick, civic, churches, warehouses | hip or gable | corbel table; round arches, rusticated base |
| `gothic_church` | 1840-1930 | stone or brick nave and tower | steep gable, spire | none; pointed windows |
| `beaux_arts` | 1895-1930 | limestone, civic and banks | flat behind a balustrade | modillion; tall windows between pilasters |
| `chicago_commercial` | 1890-1925 | brick or terracotta office, 6-16 stories | flat | deep cornice; wide windows between piers |
| `art_deco` | 1925-1945 | limestone or brick, offices | flat, stepped setbacks | stepped crown; vertical piers, spandrel panels |
| `warehouse_loft` | 1870-1930 | brick, 4-8 stories | flat | corbel table; segmental windows between brick piers |
| `daylight_factory` | 1905-1940 | concrete frame | flat, sawtooth or monitor | coping; wide steel sash |
| `worker_cottage` | 1840-1910 | frame or brick, 1-1½ stories, shotgun | gable | none; small flat-headed windows |
| `tenement_flats` | 1870-1915 | brick, 4-5 stories, light wells | flat | pressed-metal; flat lintels |
| `mid_century_modern` | 1945-1975 | concrete, metal, glass | flat | none; ribbon or curtain wall |
| `brutalist` | 1960-1980 | concrete | flat | deep coping; deep-set windows |
| `contemporary_infill` | 1990- | brick, panel and glass, often podium and mid-rise | flat | coping; large flat windows, shopfront |
| `parking_garage` | 1950- | concrete decks | flat | open spandrel bands |
| `generic` | any | the fallback for a building no rule places | from the measured solid or flat | plain |

**The default rule** (`region/ext/buildings/rules/style_defaults.yaml`, rule `bldg.style.default`):
- Ordered rows of `{use, material, era, stories, plan form, frontage}` to a style. The first row that matches wins. A row's era may be `any`.
- Era comes from `opened`. An undated measured building uses the dating order of 7.8. A building with no date at all matches only rows with era `any`, and gets `generic` only when no row matches (outside Hamilton County most buildings are undated).
- The card names the row ("rule bldg.style.default, row 4: brick, residential, 1850-1890, frontage under 9 m").
- **Use adds to the style:** commercial and mixed get a shopfront; residential a stoop; industrial loading doors; parking open decks; religious and civic keep the style's own ground floor.
- A style Ben picks against its era or use gives the `bldg.era` warning only. He may put a Queen Anne house in 2030.

**Inference tables** (`region/ext/buildings/rules/`):
- `infer_sanborn.yaml`: Sanborn codes, fills and named uses to use, `use_detail`, material, stories and basement.
- `infer_real.yaml`: the auditor land-use codes and the CAGIS fields to use and `use_detail`.

### 7.6 The generator and the Model look

**Where.**
- `engine/src/mesh/`, pure TS with no three.js (2.1).
- New files `building.ts`, `roof.ts`, `facade.ts`, `footprint.ts` and `values.ts` (`bldg.values@1`, 7.4), built on the 2.2 kernel: `sweep`, `instances` and `toGlb` from Step 0, plus `prism`, which B0b adds.
- Method `mesh.building@1`, contract `mesh_input/0`, registered in `engine/src/methods.ts`. The server job and the app's draft worker import the same file.
- A building's mesh depends only on its own resolved record, the ground patch under it, its street-facing edges and its party edges. It never depends on its neighbours' heights or styles, so an edit re-meshes one building.
- The engine never reads records (2.1). `mesh_input` for a cell carries the cell's ground patch, resolved values and edge lists. The app worker caches the patch for drafts.
  - A date edit that crosses a ground change (a regrade year, a timeline switch) fetches that year's patch before the draft draws.

**1. Resolve.** `bldg.values@1` (in the worker for drafts) and `bldg.resolve@1` (per cell on the server) resolve every value with its source (7.4). The cell job also works out the street-facing edges and the party edges.
- Street-facing edges face the street set of the building's era: the 1904 and 1922 basin streets for historic buildings; for measured and proposed ones, today's streets from the OSM extracts already in the repo (`data/sanborn/basin/osm_basin.geojson`, `data/sanborn/lph/osm_*.geojson`) until the street model of 2.3.10 exists. Beyond those extracts there is no today's-street layer yet.
- With no street layer (a cloud session), edges not shared with a neighbour count as faces.
- Ben's `front_edges[]` wins over both.

**2. Measured or generated massing.**
- A measured building with a `measured.solid` is drawn from that solid, unless a massing field is set or `massing` is `generated`.
- **Massing fields:** the footprint, `roof`, `parts` and their stepbacks. `height_m` is drawn on the solid (below).
- **Kept on the measured solid:** name, address, notes, use, style, material, colour, facade, shopfront, dates, timeline, stories, floor heights and height.
  - Facade, shopfront and cornice are laid on the solid's street-facing vertical walls, between the drawn ground and the measured eave of that wall.
  - **Stories.** A count whose height (stories × floor heights) is within one floor of the measured height only re-divides the window rows on the solid. A count beyond that is a height edit (next bullet). Floor heights alone never change the massing.
  - **Raised or lowered measured solid.** A `height_m` edit (typed, dragged, or from a stories count beyond the fit) keeps the solid. Every vertex above the lowest measured eave moves by the change, so the walls lengthen or shorten and the lidar roof is kept. The source reads "lidar 2022 roof, raised 6.8 m (Ben, 24 Nov 2026)". A lowering that would put the lowest eave under one story switches to the generator.
- **Generated:** the first massing edit switches the building to the generator.
  - Its starting values come from `measured`: the footprint, h_70p per LoD1.3 level as `parts`, and `measured.roof` as the roof form, pitch and ridge. So the generated building starts close to the measured one.
  - The card's "Drawn from" row then reads "parameters (lidar solid kept; Back to measured)".
  - While a generated measured building is selected, **Show measured** draws the lidar solid as a ghost (#c9c5ba at 0.15), so Ben sees what the parameters replaced.
- A `model` record behaves the same way, with **Back to model** (7.3).
- **Historic and proposed buildings** are always generated. A historic building's "Back to Sanborn" returns it to the traced footprint and read values.

**3. Footprint.** `footprint.ts` fixes ring orientation, removes slivers and spikes, and finds the minimum-area rectangle.

**4. Walls.** Each part is a closed `prism(slot, ring, z_base - bldg.skirt_m, z_top)`.
- `z_base` is sampled from the same `region.ground` grid the terrain tile draws, per timeline. The element table holds `z_base_real` and `z_base_canon`, and the shader picks one by `uTimeline`. The lidar DTM is a check only.
- Hillside rows step down as plinths.
- A part can stand on another part, or on a structure (shops under a viaduct).
- A part's height is `height_m`, or stories × floor heights. Stepbacks shrink the ring above their story.

**5. Roofs** (`roof.ts`).
- Forms: flat and parapet; shed; gable, hip and mansard by a straight skeleton; gambrel; sawtooth and monitor (Mill Creek industry); pyramid, spire and dome.
- If the skeleton fails, the roof falls back to the oriented rectangle clipped to the ring. If that fails too, it falls back to flat with a Review flag.
- **The measured solid** is roofer's whole LoD2.2 solid (walls and roof), stored relative to its own DTM base (`z - dtm_min`) and re-based on the drawn ground. It is never a prism plus a clipped roof, because real eaves vary.
- **Roof reduction** (for `measured.roof`) runs per roofer height level: all planes under 5° is flat; one plane is shed; two opposing planes gable; four hip; two tiers of slope mansard. A building with more than one level, or a fit above `bldg.roof.fit_rmse_max_m`, records `form: null`. Expect that for most of the CBD.

**6. Facades** (`facade.ts`). From A's `facade()` and its `faceM` frame (u along, v up, w out), with the same parameter style (frame 0.25, cornice 0.55, parapet 0.66).
- A grammar of stories × bays: the ground floor (shopfront, stoop and door, blank, arcade, lobby, loading), upper windows with hoods or sills, string courses, cornice and parapet. The style gives every value; Ben's facade fields override them.
- Full facades go only on street-facing walls longer than `bldg.facade_min_wall_m`. Party and rear walls stay plain.

**Exaggeration.** Building vertices are stored relative to the base, so `_G` cannot be their own y. Instead they carry a flag in the element texture. The shader adds the timeline's `z_base` and then sets g = y for them, so exaggeration (1.8) leaves them unchanged. `pick.ts`, the BVH raycast and the label pass add the same `z_base` on the CPU. Buildings stand on true ground at every k.

**Watertight.** Generated solids are closed and covered by the watertight test (5, item 3). The measured solid passes the same test or is left out of stencil caps.

**LOD** (fits 4.3).

| LOD | Distance | Content | Triangles per building |
|---|---|---|---|
| HLOD | 4 km and 16 km parents | one oriented-rectangle prism per building (12 triangles), with `_ERA` per building; tiles capped at 60,000 buildings; chosen by screen-space error; buildings under 2 px culled | 12 |
| L0 | over 2 km | prism plus simplified roof (roofer LoD1.2, or eave plus half the rise) | 20-60 |
| L1 | 300 m to 2 km | the measured solid decimated, or the full generated roof; cornice and ground-floor bands; windows as a procedural canvas tile in metre UVs | 100-300 |
| L2 | under 300 m | recessed windows, hoods, shopfronts (`glass_lit` at night), cornice profiles by `sweep`, fire escapes and water tanks as `instances`; landmark models at full detail | 1,000-3,000 |

- L0 and L1 are prebuilt. L2 is built on demand for cells within 300 m and kept in an LRU cache capped by `bldg.cache_gb`.

**Model look.**
- One palette for real, lost and proposed buildings. Lambert, with main and secondary values per material (1.3).
- No photo textures, no lidar textures, no edges.
- The windows (L1) and brick-course (L2) tiles in 1.3's list are for buildings.
- **Labels.** Buildings with a name get labels of class `building`, the lowest priority in 1.6's collision pass (after station, structure, element), culled beyond 400 m (*drawing value*), through 1.6's collision and occlusion passes.
- **Provenance views**, not a second look:
  - **Tint by origin** (measured, historic, proposed, model): a toggle on the 3D pane.
  - **Unchecked and invented mark:** a lighter value on historic buildings not yet accepted (`checked` null), on frontage fills, and on any building whose footprint or height confidence is `inferred` or `invented`. Measured buildings are marked only while they carry an open Review item (merged row, shift, gone since 2011). Authored records count as checked by their author. So the default view of today's city and of Ben's designs is not lightened. On by default until Ben rules (7.12), so invented history never passes for traced.
- **Diagram mode:** buildings draw as one translucent neutral (#c9c5ba at 0.15, no depthWrite), or hide. A toggle, default hide.

**GLB** (as 4.2, with these changes for buildings).
- Each vertex carries a slot `_S` (uint8: wall, secondary, trim, roof, glass, frame, plinth), `_EL` (Uint32 for building GLBs, since 2.1's Uint16 caps at 65,535 elements), `_G` and `_ERA`.
- **One shared Lambert material per LOD**, built by `look.ts`. It reads an element texture: per building, each slot's material id or hex, both intervals, the timeline bits, both `z_base` values and the exaggeration flag. So:
  - a palette edit rebuilds nothing (4.1);
  - a colour or material edit on one building rewrites one row of the texture, with no re-mesh.
- **Draw calls.** About 200 cells of 250 m lie within L1's 2 km, so one draw per cell per LOD would break 7.9's cap. The cells of one LOD draw through one three.js `BatchedMesh` per LOD, with the one shared material, and `_EL` indexes one element texture for all loaded cells. Draw calls do not grow with cells. If `BatchedMesh` fails the parity tests, L0 and L1 are packed per 1 km district from the fragment memo instead.
- **The element texture comes from its own blob.** `bldg.resolve@1` writes two outputs per cell (7.10): the mesh slice (the values the generator reads) and the element slice (names, sources, intervals, timeline bits, `z_base` and slot colours, as blob `bldg.elements`). The pane loads the element slice into the texture. A name, dates or colour save rebuilds no GLB.
- 2.1's `Element` gains optional `open_real, close_real, open_canon, close_canon, z_base_real, z_base_canon`. 4.5 adds `uTimeline`.
- A uniform `uHidden` (an element-id texture) hides the saved mesh of the building being edited while its draft draws, and the saved meshes of neighbours re-meshed by a footprint drag.
- `pick.ts` and the label occlusion pass apply the same `_ERA`, `uTimeline` and `uHidden` tests on the CPU, so a hidden building cannot be picked.
- `extras` hold the element table and a float64 origin taken from the content bounds, not from the cell name. Meshopt quantisation.
- A 3D Tiles 1.1 export for other viewers, by a later `crhub tiles3d` command (a new name; `crhub export` is the seed export, `region/cli/export.py`), is an option, not the hub's own format.

### 7.7 Editing a building in the app

All of this happens on the map pane, the 3D pane (`app/src/plugins/view3d/`, planned) and the inspector, which share selection and drafts (Architecture 8).

**The map's Buildings layer.**
- Static PMTiles from the tile job `tiles.bldg@1` (7.10) for the overview, as 9.30 requires.
- Full GeoJSON from the API for the cells in view at edit zoom (z 16 and up). That is what Ben selects and edits.
- Both come from `bldg.resolve` output and carry each building's real and canon intervals and its timeline bit. The map filters by year and timeline on the client (9.30), so the slider never refetches.
- Buildings changed in the view's layer since the last tile run draw from GeoJSON over the PMTiles at every zoom, with their tile features hidden by id. So a save shows on the overview at once.

**Select.**
- Click a building on the map or in 3D. Shift-click adds to the selection; a box drag on the map selects many. Ctrl+K finds a building by name (the `name` column). Search by address needs a new promoted column or a search index (7.4, "Store change").
- Selection goes to the host (`sel=building:01K…`). The 3D pane outlines it (1.5), and the map draws it with its vertices.

**The building card** (in the inspector). Collapsible groups:
1. **Identity:** name, address, notes, use, use detail.
2. **Style:** style (the list is ordered by fit to era, material and use, with the default marked), material, colours (main, secondary, trim, roof), ground floor and shopfront, piers, string courses, base, windows, cornice, ornament, plan form, dormers. Each is the style's value until Ben overrides it (7.5). **Edit style** and **Make style from this building** are here.
3. **Massing:** Drawn from (measured solid or parameters), with **Show measured** while generated; footprint area and frontage (read-only), stories, floor heights, height, basement, roof form and pitch, parts (podium, tower, setbacks, wings, each with its use), GFA per use (read-only).
4. **Dates:** year built, year demolished, their qualifiers, timeline, and the derived close with its cause (a site or `replaces`), read-only.
5. **Provenance:** origin, checked (by and date), confidence per attribute, evidence, `same_as`, `replaces`, lots, and the raw source fields (collapsed).

Each row:
- label, value, source in words with a rule chip, a "was" note while the draft differs, and a reset mark where Ben's value hides a lower one (7.4);
- number fields behave as the line sheet's: each visit to a field is one undo step, Enter saves and leaves the field, and lengths follow the m and ft switch.
- In the stories field Up and Down step one story. In the height field and other lengths they step 0.1 m (Shift 1 m).

For a multiple selection, the card shows shared values and "mixed" where they differ. Setting a value drafts it on every selected building, and Enter saves them in one changeset (Apply to selection). On a "mixed" number field Up and Down step every selected building by the same amount.

**Change the footprint on the map.**
- Edit footprint (F) shows the vertices as handles (terra-draw, 2.3.8). Drag a vertex; drag an edge midpoint to add one; Del removes one; or Draw footprint for a new building.
- Snapping: neighbouring walls, the street sides of the building's era, parcel lines (tier `parcels`, 7.3), and right angles. Alt turns snapping off, for every handle, footprint and height alike.
- Dragging a vertex moves this building only. Alt+Shift moves a shared party-wall vertex in both buildings. The hint names the neighbour ("also moves 1214 Vine St; it is drawn from parameters after this"). The neighbour's change is in the same changeset and the same undo step. `bldg.overlap` flags the rest.
- A footprint edit is a massing edit, so a measured building switches to generated (7.6).

**Change the height in 3D, or type it.**
- The 3D pane gets a handle layer, `app/src/three/handles.ts` (new; 4.6 is pick-only today).
- The selected building shows a top-face handle per part. Drag it up or down. It snaps to whole stories; Alt drags free. A label shows the height and stories.
- On a measured building the drag raises or lowers the lidar solid and keeps its roof (7.6, step 2).
- A stepback shows an edge handle for its depth.
- Typing the height in the card does the same as the drag. Typing stories does the same as dragging the handle by that many stories.

**Pick use and style.** From the card, for one building or the selection.
- A building on the default style follows the default: change its use or date, and the style re-resolves, with the source saying so.
- A style Ben picked stays picked.
- **Edit style** opens the `building_style` record in the inspector with the same rows (value, source, "was", reset). While it is a draft, the worker redraws the visible buildings on that style, nearest first, up to `bldg.budget.style_draft` (200, *drawing value*). The rest follow after the save, with a pending mark.
- **Make style from this building** creates a style draft from the building's overrides. Enter saves it as a new style in the view's layer.

**Change parts, roof and facade.** Add tower, Add setback and Add wing make a part. The tower takes its ring as an inset of the podium (setback_m) or its own drawn ring. Roof form, pitch, shopfront, cornice and windows are fields in the card.

**Back to the measured or historic original.**
- **Per value:** the reset mark sets Ben's field back to null. The source then shows what the value follows.
- **Back to measured** (or **Back to Sanborn**, **Back to model**): sets `massing`, `height_m`, `roof` and `parts` back to null and writes the import's geometry back, so the measured solid draws again. Identity, use, style, facade, colour and dates edits stay. It also works on a selection.
- **Reset all:** writes a revision equal in content to the import below, as the store already does when a scenario's first edit is undone.
- Each is a draft that draws at once, then one changeset and one undo step. The import revision underneath is never touched.

**Drafts, saving and undo.**
- Every change is a draft shared by the map, 3D and the card. That includes the one-click actions: Back to measured, Reset all, Apply to selection, Split at this year, Replaces..., Fill frontage, From Sanborn and Draw footprint. Each makes drafts that draw at once. Only the Review actions (Accept, Check sheet) write directly.
- The worker re-meshes only the drafted buildings (7.9), and `uHidden` hides their saved meshes.
- **Enter** or **Ctrl+S** (or Save) saves all drafts of the action as one changeset, with If-Match, to the view's layer, main or a scenario. The store refuses writes to import layers.
  - The first write copies the record up with `base_hash`. In main its version is 1. In a scenario the version continues from the base (base + 1).
  - The server re-meshes that building and swaps its cell over SSE. The draft then drops. If the job fails, the draft stays drawn with an error chip.
- **Esc** drops the draft. **Ctrl+Z** steps back through the draft, and after a save undoes by a revert changeset.
- A 412 offers Keep mine or Take theirs. On a changeset with several records it lists the stale buildings. Keep mine rebases each one three-way and sends the changeset again. Take theirs drops those buildings from it.
- A re-import under Ben's revision merges what he did not change; the rest waits in Review, and his revision stays on read (7.4, "Merge").

**A. A proposed building on a downtown parking lot**
1. In the layer chip, pick or make the target layer, for example the scenario `cbd-infill-a`. Set the year (2032) and the timeline.
2. Turn on **Sites** (the `bldg.sites@1` candidates) and click one. Or use **Draw footprint**.
3. Pick an envelope preset (`dd_a_core`). Its values are edited in the card, and the volume draws in 3D as a translucent wire. 3D handles for envelopes reuse `handles.ts` later.
4. Pick a use (mixed) and a style (`contemporary_infill`). The generator fills the envelope, and the draft shows at once.
5. Adjust: drag the podium and tower heights, add a setback, tick shopfront, change the colour. The card shows GFA, FAR and stories. A broken envelope turns the building red and lists the Review item.
6. Set the year built and the timeline. Press **Replaces...** and click the garage on the lot. That fills `replaces[]`, which closes the garage at this building's year built, on its timeline, in this layer. Nothing in `import:bldg_real` changes.
7. Enter saves.
8. Compare with `/layers/{slug}/diff` (records created, changed and deleted). Buildings that a new `replaces` or a site hides do not appear there, because their records are unchanged. They come from `bldg.resolve` output, and the 3D before and after uses that. A scenario lives only on Ben's machine; promote it to `proposal:cbd-infill` for a git copy, or to main when Ben decides. Alternatives are sibling scenarios.

**B. A lost West End building**
1. Layer main, year 1930, timeline real. Turn on the 1904 Sanborn tiles under the map (2.3.12).
2. **Check sheet** steps through the Sanborn Review items with a trace/plate swipe. One key accepts the sheet, with per-building exceptions: A accepts, E edits, X rejects (a tombstone, for a wrong trace). Accepting sets `checked`. A progress counter runs per district. The West End box of 7.2 alone covers 41 frames.
3. For a building the trace missed, use **From Sanborn**: click inside it on the plate. The traced fill there becomes the footprint, prefilled with the stories and material read there. Or draw it by hand, with `origin.ref` set to the sheet.
4. Fix stories, roof or style in the card. This is a field revision in main that a re-import keeps.
5. Add evidence: a photo ref with a date and a note.
6. Set dates if they are known. Otherwise the Kenyon-Barr site closes the building on the real timeline, and the card shows the derived close.

**C. A block with no traces yet: Fill frontage**
1. Click a block face (a `basin.json` block). Choose a use, a style, a lot width, a depth (`bldg.fill.street_wall_depth_m`) and stories.
2. The app makes drafts of `building` records with random ULIDs and `attrs.fill_key`, and Enter saves them in one changeset. They get `method: frontage_fill` and `confidence: inferred`, and carry the unchecked mark.
3. **Apply to selection** changes many records in one changeset. **Re-roll** changes their seeds.
4. Fill frontage works one block face at a time unless Ben rules otherwise (7.12).

**D. A landmark model**
1. Ben saves the .glb in the `models3d` tier folder. Ctrl+K "Place model" lists the tier's files.
2. The hub checks it with `@gltf-transform`: metres, Y-up converted to the 26916 frame, and the triangle budget.
3. Place it with a gizmo (E, N, on ground, azimuth), snapping to the footprint it stands for. Map its materials onto `look.materials` slots.
4. The hub proposes `same_as` (it is the real building) or `replaces` (it stands where others stood).

Cloud sessions can draft fills, envelopes, style edits and proposals as `region/seed/proposals/<name>/` on a branch. Ben pulls, imports and promotes. No artifacts are involved (CLAUDE.md).

### 7.8 Eras, timelines and layers

**Job `bldg.resolve@1`** (process host; scope one 250 m cell plus a 50 m margin; each cell's output has its own hash, so early cutoff limits an edit to its cell):
1. Read the layer chain (scenario, main, legacy, imports) for every `building` and `site` whose bbox touches the cell, plus the works footprints and the styles in use.
2. Resolve every value with its source (7.4) and the edges (7.6).
3. For `same_as` pairs, the measured record gives the geometry from its `opened` date. Before that, the historic record shows. A `same_as` to a `station_element` or `structure` suppresses the building, so the CAGIS Union Terminal is not drawn over the station model.
   - In a `same_as` pair, the historic record's unset name, address, notes, style, material and colour follow the measured record, with the source "same building, measured record". Ben edits them once, and a 2026 rename shows in 1930.
4. Date undated measured buildings in this order: Ben's value; a Sanborn match (before 1904 or before 1922); the auditor's year built; else `bldg.undated_past`.
   - `opened_q: before` opens at `bldg.before_floor_year` (1850). Otherwise `is_open` would hide every "standing by 1904" building in 1900.
   - An undated measured building that overlaps an unmatched historic building opens `after` the last edition that shows the historic one, and the historic one closes then.
5. Effective close is the earliest of `closed`, the `opened` of the first site that hides the building, and the `opened` of a building that lists it in `replaces` on the same timeline.
6. **Redevelopment rule.** A building that opens after a real-only site's `opened`, and lies mostly inside it, defaults to timeline `real`. The redevelopment belongs to the history that cleared the land. The same holds inside the footprints of `real_works_removed` and the deck outline. Ben overrides it per building (timeline) or per site (`redevelopment_timeline`).
7. Output, two slices per cell, each with its own hash:
   - the **mesh slice**: the values the generator reads (footprint, parts, heights, roof, facade, edges, the solid ref);
   - the **element slice** (blob `bldg.elements`): the element table `{id, rec hash, source, confidence, open_real, close_real, open_canon, close_canon, z_base_real, z_base_canon}`, names, slot colours and the values with sources for the card.

Without step 4, 9.16 ("undated built records count only at the present") would empty every historical downtown view.

**The slider.**
- `_ERA` carries both intervals and a timeline bit. The shader discards against `uInstant` and `uTimeline` (4.5).
- Year and timeline are not job axes, so moving the slider or switching timeline never rebuilds anything.

**Layers.**
- Edits to any building, real, historic or proposed, live in main or a scenario. Import layers hold only what the imports read.
- An edit applies to the whole life of that record. A change from a given year is **Split at this year** (7.4).
- The layer enters only through content, so main and an untouched scenario share every cell.
- Eras stay records (`region/ext/rules/kinds/era.yaml`), never layers.

**Canon and real.**
- Kenyon-Barr and the I-75 take are `timeline: real` sites by default. With the redevelopment rule, canon shows the West End standing and not today's Queensgate on the same ground.
- A canon West End rebuilt in a planned form is a scenario, such as `west-end-rebuilt`, with its own sites and buildings.

**Ground under buildings.**
- The base is sampled per timeline at `opened`.
- Real ground today (`region/ground/compose.py`) is the 1912 survey less the 1912 riverworks delta, plus the 2026 ground (`ground_2026`, the map3 DEM) in the dated post-1912 works zones (`real_works_kept`: `ground/zones/zones_post1912_works.geojson`, `zone_years.json`) and outside the 1912 raster.
- Elsewhere a real building after 1912 stands on 1912 levels. Whether buildings use `ground_2026` as real-present ground everywhere, or wait for the region tiers of checklist 2.0.14, is for Ben (7.12). B1 flags the gap.
- A building that spans a regrade (the deck fill, a canon interstate) is split into two lives or re-based by Ben. The resolve job flags any base that moves more than 1 m across its life (*drawing value*).

### 7.9 Budgets

**Live editing** (warn-only tests in `tests/perf` and `app/e2e`, on Ben's machine; *drawing values* except the 1 s save, which is Architecture section 6's edit-to-SSE budget):

| Edit | What runs | Budget |
|---|---|---|
| name, address, notes, timeline; dates where the style is set | no mesh; the card and the element texture | under 16 ms |
| colour; material where the style is set | one element-texture row; no re-mesh | under 16 ms |
| use, dates or material where the style follows the default | the style re-resolves (`bldg.values@1`), then the worker re-meshes that building | as the next row |
| style, facade, shopfront, stories on a measured solid | the worker re-meshes that building | under 16 ms per draft step at L2 (3,000 triangles); under 50 ms for the largest generated building (10 parts) |
| height drag, roof, parts | the worker re-meshes that building | as above |
| footprint drag | that building, plus neighbours whose shared edges change (usually 0-2) | as above |
| save, undo, Back to measured | `bldg.resolve` for one cell (under 200 ms), then `glb.bldg` re-meshes the changed buildings and re-packs the cell from the fragment memo; SSE swaps it | edit to swapped cell under 1 s |
| Apply to selection (n buildings) | the worker re-meshes nearest first within 16 ms per frame, the rest over the following frames with a pending mark; on save each touched cell is re-packed in parallel | each cell swaps within 1 s of the save |
| a style record edit | the draft redraws visible buildings on the style, nearest first, up to `bldg.budget.style_draft` (7.7); after the save every cell that uses the style, visible cells first, in the background | not a one-building edit; a pending mark shows progress |

- While Ben drags, the worker takes the latest input and drops stale ones, so the frame never waits.
- No edit reruns roofer, the lidar pass or an import.

**Rendering** (a city share inside 4.3's totals):
- at most 100 draw calls (one `BatchedMesh` per LOD, 7.6) and 1.5 M visible triangles for buildings;
- L2 only within 300 m, capped by count, nearest first;
- buildings cast shadows only in the 500 m cascade;
- render on demand, 0 fps idle.
- The city share (1.5 M) plus R's 2.39 M exceeds 4.3's 3 M. Either 4.3's total rises for city views, or the city share drops to 0.6 M within 1 km of a structure view. Ben to rule (7.12).

**Tests:** downtown at 1 km altitude; the whole metro at HLOD; a height drag on one building that redraws in one frame and saves (version 1 in main, or base + 1 in a scenario) within 1 s; Back to measured that restores the lidar solid in one undo step.

### 7.10 Whole-metro scale and storage

**Grid.** Fixed EPSG:26916 cells.
- Districts of 1 km, named `d<E_km>_<N_km>` (for example `d713_4331` for the West End), used for batch runs and bookmarks.
- 250 m cells for resolve, L0, L1 and L2.
- HLOD parents at 4 km and 16 km.
- Named districts (CBD, West End, OTR, Queensgate) are only bookmarks.

**Jobs.**

| Job | Host | Scope | Key |
|---|---|---|---|
| `cagis_fetch`, `parcels_fetch`, `lidar/run_cells` | lane B batch (not a hub job) | 1 km cell, resumable | writes tiers with `MANIFEST.csv` and `STATUS.json` |
| `bldg.resolve@1` | process | 250 m cell | building, site and style record hashes in the cell and margin; the hashes of structures and sections that a part stands on; works footprint hash; ground tile hashes; `bldg.floor_h.*`, `bldg.before_floor_year`, `bldg.undated_past`, `bldg.sanborn.*` |
| `glb.bldg@1` | engine | 250 m cell × LOD | the resolve **mesh slice** hash for the cell (not the element slice), roofer cell file sha, model shas, `bldg.floor_h.*`, `bldg.skirt_m`, `bldg.parapet_m`, `bldg.facade_min_wall_m`, `bldg.roof.*`, `engine_build` |
| `glb.bldg_hlod@1` | engine | 4 km and 16 km parents, background priority | the child cells' mesh slice hashes; until it ends, the old prism shows beyond 2 km |
| `tiles.bldg@1` | process | 1 km district, background priority | the district's resolve outputs; writes the PMTiles overview |
| `bldg.sites@1` | process | district | `parcels` tier and lidar hashes |

- Keys hold only the params the plan reads (`region/jobs/registry.py`). Render and app params (`bldg.lod.*`, `bldg.budget.*`, `bldg.cache_gb`, `bldg.fill.*`) are in no key, so changing them rebuilds nothing.
- `param:look.*` is not in the `glb.bldg` key, because the palette is a uniform.
- The element slice is not in the `glb.bldg` key, so a name, dates or colour save rebuilds no GLB (7.6, "GLB").
- The geometry jobs have no year or timeline axis.
- A per-building fragment memo inside `glb.bldg` makes one edit cost about one building.
- Roof fields reach `import:bldg_real` only through `buildings_real@1` re-imports of changed cells. Import layers are written by import runs only.
- `/api/v1/view3d/index?bbox&layer&year&lod` lists scope `bldg_cell` beside the section GLBs. A new blob route (to add; today only `/api/v1/data/{tier}/{path}` serves files, `region/api/files.py`) serves the content-addressed GLBs and `bldg.elements` blobs from `var/cache/blobs/` (9.18).

**Imports at scale.**
- Each cell's import is one changeset, so a cell of more than 200 changed records emits one summary event (9.28). Unchanged records are no-ops: no version, no event.
- A record is about 1.5 KB (an estimate, not measured), and each revision writes `rec` and `rec_hist` rows, so about 3 KB.

**Growth.** Each step is only a larger cell list.
1. Pilot box E 712,000-716,000 / N 4,330,000-4,333,000 (12 districts): downtown to Fountain Square (E 715,202) and the riverfront, OTR to McMicken, Queensgate and the West End.
2. The basin, E 711-721 km / N 4,330-4,340 km, where the 1904 and 1922 work is (the 1904 frames reach E 718.3 and N 4,339.5 km; the guided 1922 plates reach further east).
3. The City of Cincinnati, then Hamilton County (about 1,100 districts).
4. Northern Kentucky and the Ohio counties, with the footprint sources Ben approves.

**Storage on Ben's machine.**
- New tiers in `configs/hub_paths.json`: `bldg_footprints`, `parcels`, `bldg_lidar` and `models3d`, all `mount: true`, `required: false`. The hub reads them and never writes them.
- A missing tier is a status chip. Cloud sessions get the parametric fallback.
- `configs/local.json` can move a tier root onto an external drive.
- The sizes below are estimates, to check against the USGS listing before buying disk.

| Data | Hamilton County | Metro |
|---|---|---|
| LAZ (optional to keep after a cell is processed; none with EPT) | 30-60 GB | 150-300 GB |
| DTM COG 0.5 m | 5-10 GB | not estimated |
| roofer output | 1-2 GB | 2-5 GB |
| footprints and parcels | under 1 GB | not estimated |
| GLB cells, L0 and L1 (a rebuildable cache) | 0.5-1 GB | 1-2 GB per distinct layer content |
| L2 cache | capped by `bldg.cache_gb` | same |
| SQLite (rec plus rec_hist, about 3 KB per building) | 300-400k measured, 40-60k Sanborn: about 1-1.5 GB | about 1 M: about 3 GB |

**In git:** the kinds, styles, rules tables in `region/ext/buildings/rules/` (`style_defaults.yaml`, `infer_sanborn.yaml`, `infer_real.yaml`), params, tools, the Sanborn vectors, the `bldg_real` aliases, and Ben's main and proposal seeds. Never LAZ, roofer output, GLBs, models or CAGIS geometry (unless its terms allow, 7.4).

### 7.11 Order of work

**On hold (Ben, 24 Nov 2026):** no building work starts until the rest of the hub is complete. The open questions in 7.12 wait until then too.

Buildings follow section 6, Step 0 (the kernel and the `view3d` pane) and reuse its kernel.

| Step | Work | Needs | Gate Ben sees |
|---|---|---|---|
| **B0a** (no kernel needed) | Kind `building` (7.4), namespace `bldg_real`, tier `bldg_footprints`, `cagis_fetch.py` on the pilot box, importer with `method: cagis_extrude`, the map's Buildings layer, the timeline column and store filter | CAGIS URL, fields and terms checked (the seed gate, 7.4) | CAGIS LoD1 heights for downtown, OTR and the West End on the map; the card shows the CAGIS fields with their sources |
| **B0b** (after Step 0) | `building.ts`, `roof.ts` (flat, parapet, shed, gable, hip, mansard), `facade.ts` (rowhouse and commercial grammars), `mesh.building@1`; about 15 hand-written fixture records on one block (each roof form, a podium and tower, an OTR row, a church) in `engine/test/mesh/fixtures/buildings/`; golden tests on 50 hard synthetic or Sanborn-traced footprints (no CAGIS geometry in git) | Step 0 | That block in the 3D pane in the Model look, with the era slider and the timeline bit working |
| B1 | Kinds `building_style`, `site`, `envelope`; the starter catalogue and the default rule; `look.materials` and `bldg.*` params; `bldg.values@1`; jobs `bldg.resolve@1`, `glb.bldg@1`, `tiles.bldg@1` and `glb.bldg_hlod@1`; the building card with sources; Edit style; edits that need no massing (identity, use, style, material, colour, facade, dates) live through the worker | Ben's ruling on real-present ground (7.8), or the gap flagged | The pilot box in 3D at L0 and L1; Ben renames a building and changes its style and colour, live |
| B2 | Lidar pilot: first a check of Ben's own LiDAR (7.3); `tools/buildings/lidar/` and roofer on 4 cells (CBD, Queensgate and West End, OTR, one hillside); the survey print; the shift fit; measured solids; roof reduction; change detection once validated | roofer in WSL2 or Docker; disk | Lidar solids downtown; counts of roof forms, fit RMSE, the mismatch list |
| B3 | Massing edits: `handles.ts` (height drag, the raised measured solid), footprint vertices on the map, parts and stepbacks, roof, Draw from parameters, Back to measured, Show measured, Reset all; proposed infill: Sites, Draw footprint, envelope presets, Replaces..., diff and promote, on one real parking lot in `cbd-infill-a` | 2.3.8 (terra-draw); tier `parcels` and auditor land use for Sites (*unconfirmed*) | Ben raises a measured building two stories and puts it back; Ben designs one infill building end to end |
| B4 | Historic pilot: `trace.py` and the new reader instructions on plate 44 first (a test of the method, not the West End; Ben's plate 44 lines check block clipping, and a new hand-checked outline set checks footprints, 7.3), then on one 1904 Kenyon-Barr sheet; Check sheet; From Sanborn; the Kenyon-Barr site records; `same_as` proposals | 2.3.12 (1904 tiles on the map; today only the 1922 overview) | That 1904 sheet in 3D at 1930 and gone at 1962 on real |
| B5 | Fill frontage, Apply to selection, `region/ext/buildings/rules/infer_sanborn.yaml`; one landmark model through the tier path; the Deck envelopes | `import:deck` (Architecture 11, item 7) | A filled West End block and one landmark model in 3D |
| B6 | Grow: the basin, the city, the county, then the metro; the vectorised works footprints as implicit canon sites; perf tests | tier `parcels` beyond the pilot box (7.3) | Each new extent in 3D, within the budgets |

### 7.12 Open questions for Ben

1. **Sanborn edition.** The repo has 1904 and 1922 only. Do you have 1912 Sanborn scans, or a 1922 edition corrected to about 1950 (rights after 1929 *unconfirmed*)? If not, the West End is dated "by 1904", and changes up to clearance are missed unless photos fill them.
2. **Canon West End.** Does it stand in canon (the default here), get rebuilt in a planned form as a scenario, or get cleared on canon too? What dates should the Kenyon-Barr phases, the I-75 take and the other clearances carry?
3. **Today's buildings in canon.** All of them outside the divergence zones (the redevelopment rule, 7.8), or only those you mark?
4. **Dates for real buildings.** May the auditor's year built date measured buildings, with Sanborn presence winning? Should an undated building be hidden or shown in past years (`bldg.undated_past`; showing departs from 9.16)?
5. **The Sanborn check.** Must every traced sheet pass Check sheet before it shows, or show with the unchecked mark until you check it?
6. **Placeholders.** May Fill frontage stand in for untraced West End blocks (`inferred`, marked), or should they stay empty until traced?
7. **Marking.** Should unchecked and invented buildings carry the lighter value by default?
8. **Styles and colours.** Is the starter catalogue right, and which Cincinnati styles are missing (breweries, hillside stacked houses)? May you pick any hex colour, or only `look.materials` colours?
9. **Envelopes.** The downtown zoning (DD-A, DD-B) as written, or your own rules?
10. **Proposals.** One proposal layer per district shared through git, machine-local scenarios you promote, or straight into main with opening dates?
11. **Footprints beyond Hamilton County.** Each county's GIS only, or also OSM or Microsoft footprints (both ODbL)? KyFromAbove lidar for Kentucky?
12. **Ledger and seeds.** Is an alias-only `bldg_real` ledger in git acceptable? May seed export write only the changed fields of a building revision over an import, leaving unchanged geometry out, whatever the CAGIS terms say (7.4)?
13. **Budgets.** Raise 4.3's 3 M triangles for city views, or cap the city at 0.6 M near a structure view?
14. **Landmarks.** Which should be hand-made models (Union Terminal, Music Hall, Carew Tower, the Palace, lost West End churches), and in what tool?
15. **Disk and tools.** Where should the tiers live, and how much disk? Keep the LAZ after each cell? Is WSL2 or Docker acceptable for roofer?
16. **Photo sources.** Which collections may be cited as evidence (LOC HABS/HAER, the public library's digital collections, your own)?
17. **Height edits on measured buildings.** May a height edit keep the lidar roof by raising or lowering the measured solid (the default here, 7.6 step 2), or should every height edit switch the building to parameters?
18. **New footprints under your edits.** Any import footprint change under one of your revisions is a Review conflict (9.11), even where you kept the old footprint. Is the grouped Review action enough (7.4, "Merge"), or may a building revision whose geometry equals its base take a new import footprint on its own (a bend of 9.11 for this kind)?
19. **Real ground after 1912.** Should real-timeline buildings stand on the 2026 ground (`ground_2026`) wherever the 1912 ground is out of date, or wait for the region tiers of checklist 2.0.14 (7.8)?
20. **Lidar.** Is the LiDAR you already hold (checklist 2.0.14, `ground/2026`) a classified point cloud, and from which year? If not, may B2 fetch USGS 3DEP for Ohio?

---

## Reference screenshots to keep in `design/3d_artifacts/reference/`

All the sources are in `/tmp/claude-0/-home-user-cincinnati-rail/388de07f-a9eb-500e-a913-639254f5ddc4/scratchpad/art3d/`. The selection below is 42 files, about 7.0 MB (6.7 MiB).

| Target in the repo | Source file | Shows |
|---|---|---|
| `river_bridges/01_default.png` | `rb_01_default_both.png` | both bridges, default |
| `river_bridges/02_co_pier.png` | `rb_03_co_pier.png` | truss, two-tone pier, Embankment |
| `river_bridges/03_cs_tower.png` | `rb_05_cs_tower.png` | Deco tower, portal, bearings |
| `river_bridges/04_co_viaduct.png` | `rb_06_co_viaduct.png` | trough, blind-arch climb, quad viaduct |
| `river_bridges/05_covington.png` | `rb_07_covington.png` | blind arcade, street spans, platforms |
| `river_bridges/06_seethrough.png` | `rb_08_seethru_river.png` | see-through ground, RER C |
| `southern_bridge/01_default.png` | `sb_v-over.png` | default |
| `southern_bridge/02_deck.png` | `sb_v-deck.png` | through the portal (also the shadow-acne fault) |
| `co_bridge_1927/01_default.png` | `co_v-over.png` | default |
| `co_bridge_1927/02_pier.png` | `co_v-pier.png` | truss and pier close-up |
| `co_bridge_1927/03_route.png` | `co_v-route.png` | climb to the viaduct |
| `co_bridge_1927/04_covington.png` | `co_v-cov.png` | Covington blind arcade |
| `western_viaduct/01_default.png` | `wv_v-over.png` | default (today), draped street map |
| `western_viaduct/02_between.png` | `wv_v-between.png` | between the decks |
| `western_viaduct/03_junction.png` | `wv_v-junc.png` | masonry arches, tied arch |
| `western_viaduct/04_blvd_arch.png` | `wv_v-blvd.png` | steel arch |
| `western_viaduct/05_portal.png` | `wv_v-portal.png` | tunnel portal |
| `western_viaduct/06_1933.png` | `wv_e-1933+v-over.png` | era 1933 |
| `viaduct_arcade/01_default.png` | `va_v-over.png` | default |
| `viaduct_arcade/02_dolph.png` | `va_v-dolph.png` | arcade, shopfronts, pylon, bus |
| `viaduct_arcade/03_harrison_skew.png` | `va_v-harr.png` | skew arch |
| `viaduct_arcade/04_deck.png` | `va_v-deck.png` | on the deck |
| `metro_box/01_default.png` | `mbox_v-over.png` | default cutaway |
| `metro_box/02_track.png` | `mbox_v-track.png` | inside at eye level |
| `metro_box/03_section.png` | `mbox_v-section.png` | end-on section (also the label pile-up) |
| `metro_box/04_closed_end.png` | `mbox_v-end.png` | closed end |
| `metro_tube/01_A_default.png` | `mtube_A_over.png` | type A cutaway |
| `metro_tube/02_A_section.png` | `mtube_A_end.png` | type A section |
| `metro_tube/03_C_track.png` | `mtube_C_track.png` | ring joints, walkway |
| `metro_tube/04_C_section.png` | `mtube_C_end.png` | type C section |
| `metro_tube/05_bore_section.png` | `mtube_B_end.png` | double-track bore |
| `metro_tube/06_C_xpassage_fault.png` | `mtube_C_xp_notrain.png` | cross passage on the wrong side, no lining opening |
| `metro_sections/plate_A.png` | `msec_plateA.png` | type A section drawing |
| `metro_sections/plate_E.png` | `msec_plateE.png` | type C with walkway |
| `metro_sections/plate_F.png` | `msec_plateF.png` | box (also the clipped top dimension) |
| `metro_sections/plate_H.png` | `msec_plateH.png` | island approach plan |
| `metro_sections/plate_I.png` | `msec_plateI.png` | equipment along 1 km |
| `station_3d/01_default.png` | `st3d_01_default_fountain_sw229.png` | Diagram mode default |
| `station_3d/02_spread_cut.png` | `st3d_03_fountain_spread3_cutnear.png` | spread ×3, near half cut |
| `station_3d/03_arcade.png` | `st3d_05_cut_south_arch_arcade_close.png` | arcade at L2 |
| `station_3d/04_equipment.png` | `st3d_06_metro_box_equipment_close.png` | Metro equipment |
| `station_3d/05_viaduct_fault.png` | `st3d_09_section_rer_b_under_arch_viaduct_cutnear.png` | the viaduct over RER B (the 2.0.13 fault) |

Also to commit beside them:
- a `poses.json` per page folder, from each page's preset table and `window.__cam`;
- a short `README.md` with the harness settings.

The harness scripts are in the scratchpad, to be copied to `tools/reference_shots/` if kept:
- `/tmp/claude-0/-home-user-cincinnati-rail/388de07f-a9eb-500e-a913-639254f5ddc4/scratchpad/art3d/rb_scripts/shot.js`
- `/tmp/claude-0/-home-user-cincinnati-rail/388de07f-a9eb-500e-a913-639254f5ddc4/scratchpad/art3d_scripts/shots.js`
- `/tmp/claude-0/-home-user-cincinnati-rail/388de07f-a9eb-500e-a913-639254f5ddc4/scratchpad/art3d/mt_scripts/shot.js`
- `/tmp/claude-0/-home-user-cincinnati-rail/388de07f-a9eb-500e-a913-639254f5ddc4/scratchpad/st3d_scripts/shoot.js`

---
