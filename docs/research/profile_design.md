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

- **Vertical curves are built into the rail** (page and `railsim/metro_profile.py`, so run times use them): radius 1,500 m Metro, 3,000 m RER. Curves stay off platforms: the platform level runs on past each platform end for half the curve (the transition), then the curve, then the straight grade. Where the straight grade is too short the curves are shortened and flagged. The station solver allows for the transitions (each platform counts as its length plus one curve at the steepest grade), and river-tube bottoms are held half a curve beyond each bank.
- **Bored tunnels need the cover of their era's practice**, else the stretch is cut and cover:
  - Lines 1-7 (1903-1913): about 2 m, the shallow shield and gallery work of the day (canon basin method).
  - Lines 8-12 (1933-1941) and 13-14 (1949-1959): about one tube diameter, 6 m (Chicago State Street 1938-43 and Dearborn 1951: 25 ft shields, tube floors 43-50 ft below the street).
  - RER (1985-1996): one diameter, 8.5 m.
- **RER-3 covered way** may stay flat: it drains beneath into the sewers (no drainage flags there).
- Stations may slope slightly (MTA practice); not modelled, since 3 per mille over a platform gains under half a metre.
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
