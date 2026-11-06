# Baseline (checklist 2.0.10)

Captured 2026-11-06. Sources: Ben's hub work folder (snapshot synced 2026-11-05T16:27:44Z), railsim on the configs.

The rebuild compares every route's solved rail and structure types against `profiles/<route>.json` (every 5 m, rail in m, types
run-length coded) and every service's run time against `runtimes.json`; a difference is classed same, rule fix with its rule id,
or unexplained (must be zero). `issues.json` is the old 3D build's issue list. `platforms.json` and `approaches.json` are the
page's platform and approach records.

| Route | samples | step | saved | types |
|---|---|---|---|---|
| CVG_Express | 3830 | 5 | True | atgrade, cutcover, deep, elevated, trough |
| Line_1 | 4101 | 5 | True | atgrade, cutcover, deep, elevated, shield, trough |
| Line_10 | 4455 | 5 | False | atgrade, cutcover, deep, elevated, shield, sunk, trough |
| Line_11 | 6011 | 5 | False | atgrade, cutcover, deep, elevated, shield, sunk, trough |
| Line_12 | 4940 | 5 | True | cutcover, deep, shield |
| Line_13 | 5309 | 5 | False | atgrade, cutcover, deep, elevated, trough |
| Line_14 | 7226 | 5 | True | atgrade, cutcover, deep, elevated, trough |
| Line_2 | 4006 | 5 | True | atgrade, cutcover, shield, sunk, trough |
| Line_2b | 1015 | 5 | True | atgrade, cutcover, shield, trough |
| Line_3 | 5056 | 5 | True | atgrade, cutcover, deep, elevated, shield, sunk, trough |
| Line_4 | 4661 | 5 | True | cutcover, deep, shield, trough |
| Line_5 | 6321 | 5 | True | cutcover, deep, shield, trough |
| Line_6 | 5908 | 5 | True | atgrade, cutcover, deep, shield, sunk, trough |
| Line_7 | 5894 | 5 | True | cutcover, deep, shield, trough |
| Line_8 | 3803 | 5 | True | atgrade, cutcover, deep, elevated, shield, sunk, trough |
| Line_9 | 5568 | 5 | True | atgrade, cutcover, deep, elevated, shield, trough |
| RER_A_blueash | 2877 | 5 | True | atgrade, cutcover, elevated, shield, trough |
| RER_A_colerain | 2220 | 5 | True | atgrade, cutcover, deep, elevated, shield, trough |
| RER_A_cumminsville | 789 | 5 | True | elevated |
| RER_A_milford | 4301 | 5 | True | atgrade, cutcover, elevated, trough |
| RER_A_trunk | 2154 | 5 | True | atgrade, cutcover, deep, elevated, shield, trough |
| RER_A_westwood | 4356 | 5 | True | atgrade, cutcover, deep, elevated, shield, trough |
| RER_A_wyoming | 2669 | 5 | True | atgrade, cutcover, elevated, trough |
| RER_B_cvg | 3282 | 5 | True | atgrade, cutcover, deep, elevated, shield, trough |
| RER_B_decoursey | 1013 | 5 | True | atgrade, elevated, trough |
| RER_B_highland | 1199 | 5 | True | atgrade, elevated |
| RER_B_latonia | 747 | 5 | True | atgrade, cutcover, deep, elevated, shield, trough |
| RER_B_trunk | 4867 | 5 | True | atgrade, cutcover, deep, elevated, shield, sunk, trough |
| RER_C_cvg | 1149 | 5 | True | atgrade, cutcover, deep, elevated, shield, sunk, trough |
| RER_C_eastgate | 1431 | 5 | True | atgrade, elevated, trough |
| RER_C_saylerpark | 1852 | 5 | True | atgrade |
| RER_C_trunk | 6964 | 5 | True | atgrade, cutcover, deep, elevated, shield, sunk, trough |
| RER_C_withamsville | 872 | 5 | True | atgrade, elevated |
| RER_D_coldspring | 2404 | 5 | True | atgrade, cutcover, elevated, shield, trough |
| RER_D_ross | 4519 | 5 | True | atgrade, cutcover, elevated, shield, trough |
| RER_D_trunk | 5158 | 5 | True | atgrade, cutcover, deep, elevated, shield, sunk, trough |
| RER_E_cvg | 2646 | 5 | True | atgrade, cutcover, elevated, trough |
| RER_E_kenton | 540 | 5 | True | atgrade, cutcover, trough |
| RER_E_napoleon | 298 | 5 | True | atgrade, trough |
| RER_E_trunk | 7451 | 5 | True | atgrade, cutcover, deep, elevated, shield, sunk, trough |
| RER_E_williamstown | 251 | 5 | True | atgrade, trough |

Run times: `python tests/baseline/capture.py --runtimes metro` here, `--runtimes commuter` on Ben's machine (the TRI configs read ground outside the core).
