# Handoff to the code session: the Chronology view, tunnel depths and how tunnels are built by era

Chat session, 28 October 2026. For the hub repo github.com/peckbe899/cincinnati_rail, branch claude/stoic-cray-fqf881. The chat session has not touched the repo. Ben's rulings are marked "Ben"; everything else is a proposal or a drawing value and says so.

Tube sizes are from `data/profile/metro_structure.json`.

## 1. A fourth view: Chronology (Ben)

### 1.1 What it is for

A map page in the hub, beside the Deck, the Rail Profiles and Station 3D, where the opening year and phase of every Metro and TRI segment and station are set. The phase decides the tube type and the construction rules in section 2.

Like the other three views, it reads and writes the hub's database and updates live: change a year there and the Profiles, the Deck and Station 3D follow; change a route in the Deck and the Chronology map follows.

### 1.2 What it shows

- A map like the Deck's, showing only the Metro and TRI lines and their stations (no streets, yards or APEx), over the relief or a plain base.
- Colour by phase or by opening year (a toggle).
- A slider for "the network as of" a year, showing only what had opened by then.
- Segments not yet set drawn as dashed, so the gaps are visible.

### 1.3 How years are set

- **Segments:** pick a station, then another station on the same line. Every segment between them is selected. Add more with shift-click or a lasso.
- **Setting:** set the opening year, the phase, or both in a side panel.
- **Shared track:** a segment shared by several lines is one segment, so setting it once sets it for every line on it.
- **Infill stations:** click a station to give it its own opening year. A station that opened later than its segment is an infill station.

### 1.4 Order rules (Ben)

**The rule:** stations further out on a line can't be older than the ones inside them, unless they are infill. The page enforces that:

1. **The core.** Each line's core is its earliest segment: the tracker's original or opening segment, or else the earliest year set. Everything else is an extension outward from it, on either side and on each branch.
2. **Outward, never older.** Going outward from the core, a segment's year must be at least that of the segment it extends from. On a branch, each arm must be at least the year of the segment at the junction.
3. **A station can't open before its track.** A station's year is at least the earliest year of the segments that touch it. By default it equals that year.
4. **Infill.** A station whose year is later than the earliest segment touching it is infill. The page marks it so automatically; it is the only way a station can be newer than the stations beyond it.
5. **Shared track** carries one year, and must satisfy rule 2 for every line on it.
6. **Unset segments** are skipped in the checks. Once neighbours on either side are set, the side panel shows the range of years an unset segment may take.

**Enforcing it:**

- An edit that would break rules 2, 3 or 5 is refused, and the side panel says why: which segment or station is older than the one inside it.
- Setting a segment later than the segments beyond it offers to push those outer segments, and their stations, to the same year in one step.
- Violations already in the record (from the defaults or older saves) are drawn in red and listed until they are fixed.

### 1.5 The record

Add a new hub record, `chronology/segments`, saved, versioned and broadcast like the others.

- **Segment key:** system (Metro or TRI), line, and the two station names at its ends, taken from the tied routes, so the key survives geometry edits. Fields: year, phase, source (tracker, Ben, default) and note.
- **Station key:** system and station name. Fields: year, source and note.
- **Orphans:** entries whose station names no longer exist after a Deck edit are kept and listed for Ben, not deleted.

### 1.6 Phase from year

The tracker's phases (2B):

| Phase | Years |
|---|---|
| Phase 1 | 1903-1918 |
| Phase 2 | 1934-1941 |
| Phase 3 | 1950s-1970s |
| Later | everything after |

**Years between phases (proposed, Ben to confirm):** 1919-1933 build with Phase 1 methods, 1942-1949 with Phase 2, and 1980 on as "later".

A phase set by hand without a year stands on its own.

### 1.7 Defaults until Ben sets them (tracker 2B)

**Phase 1:**

- Lines 1-7 between their original termini are Phase 1, with years not set.
- First revenue service is Line 1, the Pearl Street Trunk, November 1905; the tracker names no stations for it.

**Phase 2:** the opening segments with their years, as the tracker gives them:

