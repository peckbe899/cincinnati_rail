# Handoff to the code session: Mill Creek yards and Metro structures

Chat session of 27-28 October 2026. For the hub repo github.com/peckbe899/cincinnati_rail, branch claude/stoic-cray-fqf881. Everything below is Ben's ruling unless marked as a drawing value or an assumption.

The chat session can't push, so the files to bring in are on the frozen claude.ai artifacts. Read them with the Artifact tool's read action, giving the artifact link and `path`.

## 1. Mill Creek Deck: yards under the deck (draft 6)

### 1.1 What to bring in

The repo's Deck (`hub/sites/deck/`) is the published Deck version 140 (version id 1793128963-c39d), which is yards draft 5. Draft 6 is version 141 (version id 1793139343-a4fe) of https://claude.ai/artifact/L81dVQSV8THSWai2LhZhcv.

1. Replace `hub/sites/deck/yard.json` with `yard.json` from version 141.
2. In `hub/sites/deck/index.html` (about line 2112), change the yard selection text from `'Draft 5. '` to `'Draft 6. '`. Nothing else in the page changed.
3. `context.json` already matches version 141. It holds the Evans mark at 139.0 m from the RER A lowering.

### 1.2 Rulings behind the yards

**Extent:**

- The yard sits inside Ben's buildable area of 27 October: between the arch viaduct, RER and Mill Creek, 142.2 ha.
- It is stored as the `yard_limit` feature in `yard.json` (EPSG:26916), from his KML.
- It replaces the earlier limit (deck between CUT and New St W, flattened land north to Albone).

**Mill Creek:**

- The creek runs under Exposition Boulevard and Millvale Boulevard. The yards may not extend west of it.
- An unmarked culvert links the two segments. It follows Ben's KML sketch, smoothed:
  - points of intersection at (712446, 4333516), (712293, 4334318) and (711975, 4334970);
  - radii 900, 800 and 500 m;
  - width tapering from 70 m to 45.72 m.
- The yards may not cross the culvert. It runs underground, and the Palace stands over it.

**Area target:** as large as today's yard, 108.7 ha. It is measured like today's yard: tracks buffered 3 m, gaps under 24 m closed, parts over 2,000 m² kept. By that measure today's yard is 120.2 ha in all and 108.7 ha clipped to the deck.

**Type:** a hump yard plus flat yards, with their own freight ramp to the Cincinnati Southern bridge. Which yard does which job (receiving, bowl, departure) is still open.

**Track rules:**

