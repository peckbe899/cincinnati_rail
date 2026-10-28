# Handoff to the code session: viaduct heights, the arcade remodel, and MT and J1

Chat session, 28 October 2026. For the hub repo github.com/peckbe899/cincinnati_rail, branch claude/stoic-cray-fqf881. The chat session has not touched the repo. Ben's rulings are marked "Ben"; everything else is a drawing value or an assumption, and says so.

Files that hold what changes: `tools/make_profile_context.py` (the APEx marks, `STREET_CLEAR`, the W 8th re-grade, `VIA`), `tools/station3d/context3d.py`, the Deck (`hub/sites/deck/`: `index.html` text, `basin.json` and `deck.json` streets, `structures.json`, the page's layout doc), and `tests/test_core.py`.

## 1. Rail height over the streets (Ben: 7.4 m)

**The arch check.** A true masonry arch has to carry the trains. The rule of thumb used: ring thickness at least span² ÷ (40 × rise) (Boothby, APT Practice Point 22).

- The 1-in-10 street arches of the first draft failed that rule. An 18.3 m street needs a 4.6 m ring against about 1 m available.
- The lowest true arch over a 60 ft (18.3 m) street springs at the street, rises 1 in 3.5 (crown 5.21 m), has a 1.61 m ring and about 0.6 m of ballast, sleepers and rail. That puts the rail at 7.42 m. The 0.6 m is the chat's assumption.

**Rulings (Ben, 28 October):**

- **Rail at street + 7.4 m** at every street the arch viaducts cross. This replaces 5.9 m (and the old 6.5 m).
- **Sidewalk headroom at least 10 ft (3.05 m).**
- **Arches start as close to the sidewalks as possible:** piers at the building lines.
- **Arches square to the road:** the span is the street width measured square, and the opening is the same width on both faces of the viaduct.
- **Anything that can't be a true arch** is a girder bridge:
  - its piers are built into the blind arcade;
  - the girders are hidden behind an arch fascia, so from the side the arcade reads as continuous;
  - underneath, it is a bridge.

**What that means:**

- **The true-arch limit.** With 10 ft at the pier face and the rail at 7.4 m, a true arch fits only streets up to about 11.8 m wide: 7.4 = 3.05 + 2S/√40 + 0.6, so S = 3.75 × √40 ÷ 2 = 11.86 m, before the bus check.
- **Candidates for true arches:** Meeker (9.1 m) and Stock (4.9 m). Streng and the narrow Ford line are inside the Spring Grove knot, which is a bridge anyway.
- **Every other street crossing is a hidden girder bridge**, every 60 ft street included.
- **The arch fascia on a bridge** springs 3.05 m above the street at the piers, and its crown is the girder soffit.
  - The girder depth, rail to soffit, is drawn as 2.0 m. **That figure is not checked**; set it from a girder design.
  - With 2.0 m, the fascia over a 60 ft street clears a kerb-lane bus (3.38 m) by about 1.2 m, and over Harrison by about 1.0 m.
- **Blocks switched to open arches** are hidden girder bridges too: their 18 m bays can't be true arches.

**Reference vehicle:** a 40 ft transit bus, 3.38 m tall and 2.59 m wide, 0.25 m off the kerb, with 3.4 m sidewalks (drawing values).

## 2. Levels

### 2.1 Deck lobe, Bank to the deck tip

- **The rule:** rail at finished street + 7.4 m at every street crossed, interpolated between.
- **The change:** this is about 1.5 m higher than the 5.9 m draft and about 0.9 m above the old 6.5 m marks.
- **The north end:** Bates (159.6 m) gives 167.0 m, which falls about 0.28% over about 400 m to Arlington's locked 165.9 m. That's compatible.
- **The south end:** CUT stays at 160.3 m. The climb to Bank (lowered 2.0 m for the dive) is about 0.3%.

### 2.2 Deck tip to Ludlow (Millvale): a dip

| Point | Level |
|---|---|
| Arlington (RER B), N 4,335,724-4,335,928 | 165.9 m, level across the platform (locked, Ben 27 October) |
| North platform end onward | down at 1.5% (the trunk fill's grade) |
| Spring Grove | about 158.4 m (the 1.5% fall governs; street + 7.4 would be 156.8 m) |
| Ford, Colerain, Streng | about 159.0 m (street + 7.4) |
| Millvale Boulevard | about 159.9 m (street + 7.4) |
| Ludlow | 162.5 m, unchanged (locked Northside / Spring Grove platforms; the existing underbridge, 7.1 m over Ludlow) |

- **The climb to Ludlow:** about 1.0%.
- **Accuracy:** these are the chat's figures against the map 3 ground; recompute them along the deck.
- **Every track on the lower deck** follows the profile.

### 2.3 What stays

- **The CUT platform deck:** 160.3 m.
- **The south approach:** its grade from CUT (160.3 m) to the APEx bridge (164.0 m), including 161.7 m over W 8th.
- **The Indianapolis + D upper deck:** set by what it crosses (section 6).

### 2.4 W 8th under the south approach (Ben: lower the hump)

- **The pinned rail:** 161.7 m. W 8th's surveyed level is 153.0 m.
- **A true arch is out:** it would need the hump at 1.3 m or less, and W 8th is 33.5 m wide anyway.
- **As a hidden bridge:** the hump may be at most 161.7 - 153.0 - (4.3 bus clearance + 2.0 girder) = **2.4 m** under the structure. That replaces the 2.8 m of the first draft.
- **New profile:**
  - 5.0 m over the intercity pair to x 712,671;
  - down to 2.4 m at the structure's west face (about 2.8% over about 93 m);
  - 2.4 m or less under the structure;
  - zero at x 712,941.
- **Check the fascia over the 33.5 m width:** with the crown 4.3 m above the street, a kerb-lane bus keeps only about 0.16 m over its roof corner, short of the 0.3 m used elsewhere. W 8th probably needs a pier in its median, built into the arcade, or a lower hump.
- **Recheck** the Horne hump and the Line 4 test.

## 3. Streets that cross at an angle (Ben)

- **Openings are square to the road** and the same width on both faces: the street width divided by the sine of the crossing angle.
- **Skewed crossings are bridges.** Under section 1 all of them are hidden girder bridges except Meeker (9.1 m, 37°), which could be a skew true arch if it passes the bus check.
- **Millvale Boulevard:** a bridge with no piers on the culvert.
- **The Spring Grove knot** (Spring Grove, both Ford lines, Colerain, Streng, N 4,336,426-4,336,563): one bridge.
- **Ludlow:** the existing underbridge.
- **Dolph, McRoberts and Western** bend under the east side of the viaduct today, about 5 m inside the east face, where the Deck's streets meet the basin's. Ben: they would have been altered.
  - Run each straight through on the Deck line and bend it beyond the east face (the 3D model uses 10 m, a drawing value).
  - The opening is then the same width on both faces.

## 4. The arcade remodel (Ben's mockup)

**Source.** Ben has a mockup image; ask him to attach it. It is for style only and not to scale (Ben). Take the dimensions from section 1. A 3D model of the stretch from just north of Bank to past Harrison is the "Viaduct Arcade 3D" artifact (version 2).

**Applies to:**

- the two arch viaducts: the north arch viaduct (lower deck) and the south approach from W 9th to the Cardinal crossing.
- **Not:**
  - the CUT fan (an embankment with bridges, as at Amsterdam Centraal);
  - the normal viaducts south of the Cardinal crossing;
  - RER A's own viaduct;
  - the Indianapolis + D upper deck and R5's level under it (on columns).

**Openings:**

- **Open openings** at every street, and at any block Ben marks open. True arches only where section 1 allows; everywhere else a hidden girder bridge behind the same arch fascia.
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
- **Elmore**, near Ludlow: its east end clips the viaduct edge with 5.5 m from rail to street, short of both 7.4 m and a bridge's 4.3 m clearance plus girder depth.
- **Clearance checks:** rerun them for every line crossing under or over the north viaduct between the deck tip and Ludlow after the dip (Metro Line 12 crosses near Arlington and at N 4,336,549).
- **Girder depths:** the real rail-to-soffit depth for each bridge span (the 3D uses 2.0 m), and anywhere it changes the fascia or the rail.
- **W 8th:** whether it needs a median pier (section 2.4).
- **The east side:** anywhere J1 can't fit.

Log the work in `claude/Station_3D_Log.md`.

## 7. Catenary supports, widening, shops and frontage streets (Ben, 28 October)

### 7.1 Catenary supports

**A single box span across the deck (48.9-53.3 m) is too large.** Use middle supports straddling the APEx group: one between the ORR / Transvalley west pair and APEx track 1, and one between APEx track 6 and the east pair.

**Style (Ben, 28 October): masonry.**

- Masonry pylons continue every fourth arcade pier up past the cornice.
- Lattice girders span from them to steel lattice middle masts.

**Spacing:**

- New Haven set its supports 300 ft (91 m) apart on the New York-New Haven line.
- Every fourth pier gives about 83-88 m here, on curves of 740-1,310 m radius.
- The anchor structures go on the street-bridge piers.

**Room for the middle masts:**

- Today every track is at 4.5 m, which leaves no room for a mast.
- A middle mast needs about 2.5 m from each track centre to its face, plus the mast. That is Indian Railways' standard implantation; the chat found no US figure.
- So widen both APEx-side gaps to about 6.0 m (drawing value). The deck gets about 3 m wider.

### 7.2 Which side widens

"Widen on a side" means the opposite face stays put, APEx moves 1.5 m toward the widened side, and the near ORR / Transvalley pair moves 3.0 m.

The sides, going north from CUT. Distances are along the APEx Dayton track from the end of the CUT north throat tracks.

| Stretch | Widen on |
|---|---|
| The straight north from CUT (due north, to about 1,250 m) | the Exposition Boulevard (west) side |
| The turn to the northwest (heading about 325°, about 1,250-2,200 m) | the Spring Grove Avenue (northeast) side |
| The turn back north at Hopple, then north to Queen Street | J1's (east) side |
| North of Queen Street | the north (northwest) side |

- **Side switches** happen inside the curves, with every track redrawn as a single-radius curve.
- **The CUT north throat:** the widening tapers out there, before the platforms.
- **Queen Street** is the former New street M4 (layout streets SMV0005 and SMV0006, extended east to (712436, 4336212)).
- **J1 and Queen:** J1 ends at Queen at about (712360, 4336212). J1's 18.3 m right of way already reaches inside the east face there. Push the curve slightly north so the widened structure clears that corner.
- **North of Queen Street** (heading about 32° toward Ludlow): widen on the north (northwest) side (Ben).

### 7.3 Shops in the arcade

**The arcade is not load-bearing** (Ben). The viaduct is an embanked structure faced to look like a continuous arcade. The look was chosen to show off Art Deco and to echo the CUT's semicircular facade.

**Shops and boutiques may be cut into the embankment** behind the blind arches:

- each is a cell with its own structure (concrete cross walls and a roof slab under the fill);
- two or three shopfronts sit in each facade arch, glazed to the arch's curve;
- the middle of the embankment stays solid, so the masonry catenary pylons stand on solid piers;
- there is about 5.4 m to the fascia crown, enough for a mezzanine across the middle.

**The Deck's per-block switch** becomes three states: blind, shops, open.

**Notes:** a waterproof membrane under the ballast; noise and vibration from the tracks overhead; services and fire separation in each cell.

### 7.4 Frontage streets for the shops

**Type (Ben, 28 October):**

- **As built, at opening:** a one-way street with parking on both sides and a wide sidewalk along the arcade.
- **Today:** converted to pedestrian only. The date of the conversion is not set.

**Section (drawing values, about 15 m in all):**

| Part | Width |
|---|---|
| Sidewalk along the arcade | 4.5 m |
| Parking | 2.4 m |
| Travel lane, one way | 3.4 m |
| Parking | 2.4 m |
| Sidewalk on the block side | 2.4 m |

**Direction:** each street's direction is not set.

**Today's pedestrian street:** it keeps a clear 20 ft (6.1 m) fire lane through it (International Fire Code), since the shops have no rear access.

- **Both sides of the viaduct from Hopple to Bank:** add these corridors.
- **Findlay to Wade:** maybe add them as well.
- **Wade to Kenner:** use McLean.
- **The west side:** Horne can be shifted and extended north, parallel to the viaduct.
- **North of Hopple:** MT (west) and J1 (east) are the frontage streets (section 5).
- **Placement:** set the corridors against the widened faces.

## Sources

- FHWA, "Right of Passage: the controversy over vertical clearance" (14 ft in 1956, 16 ft in 1960).
- TxDOT Roadway Design Manual 4.8.6 (vertical clearance; 14.5 ft absolute minimum with resurfacing allowance).
- New Flyer Xcelsior (Wikipedia): 3.20 m diesel, 3.38 m CNG and battery, 2.59 m wide.
- Skew arch (Wikipedia): skew arches built to a crossing of about 25° (Southdown Road, Harpenden); girders or a squared road beyond that.