| Line | Opening segment | Year |
|---|---|---|
| 8 | Northside to Union Terminal | 1934 |
| 9 | Camp Washington to Oakley | 1936 |
| 10 | Mill Creek to Paradrome | 1937 |
| 11 | Manhattan (Bellevue) to Ludlow | 1939 |
| 12 | Hopple to Pleasant Ridge | 1941 |

The rest of Lines 8-12 are Phase 2 with years not set.

**Phase 3:** Lines 13 and 14, years not set.

**Everything else** (extensions beyond the original or opening termini) is "not set". It falls back to the line's phase for the rules until Ben sets it, and the map shows it dashed.

**TRI:** years only. The TRI profile rules don't change by phase.

### 1.8 What reads it

- **Rail Profiles:**
  - the phase per chainage comes from `chronology/segments`, replacing `piece_phase` and `line_phase` in `metro_structure.json` (keep those only as the fallback);
  - add a band under the profile showing each segment's year and phase;
  - clicking the band opens the Chronology view at that segment.
- **Deck and Station 3D:** the tube type per segment from the same record.
- **The view bar and the hub page:** add the fourth view; extend `tests/test_hub.py` and `hub/test_hub.js` so a change on the Chronology page reaches an open Profiles page live.

## 2. Tunnel depths and how tunnels are built, by era (Ben: approved)

### 2.1 Minimum cover over bored tubes (Ben)

**The rule:** every shield-driven tube (shallow shield, deep tube and the double-track bore) needs at least one outside diameter of ground over its crown. The rule of thumb for shield and TBM tunnels is cover of at least one diameter: below that the ground can't arch over the tube.

**What it replaces:** today's split, which allows 2.0 m with the tube top above the water table (140 m) and one diameter below it.

- In `profiles.html`, `reqCover` returns one outside diameter for every tube.
- `TUBE_COVER_HIGH` and the water-table split for cover go.
- The river rule (rail at least 7.5 m below the bed) is unchanged.

**Minimum rail depth** (crown above the rail + one diameter):

| Tube | Crown above rail | Cover | Minimum rail depth |
|---|---|---|---|
| Type A | 4.60 m | 5.50 m | 10.10 m |
| Type C | 4.95 m | 5.90 m | 10.85 m |
| Double-track bore | 6.50 m | 9.00 m | 15.50 m |

Shallower than that is cut and cover. Station boxes are unaffected.

**Stacked tubes:**

