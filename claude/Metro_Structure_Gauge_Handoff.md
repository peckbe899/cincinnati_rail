# Metro structure gauge change: handoff for the code session

Ben, 27-28 October 2026. For the hub repo (github.com/peckbe899/cincinnati_rail, branch claude/stoic-cray-fqf881): Deck, Profiles, Station 3D and the hub's shared parameters. The drawings are on the "Metro Tube and Box Sections" page (claude.ai artifact 3wNvymSc1DGcnxZ47zEx4X), version 2.

Revised 28 October: underground structures are now sized to the train's dynamic envelope plus a running clearance, not to the CTA standard envelope, and the tube type follows the building era.

## 1. Ben's decisions

1. **Metro loading gauge:** CTA / MBTA Orange Line class, with cars 9'3" to 9'4" (2.82 to 2.85 m) wide and about 12'0" (3.66 m) tall over the rail. This replaces the IRT A Division gauge in fact tracker 2C and the 4.4 m tube (Relief log 10j.1).

2. **Envelopes:**
   - Tunnels and boxes use the dynamic envelope plus running clearance (London-style tight tubes; Ben: "the Tube uses a much tighter spacing").
   - Open structures (at grade, elevated) keep the CTA Appendix B standard envelope, 4.37 m wide x 4.42 m high over the rail.

3. **Tube type by era (fact tracker 2B phases):**
   - Phase 1 (Lines 1-7, 1903-18): type A, cast iron, bench walls, no walkway.
   - Phase 2 (Lines 8-12, 1934-41): **open.** Either the canon 9.0 m double-track bore (ruled 9 October) or type A twin tubes.
   - Phase 3 (Lines 13-14, 1950s-70s) and all later extensions and infill: type C, concrete segments, side walkway.
   - Deep tubes in the hills use the same type as their era.

4. **Island platforms by default** at every Metro station on a shallow-shield bored stretch. Ben's per-station settings still override (my reading).

5. **Station approaches:** re-engineer how the tubes come together and spread apart at stations (section 3).

6. **Metro grades:** 5% stays the limit; straight underground sections may reach 6%.

| Where | Over 5% | Over 6% |
|---|---|---|
| Straight, bored or box (covered and dry) | warning | error |
| On a curve, in a trough, or not underground | error | error |

This amends the 50‰ maximum in fact tracker 2C.

## 2. Values

These are drawing values.

**Envelope basis:**

