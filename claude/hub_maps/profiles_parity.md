# Rail Profiles parity: the old page against the new line sheet

Written 23 November 2026 for the round that answers Ben: "The station profiles are still inferior to the old rail
profile. I cannot discern stations or set anything about stations like I could before. Look at the rail profiles from
before and see the capabilities. That's the baseline on which to improve."

Standing rule: a new-hub pane is done only after item-by-item parity with the old page it replaces.

- Old page: `data/profile/profiles.html` (3,944 lines). Bare line numbers below are in that file.
- Old docs: `hub/seed/alignments/*.json`. Their derived `stations` array ({name, c, point_c, rail, ground, depth, type})
  is the old page's own output at its last save, so it is a golden for chainage, level, depth and type.
- New sheet: `app/src/plugins/line-sheet/{pane.ts, bands.ts, drawing.ts, model.ts}`; engine `vertical.rail@1`.
- Map of the old engine: `claude/hub_maps/profiles.md`.
- Old screenshots (Lines 3 and 6, plus Line 1 and RER A): the scratch folder `parity/old/` of this session. Each one is
  named for what it shows (for example `Line_3_03_station_card_Genesee.png`).
- S1 to S82 are the items of the station inventory; R1 to R65 the items of the rest of the page. Both are below.
- Status: **done** (the new sheet does what the old page did), **partial**, **missing**.

Ben's second ask on the same day ("we have the tunnels diagrammed, we will do the same for the stations") is a 3D view
ruling, already written into `claude/Hub_3D_View_Spec.md` (open question 4, commit 6a5a29d): Model is the default mode
and stations get their own Diagram drawings in slice 5 (2.5.4, 2.5.6). This round's long-section drawing uses the same
station box, hall and shaft sizes (params `metro_structure.box`, `island_box`, `hall`, `elevated_station`), so the sheet
and the later 3D diagram show one station, not two.

## 0. What the new hub needs before A can be built

Today the sheet has one station edit (the rail level). Every other station value is either stored and inert, or not in
the new hub at all. Four small pieces close that. None needs the structure solver (I2.2).

**0.1 Records.**

| Piece | Where it goes | Source on disk | Who writes it |
|---|---|---|---|
| Ben's access choice | new field `access` on the profile record: {platform id: {type, stages?}}, kind `profile` version 2, additive | `hub/seed/params/station_access.json` (10 entries: Lines 1, 2, 3, 4, 12) | the `old_hub` importer on layer `import:profiles`; Ben's edits on his scenario layer through the draft |
| Side or island | the existing `platform.side` field (null today on every platform) | `hub/seed/params/station_platforms.json` (436: 308 side, 128 island) | the network importer; Ben's edits through a draft on the platform record |
| Station complexes (who is one station with whom) | read only, one record per complex member list, until 2.1.4 builds real complexes | `hub/seed/params/station_complexes.json` (435 auto, 1 marked) | importer only |
| Opening year per station | read only, from the Chronology's `stations` entries and the segments either side (the old `chrStationYear` 483) | `hub/seed/chronology/segments.json`, `data/profile/chronology_lines.json` | importer only; I2.4 replaces it with the full Chronology |
| Streets and roads by chainage | read only, one record per section | `data/profile/context/lines.json` (`streets`, `roads`) | importer only; also feeds R35 later |

The access choice moves into the profile on purpose. On the old page it lived outside the alignment and outside undo
(S26). In the profile it goes through the same draft, If-Match, layer and rebase as every other station edit, and Ben
can undo it.

