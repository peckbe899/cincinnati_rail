# Commuter / RER / Regional rail — physical parameters for the travel-time simulator

Compiled 2026-10-08.

**How this was gathered.** Direct page fetches (WebFetch, and curl to ecfr.gov, cornell.edu, stadlerrail.com and siemens.com) were blocked by DNS or the egress proxy in this session. Most figures therefore come from web-search result extracts of the cited URLs. Two GitHub repositories could be cloned and were read directly:

- TransitMatters `regional-rail-schedule-generator`, which contains the full **MBTA GTFS, Fall 2025 "version D"** (feed 2025-09-09 to 2025-12-13).
- `railtoolkit/TrainRuns.jl`, which implements the Wende/Sauthoff resistance model.

**Tags used on every number:**

- **[P]**: published by a manufacturer, agency or regulation.
- **[S]**: secondary source (Wikipedia, news, trade press, forum, blog).
- **[E]**: my own estimate or derivation. The derivation is shown.

**Unit conversions used throughout:**

- 1 lbf = 4.44822 N.
- 1 short ton = 0.907185 t.
- 1 mph = 0.44704 m/s.
- 1 mph/s = 0.447 m/s².
- 1 lb/mph = 9.950 N/(m/s).
- 1 lb/mph² = 22.26 N/(m/s)².
- 1 lb/short-ton = 4.903 N/t.

---

## 1. Rolling stock parameters

The tables below give one block per train type. "—" means no source was found. Fill-in planning values are listed after the tables.

### 1a. Electric multiple units

| Field | Stadler FLIRT 160 (EMU, generic and Swiss/Nordic) | Stadler KISS (Caltrain) | Siemens Mireo (3-car) / Desiro HC | Alstom Coradia Stream | Kawasaki M9 (LIRR/MNR) |
|---|---|---|---|---|---|
| Consist | 2–8 cars. Swiss RABe 523 = 4 cars, with only the two end Jacobs bogies powered [S] (loco-info / Wikipedia via search). Norway Type 75 ≈ 112.7 m [S] (loco-info 14981) | Caltrain 6-car = 515 ft 3 in (157 m); can be extended to 7–8 cars [S] (railjournal, railwayage) | Mireo 3-car = 69.86 m [P] (Siemens Mireo Smart data sheet). Desiro HC 4-car = 105 m [P] (Siemens Desiro HC Egypt data sheet) | NS ICNG 5-car = 110 m, 8-car = 164.9 m [S] (Wikipedia NS ICNG). NAH.SH 4-car = 106 m [S] (globalrailwayreview) | 85 ft (25.9 m) cars in married pairs [S] (Wikipedia M9) |
| Empty mass | FLIRT family 76–206 t [S] (Wikipedia FLIRT). RABe 521: 123.4 t [P-ish] (EPFL fiche Fich0321). Type 74/75 ≈ 170 t [S] (loco-info) | 6-car generic KISS 296 t [S] (Wikipedia Stadler KISS) | Mireo 3-car 112 t [S] (Wikipedia Siemens Mireo) | ICNG 5-car 198.7 t, 8-car 285.7 t (tare or service not stated) [S]. ETR 104 Pop 4-car 143.5 t [S] (Wikipedia Pop) | > 131,000 lb (59.4 t) per car [S] (NY Post 2023-01-18) |
| Loaded mass | Use tare + 75 kg × (seats + standees at 4/m²) [E] | Same [E] | Same [E] | Same [E] | Same [E] |
| Power | FLIRT 160: max 2,600–3,000 kW **at wheel** [P] (Stadler flirt-160 neutral DE sheet). Type 75: 4,500 kW (or 3,000 kW; column ambiguous) [S] | 7,000 kW per EMU [S] (railway-technology "caltrain electric train cars 2024"). Treat as unverified [E] | Mireo 2-car 1,700 kW; 3-car 2,600 kW [P] (Siemens data sheets) | STA (South Tyrol) set ≈ 3,000 kW continuous at wheel [P] (Alstom press release 2025-05). ICNG 2,545 / 3,390 kW [S] | 2,200 hp (1.64 MW) "per unit", 8 × 275 hp motors [S] (Wikipedia M9) |
| Starting tractive effort | 200 kN [P] (Stadler FLIRT 160 DE sheet; EPFL RABe 521 sheet) | 320 kN for a 6-car 2M4T [S] (trainspo 3739) | — | — | — |
| Adhesion implied | 200 kN on ~4 powered axles × ~17 t ≈ 0.30 [E] | 320 kN on ~8 motored axles ≈ 0.23 [E] | — | — | — |
| Max speed | 160 km/h (FLIRT 160) [P]; 200 km/h (FLIRT 200 / Type 75) [P] | 110 mph design; 79 mph corridor limit [S] (railway-technology, railwayage) | 3-car 160 km/h, 2-car 140 km/h [P]. Desiro HC 160 km/h (Egypt) [P]; 190 km/h (DB Franken-Süd-Thüringen) [P] | 160 km/h [P/S] | 100 mph design, 80 mph service [S] |
| Acceleration | 1.2 m/s² starting [P] (FLIRT 160 sheet). Nordic FLIRT 0.8 m/s² [P] (flirt-200-nordic sheet). Family range 0.8–1.3 m/s² [S] | 1.1 m/s² generic KISS [S] (Wikipedia). Caltrain "≈1 m/s²" [S] (rollingstockworld) | Mireo 3-car up to 1.2 m/s² [P] (newer sheet); older sheet 0.96 m/s² [P]. 2-car 1.1 m/s² [P]. Desiro HC 4-car 1.1, 6-car 0.91 m/s² [S, forum] | IC5 (DK) 1.2 m/s² from 0–70 km/h [S] (Wikipedia IC5) | 2.0 mph/s = 0.89 m/s² [S] (Wikipedia M9) |
| Service braking | — (use 0.9–1.0 m/s² [E]) | — (use 0.9 m/s² [E]) | — (use 0.9–1.0 m/s² [E]) | — | 3.0 mph/s = 1.34 m/s² [S] |
| Emergency braking | — (≈1.2–1.5 m/s² with track brakes [E]) | — | — | — | 3.2 mph/s = 1.43 m/s² [S] |
| Doors per side | 1–2 bi-parting per car; NS = 2 per carbody per side [P] (Stadler flirt_ns_en) | Generic 2 per car side, optionally 4 [P] (Stadler kiss_en). Caltrain cars have lower-level and intermediate-level doors [P] (FRA-2018-0067 attachment) | — | IC5: 5 per side (whole unit) [S] | 2 per side per car [E, typical LIRR M-series] |
| Door width | 1,300 mm [P] (several Stadler FLIRT sheets) | 1,400 mm [P] (Stadler kiss_en) | — | "Wide double-leaf" [S] | ≈ 1,270 mm (50 in) [E] |
| Floor and boarding | Low floor 600–800 mm (NS 780, Nordic 800) [P]. Level boarding when platform matches | Low floor 500 mm generic [P]. Caltrain lower doors at 22 in ATOR with a retractable step at ~16 in, serving 8 in platforms; 25 in level-boarding target [P] (FRA petition; Caltrain LPMG) | Desiro HC ≈ 760–800 mm entrance [E] | — | 48 in high floor, high platforms only [S] |

