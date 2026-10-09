# Metro profile rules: flags by line

Generated headless from the Rail Profiles page (saved profiles from the page database, solver defaults elsewhere) after applying Ben's rules:

1. Metro structures from top of rail: box 1.0 below / 4.6 to top; twin tube 0.68 / 4.08 (4.76 m OD) for deep tube, Lines 1-7 shield and every river crossing; double-track bore 3.2 / 5.8 (9.0 m OD) for Lines 8-14 shield.
2. Crossings: rail-to-rail separation >= upper line's below-rail + 0.5 m + lower line's rail-to-top (both systems; RER uses its settings: box 6.6, bore 7.5, floor 1.0; viaduct deck 1.5 Metro / 2.0 RER, track bed at grade 0.8; a line in the open counts its box height as the clear height under a bridge).
3. Cover over the top (Metro): tube or bore with top above 140.0 m 2.0 m, at or below 140.0 m one OD; box roof 0.6 m. Shallower tubes and bores are typed cut and cover, so cover flags on tubes appear only where a stretch is painted.
4. Rivers: in tunnel inside a river range, rail <= bed - 7.5 m (Metro) / bed - 8.0 m (RER), bed = the ground raster there.

Chainages are the line's own (km+m). 'Saved' = your saved profile; 'default' = the solver default (no saved profile).

## Summary

| Line | Profile | Crossings (2) | Cover (3) | Rivers (4) |
|---|---|---|---|---|
| Line 1 | saved | 14 | 14 | 0 |
| Line 2 | saved | 17 | 16 | 0 |
| Line 2b | default | 2 | 8 | 0 |
| Line 3 | default | 20 | 19 | 0 |
| Line 4 | saved | 19 | 13 | 0 |
| Line 5 | saved | 15 | 12 | 0 |
| Line 6 | saved | 15 | 30 | 0 |
| Line 7 | default | 22 | 28 | 0 |
| Line 8 | default | 20 | 11 | 0 |
| Line 9 | default | 15 | 30 | 0 |
| Line 10 | default | 20 | 16 | 0 |
| Line 11 | default | 7 | 31 | 0 |
| Line 12 | default | 10 | 29 | 0 |
| Line 13 | default | 11 | 21 | 0 |
| Line 14 | default | 8 | 28 | 0 |
| RER-1 | saved | 18 | 0 | 0 |
| RER-2 | saved | 8 | 0 | 0 |
| RER-3 | default | 6 | 0 | 0 |
| RER-4 | default | 14 | 0 | 0 |
| RER-5 | default | 18 | 0 | 1 |
| **Total** | | 279 | 306 | 1 |

Cover flags split into two kinds: 'Box roof ... above ground' is a cut-and-cover box whose rail is 3.0 to 4.6 m down (typed box from 3.0 m, the at-grade threshold), mostly portal ramps; 'cover down to ... needs' is a box or tube with too little ground over it.

## Line 1 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 0+003 | 2 crossing | 0.20 m under Line 14 at 0+003; needs 6.10 m (box over box) |
| 3+255 | 3 cover | Box roof 1.4 m above ground from 3+235 to 3+275 |
| 3+440 | 3 cover | Box roof 1.5 m above ground from 3+405 to 3+475 |
| 4+150 | 3 cover | Box roof cover down to 0.18 m from 4+105 to 4+195, needs 0.6 m |
| 4+815 | 3 cover | Box roof 1.6 m above ground from 4+785 to 4+845 |
| 6+079 | 2 crossing | 7.29 m over RER-2 at 6+079; needs 8.60 m (viaduct over at grade) |
| 6+660 | 3 cover | Box roof 1.2 m above ground from 6+645 to 6+675 |
| 7+747 | 2 crossing | 3.04 m under Line 13 at 7+747; needs 8.30 m (double-track bore over box) |
| 8+215 | 3 cover | Box roof 1.5 m above ground from 8+155 to 8+275 |
| 8+465 | 2 crossing | 0.11 m over Line 8 at 8+465; needs 6.10 m (box over box) |
| 8+645 | 3 cover | Box roof 0.4 m above ground from 8+575 to 8+715 |
| 8+786 | 2 crossing | 1.58 m under Line 9 at 8+787; needs 6.10 m (box over box) |
| 11+105 | 3 cover | Box roof 0.5 m above ground from 11+105 to 11+105 |
| 11+982 | 2 crossing | 2.43 m over RER-5 at 11+982; needs 8.10 m (box over box) |
| 11+982 | 2 crossing | 3.52 m over Line 10 at 11+982; needs 6.10 m (box over box) |
| 12+250 | 3 cover | Box roof 1.5 m above ground from 11+805 to 12+695 |
| 12+524 | 2 crossing | 5.14 m over RER-4 at 12+524; needs 8.10 m (box over box) |
| 12+527 | 2 crossing | 5.17 m over RER-1 at 12+527; needs 8.10 m (box over box) |
| 12+552 | 2 crossing | 4.42 m over Line 8 at 12+552; needs 6.10 m (box over box) |
| 12+970 | 3 cover | Box roof 1.4 m above ground from 12+945 to 12+995 |
| 13+070 | 3 cover | Box roof 1.3 m above ground from 13+065 to 13+075 |
| 13+124 | 2 crossing | 0.29 m under Line 4 at 13+124; needs 5.78 m (twin tube over box) |
| 13+509 | 2 crossing | 1.90 m over Line 7 at 13+509; needs 5.58 m (box over twin tube) |
| 13+570 | 3 cover | Box roof 1.1 m above ground from 13+555 to 13+585 |
| 13+890 | 3 cover | Box roof 1.6 m above ground from 13+865 to 13+915 |
| 14+916 | 2 crossing | 4.21 m over Line 2 at 14+916; needs 5.26 m (twin tube over twin tube) |
| 15+488 | 2 crossing | 4.64 m under Line 6 at 15+488; needs 5.78 m (twin tube over box) |
| 19+100 | 3 cover | Box roof 1.5 m above ground from 18+915 to 19+285 |

## Line 2 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 0+300 | 3 cover | Box roof 1.6 m above ground from 0+295 to 0+305 |
| 0+355 | 3 cover | Box roof 0.7 m above ground from 0+355 to 0+355 |
| 1+606 | 2 crossing | 1.67 m under Line 14 at 1+606; needs 6.10 m (box over box) |
| 3+835 | 3 cover | Box roof 1.4 m above ground from 3+815 to 3+855 |
| 4+200 | 3 cover | Box roof 1.6 m above ground from 3+915 to 4+485 |
| 4+735 | 3 cover | Box roof 1.5 m above ground from 4+655 to 4+815 |
| 4+995 | 3 cover | Box roof 1.6 m above ground from 4+935 to 5+055 |
| 5+058 | 2 crossing | 1.92 m over Line 3 at 5+058; needs 5.58 m (box over twin tube) |
| 6+375 | 3 cover | Box roof 1.3 m above ground from 6+215 to 6+535 |
| 7+489 | 2 crossing | 1.53 m under Line 13 at 7+489; needs 6.10 m (box over box) |
| 8+080 | 3 cover | Box roof 1.4 m above ground from 8+055 to 8+105 |
| 8+380 | 3 cover | Box roof 1.3 m above ground from 8+365 to 8+395 |
| 9+017 | 2 crossing | 1.02 m under Line 9 at 9+017; needs 8.30 m (double-track bore over box) |
| 9+479 | 2 crossing | 2.47 m over RER-5 at 9+479; needs 8.68 m (twin tube over bored tube) |
| 9+690 | 2 crossing | 0.88 m under Line 8 at 9+690; needs 5.26 m (twin tube over twin tube) |
| 10+253 | 2 crossing | 1.45 m under RER-5 at 10+253; needs 5.58 m (bored tube over twin tube) |
| 11+982 | 2 crossing | 0.69 m under RER-5 at 11+982; needs 6.10 m (box over box) |
| 11+990 | 2 crossing | 0.30 m under Line 10 at 11+990; needs 6.10 m (box over box) |
| 12+388 | 2 crossing | 0.39 m under Line 8 at 12+388; needs 6.10 m (box over box) |
| 12+952 | 2 crossing | 0.50 m under Line 4 at 12+952; needs 5.78 m (twin tube over box) |
| 13+245 | 2 crossing | 0.18 m under RER-4 at 13+245; needs 6.10 m (box over box) |
| 13+247 | 2 crossing | 3.16 m under RER-1 at 13+247; needs 6.10 m (box over box) |
| 13+319 | 2 crossing | 4.21 m under Line 1 at 13+319; needs 5.78 m (twin tube over box) |
| 14+146 | 2 crossing | 1.50 m under RER-3 at 14+147; needs 5.58 m (box over twin tube) |
| 14+515 | 3 cover | Box roof 0.9 m above ground from 14+515 to 14+515 |
| 14+894 | 2 crossing | 0.10 m under Line 11 at 14+895; needs 6.10 m (box over box) |
| 15+954 | 2 crossing | 1.36 m over Line 6 at 15+954; needs 5.58 m (box over twin tube) |
| 16+055 | 3 cover | Box roof 1.2 m above ground from 16+035 to 16+075 |
| 16+280 | 3 cover | Box roof 1.5 m above ground from 16+245 to 16+315 |
| 16+985 | 3 cover | Box roof 1.4 m above ground from 16+835 to 17+135 |
| 17+220 | 3 cover | Box roof cover down to 0.52 m from 17+205 to 17+235, needs 0.6 m |
| 17+465 | 3 cover | Box roof 1.4 m above ground from 17+445 to 17+485 |
| 17+715 | 3 cover | Box roof 1.4 m above ground from 17+645 to 17+785 |

