# Platform and track design: brief

Written 2026-10-26, for a later session (here or in Claude Code) to carry on. It covers:

- how the Mill Creek Deck draws platforms and tracks;
- what the Deck holds today at Fountain Square, Union Terminal and Norwood Central;
- where lines share tracks;
- where the design conflicts with the other sources;
- how the Deck is read together with the Rail Profiles page into a 3D model of the system (section 10). That section covers the north viaduct, the drops to the underground platforms and the TRI interlining in detail.

Ben's project rules apply throughout: fact tracker first, push back when something is unrealistic, plain language.

The data behind it is in the folder `design/platform_track/` (repo `peckbe899/cincinnati_rail`, once pushed). It is a separate package from the Fountain Square model (`stations/fountain_square/`) and the 3D tool brief (`claude/Station_3D_Brief.md`).

## Sources and how they were read

- **Mill Creek Deck** (https://claude.ai/artifact/L81dVQSV8THSWai2LhZhcv), published version of 2026-10-26 15:36 UTC, with Ben's saved layout `deck/layout` (version 2461, last saved 15:25 UTC: 66 station settings, 12 line edits).

- The page was run headless on its own published files, with a stand-in database serving that layout. Every platform and track pair below comes from the page's own functions (`stopType`, `stopBands`, `stopRings`, `trackPair`, `hAt`), so it matches what the page draws. Nothing was written back to the page.

- **Rail Profiles** (https://claude.ai/artifact/A5XH4264dpWHdPdDKZgDsG): saved alignments for Lines 1, 2, 3, 4, 5, 6, 8, CVG Express, RER-1 and RER-2. Lines 7, 9 to 14 and RER-3 to RER-5 have none.

- Deck data files: `context.json` (lines, stations, generated platforms and tracks, design constants), `tracks.json` (CUT and the north trunk), `norwood.json` (Norwood Central sketch v13).

- Logs: `claude/Relief_Maps_Log.md` (10j, 10l, 10p, 10r, 10z, 10zzy), `claude/North_Viaduct_Plan.md`, `claude/Norwood_Central_Log.md`, `claude/Station_Area_Maps_Log.md` (4.11, Fountain Square).

## 1. The rules the Deck draws with

All widths and track centres are drawing values, not canon, except where marked as Ben's.

| System | Platform length | Island | Side platform | Track centres between stations | Rail to platform edge |
|---|---|---|---|---|---|
| Metro | 121.92 m, 400 ft (Ben, 23 October) | 8.0 m | 4.0 m | bored 8.0 m (two single-track tubes); box, trough, at grade, elevated 3.9 m (one double-track structure) (Ben, 26 October) | 1.45 m |
| TRI / RER | 204.2 m, 670 ft (Ben, 5 October) | 11.0 m | 6.0 m | 4.5 m everywhere | 1.75 m |
| CVG Express (airside) | 200 m | 10.0 m | 6.0 m | 4.5 m | 1.6 m |
| APEx and ORR, CUT and Norwood heritage platforms | 488 m APEx, 305 m ORR, lower level and Transvalley | 8.3 m | (APEx side platforms at Norwood are the old 8.3 m islands) | 11.68 m across an island, 3.97 m back to back at CUT, 4.5 m at Norwood | 1.68 m |
| CUT lower level | 305 m | 11.0 m | none | 15.5 m across an island, 4.5 m back to back | 2.25 m |
| North trunk viaduct | | | | 4.5 m between neighbouring tracks; TRI islands 14.4 m between track centres | deck edge 4.2 m outside the outer track |

How it works on the page:

- **Platform type by default.** Lines 1 to 7 get islands and Lines 8 to 14 side platforms (log 10j.4, 9 October: founding-era twin tubes, later-era double-track bores). TRI stops get an island when the generated layout has one platform polygon, side platforms when it has two. Ben's per-station setting overrides either.

- **Track spacing by construction (Metro only).** `context.json` holds samples every 20 m along each Metro line, marked bored or not. They come from the Profiles editor's structure types (its saved profiles, else its defaults) at the time `context.json` was built. Runs under 60 m are merged and each change is eased over 40 m. TRI has no such rule.

- **At a platform.** An island pushes its tracks apart to clear it (Metro: to ±5.45 m from the line, so 10.9 m apart; TRI: to ±7.25 m, 14.5 m apart), over 40 m tapers at each end. That happens even on bored Metro lines: the tubes run 8.0 m apart, and an 8.0 m island with 1.45 m edges needs 10.9 m. Side platforms sit outside the tracks at whatever spacing the construction gives.

- **Drawn from settings.** A line is redrawn from these rules as soon as the line or any station on it is edited. Otherwise the generated platforms and tracks in `context.json` are drawn. Today 15 Metro pieces and 9 TRI and CVG Express lines are drawn from settings, which covers every line through the basin.

- **Sliding.** A platform may slide up to 150 m either way from its station point (Ben, 24 October).

Cross-section widths that follow from these values (outer platform edge to outer platform edge, walls not included):

| Metro station | Track centres | Across the platforms |
|---|---|---|
| Side platforms on a box line | 3.9 m | 14.8 m |
| Side platforms on twin tubes | 8.0 m | 18.9 m |
| Island, either construction | 10.9 m | 8.0 m island, 13.8 m between the outer rails' edges |

The Profiles editor gives the structure heights: box 1.0 m below and 4.6 m above the rail; twin tube 0.68 m and 4.08 m, 4.76 m outside diameter (8.0 m centres leave 3.24 m of ground between the tubes); double-track bore 3.2 m and 5.8 m, 9.0 m outside diameter. Neither editor sets a box's width or a TRI tube's diameter.

## 2. Platform types as saved

Metro stops on live stations, by era of the line and the construction at the platform centre (407 in all):

| Lines | Island on a box | Island on a bored stretch | Side on a box | Side on a bored stretch |
|---|---|---|---|---|
| 1 to 7 | 166 | 32 | 20 | 6 |
| 8 to 14 | 1 | 0 | 163 | 19 |

Check: 166 + 32 + 20 + 6 + 1 + 163 + 19 = 407.

- Every side platform on Lines 1 to 7 (26) is Ben's setting: 8th (4); Camp Washington, Chinatown-Gest, Courthouse, Crosley East, Sassafras, Wilstach (5); Central Ave (1 and 3); Draper, Findlay, Hopple, Marshall, Music Hall, Warner (3); Eggleston (5 and 7); Fountain Square, Holy Trinity, Pennsylvania Station, Plum (1); Kenyon (7); Lincoln Court (1 and 5); Taft Theater (1 and 6). Lytle Park (6) is also set to side, on a deleted station.

- His one island on Lines 8 to 14 is Wayne (13).

- TRI: 124 islands, plus Ben's side platforms at Music Hall/Washington (B), the generated three-track South Cumminsville (A, with R5 on the centre track) and the fixed Union Terminal box (three islands). CVG Express: five airside stations, side platforms.

- Deleted Metro stations: Baltimore, Freedom Center, Lytle Park, Mound, Sherman, Ziegler.

The full list, with offsets, widths and track spacing for every stop, is `data/stations_platforms.csv`.

## 3. Fountain Square

Positions in the Fountain Square model's frame (metres; u east along the cross streets, v north up Vine, origin the KMZ reference point). Plan: `plans/fountain_square.png`.

| Line | Deck as saved | Fountain Square model | Profiles (rail, depth, structure) |
|---|---|---|---|
| Metro 1 | side, 2 × 4.0 m (Ben's setting); v −57.9, u 28.4 to 150.2 | side, 2 × 5.45 m; v −57.5, u −7.8 to 144.6 (500 ft) | 160.9 m, 7.2 m, cut and cover |
| Metro 2 | island 8.1 m (generated), 2.9 m off its own line, so its tracks sit at +2.6 and −8.4 m; u −48.0, v −118.5 to 3.7 | side, 2 × 5.45 m; u −54.5, v −108.9 to 43.5 | 153.4 m, 14.27 m, cut and cover |
| Metro 7 | island 8.1 m (generated); v 82.4, u −111.6 to 10.2 | side, 2 × 5.45 m; v 84.25, u −129.6 to 22.8 | no saved profile |
| TRI A/D | one island 11 m, two tracks at ±7.24 m; v 7.6 to 20.3, u −196.9 to 7.1 (slid 12 m west by Ben) | two islands 10 m, four tracks (v −20.15, −5.65, 6.85, 21.35): westbound north, eastbound south, A outer and D inner; u −185.1 to 19.1 | RER-1 156.56 m, 12 m, cut and cover |
| TRI B | island 11 m; u 82.6 to 93.9, v 11.6 to 216.3 (slid 11 m north by Ben) | island 12 m; u 81 to 93, v 22.7 to 226.9 | RER-2 140.59 m, 27.51 m, deep |

- TRI A and D share one pair from Union Terminal through City Hall and Fountain Square. They part about 470 m east of the A/D platform centre (E 715,467, N 4,331,119), A for the Basin Crossover Tunnel and D for Newport.

- The model's four A/D tracks come from the depth order settled with Ben on 4 October ("TRI A/D on four tracks") and his A/D platform KMZs of 5 October. The Deck still draws two.

- The Deck's A/D island lies on the model's westbound island, 12 m further west.

- Metro 2 and 7 are islands in the Deck only because the 10j.4 default was never overridden there. Ben has set 26 other basin stations on Lines 1 to 7 to side.

## 4. Union Terminal (CUT)

Plan: `plans/cut.png`. Levels, top down:

- **Level 0:** APEx rail 160.3 m, on the arch viaduct (the real 1933 platforms were 156.3 m).
- **Level −1:** the Hartwell concourse, at street level under the viaduct.
- **Level −2:** lower platforms, rail 144.0 m.
- **Below:** TRI and Metro.

### 4.1 APEx field (level 0)

- 16 platform tracks in 8 islands, 488 m (1,600 ft), from the 1931 HABS plot plan: islands 8.3 m, 11.68 m across an island, 3.97 m back to back.

- Tracks are numbered 1 at the building (east) to 14 (west). Platform M, CVG Express tracks 15 and 16 (the 1933 mail platform), is drawn east of track 1. The 10l.1 draft had 15 and 16 on the west side.

- The freight passing track runs 4.0 m west of track 14, throat to throat.

- Throats, as drawn (speeds are the page's drawing values):
  - a 1:15 ladder of 5 crossovers at each end (80 km/h);
  - 6 turnouts at 1:12 at each end taking the platform tracks onto the approach (60 km/h);
  - track 14 to the passing track at 1:9 (40 km/h);
  - the transfer track from the passing track onto the intercity east track at 1:12;
  - one 1:12 crossover on the intercity pair south of the transfer;
  - the Cardinal branch east along the river: 2 crossovers at 1:46 east of the river junction and 2 at the Cardinal/Floridian junction west (160 km/h).

- North approach: tracks 1 and 2 are Indianapolis, 3 and 4 Dayton, 5 and 6 Norwood. The only two crossovers on the north trunk are on the Dayton pair, at 1:46.

- The CVG Express leaves platform M by its own south throat, crosses the Cardinal pair at grade south of W 8th, and has its own span beside the APEx bridge.

### 4.2 Lower level (−2)

- 8 through tracks, A to H, in 4 islands of 11.0 m, 305 m long (1,000 ft). They lie at E 712,745 to 712,821, N 4,331,738 to 4,332,042, centred under the APEx field.

- South end:
  - A to D join the Cincinnati Southern (intercity) pair, which climbs 1.71% to W 8th (150.9 m, street humped 5 m), then 2.92% onto the TRIMET CS viaduct and the CS bridge at 164.0 m;
  - E to H join the C&O pair: level at 144 m under Gest, W 8th and W 6th, then 2.12% to the C&O viaduct at 160.4 m.

- North end: every lower track reaches both north pairs (ORR/Transvalley west and east) through the fans. The pairs dive at 2.72% between Bank (160.1 m) and Findlay (150.2 m).

### 4.3 TRI under CUT

- **The box.** The Union Terminal TRI box is at E 713,157, about 370 m east of the field's centre, heading −3.75°. It has three 11 m islands, 204.2 m long, set out like Châtelet-Les Halles (log 10r.10):

| From the north | Track or island | Offset from the box axis |
|---|---|---|
| A westbound | track | +26.25 m |
| North island (A and B westbound) | island | +19.0 m |
| B westbound | track | +11.75 m |
| D westbound | track | +7.25 m |
| Centre island (D) | island | 0 |
| D eastbound | track | −7.25 m |
| B eastbound | track | −11.75 m |
| South island (B and A eastbound) | island | −19.0 m |
| A eastbound | track | −26.25 m |

- **Directions.** A and B change cross-platform in the same direction; D has the centre island. The box is 52.5 m between the outer tracks.

- **From the west.** B and D arrive as one bored pair from Western, on a direct line with a 250 m radius bend onto the box axis 330 m west of its centre. B takes the line tracks into the box, and D leaves them at a turnout.

- **TRI A from the west** comes from Evans, at yard level (147.5 m under W Liberty), then falls 1.8% to 135.9 m to pass under the lower level.

- **East of the box:**
  - D joins A's tracks: A westbound leaves D westbound 330 m out, and A eastbound joins D eastbound 470 m out. A and D then share one pair to City Hall.
  - B leaves on its own pair, north of the A/D trunk.

- **Crossings,** all at separate levels:
  - west: A westbound across the B/D pair, about 280 m beyond the platforms;
  - east: A westbound across B westbound (292 m), B eastbound across D eastbound (352 m), and A/D westbound across B eastbound (390 m). The B pair changes level once to make these.

- **Level rule** (Ben, 10l.26): TRI A runs at or below 135.9 m under the lower level. B/D may share A's level in the box or sit above it.

- **In plan,** A and B/D pass 56 to 58 m under the lower level and 104 to 109 m under the APEx tracks, at about N 4,331,880.

- **TRI E** has its own island station at E 712,984, 11 m wide, heading 183.5°.

### 4.4 Metro at CUT

Metro at CUT runs below the lower level (staged for the tracker).

| Line | Platform | Structure at the platform | Notes |
|---|---|---|---|
| 5 | island | box | slid 50 m by Ben |
| 7 | island | box | runs 324 m under the east edge of the APEx field (platform M and tracks 1 and 15) |
| 8 | side | box | 72 m west of the station point |
| 10 | side | box | 71 m east of the station point |

- Lines 8 and 10 run east-west at about N 4,331,783. They pass 56 m under the lower level and about 104 m under the APEx tracks.

- The log's separation under the lower level (6.1 m rail to rail for Metro, 10l.3) puts Lines 8 and 10 at or below 137.9 m there.

## 5. Norwood Central

Plans: `plans/norwood_central.png` (true plan) and `plans/norwood_central_tracks.png` (track diagram, offsets stretched 4 times).

- **Frame.** s is the Norwood frame chainage; the APEx platform centre is at s 4,682 and the heritage platforms and concourse centre at s 4,697.5.

- **Level.** The platforms are in a cut, with their roofs at street level and the concourse above them (Baltimore Penn rather than New Haven). Rail is about 178 m (approximate, from the ground data).

### 5.1 Surface tracks (sketch v13)

Offsets from the APEx through track T7 at the platform centre, north positive:

| Track or platform | Offset | Use |
|---|---|---|
| Bay B2 | −65.5 m | west-facing bay |
| Bays island | −63.8 to −55.5 m | heritage island, 305 m, buffers at the east end |
| Bay B1 | −53.8 m | |
| ORR T1 | −49.3 m | Norwood-Oakley Jct island, south face (R1 to R3, L71) |
| ORR 1-2 island | −47.7 to −39.3 m | 305 m |
| ORR T2 | −37.7 m | north face |
| ORR T3 | −33.2 m | X1 / L75 island, south face |
| ORR 3-4 island | −31.5 to −23.2 m | 305 m |
| ORR T4 | −21.5 m | north face |
| APEx S side platform | −19.5 to −11.2 m | 488 m (old island, 1,600 ft) |
| APEx T5 | −9.5 m | platform track |
| APEx T6 | −4.5 m | through track |
| APEx T7 | 0 | through track |
| APEx T8 | +5.0 m | platform track |
| APEx N side platform | +6.7 to +15.0 m | 488 m |
| Transvalley T9 | +17.0 m | |
| TV island | +18.7 to +27.0 m | 305 m |
| Transvalley T10 | +28.7 m | |

- **Spacing.** 11.68 m across each island and 4.5 m between neighbouring pairs, as at CUT's heritage platforms. Each APEx platform track is 5.0 m from its through track. The ORR T4 and Transvalley T9 tracks pass 2.0 m from the back of the APEx side platforms, which have screen doors (X1 never uses them).

- **West of the station** there are 6 tracks (ORR T2 and T4, APEx T6 and T7, Transvalley T9 and T10), with 8.25 m gaps between the groups.

- **East of the station** there are 8 tracks besides the Waynesville pair: ORR 4, APEx 2, Hamilton 2.

### 5.2 Turnouts and crossings

| Where (frame s) | What |
|---|---|
| 4,300 and 5,100 | APEx T5 and T8 leave and rejoin T6 and T7: 138 m beyond the west platform end and 174 m beyond the east end. They reach 2 m apart 62 m and 76 m from the switch |
| 4,300 | ORR T3 leaves T4, and T1 leaves T2 |
| 4,285 and 4,295 | Bays B2 and B1 leave T2 |
| 4,850 | Transvalley W1 (Waynesville) leaves T9 |
| about 4,975 | W2 leaves T10's line |
| 5,051 | the one diamond: W1 across Hamilton T10 |

- **No crossovers are drawn anywhere in the station.** As drawn:
  - island 3-4 can only be reached from T4, and island 1-2 and the bays only from T2;
  - a bay train has to leave on the track it came in on;
  - APEx trains can't change between T6 and T7;
  - the Transvalley pair has no crossover either.

- **On the trunk,** the Norwood APEx pair and both ORR/TV pairs have no crossovers. Log 10zzy.35 (25 October) said one set each on the Dayton and Norwood pairs; the 26 October install put both on the Dayton pair.

### 5.3 The Norwood branch into the station (North Viaduct Plan, Versions 129 and 130)

- Four tracks at 4.5 m run to the Transvalley junction, 30 m east of Reading Road (frame s 3,060).

- The Transvalley peels off to the south, and its inbound track crosses ORR outbound on the level.

- It then crosses over ORR and APEx at ground on one pair of 800 m curves, 7.3 m or more clear between s 3,460 and 3,573, on its own bridge (s 3,431 to 3,590). It lands north onto T10 and T9 by s 3,687.

- ORR takes one S-curve (s 3,650 to 3,900) into the 8.25 m gap.

- ORR and APEx fall 2% from s 3,220 to about 170.0 m, then climb about 1.4% to the platforms.

- Transcontinental east of the station: from the east end of the APEx through tracks (s 5,298), on one 754 m curve onto the KMZ line.

### 5.4 Below the platforms

| Level | What | In the Deck |
|---|---|---|
| Platform level | Metro 3 terminus (Ben, 24 October) | island, box, slid 3 m |
| −1 | passage from Metro 4 to TRI A along the station axis, with lifts and stairs up to the concourse | (not a line) |
| −2 | Metro 4 terminus | island; the Deck reads its terminus as a bored stretch, but Profiles saves a cut-and-cover station 7.62 m deep (rail 178.5 m) |
| −3 | Metro 14 | side platforms, generated |
| −3 | TRI A | island 11 m, slid 32 m by Ben |
| −4 | TRI E, deep bore, built last | island 11 m, between the old main tunnel line and TRI A |

- **The Waynesville pair** (Transvalley north) runs underground once past the station junction. It straddles TRI A, 4.0 to 5.0 m from its tracks, up to the TRI/TV meet (frame s 5,233, o +391). It crosses over TRI A once, at the box's north-east corner.

## 6. Where lines share tracks

| Stretch | Lines | Arrangement |
|---|---|---|
| Western to Union Terminal | TRI B, D | one bored pair; B on the line tracks into the box, D to the centre island |
| Union Terminal to Fountain Square, and about 470 m on | TRI A, D | one pair after D joins A east of the box; four tracks at Fountain Square in the model, two in the Deck |
| North trunk, Camp Washington | TRI B, D | D leaves B at s 3,200 to 3,420, inward between the B tracks (no crossing), and climbs 2.5% to the Indianapolis deck |
| CUT approach, tracks 1 to 6 | APEx Indianapolis, Dayton, Norwood | one pair each; the two crossovers are on the Dayton pair |
| North trunk, west pair | ORR X2, R5 | R5 leaves at s 3,991; R5 northbound crosses the pair's southbound track on the level |
| North trunk, east pair | ORR, Transvalley | shared to the Transvalley junction near Reading Road; there Transvalley inbound crosses ORR outbound on the level |
| After Mitchell | ORR X2 | X2 turns out east (s 7,949 to 8,149); X2 southbound crosses ORR northbound on the level |
| CUT lower level | intercity, Transvalley, ORR | A to D to the CS pair, E to H to the C&O pair, all eight to the north pairs |
| Norwood Central | APEx and ORR | separate: ORR never uses APEx tracks, and X1 never uses APEx platforms (Ben, 23 October) |
| Norwood Central east | Transvalley Hamilton, Waynesville | double junction, one diamond (s 5,051) |

Flat crossings in the design:

- R5 at s 3,991;
- the Transvalley junction near Reading Road;
- X2 after Mitchell;
- the Waynesville diamond at Norwood;
- the CVG Express across the Cardinal pair south of W 8th.

## 7. Conflicts and gaps found

1. **Bored Metro on Lines 8 to 14.** The Deck now draws every bored stretch as two tubes 8.0 m apart (26 October). The Profiles editor still sizes Lines 8 to 14 shield as one 9.0 m double-track bore, from the era rule (10j.4 and 10j.5, 9 October). 19 stops on Lines 8 to 14 sit on bored stretches, 14 of them drawn from settings. The two editors disagree on width and depth there.

2. **TRI spacing ignores construction.** The Deck uses 4.5 m everywhere. But the B/D twin bores on the north trunk are 14.4 m apart, and the Fountain Square model has separate A/D caverns. A 3D model needs real tube positions.

3. **Fountain Square, A/D tracks.** Two tracks and one island in the Deck, against four tracks and two islands in the model.

4. **Fountain Square, Metro 2 and 7.** Islands in the Deck, against side platforms in the model. The Deck's Metro 2 island is also 2.9 m off its line.

5. **Platform lengths.**
   - Metro: 400 ft in both editors, 500 ft in the Fountain Square model.
   - TRI: 204.2 m in the Deck, 200 m in Profiles.
   - CVG Express: 200 m in the Deck, 204.216 m in Profiles.
   - The Deck's own note still reads "Platform lengths are canon (Ben, 2026-10-05)".

6. **Levels at CUT.**
   - Profiles saves RER-1 at 142.0 m at Union Terminal (16 October), above the 135.9 m limit; RER-2 (135.7 m) fits.
   - Line 8 is saved at 143.8 m at Union Terminal, against 137.9 m or lower where it passes under the lower level.
   - Lines 7 and 10 have no saved profile.

7. **Levels at Fountain Square.** RER-1's box (155.56 to 163.16 m) overlaps Line 2's (152.4 to 158.0 m) by 2.44 m where A/D crosses Vine (also in the 3D brief).

8. **Norwood has no crossovers** in any throat, and neither does the trunk's Norwood pair (5.2).

9. **A stale construction snapshot.** The bored-or-box samples in `context.json` are a snapshot taken before the page was published at 15:36 UTC. Line 1's profile was saved again at 17:25 UTC and Line 6's at 16:22 UTC, so their spacing may be out of date until `context.json` is rebuilt.

10. **Generated islands off their line.**
    - Dent and Monfort Heights (TRI D, outside the plan window) are islands 8 to 9 m off the line, with both tracks on one side, so only one track can reach them.
    - The step-out islands on TRI B north of Mitchell (Ivorydale, Elmwood Place, Paddock, Aviation) are off-centre by design.

11. **A gap in the APEx north throat.** `tracks.json` has no APEx running tracks for 440 m between the end of the north throat tracks (N 4,332,400) and the start of the approach tracks (N 4,332,842). Only the five 1:15 ladder crossovers are there. Checked on the page at 4 px/m.

12. **The Profiles page is on the old CUT basis.** Its `rer/canon.json` fixes TRI A, B, D and E at 142.0 m at Union Terminal, "12 m below the 154.0 m track level", and has B and D at yard level under the deck. The Deck has APEx at 160.3 m, the lower level at 144 m, TRI A at or below 135.9 m, and B and D on the north viaduct (165 to 174 m). Section 10 lists the differences.

13. **Norwood's level stack against Profiles.**
    - Metro 4 is saved at 178.5 m at Norwood Central (6 October). That is the level of the surface platforms (about 178 m), where the 23 October rulings put Metro 4 at −2.
    - Metro 14 is at 180.2 m on the defaults; the rulings put it at −3.
    - TRI E is at grade (190.9 m) in `rer/canon.json`; the rulings put it at −4, in a deep bore.

## 8. Decisions for Ben

| # | Decision | Options | Deciding factors |
|---|---|---|---|
| 1 | Bored Metro on Lines 8 to 14 | A: twin tubes 8.0 m, as the Deck now draws. B: one 9.0 m double-track bore, 3.9 m centres, as Profiles and 10j.4 | Whether the 26 October rule was meant for every line; B gives side platforms with no track spreading, A gives islands with little; the editors' heights differ (twin tube 0.68 / 4.08 m, bore 3.2 / 5.8 m) |
| 2 | TRI spacing | A: 4.5 m everywhere. B: by construction, like the Metro (box 4.5 m; twin bores wider, 14.4 m on the north trunk) | Needed for 3D and for the Fountain Square caverns |
| 3 | Fountain Square A/D | A: two tracks, one island (Deck). B: four tracks, two islands (model, 4 October) | Cross-platform A and D by direction; the Deck has to be brought into line with whichever stands |
| 4 | Fountain Square Metro 2 and 7 | A: island (Deck default). B: side (model, and Ben's other basin settings) | Ben has set 26 basin stations on Lines 1 to 7 to side |
| 5 | Norwood crossovers | A: none, as drawn. B: add ORR T2 to T4 at the west throat, APEx T6 to T7 at both ends, Transvalley T9 to T10 at the west end | Under A, each ORR island and the bays are reached from one direction only |
| 6 | CUT levels | Re-solve RER-1 to 135.9 m or lower at Union Terminal, and Line 8 to 137.9 m or lower under the lower level (Line 10 likewise once profiled) | Both are Profiles edits; the Deck already draws TRI A at 135.9 m |
| 7 | Lengths | Profiles TRI to 204.2 m; Deck CVG Express to 204.216 m; the Fountain Square model to 400 ft | Settled canon (Ben, 23 October; TRI 5 October) |
| 8 | Levels at CUT and on the north trunk | A: the Deck's marks stand, and the Profiles page is brought onto the arch-viaduct basis and the North Viaduct routes. B: the Profiles page stands, and the Deck's marks are revised | The Deck's are the later rulings (10l.19 to 26 October); the 3D model uses them for now (section 10) |

## 9. The folder: `design/platform_track/`

| Path | What |
|---|---|
| `README.md` | what is here and how to re-run it |
| `Platform_Track_Design_Brief.md` | this brief |
| `extract/deck_headless.py`, `extract/extract.js` | runs the Deck page headless on its published files and a saved layout, and reads the design out through the page's functions |
| `extract/profiles_headless.py` | runs the Rail Profiles page headless on its published files and saved alignments, and samples every line's rail level and structure |
| `extract/summarise.py` | turns the Deck extract into the tables, area files and plans |
| `extract/combine3d.py` | puts a rail level on every Deck track (section 10) |
| `extract/render3d.py` | the long section, cross-sections and 3D views |
| `data/deck_extract.json` | the raw Deck extract: every station stop, every line's bored runs, every drawn track |
| `data/profiles_extract.json` | the raw Profiles extract: rail level and structure every 5 m on all 21 lines |
| `data/stations_platforms.csv` | one row per stop (546), with type, widths, offsets, track spacing, construction and Ben's settings |
| `data/lines.csv` | one row per line piece (117), with bored and box lengths |
| `data/areas/*.geojson` | Fountain Square, CUT and Norwood Central: platforms, drawn tracks, the CUT layers from `tracks.json`, the Norwood layer; UTM 16N (EPSG:32616) |
| `data/system3d.geojson` | every track with x, y and rail level z (UTM 16N, metres NAVD88), and where each level came from |
| `data/platforms3d.csv` | the rail level at each platform centre and its source |
| `data/conflicts.csv` | every place where two sources give different levels for one track |
| `data/coverage.json` | track length and the length with a level, per track |
| `plans/*.png` | the plans in sections 3 to 5, and the drawings in section 10 |

## 10. Reading the Deck with the Profiles page: a 3D model

### How it works

1. **Read the Deck** (`deck_headless.py`). It runs the page on its published files and the saved layout, and reads through the page's own functions:
   - every station stop: type, widths, offset, track spacing;
   - every line's bored and box runs;
   - every drawn track pair: `trackPair` for lines drawn from settings, the generated tracks otherwise.

   This gives the plan only. The Deck holds no rail level per point.

2. **Read the Profiles page the same way** (`profiles_headless.py`), with its saved alignments. It switches through all 21 lines and samples `railAt` and `typeAt` every 5 m. Checked against the saved station levels: Line 1 at Fountain Square 160.9 m, RER-2 at Fountain Square 140.59 m, RER-1 at Union Terminal 142.0 m, all as saved.

3. **Put a level on every Deck track** (`combine3d.py`):
   - **Metro, the five TRI core lines and the CVG Express:** the Profiles level at the point's chainage, found by projecting the point onto the Profiles line (within 30 m). Where two Profiles lines run on one Deck pair (A/D, B/D), both are read and compared.
   - **What the Profiles page doesn't cover:** the Deck's own levels. These are:
     - the level marks in `tracks.json` and `context.json`, each a located level;
     - the CUT summary (APEx 160.3 m; the street levels of the viaduct; the lower level at 144 m; the dive figures);
     - the intercity and C&O profiles, which `tracks.json` already carries in 3D.

     A track takes the marks of its group that lie near it and is interpolated along its length. Nothing is extrapolated, and gaps over 2 km are left open.
   - **TRI stretches the Profiles page routes differently** (B/D south of Straight): its station levels, used as anchors at the Deck's platform centres.
   - **Norwood Central's surface tracks:** about 178 m, the only level given.

4. **Draw it** (`render3d.py`).

| Where | Level from | Why |
|---|---|---|
| Metro, TRI through the basin, CVG airside | Profiles page | it sets depths |
| APEx, lower level, ORR and Transvalley, intercity, C&O, R5 | Deck marks | the Profiles page has no such lines |
| TRI A west of CUT; B/D and B on the north trunk; D on the Indianapolis deck; the CVG Express at platform M | Deck marks, where the Deck gives one | the Deck's are the later rulings (10l.19 to the North Viaduct Plan); the Profiles page is still on the old basis (section 7, item 12) |

### The north viaduct

Drawings: `plans/north_trunk_long_section.png` and `plans/north_viaduct_sections.png`.

- **Order.** At Camp Washington, west to east: ORR/TV west pair, B/D, Indianapolis, APEx Dayton and Norwood, ORR/TV east pair. All are at about 165 m, as in the North Viaduct Plan.

- **APEx levels:**
  - 160.3 m at the platforms;
  - deck + 6.5 m over the streets, 161.1 m at W Liberty rising to 164.5 m at Marshall;
  - 166.6 m at the deck tip;
  - 0.28% down to 162.5 m at Ludlow.

- **Indianapolis and D** climb 2.5% to 174.3 m. At Arlington, D (174.3 m) is 8 m over R5 (166.4 m) at the west edge, and B's island is at 165.9 m.

### The drops to the underground platforms

- **Lower pairs:** 160.1 m over Bank, then 2.72% down to 150.2 m at the Findlay portals, 146.0 m at Sherman, and 0.5% to the lower platforms at 144.0 m.

- **B/D:**
  - from 165.2 m at Camp Washington (on the viaduct), down 3.3% to the Straight box at 151.64 m;
  - bored south of Straight, to Western at 138.5 m (the Profiles station level) and on to the Union Terminal box.

- **TRI A:** 135.9 m under the lower level (Deck), 147.5 m at Evans, 159.3 m at the fork.

- **Intercity pair:** from 144 m, 1.71% up to W 8th (150.9 m), then 2.92% to 164.0 m at the CS bridge.

- **C&O pair:** from 144 m to 160.4 m.

- **3D views** (`plans/cut_3d.png`, `plans/north_trunk_3d.png`, `plans/fountain_square_3d.png`): heights stretched 6 to 8 times; the cross-sections are true to scale.

### TRI interlining, checked level against level

- **A and D, Union Terminal to Fountain Square.** RER-1 and RER-4 agree: median difference 0.03 m, within 2.6 m for 95% of the shared points. The largest, 6.6 m, is at the split east of Fountain Square, where the two lines part.

- **B and D, Western to Union Terminal.** RER-2 and RER-4 disagree by up to 9.1 m near E 712,665, N 4,333,000 (B 138.2 m, D 147.3 m). RER-4 has no saved profile, so it is on the page's defaults.

- **The Union Terminal box.** The Profiles page has TRI A, D and E at 142.0 m there. The Deck has TRI A at or below 135.9 m under the lower level. RER-2's 135.7 m fits.

- **North trunk.** The Profiles page has B and D 14 to 28 m below the Deck: at yard level, against the viaduct and the Indianapolis deck.

### Coverage

| Lines | Track length | With a level |
|---|---|---|
| Metro | 704 km | 100% |
| TRI as drawn in the Deck | 628 km | 39% (the core and the north trunk; the KMZ pieces out to the region's edge have none) |
| APEx | 263 km | 30% (the CUT area and the north trunk; the regional lines have none) |
| Lower level, ORR, Transvalley, intercity, C&O | 88 km | 40% |
| Norwood Central surface | 13 km | 95% |
| CVG Express airside | 17 km | 100% |

- No level yet for Metro 3 and TRI A at Norwood Central: the Deck's routes there are Ben's later lines, more than 30 m from the Profiles lines.

- No level for the APEx north throat gap (section 7, item 11).

- **Interpolated levels.** Where marks are far apart the level is linear between them. For example, the lower pairs between Bank and Marshall sit up to 1.5 m under the APEx tracks they share the viaduct with.

### What would make it exact

- **Levels from the Deck itself.** The Deck's generators compute a rail level for each track they build. Publishing it per point in `tracks.json` and `context.json` would replace the marks and the interpolation.

- **The Profiles page updated:**
  - onto the Deck's CUT basis (lower level 144 m, TRI A at or below 135.9 m, platform M at 160.3 m);
  - onto the North Viaduct routes and levels for B and D;
  - onto Ben's Norwood level stack.

- **Line ids.** Each Profiles line could name the Deck line ids it matches, so the two are joined by id rather than by distance.

## Working rules

- Read both editors' databases freely; change them only when Ben asks.

- Re-run the extract before relying on these numbers. Ben edits the Deck daily.

- Log decisions in `claude/Station_Area_Maps_Log.md` (Fountain Square), `claude/Norwood_Central_Log.md`, or `claude/Relief_Maps_Log.md` (CUT and the Deck).