### 1b. US low-floor DMU / hydrogen FLIRT

| Field | TEXRail FLIRT DMU | SBCTA Arrow FLIRT DMU / ZEMU (FLIRT H2) |
|---|---|---|
| Consist | 81 m, 4 cars plus power pack [S] (news via search) | 2 cars plus power module, 48.5 m [S] (Railway Gazette) or 163 ft [P] (Stadler slide). H2 version 169 ft [P] |
| Mass | 160 t empty, 201 t loaded [S] | — |
| Engines | 2 × 520 kW Deutz, Tier 4 = 1,040 kW engine [S] | Tier 4 diesel [P] (Stadler / SBCTA) |
| Electric drive at rail | ≈ 0.85 × (1,040 − aux) ≈ 820–860 kW [E] | — |
| Max speed | 130 km/h design, 110 km/h in service [S] | 80 mph (DMU) [P] (Stadler slide); H2 130 km/h [P] |
| Seats | 224 [P, Stadler] / 229 [S] | 116 seats + 118–120 standing [P/S] |

### 1c. Locomotives and coaches

| Locomotive | Weight | Power | Starting TE | Implied μ | HEP | Vmax | Sources |
|---|---|---|---|---|---|---|---|
| Siemens Charger SC-44 | 267,000 lb (121.1 t) [P] (Siemens MARC Charger data sheet); 260,000 lb [S] | 4,400 hp (3,281 kW) engine, Cummins QSK95 [P] (Siemens IDOT data sheet). 4 × 729 kW AC motors [S] | 65,000 lbf (290 kN) [P] (IDOT sheet). Continuous 62,000 lbf (275 kN) @16 mph [S] | 290 / (121.1 × 9.81) = 0.244 [E] | 600 kW [P] (IDOT and MARC sheets); 660–1,000 kW [S] | 125 mph [P] | assets.new.siemens.com IDOT/MARC Charger data sheets |
| Bombardier ALP-45DP | 130.6–131 t [S] (Railvolution, Wikipedia) | Electric 4,000 kW continuous / 4,400 kW max **at rail**. Diesel engines 2 × 1,567 kW (3,134 kW). Diesel at rail 2,700 kW without HEP, 2,039 kW with HEP for 8 cars [S] (Wikipedia; Railway Gazette) | 316 kN (71,000 lbf). Continuous 262 kN electric @55 km/h, 291 kN diesel @25 km/h [S] | 316 / (131 × 9.81) = 0.246 [E] | 1,000 kW / 1,100 kVA [S] | 125 mph electric, 100 mph diesel [S] | Wikipedia ALP-45DP; railwaygazette 35323 |
| MPI HSP46 (MBTA) | 287,500 lb (130.4 t) [S]; 290,000 lb nominal [S] (Railway Age) | 4,650 hp (3,470 kW) at alternator. ~3,200 kW (no HEP) to ~2,600 kW (full HEP) at wheel [S] | 65,000 lbf (289 kN) [S] (Railway Age) | 0.226 [E] | 600 kW inverter HEP [S] | 110 mph design, 80 mph service [S] | Wikipedia MPI HSP46; railwayage p=8296 |
| MPI MP36PH-3C | 285,000–295,000 lb (129–134 t) [S] | 3,600 hp (2,685 kW), EMD 645F3B. Separate Cat C27 HEP genset [S] | Listed range 72,500–85,000 lbf [S] (start/continuous not stated) | ≈ 0.25 [E] | ≈ 500 kW (C27 genset) [E, unverified] | 82–102 mph (gearing) [S] | Wikipedia MPI MPXpress |
| EMD F40PH / F40PH-2C / -3C | 260,000 lb (F40PH); 282,000 lb (-2C); 277,000 lb (-3C) [S] (thedieselshop data sheets) | 3,000 hp (-2C) / 3,200 hp (-3C), 16-645E3. HEP taken from the main engine on the base F40PH [S] | 65,000 lbf "at 25% adhesion"; continuous 38,240 lbf @16.1 mph [S] | 0.25 (stated) [S] | 500–800 kW [S/E] | 95–110 mph by gear: 59:15 = 95 mph; 57:20 = 103 mph [S] | thedieselshop.us F40PH pages; Wikipedia EMD F40PH |

Coaches:

- **Bombardier/Alstom MultiLevel coach.** 85 ft (25.9 m) long [S].
  - Weights [S] (Wikipedia Bombardier MultiLevel Coach): trailer 132,490 lb (60.1 t); trailer with toilet 134,380 lb (61.0 t); cab car 139,000 lb (63.0 t); power car (MLV EMU) 181,000 lb.
  - Capacity 127–142 seats [S].
  - Side doors are at the intermediate level and serve both high and low platforms [S]. With traps open at low platforms, passengers climb steps [E].
- **Siemens Venture coach.** 85 ft long, 112,000 lb (50.8 t); whether this is empty is not stated [S] (Wikipedia Siemens Venture).
  - Economy 70 seats [P] (Siemens Venture spec sheet).
  - Brightline sets have 4 coaches [P/S].
- **Bombardier BiLevel coach.** About 50 t empty [S] (Pedestrian Observations train-weights table). Two sets of bi-parting doors per side; intermediate level about 1,300 mm above rail [S].
- **Budd RDC-1.** 109,200–118,300 lb (49.5–53.7 t) [S].
  - Two Detroit Diesel 6-110 engines of 275 hp each (410 kW total), each driving one axle through a hydraulic torque converter [S] (Wikipedia Budd RDC; american-rails).
  - Top speed 85 mph [S].
  - Acceleration: 0–44 mph in 60 s, 0–54 mph in 90 s, 0–80 mph in under 4 min [S] (rapidotrains.com Budd RDC master class). That is about 0.33 m/s² average to 44 mph [E].

### Planning values to fill gaps [E]