## Line 2b (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+380 | 3 cover | Box roof 1.6 m above ground from 0+335 to 0+425 |
| 0+615 | 3 cover | Box roof 0.9 m above ground from 0+615 to 0+615 |
| 0+685 | 3 cover | Box roof 1.0 m above ground from 0+685 to 0+685 |
| 0+845 | 3 cover | Box roof cover down to 0.20 m from 0+845 to 0+845, needs 0.6 m |
| 1+025 | 3 cover | Box roof 1.5 m above ground from 1+005 to 1+045 |
| 1+120 | 3 cover | Box roof 1.4 m above ground from 1+105 to 1+135 |
| 3+425 | 3 cover | Box roof 1.5 m above ground from 3+405 to 3+445 |
| 3+500 | 3 cover | Box roof 1.4 m above ground from 3+475 to 3+525 |
| 4+107 | 2 crossing | 0.16 m over Line 11 at 4+107; needs 6.10 m (box over box) |
| 4+844 | 2 crossing | 0.27 m under Line 3 at 4+844; needs 5.26 m (twin tube over twin tube) |

## Line 3 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+240 | 3 cover | Box roof 0.5 m above ground from 0+135 to 0+345 |
| 0+358 | 2 crossing | 1.89 m over Line 14 at 0+358; needs 6.98 m (twin tube over double-track bore) |
| 0+370 | 2 crossing | 3.47 m over Line 4 at 0+371; needs 5.26 m (twin tube over twin tube) |
| 0+645 | 3 cover | Box roof 1.0 m above ground from 0+395 to 0+895 |
| 1+985 | 2 crossing | 3.94 m over Line 7 at 1+985; needs 5.58 m (box over twin tube) |
| 2+878 | 2 crossing | 2.50 m under Line 6 at 2+878; needs 6.10 m (box over box) |
| 3+355 | 3 cover | Box roof 1.6 m above ground from 3+265 to 3+445 |
| 3+515 | 3 cover | Box roof 1.5 m above ground from 3+515 to 3+515 |
| 3+745 | 3 cover | Box roof 1.5 m above ground from 3+685 to 3+805 |
| 4+888 | 2 crossing | 1.92 m under Line 2 at 4+888; needs 6.10 m (box over box) |
| 6+050 | 3 cover | Box roof 1.4 m above ground from 6+045 to 6+055 |
| 6+145 | 3 cover | Box roof 1.1 m above ground from 6+135 to 6+155 |
| 9+019 | 2 crossing | 0.80 m under Line 8 at 9+019; needs 6.10 m (box over box) |
| 9+148 | 2 crossing | 0.01 m over Line 13 at 9+148; needs 6.10 m (box over box) |
| 9+275 | 3 cover | Box roof cover down to 0.53 m from 9+265 to 9+285, needs 0.6 m |
| 9+545 | 3 cover | Box roof cover down to 0.19 m from 9+515 to 9+575, needs 0.6 m |
| 10+481 | 2 crossing | 2.60 m over Line 12 at 10+481; needs 7.30 m (box over double-track bore) |
| 10+675 | 3 cover | Box roof cover down to 0.12 m from 10+615 to 10+735, needs 0.6 m |
| 11+036 | 2 crossing | 0.70 m under Line 9 at 11+036; needs 6.10 m (box over box) |
| 12+860 | 3 cover | Box roof 0.0 m above ground from 12+815 to 12+905 |
| 14+344 | 2 crossing | 6.18 m over RER-5 at 14+344; needs 8.10 m (box over box) |
| 14+344 | 2 crossing | 0.00 m over Line 10 at 14+344; needs 6.10 m (box over box) |
| 14+867 | 2 crossing | 0.50 m under Line 8 at 14+867; needs 6.10 m (box over box) |
| 15+218 | 2 crossing | 3.08 m under Line 5 at 15+218; needs 5.78 m (twin tube over box) |
| 15+403 | 2 crossing | 5.11 m under Line 4 at 15+403; needs 5.78 m (twin tube over box) |
| 15+524 | 2 crossing | 0.46 m under RER-4 at 15+524; needs 5.58 m (box over twin tube) |
| 15+544 | 2 crossing | 1.91 m under RER-1 at 15+544; needs 5.58 m (box over twin tube) |
| 16+635 | 2 crossing | 3.79 m under RER-3 at 16+635; needs 5.58 m (box over twin tube) |
| 16+985 | 3 cover | Box roof 0.1 m above ground from 16+985 to 16+985 |
| 17+358 | 2 crossing | 0.16 m over Line 11 at 17+358; needs 6.10 m (box over box) |
| 17+971 | 2 crossing | 0.27 m over Line 2b at 17+971; needs 5.26 m (twin tube over twin tube) |
| 18+471 | 2 crossing | 0.07 m under Line 6 at 18+471; needs 5.78 m (twin tube over box) |
| 19+545 | 3 cover | Box roof 1.3 m above ground from 19+525 to 19+565 |
| 19+895 | 3 cover | Box roof 1.6 m above ground from 19+715 to 20+075 |
| 20+780 | 3 cover | Box roof 1.0 m above ground from 20+535 to 21+025 |
| 21+815 | 3 cover | Box roof 1.6 m above ground from 21+805 to 21+825 |
| 22+470 | 3 cover | Box roof 0.7 m above ground from 22+455 to 22+485 |
| 23+170 | 3 cover | Box roof 1.4 m above ground from 23+155 to 23+185 |
| 25+225 | 3 cover | Box roof 1.1 m above ground from 25+215 to 25+235 |

