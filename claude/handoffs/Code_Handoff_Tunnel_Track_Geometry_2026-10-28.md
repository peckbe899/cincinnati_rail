# Handoff to the code session: track geometry in tunnels and station approaches

Chat session, 28 October 2026. For the hub repo github.com/peckbe899/cincinnati_rail, branch claude/stoic-cray-fqf881. The chat session has not touched the repo. Ben's rulings are marked "Ben"; everything else is a proposal or a drawing value and says so.

It goes with `claude/Code_Handoff_Chronology_and_Tunnel_Methods_2026-10-28.md` (depths, methods by era and switch points). Spacings are from `data/profile/metro_structure.json`.

## 1. Centreline and spacing

The centreline is the line's route from the Deck tie. Each track is offset by its construction's spacing:

| Construction | Track centres |
|---|---|
| Cut-and-cover box | 3.90 m |
| Type A tubes | 8.74 m |
| Type C tubes | 9.14 m |
| Double-track bore | 3.90 m |
| Island station | 10.90 m |

Platforms stay straight. Every spacing change starts beyond the platform end.

## 2. The approach belongs to the station (Ben)

The stretch where the tracks change spacing next to a station is part of the station, not the running tunnel, and is built the way the station is built.

- **A cut-and-cover station meeting bored tubes:**
  - the station box carries on through the approach, cut and cover, until the tracks reach the tubes' running spacing (type A 8.74 m, type C 9.14 m);
  - the tubes start there;
  - the box's end is that point, not the platform end.
- **A side-platform cut-and-cover station meeting bored tubes** (Ben): this is where the rule matters most.
  - The tracks run 3.90 m apart through the platforms and have to spread to the tube spacing: 2.42 m outward each for type A (3.90 to 8.74 m), 2.62 m for type C (3.90 to 9.14 m).
  - The whole spread is in the station's box. The box widens until the tracks are at tube spacing, and the tubes start there.
- **A cut-and-cover station on a box line:** the approach (an island's 10.90 m to 3.90 m, or none for side platforms) is in the box anyway.
- **A bored or deep station (platform tunnels):** the approach is bored as part of the station tunnels.
- **Box and tubes meeting away from a station:** the same rule applies. The change from 3.90 m to the tube spacing happens inside the box, and the tubes start at their running spacing (as already ruled).

**Consequences:**

- **Switch points:** the station box, approach included, is the switch point for the rules in the Chronology handoff (section 2.4). It doesn't count toward a drive's minimum length.
- **Spacing in bored tubes:** they always run at their running spacing; they never ease apart themselves. This replaces "bored tubes never come closer than their running spacing; they only spread out from it".
- **Box ends:** mark each box's start and end at the end of its approach.

## 3. How the tracks change spacing

### 3.1 On a straight

A symmetrical S-ease, as now: each track shifts half the change.

**Approach length:** the approach is at least `approach_m` (40 m) and long enough that the reverse curves meet the minimum radius. Over a length L, a shift of Δ gives reverse curves of about L² ÷ (4Δ), so L is at least √(4 × minimum radius × Δ).

| Case | Shift per track | Reverse-curve radius over 40 m | Length for 300 m curves (example) |
|---|---|---|---|
| Island to type A tubes | 1.08 m | 40² ÷ (4 × 1.08) = 370 m | 40 m (already enough) |
| Side platforms to type A tubes | 2.42 m | 40² ÷ (4 × 2.42) = 165 m | √(4 × 300 × 2.42) = 53.9 m |
| Side platforms to type C tubes | 2.62 m | 40² ÷ (4 × 2.62) = 153 m | √(4 × 300 × 2.62) = 56.1 m |

The 300 m is only an example; use the editor's minimum (section 3.3).

### 3.2 On a curve, or running into one (Ben)

**The rule:** each track takes one arc of its own radius, tangent to its straight (or earlier curve) and tangent to its running curve. The change in spacing happens inside the curve, with no S-bend and no compound curve.

**Which way each track bends depends on whether the tracks close up or spread:**

| Case | Outer track (away from the curve's centre) | Inner track |
|---|---|---|
| Closing up (an island to tubes) | moves inward: flatter than its running curve, starting later | moves outward: tighter than its running curve |
| Spreading (side platforms to tubes) | moves outward: tighter than its running curve | moves inward: flatter than its running curve |

**Worked example** (type A island station, then a 300 m centreline curve; each track moves from ±5.45 m to ±4.37 m, 1.08 m):

| Track | Running radius | Transition arc must be | Example |
|---|---|---|---|
| Outer | 304.37 m | flatter than about 304.9 m | a 400 m arc starts about 14 m past the nominal curve start |
| Inner | 295.63 m | tighter than about 295.1 m | a 250 m arc starts about 10 m in |

**The formulas** (all distances in metres):

- R is the centreline radius, r the arc's radius, and a the distance from the nominal curve start to where the track's arc starts.
- o_s and o_r are the track's offsets from the centreline at the station and on the running curve.
- Δ = o_s − o_r is positive when the tracks close up and negative when they spread.

| Track | Formula |
|---|---|
| Outer | a² = Δ × (2r − 2R − o_s − o_r) |
| Inner | a² = Δ × (2R − o_s − o_r − 2r) |

A radius only works when a² comes out positive, which gives the flatter or tighter limits above. In the example, o_s = 5.45, o_r = 4.37 and Δ = 1.08.

**Choosing the radii:**

- the outer track takes the flattest radius that fits before its running curve;
- the inner track takes the flattest radius at or above the minimum radius.

The two arcs generally start at different points; the inner one can't start as early. In the example the inner track can begin at most about 18 m before its tangent point if its radius stays at 150 m or more.

**The same method** applies wherever the spacing changes on a curve: box-to-tube changes inside a box, junctions, and crossover ends.

### 3.3 Minimum radius

Use the editor's existing Metro minimum radius; the chat has not checked its value. If an inner arc can't fit at or above it, flag it, and move the curve start further from the platform or lengthen the approach.

## 4. Corridor

- **Cut and cover**, approach boxes included, has to fit inside the street's right of way, round corners too. The box is 7.90 m wide outside, the island box 14.90 m; the approach box widens between them. The box's outer edge sets the corner radius.
- **Shallow-shield tubes** also follow the streets, so buildings don't need underpinning.
- **Deep tubes** may cut under blocks.

## 5. Report back to Ben

- Station approaches whose arcs or S-eases can't meet the minimum radius.
- Side-platform stations meeting tubes, with their new approach box lengths.
- Approach boxes that don't fit inside the street at corners.
- Stations whose box length changed because the approach is now part of the box.

Log the work in `claude/Station_3D_Log.md`.