- The dynamic envelope is the car (2.85 x 3.66 m) plus 0.15 m sway each side and 0.05 m bounce.
- Below 1.0 m over the rail, only the shoe and truck zone needs room, 1.45 m either side of centre (assumed). The third rail sits 1.27 m off centre (MBTA spec).
- Running clearance is 0.15 m (LA Metro's preferred figure).
- Build tolerance for bored tubes is 0.10 m radial (Singapore).

| Item | Value |
|---|---|
| Type A tube (Phases 1-2) | 5.10 m inside, 5.50 m outside (cast iron, 0.20 m); fitted size 4.94 m |
| Type C tube (Phase 3 on) | 5.40 m inside, 5.90 m outside (0.25 m concrete segments); tube centre 0.17 m toward the walkway; fitted 5.20 m |
| Rail over the inside invert, both tube types | 0.70 m (slab or concrete with a centre drain; rail 0.168 m) |
| Type A rail to inside crown | 4.40 m |
| Bench walls, type A | top 0.9 m over the rail, outside the shoe zone, holding duct banks (assumed) |
| Walkway, type C | 0.76 x 2.03 m envelope at 1.12 m over the rail, on the side away from the third rail, with a handrail and cable troughs under it |
| Twin-tube running centres | type A 8.74 m, type C 9.14 m (outside diameter + 3.24 m of ground) |
| Double-track bore (Phase 2, option 1) | 8.60 m inside, 9.00 m outside (canon); 3.90 m track centres; rail 2.30 m over the invert; fitted 8.06 m |
| Double-track box | 3.90 m track centres (Ben, 26 October, confirmed by the new envelope); steel columns between the tracks (Ben, 28 October), about 0.25 m square, 1.52 m (5 ft) apart, carrying roof beams at the same spacing (1904 IRT frame); 7.90 m inside, rail to roof underside 4.0 m, 1.0 m below and 4.6 m above the rail outside (canon) |
| Island station box | 10.90 m track centres, 8.0 m island at 1.12 m, 14.90 m inside, rail to roof underside 4.6 m |
| Island approach | type A tubes ease out 1.08 m each, type C 0.88 m, over about 40 m |

This replaces the 5.65 m tube, the 9.35 m twin centres and the 4.82 m box centres of the first version of this note.

## 3. Work for the code session

1. **Shared parameters:** put section 2 into the hub's parameter registry, the Deck, the Profiles editor and Station 3D, with the tube type chosen by the line's phase (Lines 1-7 type A, 8-12 per Ben's Phase 2 choice, 13-14 type C). Extensions built after a line's phase use type C; the date of each extension needs a field if it isn't held already.

2. **Platform default:** use an island where the platform centre falls on a shallow-shield bored stretch. Otherwise keep the current defaults. Ben's per-station settings override.

3. **Station approaches:**
   - Tubes ease from their running spacing to 10.9 m before an island.
   - Bored tubes never come closer than their running spacing. Any approach that brings tracks closer has to happen inside a cut-and-cover box; mark where each box starts and ends.

4. **Grade checks:** apply decision 6 in the Profiles editor's checks. "Straight" means no curve in plan; "underground" means bored or box only.

5. **Tunnel equipment in Station 3D**, on separate layers (legacy, CBTC, safety). Use simple repeated objects at these positions and spacings:

| Item | Position | Spacing |
|---|---|---|
| Third rail | 1.27 m off centre, 0.15 m up, uncovered | continuous; insulators about every 3 m |
| Trip stop (legacy) | beside the running rail opposite the third rail; arm 64 mm above the rail | one at each signal |
| Colour-light signal (legacy) | on the wall, same side as the trip stop, head about 2.4 m up (assumed) | block ends, 250 m blocks (assumed) plus platform ends |
| Track-circuit joints and impedance bonds (legacy) | in and beside the rails | at block ends |
| CBTC transponder | between the rails | every 100 m (assumed) plus one at each stopping point |
| CBTC radio access point | upper wall, about 3 m or higher | every 300 m (assumed) |
| Leaky feeder | upper wall, continuous | fed at most every 800 m |
| Cable racks / duct banks | traction feeders on the third-rail side, signals and comms opposite; in bench walls (A) or under the walkway (C) | continuous |
| Tunnel light | upper wall | every 18 m (1904 IRT); at least 0.25 fc at the walking surface (NFPA 130) |
| Standpipe and hose outlets | low on the wall | outlets every 61 m (200 ft) |
| Blue light station | on the wall at hand height | about every 244 m (800 ft) and at platform ends |
| Cross passage (twin tubes) | at bench or walkway level, fire doors | at most 244 m apart |
| Drain | centre channel in the slab or invert; sump at each low point | |
| Vent shafts | station ends; mid-tunnel where stations are over 6,000 ft apart; draught relief shafts on deep tubes | |
| Intrusion detection (GoA3) | track approaches and platform edges | last 100 m into each platform (assumed) |
| Distance markers | below 1.5 m | every 100 m |

6. **Report back:**
   - stations whose new approach doesn't fit;
   - side-platform stations on bored stretches;
   - the 4.2 m clear height under structures in the open (log 10j.7), now below the 4.42 m standard envelope.

7. **Logging:** log the change in `claude/Station_3D_Log.md`. Fact tracker 2C needs Ben's canon update for the gauge, the tubes and the grade rule.

## 4. Sources

- CTA Appendix B (drawing, Ben); MBTA VE-10-036 Part T 02.00, tables 2-1 and 2-2.
- LA Metro Rail Design Criteria §4 (walkway, running clearance, 18'10" tubes).
- Singapore tunnel design practice (5.2 / 5.6 m tubes, 100 mm tolerance).
- Zhou, Cambridge (London tube diameters); Jubilee Line Extension (4.35 m with walkway); Toronto-York Spadina extension (5.4 m with walkway).
- NFPA 130 through JICA and the Seattle amendments (walkways, cross passages, lighting, standpipes); WMATA blue lights (DC FEMS report).
- 1904 IRT (duct banks, lighting, drainage) on nycsubway.org; London Metropolitan line slab track; Train stop and 49 CFR 236.531; ORR's IEC 62267 GoA table.