## Line 4 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 0+968 | 2 crossing | 3.06 m under Line 9 at 0+968; needs 5.58 m (box over twin tube) |
| 2+440 | 3 cover | Box roof 0.5 m above ground from 2+355 to 2+525 |
| 3+172 | 2 crossing | 0.09 m over Line 7 at 3+172; needs 5.58 m (box over twin tube) |
| 3+370 | 3 cover | Box roof 1.6 m above ground from 3+345 to 3+395 |
| 4+000 | 3 cover | Box roof 1.3 m above ground from 3+985 to 4+015 |
| 4+380 | 3 cover | Box roof 1.3 m above ground from 4+365 to 4+395 |
| 4+800 | 3 cover | Box roof 1.5 m above ground from 4+655 to 4+945 |
| 10+795 | 3 cover | Box roof 1.1 m above ground from 10+795 to 10+795 |
| 11+975 | 3 cover | Box roof 1.1 m above ground from 11+965 to 11+985 |
| 12+116 | 2 crossing | 1.42 m over Line 7 at 12+116; needs 5.58 m (box over twin tube) |
| 12+260 | 3 cover | Box roof 0.7 m above ground from 12+185 to 12+335 |
| 12+920 | 3 cover | Box roof cover down to 0.38 m from 12+895 to 12+945, needs 0.6 m |
| 13+021 | 2 crossing | 0.29 m over Line 1 at 13+021; needs 5.58 m (box over twin tube) |
| 13+215 | 3 cover | Box roof 0.8 m above ground from 13+135 to 13+295 |
| 13+784 | 2 crossing | 5.37 m over RER-1 at 13+784; needs 8.10 m (box over box) |
| 13+790 | 2 crossing | 5.18 m over RER-4 at 13+790; needs 8.10 m (box over box) |
| 13+886 | 2 crossing | 5.11 m over Line 3 at 13+886; needs 5.58 m (box over twin tube) |
| 14+314 | 2 crossing | 0.50 m over Line 2 at 14+314; needs 5.58 m (box over twin tube) |
| 14+887 | 2 crossing | 2.99 m under Line 6 at 14+887; needs 5.26 m (twin tube over twin tube) |
| 15+044 | 2 crossing | 5.70 m over RER-1 at 15+044; needs 8.10 m (box over box) |
| 15+080 | 3 cover | Box roof cover down to 0.40 m from 15+055 to 15+105, needs 0.6 m |
| 15+963 | 2 crossing | 4.80 m under Line 10 at 15+963; needs 8.30 m (double-track bore over box) |
| 18+575 | 2 crossing | 4.41 m under Line 9 at 18+575; needs 6.10 m (box over box) |
| 19+260 | 2 crossing | 4.62 m over Line 7 at 19+260; needs 5.58 m (box over twin tube) |
| 19+260 | 3 cover | Box roof 1.3 m above ground from 19+205 to 19+315 |
| 19+822 | 2 crossing | 4.12 m under Line 12 at 19+822; needs 6.10 m (box over box) |
| 20+606 | 2 crossing | 3.68 m over Line 12 at 20+606; needs 6.10 m (box over box) |
| 20+650 | 3 cover | Box roof 1.1 m above ground from 20+575 to 20+725 |
| 21+014 | 2 crossing | 0.59 m over Line 13 at 21+014; needs 7.30 m (box over double-track bore) |
| 21+112 | 2 crossing | 4.59 m under RER-1 at 21+112; needs 5.38 m (at grade over twin tube) |
| 23+328 | 2 crossing | 3.47 m under Line 3 at 23+328; needs 5.78 m (twin tube over box) |
| 23+379 | 2 crossing | 1.63 m under Line 14 at 23+379; needs 6.10 m (box over box) |

## Line 5 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 0+265 | 3 cover | Box roof cover down to 0.28 m from 0+225 to 0+305, needs 0.6 m |
| 1+440 | 3 cover | Box roof 0.6 m above ground from 1+335 to 1+545 |
| 1+645 | 2 crossing | 3.14 m over Line 14 at 1+645; needs 7.30 m (box over double-track bore) |
| 1+925 | 3 cover | Box roof 1.4 m above ground from 1+905 to 1+945 |
| 2+190 | 3 cover | Box roof 1.6 m above ground from 2+165 to 2+215 |
| 8+910 | 2 crossing | 0.00 m over Line 13 at 8+910; needs 7.30 m (box over double-track bore) |
| 9+005 | 3 cover | Box roof 0.9 m above ground from 9+005 to 9+005 |
| 10+111 | 2 crossing | 4.30 m under Line 12 at 10+111; needs 5.58 m (box over twin tube) |
| 10+801 | 2 crossing | 5.60 m under Line 9 at 10+801; needs 6.10 m (box over box) |
| 13+707 | 2 crossing | 0.42 m over Line 10 at 13+707; needs 7.30 m (box over double-track bore) |
| 13+807 | 2 crossing | 1.45 m under RER-5 at 13+807; needs 5.58 m (box over twin tube) |
| 14+202 | 2 crossing | 3.67 m over RER-4 at 14+202; needs 7.78 m (twin tube over box) |
| 14+202 | 2 crossing | 3.67 m over RER-1 at 14+202; needs 7.78 m (twin tube over box) |
| 14+290 | 2 crossing | 0.53 m under Line 8 at 14+290; needs 6.10 m (box over box) |
| 14+330 | 3 cover | Box roof cover down to 0.52 m from 14+315 to 14+345, needs 0.6 m |
| 15+451 | 2 crossing | 1.11 m over RER-4 at 15+451; needs 7.78 m (twin tube over box) |
| 15+458 | 2 crossing | 1.23 m over RER-1 at 15+458; needs 7.78 m (twin tube over box) |
| 15+744 | 2 crossing | 3.08 m over Line 3 at 15+744; needs 5.58 m (box over twin tube) |
| 16+980 | 2 crossing | 2.20 m under RER-1 at 16+981; needs 6.10 m (box over box) |
| 17+138 | 2 crossing | 1.26 m under Line 7 at 17+138; needs 5.78 m (twin tube over box) |
| 18+905 | 3 cover | Box roof cover down to 0.58 m from 18+895 to 18+915, needs 0.6 m |
| 19+076 | 2 crossing | 1.83 m over Line 10 at 19+076; needs 7.30 m (box over double-track bore) |
| 19+970 | 3 cover | Box roof cover down to 0.35 m from 19+945 to 19+995, needs 0.6 m |
| 20+365 | 3 cover | Box roof cover down to 0.12 m from 20+295 to 20+435, needs 0.6 m |
| 24+370 | 3 cover | Box roof cover down to 0.44 m from 24+325 to 24+415, needs 0.6 m |
| 27+915 | 3 cover | Box roof 0.1 m above ground from 27+915 to 27+915 |
| 29+010 | 3 cover | Box roof 1.1 m above ground from 28+945 to 29+075 |

## Line 6 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 1+053 | 2 crossing | 2.50 m over Line 3 at 1+053; needs 5.58 m (box over twin tube) |
| 1+070 | 3 cover | Box roof 1.2 m above ground from 1+055 to 1+085 |
| 2+005 | 3 cover | Box roof 1.5 m above ground from 1+985 to 2+025 |
| 2+935 | 3 cover | Box roof 1.5 m above ground from 2+925 to 2+945 |
| 2+995 | 3 cover | Box roof 1.3 m above ground from 2+975 to 3+015 |
| 3+740 | 3 cover | Box roof 0.7 m above ground from 3+665 to 3+815 |
| 4+545 | 3 cover | Box roof 1.6 m above ground from 4+495 to 4+595 |
| 4+700 | 3 cover | Box roof 1.5 m above ground from 4+635 to 4+765 |
| 4+830 | 2 crossing | 4.33 m over Line 13 at 4+830; needs 7.30 m (box over double-track bore) |
| 5+060 | 3 cover | Box roof 1.5 m above ground from 5+005 to 5+115 |
| 5+410 | 3 cover | Box roof 1.5 m above ground from 5+375 to 5+445 |
| 5+939 | 2 crossing | 5.17 m over Line 9 at 5+939; needs 7.30 m (box over double-track bore) |
| 8+647 | 2 crossing | 1.85 m over Line 10 at 8+647; needs 7.30 m (box over double-track bore) |
| 9+390 | 3 cover | Box roof cover down to 0.19 m from 9+305 to 9+475, needs 0.6 m |
| 9+676 | 2 crossing | 2.99 m over Line 4 at 9+676; needs 5.58 m (box over twin tube) |
| 9+898 | 2 crossing | 4.69 m under Line 7 at 9+898; needs 5.26 m (twin tube over twin tube) |
| 9+926 | 2 crossing | 0.30 m over RER-1 at 9+926; needs 7.78 m (twin tube over box) |
| 10+039 | 2 crossing | 4.64 m over Line 1 at 10+039; needs 5.58 m (box over twin tube) |
| 10+445 | 3 cover | Box roof 1.5 m above ground from 10+375 to 10+515 |
| 10+844 | 2 crossing | 2.72 m under RER-3 at 10+844; needs 5.58 m (box over twin tube) |
| 10+865 | 3 cover | Box roof 0.3 m above ground from 10+865 to 10+865 |
| 11+490 | 2 crossing | 0.20 m under Line 11 at 11+490; needs 6.10 m (box over box) |
| 13+235 | 3 cover | Box roof 1.3 m above ground from 13+215 to 13+255 |
| 13+335 | 3 cover | Box roof 0.2 m above ground from 13+335 to 13+335 |
| 13+410 | 3 cover | Box roof 1.5 m above ground from 13+365 to 13+455 |
| 13+963 | 2 crossing | 1.36 m under Line 2 at 13+963; needs 5.78 m (twin tube over box) |
| 14+539 | 2 crossing | 0.07 m over Line 3 at 14+539; needs 5.58 m (box over twin tube) |
| 15+065 | 2 crossing | 0.80 m under Line 11 at 15+065; needs 6.10 m (box over box) |
| 18+845 | 3 cover | Box roof 0.2 m above ground from 18+775 to 18+915 |
| 19+100 | 3 cover | Box roof 0.3 m above ground from 19+075 to 19+125 |
| 19+100 | 2 crossing | 3.25 m over Line 11 at 19+101; needs 6.10 m (box over box) |
| 19+103 | 2 crossing | 3.54 m under RER-2 at 19+103; needs 5.90 m (at grade over box) |
| 20+735 | 3 cover | Box roof 1.5 m above ground from 20+705 to 20+765 |
| 20+965 | 3 cover | Box roof 1.3 m above ground from 20+935 to 20+995 |
| 21+845 | 3 cover | Box roof cover down to 0.03 m from 21+765 to 21+925, needs 0.6 m |
| 22+380 | 3 cover | Box roof 0.9 m above ground from 22+345 to 22+415 |
| 22+955 | 3 cover | Box roof cover down to 0.06 m from 22+905 to 23+005, needs 0.6 m |
| 23+455 | 3 cover | Box roof 1.6 m above ground from 23+415 to 23+495 |
| 23+595 | 3 cover | Box roof 1.6 m above ground from 23+555 to 23+635 |
| 24+595 | 3 cover | Box roof 1.5 m above ground from 24+485 to 24+705 |
| 26+185 | 3 cover | Box roof 1.4 m above ground from 26+165 to 26+205 |
| 26+445 | 3 cover | Box roof 1.1 m above ground from 26+435 to 26+455 |
| 27+520 | 3 cover | Box roof 1.4 m above ground from 27+075 to 27+965 |
| 28+685 | 3 cover | Box roof 1.6 m above ground from 28+005 to 29+365 |
| 29+570 | 3 cover | Box roof 0.7 m above ground from 29+485 to 29+655 |