- **Loaded mass.** Add 75–80 kg per passenger.
  - Commuter design load ≈ seats + 1.0–1.5 × seats standing.
  - A 4-car EMU of ~120–150 t tare gains about 25–40 t crush.
  - US-built FRA-compliant EMUs and DMUs are heavier: a 4-car is about 180–220 t.
- **Rotating-mass factor ξ.** Train 1.08 for a rough calculation; locomotive 1.09; coaches 1.06 [S] (Wende 2003 p.13, as encoded in TrainRuns.jl `constructors.jl`).
- **Braking for timetable planning.**
  - TrainRuns.jl defaults to −0.375 m/s² for passenger trains (and uses −0.4253 m/s² for a Desiro DMU) [S] (railtoolkit/TrainRuns.jl). These are deliberately conservative.
  - Recommended planning service-brake rates: EMU 0.8–1.0 m/s²; loco-hauled push-pull 0.5–0.7 m/s² [E]. The M9's published 1.34 m/s² is the upper bound [S].
  - The federal rule (49 CFR 238.431) sets no numeric emergency rate, only stopping within signal spacing.

---

## 2. Running resistance (Davis form R = A + B·v + C·v²)

### 2.1 Formula variants

**Original Davis (1926)**, General Electric Review 29:2–24. R is in lb/short ton, w is tons per axle, n is axles per car, V is mph, a is frontal area in ft².

- Freight: R = 1.3 + 29/w + 0.045·V + 0.0005·a·V²/(w·n) [S] (rosap.ntl.bts.gov dot 79083).
- Total-force version: R_lb = 1.3·W + 29·N + b·W·V + C·a·V².
- Coefficients (search extract of the KSU ce435 tutorial; the table was garbled, so the pairing is approximate) [S]:
  - Locomotive: b = 0.03, C = 0.0024, a = 105–120 ft².
  - Passenger car: b = 0.03, C = 0.00034, a = 120 ft².
  - Freight car: b = 0.045, C = 0.0005.

**Modified Davis (AREA, roller bearings):** Ru = 0.6 + 20/w + 0.01·V + K·V²/(w·n) lb/ton. K = 0.07 conventional, 0.0935 container, 0.16 TOFC [S] (USPTO 9875324). Multiplied by car weight, the aerodynamic term is K·V² lb per car. Passenger K is not published in these sources. Use Davis C·a: about 0.29 lb/mph² for a blunt leading unit and about 0.05 lb/mph² per trailing bilevel [E].

**Canadian National (1990):** R = 1.5 + 18·N/W + 0.03·V + C_a·a·V²/(10,000·W) lb/ton. W is total tons, N is axles, C_a is the CN streamlining coefficient [S] (rosap dot 79083; slideserve "module 5 tractive effort"). See AREMA MRE Ch.16 §2.1.3.

**Sauthoff (passenger coaches) and Strahl (locos and freight)**, after Wende, Fahrdynamik des Schienenverkehrs (2003) pp.151–153, as encoded in TrainRuns.jl `formulary.jl` [S]:

- Coaches: F = m·g·[f0 + f1·(v/v00) + f2·((v + Δv)/v00)²]/1000, with v00 = 100 km/h and Δv (headwind allowance) = 15 km/h.
  - Double-deck articulated coaches (DB IC2): f0 = 2.0‰, f1 = 0.715‰, f2 = 3.64‰.
- Traction unit: F = f_Rtd0·m_driving·g + f_Rtc0·m_carrying·g + f_Rt2·m·g·((v + Δv)/v00)².
  - Traxx P160 loco: f0 = 2.5‰; air term 5,000–6,000 N at 100 km/h.
  - Desiro Classic DMU (68 t, 2-car): f0 = 3.0‰ on driving axles, 1.4‰ on carrying axles. Air 2,200 N + 400 N per extra section at 100 km/h.
  - Wende ranges: f_WL0 = 2.5–3.5‰, f_WW0 = 1.2–1.6‰.

**Measured values (Europe):**

- Locomotive-hauled passenger train behind an LE 060 EA locomotive: A = 1,500 N, B = 12 N/(km/h) = 43 N/(m/s), C = 0.3 N/(km/h)² = 3.9 N/(m/s)² [S] (ResearchGate 281028864).
- Swedish full-scale tests (X2, Regina, loco-hauled) are in Lukaszewicz 2007, IMechE F 221(2):183–193, doi 10.1243/0954409JRRT89 [S]. Coefficient tables were not retrievable.
- Coast-down determination method: EN 14067-4.

**Conversions:** C[N/(m/s)²] = C[N/(km/h)²] × 12.96. B[N/(m/s)] = B[N/(km/h)] × 3.6.

### 2.2 Representative SI coefficients (v in m/s, R in N)

All [E], derived from the formulas above. Arithmetic is shown so the values can be re-derived.

**(a) 4-car EMU, 200 t, 16 axles, ~105 m, frontal area ~10 m² (108 ft²)**

| Method | A [N] | B [N/(m/s)] | C [N/(m/s)²] |
|---|---|---|---|
| Modified Davis mechanical + Davis aero (lead 0.0016·108, 3 × 0.00034·108 = 0.283 lb/mph²) | 0.6·220.5 + 20·16 = 452 lb → **2,012** | 0.01·220.5 lb/mph → **21.9** | **6.3** |
| Wende (1.5‰ rolling; air 2,200 + 3·400 N at 100 km/h) | **2,943** | (in f1, ≈ 50) | 3,400 / 771.6 = **4.4**, applied to (v + 4.17)² |
| **Recommended** | **2,500** | **40** | **6.0** |

Checks with the recommended values: 11.4 kN (≈ 400 kW) at 79 mph; 19 kN (≈ 940 kW) at 110 mph.

**(b) SC-44 + 6 MultiLevel-type bilevels (5 trailers + 1 cab car), ≈ 485 t empty, 500 t with load, 28 axles**

| Method | A [N] | B [N/(m/s)] | C [N/(m/s)²] |
|---|---|---|---|
| Modified Davis (W = 551 short tons) | 0.6·551 + 20·28 = 891 lb → **3,962** | 5.51 lb/mph → **54.8** | — |
| Original Davis | 1.3·551 + 29·28 = 1,529 lb → **6,799** | — | lead 0.0024·120 + 6 × 0.00034·150 = 0.594 lb/mph² → **13.2** |
| Wende/Sauthoff (coaches 379 t at 2.0 / 0.715 / 3.64‰; loco 121 t at 2.5‰, 5,500 N air at 100 km/h) | 7,436 + 2,968 = **10,404** | **95.7** | 17.5 + 7.1 = **24.7**, applied to (v + 4.17)² |
| **Recommended** | **6,000** | **80** | **14** |

