# Handoff to the code session: minimum cover over bored Metro tubes

Chat session, 28 October 2026. For the hub repo github.com/peckbe899/cincinnati_rail, branch claude/stoic-cray-fqf881. The chat session has not touched the repo. Ben's rulings are marked "Ben"; tube sizes are from `data/profile/metro_structure.json`.

## 1. Rule

Ben, 28 October: every shield-driven tube (shallow shield, deep tube and the double-track bore) needs at least one outside diameter of ground over its crown. The rule of thumb for shield and TBM tunnels is cover of at least one diameter: below that the ground can't arch over the tube.

**What it replaces:** today's split, which allows 2.0 m with the tube top above the water table (140 m) and one diameter below it. In `profiles.html`, `reqCover` returns one outside diameter for every tube, and `TUBE_COVER_HIGH` and the water-table split for cover go. The river rule (rail at least 7.5 m below the bed) is unchanged.

## 2. Minimum rail depth

Crown above the rail plus one diameter:

| Tube | Crown above rail | Cover | Minimum rail depth |
|---|---|---|---|
| Type A | 4.60 m | 5.50 m | 10.10 m |
| Type C | 4.95 m | 5.90 m | 10.85 m |
| Double-track bore | 6.50 m | 9.00 m | 15.50 m |

Shallower than that is cut and cover, as now. Station boxes are unaffected.

## 3. Stacked tubes

The rule applies to the top tube. The lower tube is governed by its separation from the tube above (today's crossing rule: upper floor + 0.5 m + lower top). For type A that puts the lower rail at least 0.90 + 0.50 + 4.60 = 6.0 m below the upper rail, so at least 16.1 m deep. The chat found no firm figure for ground between stacked bored tubes, so the 0.5 m stands until Ben rules.

## 4. Report back to Ben

Work out from the current profiles which stations and running tunnels change from shield to cut and cover under the new minimum, and list them.

Log the change in `claude/Station_3D_Log.md`.

## Sources

- SI Engineering, "Scale factors of large-diameter TBM built tunnels": ground cover of at least one tunnel diameter as a rule of thumb.
- Frontiers in Earth Science (2023), "Face stability of shallow shield tunnels in sand": with cover of one diameter or less, the face collapse zone reaches the surface.