## Line 7 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+065 | 3 cover | Box roof 1.3 m above ground from 0+045 to 0+085 |
| 1+130 | 3 cover | Box roof 1.0 m above ground from 1+115 to 1+145 |
| 1+320 | 3 cover | Box roof 1.4 m above ground from 1+305 to 1+335 |
| 1+590 | 3 cover | Box roof 1.3 m above ground from 1+575 to 1+605 |
| 1+815 | 3 cover | Box roof 1.5 m above ground from 1+795 to 1+835 |
| 2+440 | 3 cover | Box roof 0.6 m above ground from 2+435 to 2+445 |
| 4+471 | 2 crossing | 0.09 m under Line 4 at 4+471; needs 5.78 m (twin tube over box) |
| 4+595 | 3 cover | Box roof 1.4 m above ground from 4+575 to 4+615 |
| 5+545 | 3 cover | Box roof 1.3 m above ground from 5+525 to 5+565 |
| 8+405 | 3 cover | Box roof 0.5 m above ground from 8+405 to 8+405 |
| 8+505 | 3 cover | Box roof 1.5 m above ground from 8+465 to 8+545 |
| 8+645 | 3 cover | Box roof cover down to 0.40 m from 8+645 to 8+645, needs 0.6 m |
| 9+350 | 3 cover | Box roof 1.6 m above ground from 9+175 to 9+525 |
| 10+325 | 3 cover | Box roof cover down to 0.52 m from 10+315 to 10+335, needs 0.6 m |
| 10+475 | 3 cover | Box roof cover down to 0.31 m from 10+405 to 10+545, needs 0.6 m |
| 11+769 | 2 crossing | 7.14 m over RER-2 at 11+769; needs 7.78 m (twin tube over box) |
| 11+769 | 2 crossing | 0.44 m over RER-4 at 11+769; needs 7.78 m (twin tube over box) |
| 13+304 | 2 crossing | 2.44 m over RER-4 at 13+304; needs 7.78 m (twin tube over box) |
| 13+452 | 2 crossing | 1.53 m over RER-1 at 13+452; needs 7.78 m (twin tube over box) |
| 13+539 | 2 crossing | 0.90 m over Line 8 at 13+539; needs 7.30 m (box over double-track bore) |
| 13+551 | 2 crossing | 1.00 m over Line 10 at 13+551; needs 7.30 m (box over double-track bore) |
| 13+900 | 2 crossing | 5.73 m over RER-5 at 13+900; needs 7.78 m (twin tube over box) |
| 14+100 | 2 crossing | 1.42 m under Line 4 at 14+100; needs 5.78 m (twin tube over box) |
| 15+055 | 3 cover | Box roof 0.1 m above ground from 15+015 to 15+095 |
| 15+219 | 2 crossing | 1.90 m under Line 1 at 15+219; needs 5.78 m (twin tube over box) |
| 16+167 | 2 crossing | 5.13 m over RER-1 at 16+167; needs 7.78 m (twin tube over box) |
| 16+206 | 2 crossing | 6.79 m over RER-4 at 16+206; needs 7.78 m (twin tube over box) |
| 17+074 | 2 crossing | 4.69 m over Line 6 at 17+075; needs 5.26 m (twin tube over twin tube) |
| 17+117 | 2 crossing | 5.10 m over RER-1 at 17+117; needs 7.78 m (twin tube over box) |
| 17+380 | 2 crossing | 1.26 m over Line 5 at 17+380; needs 5.58 m (box over twin tube) |
| 18+341 | 2 crossing | 3.49 m over Line 10 at 18+341; needs 5.26 m (twin tube over twin tube) |
| 18+675 | 3 cover | Box roof 1.3 m above ground from 18+675 to 18+675 |
| 19+655 | 3 cover | Box roof cover down to 0.10 m from 19+655 to 19+655, needs 0.6 m |
| 19+820 | 3 cover | Box roof 1.4 m above ground from 19+795 to 19+845 |
| 20+235 | 3 cover | Box roof 1.0 m above ground from 20+105 to 20+365 |
| 20+444 | 2 crossing | 0.20 m under Line 12 at 20+444; needs 6.10 m (box over box) |
| 20+700 | 3 cover | Box roof 1.5 m above ground from 20+555 to 20+845 |
| 21+020 | 3 cover | Box roof 1.5 m above ground from 20+995 to 21+045 |
| 21+180 | 2 crossing | 2.47 m over Line 9 at 21+180; needs 7.30 m (box over double-track bore) |
| 21+830 | 3 cover | Box roof 0.3 m above ground from 21+755 to 21+905 |
| 22+148 | 2 crossing | 4.62 m under Line 4 at 22+148; needs 6.10 m (box over box) |
| 23+445 | 2 crossing | 3.73 m under Line 13 at 23+445; needs 6.10 m (box over box) |
| 24+455 | 3 cover | Box roof 0.7 m above ground from 24+345 to 24+565 |
| 25+200 | 3 cover | Box roof 1.1 m above ground from 25+115 to 25+285 |
| 26+145 | 3 cover | Box roof 1.6 m above ground from 26+125 to 26+165 |
| 26+294 | 2 crossing | 3.93 m under Line 3 at 26+295; needs 5.26 m (twin tube over twin tube) |
| 27+945 | 3 cover | Box roof 0.1 m above ground from 27+885 to 28+005 |
| 28+491 | 2 crossing | 2.28 m over Line 14 at 28+491; needs 7.30 m (box over double-track bore) |
| 28+585 | 3 cover | Box roof 1.3 m above ground from 28+565 to 28+605 |
| 28+720 | 3 cover | Box roof 1.5 m above ground from 28+695 to 28+745 |