| Item | Rule |
|---|---|
| Track spacing | 4.5 m (the real yard's median) |
| Turnouts | No. 8 in the yards; No. 10 at the bridge |
| Ladders | compound: master ladder 14.3°, group ladders 7.15° |
| Curve radius | yards 200 m or more (206 m reached), leads 300 m or more, ramp 450 m |
| Ramp ruling grade | 1.5% |

**Ladder fix:** the first track on each side of a ladder used to cross the first ladder leg. Every track now comes off its ladder by a turnout.

**RER A lowered under the yard** (Ben chose "Lower RER A"):

- At least 7 m under the yard floor from Evans to the Union Terminal box.
- Rail 139.0 m at Evans (was 147.5 m) and 135.9 m at the UT box, then 2.2% up to the deck edge at 148.4 m.
- **The Profiles editor still has RER A at 154.8 m at Evans and needs this.**

### 1.3 The layout in draft 6 (layout A)

Ben asked for the yard orientation that gives the most yard space in his area. All tracks run lengthwise along the corridor. These are the options compared, measured as above, without leads or the ramp:

| Arrangement | Footprint |
|---|---|
| Two long yards end to end, extra tracks in the wide parts | 93.9 ha (chosen) |
| Two lanes side by side, leads outside, staggered | 72.5 ha |
| Four yards end to end | 57.3 ha |
| Nested three (draft 5's layout), rerun in the area | 54.8 ha |
| One 5.3 km yard (not realistic) | 104.6 ha |

Ben's change to it: the CS bridge exit is solved by a CVG-type stub fan in the lower left, leaving the east side for the ramp.

What draft 6 holds (distances along the area's centreline frame, t from the south):

| Part | Extent | Tracks | Footprint |
|---|---|---|---|
| South yard | throat at t 1,230 (about N 4,332,100) to t 2,370, just south of the Palace | 39 | 12.8 ha |
| North yard | t 2,430 to t 5,350 (about N 4,336,100); extra tracks branch off its outer tracks where the area widens | 57 | 51.3 ha |
| South fan (stub, to the river) | throat at (712485, 4331925); lead 144 m at R 300 off the departure line at N 4,332,068 | 55 | 18.9 ha |

Leads in draft 6:

- **Lead between the yards:** straight.
- **Lead to the north:** to the end of the area. Its route beyond is not set.
- **Departure line and freight ramp:** 1,336 m long, at yard level to the foot at N 4,332,029, then 1.47% up the east side, 12.2 m clear of the intercity. It merges into the intercity west track at the CS bridge north end (712616.7, 4330783.7) at 164.0 m by No. 10 turnouts.

Total footprint: 12.8 + 51.3 + 18.9 = 83.0 ha for the yards, 85.1 ha with the leads and ramp. That is 23.6 ha short of 108.7.

Checks passed: everything inside the area (except the ramp's final approach to the bridge), no crossings, radii as in 1.2.

### 1.4 Yard flags to report or resolve

- Ben's area overlaps the RER E box (499 m² of yard, 133 m² of lead) and the Mill Creek (RER E) station box (1,790 m² of yard). The yards were left as drawn.
- Lines 7, 8, 9 and 10 have no levels set where they pass under the deck.
- The north connection beyond the area's north end is not set.
- The yard roles (receiving, hump bowl, departure) are not assigned yet.

### 1.5 The builder scripts

The scripts that generated the yards (`buildA.py`, `zipkit.py`, `ygen.py`) live only in the chat session's scratch space and are not in the repo. If the yards need regenerating, the method is:

- a smoothed centreline frame along the area, with curves of R 800 m or more;
- through yards with compound ladder fans at each end, each track kept only if its body is at least 250 m and inside the area;
- side yards hung off the outermost core track where the area is at least 20 m wider for 500 m or more;
- a stub fan placed by search for the largest footprint;
- the ramp found by search for curves of 450 m and grades of 1.5% or less.

## 2. Metro structures: gauge, tubes, boxes and tunnel equipment

The full detail is in the project doc `claude/Metro_Structure_Gauge_Handoff.md` (current as of 28 October). The drawings are in two artifacts:

- **Metro Tube and Box Sections**, version 5: https://claude.ai/artifact/3wNvymSc1DGcnxZ47zEx4X. Plates A to I.
- **Metro Box Cutaway**: https://claude.ai/artifact/LhCAbhX6NWjncJubLjcEre. 3D, 250 m of double-track box.

### 2.1 Rulings

1. **Loading gauge:** CTA / MBTA Orange Line class cars, 2.82-2.85 m wide and 3.66 m tall over the rail. This replaces IRT A Division (fact tracker 2C) and the 4.4 m tube (log 10j.1).

2. **Envelopes:**
   - Tunnels and boxes are sized to the dynamic envelope plus running clearance, London-style tight. Ben: "the Tube uses a much tighter spacing".
   - Open structures keep the CTA standard envelope, 4.37 x 4.42 m.

3. **Tube type follows the building era (tracker 2B phases):**
   - Phase 1 (Lines 1-7): type A.
   - Phase 2 (Lines 8-12): **open.** Either the canon 9.0 m double-track bore, which fits again at the tight envelope, or type A twin tubes.
   - Phase 3 (Lines 13-14) and all later extensions: type C.
   - Deep tubes in the hills use their era's type.

4. **Islands by default** at Metro stations on shallow-shield bored stretches. Ben's per-station settings override.

5. **Station approaches:** bored tubes never come closer than their running spacing; any closer approach happens inside a box.

6. **Grades:**
   - 5% is the limit.
   - On straight sections that are bored or box (covered and dry, not trough), over 5% gives a warning and over 6% an error.
   - Everywhere else, over 5% is an error.

7. **Boxes have steel columns between the tracks** (Ben, 28 October): about 0.25 m square, 1.52 m (5 ft) apart, each carrying a roof beam (1904 IRT frame). Clear span (Cambridge 1912) and centre wall (Dorchester 1912) were rejected.

8. **Sumps go at every low point of each tube's profile**, not at a fixed spacing.

### 2.2 Values

These are drawing values.

| Item | Value |
|---|---|
| Dynamic envelope | car + 0.15 m sway, + 0.05 m bounce; shoe zone 1.45 m off centre (assumed) |
| Running clearance / bored build tolerance | 0.15 m / 0.10 m radial |
| Type A tube | 5.10 m inside, 5.50 m outside, cast iron; rail 0.70 m over the invert; bench walls with duct banks, top 0.9 m (assumed) |
| Type C tube | 5.40 m inside, 5.90 m outside, concrete segments; rail 0.70 m over the invert; walkway 0.76 x 2.03 m at 1.12 m on the side away from the third rail; tube centre 0.17 m toward the walkway |
| Twin-tube running centres | A 8.74 m, C 9.14 m (3.24 m of ground) |
| Double-track bore (Phase 2 option) | 8.60 / 9.00 m, track centres 3.90 m, rail 2.30 m over the invert |
| Double-track box | track centres 3.90 m, 7.90 m inside, rail to roof underside 4.0 m, 1.0 m below and 4.6 m above the rail outside |
| Island station box | track centres 10.90 m, 8.0 m island at 1.12 m, 14.90 m inside, rail to roof underside 4.6 m |
| Island approach | type A tubes ease 1.08 m each, type C 0.88 m, over about 40 m |

### 2.3 Tunnel equipment for Station 3D

Put these on separate layers (legacy, CBTC, safety, services). Positions and spacings are in the Metro handoff's section 3 item 5 and drawn in plates A, E, I and the cutaway.

- **Legacy:**
  - signals on the outer wall, head about 2.4 m up (assumed), at block ends (250 m blocks, assumed);
  - trip stops beside the inner rail;
  - insulated joints and impedance bonds at block ends.
- **CBTC:**
  - transponders between the rails every 100 m (assumed);
  - radio access points about every 300 m (assumed);
  - leaky feeders on the walls.
- **Safety:**
  - standpipe with hose valves every 61 m;
  - blue light stations every 250 m and at platform ends;
  - cross passages at most 244 m apart (twin tubes);
  - distance markers every 100 m;
  - intrusion detection on the last 100 m into each platform and along platform edges (GoA3).
- **Services:**
  - third rail on insulators every 3 m;
  - cable racks;
  - lights every 18 m;
  - drains, with a sump at each low point;
  - vent shafts at station ends, plus draught relief shafts on deep tubes.

In the boxes, the third rails are on the outer sides and the trip stops by the inner rails, which puts the trip stops on each train's left (as on New York's lettered lines).

## 3. Order of work

1. Bring in Deck draft 6 (section 1.1).
2. Update RER A in the Profiles editor to the lowered levels (section 1.2).
3. Put the Metro structure values into the hub's parameter registry, the Deck, the Profiles editor and Station 3D, with the tube type chosen by phase.
4. Apply the island default and the station-approach rule; mark where boxes start and end.
5. Apply the grade checks.
6. Add the tunnel equipment layers to Station 3D.
7. Log everything in `claude/Station_3D_Log.md`. Fact tracker 2C needs Ben's canon update for the gauge, tubes and grades.

## 4. Report back to Ben

- stations whose new approach doesn't fit;
- side-platform stations on bored stretches;
- the 4.2 m clear height under structures in the open (log 10j.7), now below the 4.42 m standard envelope;
- the yard flags in section 1.4;
- anything in this note that disagrees with the repo.
