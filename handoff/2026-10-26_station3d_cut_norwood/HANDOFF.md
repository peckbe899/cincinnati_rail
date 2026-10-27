# Station 3D: CUT and Norwood Central structures (from a chat session, 2026-10-26)

A chat session made these changes directly, which it should not have done; they are here for the Claude Code session to review and apply. Nothing outside this folder was changed.

Already live from the chat session: Station 3D page version 5 (this `page_index.html`) and a new snapshot in its database (`snapshots/region`, parts now include `context-*` and `gtiles-*`).

Files (copies of the changed files, flattened):

- `context3d.py` → `tools/station3d/context3d.py` (new)
- `sync.py` → `tools/station3d/sync.py`
- `page_index.html` → `tools/station3d/page/index.html`
- `station3d_README.md` → `tools/station3d/README.md` (new section "CUT and Norwood Central structures")
- `test_context.js` → `tools/station3d/test_context.js` (new)
- `make_profile_context.py` → `tools/make_profile_context.py` (split into `build()` and `main()`; output unchanged)
- `changes.patch`: the same changes as a diff against `claude/stoic-cray-fqf881` at ee96c44

## Prompt for Claude Code

Review handoff/2026-10-26_station3d_cut_norwood (HANDOFF.md). It draws the CUT and Norwood Central structures, platforms and finished ground in Station 3D, per Ben's 26 October rulings in the README section. Apply it to tools/ if it holds up (or redo it your way), run the tests, the sync and the render checks, publish the page and snapshot, then delete the handoff folder.

## Structure types at CUT (Ben, 26 October): read before applying

The handoff draws every CUT structure as a deck on piers set across the tracks every 20 m. That is wrong. Use these instead:

| Structure | Type |
|---|---|
| The fan from W 9th to W Liberty (`CUT platform deck` and the throats) | Embankment, with bridges over the streets as at Amsterdam Centraal. Streets crossing it in the Deck: W 9th, Richmond, Court, Gest, Oehler, Clark, Courtland, Flint, Wade, Wilstach, W Liberty |
| South approach (`CUT approach viaduct (south)`), W 9th to the Cardinal crossing | Arch viaduct. The arch viaduct is only for the wide multi-track structure and ends at the Cardinal crossing, where the tracks split (the Cardinal branch leaves the approach at about E 712,784, N 4,331,400 in the Deck) |
| South of the Cardinal crossing (APEx to the bridge, CVG Express) | Normal viaducts |
| North arch viaduct (wide trunk) | Arch viaduct |
| Intercity and C&O pairs (`Intercity pair: viaduct`, `C&O pair: viaduct`, the TRIMET C&O viaduct) | Normal viaducts, not arch viaducts. Their descents are embankments with blind (fake) arches on the faces, no real arches |

- Arches run parallel to the streets: each arch spans a street, so the piers stand along the street edges, not across the tracks at a fixed spacing.
- These are drawing rules for the structure type; levels are unchanged.
- The Rail Profiles context (`tools/make_profile_context.py`, `data/profile/context/lines.json`) still treats the fan as a viaduct with an arch underside 1.6 m below the rail. Under an embankment a line crosses in the open only at a street bridge, so its clearance checks need the same change.