## Line 8 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+215 | 3 cover | Box roof 1.4 m above ground from 0+175 to 0+255 |
| 0+555 | 3 cover | Box roof 0.8 m above ground from 0+545 to 0+565 |
| 0+562 | 2 crossing | 5.14 m under RER-2 at 0+562; needs 5.90 m (at grade over box) |
| 0+628 | 2 crossing | 0.80 m over Line 3 at 0+628; needs 5.58 m (box over twin tube) |
| 0+863 | 2 crossing | 0.72 m over Line 13 at 0+863; needs 7.78 m (double-track bore over twin tube) |
| 2+807 | 2 crossing | 0.11 m under Line 1 at 2+807; needs 5.78 m (twin tube over box) |
| 3+586 | 2 crossing | 0.93 m over Line 9 at 3+586; needs 6.10 m (box over box) |
| 4+276 | 2 crossing | 5.10 m over RER-5 at 4+276; needs 8.68 m (twin tube over bored tube) |
| 4+482 | 2 crossing | 0.88 m over Line 2 at 4+482; needs 5.26 m (twin tube over twin tube) |
| 5+166 | 2 crossing | 8.39 m over RER-5 at 5+166; needs 8.68 m (twin tube over bored tube) |
| 6+623 | 2 crossing | 3.57 m under Line 10 at 6+623; needs 6.10 m (box over box) |
| 7+197 | 2 crossing | 0.39 m over Line 2 at 7+197; needs 5.58 m (box over twin tube) |
| 7+624 | 2 crossing | 0.50 m over Line 3 at 7+624; needs 5.58 m (box over twin tube) |
| 8+262 | 2 crossing | 0.09 m over RER-4 at 8+262; needs 8.10 m (box over box) |
| 8+266 | 2 crossing | 0.03 m over RER-1 at 8+267; needs 8.10 m (box over box) |
| 8+329 | 2 crossing | 4.42 m under Line 1 at 8+329; needs 6.10 m (box over box) |
| 8+702 | 2 crossing | 0.53 m over Line 5 at 8+702; needs 6.10 m (box over box) |
| 8+845 | 3 cover | Box roof 0.3 m above ground from 8+685 to 9+005 |
| 9+101 | 2 crossing | 3.38 m over RER-5 at 9+101; needs 8.10 m (box over box) |
| 9+108 | 2 crossing | 0.10 m over Line 10 at 9+108; needs 6.10 m (box over box) |
| 9+232 | 2 crossing | 0.90 m under Line 7 at 9+232; needs 5.78 m (twin tube over box) |
| 11+474 | 2 crossing | 0.09 m over Line 10 at 11+474; needs 6.10 m (box over box) |
| 11+585 | 3 cover | Box roof cover down to 0.42 m from 11+585 to 11+585, needs 0.6 m |
| 11+658 | 2 crossing | 0.50 m under RER-3 at 11+658; needs 6.10 m (box over box) |
| 12+065 | 3 cover | Box roof 1.5 m above ground from 12+065 to 12+065 |
| 12+240 | 3 cover | Box roof 1.0 m above ground from 12+215 to 12+265 |
| 13+570 | 3 cover | Box roof cover down to 0.31 m from 13+555 to 13+585, needs 0.6 m |
| 14+020 | 3 cover | Box roof 1.1 m above ground from 14+005 to 14+035 |
| 14+720 | 3 cover | Box roof 0.7 m above ground from 14+715 to 14+725 |
| 18+345 | 3 cover | Box roof 1.5 m above ground from 18+325 to 18+365 |
| 18+705 | 3 cover | Box roof 1.2 m above ground from 18+695 to 18+715 |

## Line 9 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 2+080 | 3 cover | Box roof cover down to 0.17 m from 2+045 to 2+115, needs 0.6 m |
| 3+749 | 2 crossing | 3.06 m over Line 4 at 3+749; needs 5.58 m (box over twin tube) |
| 6+000 | 3 cover | Box roof 1.1 m above ground from 5+975 to 6+025 |
| 6+575 | 3 cover | Box roof 1.5 m above ground from 6+535 to 6+615 |
| 7+030 | 3 cover | Box roof 1.5 m above ground from 6+995 to 7+065 |
| 7+280 | 3 cover | Box roof 1.6 m above ground from 7+255 to 7+305 |
| 8+230 | 3 cover | Box roof 1.5 m above ground from 8+165 to 8+295 |
| 8+925 | 3 cover | Box roof 0.6 m above ground from 8+905 to 8+945 |
| 9+085 | 3 cover | Box roof 0.2 m above ground from 9+025 to 9+145 |
| 9+770 | 3 cover | Box roof 1.6 m above ground from 9+755 to 9+785 |
| 10+550 | 3 cover | Box roof 1.0 m above ground from 10+545 to 10+555 |
| 12+140 | 3 cover | Box roof 0.2 m above ground from 12+125 to 12+155 |
| 12+535 | 2 crossing | 0.00 m under RER-2 at 12+535; needs 7.30 m (box over double-track bore) |
| 12+535 | 2 crossing | 0.03 m under RER-4 at 12+535; needs 7.30 m (box over double-track bore) |
| 12+970 | 3 cover | Box roof 1.5 m above ground from 12+935 to 13+005 |
| 13+405 | 3 cover | Box roof 1.5 m above ground from 13+395 to 13+415 |
| 13+445 | 2 crossing | 0.70 m over Line 3 at 13+445; needs 5.58 m (box over twin tube) |
| 14+090 | 3 cover | Box roof 1.5 m above ground from 14+055 to 14+125 |
| 14+615 | 3 cover | Box roof 1.2 m above ground from 14+605 to 14+625 |
| 14+669 | 2 crossing | 1.58 m over Line 1 at 14+669; needs 5.58 m (box over twin tube) |
| 14+915 | 3 cover | Box roof 0.7 m above ground from 14+915 to 14+915 |
| 15+115 | 3 cover | Box roof 1.2 m above ground from 15+095 to 15+135 |
| 15+316 | 2 crossing | 0.93 m under Line 8 at 15+316; needs 6.10 m (box over box) |
| 15+664 | 2 crossing | 1.02 m over Line 2 at 15+664; needs 7.78 m (double-track bore over twin tube) |
| 16+296 | 2 crossing | 3.92 m over RER-5 at 16+297; needs 10.30 m (double-track bore over box) |
| 16+428 | 2 crossing | 5.17 m under Line 6 at 16+428; needs 5.78 m (twin tube over box) |
| 17+065 | 3 cover | Box roof 0.7 m above ground from 17+055 to 17+075 |
| 17+202 | 2 crossing | Crosses RER-1 at grade at 17+202: needs a grade separation |
| 17+455 | 3 cover | Box roof 1.4 m above ground from 17+425 to 17+485 |
| 17+641 | 2 crossing | 4.41 m over Line 4 at 17+641; needs 5.58 m (box over twin tube) |
| 17+970 | 3 cover | Box roof 0.1 m above ground from 17+885 to 18+055 |
| 18+235 | 3 cover | Box roof cover down to 0.59 m from 18+235 to 18+235, needs 0.6 m |
| 18+419 | 2 crossing | 2.47 m under Line 7 at 18+419; needs 6.98 m (twin tube over double-track bore) |
| 18+708 | 2 crossing | 3.37 m under Line 12 at 18+708; needs 6.10 m (box over box) |
| 19+920 | 3 cover | Box roof 0.0 m above ground from 19+875 to 19+965 |
| 20+615 | 3 cover | Box roof cover down to 0.38 m from 20+585 to 20+645, needs 0.6 m |
| 21+036 | 2 crossing | 0.40 m over Line 13 at 21+036; needs 6.10 m (box over box) |
| 21+130 | 3 cover | Box roof 1.4 m above ground from 21+095 to 21+165 |
| 21+840 | 3 cover | Box roof 1.4 m above ground from 21+825 to 21+855 |
| 23+909 | 2 crossing | 0.10 m under Line 14 at 23+909; needs 6.10 m (box over box) |
| 25+090 | 3 cover | Box roof 1.6 m above ground from 25+015 to 25+165 |
| 25+220 | 3 cover | Box roof 1.6 m above ground from 25+195 to 25+245 |
| 26+025 | 3 cover | Box roof 1.3 m above ground from 26+005 to 26+045 |
| 26+610 | 3 cover | Box roof 1.2 m above ground from 26+595 to 26+625 |
| 26+920 | 3 cover | Box roof 0.5 m above ground from 26+885 to 26+955 |