Check with the recommended values: 26.3 kN at 79 mph, about 930 kW at the rail. This is plausible for a US push-pull cruising at track speed. With a blunt cab car leading, use the same C (cab-car fronts are about as blunt as locomotives).

Notes:

- **Start-up (breakaway) resistance.** Roller bearings: about 5 lb/ton (≈ 25 N/t, ≈ 2.5‰), fading to the running value by about 3–5 mph. Plain journal bearings: 15–25 lb/ton. These are the classic Hay figures, not re-verified [E]. In a timetable simulator this changes start times by under 1 s; it can usually be ignored or added as a constant ≈ 1.5·A below 2 m/s.
- **Bearing and flange terms are already inside A** (the 20 lb/axle in modified Davis vs 29 in the original reflects the move to roller bearings) [S] (rosap dot 79083).
- **Curve resistance:** AREMA ≈ 0.8 lb/ton per degree of curvature [E, standard US value], or Röckl r = 650/(R − 55) N/kN for R ≥ 300 m [E]. Grade: 20 lb/ton per 1% grade (= m·g·i).
- **Tunnels:** C is 1.5–2.5× higher, depending on blockage ratio [E]. Not relevant to surface, at-grade or elevated alignments.

---

## 3. Tractive effort modelling

**Recommended model:** F_T(v) = min( F_start, μ(v)·m_adh·g, η·P/v ).

- **Electric (EMU or electric loco):** P = published power at the wheel (FLIRT 160: 2.6–3.0 MW [P]; ALP-45DP: 4.0 MW continuous / 4.4 MW max at rail [S]), so η = 1 if the value is given "at wheel".
  - If the value is given as motor or converter rating, use η ≈ 0.88–0.92 (transformer + converter + motor + gear) [E].
  - Use the continuous rating for runs longer than about 5 min, the short-time maximum for acceleration [E].
- **Diesel-electric:** P_rail = η_tr·(P_engine − P_aux − P_HEP).
  - η_tr derived from published data: ALP-45DP 2,700 kW at rail / 3,134 kW engine = **0.86** [E from S].
  - HSP46: about 3,200 kW at wheel / 3,470 kW at alternator = 0.92 (alternator to wheel only) [S/E].
  - Forum-level estimates: modern AC 0.90–0.93; older DC (F7) about 0.82; DC rectifier units (SD40-2) about 0.88 [S] (trains.com forums).
  - Recommended η_tr: modern AC 0.85–0.88 from the engine nameplate; legacy DC (F40PH) 0.80–0.83 [E]. P_aux (cooling fans, compressor) ≈ 3–5% of engine power [E].
  - Diesel low-speed limit: use the continuous TE (SC-44: 275 kN at 16 mph; F40PH: 170 kN at 16.1 mph [S]) as an extra current-limit cap.
- **HEP deduction (locomotive-hauled):**
  - Rated HEP: SC-44 600 kW [P]; HSP46 600 kW [S]; ALP-45DP 1,000 kW [S]. On the ALP-45DP in diesel mode, 8-car HEP costs about 660 kW at the rail (2,700 → 2,039 kW) [S].
  - Actual load is about 8 kW per car average for lights and AC [S] (NAP 22083 ch.12, citing Frey & Graver 2012). Amtrak allocates up to 85 kW per car, 1,200 kW per train trainline limit [S] (utahrails Amtrak HEP).
  - Simulator default for commuter bilevels: 30–50 kW per car in summer, so 6 cars ≈ 200–300 kW [E].
  - For an SC-44 + 6: P_rail ≈ 0.86 × (3,281 − 130 − 250) ≈ 2,500 kW [E].
- **Adhesion:**
  - Curtius–Kniffler (dry rail, v in km/h): μ = 0.161 + 7.5/(v + 44). This gives 0.33 at standstill, 0.24 at 50 km/h and 0.21 at 100 km/h [E, formula from standard German traction texts; the 0.33 standstill value matches the TU Dresden slides citing Bendel 1994].
  - Published starting TE of US locomotives implies μ ≈ 0.23–0.25 (SC-44 0.244, ALP-45DP 0.246, HSP46 0.226, F40PH 0.25) [E from P/S].
  - Modern EMU with slip control: about 0.30 on dry rail at start (FLIRT 200 kN on ~68 t adhesive mass) [E].
  - **Planning recommendation [E]:**
    - Locomotives: μ_start = 0.25 (dry) or 0.18 (wet).
    - EMUs: 0.30 (dry) or 0.20 (wet).
    - Taper both with Curtius–Kniffler shape: μ(v) = μ0·(0.161 + 7.5/(v + 44))/0.331.
    - The 0.25–0.35 range in the brief is optimistic for wet or leafy days.
  - For EMUs, m_adh = powered-axle mass only. FLIRT 4-car ≈ 2 powered bogies (≈ 35% of mass); KISS 6-car ≈ 8 of 24 axles motored [S/E].
- **Jerk limit for passenger comfort:** about 0.5–1.0 m/s³ [E]. Adds about 1–2 s per stop.

---

## 4. US speed regulation (49 CFR Part 213 and Part 236)

**Track classes (49 CFR 213.9) [P]** (law.cornell.edu/cfr/text/49/213.9; text as amended 85 FR 63388, 2020):

| Class | Passenger mph | Freight mph |
|---|---|---|
| Excepted | not allowed | 10 |
| 1 | 15 | 10 |
| 2 | 30 | 25 |
| 3 | 60 | 40 |
| 4 | 80 | 60 |
| 5 | 90 | 80 |

**Classes 6–9 (213.307) [P]:** 110 / 125 / 160 / 220 mph. Speeds above 125 mph need separate FRA approval. Class 9 was 200 mph in older editions.

**Signal and train-control thresholds (49 CFR 236.0) [P]** (law.cornell.edu/cfr/text/49/236.0):

- At 60 mph or more, passenger trains need a block signal system or PTC.
- At 80 mph or more, they need PTC, or cab signals / ATS / ATC with FRA approval.
- In practice this gives a 59 mph cap on dark territory and a 79 mph cap without cab signals or ATC. Most US commuter lines are capped at 79 mph.

**Curve speed (213.57(b); same formula in 213.329(b) for Class 6+) [P]:**

- V_max = sqrt( (Ea + Eu) / (0.0007·D) ), with V in mph.
  - Ea = actual elevation in inches, averaged over each 155 ft of curve body using 11 points at 15.5 ft.
  - Eu = qualified cant deficiency in inches.
  - D = degree of curvature (chord definition, 100 ft chord). D = 2·asin(50/R_ft) ≈ 5729.58/R_ft.
