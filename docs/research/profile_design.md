# Vertical alignment practice for the Rail Profiles page

What real long-section design checks that the editor did not, and what the page now does. Tags: [S] source found, [E] engineering estimate or rule of thumb.

| Topic | Practice | Source |
|---|---|---|
| Vertical curves | A vertical curve is always introduced where the grade changes. Metros use minimum radii of 1,500 to 3,000 m, main lines 3,000 to 4,000 m. At 80 km/h that is about 0.32 m/s² (1,500 m) and 0.17 m/s² (3,000 m) of vertical acceleration. | [S] Transportation tunnels chapter via Taylor & Francis; metro radius figures in a metro design note quoted by search |
| Curves on platforms | Vertical curves stay off platforms; at a platform end the whole curve lies outside it. | [E] common practice |
| Drainage | Minimum tunnel grade 0.3% (3 per mille) for drainage; Brisbane Airport Link used 0.5%. Low points need pump sumps. Stations about 0.2-0.3% at most. | [S] Taylor & Francis "Drainage gradient" chapter; Airport Link EIS ch. 4; NYC subway drainage chapter |
| Cover over bored tunnels | About one tunnel diameter (1D) of cover is the usual screening value; less needs specific analysis (lining, flotation, blow-out); under structures often 1.5D or more. The 1900s basin method in canon ran shallower. | [S] large-diameter TBM note; Eng-Tips thread; IS 13783 summary |
| Curve compensation | Grade on a curve is reduced for curve resistance: 0.04% per degree of curve (Indian/AREMA practice, about 700/R per mille) or SNCF 800/R per mille, the rule the simulator already uses for curve resistance. | [S] Ruling gradient (Wikipedia); IIT railway notes; OSRD physical modelling |
| Crossings | Rail-to-rail clearance at crossings (the page's 8 m Metro / 9 m RER) is a design input; lines are solved together, not one at a time. | [E] |

## What the page now checks

- **Vertical curve**: every grade change needs a curve of `vcRadius x change` (half each side; all of it outside a platform). A flag where the straight grade between two changes is shorter than the curves need (for example Line 5 Times to Eggleston, 55.6 m at 50 per mille between two level platforms needs 150 m at 1,500 m radius).
- **Drainage**: tunnel stretches flatter than `drainMin` (3 per mille) for more than 60 m, outside platforms; tunnel low points counted as sumps.
- **Cover**: shallow-shield and deep-tube stretches with less than `minCover` over the crown (rail + envelope); cut-and-cover with its roof above ground.
- **Curve grade**: grade plus `curveK / R` per mille over the limit, with R from the drawn plan (circle through points 40 m apart).
- Flags are listed along the line with their kind, click to jump; red markers sit along the bottom of the profile.
- **Solve levels with crossings**: re-solves the line so each crossing keeps the minimum clearance, under the other line where the plain solution is lower and over it where higher, adding crossings one at a time and keeping only those that fit within the grade limit, the canon levels and the river tubes.

## Rulings (Ben) and what the page and simulator now do

- **Vertical curves are built into the rail** (page and `railsim/metro_profile.py`, so run times use them): radius 1,500 m Metro, 3,000 m RER. Curves stay off platforms: the platform level runs on past each platform end for half the curve (the transition), then the curve, then the straight grade. Every curve is at least 30.5 m long (AREMA and Amtrak 100 ft minimum; UK practice 25 m), so small bends are rounded visibly and in the rail too. Where the straight grade is too short the curves are shortened and flagged. The station solver allows for the transitions (each platform counts as its length plus one curve at the steepest grade), and river-tube bottoms are held half a curve beyond each bank.
- **Bored tunnels need the cover of their era's practice**, else the stretch is cut and cover:
  - Lines 1-7 (1903-1913): about 2 m, the shallow shield and gallery work of the day (canon basin method).
  - Lines 8-12 (1933-1941) and 13-14 (1949-1959): about one tube diameter, 6 m (Chicago State Street 1938-43 and Dearborn 1951: 25 ft shields, tube floors 43-50 ft below the street).
  - RER (1985-1996): one diameter, 8.5 m.
- **Structure sizes by era** (Ben: standard metro boxes of the era; RATP RER or LIRR for the RER), from top of rail to top of roof or lining:

  | Lines | Era | Box and station box | Bored tube crown | Basis |
  |---|---|---|---|---|
  | 1-6, 2b | 1903-1913 | 5.0 m | 4.3 m | IRT 1904 minimum section 12 ft 3 in clear above rail [S], 2 ft 6 in roof [S]; shield tubes about 15.5 ft inside [E] |
  | 7 | 1913 | 5.0 m | 4.3 m | Lexington Ave (Dual Contracts) 13 ft 10 in clear [S] + roof |
  | 8-14 | 1933-1959 | 5.0 m | 5.2 m | Chicago State St / Dearborn tubes 15 ft clear [S]; Boston 1897 boxes 14 ft clear [S] + about 0.8 m roof [E] |
  | RER | 1985-1996 | 6.6 m | 7.5 m | RATP RER style with 25 kV overhead over bilevel stock: about 5.8 m clear + roof [E]; Paris RER bores 6.3 m single-track, 8.7 m double-track [S] |

  Metro boxes are one 5.0 m standard on every line (Ben: mezzanines and connectors are designed on top of them later); the era sizes in the basis column are the reference. Station boxes are single-level like the running box. The old flat 5.5 m (Metro) and 7 m (RER) were too tall for the early lines.
- **Grade separation at crossings** (above or below ground) replaces the flat 8 m / 9 m rail-to-rail minimum. The upper rail must clear: the lower line's height (its box, its bored tube, or in the open the clear height its trains and wires need under a bridge: the box less a 0.8 m roof, 4.2 m Metro, 5.8 m RER under 25 kV) + the upper line's structure below its rail (viaduct deck 1.5 m Metro / 2.0 m RER, box or tube floor 1.0 m, track bed at grade 0.8 m) + 2 m of ground where a bored tube meets another structure underground. Two lines at grade crossing each other are flagged as needing a grade separation. Each line's type at the crossing comes from its own rail and the ground there. Deck, floor, bed, gap and clear-height values accepted by Ben. The RER-2 / Line 7 level crossing on the Mill Creek trunk (RER-2 9+716) is Ben's to fix in the drawing. The crossing solver uses the same requirement.
- **Metro structure rules** (Ben, replacing the era boxes and tubes above, the 5.5 m envelope and the 8 m crossing minimum; heights from top of rail):

  | Structure | Below rail | Rail to top | Outside | Used for |
  |---|---|---|---|---|
  | Cut-and-cover box (and station box) | 1.0 m | 4.6 m | | type cut & cover |
  | Twin tube (4.4 m inside, rail 0.5 m above invert) | 0.68 m | 4.08 m | 4.76 m | deep tube on every line; shield on Lines 1-7; every river crossing |
  | Double-track bore | 3.2 m | 5.8 m | 9.0 m | shield on Lines 8-14 |

  - Crossings: rail-to-rail separation at least the upper line's below-rail + 0.5 m + the lower line's rail-to-top. Applied to every crossing on both systems, RER with its own settings (box 6.6 m, bore 7.5 m, floor 1.0 m). A viaduct counts its deck (1.5 m Metro, 2.0 m RER) and a line at grade its track bed (0.8 m) as below-rail. A line in the open counts its box height as its rail-to-top (the clear height under a bridge). Two lines at grade are flagged as needing a grade separation.
  - Cover over the top: tube or bore with its top above 140.0 m (basin water table, about river level) 2.0 m, at or below 140.0 m one outside diameter (4.76 m tube, 9.0 m bore); box roof 0.6 m. A tube or bore with less cover is typed cut and cover.
  - Rivers: at every chainage inside a river range, in tunnel, rail at most bed - 7.5 m on the Metro (1.0 scour + 2.38 half-diameter cover + 4.08 rail to top) and bed - 8.0 m on the RER (1.0 scour + 1.5 backfill + 5.5 rail to top), bed = the ground raster there.
  - Flags by line: `docs/research/metro_rules_flags.md`.
- **Rulings of 2026-10-09** (Ben):
  - Portal ramps (Metro): rail less than 4.6 m below ground is an open trough (new type, no cover rule); 4.6 to 5.2 m is a box whose roof forms the street surface (thin-cover WARNING, not an error); from 5.2 m the 0.6 m roof cover rule.
  - A line in the open under another structure needs its clear height from rail to the structure's underside: Metro 4.2 m (ballasted track is lifted in maintenance and the car bounces more than on tunnel slab track), RER 5.8 m.
  - River bed: the map 3 ground now holds the canon riverbed in the Ohio and Licking (handoff tiles of 2026-10-09); canon.json's 12 m Ohio bed depth is dropped. The Little Miami has no survey: pool - 3 m.
  - RER river crossings are sunk box sections in a dredged trench (Transbay model), drawn as RER boxes: rail <= bed - 9.1 m (1.0 scour + 1.5 backfill + 6.6 rail to top), replacing bed - 8.0 m.
  - Solvers: the Metro solver holds rail <= bed - 7.5 m under rivers for default-solved lines; saved profiles are only flagged. The RER solver holds rail <= bed - 9.1 m (was pool - 22.5 m). Both hold the lowest bed in the river range.
- **RER-3 covered way** may stay flat: it drains beneath into the sewers (no drainage flags there).
- **Sloped platforms** (Ben: MTA-style slight grades in stations, to ease the bends on either side; limit by era): each station has a platform grade about its centre level (`sg`, per mille). The transitions carry the platform grade on, so a station on a climb needs smaller bends at both ends. 'Ease the bends' (per station) and 'Ease all platforms' set each platform to the mean of the grades either side, within the limit. Saved with the profile and used by the simulator. Limits by era:

  | System / era | Platform limit | Basis |
  |---|---|---|
  | Metro Lines 1-7 (1903-1913) | 7.5 per mille | Ben's ruling; New York, *The Design of Subways* (1918): stations and approaches at most 0.75% so trains do not creep with brakes off; vertical curves kept off stations [S] |
  | Metro Lines 8-14 (1933-1959) | 4 per mille | Ben's ruling; close to London's historic 1 in 260 (3.8 per mille) |
  | RER (1985-1996) | 2.5 per mille | Modern main-line station limit: German EBO / European TSI 2.5 per mille for new station tracks [S]; UK about 1 in 400 for new platforms (historic 1 in 260, later 1 in 500) [S, forum-quoted] |
  | Reference | | London exceptions: Oval northbound 1 in 76 (13 per mille, 1920s extension), West Finchley 1 in 81 [forum]; BOStrab 1969 (trams) 2.5% at terminal stops [S]; Paris: no published figure found |
- Starting values still: `drainMin` 3 per mille, `curveK` 800.

Sources added for the era cover: Chicago State Street subway (ASCE 1943 abstract; chicago-l.org), Dearborn subway (Encyclopedia of Chicago), Paris Metro construction (RATP).
- https://ascelibrary.com/doi/10.1061/TACEAT.0005664
- https://www.chicago-l.org/operations/lines/state_subway.html
- https://www.chicago-l.org/tour/handout03.pdf
- https://encyclopedia.chicagohistory.org/pages/1275.html
- https://www.ratp.fr/decouvrir/le-metro-parisien-a-120-ans

## Sources

- https://taylorandfrancis.com/knowledge/Engineering_and_technology/Civil%2c_environmental_and_geotechnical_engineering/Drainage_gradient
- https://eisdocs.dsdip.qld.gov.au/Airport%20Link/EIS/Volume%201%20-%20EIS/eis-04-project-description.pdf
- https://nycsubway.org/wiki/The_New_York_Subway:_Chapter_10,_Subway_Drainage
- https://www.si-eng.org/post/scale-factors-of-large-diameter-tbm-built-tunnels
- https://eng-tips.com/threads/soil-cover-for-tunnels.320691
- https://infralens.in/code/IS-13783-Part-2-1993
- https://en.wikipedia.org/wiki/Ruling_gradient
- https://sathee.iitk.ac.in/sathee-railway-exams/student-corner/railway-gk/track-engineering/curves-gradients
- https://en.wikipedia.org/wiki/Minimum_railway_curve_radius
- https://libraryarchives.metro.net:443/DPGTL/scrtd/1986-civil-speed-limits-on-horizontal-and-vertical-curves.pdf
- https://www.nycsubway.org/wiki/Chapter_04._Design_of_Structure_and_Track
- https://www.nycsubway.org/wiki/Chapter_14:_Engineering_Features_of_the_New_York_Subway
- https://www.nycsubway.org/wiki/The_New_York_Subway:_Chapter_02,_Types_and_Methods_of_Construction
- https://www.nycsubway.org/wiki/Chapter_20:_Rapid_Transit_in_Other_Cities:_London,_Berlin,_Budapest,_Paris,_Glasgow,_Boston,_Chicago,_Philadelphia
- https://en.wikipedia.org/wiki/Cobble_Hill_Tunnel
- https://mirror2.polsri.ac.id/wiki/wp/r/RER.htm
- https://www.nycsubway.org/wiki/The_Design_of_Subways_(1918)
- https://www.railforums.co.uk/threads/steepest-track-gradient-in-stations.183578/
- https://www.railforums.co.uk/threads/maximum-slope-allowed-in-new-stations.230452/
- https://www.kontextwochenzeitung.de/politik/100/der-schiefbahnhof-1-398.html
- http://www.meyer-strassenbahn.de/bostrab/bostrab1969.html
- https://www.lagrandealliance.quebec/wp-content/uploads/2023/05/LGA-APPENDICES-Railway-design-criteria.pdf
- https://railtec.illinois.edu/wp/wp-content/uploads/AREMA-Chapter-5-2007.pdf
- https://www.amtrak.com/content/dam/projects/dotcom/english/public/documents/corporate/engineering-practices/engineering-specs/amtrak-track-design-specification-63.pdf
- https://www.thepwi.org/wp-content/uploads/2021/02/Journal-202004-Vol138-Pt2-BACK-TO-BASICS-Vertical-alignment-design.pdf
