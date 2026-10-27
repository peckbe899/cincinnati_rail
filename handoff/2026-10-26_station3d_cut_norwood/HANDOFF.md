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