- **SI equivalent [E]:** V[km/h] = sqrt( (Ea + Eu)[mm]·R[m] / 11.99 ). FRA's 0.0007 implies 60 in (1,524 mm) between rail centres; UIC uses 1,500 mm, giving the divisor 11.8. Verified numerically.
- **Lateral acceleration [E]:** a_lat = (Eu/60)·g. Eu 3 in = 0.49 m/s²; 4 in = 0.65; 5 in = 0.82; 6 in = 0.98; 7 in = 1.14; 9 in = 1.47 m/s².

**Cant deficiency limits [P]** (213.57(c); 213.345 via search extract):

- All vehicles are qualified for **Eu ≤ 3 in**. Most US commuter equipment runs at 3 in [E].
- Above 3 in requires FRA approval of the vehicle type. Above **5 in** requires §213.345 vehicle/track qualification testing. Above **6 in** (or Class 7+) also requires wheel/rail force measurement on the route.
- Actual cant deficiency may exceed the qualified Eu by **1 in** on Class 1–5 track and **0.5 in** on Class 6+.
- Practical values: modern non-tilt EMUs and coaches are typically qualified for 5–6 in [E]. Tilting Acela (original) ran up to about 7 in [E, from memory; verify]. Tilt raises Eu by roughly 3–4 in more [E].

**Maximum elevation [P]:**

- Classes 1–2: 8 in.
- Classes 3–5: 7 in (213.57(a)).
- Class 6+: 7 in (213.329).
- Mixed freight lines typically use Ea ≤ 4–5 in [E] because slow freight would otherwise run with excess cant.

**Speed vs radius table (mph)** [E], computed from the FRA formula with D from chord geometry:

| R (m) | D (°) | Ea+Eu = 3 in | 6 in | 10 in (7+3) | 12 in (7+5) | 13 in (7+6) |
|---|---|---|---|---|---|---|
| 150 | 11.66 | 19 | 27 | 35 | 38 | 40 |
| 200 | 8.74 | 22 | 31 | 40 | 44 | 46 |
| 300 | 5.82 | 27 | 38 | 50 | 54 | 56 |
| 400 | 4.37 | 31 | 44 | 57 | 63 | 65 |
| 500 | 3.49 | 35 | 50 | 64 | 70 | 73 |
| 600 | 2.91 | 38 | 54 | 70 | 77 | 80 |
| 800 | 2.18 | 44 | 63 | 81 | 89 | 92 |
| 1000 | 1.75 | 50 | 70 | 90 | 99 | 103 |
| 1500 | 1.16 | 61 | 86 | 111 | 121 | 126 |
| 2000 | 0.87 | 70 | 99 | 128 | 140 | 146 |

Turnouts: No. 10 ≈ 20–25 mph, No. 15 ≈ 30–35 mph, No. 20 ≈ 40–45 mph, No. 24 ≈ 50 mph, No. 32/33 ≈ 60–80 mph [E, standard AREMA practice; not re-verified this session].

---

## 5. Dwell times

**Measured and published figures:**

- **Caltrain** (bilevel Bombardier and gallery cars, low platforms with steps, 5,149 stops): median wheel-stop to wheel-start **49 s**, mean **58 s** [S] (caltrain-hsr.blogspot.com 2016-05, reporting a Caltrain dwell study).
  - Two-step Bombardier cars: about 55 s per station; level boarding was estimated to save at least 15 s [S] (Streetsblog SF 2013-11-08).
  - Advocacy modelling assumes about 30 s with level boarding, roughly one-third less for the same passenger volume [S].
  - "Bikes First" pilot: one Mountain View dwell fell from 2 min 16 s to about 1 min 4 s [S] (KQED).
- **Platform-height effects (FRA platform-gap study; MATEC 2016):** the vertical gap strongly affects dwell for passengers with luggage or reduced mobility. Two adjacent vestibules at a mini-high double accessible boarding capacity [S].
- **Low-level platform car designs:** a design suited to low platforms saves 2–5% of trip time at station spacing of 1.25–5 mi [S] (worldtransitresearch 679).
- **Mixed high/low platforms** (Morlok 2002): long dwells, larger crews, ADA problems. SEPTA's trap-door operation was cited as the reason for building all-high platforms [S] (worldtransitresearch 850; Progressive Railroading 10726).
- **Boarding mix (Harris et al., via literature review):** boarding and alighting take 40.8 s with balanced flow, 41.9 s alighting-dominated, 49.6 s boarding-dominated [S] (tandfonline 10.1080/01441647.2021.1887960).
- **SBB / ETH dwell model:** five sub-processes (door unlock, door open, passenger exchange, door close, dispatch), from more than 3 million measurements [S] (WIT CR08051). Per-process values not retrieved.
- **Door cycle:** 2.5–4.5 s per door pair; dispatch 3–8 s [S, low reliability] (railwaynews.net wiki). Metro door-close assumptions run up to 14 s [S] (Springer s40864-020-00128-1).
- **TransitMatters regional-rail EMU assumption for MBTA:** 45 s dwell, 0.667 m/s² acceleration, 0.888 m/s² braking, 129 km/h max [P, model input] (transitmatters/regional-rail-schedule-generator `scenarios/regional_rail/trainset.py`).

**Recommended dwell model [E]:**

t_dwell = t_unlock/open + max over doors of (n_alight·t_a + n_board·t_b) + t_close + t_dispatch

| Component | Level boarding, EMU | Low platform, steps or traps |
|---|---|---|
| Unlock and open | 2–3 s | 3–5 s, plus the conductor dropping traps at manual doors |
| Per-passenger time per door channel, t_a / t_b | 1.0 / 1.2 s | 2.0 / 2.5 s; wheelchair via mini-high 60–120 s |
| Close and lock | 3–5 s | 5–8 s |
| Dispatch (conductor "all aboard", buzzer or radio signal to the engineer, reaction) | 3–5 s (driver-only or CCTV) | 8–15 s |

**Defaults by station type [E]:**

| Station | Level-boarding EMU | Low-level / mini-high, loco-hauled |
|---|---|---|
| Minor | 20–30 s | 40–60 s |
| Medium | 30–45 s | 60–90 s |
| Major / terminal-adjacent (Back Bay class) | 45–90 s | 90–180 s |

Off-peak flag stops are about 15–20 s if nobody boards. The Caltrain 49 s median is a good calibration point for the low-platform loco-hauled case.

---

## 6. Schedule padding

**UIC 451-1 (4th ed., 2000)**, "Timetable recovery margins to guarantee timekeeping". The official table is paywalled; scope via the Scribd summary and GlobalSpec listing.

