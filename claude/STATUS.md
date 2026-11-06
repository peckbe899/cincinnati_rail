# STATUS (the board; updated at the end of every session)

Updated 2026-11-06 by the cloud session. Checklist: `Hub_Region_Checklist.md`. Branch `hub_region`.

## In flight

| Lane | Session | Doing | Blocked on | Last push |
|---|---|---|---|---|
| A | cloud | slice 0: baseline and gates done; next the rule registry, then the model schema | nothing | this commit |
| B | local 1 | the 1912 ground to `ground/1912/SPEC.md`; registration done (48 sheets, rms 2.06 m), contours in progress | nothing | 1f68094 |
| B | local 2 | Sanborn: tiles back, pipeline in repo, seam report done; next the joint refit of plate positions (ruling b) | nothing | b48bc7f |

## Done today

ground/ consolidated and map 3 moved; region.ground compositor, parametric works, catalogue and map; rulings of 6 Nov
in the ledger; roadmap, checklist, working method, code scrutiny; node_modules and .venv out of git; baseline
captured (41 routes every 5 m, 17 Metro run times, issues) and the calibration gates pass (Orange 35.82/35.74,
Needham 34.29/33.94 technical).

## Open rulings

See checklist section 6. None blocking today.

## Next checkpoint

When the 1912 surface lands (STATUS.json done) or the Sanborn refit reports: merge main, rerun every test, update.
