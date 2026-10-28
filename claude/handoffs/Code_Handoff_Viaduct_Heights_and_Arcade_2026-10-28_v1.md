# Handoff to the code session: viaduct heights, the arcade remodel, and MT and J1

Chat session, 28 October 2026. For the hub repo github.com/peckbe899/cincinnati_rail, branch claude/stoic-cray-fqf881. The chat session has not touched the repo. Ben's rulings are marked "Ben"; everything else is a drawing value or an assumption, and says so.

Files that hold what changes: `tools/make_profile_context.py` (the APEx marks, `STREET_CLEAR`, the W 8th re-grade, `VIA`), `tools/station3d/context3d.py`, the Deck (`hub/sites/deck/`: `index.html` text, `basin.json` and `deck.json` streets, `structures.json`, the page's layout doc), and `tests/test_core.py`.

## 1. Street clearance under the arch viaducts (Ben: 14 ft)

- **Ruling:** 4.3 m (14 ft) street clearance, chosen as "just high enough for buses". It replaces 4.9 m (16 ft, the 1960 Interstate standard).
- **Rail over a street:** 4.3 m clearance + 1.6 m arch crown, fill and track = **5.9 m** (was 6.5 m). `STREET_CLEAR` goes from 6.5 to 5.9; the 1.6 m stays.
- **Reference vehicle** for checks: a 40 ft transit bus, 3.38 m tall (CNG or battery Xcelsior) and 2.59 m wide.
- **The arches are flat.** One arch per street, spanning the whole street. With the crown at 4.3 m, the outer lanes need a segmental arch rising about 1 in 10. On a 60 ft (18.3 m) street it springs about 2.5 m up at the building lines and is about 3.7 m up at 5.5 m from the centre, so a kerb-lane bus clears by about 0.3 m. Check every street opening against the bus in its outer lanes.
- **Wider streets** get more than one arch, with piers in the median.
- **Where the rail is held higher than street + 5.9 m** by something else, the arches rise with it.

## 2. Levels

### 2.1 Deck lobe, Bank to the deck tip

The marks were set at street + 6.5 m. In practice they run 6.3-6.6 m over the streets (Bank to Bates).

- Replace the hand marks with: rail at or above finished street + 5.9 m at every street the viaduct crosses, interpolated between.
- Don't simply drop the marks 0.6 m. Dolph, McRoberts, Harrison, Alfred, Straight, Marshall, Garrard line and Meeker sit at 6.3 m now, so they can come down 0.4 m, not 0.6 m.

### 2.2 Deck tip to Ludlow (Millvale): a dip

Today the rail falls in one straight line, 0.28%, from the deck tip (166.6 m) to Ludlow (162.5 m). Millvale's ground is 149-152 m, so the rail runs 10.8-14.6 m over its streets. Replace that line with a dip that keeps the locked levels:

| Point | Level |
|---|---|
| Arlington (RER B), N 4,335,724-4,335,928 | 165.9 m, level across the platform (locked, Ben 27 October; the APEx marks now slope 166.0 to 165.5 there) |
| North platform end to the dip | down at 1.5% (the trunk fill's grade) |
| Spring Grove | about 158.1 m (set by the 1.5% fall, not the street) |
| Ford, Colerain, Streng | about 157.4-157.5 m (street + 5.9) |
| Millvale Boulevard | about 158.4 m (street + 5.9) |
| Ludlow | 162.5 m, unchanged: the Northside / Spring Grove platforms (locked) start at its north edge |

- The climb to Ludlow is under 1.5%.
- These are the chat's figures on track 3 (APEx Dayton 1) against the map 3 ground. Recompute them along the deck.
- The structure is one level, so every track on the lower deck follows this profile.

### 2.3 What stays

- **The CUT platform deck:** 160.3 m (the rotunda floor).
- **The south approach:** its straight grade from CUT (160.3 m) to the APEx bridge (164.0 m), including 161.7 m over W 8th. The streets under it (Richmond, W 9th, W 7th, Budd and W 6th, 7.8-13.0 m) can't be lowered without lowering W 8th or the bridge.
- **The Indianapolis + D upper deck.** It is set by what it crosses, not by the lower deck (section 6).

### 2.4 W 8th under the south approach (Ben: lower the hump)

- **The problem:** the W 8th re-grade is still 3.0-3.3 m high where it meets the APEx tracks (x about 712,764-712,778). With the rail at 161.7 m, that leaves 5.4-5.7 m from rail to street, so the street is short of clearance.
- **The fix:** the hump may be at most 161.7 - 5.9 - 153.0 (W 8th's surveyed level) = **2.8 m** under the south approach.
- **New profile:**
  - keep 5.0 m over the intercity pair to x 712,671;
  - fall to 2.8 m at the structure's west face (about 2.4% over about 93 m);
  - hold 2.8 m or less under the structure;
  - then fall to zero at x 712,941 as now.
- **In the code:** the `w8` points in `make_profile_context.py` are `(712671, 5.0), (712806, 2.5)`.
- **Recheck** the Horne hump and the Line 4 test against the new W 8th.

## 3. Streets that cross at an angle (Ben)

| Crossing | Treatment |
|---|---|
| Millvale Boulevard (42°, 45.7 m) | **A bridge.** The boulevard carries the culverted Mill Creek, and nothing may stand on the culvert |
| The knot: Spring Grove (38°), Ford (49° and 40°), Colerain (52°), Streng (60°), N 4,336,426-4,336,563 | **One bridge over all five** |
| Ludlow (30°) | The existing Ludlow underbridge |
| Every other skewed crossing (Harrison, Marshall, Garrard line, New street N, Meeker, Township, Rawson, Willow Lane, Johnson, Hopple) | **Skew arches.** The barrel follows the street; the face opening is the street width divided by the sine of the angle |

- **Bridge depth:** keep the construction depth under the rail within the 1.6 m allowance (through girders or through trusses), or report where the rail would have to rise.
- **Bridge appearance:** not set by Ben. Draw them like the Ludlow underbridge for now.

## 4. The arcade remodel (Ben's mockup)

**Source.** Ben has a mockup image; ask him to attach it. It is for style only and not to scale (Ben). Take the dimensions from section 1.

**Applies to:**

- the two arch viaducts: the north arch viaduct (lower deck) and the south approach from W 9th to the Cardinal crossing.
- **Not:**
  - the CUT fan (an embankment with bridges, as at Amsterdam Centraal);
  - the normal viaducts south of the Cardinal crossing;
  - RER A's own viaduct;
  - the Indianapolis + D upper deck and R5's level under it (on columns).

**Openings:**

- **Open arches** at every street, and at any block Ben marks open.
- **Blind arches** everywhere else, using the same arch shape and bay rhythm.
- **Block switch** (Ben: a switch per block): add an "open arches" switch to the Deck's blocks along the viaducts, every block blind by default. Save it with the page's layout and read it into Station 3D.
- **Bay width between streets:** not set by Ben. Use equal bays close to the standard street arch (drawing value).

**Style, from the mockup:**

- **Walls:** warm buff limestone in coursed ashlar.
- **Piers:** project slightly, with dark grey granite stepped plinths at the base. The piers at the ends of each run (beside a bridge or the viaduct end) carry a winged-wheel roundel and three vertical flutes.
- **Arches:**
  - a projecting, stepped two-band archivolt;
  - a tall keystone with three vertical grooves, flanked by Art Deco fan rays;
  - blind arches recessed with ashlar infill.
- **Top of the wall:**
  - a frieze of small T-shaped corbel blocks under the cornice;
  - a projecting cornice band, broken forward over each pier;
  - a dark bronze Art Deco railing on top, with rectangular panels and a post over each pier.
- **At the base:** pale stone paving.

## 5. MT and J1 (Ben)

**Ruling.** New street MT (the trunk frontage street) and New street J1 should run on either side of the viaduct. They weren't moved when the viaduct was.

**Where they are now:**

- **MT** (basin `SMV0032`) runs from Hopple (N 4,334,891) to N 4,336,477. From Hopple to about N 4,336,000 its centreline is within 2 m of the west pair's west track. Its band overlaps the tracks by about 12,000 m², about 1.16 km of it under the structure.
- **J1** (layout `S056`, extended by Ben to (712360, 4336208)) is a straight line on the east side. It cuts into the structure near Hopple (N 4,335,000) and again near N 4,336,200.

**Change:**

- MT runs along the west side of the structure and J1 along the east side, from Hopple to their present north ends.
- Each street's near edge sits 2.3 m from the structure edge. That is the gap the 15 October layout had between J1, J2 and the structure (Deck page text); Ben can change it.

**Consequences to handle and report:**

- the Millvale cross streets (M20 to M1) end at MT, so trim or extend them to the moved line, and re-cut the blocks and plots on both sides;
- check J1 on the east side against the Mill Creek culvert and OH-75 (the trunk keeps at least 3 m + 1.5 m from both), and report any stretch with no room.

## 6. Report back to Ben

- **The Indianapolis + D upper deck is 0.4 m short.**
  - It is held at 174.5 m, but it crosses RER A and R5 at 167.0 m (South Cumminsville), and the 7.9 m rule needs 174.9 m there.
  - It also crosses RER B at Arlington (165.9 m, needs 173.8 m).
  - The code takes the highest lower-deck rail from s 3,644 on; it should take the rail of whatever the upper deck crosses.
- **Elmore**, near Ludlow: its east end clips the viaduct edge with 5.5 m from rail to street, 0.4 m short of 5.9 m.
- **Clearance checks:** rerun them for every line crossing under or over the north viaduct between the deck tip and Ludlow after the dip (Metro Line 12 crosses near Arlington and at N 4,336,549).
- **Bridge depths:** any bridge whose depth won't fit the 1.6 m allowance.
- **The east side:** anywhere J1 can't fit.

Log the work in `claude/Station_3D_Log.md`.

## Sources

- FHWA, "Right of Passage: the controversy over vertical clearance" (14 ft in 1956, 16 ft in 1960).
- TxDOT Roadway Design Manual 4.8.6 (vertical clearance; 14.5 ft absolute minimum with resurfacing allowance).
- New Flyer Xcelsior (Wikipedia): 3.20 m diesel, 3.38 m CNG and battery, 2.59 m wide.
- Skew arch (Wikipedia): skew arches built to a crossing of about 25° (Southdown Road, Harpenden); girders or a squared road beyond that.
