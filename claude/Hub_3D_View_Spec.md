# The hub's 3D view: spec

Status: draft for Ben, 22 Nov 2026. Branch `hub_region`. Sources: the nine pages in `design/3d_artifacts/`, `claude/Hub_Region_Architecture.md`, checklist items 2.0.12, 2.0.13, 2.3.4, 2.5.4, 2.5.5 and 2.5.6, the 6 Nov rulings (checklist section 5), and scrutiny section 4. No repository file was changed while writing this.

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
  - Lots are extruded later (2.3.11).
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
| `lotMass` | lot footprint, height | building | new (2.3.11) |

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
  - **Output:** a content-addressed GLB blob, served under `/api/v1/files` with ETag and Range.
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