- Margins depend on train type, maximum speed and hauled mass, with a percentage part and a distance part [S].
- Confirmed table points [S] (Schienen-Control Kommission decision SCK-22-018, citing UIC 451-1): **4% at Vmax 160 km/h and 393 t; 6% at 230 km/h and 393 t**.
- Commonly reproduced structure [E, reconstructed; verify against the leaflet, e.g. TU Wien Vial 2016 thesis, Fig. 1.9]:
  - ≤ 140 km/h: 3% (light) to 4% (heavy hauled loads).
  - 141–160 km/h: 4%.
  - 161–200 km/h: 5%.
  - 201–250 km/h: 6%.
  - 251–300 km/h: 7%.
  - Plus a distance term of about **1.0 min/100 km for multiple units** and **1.5 min/100 km for loco-hauled trains**.
- DB's Regelzuschlag matches: 3–7% by speed and traction, plus at least 1.0 min/100 km for MUs and 1.5 min/100 km for loco-hauled trains [S] (de.wikipedia Regelzuschlag). DB adds a separate Bauzuschlag in absolute minutes for engineering work.

**Typical totals:**

- Europe 3–7%; North America 6–8% [S] (Pachl 2002, cited in Springer s11116-019-10057-z).
- Switzerland, Netherlands, Sweden about 7% [S] (Pedestrian Observations 2025-08-29; nec.transitcosts.com/scheduling).
- MTA says Metro-North averages about 10%. Pedestrian Observations estimates 20–30% on the NEC (Amtrak and Metro-North) [S, advocacy].
- Amtrak places most recovery time before the endpoint [S] (FRA OTP Report to Congress 2008-07).
- NJ Transit: about 10 min per run, at least half of it in the last segment [S, forum].

**Network Rail Timetable Planning Rules allowances** [S] (wiki.openraildata.com/Allowances; NASEM 29463):

- **Engineering allowance** ("box time" [ ]): covers temporary speed restrictions from engineering work, usually spread over a route section.
- **Pathing allowance** ("circle time" ( )): time inserted so a train fits its planned path past a conflict (junction, a slower train ahead, a single-line section). It is not recovery time and is often recovered when the conflict is absent.
- **Performance allowance** ("diamond time"): a buffer for day-to-day lateness at key timing points.
- **Adjustment allowance:** unrecoverable running time, such as approach to a diverging junction (2024 TPR lists four types).
- Values are per route and set by simulation or measurement; there are no universal minutes.

**Recommended for the simulator [E]:**

- Compute the technical minimum running time, then add:
  - 5% (EMU) or 7% (loco-hauled) distributed over the run, plus 1.0 / 1.5 min per 100 km.
  - A 1–3 min endpoint recovery for US-style schedules.
  - Explicit pathing time at single-track meets, equal to the scheduled wait.
- Report both "pure" and "padded" times.
- Rounding to whole minutes per segment (as in GTFS) adds about 0.5 min per timepoint on average.

---

## 7. MBTA Needham Line calibration data

**Primary data:** MBTA GTFS, Fall 2025 version D (feed_info 20250909–20251213), copied in github.com/transitmatters/regional-rail-schedule-generator `data/gtfs-present/` [P] (`stops.txt`, `facilities.txt`, `shapes.txt` and `stop_times.txt` were read directly).

**Mileposts from stop IDs [E, inferred].** MBTA stop IDs encode the milepost in tenths of a mile:

- NEC series (from New York): NEC-2287 South Station = 228.7.
- NB series (from South Station): NB-0137 Needham Heights = 13.7 mi, which matches the 13.7 mi line length [S] (Wikipedia Needham Line).

### (a) Stations, in order, with along-track distances

Coordinates are GTFS commuter-rail platform stops, i.e. platform points [P]. Chainage is measured along GTFS shape 9860002 (outbound), with the stop snapped to the shape [E]; snap offsets are 3–45 m. Total shape length is 21,905 m (13.61 mi).

| # | Station | GTFS platform stop | Lat | Lon | Chainage from SS (m) | Segment (m) | Platform [P] (GTFS facilities.txt) |
|---|---|---|---|---|---|---|---|
| 1 | South Station | NEC-2287 (tracks 1–13) | 42.351410 | -71.055417 | 27 | — | Full high-level (all tracks) |
| 2 | Back Bay | NEC-2276-01/-03 | 42.347350 | -71.075727 | 2,170 | 2,143 | Full high-level, tracks 1/2/3 |
| 3 | Ruggles | NEC-2265-01/-03 | 42.336608 | -71.089208 | 3,803 | 1,633 | Full high-level, tracks 1/2/3 |
| 4 | Forest Hills | NEC-2237-03 (outbound) / -05 (inbound) | 42.301085 | -71.113551 | 8,229 | 4,425 | Full high-level, tracks 3 and 5. Amtrak-style 1,050 ft, 12-car platforms [S] |
| 5 | Roslindale Village | NB-0064-S | 42.287442 | -71.130283 | 10,350 | 2,121 | Low-level + mini-high |
| 6 | Bellevue | NB-0072-S | 42.286588 | -71.145557 | 11,606 | 1,257 | Low-level + mini-high |
| 7 | Highland | NB-0076-S | 42.284969 | -71.153937 | 12,348 | 742 | Low-level + mini-high |
| 8 | West Roxbury | NB-0080-S | 42.281358 | -71.160065 | 12,982 | 634 | Low-level + mini-high |
| 9 | Hersey | NB-0109-S | 42.275648 | -71.215528 | 17,679 | 4,697 | Low-level + mini-high |
| 10 | Needham Junction | NB-0120-S | 42.273187 | -71.235559 | 19,369 | 1,691 | Low-level + mini-high |
| 11 | Needham Center | NB-0127-S | 42.280775 | -71.237686 | 20,522 | 1,152 | Low-level + mini-high |
| 12 | Needham Heights | NB-0137-S | 42.293444 | -71.236027 | 21,905 | 1,383 | Low-level + mini-high |

- Every Needham Branch station has a single platform: GTFS lists only "Track 1 (All Trains)", and Wikipedia describes one side platform on a single track [P/S].
- The line is fully accessible [S] (Wikipedia MBTA accessibility).
- Wikipedia coordinates agree to within about 20–200 m (for example Forest Hills 42.30069, -71.114) [S].

### (b) Rolling stock

The line is diesel push-pull out of South Station. GTFS lists no electrification, and the branch is unelectrified [S] (OSM way 795409167).

**Locomotives:**