## Line 10 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+205 | 3 cover | Box roof 1.3 m above ground from 0+165 to 0+245 |
| 0+585 | 3 cover | Box roof 1.6 m above ground from 0+555 to 0+615 |
| 1+870 | 3 cover | Box roof 1.4 m above ground from 1+855 to 1+885 |
| 3+790 | 3 cover | Box roof cover down to 0.19 m from 3+785 to 3+795, needs 0.6 m |
| 4+840 | 3 cover | Box roof cover down to 0.58 m from 4+835 to 4+845, needs 0.6 m |
| 5+070 | 3 cover | Box roof 1.5 m above ground from 5+035 to 5+105 |
| 5+850 | 3 cover | Box roof 0.9 m above ground from 5+845 to 5+855 |
| 7+010 | 3 cover | Box roof 0.2 m above ground from 6+915 to 7+105 |
| 9+014 | 2 crossing | 0.09 m under Line 8 at 9+014; needs 6.10 m (box over box) |
| 11+061 | 2 crossing | 1.00 m under Line 7 at 11+061; needs 5.78 m (twin tube over box) |
| 11+187 | 2 crossing | 0.10 m under Line 8 at 11+187; needs 6.10 m (box over box) |
| 11+196 | 2 crossing | 3.28 m over RER-5 at 11+196; needs 8.10 m (box over box) |
| 11+290 | 2 crossing | 2.72 m over RER-1 at 11+290; needs 10.30 m (double-track bore over box) |
| 11+296 | 2 crossing | 9.32 m over RER-2 at 11+296; needs 11.20 m (double-track bore over bored tube) |
| 11+296 | 2 crossing | 2.95 m over RER-4 at 11+296; needs 10.30 m (double-track bore over box) |
| 11+486 | 2 crossing | 1.97 m over RER-5 at 11+486; needs 8.10 m (box over box) |
| 12+027 | 2 crossing | 0.42 m under Line 5 at 12+027; needs 5.78 m (twin tube over box) |
| 12+446 | 2 crossing | 3.52 m under Line 1 at 12+447; needs 6.10 m (box over box) |
| 12+875 | 3 cover | Box roof cover down to 0.36 m from 12+855 to 12+895, needs 0.6 m |
| 12+997 | 2 crossing | 0.00 m over Line 3 at 12+997; needs 5.58 m (box over twin tube) |
| 13+443 | 2 crossing | 0.30 m over Line 2 at 13+443; needs 5.58 m (box over twin tube) |
| 13+738 | 2 crossing | 3.57 m over Line 8 at 13+738; needs 7.30 m (box over double-track bore) |
| 14+605 | 2 crossing | 1.85 m under Line 6 at 14+605; needs 6.98 m (twin tube over double-track bore) |
| 14+749 | 2 crossing | 1.13 m over RER-1 at 14+749; needs 8.10 m (box over box) |
| 14+819 | 2 crossing | 4.80 m over Line 4 at 14+819; needs 7.78 m (double-track bore over twin tube) |
| 15+540 | 2 crossing | 3.50 m under Line 7 at 15+540; needs 5.26 m (twin tube over twin tube) |
| 16+311 | 2 crossing | 1.83 m under Line 5 at 16+311; needs 5.78 m (twin tube over box) |
| 16+393 | 2 crossing | 0.18 m over RER-3 at 16+393; needs 8.10 m (box over box) |
| 17+020 | 3 cover | Box roof 1.3 m above ground from 17+005 to 17+035 |
| 17+107 | 2 crossing | 0.90 m under Line 11 at 17+107; needs 6.10 m (box over box) |
| 17+865 | 3 cover | Box roof 1.3 m above ground from 17+855 to 17+875 |
| 18+220 | 3 cover | Box roof 1.1 m above ground from 18+205 to 18+235 |
| 18+645 | 3 cover | Box roof 1.5 m above ground from 18+595 to 18+695 |
| 18+985 | 3 cover | Box roof 1.6 m above ground from 18+855 to 19+115 |
| 21+255 | 3 cover | Box roof 0.2 m above ground from 21+255 to 21+255 |
| 21+380 | 3 cover | Box roof 0.2 m above ground from 21+355 to 21+405 |

## Line 11 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+625 | 3 cover | Box roof cover down to 0.11 m from 0+525 to 0+725, needs 0.6 m |
| 2+344 | 2 crossing | 0.90 m over Line 10 at 2+344; needs 7.30 m (box over double-track bore) |
| 4+482 | 2 crossing | 0.20 m over Line 6 at 4+482; needs 5.58 m (box over twin tube) |
| 5+045 | 3 cover | Box roof 0.1 m above ground from 5+045 to 5+045 |
| 5+155 | 3 cover | Box roof 1.0 m above ground from 5+135 to 5+175 |
| 5+538 | 2 crossing | 0.10 m over Line 2 at 5+538; needs 5.58 m (box over twin tube) |
| 5+962 | 2 crossing | 0.15 m under Line 3 at 5+962; needs 5.78 m (twin tube over box) |
| 6+615 | 3 cover | Box roof cover down to 0.14 m from 6+605 to 6+625, needs 0.6 m |
| 6+740 | 3 cover | Box roof 0.3 m above ground from 6+725 to 6+755 |
| 7+070 | 3 cover | Box roof cover down to 0.14 m from 7+015 to 7+125, needs 0.6 m |
| 7+804 | 2 crossing | 0.16 m under Line 2b at 7+804; needs 5.78 m (twin tube over box) |
| 7+833 | 2 crossing | 0.80 m over Line 6 at 7+833; needs 5.58 m (box over twin tube) |
| 8+170 | 3 cover | Box roof 1.6 m above ground from 8+115 to 8+225 |
| 8+570 | 3 cover | Box roof 1.3 m above ground from 8+505 to 8+635 |
| 10+170 | 3 cover | Box roof 1.5 m above ground from 10+135 to 10+205 |
| 10+585 | 3 cover | Box roof 1.6 m above ground from 10+495 to 10+675 |
| 11+205 | 3 cover | Box roof 0.9 m above ground from 11+185 to 11+225 |
| 11+415 | 3 cover | Box roof 1.6 m above ground from 11+285 to 11+545 |
| 11+930 | 3 cover | Box roof 1.5 m above ground from 11+805 to 12+055 |
| 12+186 | 2 crossing | 3.25 m under Line 6 at 12+186; needs 6.10 m (box over box) |
| 12+570 | 3 cover | Box roof 1.4 m above ground from 12+505 to 12+635 |
| 13+230 | 3 cover | Box roof 1.5 m above ground from 13+145 to 13+315 |
| 14+315 | 3 cover | Box roof 1.4 m above ground from 14+285 to 14+345 |
| 14+950 | 3 cover | Box roof 0.2 m above ground from 14+885 to 15+015 |
| 16+815 | 3 cover | Box roof 0.9 m above ground from 16+655 to 16+975 |
| 18+965 | 3 cover | Box roof 1.5 m above ground from 18+895 to 19+035 |
| 19+400 | 3 cover | Box roof 1.6 m above ground from 19+205 to 19+595 |
| 21+740 | 3 cover | Box roof 1.5 m above ground from 21+675 to 21+805 |
| 22+120 | 3 cover | Box roof 1.4 m above ground from 22+025 to 22+215 |
| 22+325 | 3 cover | Box roof 1.3 m above ground from 22+295 to 22+355 |
| 22+740 | 3 cover | Box roof 1.5 m above ground from 22+645 to 22+835 |
| 23+670 | 3 cover | Box roof 1.3 m above ground from 23+635 to 23+705 |
| 24+930 | 3 cover | Box roof 1.5 m above ground from 24+905 to 24+955 |
| 25+750 | 3 cover | Box roof 1.6 m above ground from 25+725 to 25+775 |
| 27+465 | 3 cover | Box roof 1.5 m above ground from 27+405 to 27+525 |
| 28+100 | 3 cover | Box roof 1.5 m above ground from 27+625 to 28+575 |
| 29+500 | 3 cover | Box roof 1.6 m above ground from 29+465 to 29+535 |
| 29+830 | 3 cover | Box roof 1.4 m above ground from 29+805 to 29+855 |