- The rule applies to the top tube.
- The lower tube is governed by its separation from the tube above (today's crossing rule: upper floor + 0.5 m + lower top). For type A that puts the lower rail at least 0.90 + 0.50 + 4.60 = 6.0 m below the upper rail, so at least 16.1 m deep.
- The chat found no firm figure for ground between stacked bored tubes, so the 0.5 m stands until Ben rules.

### 2.2 What the rules rest on

- **Phase 1 (founding era):** American practice was shallow cut and cover, tunnelling only where digging was blocked (hills, under parks or buildings, under rivers), with lift-only deep stations. New York's IRT (1904) had tunnel roofs usually about 30 in under the street and local stations about 17 ft down.
- **Phase 2:** shield tunnels between cut-and-cover stations became normal where the ground suited. Chicago's 1943 subway drove its running tunnels through clay about 43 ft down and used cut and cover only for stations and mezzanines.
- **Phase 3:** both methods in use, with the choice by ground and street disruption (Toronto 1954 and the Market Street subway cut and cover; Washington twin soft-ground tunnels between cut-and-cover stations).

### 2.3 Thresholds

All depths are rail depth below finished ground:

| Rule | Phase 1 (type A) | Phase 2 (9.0 m bore) | Phase 3 and later (type C) |
|---|---|---|---|
| Open trough / box | trough under 4.6 m; box with the roof as the street 4.6-5.2 m; buried box from 5.2 m | same | same |
| Shield allowed from (section 2.1) | 10.1 m | 15.5 m | 10.85 m |
| Deepest cut and cover | 12.19 m (40 ft, the existing canon-shallow flag) | 16.5 m (bore minimum + 1 m, so the methods overlap) | 15 m |
| Minimum shield drive (judgement, not sourced) | 400 m | 300 m | 300 m |
| Deep (lift or escalator stations) from | 18.29 m (60 ft, the existing setting) | 18.29 m | 18.29 m |

Put these per phase in `metro_structure.json` (`phases`), editable on the hub page.

### 2.4 Transition rules

The same pattern applies at both boundaries: cut and cover to shallow shield, and shallow shield to deep.

1. **Raw type by depth:**
   - shallower than the shield minimum: cut and cover;
   - deeper than the cut-and-cover limit: bored;
   - between the two: cut and cover unless the stretch meets rule 2's minimum drive;
   - deeper than 18.29 m: deep.
2. **No short pockets.** No stretch of any type shorter than its phase's minimum drive, except at station boxes and portals.
   - A short bored pocket becomes cut and cover. If it's deeper than the cut-and-cover limit, flag it.
   - A short cut-and-cover pocket inside a drive becomes bored if the cover allows. If it doesn't, flag it: the profile has to dive.
   - A short deep pocket is shallow shield; the tube is the same.
3. **Switching:**
   - **Cut and cover to shield, or back:** only at a station box, a portal or a shaft. Shield drives run box to box or box to portal.
   - **Shallow shield to deep:** only between stations. A stretch is deep if it holds a deep station or runs at least the minimum drive below 18.29 m.
4. **Deep stations** are platform tunnels with lift or escalator shafts, not boxes, since 18.29 m is past every era's cut-and-cover limit.
5. **Phase changes:** where the phase changes along a line (from the Chronology record), a drive ends at the station box where it changes.
6. **Precedence (as now):** canon sections set the method where the tracker gives one, and painted stretches override everything.

### 2.5 Twin tubes or one bore

By phase:

- Phase 1: type A twin tubes;
- Phase 2: the 9.0 m double-track bore;
- Phase 3 and later: type C twin tubes.

Two local exceptions (proposed):

- **Narrow streets:** under a street narrower than the twin-tube footprint (type A 8.74 + 5.50 = 14.2 m; type C 9.14 + 5.90 = 15.0 m), use the single bore or stacked twin tubes, so the tunnel stays under the street.
- **Shallow lines:** where a Phase 2 line can't reach 15.5 m, the single bore is impossible, so it is twin tubes or cut and cover.

### 2.6 A label to check

Cincinnati's hills are bedrock (Ordovician limestone and shale). Where a deep tube runs in rock it would be drill-and-blast, as the IRT did through Washington Heights, not a Greathead shield. The editor's "deep tube (Greathead shield)" label is wrong there. The editor has no bedrock data, so this is a label change only, for Ben to confirm.

## 3. Report back to Ben

- From the current profiles, the stations and running tunnels whose method changes under section 2 (the new minimum cover and the era rules), by line.
- Short pockets that rule 2 could not merge (the profile has to dive or rise).
- Every orphaned Chronology entry after a Deck edit.
- Segments still "not set".
- Violations of the order rules (section 1.4) in the starting record.

Log the work in `claude/Station_3D_Log.md`.

## Sources

- Early history of the IRT subway (Wikipedia); ASCE Civil Engineering, "The first New York City subway delivers speed" (2024).
- New York Transit Museum, IND tour backgrounder (2023).
- Encyclopedia of Chicago, subway; chitransit.org, "How Chicago's 1943 initial subway was built".
- London Physical Society, "The influence of geology on London's Underground railways".
- Market Street subway (Wikipedia); SME, "Washington Metro's topless tunnels".
- HotRails, "Tunnels" (cut and cover typically 8-12 m, sometimes up to 20 m).
- SI Engineering, "Scale factors of large-diameter TBM built tunnels": ground cover of at least one tunnel diameter as a rule of thumb.
- Frontiers in Earth Science (2023), "Face stability of shallow shield tunnels in sand": with cover of one diameter or less, the face collapse zone reaches the surface.
