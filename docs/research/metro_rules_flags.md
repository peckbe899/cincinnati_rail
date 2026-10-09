# Metro profile rules: flags by line

Generated headless from the Rail Profiles page (Ben's saved profiles from the page database, solver defaults elsewhere) on the 2026-10-09 ground with the canon Ohio and Licking riverbed, after Ben's rules and rulings of 2026-10-09:

1. Metro structures from top of rail: open trough where the rail is less than 4.6 m down (no cover rule); box 1.0 below / 4.6 to top; twin tube 0.68 / 4.08 (4.76 m OD) for deep tube, Lines 1-7 shield and every river crossing; double-track bore 3.2 / 5.8 (9.0 m OD) for Lines 8-14 shield. RER river crossings: sunk box sections in a dredged trench (RER box 1.0 / 6.6).
2. Crossings: rail-to-rail separation >= upper line's below-rail + 0.5 m + lower line's rail-to-top (both systems). A line in the open (viaduct, at grade, trough) underneath needs its clear height: Metro 4.2 m, RER 5.8 m. Below-rail: viaduct deck 1.5 m Metro / 2.0 m RER, track bed 0.8 m. Two lines at grade are flagged as needing a grade separation.
3. Cover over the top (Metro): tube or bore with its top above 140.0 m 2.0 m, at or below one OD (thinner is typed cut and cover). Box roof: cover under 0.6 m (rail 4.6 to 5.2 m down) is a WARNING, the roof forming the street; a roof above ground is an error.
4. Rivers: in tunnel inside a river range, rail <= bed - 7.5 m (Metro) / bed - 9.1 m (RER); bed = the canon riverbed (Ohio, Licking) or pool - 3 m (Little Miami, no survey). The solvers hold it for default-solved lines; saved profiles are only flagged.

Chainages are the line's own (km+m). 'Saved' = Ben's saved profile; 'default' = the solver default.

## Summary

| Line | Profile | Crossings (2) | Cover errors (3) | Thin cover warnings (3) | Rivers (4) |
|---|---|---|---|---|---|
| Line 1 | saved | 14 | 0 | 16 | 1 |
| Line 2 | saved | 16 | 0 | 16 | 0 |
| Line 2b | default | 1 | 0 | 4 | 0 |
| Line 3 | default | 13 | 0 | 17 | 0 |
| Line 4 | saved | 18 | 0 | 17 | 0 |
| Line 5 | saved | 13 | 0 | 12 | 0 |
| Line 6 | saved | 13 | 0 | 34 | 0 |
| Line 7 | default | 21 | 0 | 33 | 0 |
| Line 8 | default | 17 | 0 | 9 | 0 |
| Line 9 | default | 15 | 0 | 31 | 0 |
| Line 10 | default | 13 | 0 | 10 | 0 |
| Line 11 | default | 4 | 0 | 29 | 0 |
| Line 12 | default | 10 | 0 | 37 | 0 |
| Line 13 | default | 11 | 0 | 21 | 0 |
| Line 14 | default | 8 | 0 | 29 | 0 |
| RER-1 | saved | 16 | 0 | 0 | 0 |
| RER-2 | saved | 10 | 0 | 0 | 1 |
| RER-3 | default | 3 | 0 | 0 | 0 |
| RER-4 | default | 13 | 0 | 0 | 1 |
| RER-5 | default | 18 | 0 | 0 | 1 |
| **Total** | | 247 | 0 | 315 | 4 |

## Line 1 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 0+003 | 2 crossing | 0.20 m under Line 14 at 0+003; needs 6.10 m (box over box) |
| 3+235 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.47 m from 3+235 to 3+235 (under 0.6 m) |
| 3+470 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.00 m from 3+465 to 3+475 (under 0.6 m) |
| 4+150 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.18 m from 4+105 to 4+195 (under 0.6 m) |
| 4+790 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.22 m from 4+785 to 4+795 (under 0.6 m) |
| 6+079 | 2 crossing | 7.29 m over RER-2 at 6+079; needs 7.80 m (viaduct over at grade) |
| 6+675 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.18 m from 6+675 to 6+675 (under 0.6 m) |
| 7+747 | 2 crossing | 3.04 m under Line 13 at 7+747; needs 8.30 m (double-track bore over box) |
| 8+155 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.37 m from 8+155 to 8+155 (under 0.6 m) |
| 8+275 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.36 m from 8+275 to 8+275 (under 0.6 m) |
| 8+465 | 2 crossing | 0.11 m over Line 8 at 8+465; needs 6.10 m (box over box) |
| 8+590 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 8+575 to 8+605 (under 0.6 m) |
| 8+710 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.07 m from 8+705 to 8+715 (under 0.6 m) |
| 8+786 | 2 crossing | 1.58 m under Line 9 at 8+787; needs 6.10 m (box over box) |
| 11+900 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 11+895 to 11+905 (under 0.6 m) |
| 11+982 | 2 crossing | 2.43 m over RER-5 at 11+982; needs 7.90 m (open trough over box) |
| 11+982 | 2 crossing | 3.52 m over Line 10 at 11+982; needs 5.90 m (open trough over box) |
| 12+325 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 12+285 to 12+365 (under 0.6 m) |
| 12+524 | 2 crossing | 5.14 m over RER-4 at 12+524; needs 7.90 m (open trough over box) |
| 12+527 | 2 crossing | 5.17 m over RER-1 at 12+527; needs 7.90 m (open trough over box) |
| 12+552 | 2 crossing | 4.42 m over Line 8 at 12+552; needs 5.90 m (open trough over box) |
| 12+690 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.14 m from 12+685 to 12+695 (under 0.6 m) |
| 12+945 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.35 m from 12+945 to 12+945 (under 0.6 m) |
| 13+124 | 2 crossing | 0.29 m under Line 4 at 13+124; needs 5.78 m (twin tube over box) |
| 13+509 | 2 crossing | 1.90 m over Line 7 at 13+509; needs 5.58 m (box over twin tube) |
| 13+555 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.42 m from 13+555 to 13+555 (under 0.6 m) |
| 14+916 | 2 crossing | 4.21 m over Line 2 at 14+916; needs 5.26 m (twin tube over twin tube) |
| 15+488 | 2 crossing | 4.64 m under Line 6 at 15+488; needs 5.78 m (twin tube over box) |
| 16+406 | 4 river | Under the Ohio River from 16+348 to 16+674 the rail is up to 8.41 m above bed − 7.5 m (worst at 16+406) |
| 18+915 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.35 m from 18+915 to 18+915 (under 0.6 m) |
| 19+285 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.28 m from 19+285 to 19+285 (under 0.6 m) |

## Line 2 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 0+295 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.55 m from 0+295 to 0+295 (under 0.6 m) |
| 1+606 | 2 crossing | 1.67 m under Line 14 at 1+606; needs 6.10 m (box over box) |
| 3+815 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.50 m from 3+815 to 3+815 (under 0.6 m) |
| 3+940 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 3+915 to 3+965 (under 0.6 m) |
| 4+475 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.16 m from 4+465 to 4+485 (under 0.6 m) |
| 4+655 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.49 m from 4+655 to 4+655 (under 0.6 m) |
| 5+020 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.00 m from 5+015 to 5+025 (under 0.6 m) |
| 5+058 | 2 crossing | 1.92 m over Line 3 at 5+058; needs 5.38 m (open trough over twin tube) |
| 6+220 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.14 m from 6+215 to 6+225 (under 0.6 m) |
| 6+505 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.04 m from 6+475 to 6+535 (under 0.6 m) |
| 7+489 | 2 crossing | 1.53 m under Line 13 at 7+489; needs 6.10 m (box over box) |
| 8+055 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.44 m from 8+055 to 8+055 (under 0.6 m) |
| 8+395 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.51 m from 8+395 to 8+395 (under 0.6 m) |
| 9+017 | 2 crossing | 1.02 m under Line 9 at 9+017; needs 8.30 m (double-track bore over box) |
| 9+479 | 2 crossing | 2.47 m over RER-5 at 9+479; needs 8.68 m (twin tube over bored tube) |
| 9+690 | 2 crossing | 0.88 m under Line 8 at 9+690; needs 5.26 m (twin tube over twin tube) |
| 10+253 | 2 crossing | 1.45 m under RER-5 at 10+253; needs 5.58 m (bored tube over twin tube) |
| 11+982 | 2 crossing | 0.69 m under RER-5 at 11+982; needs 6.10 m (box over box) |
| 11+990 | 2 crossing | 0.30 m under Line 10 at 11+990; needs 6.10 m (box over box) |
| 12+388 | 2 crossing | 0.39 m under Line 8 at 12+388; needs 6.10 m (box over box) |
| 12+952 | 2 crossing | 0.50 m under Line 4 at 12+952; needs 5.78 m (twin tube over box) |
| 13+245 | 2 crossing | 2.59 m under RER-4 at 13+245; needs 6.10 m (box over box) |
| 13+247 | 2 crossing | 3.16 m under RER-1 at 13+247; needs 6.10 m (box over box) |
| 13+319 | 2 crossing | 4.21 m under Line 1 at 13+319; needs 5.78 m (twin tube over box) |
| 14+146 | 2 crossing | 1.50 m under RER-3 at 14+147; needs 5.58 m (box over twin tube) |
| 15+954 | 2 crossing | 1.36 m over Line 6 at 15+954; needs 5.58 m (box over twin tube) |
| 16+040 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 16+035 to 16+045 (under 0.6 m) |
| 16+310 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 16+305 to 16+315 (under 0.6 m) |
| 16+875 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.20 m from 16+835 to 16+915 (under 0.6 m) |
| 17+135 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.30 m from 17+135 to 17+135 (under 0.6 m) |
| 17+220 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.52 m from 17+205 to 17+235 (under 0.6 m) |
| 17+745 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 17+705 to 17+785 (under 0.6 m) |

## Line 2b (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+345 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 0+335 to 0+355 (under 0.6 m) |
| 0+845 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.20 m from 0+845 to 0+845 (under 0.6 m) |
| 1+135 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.38 m from 1+135 to 1+135 (under 0.6 m) |
| 3+525 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.48 m from 3+525 to 3+525 (under 0.6 m) |
| 4+107 | 2 crossing | 0.16 m over Line 11 at 4+107; needs 6.10 m (box over box) |

## Line 3 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+140 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 0+135 to 0+145 (under 0.6 m) |
| 0+358 | 2 crossing | 1.89 m over Line 14 at 0+358; needs 6.98 m (twin tube over double-track bore) |
| 0+370 | 2 crossing | 3.47 m over Line 4 at 0+371; needs 5.26 m (twin tube over twin tube) |
| 0+395 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.39 m from 0+395 to 0+395 (under 0.6 m) |
| 1+985 | 2 crossing | 3.94 m over Line 7 at 1+985; needs 5.58 m (box over twin tube) |
| 2+878 | 2 crossing | 2.50 m under Line 6 at 2+878; needs 6.10 m (box over box) |
| 3+275 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 3+265 to 3+285 (under 0.6 m) |
| 3+795 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.09 m from 3+785 to 3+805 (under 0.6 m) |
| 4+888 | 2 crossing | 1.92 m under Line 2 at 4+888; needs 5.90 m (open trough over box) |
| 6+155 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.47 m from 6+155 to 6+155 (under 0.6 m) |
| 9+019 | 2 crossing | 0.80 m under Line 8 at 9+019; needs 6.10 m (box over box) |
| 9+148 | 2 crossing | 0.01 m over Line 13 at 9+148; needs 6.10 m (box over box) |
| 9+275 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.53 m from 9+265 to 9+285 (under 0.6 m) |
| 9+545 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.19 m from 9+515 to 9+575 (under 0.6 m) |
| 10+481 | 2 crossing | 2.60 m over Line 12 at 10+481; needs 7.30 m (box over double-track bore) |
| 10+675 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 10+615 to 10+735 (under 0.6 m) |
| 11+036 | 2 crossing | 0.70 m under Line 9 at 11+036; needs 6.10 m (box over box) |
| 12+860 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.00 m from 12+815 to 12+905 (under 0.6 m) |
| 14+344 | 2 crossing | 4.32 m over RER-5 at 14+344; needs 8.10 m (box over box) |
| 14+344 | 2 crossing | 1.86 m under Line 10 at 14+344; needs 6.10 m (box over box) |
| 14+790 | 2 crossing | 2.21 m under RER-2 at 14+790; needs 6.10 m (bored tube over box) |
| 18+471 | 2 crossing | 0.07 m under Line 6 at 18+471; needs 5.78 m (twin tube over box) |
| 19+525 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.26 m from 19+525 to 19+525 (under 0.6 m) |
| 20+070 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 20+065 to 20+075 (under 0.6 m) |
| 20+550 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 20+535 to 20+565 (under 0.6 m) |
| 21+020 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.20 m from 21+015 to 21+025 (under 0.6 m) |
| 21+805 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.42 m from 21+805 to 21+805 (under 0.6 m) |
| 22+480 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.07 m from 22+475 to 22+485 (under 0.6 m) |
| 23+155 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.39 m from 23+155 to 23+155 (under 0.6 m) |
| 25+235 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.39 m from 25+235 to 25+235 (under 0.6 m) |

## Line 4 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 0+968 | 2 crossing | 3.06 m under Line 9 at 0+968; needs 5.58 m (box over twin tube) |
| 2+375 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 2+355 to 2+395 (under 0.6 m) |
| 2+525 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.28 m from 2+525 to 2+525 (under 0.6 m) |
| 3+172 | 2 crossing | 0.09 m over Line 7 at 3+172; needs 5.58 m (box over twin tube) |
| 3+350 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.28 m from 3+345 to 3+355 (under 0.6 m) |
| 4+015 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.45 m from 4+015 to 4+015 (under 0.6 m) |
| 4+365 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.31 m from 4+365 to 4+365 (under 0.6 m) |
| 4+855 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.07 m from 4+815 to 4+895 (under 0.6 m) |
| 11+985 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.15 m from 11+985 to 11+985 (under 0.6 m) |
| 12+116 | 2 crossing | 1.42 m over Line 7 at 12+116; needs 5.58 m (box over twin tube) |
| 12+190 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 12+185 to 12+195 (under 0.6 m) |
| 12+310 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 12+285 to 12+335 (under 0.6 m) |
| 12+920 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.38 m from 12+895 to 12+945 (under 0.6 m) |
| 13+021 | 2 crossing | 0.29 m over Line 1 at 13+021; needs 5.58 m (box over twin tube) |
| 13+140 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 13+135 to 13+145 (under 0.6 m) |
| 13+290 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.20 m from 13+285 to 13+295 (under 0.6 m) |
| 13+784 | 2 crossing | 5.37 m over RER-1 at 13+784; needs 8.10 m (box over box) |
| 13+790 | 2 crossing | 5.18 m over RER-4 at 13+790; needs 8.10 m (box over box) |
| 14+314 | 2 crossing | 0.50 m over Line 2 at 14+314; needs 5.58 m (box over twin tube) |
| 14+887 | 2 crossing | 2.99 m under Line 6 at 14+887; needs 5.26 m (twin tube over twin tube) |
| 15+044 | 2 crossing | 5.70 m over RER-1 at 15+044; needs 8.10 m (box over box) |
| 15+080 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.40 m from 15+055 to 15+105 (under 0.6 m) |
| 15+963 | 2 crossing | 5.21 m over Line 10 at 15+963; needs 5.58 m (box over twin tube) |
| 18+575 | 2 crossing | 4.41 m under Line 9 at 18+575; needs 6.10 m (box over box) |
| 19+210 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 19+205 to 19+215 (under 0.6 m) |
| 19+260 | 2 crossing | 4.62 m over Line 7 at 19+260; needs 5.38 m (open trough over twin tube) |
| 19+315 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 19+315 to 19+315 (under 0.6 m) |
| 19+822 | 2 crossing | 4.12 m under Line 12 at 19+822; needs 6.10 m (box over box) |
| 20+575 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.37 m from 20+575 to 20+575 (under 0.6 m) |
| 20+606 | 2 crossing | 3.68 m over Line 12 at 20+606; needs 5.90 m (open trough over box) |
| 20+720 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.16 m from 20+715 to 20+725 (under 0.6 m) |
| 21+014 | 2 crossing | 0.59 m over Line 13 at 21+014; needs 7.30 m (box over double-track bore) |
| 21+112 | 2 crossing | 4.59 m under RER-1 at 21+112; needs 5.38 m (at grade over twin tube) |
| 23+328 | 2 crossing | 3.47 m under Line 3 at 23+328; needs 5.78 m (twin tube over box) |
| 23+379 | 2 crossing | 1.63 m under Line 14 at 23+379; needs 6.10 m (box over box) |

## Line 5 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 0+265 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.28 m from 0+225 to 0+305 (under 0.6 m) |
| 1+380 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 1+335 to 1+425 (under 0.6 m) |
| 1+540 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 1+535 to 1+545 (under 0.6 m) |
| 1+645 | 2 crossing | 3.14 m over Line 14 at 1+645; needs 7.30 m (box over double-track bore) |
| 1+905 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.40 m from 1+905 to 1+905 (under 0.6 m) |
| 2+215 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.27 m from 2+215 to 2+215 (under 0.6 m) |
| 8+910 | 2 crossing | 0.00 m over Line 13 at 8+910; needs 7.30 m (box over double-track bore) |
| 10+111 | 2 crossing | 4.30 m under Line 12 at 10+111; needs 5.58 m (box over twin tube) |
| 10+801 | 2 crossing | 5.60 m under Line 9 at 10+801; needs 6.10 m (box over box) |
| 13+707 | 2 crossing | 0.42 m over Line 10 at 13+707; needs 7.30 m (box over double-track bore) |
| 13+807 | 2 crossing | 1.45 m under RER-5 at 13+807; needs 5.58 m (box over twin tube) |
| 14+202 | 2 crossing | 3.67 m over RER-4 at 14+202; needs 7.78 m (twin tube over box) |
| 14+202 | 2 crossing | 3.67 m over RER-1 at 14+202; needs 7.78 m (twin tube over box) |
| 14+290 | 2 crossing | 0.53 m under Line 8 at 14+290; needs 6.10 m (box over box) |
| 14+330 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.52 m from 14+315 to 14+345 (under 0.6 m) |
| 15+451 | 2 crossing | 1.11 m over RER-4 at 15+451; needs 7.78 m (twin tube over box) |
| 15+458 | 2 crossing | 1.23 m over RER-1 at 15+458; needs 7.78 m (twin tube over box) |
| 16+980 | 2 crossing | 2.20 m under RER-1 at 16+981; needs 6.10 m (box over box) |
| 17+138 | 2 crossing | 1.26 m under Line 7 at 17+138; needs 5.78 m (twin tube over box) |
| 18+905 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.58 m from 18+895 to 18+915 (under 0.6 m) |
| 19+970 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.35 m from 19+945 to 19+995 (under 0.6 m) |
| 20+365 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 20+295 to 20+435 (under 0.6 m) |
| 24+370 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.44 m from 24+325 to 24+415 (under 0.6 m) |
| 28+945 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.24 m from 28+945 to 28+945 (under 0.6 m) |
| 29+070 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.09 m from 29+065 to 29+075 (under 0.6 m) |

## Line 6 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 1+053 | 2 crossing | 2.50 m over Line 3 at 1+053; needs 5.58 m (box over twin tube) |
| 1+055 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.37 m from 1+055 to 1+055 (under 0.6 m) |
| 2+025 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.20 m from 2+025 to 2+025 (under 0.6 m) |
| 2+925 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.55 m from 2+925 to 2+925 (under 0.6 m) |
| 3+010 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 3+005 to 3+015 (under 0.6 m) |
| 3+770 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 3+725 to 3+815 (under 0.6 m) |
| 4+515 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.15 m from 4+495 to 4+535 (under 0.6 m) |
| 4+760 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 4+755 to 4+765 (under 0.6 m) |
| 4+830 | 2 crossing | 4.33 m over Line 13 at 4+830; needs 7.30 m (box over double-track bore) |
| 5+015 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 5+005 to 5+025 (under 0.6 m) |
| 5+440 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.30 m from 5+435 to 5+445 (under 0.6 m) |
| 5+939 | 2 crossing | 5.17 m over Line 9 at 5+939; needs 7.30 m (box over double-track bore) |
| 9+390 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.19 m from 9+305 to 9+475 (under 0.6 m) |
| 9+676 | 2 crossing | 2.99 m over Line 4 at 9+676; needs 5.58 m (box over twin tube) |
| 9+898 | 2 crossing | 4.69 m under Line 7 at 9+898; needs 5.26 m (twin tube over twin tube) |
| 9+926 | 2 crossing | 0.30 m over RER-1 at 9+926; needs 7.78 m (twin tube over box) |
| 10+039 | 2 crossing | 4.64 m over Line 1 at 10+039; needs 5.58 m (box over twin tube) |
| 10+375 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.34 m from 10+375 to 10+375 (under 0.6 m) |
| 10+515 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.50 m from 10+515 to 10+515 (under 0.6 m) |
| 10+844 | 2 crossing | 2.72 m under RER-3 at 10+844; needs 5.58 m (box over twin tube) |
| 13+225 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 13+215 to 13+235 (under 0.6 m) |
| 13+455 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.58 m from 13+455 to 13+455 (under 0.6 m) |
| 13+963 | 2 crossing | 1.36 m under Line 2 at 13+963; needs 5.78 m (twin tube over box) |
| 14+539 | 2 crossing | 0.07 m over Line 3 at 14+539; needs 5.58 m (box over twin tube) |
| 15+065 | 2 crossing | 0.80 m under Line 11 at 15+065; needs 6.10 m (box over box) |
| 18+790 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.09 m from 18+775 to 18+805 (under 0.6 m) |
| 18+905 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.09 m from 18+895 to 18+915 (under 0.6 m) |
| 19+100 | 2 crossing | 3.25 m over Line 11 at 19+101; needs 5.90 m (open trough over box) |
| 19+103 | 2 crossing | 3.54 m under RER-2 at 19+103; needs 5.50 m (at grade over open trough) |
| 19+120 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 19+115 to 19+125 (under 0.6 m) |
| 20+710 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.08 m from 20+705 to 20+715 (under 0.6 m) |
| 20+990 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 20+985 to 20+995 (under 0.6 m) |
| 21+845 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 21+765 to 21+925 (under 0.6 m) |
| 22+415 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.00 m from 22+415 to 22+415 (under 0.6 m) |
| 22+955 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 22+905 to 23+005 (under 0.6 m) |
| 23+420 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.22 m from 23+415 to 23+425 (under 0.6 m) |
| 23+625 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 23+615 to 23+635 (under 0.6 m) |
| 24+495 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.16 m from 24+485 to 24+505 (under 0.6 m) |
| 24+700 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 24+695 to 24+705 (under 0.6 m) |
| 26+165 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.25 m from 26+165 to 26+165 (under 0.6 m) |
| 26+455 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.39 m from 26+455 to 26+455 (under 0.6 m) |
| 27+085 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 27+075 to 27+095 (under 0.6 m) |
| 27+820 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.07 m from 27+675 to 27+965 (under 0.6 m) |
| 28+120 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 28+005 to 28+235 (under 0.6 m) |
| 28+300 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 28+295 to 28+305 (under 0.6 m) |
| 29+350 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 29+335 to 29+365 (under 0.6 m) |
| 29+515 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 29+485 to 29+545 (under 0.6 m) |

## Line 7 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+045 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.52 m from 0+045 to 0+045 (under 0.6 m) |
| 1+145 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.42 m from 1+145 to 1+145 (under 0.6 m) |
| 1+305 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.21 m from 1+305 to 1+305 (under 0.6 m) |
| 1+605 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.37 m from 1+605 to 1+605 (under 0.6 m) |
| 1+795 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 1+795 to 1+795 (under 0.6 m) |
| 2+445 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.41 m from 2+445 to 2+445 (under 0.6 m) |
| 4+471 | 2 crossing | 0.09 m under Line 4 at 4+471; needs 5.78 m (twin tube over box) |
| 4+575 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.24 m from 4+575 to 4+575 (under 0.6 m) |
| 5+560 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.08 m from 5+555 to 5+565 (under 0.6 m) |
| 8+495 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.24 m from 8+495 to 8+495 (under 0.6 m) |
| 8+645 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.40 m from 8+645 to 8+645 (under 0.6 m) |
| 9+370 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 9+305 to 9+435 (under 0.6 m) |
| 9+510 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 9+495 to 9+525 (under 0.6 m) |
| 10+325 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.52 m from 10+315 to 10+335 (under 0.6 m) |
| 10+475 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.31 m from 10+405 to 10+545 (under 0.6 m) |
| 11+769 | 2 crossing | 7.14 m over RER-2 at 11+769; needs 7.78 m (twin tube over box) |
| 11+769 | 2 crossing | 0.44 m over RER-4 at 11+769; needs 7.78 m (twin tube over box) |
| 13+304 | 2 crossing | 2.44 m over RER-4 at 13+304; needs 7.78 m (twin tube over box) |
| 13+452 | 2 crossing | 1.53 m over RER-1 at 13+452; needs 7.78 m (twin tube over box) |
| 13+539 | 2 crossing | 0.90 m over Line 8 at 13+539; needs 7.30 m (box over double-track bore) |
| 13+551 | 2 crossing | 1.00 m over Line 10 at 13+551; needs 7.30 m (box over double-track bore) |
| 13+900 | 2 crossing | 5.73 m over RER-5 at 13+900; needs 7.78 m (twin tube over box) |
| 14+100 | 2 crossing | 1.42 m under Line 4 at 14+100; needs 5.78 m (twin tube over box) |
| 15+030 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.07 m from 15+015 to 15+045 (under 0.6 m) |
| 15+090 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.15 m from 15+085 to 15+095 (under 0.6 m) |
| 15+219 | 2 crossing | 1.90 m under Line 1 at 15+219; needs 5.78 m (twin tube over box) |
| 16+167 | 2 crossing | 5.13 m over RER-1 at 16+167; needs 7.78 m (twin tube over box) |
| 16+206 | 2 crossing | 5.32 m over RER-4 at 16+206; needs 7.78 m (twin tube over box) |
| 17+074 | 2 crossing | 4.69 m over Line 6 at 17+075; needs 5.26 m (twin tube over twin tube) |
| 17+117 | 2 crossing | 5.10 m over RER-1 at 17+117; needs 7.78 m (twin tube over box) |
| 17+380 | 2 crossing | 1.26 m over Line 5 at 17+380; needs 5.58 m (box over twin tube) |
| 19+655 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 19+655 to 19+655 (under 0.6 m) |
| 19+845 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.23 m from 19+845 to 19+845 (under 0.6 m) |
| 20+110 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 20+105 to 20+115 (under 0.6 m) |
| 20+365 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.23 m from 20+365 to 20+365 (under 0.6 m) |
| 20+444 | 2 crossing | 0.20 m under Line 12 at 20+444; needs 6.10 m (box over box) |
| 20+555 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.32 m from 20+555 to 20+555 (under 0.6 m) |
| 20+765 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 20+745 to 20+785 (under 0.6 m) |
| 21+045 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.35 m from 21+045 to 21+045 (under 0.6 m) |
| 21+180 | 2 crossing | 2.47 m over Line 9 at 21+180; needs 7.30 m (box over double-track bore) |
| 21+760 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.21 m from 21+755 to 21+765 (under 0.6 m) |
| 21+870 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.04 m from 21+835 to 21+905 (under 0.6 m) |
| 22+148 | 2 crossing | 4.62 m under Line 4 at 22+148; needs 5.90 m (open trough over box) |
| 23+445 | 2 crossing | 3.73 m under Line 13 at 23+445; needs 5.90 m (open trough over box) |
| 24+375 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 24+345 to 24+405 (under 0.6 m) |
| 24+550 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 24+535 to 24+565 (under 0.6 m) |
| 25+145 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 25+115 to 25+175 (under 0.6 m) |
| 26+165 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.30 m from 26+165 to 26+165 (under 0.6 m) |
| 26+294 | 2 crossing | 3.93 m under Line 3 at 26+295; needs 5.26 m (twin tube over twin tube) |
| 27+900 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.00 m from 27+885 to 27+915 (under 0.6 m) |
| 27+985 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 27+965 to 28+005 (under 0.6 m) |
| 28+491 | 2 crossing | 2.28 m over Line 14 at 28+491; needs 7.30 m (box over double-track bore) |
| 28+565 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.34 m from 28+565 to 28+565 (under 0.6 m) |
| 28+745 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.44 m from 28+745 to 28+745 (under 0.6 m) |

## Line 8 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+185 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.04 m from 0+175 to 0+195 (under 0.6 m) |
| 0+562 | 2 crossing | 5.14 m under RER-2 at 0+562; needs 5.90 m (at grade over box) |
| 0+565 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.37 m from 0+565 to 0+565 (under 0.6 m) |
| 0+628 | 2 crossing | 0.80 m over Line 3 at 0+628; needs 5.58 m (box over twin tube) |
| 0+863 | 2 crossing | 0.72 m over Line 13 at 0+863; needs 7.78 m (double-track bore over twin tube) |
| 2+807 | 2 crossing | 0.11 m under Line 1 at 2+807; needs 5.78 m (twin tube over box) |
| 3+586 | 2 crossing | 0.93 m over Line 9 at 3+586; needs 6.10 m (box over box) |
| 4+276 | 2 crossing | 5.10 m over RER-5 at 4+276; needs 8.68 m (twin tube over bored tube) |
| 4+482 | 2 crossing | 0.88 m over Line 2 at 4+482; needs 5.26 m (twin tube over twin tube) |
| 5+166 | 2 crossing | 8.39 m over RER-5 at 5+166; needs 8.68 m (twin tube over bored tube) |
| 6+623 | 2 crossing | 3.57 m under Line 10 at 6+623; needs 6.10 m (box over box) |
| 7+197 | 2 crossing | 0.39 m over Line 2 at 7+197; needs 5.58 m (box over twin tube) |
| 8+262 | 2 crossing | 0.09 m over RER-4 at 8+262; needs 8.10 m (box over box) |
| 8+266 | 2 crossing | 0.03 m over RER-1 at 8+267; needs 8.10 m (box over box) |
| 8+329 | 2 crossing | 4.42 m under Line 1 at 8+329; needs 5.90 m (open trough over box) |
| 8+702 | 2 crossing | 0.53 m over Line 5 at 8+702; needs 6.10 m (box over box) |
| 8+705 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 8+685 to 8+725 (under 0.6 m) |
| 8+955 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 8+905 to 9+005 (under 0.6 m) |
| 9+101 | 2 crossing | 3.38 m over RER-5 at 9+101; needs 8.10 m (box over box) |
| 9+108 | 2 crossing | 0.10 m over Line 10 at 9+108; needs 6.10 m (box over box) |
| 9+232 | 2 crossing | 0.90 m under Line 7 at 9+232; needs 5.78 m (twin tube over box) |
| 13+570 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.31 m from 13+555 to 13+585 (under 0.6 m) |
| 14+005 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.46 m from 14+005 to 14+005 (under 0.6 m) |
| 14+725 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.31 m from 14+725 to 14+725 (under 0.6 m) |
| 18+325 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.39 m from 18+325 to 18+325 (under 0.6 m) |
| 18+715 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.13 m from 18+715 to 18+715 (under 0.6 m) |

## Line 9 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 2+080 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 2+045 to 2+115 (under 0.6 m) |
| 3+749 | 2 crossing | 3.06 m over Line 4 at 3+749; needs 5.58 m (box over twin tube) |
| 5+980 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 5+975 to 5+985 (under 0.6 m) |
| 6+615 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.25 m from 6+615 to 6+615 (under 0.6 m) |
| 7+000 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.19 m from 6+995 to 7+005 (under 0.6 m) |
| 7+300 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 7+295 to 7+305 (under 0.6 m) |
| 8+175 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 8+165 to 8+185 (under 0.6 m) |
| 8+935 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.08 m from 8+925 to 8+945 (under 0.6 m) |
| 9+045 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 9+025 to 9+065 (under 0.6 m) |
| 9+135 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.04 m from 9+125 to 9+145 (under 0.6 m) |
| 9+755 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.57 m from 9+755 to 9+755 (under 0.6 m) |
| 10+555 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.32 m from 10+555 to 10+555 (under 0.6 m) |
| 12+150 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.07 m from 12+145 to 12+155 (under 0.6 m) |
| 12+535 | 2 crossing | 0.00 m under RER-2 at 12+535; needs 7.30 m (box over double-track bore) |
| 12+535 | 2 crossing | 0.03 m under RER-4 at 12+535; needs 7.30 m (box over double-track bore) |
| 12+940 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.21 m from 12+935 to 12+945 (under 0.6 m) |
| 13+445 | 2 crossing | 0.70 m over Line 3 at 13+445; needs 5.58 m (box over twin tube) |
| 14+060 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.27 m from 14+055 to 14+065 (under 0.6 m) |
| 14+625 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.07 m from 14+625 to 14+625 (under 0.6 m) |
| 14+669 | 2 crossing | 1.58 m over Line 1 at 14+669; needs 5.58 m (box over twin tube) |
| 15+130 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 15+125 to 15+135 (under 0.6 m) |
| 15+316 | 2 crossing | 0.93 m under Line 8 at 15+316; needs 6.10 m (box over box) |
| 15+664 | 2 crossing | 1.02 m over Line 2 at 15+664; needs 7.78 m (double-track bore over twin tube) |
| 16+296 | 2 crossing | 3.92 m over RER-5 at 16+297; needs 10.30 m (double-track bore over box) |
| 16+428 | 2 crossing | 5.17 m under Line 6 at 16+428; needs 5.78 m (twin tube over box) |
| 17+055 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.37 m from 17+055 to 17+055 (under 0.6 m) |
| 17+202 | 2 crossing | Crosses RER-1 at grade at 17+202: needs a grade separation |
| 17+480 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.33 m from 17+475 to 17+485 (under 0.6 m) |
| 17+641 | 2 crossing | 4.41 m over Line 4 at 17+641; needs 5.58 m (box over twin tube) |
| 17+895 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 17+885 to 17+905 (under 0.6 m) |
| 18+030 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 18+005 to 18+055 (under 0.6 m) |
| 18+235 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.59 m from 18+235 to 18+235 (under 0.6 m) |
| 18+419 | 2 crossing | 2.47 m under Line 7 at 18+419; needs 6.98 m (twin tube over double-track bore) |
| 18+708 | 2 crossing | 3.37 m under Line 12 at 18+708; needs 6.10 m (box over box) |
| 19+920 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 19+875 to 19+965 (under 0.6 m) |
| 20+615 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.38 m from 20+585 to 20+645 (under 0.6 m) |
| 21+036 | 2 crossing | 0.40 m over Line 13 at 21+036; needs 6.10 m (box over box) |
| 21+095 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.37 m from 21+095 to 21+095 (under 0.6 m) |
| 21+855 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.16 m from 21+855 to 21+855 (under 0.6 m) |
| 23+909 | 2 crossing | 0.10 m under Line 14 at 23+909; needs 6.10 m (box over box) |
| 25+025 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 25+015 to 25+035 (under 0.6 m) |
| 25+240 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.13 m from 25+235 to 25+245 (under 0.6 m) |
| 26+005 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.31 m from 26+005 to 26+005 (under 0.6 m) |
| 26+625 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.26 m from 26+625 to 26+625 (under 0.6 m) |
| 26+885 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 26+885 to 26+885 (under 0.6 m) |
| 26+955 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.19 m from 26+955 to 26+955 (under 0.6 m) |

## Line 10 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+175 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 0+165 to 0+185 (under 0.6 m) |
| 1+885 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.23 m from 1+885 to 1+885 (under 0.6 m) |
| 3+790 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.19 m from 3+785 to 3+795 (under 0.6 m) |
| 4+840 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.58 m from 4+835 to 4+845 (under 0.6 m) |
| 5+045 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.08 m from 5+035 to 5+055 (under 0.6 m) |
| 6+935 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 6+915 to 6+955 (under 0.6 m) |
| 7+080 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 7+055 to 7+105 (under 0.6 m) |
| 11+061 | 2 crossing | 1.00 m under Line 7 at 11+061; needs 5.78 m (twin tube over box) |
| 11+187 | 2 crossing | 0.10 m under Line 8 at 11+187; needs 6.10 m (box over box) |
| 11+196 | 2 crossing | 3.28 m over RER-5 at 11+196; needs 8.10 m (box over box) |
| 11+290 | 2 crossing | 2.72 m over RER-1 at 11+290; needs 10.30 m (double-track bore over box) |
| 11+296 | 2 crossing | 9.32 m over RER-2 at 11+296; needs 11.20 m (double-track bore over bored tube) |
| 11+296 | 2 crossing | 2.95 m over RER-4 at 11+296; needs 10.30 m (double-track bore over box) |
| 11+486 | 2 crossing | 1.97 m over RER-5 at 11+486; needs 8.10 m (box over box) |
| 12+027 | 2 crossing | 0.42 m under Line 5 at 12+027; needs 5.78 m (twin tube over box) |
| 12+446 | 2 crossing | 3.52 m under Line 1 at 12+447; needs 5.90 m (open trough over box) |
| 12+875 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.36 m from 12+855 to 12+895 (under 0.6 m) |
| 12+997 | 2 crossing | 1.86 m over Line 3 at 12+997; needs 5.58 m (box over twin tube) |
| 13+443 | 2 crossing | 0.30 m over Line 2 at 13+443; needs 5.58 m (box over twin tube) |
| 13+738 | 2 crossing | 3.57 m over Line 8 at 13+738; needs 7.30 m (box over double-track bore) |
| 14+819 | 2 crossing | 5.21 m under Line 4 at 14+819; needs 5.26 m (twin tube over twin tube) |
| 21+360 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 21+355 to 21+365 (under 0.6 m) |
| 21+405 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.57 m from 21+405 to 21+405 (under 0.6 m) |

## Line 11 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+625 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 0+525 to 0+725 (under 0.6 m) |
| 5+541 | 2 crossing | 7.76 m over RER-2 at 5+541; needs 8.68 m (twin tube over bored tube) |
| 6+615 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.14 m from 6+605 to 6+625 (under 0.6 m) |
| 6+725 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.22 m from 6+725 to 6+725 (under 0.6 m) |
| 7+070 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.14 m from 7+015 to 7+125 (under 0.6 m) |
| 7+804 | 2 crossing | 0.16 m under Line 2b at 7+804; needs 5.78 m (twin tube over box) |
| 7+833 | 2 crossing | 0.80 m over Line 6 at 7+833; needs 5.58 m (box over twin tube) |
| 8+125 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 8+115 to 8+135 (under 0.6 m) |
| 8+600 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 8+565 to 8+635 (under 0.6 m) |
| 10+140 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 10+135 to 10+145 (under 0.6 m) |
| 10+670 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 10+665 to 10+675 (under 0.6 m) |
| 11+200 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 11+185 to 11+215 (under 0.6 m) |
| 12+015 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 11+975 to 12+055 (under 0.6 m) |
| 12+186 | 2 crossing | 3.25 m under Line 6 at 12+186; needs 5.90 m (open trough over box) |
| 12+530 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 12+505 to 12+555 (under 0.6 m) |
| 14+340 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.29 m from 14+335 to 14+345 (under 0.6 m) |
| 14+900 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 14+885 to 14+915 (under 0.6 m) |
| 15+010 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.18 m from 15+005 to 15+015 (under 0.6 m) |
| 16+780 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.36 m from 16+655 to 16+905 (under 0.6 m) |
| 16+975 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 16+975 to 16+975 (under 0.6 m) |
| 18+905 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.21 m from 18+895 to 18+915 (under 0.6 m) |
| 19+555 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.00 m from 19+515 to 19+595 (under 0.6 m) |
| 21+690 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 21+675 to 21+705 (under 0.6 m) |
| 22+200 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 22+185 to 22+215 (under 0.6 m) |
| 22+300 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.16 m from 22+295 to 22+305 (under 0.6 m) |
| 22+820 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.21 m from 22+805 to 22+835 (under 0.6 m) |
| 23+640 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.13 m from 23+635 to 23+645 (under 0.6 m) |
| 24+950 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 24+945 to 24+955 (under 0.6 m) |
| 25+730 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 25+725 to 25+735 (under 0.6 m) |
| 27+505 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 27+485 to 27+525 (under 0.6 m) |
| 27+640 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 27+625 to 27+655 (under 0.6 m) |
| 29+520 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 29+505 to 29+535 (under 0.6 m) |
| 29+810 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 29+805 to 29+815 (under 0.6 m) |

## Line 12 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+130 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.44 m from 0+095 to 0+165 (under 0.6 m) |
| 0+875 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 0+865 to 0+885 (under 0.6 m) |
| 1+090 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 1+065 to 1+115 (under 0.6 m) |
| 2+010 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 1+955 to 2+065 (under 0.6 m) |
| 2+232 | 2 crossing | 2.93 m under RER-4 at 2+232; needs 5.50 m (at grade over open trough) |
| 2+325 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.00 m from 2+315 to 2+335 (under 0.6 m) |
| 2+900 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 2+885 to 2+915 (under 0.6 m) |
| 3+140 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.29 m from 3+135 to 3+145 (under 0.6 m) |
| 3+423 | 2 crossing | 5.45 m under RER-2 at 3+423; needs 7.30 m (box over double-track bore) |
| 3+658 | 2 crossing | 4.30 m over Line 5 at 3+658; needs 5.58 m (box over twin tube) |
| 3+740 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.04 m from 3+735 to 3+745 (under 0.6 m) |
| 3+945 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.00 m from 3+915 to 3+975 (under 0.6 m) |
| 4+075 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 4+015 to 4+135 (under 0.6 m) |
| 4+175 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.49 m from 4+175 to 4+175 (under 0.6 m) |
| 4+306 | 2 crossing | 2.60 m under Line 3 at 4+307; needs 5.78 m (twin tube over box) |
| 4+545 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 4+545 to 4+545 (under 0.6 m) |
| 4+720 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.13 m from 4+715 to 4+725 (under 0.6 m) |
| 4+860 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.26 m from 4+845 to 4+875 (under 0.6 m) |
| 8+315 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.47 m from 8+315 to 8+315 (under 0.6 m) |
| 8+715 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.08 m from 8+715 to 8+715 (under 0.6 m) |
| 8+775 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.27 m from 8+775 to 8+775 (under 0.6 m) |
| 9+844 | 2 crossing | 0.20 m over Line 7 at 9+844; needs 5.58 m (box over twin tube) |
| 10+777 | 2 crossing | 3.37 m over Line 9 at 10+777; needs 7.30 m (box over double-track bore) |
| 11+648 | 2 crossing | 4.12 m over Line 4 at 11+648; needs 5.58 m (box over twin tube) |
| 11+895 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.44 m from 11+895 to 11+895 (under 0.6 m) |
| 12+085 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.07 m from 12+085 to 12+085 (under 0.6 m) |
| 12+640 | 2 crossing | 3.68 m under Line 4 at 12+640; needs 5.90 m (open trough over box) |
| 13+485 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.19 m from 13+475 to 13+495 (under 0.6 m) |
| 13+625 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.04 m from 13+605 to 13+645 (under 0.6 m) |
| 13+842 | 2 crossing | 0.52 m over Line 13 at 13+842; needs 7.30 m (box over double-track bore) |
| 13+985 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.37 m from 13+965 to 14+005 (under 0.6 m) |
| 14+205 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 14+195 to 14+215 (under 0.6 m) |
| 14+925 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.25 m from 14+925 to 14+925 (under 0.6 m) |
| 15+415 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.41 m from 15+415 to 15+415 (under 0.6 m) |
| 15+565 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 15+545 to 15+585 (under 0.6 m) |
| 15+888 | 2 crossing | 1.40 m under Line 14 at 15+888; needs 6.10 m (box over box) |
| 16+970 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.07 m from 16+915 to 17+025 (under 0.6 m) |
| 18+135 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.16 m from 18+135 to 18+135 (under 0.6 m) |
| 20+755 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.33 m from 20+735 to 20+775 (under 0.6 m) |
| 21+075 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.32 m from 21+075 to 21+075 (under 0.6 m) |
| 21+540 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.14 m from 21+515 to 21+565 (under 0.6 m) |
| 21+605 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.25 m from 21+595 to 21+615 (under 0.6 m) |
| 22+050 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 22+045 to 22+055 (under 0.6 m) |
| 22+465 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.13 m from 22+445 to 22+485 (under 0.6 m) |
| 22+680 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.22 m from 22+675 to 22+685 (under 0.6 m) |
| 22+840 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.24 m from 22+835 to 22+845 (under 0.6 m) |
| 23+020 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 23+015 to 23+025 (under 0.6 m) |

## Line 13 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+752 | 2 crossing | 0.00 m over Line 5 at 0+752; needs 5.58 m (box over twin tube) |
| 0+815 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.30 m from 0+815 to 0+815 (under 0.6 m) |
| 1+024 | 2 crossing | 0.01 m under Line 3 at 1+024; needs 5.78 m (twin tube over box) |
| 1+261 | 2 crossing | 0.72 m under Line 8 at 1+261; needs 7.78 m (double-track bore over twin tube) |
| 1+515 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.14 m from 1+515 to 1+515 (under 0.6 m) |
| 2+315 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.04 m from 2+305 to 2+325 (under 0.6 m) |
| 2+951 | 2 crossing | 3.04 m over Line 1 at 2+951; needs 7.78 m (double-track bore over twin tube) |
| 3+445 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.44 m from 3+415 to 3+475 (under 0.6 m) |
| 3+585 | 2 crossing | 1.53 m over Line 2 at 3+585; needs 5.58 m (box over twin tube) |
| 4+908 | 2 crossing | 4.33 m under Line 6 at 4+908; needs 6.98 m (twin tube over double-track bore) |
| 5+562 | 2 crossing | 3.95 m over RER-5 at 5+562; needs 8.10 m (box over box) |
| 6+565 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.42 m from 6+565 to 6+565 (under 0.6 m) |
| 6+591 | 2 crossing | 3.73 m over Line 7 at 6+591; needs 5.38 m (open trough over twin tube) |
| 6+715 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 6+705 to 6+725 (under 0.6 m) |
| 7+570 | 2 crossing | 0.59 m under Line 4 at 7+570; needs 6.98 m (twin tube over double-track bore) |
| 8+515 | 2 crossing | 0.52 m under Line 12 at 8+515; needs 6.10 m (box over box) |
| 9+310 | 2 crossing | 0.40 m under Line 9 at 9+310; needs 6.10 m (box over box) |
| 15+555 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.54 m from 15+555 to 15+555 (under 0.6 m) |
| 15+840 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 15+835 to 15+845 (under 0.6 m) |
| 16+345 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.14 m from 16+335 to 16+355 (under 0.6 m) |
| 16+540 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 16+515 to 16+565 (under 0.6 m) |
| 19+190 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.22 m from 19+185 to 19+195 (under 0.6 m) |
| 19+940 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 19+935 to 19+945 (under 0.6 m) |
| 20+115 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 20+105 to 20+125 (under 0.6 m) |
| 22+040 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 22+035 to 22+045 (under 0.6 m) |
| 22+355 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.11 m from 22+275 to 22+435 (under 0.6 m) |
| 22+950 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 22+905 to 22+995 (under 0.6 m) |
| 23+270 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 23+045 to 23+495 (under 0.6 m) |
| 24+015 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 23+995 to 24+035 (under 0.6 m) |
| 24+155 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 24+145 to 24+165 (under 0.6 m) |
| 26+270 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 26+265 to 26+275 (under 0.6 m) |
| 26+460 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 26+445 to 26+475 (under 0.6 m) |

## Line 14 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+165 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.19 m from 0+145 to 0+185 (under 0.6 m) |
| 0+875 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.05 m from 0+865 to 0+885 (under 0.6 m) |
| 1+040 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.14 m from 1+035 to 1+045 (under 0.6 m) |
| 2+155 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.32 m from 2+155 to 2+155 (under 0.6 m) |
| 2+635 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.31 m from 2+635 to 2+635 (under 0.6 m) |
| 4+913 | 2 crossing | 3.14 m under Line 5 at 4+913; needs 6.98 m (twin tube over double-track bore) |
| 7+360 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.16 m from 7+355 to 7+365 (under 0.6 m) |
| 7+525 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.14 m from 7+515 to 7+535 (under 0.6 m) |
| 7+628 | 2 crossing | 0.20 m over Line 1 at 7+628; needs 5.58 m (box over twin tube) |
| 7+765 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.13 m from 7+755 to 7+775 (under 0.6 m) |
| 8+700 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.26 m from 8+695 to 8+705 (under 0.6 m) |
| 8+915 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.17 m from 8+915 to 8+915 (under 0.6 m) |
| 9+895 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.31 m from 9+895 to 9+895 (under 0.6 m) |
| 11+275 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 11+275 to 11+275 (under 0.6 m) |
| 12+220 | 2 crossing | 1.67 m over Line 2 at 12+220; needs 5.58 m (box over twin tube) |
| 13+205 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 13+195 to 13+215 (under 0.6 m) |
| 13+380 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.03 m from 13+375 to 13+385 (under 0.6 m) |
| 13+508 | 2 crossing | 2.30 m under Line 7 at 13+509; needs 5.78 m (twin tube over box) |
| 14+670 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.06 m from 14+665 to 14+675 (under 0.6 m) |
| 15+095 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 15+095 to 15+095 (under 0.6 m) |
| 16+145 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.22 m from 16+085 to 16+205 (under 0.6 m) |
| 16+530 | 2 crossing | 1.64 m over Line 4 at 16+530; needs 5.58 m (box over twin tube) |
| 16+582 | 2 crossing | 1.88 m under Line 3 at 16+582; needs 5.78 m (twin tube over box) |
| 18+321 | 2 crossing | 1.40 m over Line 12 at 18+321; needs 6.10 m (box over box) |
| 19+417 | 2 crossing | 0.10 m over Line 9 at 19+417; needs 6.10 m (box over box) |
| 21+100 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 21+075 to 21+125 (under 0.6 m) |
| 25+000 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.12 m from 24+985 to 25+015 (under 0.6 m) |
| 25+240 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.16 m from 25+215 to 25+265 (under 0.6 m) |
| 25+900 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 25+885 to 25+915 (under 0.6 m) |
| 26+215 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.24 m from 26+215 to 26+215 (under 0.6 m) |
| 27+750 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.02 m from 27+705 to 27+795 (under 0.6 m) |
| 28+585 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.16 m from 28+575 to 28+595 (under 0.6 m) |
| 29+110 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.10 m from 29+105 to 29+115 (under 0.6 m) |
| 31+915 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.37 m from 31+915 to 31+915 (under 0.6 m) |
| 33+490 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.28 m from 33+485 to 33+495 (under 0.6 m) |
| 34+125 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.01 m from 34+105 to 34+145 (under 0.6 m) |
| 35+920 | 3 thin cover (warning) | Box roof forms the street: cover down to 0.44 m from 35+875 to 35+965 (under 0.6 m) |

## RER-1 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 2+304 | 2 crossing | 1.53 m under Line 7 at 2+304; needs 7.78 m (twin tube over box) |
| 2+440 | 2 crossing | 0.76 m over RER-5 at 2+440; needs 8.10 m (box over box) |
| 2+465 | 2 crossing | 2.72 m under Line 10 at 2+465; needs 10.30 m (double-track bore over box) |
| 2+833 | 2 crossing | 3.66 m under Line 5 at 2+833; needs 7.78 m (twin tube over box) |
| 3+211 | 2 crossing | 5.17 m under Line 1 at 3+211; needs 7.90 m (open trough over box) |
| 3+280 | 2 crossing | 0.03 m under Line 8 at 3+280; needs 10.30 m (double-track bore over box) |
| 3+818 | 2 crossing | 1.24 m under Line 5 at 3+819; needs 7.78 m (twin tube over box) |
| 4+115 | 2 crossing | 5.37 m under Line 4 at 4+115; needs 7.78 m (twin tube over box) |
| 4+427 | 2 crossing | 5.13 m under Line 7 at 4+427; needs 7.78 m (twin tube over box) |
| 4+776 | 2 crossing | 3.16 m over Line 2 at 4+776; needs 5.58 m (box over twin tube) |
| 5+351 | 2 crossing | 0.15 m under Line 6 at 5+351; needs 7.78 m (twin tube over box) |
| 5+416 | 2 crossing | 4.73 m under Line 7 at 5+416; needs 7.78 m (twin tube over box) |
| 5+676 | 2 crossing | 5.69 m under Line 4 at 5+676; needs 8.10 m (box over box) |
| 5+682 | 2 crossing | 2.20 m over Line 5 at 5+682; needs 5.58 m (box over twin tube) |
| 9+224 | 2 crossing | Crosses Line 9 at grade at 9+225: needs a grade separation |
| 12+090 | 2 crossing | 5.07 m over Line 4 at 12+090; needs 5.90 m (at grade over box) |

## RER-2 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 3+867 | 2 crossing | 7.28 m under Line 1 at 3+867; needs 7.80 m (viaduct over at grade) |
| 6+035 | 2 crossing | 5.19 m over Line 8 at 6+035; needs 5.50 m (at grade over open trough) |
| 7+370 | 2 crossing | 5.45 m over Line 12 at 7+370; needs 7.30 m (box over double-track bore) |
| 8+172 | 2 crossing | 0.00 m over Line 9 at 8+172; needs 7.30 m (box over double-track bore) |
| 9+716 | 2 crossing | 7.06 m under Line 7 at 9+716; needs 7.90 m (at grade over box) |
| 11+409 | 2 crossing | 6.18 m under RER-5 at 11+409; needs 9.00 m (box over bored tube) |
| 11+435 | 2 crossing | 9.32 m under Line 10 at 11+435; needs 11.20 m (double-track bore over bored tube) |
| 12+856 | 2 crossing | 2.21 m over Line 3 at 12+856; needs 5.58 m (box over twin tube) |
| 15+128 | 4 river | Under the Ohio River from 15+126 to 15+380 the rail is up to 4.28 m above bed − 9.1 m (worst at 15+128) |
| 15+895 | 2 crossing | 7.76 m under Line 11 at 15+895; needs 8.68 m (twin tube over bored tube) |
| 21+721 | 2 crossing | 3.54 m over Line 6 at 21+721; needs 5.50 m (at grade over open trough) |

## RER-3 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 8+241 | 2 crossing | 7.03 m over RER-5 at 8+241; needs 8.10 m (box over box) |
| 11+225 | 2 crossing | 1.49 m over Line 2 at 11+225; needs 6.70 m (viaduct over viaduct) |
| 11+890 | 2 crossing | 2.72 m over Line 6 at 11+890; needs 5.58 m (box over twin tube) |

## RER-4 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 3+430 | 4 river | Under the Ohio River from 3+354 to 3+470 the rail is up to 0.80 m above bed − 9.1 m (worst at 3+430) |
| 5+078 | 2 crossing | 2.59 m over Line 2 at 5+078; needs 5.58 m (box over twin tube) |
| 5+382 | 2 crossing | 5.32 m under Line 7 at 5+382; needs 7.78 m (twin tube over box) |
| 5+720 | 2 crossing | 5.18 m under Line 4 at 5+720; needs 7.78 m (twin tube over box) |
| 6+024 | 2 crossing | 1.11 m under Line 5 at 6+024; needs 7.78 m (twin tube over box) |
| 6+564 | 2 crossing | 0.09 m under Line 8 at 6+565; needs 10.30 m (double-track bore over box) |
| 6+625 | 2 crossing | 5.14 m under Line 1 at 6+625; needs 7.90 m (open trough over box) |
| 7+005 | 2 crossing | 3.67 m under Line 5 at 7+005; needs 7.78 m (twin tube over box) |
| 7+374 | 2 crossing | 2.95 m under Line 10 at 7+374; needs 10.30 m (double-track bore over box) |
| 7+400 | 2 crossing | 0.25 m over RER-5 at 7+400; needs 8.10 m (box over box) |
| 7+603 | 2 crossing | 2.43 m under Line 7 at 7+603; needs 7.78 m (twin tube over box) |
| 9+093 | 2 crossing | Crosses Line 7 at grade at 9+093: needs a grade separation |
| 10+638 | 2 crossing | 0.02 m over Line 9 at 10+638; needs 7.30 m (box over double-track bore) |
| 12+556 | 2 crossing | Crosses Line 12 at grade at 12+556: needs a grade separation |

## RER-5 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 7+194 | 2 crossing | 3.95 m under Line 13 at 7+194; needs 8.10 m (box over box) |
| 8+664 | 2 crossing | 3.92 m under Line 9 at 8+665; needs 10.30 m (double-track bore over box) |
| 9+347 | 2 crossing | 2.47 m under Line 2 at 9+347; needs 8.68 m (twin tube over bored tube) |
| 9+357 | 2 crossing | 5.10 m under Line 8 at 9+357; needs 8.68 m (twin tube over bored tube) |
| 10+226 | 2 crossing | 1.45 m over Line 2 at 10+226; needs 5.58 m (bored tube over twin tube) |
| 10+404 | 2 crossing | 8.23 m under Line 8 at 10+404; needs 8.68 m (twin tube over bored tube) |
| 12+084 | 2 crossing | 0.69 m over Line 2 at 12+084; needs 5.58 m (box over twin tube) |
| 12+528 | 2 crossing | 4.32 m under Line 3 at 12+528; needs 7.78 m (twin tube over box) |
| 13+079 | 2 crossing | 2.43 m under Line 1 at 13+079; needs 7.90 m (open trough over box) |
| 13+470 | 2 crossing | 1.45 m over Line 5 at 13+470; needs 5.58 m (box over twin tube) |
| 13+892 | 2 crossing | 1.96 m under Line 10 at 13+892; needs 8.10 m (box over box) |
| 14+081 | 2 crossing | 6.18 m over RER-2 at 14+081; needs 9.00 m (box over bored tube) |
| 14+082 | 2 crossing | 0.25 m under RER-4 at 14+082; needs 8.10 m (box over box) |
| 14+093 | 2 crossing | 0.76 m under RER-1 at 14+093; needs 8.10 m (box over box) |
| 14+175 | 2 crossing | 3.28 m under Line 10 at 14+175; needs 8.10 m (box over box) |
| 14+180 | 2 crossing | 3.38 m under Line 8 at 14+180; needs 8.10 m (box over box) |
| 14+564 | 2 crossing | 5.73 m under Line 7 at 14+565; needs 7.78 m (twin tube over box) |
| 15+325 | 2 crossing | 7.03 m under RER-3 at 15+325; needs 8.10 m (box over box) |
| 15+426 | 4 river | Under the Ohio River from 15+400 to 15+426 the rail is up to 21.36 m above bed − 9.1 m (worst at 15+426) |