- **MPI HSP46** (40 units, 2000–2039) [S]. Specs in §1. 130.4 t; 4,650 hp; 600 kW HEP; 65,000 lbf starting TE; 80 mph service limit.
- **MPI F40PH-3C** (rebuilt from F40PH-2C from 2017) [S]. 3,200 hp, 277,000 lb (125.6 t), 64 ft 3 in.
- **MP36PH-3C:** only 2 units, ex-Utah (UTA) [S, forum]. Rare on this line.

**Coaches:** the MBTA bilevel fleet (≈ 300 cars) [S] (Wikipedia MBTA bilevel cars):

- Kawasaki BTC-4/4A/4B/4C and CTC-4, built 1990–2006, rebuilt 2014–21.
- Hyundai Rotem BTC-4D and CTC-5, built 2012–2027.
- All 85 ft 4 in (26.0 m) long, 10 ft wide, capacity 173–185.
- A 2025 photo shows an all-bilevel Needham train at Hersey with a CTC-5 cab car leading [S].
- Single-level BTC-1C (Pullman-Standard 1970s, rebuilt 1996, 114 seats) also appear in the fleet [S].
- No published per-car weight was found. Estimates [E]:
  - Bilevel trailer ≈ 55–62 t (same class as MultiLevel 60.1 t and BiLevel ≈ 50 t).
  - Cab car about +2–3 t.
  - Single-level BTC-1C ≈ 50 t.

**Typical consist [E]:** 1 locomotive + 5–7 coaches. South Station routes are said to run six-car bilevel sets [S, unofficial]. Suggested model consist: HSP46 + 6 bilevels ≈ 130 + 6 × 60 = **490 t empty, about 520 t loaded**, length about 22 + 6 × 26 = 178 m.

### (c) Track, speeds and geometry

**Corridor and track layout:**

- **South Station – Forest Hills** is Amtrak's Northeast Corridor through the Southwest Corridor: 3 tracks; a third track to Readville since 1873–74 [S].
- At Forest Hills, Needham trains leave the NEC.
  - Inbound trains use track 5, the single Needham Branch track east of the station, which merges into NEC track 3 north of the station [S] (Wikipedia Forest Hills station).
  - GTFS confirms the pattern: outbound trains stop on FH track 3, Ruggles track 1 and Back Bay track 1; inbound trains use FH track 5, Ruggles track 3 and Back Bay track 3 [P].
- **Needham Branch:** single track with a single platform at every station [P/S].
  - The 1906 Needham Cutoff (West Roxbury – Needham Junction) was built double track and single-tracked in the late 1920s. It is single track across Cutler Park and the Charles River crossing [S] (railpictures 407729; universalhub; blog.bimajority.org 2021-03-15).
  - Needham Junction – Needham Heights is the former Charles River Railroad, always single track [S].
  - No current passing-siding location was found in public sources.
  - **Schedule evidence of meets [P/E]:** on weekdays, West Roxbury → Hersey is 5 min on 7–8 trips, 6 min on 3 trips and **10 min on 6–7 trips** in each direction, versus 5 min on all weekend trips. The 10-min entries are scheduled waits for opposing trains (pathing time), so a meet point or passing track lies on the West Roxbury – Needham Junction cutoff [E].

**Speed limits:**

- **Published speeds found are scarce:**
  - Back Bay curve: 30 mph on all three tracks at the time of the 1990 collision (historical) [S] (Wikipedia 1990 Back Bay collision).
  - Pedestrian Observations (2011) gives 70 km/h (≈ 43 mph) through the 90° curve approaching Back Bay and 100 km/h (≈ 62 mph) south of it [S].
  - Temporary 10 mph restriction at Forest Hills in October 2024 (Orange Line work) [S] (Boston Globe 2024-10-17).
  - System maximum on MBTA Commuter Rail: 79 mph [S].
  - OSM tags one Needham Branch way at maxspeed 15 mph; this is probably a local segment [S] (osm.org/way/795409167).
  - No authoritative Needham Branch timetable speed was found; MBTA/Keolis track charts or employee timetable would be needed.
- **Curvature from the GTFS shape** [E]. Radius is fitted over a 300 m chord, so it is accurate to roughly ±20% and can understate tight curves. V uses the FRA formula with Ea = 3 in and Eu = 3 in, then Ea = 4 in and Eu = 3 in.

| Location (chainage from SS) | Min R | D | V (Ea 3, Eu 3) | V (Ea 4, Eu 3) |
|---|---|---|---|---|
| South Station throat (0.5–0.9 km) | ≈ 200 m | 8.8° | 31 mph | 34 mph |
| Back Bay curve (2.0–2.3 km) | ≈ 260 m | 6.7° | 36 mph | 39 mph |
| Southwest Corridor near Ruggles (5.4 km) | ≈ 880 m | — | 66 mph | 71 mph |
| Forest Hills junction curve off the NEC (8.4–8.55 km) | ≈ 360 m | 4.8° | 42 mph | 46 mph |
| Roslindale curves (≈ 10–10.6 km) | ≈ 720 m | — | 60 mph | 64 mph |
| Bellevue – West Roxbury (11.8–12.9 km) | ≈ 890–1,000 m | — | 66–70 mph | — |
| Curve onto the cutoff just past West Roxbury (13.15–13.5 km) | ≈ 355 m | 4.9° | 42 mph | 45 mph |
| Needham Junction (19.5–19.85 km), the wye onto the old Charles River RR | ≈ 145 m | 12° | 26–27 mph | 29 mph |

- Turnout speed at the Forest Hills junction is not published; a No. 15 crossover would give about 30–35 mph [E]. The 360 m curve governs anyway.
- **Suggested simulator speed profile [E, calibrate against the 40-min weekend schedule]:**
  - SS throat 30 mph to ~0.9 km.
  - 40 mph through Back Bay.
  - 60–70 mph Back Bay – Forest Hills (NEC commuter MAS; set 60 if calibration runs fast).
  - 40 mph at the Forest Hills junction.
  - 50–60 mph Forest Hills – West Roxbury.
  - 40 mph on the West Roxbury curve.
  - 50–60 mph on the cutoff to Needham Junction.
  - 25 mph at the Needham Junction curve.
  - 30–40 mph Needham Junction – Needham Heights (grade crossings).
- **Grade crossings:**
  - The cutoff (West Roxbury – Needham Junction) is grade-separated, with rock cuts up to 57 ft at Great Plain Ave [S] (Wikipedia Needham Line).
  - The old Charles River RR section in Needham (Needham Junction – Needham Center – Needham Heights) has at-grade crossings [S] (blog.bimajority.org; amateurplanner 2019).
  - Keolis lists Hersey, Needham Center and Roslindale Village among the top 20 most problematic stations with at-grade crossings [S] (mass.gov Appendix B – MBTA).
  - A temporary speed restriction at a Needham crossing delayed train 608 by 5–15 min [S] (MBTA_CR on X).
  - For the street-by-street list, use the FRA Crossing Inventory.

