# STATUS (the board; updated at the end of every session)

Updated 22 November 2026 by the cloud session. Checklist: `Hub_Region_Checklist.md`. Spec: `Hub_Region_Architecture.md`.
Branch `hub_region`.

## In flight

| Lane | Session | Doing | Blocked on | Last push |
|---|---|---|---|---|
| A | cloud | increment 1 of the new hub done; next increment 2 (run times on the sheet) | Windows CI green; doctor on Ben's machine | 51c551e |
| B | local 1 | the 1912 ground to `ground/1912/SPEC.md` (registration done; contours) | nothing | 1f68094 |
| B | local 2 | Sanborn: new plates (25, 28, 39, 40 built), line editor and rail rules | nothing | see git log |

## Done 21 to 22 November

The hub architecture (`Hub_Region_Architecture.md`, decisions 9.9 to 9.30) and increment 1 built on it: one record
store with layers (imports, old hub, main, scenarios), changesets, an outbox, conflicts and rebase, seeds per layer,
backups; the FastAPI server with SSE; jobs keyed by content; the TypeScript engine with `vertical.rail@1` in a Node
sidecar and in the browser (41 of 41 baseline routes within 0.5 mm); the Metro import with stable ids; the app (map,
Line 6 sheet, inspector, jobs, review, scenarios); `crhub` launchers, doctor, data tiers, CI on Ubuntu and Windows.
Tests: pytest 475 with 1 strict xfail, engine 32, app 67, Playwright 13.

## For Ben

- First run: `region/README.md`, "First run on Windows, step by step". Send back `.\crhub doctor` if it fails.
- Rulings with defaults the build already takes: chainage stays UTM grid length (9.14); `var` under
  `%LOCALAPPDATA%\CincinnatiRail\hub` (9.22); port 8766; uv optional (the pip path works); Keep mine after a stale save
  is a three-way merge for every kind, profiles included; a registry override without a ruling is listed, not refused
  (9.25); `ground_profile` still stores decimetres while 9.15 says metres (lean: convert in increment 2); merge `hub_region` into `main` once Windows CI
  is green (9.24).

## Next checkpoint

Increment 2 gate: edit a Line 6 PVI, see the run time change within 10 s, Line 6 within 1 % of the baseline.