**0.2 One engine module, `station.facts@1`.** Pure TypeScript in `engine/src/station/`, run in the sheet's worker right
after `vertical.rail@1` on every edit, and by the server job beside the solve. `vertical.rail@1` does not change, so its
41 goldens hold. Input: the SectionInput plus the section path (the section's geometry in EPSG:26916, sampled every 2 m),
each station's key, drawn point, `stt`, `gapfill`, side, access choice, opening year and complex, the profile's `ovr`
paints, and the params it names. Output per station, as data with rule ids and no UI text:

- c, point_c, half, rail, ground, depth, grade in and out (1 m beyond each end), platform grade and its limit;
- the station type and why (the station-only part of `solveTypes` 1388-1403 and `pointType` 1246-1276, below);
- the access type, its rule, its source (Ben or rule), D_HALL, hall, mezzanine, passage and shaft ranges (503-535);
- the platform curve: R, extra gap out and in, turns (2013-2072);
- flags: `kind`, `sev`, `c0`, `c1`, `rule`, `data`.

The station type here is **provisional**: Ben's selection (`stt`, or a paint over the centre) wins; else open by level
(elevated when rail minus deck depth stands `elevAbove` over the ground, at grade under `coverBelow`, trough under the
box top); else a box within the phase's `cc_max`; else mined by the phase's method (shield in Phases 1 and 2, bore from
Phase 3). The phase comes from `metro_structure.line_phase` until the Chronology is in (rule
`access.year.fallback_to_line_phase`). The full solver (canon sections, rivers, the drive's own method) is I2.2; where
the two differ the acceptance report lists the station and the reason.

**0.3 Model ops** in `model.ts`, each a JSON Patch on the draft, as `setStationLevel` is today: `setStationGrade`,
`setStationSlide`, `removeStation`, `restoreStation`, `setStationType`, `setGapfill`, `setAccess`, and `setPlatformSide`
(a draft on the platform record, not the profile).

**0.4 Draft steps.** Today Ctrl+Z undoes saved changesets only; an unsaved drag can only be discarded whole. The old page
undid each edit (200 deep) before any save. Add a step stack to each draft, so every station edit is one Ctrl+Z step
before the save, and the save is still one changeset after it.

## A. Stations, now

Every station capability of the old page that this round must reach, and the cheap improvements. Each row: the old
behaviour with its lines, the new status, and the plan.

### A.1 Seeing a station on the sheet

| # | Old (lines) | New | Plan |
|---|---|---|---|
| S1 | Platform bar, 6 px, full platform length, tilted by `sg`, ink or accent when selected, 1.5 x 10 px tick at each end (2668-2681) | done | Keep. Outline it red when the station has an error flag, amber for a warning. |
| S2 | Hollow triangle at the drawn point on the tilted level, always drawn (2678-2680) | partial: drawn only when slid | Draw it always. When the slide is over 0.5 m, add a thin line from the triangle to the platform centre with "slid -235 m". |
| S3 | The platform's structure in its type colour: roof and floor lines with a fill, one type for the whole platform; the structure band under the plot (2462-2484, 2740-2749; colours 256-263) | missing | New band `station-structure`. Over the platform span only, tilted with the bar: box from rail - `box.below` (1.0) to rail + `box.top` (4.6 side, 5.2 island), fill at 25 % in the type colour, 1.5 px edge; mined: the phase's tube outline; elevated: the deck from rail - `deckDepth` to rail; at grade and trough: no outline. A 16 px strip under the plot carries the type colour and label over each platform. The running line between stations stays one colour until I2.2 (B). |
| S4 | Name rotated 45 degrees with a dashed leader to 8 px over the rail; names under 18 px apart hidden; the selected one always shown; accent when selected (2770-2786) | done | Keep. Add a 6 px type colour square before the name. |
| S5 | Depth not on the canvas; in the table, card and readout | partial: card only | Readout (A.1), panel (A.3) and table (A.5). Better: a small depth tag under the bar ("13.6 down", "+2.1 up") when there is room. |
| S6 | Access drawing, Metro: halls or mezzanine on the box roof (z + box top up 2.75 + 0.6), elevated mezzanine from the street to the deck underside, crossunder from rail - 1.0 to rail - 3.75 for 3 m at the platform start, a 6 m shaft labelled "stairs" or "lifts", the dashed D_HALL line at ground - D_HALL; all dashed when there is no Chronology year; hidden in Rail view (2549-2585, 478-535) | missing | New band `station-access`, drawn from `station.facts@1` ranges, same sizes and labels ("ticket hall", "mezzanine", "crossunder", "stairs", "lifts"). Dashed per `access.year.fallback_to_line_phase`. |
| S9 | A second platform overlapping an earlier one is skipped; the first one's level wins (732) | partial: the engine raises `platform_overlap`, the sheet does not show it | Show the flag (S72). |
| S11 | Deleted stations not drawn; listed under "Removed" (2923-2925) | partial: they vanish, no list | Removed list (A.5). Better: a faint grey tick at the drawn point with the name struck through, so Ben sees where a removed station was. |
| S13 | Issue triangles along the bottom of the plot, red, amber or grey; station issues at the centre (2735-2738) | missing | New band `station-flags`: the same triangles for the station flags of A.6; hover gives the text and the rule id; click selects the station. |
| S14 | Vertical scale frozen while dragging (2302-2305) | done | Keep. |
| S57 (interim) | A station with no level got one from `defaultAlign` | missing: an unset station drops out of the design | Better, until I2.2: draw it as a dashed hollow bar at ground - `defDepth` with "level not set", and offer "Set to ground - 7.62 m" in the panel. |
| S18 | Hover readout: chainage, ground, rail, depth, structure top and bottom, grade, type ("(painted)"), street; no station name (3495-3540) | partial: ground, rail, below or above, grade, station name | Add, inside a platform: the type with its source, the structure top and bottom, the street. Keep the station name (better than old). |

### A.2 Selecting a station

| # | Old (lines) | New | Plan |
|---|---|---|---|
| S15 | Click the bar: platform x-span (at least +/-6 px, plus 3 px), \|y - rail\| <= 9 px; bend points win (3407-3413) | done | Keep. Check the 9 px and that a PVI wins. |
| S16 | Click a table row: select and centre, span min(current, 2500 m) (3725) | partial: centres at the current span | Cap the span at 2,500 m. |
| S17 | Esc clears; a plain click on empty canvas clears; undo and redo clear (3528, 3489, 3139) | done | Keep. |
| S18 (cursor) | ns-resize over a bar, ew-resize with Alt (3472) | partial: no Alt | ew-resize with Alt held. |
| new | none | none | `[` and `]` select the previous and next station and centre on it. |

### A.3 The station panel (replaces today's one-line card)

Today's card has name, chainage, drawn point, platform range, rail level (editable), ground, depth, grade in and out,
and platform grade as text. The panel keeps that and adds every old row. It sits under the plot, in the place of the
card, in groups. **Every row shows its value, its source and its rule**: "Ben" (his record or draft), "import" (old hub
data), "rule `id`" (computed), or "param `path`" (a limit), with the rule's text on hover. **Every edit is a draft**: the
plot redraws at once, a changed row shows "was 153.20", and nothing is saved until Save (Ctrl+S, or Enter in a field).
Discard puts every row back.

| # | Old row (lines) | New | Plan |
|---|---|---|---|
| S19 | Title: station name (3024) | done | Add the line and Prev and Next buttons. |
| S20 | Chainage (centre), and "(point x)" when slid (3036) | done | Keep. |
| S21 | Ground at centre, with "(fill/cut n)" over 0.02 m (3037) | partial: DEM ground, no fill or cut | DEM now; fill or cut needs the finished ground (B). |
| S22 | Rail level input, step 0.1, rounded 0.01, writes `st` (3038, 3089) | done | Keep. Up and Down in the field step 0.1 (Shift 1). |
| S23 | Rail below ground input: `st = refAt - value`, refAt the canon reference else the surface (3039, 3090, 930) | missing | Input against the DEM ground. The canon reference (Union Terminal track level) is B. |
| S24 | Structure: the type label (3040) | missing | Type from `station.facts@1` with its reason in plain words, for example "Cut & cover: 9.2 m down, within Phase 1's 12.19 m limit" or "Shield: 13.6 m down, past Phase 1's 12.19 m limit", and "selected by Ben" when `stt` is set. |
| S25 | Street: "under X (built over the subway)", else the roads crossing, else "not under a street" (3041, 458) | missing | From the streets and roads record (0.1). Same text. |
| S26 | Access select, Metro: "Rules: <label>" plus 9 types; writes `params/station_access` straight to the db, not undoable (3042, 3013-3021, 467-477) | missing; Ben's 10 choices are not in the new hub | Select with the same 10 options, writing `profile.access` through the draft (0.1). Undoable. The note of each type (467-477) on hover. |
| S27 | Opening: year and phase from the Chronology; interchanges at opening and later (3043, 483, 494) | missing | From the opening-year and complex records (0.1): "1906 (Phase 1); later: Line 5 1909". "Phase 1 (line default)" when no year. |
| S28 | Hall room: "needs D m of rail depth (island/side box); d here"; the only place side or island showed (3044) | missing | Same text from D_HALL (`metro_structure.hall` and box top). |
| S63 | Side or island: read only, from `station_platforms` (1287) | missing (`platform.side` null) | Better: a select "Side platforms / Island", source "import" or "Ben", writing `platform.side` through a draft. It changes the box drawing, D_HALL, hall room and the access rule at once. |
| S29 | Grade in / out, 1 m beyond each end (3045) | partial: read 4 m beyond each end | Read 1 m beyond, as the old page. |
| S30 | Platform: c-half to c+half (3046) | done | Keep. |
| S31 | Point from platform start input: step 0.5, min half-150, max half+150; writes `so = half - value`, clamped to +/-150, rounded 0.5 (3047, 3080, 3545) | missing | Same input, same clamp and rounding, through `setStationSlide`. A saved slide past 150 m shows as is and is flagged (S71), never clamped until Ben edits it. |
| S32 | Point at start / Centred / Point at end: `so = +half, 0, -half` (3053, 3081-3083) | missing | Same three buttons. |
| S33 | Platform curve, Metro: radius or "straight", ERROR / WARNING / "exception, gap fillers"; extra gap out / in in cm; "Drawing: S-curve (a/b deg)" (3048) | missing | Same rows from `station.facts@1`. |
| S34 | Platform grade input: step 0.5, rounded 0.1; writes `sg` in per mille rising with chainage, tilted about the centre (3051, 3074, 3576) | partial: text only | Input, through `setStationGrade`. The limit beside it: "limit 7.5 per mille (Lines 1-7)" with the param. |
| S35 | Hint: "The drawn point (tick on the bar) stays put; the platform slides along it. Alt + drag the bar to slide it." (3054) | missing | Same hint under the slide row. |
| S36 | Ease the bends: `sg` = mean of grades in and out, clamped to the limit, 3 passes (3055, 3076, 3579-3592) | missing | Same button, same 3 passes, one draft step. Key E. |
| S37 | Remove station: two clicks, "Click again to remove" for 4 s; takes the key out of st, sg, so, stt, mode and adds it to `del` (3055, 3085-3088, 3546-3552) | missing | Same two clicks. Better: only add to `del`; keep st, sg, so, stt, so a restore brings Ben's values back (S52). |
| S38 | Station type select, Metro: "Rules: <type>", Cut & cover (box), Shield (mined), Bore (TBM, mined), Elevated mezzanine under; writes `stt`. Elevated raises the rail to ground + 5.0 when lower (3057, 3077, 3568-3575, 269-271) | missing (`stt` stored, inert) | Same select through `setStationType`; the raise as part of the same draft step, with "raised to 184.20 for the mezzanine" in the panel. The type then drives S3, S6 and the access rule. |
| S40 | Gap fillers (named exception), Metro, shown when R < 600: toggles the key in `gapfill` (3058, 3084) | missing (`gapfill` stored, inert) | Same toggle through `setGapfill`. Better: always shown, disabled with "not needed: R 3,400 m" when R >= 600. |
| S43 | Read only when locked (3024, 912) | n/a on the Metro today | The panel is read only when the layer is (main owned by the old hub), as now. Locks are B. |
| S58 | Settings rows that touch stations: platform length, default depth, max platform grade, deck depth (555-570) | missing | Shown read only in a "Limits" group of the panel, each with its param path and a link that opens the param record in the inspector. The full settings panel is C (R20). |
| new | none | none | **Flags** group: each flag of this station with severity, text, rule id, and its fix button (Ease, Slide back to 150 m, Gap fillers, Lower to D_HALL, Choose platform level). |

### A.4 Drags, keys, save and undo

| # | Old (lines) | New | Plan |
|---|---|---|---|
| S44 | Drag the bar up or down: `st`, 0.1 m, Shift 1 m; live; save on release (3438, 3453) | done (live, saved on Save) | Keep. |
| S45 | Alt + drag the bar: slides the platform (`so`); the drawn point stays; +/-150 m; 0.5 m steps (3438, 3454) | missing | Same, through `setStationSlide`. Shift snaps to 5 m. |
| S46 | Arrow Up and Down on a selected station: `st` +/-0.1, Shift 1, in display units; Left, Right, Delete do nothing (3534-3537) | done | Keep. Better: Alt+Left and Alt+Right slide 0.5 m (Shift 5 m); PageUp and PageDown change the platform grade by 0.5 per mille; Delete arms Remove, a second Delete within 4 s removes. |
| S8 | Double-click inside a platform: "Bend points go between platforms"; a dragged bend point pushed out to half + 3 m (3175, 3143-3147) | partial: the new point is moved out to half + 1 m without a word | Refuse with the same message; push dragged points to half + 3 m. |
| S48 | Undo and redo: Ctrl+Z, Ctrl+Shift+Z, Ctrl+Y, buttons; whole-doc snapshots, 200 deep; a drag with no change dropped; every station edit but Access undoable (3136-3140, 3480) | partial: undo works on saves only | Draft steps (0.4). Every station edit, Access and side included, is one step. |
| S49 | Autosave 1.2 s after an edit; Ctrl+S saves at once; If-Version; a conflict banner (3211, 3230-3245) | partial: Save, Ctrl+S, Enter; If-Match; the conflict banner | Keep the explicit save: the draft is the preview Ben asked for. The Save button shows the count of unsaved station edits. Lead to confirm with Ben. |
| S50 | Units m / ft on every station figure (3741) | done | Keep; cover the new rows. |

### A.5 Stations table and Removed list

| # | Old (lines) | New | Plan |
|---|---|---|---|
| S51 | Columns: type chip and name, street (else roads, else "-", full text in the title), km, rail, depth ("+n" above ground); selected row highlighted; click selects and centres (2915-2926, 3724-3725) | partial: name, level (editable), chainage | Add the type chip, street, depth and a flag dot. Keep the editable level (better than old). |
| S52 | "Removed" list with Restore. Restore puts the station back at its drawn point, centred, sg 0, stt '', at the DEFAULT level; only Undo brings Ben's old level back (3554-3566) | missing | Same list under the table, with Restore. Better: Restore takes the key out of `del` only, so Ben's level, grade and slide come back. A station removed by the old page has no level: it comes back as "level not set" (A.1) with the "Set to ground - 7.62 m" button. Seed: Line_3 Goverment Center; Line_6 Lytle Park, Greenlee. |
| S82 | Line summary "Stations N" (2877) | missing | "32 stations, 1 removed" in the sheet header. |

### A.6 Rules, numbers and station flags

| # | Old (lines) | New | Plan |
|---|---|---|---|
| S59 | Station key: name, or name#idx (718) | done: platform ids (better) | Keep. |
| S60 | Platform grade limit: Lines 1-7 and 2b 7.5, Lines 8-14 and CVG 4 per mille (ERA 1186-1192, sgMaxFor 1227) | missing | In `station.facts@1` from `literal.ERA.sgMax.*`, rule `platform.grade.limit_by_era`. |
| S61 | Station type by rules (1388-1403) | missing | Provisional port (0.2), rule `station.type.selection_else_limit`. |
| S62 | `sttFromDoc` drops a saved `stt` equal to the paint under the centre (852-861; Line_3 Aloysius lost on save) | the new import keeps it | Keep it. Better: the panel notes "same as the paint here". |
| S63 | Side or island: drives box spacing, hall height, D_HALL (8.55 or 9.15), access rule (1287) | missing | Import and select (0.1, A.3). The computed default (`platDef`) is B. |
| S64 | Approach extra and complexes, read only (1293, 494) | missing | Complexes imported (0.1); approach extra with the approach boxes (B). |
| S65 | Access rule: elevated, surface, mined (deep from `deep_from`), shallower than D_HALL (platform level, or crossunder for an island or interchange), Phase 1 end halls, Phase 2 mezzanine (full if interchange), later full; Ben wins (509-517) | missing | Port in `station.facts@1`, rules `access.type.*`. |
| S66 | Slide limit 150 m: not clamped on load, clamped on any edit (1838, 1883, 3545) | missing | Same, rule `platform.slide.limit_never_clamped`. |
| S67 | Platform curve: least-squares circle through the path every 2 m over the platform; R < 600 error, < 3000 warning; gaps 15.56^2/8R out, 5.4^2/2R in; S-curve turns of 5 degrees both ways error, 2 warning (2013-2072) | missing | Port, rules `platform.curvature.gapfill`, `platform.curvature.no_s_curve`, literals `CAR_LEN`, `END_DOOR`, `PLAT_R_*`, `DRAW`. |
| S69 | Platform grade flag, error over limit + 0.05 (2088) | missing | Flag `platform_grade_over`, fix: Ease. |
| S70 | Platform curve flag: S-curve; R < 600 without gap fillers error; with gap fillers or R < 3000 warning (2090-2098) | missing | Flags `platform_curve`, `platform_s_curve`, fix: Gap fillers. |
| S71 | Platform slide flag, error past 150.05 m (2100). Seed: Line_3 Bruckman -235; Line_6 North Avondale -230, Forest -235, Oak +236; also Line_4 Hoyes, Alliance Academy, Line_7 Bank | missing | Flag `platform_slide_over`, fix: Slide back to 150 m. |
| S72 | Platform overlap flag, error, centres closer than platform - 0.5 with different drawn points (2101) | partial: engine flag, not shown | Show the engine's `platform_overlap`; check its condition matches. |
| S73 | Access flags: crossunder note; no year warning; hall too shallow error; elevated mezzanine without clearance error; non-mezzanine on an elevated station warning; hall over a mined station error (519-526) | missing | Same six, rules `access.*`. |
| S75 (part) | Bore (TBM) selected before Phase 3; a box station deeper than the cut and cover limit (1401-1402) | missing | Both, station only, rule `station.type.selection_else_limit`. |
| S77 (part) | A box station with its roof out of the ground (2175) | missing | Flag, rule `station.type.box_roof_out_of_ground_unbuildable`. The Propose fill button is B. |
| S79 (part) | Issue list: counts, filters, centre on click, fix buttons (2928-2950, 3681-3687) | missing | Station flags in the panel (A.3) and as triangles (A.1). The line-wide issues pane is C (R54). |
| S80 (part) | Saved fields: st, sg (nonzero), so (nonzero), del, gapfill, stt (Metro, non-empty) (3213-3229) | partial: st only is edited | All of them through the model ops (0.3), plus `access`. Zero values written as removals, as the old page did. |

### A.7 Line-level station actions now

| # | Old (lines) | New | Plan |
|---|---|---|---|
| S53 | Ease all platforms (3676) | missing | Button over the stations table; one draft step. |

### A.8 Missed by this matrix, found by the parity review (23 November)

The review ran the old page (a scratch copy of the old hub) and the new sheet (a scratch copy of the seeds) side by
side, read every station card on all 16 Metro lines (436 stations) and compared them row by row, then did the edits
in both and compared what was stored.

| # | Old (lines) | Found in the new sheet | Now |
|---|---|---|---|
| S83 | The other lines in the Opening row by their short names (routeName 336): "Highland (B Highland, 1900)", "later: A Blue Ash 1985" | the route ids: "RER B highland", "RER A blueash" (34 stations) | done: the short name from the Chronology's route name |
| S84 | A docless line (Lines 10, 11, 13: 79 stations) has every station at a level from defaultAlign, so its type, depth, access and hall room are real | an unset station was read at the design rail, 0 m on a line with no design: "Deep bore (TBM): 226.7 m down", Deep station, a tube 220 m under the bar | done: read at ground - 7.62, where its dashed bar is drawn; 20 of 29 Line 10 stations now match the old card; the rest differ by defaultAlign's grade limits (B, S55 S57) |
| S85 | Ease all eases each platform three times before the next (3676, 3579) | three passes over the whole line; the line-end platforms (Towne, Beechgrove) not eased at all, their end vertex being clamped to the line | done: 31 of 31 Line 6 grades equal the old page's |
| S86 | Arrow Up and Down step 0.1 (Shift 1) in the display unit and keep the centimetres (3537): 152.02 to 152.12 | 0.1 m in feet too, rounded to 0.1 m: 152.02 became 152.1 | done, on the canvas and in the level and depth fields |
| S87 | Platform start of a station at the line's start reads 0+000 | "−0+000" (10 stations) | done |
| S88 | A selection equal to the paint over the centre shows as Rules (S62) | Ben's selection, with no word why it differs from the old card (Line 2: 7 stations, Line 3 Aloysius, Line 14 Daly) | done: the panel says "Same as the paint here: the old page showed this as Rules" |
| S89 | Names readable in the top margin; the plot 1,200 px wide at 1,600 px | the plot 490 px wide beside the map, inspector and panel; names cut at the top (64 px margin); level tags and "slid" notes running into each other and over the next bars at the whole-line view | done: the sheet takes two thirds of the width (plot about 590 px), the full 84 px top margin, tags and notes only under a bar 12 px wide or on the selected station |
| S90 | Alt + Left or Right (Back and Forward in the browser on Windows) | a press with no station selected, or on main, went to the browser | done: the sheet keeps them |
| S91 | Cover checks count the hall over the box (hallAt in the cover sampling, 2118) | the hall too shallow flag only | B, with the cover checks (I2.2) |

Values that agree on every station of the 13 lines with a saved profile: chainage, drawn point, platform range, rail
level, rail below ground, ground, street, access (Ben's 10 and the rules), opening, hall room, grade in and out,
platform curve, gaps and S-curve, platform grade, station type and its select, and the station flags (platform
grade, curve, slide, overlap, access), apart from: the S62 stations (intended), Line 2b (its doc is reframed on load,
not ported), and signs of zero ("−0.0‰" on the old card is "+0.0‰"). Edits checked in both and stored alike:
platform grade 12 and its error, Ease, rail below ground 10, point from platform start 10, Elevated (raised to
ground + 5.0), End ticket halls with its errors, Ease all.

## A. Acceptance checks

The prover runs the old page on a scratch copy (old hub on port 8775, as in the scratch folder `parity/oldhub`) and the
new hub on a scratch copy, on the same seed. "Old card" means the text of the old page's selected-station card;
"old doc" means the seed alignment's derived `stations` array. Lines 3 and 6 are checked in full (every station), with
Line 1 Winton Place (elevated) and Liberty (Ben's crossunder) as extras. Each check passes only when old and new agree,
or when the difference is one this document calls intended (marked "intended").

**Seeing**

1. For each line, the set of stations drawn (bar, name, zone) equals the old page's stations minus `del`. The sheet
   exposes its drawn marks to the test (a `marks()` hook on the bands), one per platform id.
2. At the whole-line view and at 2+000 to 6+000 on Line 6, the selected station's name is always drawn, and every
   name the old page draws is drawn.
3. For each station, the bar runs from c - half to c + half and its ends are at rail -/+ sg x half (within 0.01 m),
   equal to the old doc's c and rail and the seed's sg.
4. The drawn point triangle is at the stop's c for every station (slid or not), equal to the old doc's point_c.
5. For each station, the structure outline's type equals the old doc's `type` and the old page's
   `railProfile.typeAt(c)`. Every difference is listed with its reason (canon section, river, drive method); zero
   unexplained differences on Lines 3 and 6.
6. For each Metro station, the outline's top and bottom are rail + box top (4.6 side, 5.2 island) and rail - 1.0 for a
   box, within 0.01 m.
7. For each Metro station on all 16 lines, the access type and its source equal the old card's Access select
   ("Rules: X" or Ben's choice); Ben's 10 choices match exactly. The drawn access ranges (halls, mezzanine, passage,
   shaft) equal the old `stationAccess` ranges within 0.1 m, and they are dashed exactly where the old ones are.
8. Screenshot pairs at the same view and size for Genesee, Ross, Convention Center, Westside, Bruckman (Line 3), Bond
   Hill, North Avondale, Forest, Taft Theater, Dorchester (Line 6), Winton Place and Liberty (Line 1): the new sheet
   shows the bar, the box or tube in the type colour, the halls or crossunder or shaft with the same labels, the
   D_HALL line, and the name. Ben checks these by eye; the prover attaches them to the report.
9. An unset station (clear Ross's level in a scenario) is drawn as a dashed bar marked "level not set" (intended: the
   old page solved a level).
10. A removed station has a faint struck-through mark at its drawn point and no bar (intended addition).

**Values in the panel and table**

11. For every station, the panel's chainage, drawn point, platform range, rail level, depth and platform grade equal
    the old card's, in m and again in ft.
12. Ground at centre equals the old card's within 0.05 m where the old card shows no fill or cut.
13. Grade in and out equal the old card's within 0.05 per mille.
14. Street text equals the old card's for every station.
15. Opening text (year, phase, interchanges at opening and later) equals the old card's for every station.
16. Hall room text equals the old card's for every Metro station.
17. Platform curve: R within 1 %, the severity word, extra gap out and in within 0.1 cm, and the S-curve text equal the
    old card's; and equal to `tests/baseline/profiles/platforms.json` for all 430 records.
18. Side or island equals `station_platforms.json` for all 436 platforms.
19. The stations table's text (name, street, km, rail, depth) equals the old table's for Lines 3 and 6; the type chip
    colour equals the old chip's.
20. The Removed list on the seed: Line 3 shows Goverment Center; Line 6 shows Lytle Park and Greenlee.

**Edits** (each in the old page and in the new sheet, from the seed, then compare the saved fields)

21. Drag Genesee's bar up with Shift by about 1 m: `st` + 1.0 in both.
22. Arrow Up three times, then Shift + Arrow Up once on Bond Hill: `st` + 1.3 in both.
23. Alt + drag Genesee's bar 20 m right: `so` equal in both (0.5 m steps); the drawn point unchanged.
24. Alt + drag past 150 m: `so` = 150 in both.
25. Type 10 in "Point from platform start": `so` = half - 10, rounded 0.5, in both.
26. Point at start, Centred, Point at end: `so` = +half, 0, -half in both.
27. Type 12 in the platform grade: `sg` = 12 in both; both raise the platform grade error with the same numbers.
28. Ease the bends after 27: `sg` equal within 0.05 in both.
29. Ease all platforms on Line 6: every `sg` equal within 0.05 in both.
30. Type 10 in "Rail below ground": `st` = ground - 10 within 0.01 in both.
31. Station type Elevated on a station lower than ground + 5.0: `stt` = elevated and `st` = ground + 5.0 in both.
32. Station type back to Rules: `stt` key gone in both.
33. Access End ticket halls on a station shallower than D_HALL: the access value saved (old in params, new in
    `profile.access`), and the same "hall too shallow" error in both.
34. Gap fillers on Ross (R 333 m): `gapfill` holds Ross in both; the curve flag goes from error to warning in both.
35. Remove a station (two clicks): `del` holds its key in both; the bar is gone in both. Restore: `del` loses it in both.
    The restored level is the default in the old page and Ben's own in the new sheet (intended).
36. Double-click inside a platform: no bend point added in both; the same message.
37. Each edit in 21 to 34 is one Ctrl+Z step in the new sheet before the save; after Ctrl+Z the draft equals the seed.
    After Save, one changeset; Ctrl+Z after the save reverts it.
38. On main, where the old hub owns the profile, every station input is disabled and a drag on a bar pans (as the old
    page's view-only mode).

**Flags**

39. On the seed, the station flags of Lines 3 and 6 (station, kind, severity) equal the old page's issues of kinds
    Platform grade, Platform curve, Platform slide, Platform overlap, Access and the two station Tunnel method checks.
40. On the seed, Platform slide errors for Line_3 Bruckman; Line_6 North Avondale, Forest and Oak; Line_4 Hoyes and
    Alliance Academy; Line_7 Bank; and none elsewhere.
41. Every flag carries a rule id that is in `rules/registry.yaml`.
42. Clicking a flag triangle selects its station and centres on it (old: span at most 1,500 m).

## B. Stations, later (each needs a part that is not ported)

| # | Old (lines) | Needs | Checklist |
|---|---|---|---|
| S3 (line) | Tunnel outline and structure band along the running line, not just the platforms | the structure solver (`solveTypes` 1360-1604) | I2.2 |
| S7, S74, S64 (part) | Approach boxes: cut and cover past each platform end for max(40, sqrt(4 R shift)) + approach extra; "runs into Y" warning; "leaves the street" note (1278-1294, 1431-1447, 1547) | the solver (tube choice and shift), `approach_extra` import | I2.2 |
| S10 | Station ticks on the overview strip | the overview strip (R46) | sheet page work after A (C) |
| S21 (part), S77 (part) | Fill or cut at the station; Propose fill | the finished ground (`ground.profile`) | I2.1 |
| S23 (part), S42, S43, S47, S68, S78 | Canon: the reference level (Union Terminal), fixed levels, locks (drag refused, "Locked stretch"), modes, junction and shared-track notes, "deep in a shallow-canon section" warning | canon as data (CANON 293-323 and `rer/canon.json` as records) | I2.2 (with the level solver) |
| S39, S41 | RER: "Force whole station cut and cover"; mode buttons At grade / Underground (re-solve) | RER sections (not imported) and `defaultAlign` | slice 2 (2.2.2, 2.2.3) and I2.2 |
| S54 | Solve levels with crossings | the level solver and crossings | I2.2 |
| S55, S57 | Reset this line; default station levels for unset stations | `defaultAlign` | I2.2 |
| S56 | Fix unbuildable, Lower, Raise (stations move with the rail unless held) | the solver and `regradeDrive` as an engine proposer | I2.2, 2.1.15 |
| S61 (full) | Station type from the full solver (canon, rivers, the drive's method) | the solver | I2.2 |
| S63 (default) | The computed side or island default (`platDef` 1574-1600: island at a transfer at opening, or tubes into the box) | the solver and the Chronology | I2.2, I2.4 |
| S66 (reframe) | Platform centre kept when the route is re-pathed | `reframeDoc` | I2.2 |
| S75 (rest) | Mined station inside a cut and cover stretch; double-track bore through a mined station | the solver | I2.2 |
| S76 | Painted misfit for a station selection, with Lower, Raise, Propose fill, Clear | `paintMisfits` | I2.2 |
| S27 (full) | Opening dates, phases and segment years from the full Chronology | the Chronology import | I2.4 |
| S80 (derived), S81 | Derived `stations` and `summary` on save; GeoJSON and KMZ station features; PNG and JSON exports | the solver for `type`; the export page work | I2.2, then C |
| Ben, 23 Nov | Stations drawn in the 3D view as their own Diagram drawings, like the tunnels | `station_element`, the station workspace | 2.5.4, 2.5.6 (Hub_3D_View_Spec) |

## C. The rest of the page

Grouped from the rest-of-page inventory (R numbers). Tags: [SOLVER] structure solver, [TYPE] type at each point,
[LEVEL] level solver and reframe, [GROUND] ground layers, [RIVER] rivers, [XING] crossings and context, [CHECKS]
summary and line checks, [UI] page work only.

| Items | Old | New | Increment |
|---|---|---|---|
| R1 | Line picker with km, RER grouped; opens from the hash or the last line | done (tools round): the picker lists every section of the view with its km, by system; the sheet still opens from the URL and the map selection | done; RER groups with slice 2 |
| R2, R5 | Save button and status texts, autosave, save on close; view-only mode | partial: Save, Ctrl+S, Discard, view-only by layer; no autosave (see S49) | done enough; autosave by Ben's choice |
| R3 | Conflict banner, Keep mine / Take theirs; reframe after a Deck tie | partial: banner and three-way rebase done; reframe missing | I2.2 for reframe |
| R4 | Live sync of every doc and param | done (I2.0, always live) | done |
| R6 | Save format and derived fields; RER propagation | partial: fields kept losslessly; derived and propagation missing | I2.2; RER slice 2 |
| R7 | Tools Move, Paint, Ground (M, P, G) and cursors | done (tools round): the three tools, their keys and cursors (cell, copy, the drag shapes) | done |
| R8, R9, R10, R11 | Structure brushes, tube form brushes, shaft brush, paint drag and paint bar | done (tools round): Auto and the six types, Shaft, Twin tubes, Double-track bore, Auto tubes; the drag's preview in the brush's colour; paintRange ported (cut, round, join; Auto clears shafts); the whole solve applies it 150 ms after release | done |
| R12 | Undo and redo, 200 deep | done: draft steps (0.4); Undo and Redo buttons in the tools row; every tool edit and proposal is one step | done |
| R13 | Zoom buttons and keys, wheel, pan, pinch; at least 120 m | done (F, +, -, wheel, drag); pinch to check | done |
| R14 | Show Rail / Rail + box / Box | done (integration round): the three buttons in the header, kept for the session; checked by eye and by section_solve.spec | done |
| R15 | Units m / ft | done | done |
| R16, R17, R18, R19 | Export PNG, JSON, GeoJSON, KMZ | done (tools round): the four exports of the draft as drawn; KMZ a stored zip with doc.kml (a plain .kmz, the hub has no downloads gate) | done |
| R20 | Settings panel (31 rows), Restore defaults, Reset this line | done (tools round): the 28 Metro rows as settings.* param records, each change a param draft the whole solve previews; Restore defaults back to import:registry; Reset this line as a proposal (section.propose@1) | done; the rail solve (vertical.rail@1) reads saved params only |
| R21 | Axes, grid, k+mmm, y range taking in everything, frozen while dragging | done: the y range takes in the water, the made bed and the crossings' boxes; frozen in a drag | done |
| R22, R31, R32 | Water, made-up bed, channel over the sunk box | done (integration round): pool line, shading, name, made bed and channel from the whole solve; Line 6 at the Ohio drawn as on the old page | done |
| R23, R24 | Finished ground; REGRADED and CUT | done (integration round): the solve's finished ground against the survey; the readout now reads the finished ground with "Fill" or "Cut" from the surveyed level, as the old one did (review round) | done |
| R25, R26 | Context blocks; crossings with clearance | partial (review round): blocks, ticks, dashed lines, boxes and labels from the whole solve. Fixed in review: (1) a short crossing is red as on the old page even while the other line is not set (it was grey: every short crossing was grey, since no line is set); (2) a label that met another is placed above, below or left of it (it was left off: Line 1 at 10+042 on Line 6). Still short: crossings with Lines 10, 11 and 13 (no saved levels) get no clearance on the sheet (on Line 6: Line 13 1.9 m, Line 10 4.3 m, Line 11 0.2 m apart, all red on the old page; 7 Metro crossings with lines not set yet on the old page, 4 here). Tried in review: the sheet asking profiles.neighbour@1 itself draws them right, but the always-live test (a saved line file, then Pause and Resume) failed 4 of 4 with the hub no longer answering events, against 2 of 2 without it; reverted. Needs the neighbour views kept warm on the hub and read without planning | the docless neighbours on the hub; RER crossings with slice 2 |
| R27 | Locked stretches | done (integration round): from the canon locks (transcribed; no Metro line has a lock today) | canon as records |
| R28, R30 | Rail coloured by structure; tunnel outline | done (integration round): from the whole solve's type and structure runs; the type at every 2 m sample equals the live old page's on 14 of 16 lines (review round, server input from the records, not the goldens) | done; Line 10 and Line 2b below |
| R29, R37, R38 | Over-grade halo; grade label colours; curve grade | done (review round). Fixed in review: the grade labels ran between vertical.rail@1's vertices, not the old page's chords (2642), which run from each platform's transition end; Line 6 read "+36.5‰" where the old page reads "+42.2‰" (Towne to the first bend), and 6 of the 8 over-limit stretches on Lines 1, 3, 6, 9 and 13 (Line 6's −257.9‰ and +167.6‰ among them) were never red or amber because no label's ends met them. The chords now take the transition ends from the curves; all 8 match | done |
| R33, R34, R43 | Limit lines; unbuildable hatch; structure band | done (integration round) | done |
| R35 | Roads and the street under the line | done (integration round): streets and roads from the context record; the readout now names the street under the line at every chainage (review round) | done |
| R36 | Viaducts | done (integration round): girders, trusses and piers from the solve's spans (Line 1 on the L&N bridge) | done |
| R39 | PVI handles and curve ticks | done | done |
| R40, R51 | Drawn ground lines and the ground point card | done (tools round): drawn live from the draft; Ground's double-click, drag, arrows, Del; the card with chainage, level, over the ground below, grades meeting, rail under it, the line, Remove point and line | done |
| R41 | Hover hairline and plan dot | done (hairline); the plan dot is the map's cursor | done |
| R42, R54, R55 | Issue markers, issues list with filters and groups, every issue kind | done (tools round): the list of the whole solve's findings and the station flags, severity and kind chips, the three groups, Show, each fix | done |
| R44 | Chronology band | done (integration round): year and phase per segment from the Chronology table; fewer labels than the old page at the whole line (same segments and colours) | done |
| R45 | V.E. label | done | done |
| R46 | Overview strip | done (integration round) | done |
| R47 | Hover readout, full | partial (review round): river with water and bed; finished ground with fill or cut; rail; below or above the surface; structure top with its cover and bottom with its name; grade; type with "(painted)"; the street under the line; inside a platform the station rows of A. Missing: "with curve" beside the grade, the sunk box's roof against the bed, the viaduct's soffit and span | the three rows (the solve has no allowance per point yet) |
| R48 | Plan card | partial: the map pane | done enough |
| R49 | Editing help card | done (tools round): the "?" in the tools row, and a pointer to it in the empty card | done |
| R50 | Bend point card (chainage, level, depth, grades meeting, curve length, Remove) | done (tools round) | done |
| R52 | Line summary and type table | done (tools round): length, stations, steepest grade, deepest, highest, sumps, km and share by type, from section.solve@1 | done |
| R53 | Profile set checkbox (`ready`) | done (tools round) | done |
| R56, R57, R58, R59, R60 | Lower, Raise, Propose fill, Clear; Solve levels with crossings; Fix unbuildable; Check all lines; Paints card | done (tools round): section.propose@1 (regradeDrive, fixAll, solveCross, proposeFill, plainTypes) as previews in the draft, each one step; matches the old page on all 16 Metro lines (87 of 88 Lower or Raise, Line_2b's reframed one apart); Solve levels with crossings does not see Lines 10, 11 and 13 (see R26) | done; Lines 10, 11, 13 with R26; RER with slice 2 |
| R61 | Canon structure card | partial (tools round): canon sections and locks; the rest of the old card's notes are prose | the notes with canon as data |
| R62, R63, R64 | Pointer, double-click and keys | done (tools round): M, P, G; paint drag; Ground double-click, drag, arrows, Del; PVI and station keys as before | done; pinch to check |
| R65 | RER junction PVIs and shared stretches | missing | slice 2 (network constraints) |

### C.1 Independent review of the whole page (23 November, review round)

Method: the old page from a scratch copy of the old hub (seed equal to `hub/seed`), the new sheet on a scratch hub
rebuilt from the working tree (`crhub rebuild --working-tree`), both in Playwright at 1,600 x 1,000; and, apart from
the screens, the server's `section.solve@1` input built from the records (not the golden adapter) solved in Node and
compared with the live old page sample by sample.

**Engine against the live old page, all 16 Metro lines (input from the records).**
- Type at every 2 m sample: equal on 14 lines. Line 10 differs at 79 samples (16+244 on, the Ohio approach: no saved
  levels, its default ground misses the RER lines' drawn ground). Line 2b differs at 12 samples (trough ending 0+556 on
  the old page, 0+580 here): the old page itself gives 0+556 or 0+580 depending on which line was open before
  (its model caches leak across lines; opened after Line 1 it gives 0+580, after Line 2 0+556). Not a new-hub fault.
- Metro crossings: every clearance with a line that has saved levels equals the old page's within 0.05 m (Line 2b's
  CVG crossing 0.18 m, its reframed profile). Crossings with Lines 10, 11 and 13 have no clearance on the sheet (R26,
  still short).
- Findings: the sheet's issue list on Line 6 reads 41 errors, 32 warnings, 39 notes; the old page 41, 209 (29
  distinct: it repeats one Tunnel method warning 183 times), 39. The 3 extra distinct warnings are not traced.

**Edits.** A Shield paint from 20+013 to 20+812 on Line 6 stores `[20013, 20812, "shield"]` in both (old doc, new
profile record after Save, on a scenario layer). Station edits as in A.8.

**Drag.** A bend point dragged 60 steps on Line 6 maximised, whole line and 3.5 km: frames p50 16.7 ms, p95 33 ms, max
50 to 67 ms, no long task; the whole solve did not run during the drag and ran once after it. The old page on the same
drag: max 117 ms, two long tasks (69 and 63 ms). No stutter. The local solve reads 13 ms at 3.5 km and 25 ms at the
whole line maximised (engine 2 ms; the rest is the round trip behind the whole-line paint).

**Fixed in this round** (each with a test that fails without it):
1. Grade labels from the old page's chords (transition ends), so the figures and the over-limit colours match (R29,
   R37): `app/test/unit/sheet_drawing.test.ts`.
2. A short crossing red while the other line is not set (R26): `app/test/unit/sheet_solved.test.ts`.
3. A clearance label that meets another moves above, below or left of it (R26): `sheet_solved.test.ts`.
4. The readout between stations (R47): `sheet_solved.test.ts`.
5. The engine suite's own report files (`engine/test/port/report/`) are left out of Biome, so Biome passes after
   the engine suite runs (it rewrote `checks.json` in a format Biome rejects).

**Still short.**
- Crossings with Lines 10, 11 and 13 (no saved levels): no clearance on the sheet (R26). Asking
  `profiles.neighbour@1` from the sheet was tried and reverted: it broke the always-live line file test (Pause and
  Resume, 4 of 4 runs, the hub stopped answering events). The hub should keep these views warm and the solve input
  read them without planning a job.
- RER: crossings, ticks and their checks (Line 6 shows 14 crossings where the old page has 21), junctions, shared
  stretches, modes (slice 2).
- R47: "with curve" in the readout, the sunk box's roof against the bed, the viaduct's soffit and span.
- R61: the canon card's notes (canon as records).
- Line 10's 160 m on the Ohio approach and the level solver's ground for Lines 10, 11 and 13 (RER drawn ground).
- The station panel's type from `station.facts@1` can differ from the band's (the full solve's), as reported.
- Pinch zoom unchecked (R13).
- The 16 ms local re-solve budget (`sheet.spec.ts` PVI edit, `stations.spec.ts` keys) failed in both full Playwright
  runs of this round (46.6 and 32.4 ms; 20.2 and 17.4 ms) and 6 of 6 times alone, with and without this round's
  drawing changes alike (18 to 58 ms; the engine itself 2 to 7 ms). The time is the main thread busy between the
  request and the answer, most likely the whole solve's answer and redraw landing during the typing; the integration
  round saw the same with the whole solve off (3 of 5). Not fixed here.