**Schedule (GTFS Fall 2025) [P]:**

- Weekend: 40 min in both directions.
- Weekday: 46–48 min for full trips; 26–27 min for Forest Hills short-turns (11 stops); all-stop pattern.
- Segment minutes (weekend outbound, SS → NH): 5, 3, 5, 3, 3, 2, 2, 5, 3, 4, 5.
- Weekend inbound matches the coordinator's list (4, 4, 3, 5, 2, 2, 3, 3, 5, 4, 5).
- GTFS arrival equals departure at intermediate stops, so dwell is embedded in segment minutes.
- TransitMatters' current-service model of the same line uses SS 0:00 → NH 0:45, with Hersey at 0:33 (it includes the 10-min cutoff segment) [P, model] (scenarios/regional_rail/needham.py).

**Implied average speeds [E]:** Hersey – West Roxbury 4,697 m in 5 min = 56 km/h (35 mph) including stop and start. Back Bay – South Station 2,143 m in 5 min. Both are consistent with modest line speeds (≈ 50–60 mph peak on the branch) plus about 45–60 s dwells at low platforms.

**Platform types and dwell (d):**

- Full high-level at SS, BB, RUG and FH: all doors usable; assume 45–60 s at Back Bay and Ruggles in the peak, 30–45 s at Forest Hills [E].
- Low-level with mini-high at the other 8 stations: conductors open traps at selected doors, and wheelchair users board at the mini-high, which positions the train. Assume 30–45 s off-peak and 45–75 s peak, the Caltrain-like low-platform case [E].

---

### Key source URLs

- **Regulations:**
  - https://www.law.cornell.edu/cfr/text/49/213.57
  - https://www.law.cornell.edu/cfr/text/49/213.9
  - https://www.law.cornell.edu/cfr/text/49/213.307
  - https://www.law.cornell.edu/cfr/text/49/213.329
  - https://www.law.cornell.edu/cfr/text/49/213.345
  - https://www.law.cornell.edu/cfr/text/49/236.0
- **Stadler:**
  - https://www.stadlerrail.com/api/docs/x/dda445987e/flirt-160_neutral_en.pdf
  - https://www.stadlerrail.com/api/docs/x/3293b22f9c/flirt-160_neutral_de.pdf
  - https://stadlerrail.com/api/docs/x/3297d4f3aa/kiss_en.pdf
  - https://stadlerrail.com/api/docs/x/3145dc2e7e/flirt_ns_en.pdf
  - https://stadlerrail.com/api/docs/x/fd4e7b7bbc/flirt-200-nordic_norske-tog-sa.pdf
- **Siemens:**
  - https://assets.new.siemens.com/siemens/assets/api/uuid:d8c9c389-a0bf-4c7f-b8fc-c9b5fa8f8ca8/IDOT-Charger-Data-Sheet_original.pdf
  - https://assets.new.siemens.com/siemens/assets/api/uuid:6036a8f7-ce96-43d1-bf97-76cac10c66b0/MARC-Charger-Data-Sheet_original.pdf
  - https://assets.new.siemens.com/siemens/assets/api/uuid:3a02c155-f27e-4d59-8bcd-2413bbfbcc50/siemens-mobility-mireo-smart-data-sheet.pdf
  - https://assets.new.siemens.com/siemens/assets/api/uuid:74b8dc90-22a8-416a-8043-d98d4fc2ad36/siemens-mobility-desiro-hc-egypt-data-sheet.pdf
- **Caltrain FRA waiver:** https://downloads.regulations.gov/FRA-2018-0067-0009/attachment_1.pdf
- **Wikipedia (secondary):**
  - https://en.wikipedia.org/wiki/M9_(railcar)
  - https://en.wikipedia.org/wiki/Bombardier_ALP-45DP
  - https://en.wikipedia.org/wiki/MPI_HSP46
  - https://en.wikipedia.org/wiki/MPI_MPXpress
  - https://en.wikipedia.org/wiki/Bombardier_MultiLevel_Coach
  - https://en.wikipedia.org/wiki/Siemens_Venture
  - https://en.wikipedia.org/wiki/Budd_Rail_Diesel_Car
- **F40PH:** https://www.thedieselshop.us/Data%20EMD%20F40PH.HTML
- **Resistance:**
  - https://rosap.ntl.bts.gov/view/dot/79083/dot_79083_DS1.pdf
  - https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9875324
  - https://github.com/railtoolkit/TrainRuns.jl (src/formulary.jl, test/data/trains/*.yaml)
  - https://doi.org/10.1243/0954409JRRT89
- **HEP:** https://nap.nationalacademies.org/read/22083/chapter/12 ; https://utahrails.net/pass/amtrak-hep.html
- **Dwell:**
  - https://caltrain-hsr.blogspot.com/2016/05/caltrain-has-dwell-time-problem.html
  - https://sf.streetsblog.org/2013/11/08/caltrain-wants-level-boarding-but-big-hurdles-remain
  - https://www.tandfonline.com/doi/full/10.1080/01441647.2021.1887960
  - https://www.witpress.com/Secure/elibrary/papers/CR08/CR08051FU1.pdf
- **Padding:**
  - https://www.schienencontrol.gv.at/files/1-Homepage-Schienen-Control/1b-Wettbewerbsregulierung/Veroeffentlichungen/Zuweisung%20Zugtrasse%20mit%20Halt%20in%20V%C3%B6cklabruck.pdf
  - https://de.wikipedia.org/wiki/Regelzuschlag
  - https://pedestrianobservations.com/2025/08/29/timetable-padding-practices/
  - https://wiki.openraildata.com/index.php/Allowances
  - https://railroads.dot.gov/sites/fra.dot.gov/files/fra_net/2658/OTP_Report_to_Congress_2008_07.pdf
- **MBTA:**
  - https://github.com/transitmatters/regional-rail-schedule-generator (data/gtfs-present: MBTA GTFS Fall 2025 v.D)
  - https://en.wikipedia.org/wiki/Needham_Line
  - https://en.wikipedia.org/wiki/Forest_Hills_station_(MBTA)
  - https://en.wikipedia.org/wiki/MBTA_bilevel_cars
  - https://blog.bimajority.org/2021/03/15/weekend-excursion-stations-of-the-needham-line/
  - https://www.bostonglobe.com/2024/10/17/metro/needham-commuter-rail-line-delays-orange-line/
  - https://pedestrianobservations.com/2011/08/19/mbta-hsr-compatibility/