## Line 12 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+130 | 3 cover | Box roof cover down to 0.44 m from 0+095 to 0+165, needs 0.6 m |
| 0+990 | 3 cover | Box roof 1.0 m above ground from 0+865 to 1+115 |
| 2+145 | 3 cover | Box roof 1.1 m above ground from 1+955 to 2+335 |
| 2+232 | 2 crossing | 2.93 m under RER-4 at 2+232; needs 5.90 m (at grade over box) |
| 2+940 | 3 cover | Box roof 1.5 m above ground from 2+885 to 2+995 |
| 3+120 | 3 cover | Box roof 1.3 m above ground from 3+095 to 3+145 |
| 3+423 | 2 crossing | 5.45 m under RER-2 at 3+423; needs 7.30 m (box over double-track bore) |
| 3+658 | 2 crossing | 4.30 m over Line 5 at 3+658; needs 5.58 m (box over twin tube) |
| 3+955 | 3 cover | Box roof 0.6 m above ground from 3+735 to 4+175 |
| 4+306 | 2 crossing | 2.60 m under Line 3 at 4+307; needs 5.78 m (twin tube over box) |
| 4+560 | 3 cover | Box roof 1.4 m above ground from 4+545 to 4+575 |
| 4+720 | 3 cover | Box roof cover down to 0.13 m from 4+715 to 4+725, needs 0.6 m |
| 4+860 | 3 cover | Box roof cover down to 0.26 m from 4+845 to 4+875, needs 0.6 m |
| 8+315 | 3 cover | Box roof cover down to 0.47 m from 8+315 to 8+315, needs 0.6 m |
| 8+375 | 3 cover | Box roof 0.1 m above ground from 8+375 to 8+375 |
| 8+745 | 3 cover | Box roof 1.2 m above ground from 8+715 to 8+775 |
| 9+844 | 2 crossing | 0.20 m over Line 7 at 9+844; needs 5.58 m (box over twin tube) |
| 10+777 | 2 crossing | 3.37 m over Line 9 at 10+777; needs 7.30 m (box over double-track bore) |
| 11+648 | 2 crossing | 4.12 m over Line 4 at 11+648; needs 5.58 m (box over twin tube) |
| 11+920 | 3 cover | Box roof 1.6 m above ground from 11+895 to 11+945 |
| 12+060 | 3 cover | Box roof 1.6 m above ground from 12+035 to 12+085 |
| 12+640 | 2 crossing | 3.68 m under Line 4 at 12+640; needs 6.10 m (box over box) |
| 13+560 | 3 cover | Box roof 0.3 m above ground from 13+475 to 13+645 |
| 13+842 | 2 crossing | 0.52 m over Line 13 at 13+842; needs 7.30 m (box over double-track bore) |
| 13+985 | 3 cover | Box roof cover down to 0.37 m from 13+965 to 14+005, needs 0.6 m |
| 14+275 | 3 cover | Box roof 1.5 m above ground from 14+195 to 14+355 |
| 14+905 | 3 cover | Box roof 1.4 m above ground from 14+885 to 14+925 |
| 15+500 | 3 cover | Box roof 0.9 m above ground from 15+415 to 15+585 |
| 15+888 | 2 crossing | 1.40 m under Line 14 at 15+888; needs 6.10 m (box over box) |
| 16+970 | 3 cover | Box roof cover down to 0.07 m from 16+915 to 17+025, needs 0.6 m |
| 18+155 | 3 cover | Box roof 1.6 m above ground from 18+135 to 18+175 |
| 18+620 | 3 cover | Box roof 1.3 m above ground from 18+615 to 18+625 |
| 20+755 | 3 cover | Box roof cover down to 0.33 m from 20+735 to 20+775, needs 0.6 m |
| 21+100 | 3 cover | Box roof 1.4 m above ground from 21+075 to 21+125 |
| 21+515 | 3 cover | Box roof 1.4 m above ground from 21+465 to 21+565 |
| 21+635 | 3 cover | Box roof 1.5 m above ground from 21+595 to 21+675 |
| 22+030 | 3 cover | Box roof 1.4 m above ground from 22+005 to 22+055 |
| 22+565 | 3 cover | Box roof 1.6 m above ground from 22+445 to 22+685 |
| 22+930 | 3 cover | Box roof 1.5 m above ground from 22+835 to 23+025 |

## Line 13 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+752 | 2 crossing | 0.00 m over Line 5 at 0+752; needs 5.58 m (box over twin tube) |
| 0+815 | 3 cover | Box roof cover down to 0.30 m from 0+815 to 0+815, needs 0.6 m |
| 0+895 | 3 cover | Box roof 0.5 m above ground from 0+895 to 0+895 |
| 1+024 | 2 crossing | 0.01 m under Line 3 at 1+024; needs 5.78 m (twin tube over box) |
| 1+261 | 2 crossing | 0.72 m under Line 8 at 1+261; needs 7.78 m (double-track bore over twin tube) |
| 1+530 | 3 cover | Box roof 1.4 m above ground from 1+515 to 1+545 |
| 1+830 | 3 cover | Box roof 1.5 m above ground from 1+795 to 1+865 |
| 2+065 | 3 cover | Box roof 1.5 m above ground from 2+025 to 2+105 |
| 2+280 | 3 cover | Box roof 1.5 m above ground from 2+235 to 2+325 |
| 2+951 | 2 crossing | 3.04 m over Line 1 at 2+951; needs 7.78 m (double-track bore over twin tube) |
| 3+445 | 3 cover | Box roof cover down to 0.44 m from 3+415 to 3+475, needs 0.6 m |
| 3+585 | 2 crossing | 1.53 m over Line 2 at 3+585; needs 5.58 m (box over twin tube) |
| 4+908 | 2 crossing | 4.33 m under Line 6 at 4+908; needs 6.98 m (twin tube over double-track bore) |
| 5+562 | 2 crossing | 3.95 m over RER-5 at 5+562; needs 8.10 m (box over box) |
| 6+591 | 2 crossing | 3.73 m over Line 7 at 6+591; needs 5.58 m (box over twin tube) |
| 6+645 | 3 cover | Box roof 1.4 m above ground from 6+565 to 6+725 |
| 7+570 | 2 crossing | 0.59 m under Line 4 at 7+570; needs 6.98 m (twin tube over double-track bore) |
| 8+515 | 2 crossing | 0.52 m under Line 12 at 8+515; needs 6.10 m (box over box) |
| 9+310 | 2 crossing | 0.40 m under Line 9 at 9+310; needs 6.10 m (box over box) |
| 15+540 | 3 cover | Box roof 1.4 m above ground from 15+525 to 15+555 |
| 15+855 | 3 cover | Box roof 1.5 m above ground from 15+835 to 15+875 |
| 16+325 | 3 cover | Box roof 1.2 m above ground from 16+295 to 16+355 |
| 16+580 | 3 cover | Box roof 1.5 m above ground from 16+515 to 16+645 |
| 16+715 | 3 cover | Box roof 1.4 m above ground from 16+685 to 16+745 |
| 19+210 | 3 cover | Box roof 1.6 m above ground from 19+185 to 19+235 |
| 19+465 | 3 cover | Box roof 1.2 m above ground from 19+455 to 19+475 |
| 19+955 | 3 cover | Box roof 1.2 m above ground from 19+935 to 19+975 |
| 20+090 | 3 cover | Box roof 1.5 m above ground from 20+055 to 20+125 |
| 22+235 | 3 cover | Box roof 1.2 m above ground from 22+035 to 22+435 |
| 23+200 | 3 cover | Box roof 0.1 m above ground from 22+905 to 23+495 |
| 24+080 | 3 cover | Box roof 0.3 m above ground from 23+995 to 24+165 |
| 26+370 | 3 cover | Box roof 0.7 m above ground from 26+265 to 26+475 |

## Line 14 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 0+165 | 3 cover | Box roof cover down to 0.19 m from 0+145 to 0+185, needs 0.6 m |
| 0+955 | 3 cover | Box roof 0.7 m above ground from 0+865 to 1+045 |
| 2+170 | 3 cover | Box roof 1.2 m above ground from 2+155 to 2+185 |
| 2+615 | 3 cover | Box roof 1.1 m above ground from 2+595 to 2+635 |
| 4+913 | 2 crossing | 3.14 m under Line 5 at 4+913; needs 6.98 m (twin tube over double-track bore) |
| 7+445 | 3 cover | Box roof 0.5 m above ground from 7+355 to 7+535 |
| 7+628 | 2 crossing | 0.20 m over Line 1 at 7+628; needs 5.58 m (box over twin tube) |
| 7+790 | 3 cover | Box roof 1.5 m above ground from 7+755 to 7+825 |
| 8+675 | 3 cover | Box roof 1.3 m above ground from 8+645 to 8+705 |
| 8+930 | 3 cover | Box roof 1.1 m above ground from 8+915 to 8+945 |
| 9+010 | 3 cover | Box roof 1.6 m above ground from 8+975 to 9+045 |
| 9+165 | 3 cover | Box roof 0.5 m above ground from 9+165 to 9+165 |
| 9+895 | 3 cover | Box roof cover down to 0.31 m from 9+895 to 9+895, needs 0.6 m |
| 11+265 | 3 cover | Box roof 1.3 m above ground from 11+255 to 11+275 |
| 12+220 | 2 crossing | 1.67 m over Line 2 at 12+220; needs 5.58 m (box over twin tube) |
| 13+290 | 3 cover | Box roof 0.6 m above ground from 13+195 to 13+385 |
| 13+508 | 2 crossing | 2.30 m under Line 7 at 13+509; needs 5.78 m (twin tube over box) |
| 14+695 | 3 cover | Box roof 1.5 m above ground from 14+665 to 14+725 |
| 15+085 | 3 cover | Box roof 1.0 m above ground from 15+075 to 15+095 |
| 16+145 | 3 cover | Box roof cover down to 0.22 m from 16+085 to 16+205, needs 0.6 m |
| 16+530 | 2 crossing | 1.64 m over Line 4 at 16+530; needs 5.58 m (box over twin tube) |
| 16+582 | 2 crossing | 1.88 m under Line 3 at 16+582; needs 5.78 m (twin tube over box) |
| 18+321 | 2 crossing | 1.40 m over Line 12 at 18+321; needs 6.10 m (box over box) |
| 19+417 | 2 crossing | 0.10 m over Line 9 at 19+417; needs 6.10 m (box over box) |
| 21+150 | 3 cover | Box roof 1.4 m above ground from 21+075 to 21+225 |
| 21+635 | 3 cover | Box roof 1.6 m above ground from 21+625 to 21+645 |
| 24+975 | 3 cover | Box roof 0.9 m above ground from 24+935 to 25+015 |
| 25+455 | 3 cover | Box roof 1.5 m above ground from 25+215 to 25+695 |
| 26+015 | 3 cover | Box roof 1.5 m above ground from 25+815 to 26+215 |
| 27+930 | 3 cover | Box roof 1.5 m above ground from 27+705 to 28+155 |
| 28+510 | 3 cover | Box roof 1.6 m above ground from 28+425 to 28+595 |
| 29+140 | 3 cover | Box roof 1.4 m above ground from 29+105 to 29+175 |
| 31+900 | 3 cover | Box roof 1.2 m above ground from 31+885 to 31+915 |
| 33+520 | 3 cover | Box roof 1.4 m above ground from 33+485 to 33+555 |
| 34+050 | 3 cover | Box roof 1.5 m above ground from 33+955 to 34+145 |
| 35+920 | 3 cover | Box roof cover down to 0.44 m from 35+875 to 35+965, needs 0.6 m |

## RER-1 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 2+304 | 2 crossing | 1.53 m under Line 7 at 2+304; needs 7.78 m (twin tube over box) |
| 2+440 | 2 crossing | 0.76 m over RER-5 at 2+440; needs 8.10 m (box over box) |
| 2+465 | 2 crossing | 2.72 m under Line 10 at 2+465; needs 10.30 m (double-track bore over box) |
| 2+833 | 2 crossing | 3.66 m under Line 5 at 2+833; needs 7.78 m (twin tube over box) |
| 3+211 | 2 crossing | 5.17 m under Line 1 at 3+211; needs 8.10 m (box over box) |
| 3+280 | 2 crossing | 0.03 m under Line 8 at 3+280; needs 10.30 m (double-track bore over box) |
| 3+818 | 2 crossing | 1.24 m under Line 5 at 3+819; needs 7.78 m (twin tube over box) |
| 4+115 | 2 crossing | 5.37 m under Line 4 at 4+115; needs 7.78 m (twin tube over box) |
| 4+283 | 2 crossing | 1.87 m over Line 3 at 4+283; needs 5.58 m (box over twin tube) |
| 4+427 | 2 crossing | 5.13 m under Line 7 at 4+427; needs 7.78 m (twin tube over box) |
| 4+776 | 2 crossing | 3.16 m over Line 2 at 4+776; needs 5.58 m (box over twin tube) |
| 5+351 | 2 crossing | 0.15 m under Line 6 at 5+351; needs 7.78 m (twin tube over box) |
| 5+416 | 2 crossing | 4.73 m under Line 7 at 5+416; needs 7.78 m (twin tube over box) |
| 5+676 | 2 crossing | 5.69 m under Line 4 at 5+676; needs 8.10 m (box over box) |
| 5+682 | 2 crossing | 2.20 m over Line 5 at 5+682; needs 5.58 m (box over twin tube) |
| 6+591 | 2 crossing | 1.13 m under Line 10 at 6+591; needs 10.30 m (double-track bore over box) |
| 9+224 | 2 crossing | Crosses Line 9 at grade at 9+225: needs a grade separation |
| 12+090 | 2 crossing | 5.07 m over Line 4 at 12+090; needs 5.90 m (at grade over box) |

## RER-2 (saved)

| Chainage | Rule | Flag |
|---|---|---|
| 3+867 | 2 crossing | 7.28 m under Line 1 at 3+867; needs 8.60 m (viaduct over at grade) |
| 6+035 | 2 crossing | 5.19 m over Line 8 at 6+035; needs 5.90 m (at grade over box) |
| 7+370 | 2 crossing | 5.45 m over Line 12 at 7+370; needs 7.30 m (box over double-track bore) |
| 8+172 | 2 crossing | 0.00 m over Line 9 at 8+172; needs 7.30 m (box over double-track bore) |
| 9+716 | 2 crossing | 7.06 m under Line 7 at 9+716; needs 7.90 m (at grade over box) |
| 11+409 | 2 crossing | 6.18 m under RER-5 at 11+409; needs 9.00 m (box over bored tube) |
| 11+435 | 2 crossing | 9.32 m under Line 10 at 11+435; needs 11.20 m (double-track bore over bored tube) |
| 21+721 | 2 crossing | 3.54 m over Line 6 at 21+721; needs 5.90 m (at grade over box) |

## RER-3 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 7+370 | 2 crossing | 0.50 m over Line 8 at 7+370; needs 6.10 m (box over box) |
| 8+241 | 2 crossing | 7.03 m over RER-5 at 8+241; needs 8.10 m (box over box) |
| 10+801 | 2 crossing | 3.71 m over Line 3 at 10+801; needs 7.10 m (viaduct over viaduct) |
| 11+225 | 2 crossing | 1.49 m over Line 2 at 11+225; needs 7.10 m (viaduct over viaduct) |
| 11+890 | 2 crossing | 2.72 m over Line 6 at 11+890; needs 5.58 m (box over twin tube) |
| 13+978 | 2 crossing | 0.18 m under Line 10 at 13+978; needs 8.10 m (box over box) |

## RER-4 (default)

| Chainage | Rule | Flag |
|---|---|---|
| 5+078 | 2 crossing | 0.18 m over Line 2 at 5+078; needs 5.58 m (box over twin tube) |
| 5+382 | 2 crossing | 6.79 m under Line 7 at 5+382; needs 7.78 m (twin tube over box) |
| 5+569 | 2 crossing | 0.46 m over Line 3 at 5+569; needs 5.58 m (box over twin tube) |
| 5+720 | 2 crossing | 5.18 m under Line 4 at 5+720; needs 7.78 m (twin tube over box) |
| 6+024 | 2 crossing | 1.11 m under Line 5 at 6+024; needs 7.78 m (twin tube over box) |
| 6+564 | 2 crossing | 0.09 m under Line 8 at 6+565; needs 10.30 m (double-track bore over box) |
| 6+625 | 2 crossing | 5.14 m under Line 1 at 6+625; needs 8.10 m (box over box) |
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
| 12+528 | 2 crossing | 6.18 m under Line 3 at 12+528; needs 7.78 m (twin tube over box) |
| 13+079 | 2 crossing | 2.43 m under Line 1 at 13+079; needs 8.10 m (box over box) |
| 13+470 | 2 crossing | 1.45 m over Line 5 at 13+470; needs 5.58 m (box over twin tube) |
| 13+892 | 2 crossing | 1.96 m under Line 10 at 13+892; needs 8.10 m (box over box) |
| 14+081 | 2 crossing | 6.18 m over RER-2 at 14+081; needs 9.00 m (box over bored tube) |
| 14+082 | 2 crossing | 0.25 m under RER-4 at 14+082; needs 8.10 m (box over box) |
| 14+093 | 2 crossing | 0.76 m under RER-1 at 14+093; needs 8.10 m (box over box) |
| 14+175 | 2 crossing | 3.28 m under Line 10 at 14+175; needs 8.10 m (box over box) |
| 14+180 | 2 crossing | 3.38 m under Line 8 at 14+180; needs 8.10 m (box over box) |
| 14+564 | 2 crossing | 5.73 m under Line 7 at 14+565; needs 7.78 m (twin tube over box) |
| 15+325 | 2 crossing | 7.03 m under RER-3 at 15+325; needs 8.10 m (box over box) |
| 15+426 | 4 river | Under the Ohio River from 15+400 to 15+426 the rail is up to 8.76 m above bed − 8 m (worst at 15+426) |

