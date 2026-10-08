# Metro (heavy rail) parameters for a travel-time simulator: research notes

Compiled 2026-10-08.

## How the sources were reached (read this first)

- **WebFetch did not work for any domain in this session.** Every call returned `getaddrinfo ENOTFOUND`, even for example.com. The egress proxy also returned 403 for Wikipedia, mbta.com, TRB, FTA, Kawasaki, Siemens and others.
- Every web number below therefore comes from **WebSearch result extracts** of the cited pages, not from my own reading of each page. Where a value appeared only on a fan wiki, a game-mod page or a forum, I say so.
- **MBTA GTFS was the exception: I downloaded and parsed it.** It came from the MobilityData mirror on Google Cloud Storage: `https://storage.googleapis.com/storage/v1/b/mdb-latest/o/us-massachusetts-massachusetts-bay-transportation-authority-mbta-gtfs-437.zip?alt=media`.
  - Feed: "Summer 2026, 2026-06-03, version D", valid 2026-05-27 to 2026-09-05.
  - Extracted Orange Line stop_times are in `scratchpad/scripts/ol_stop_times.csv`, and the analysis output is in `scratchpad/scripts/ol_an.out`.
  - Section 4 is **published data processed by me**.
- Labels used throughout:
  - **[P]** published value (the agency, manufacturer or standard states it).
  - **[P-2]** published, but only seen through a secondary source such as a Wikipedia infobox or a press article.
  - **[F]** fan, forum or game source; low confidence.
  - **[E]** my own estimate or calculation.
- Unit conversions: 1 mphps = 0.447 m/s², 1 mph = 0.447 m/s, 1 lb = 0.4536 kg.

---

## 1. Rolling stock

### 1a. MBTA Orange Line, CRRC MA "#14" cars (1400–1551), 2018+

**Primary source: MBTA VE-10-036, "Red / Orange Line New Vehicle Technical Specification", 22 Oct 2013.** URL: https://bc.mbta.com/business_center/bidding_solicitations/pdf/MBTA%20RO%20Technical%20Specification%20October%2022%202013.pdf. The proxy blocked the file, so these values come from search extracts of it.

| Field | Value | Status / source |
|---|---|---|
| Acceleration | **2.75 mphps ±5% (1.23 m/s²)**, constant after a jerk-limited start, up to a **tractive-effort base ("knee") speed of at least 16.3 mph (7.3 m/s)**. Required for 4- and 6-car trains at car weights from **AW0 to at least AW2**. | [P] VE-10-036 |
| Service braking | Full-service dynamic brake gives **3.0 mphps ±5% (1.34 m/s²)** from 42 mph down to 3 mph on level tangent track. | [P] VE-10-036 |
| Emergency braking | Not retrieved; the spec has a section, but the extract cut off. **Assume 3.0–3.2 mphps (1.34–1.43 m/s²)** by analogy with US practice (NYC R46/R160/R211 are 3.2 mphps). | [E] |
| Jerk limit | The spec has section 2.02.04 "Jerk Limits" and defines jerk in mphpsps. The value was not retrieved. Typical US heavy-rail specs use about 2 mphpsps (0.9 m/s³). | value [E] |
| Max speed | In-service operation **up to 63 mph**; designed and qualified to **70 mph**. | [P] VE-10-036 |
| Speed actually used | 40 mph systemwide cap until 2025; **55 mph Oak Grove–Assembly since 24 Aug 2025**. See section 4. | [P-2] |
| Max vehicle weight | **110,000 lb (49.9 t) Orange; 125,000 lb Red.** Load condition not visible in the extract; probably AW3. | [P] VE-10-036 |
| Line-current limit | **1,060 A for the Orange Line**, probably per car. At 600 V that is ≈ 636 kW electrical input per car, which caps traction power. | [P] VE-10-036; kW [E] |
| Doors | Spec extract: Red = 4 doors per side per car; the Orange text appeared to say **3 per side**. | [P] partial |
| Door width | "64 inches wide, 16 inches wider than existing Orange Line doors" (WGBH, MBTA mockup tour). An MBTA official also cited a "72-inch clear opening"; that may be a different measurement. | [P-2] https://www.wgbh.org/news/local/2019-08-14/mbta-rolls-out-new-orange-line-trains |
| Car length | ≈ **19.8 m (65 ft)** over couplers, width ≈ 2.82 m (9 ft 3 in). | [F] Steam Workshop mod, https://steamcommunity.com/sharedfiles/filedetails/?id=3358990258; consistent with the 65 ft legacy cars |
| Empty mass AW0 | **≈ 34–37 t (75–82 k lb).** CBS reported an "80,000 pound shell"; MBTA said the new cars are heavier than the 1979–81 Hawker cars. | [E] from https://www.cbsnews.com/boston/news/springfield-factory-mbta-new-train-cars and https://www.nbcboston.com/investigations/the-mbtas-new-orange-line-trains-derailed-six-times-what-went-wrong/2336846/ |
| AW3 | ≤ 49.9 t (spec cap) | [P]/[E] |
| Typical consist | **6 cars**, ≈ 119 m. Built as married pairs. | [P-2] Wikipedia Orange Line infobox, via search |
| Motored axles | All axles motored (4 per car), AC induction motors | [E]; typical for CRRC MA; not verified |
| Implied power | At the knee, 6 cars × ~44 t (AW2) × 1.23 m/s² × 7.3 m/s ≈ **2.4 MW at the wheel (≈ 400 kW per car)**. Under the 1,060 A cap, about 500–550 kW electrical per car. | [E] |

Trip-time sensitivity: past the 16.3 mph knee, acceleration falls roughly as P/(m·v), to about 0.5 m/s² at 40 mph. The 55 mph sections are therefore reached slowly.

### 1b. MBTA Red Line, CRRC MA "#4" cars (1900 series)

- Length **69 ft 9.75 in (21.3 m)**, width 10 ft. [F] Dovetail forum, https://forums.dovetailgames.com/threads/mbta-red-line-alewife-to-ashmont-braintree.58024/
- **4 doors per side** [P]. Max weight **125,000 lb** [P]. Same performance clauses as Orange in VE-10-036: 2.75 mphps, 3.0 mphps full-service dynamic brake, 63 mph in service / 70 mph design [P].
- 600 V DC third rail, with ATO and cab signalling on the Red Line. [P] MBTA system description, https://www.mass.gov/doc/appendix-b-mbta-system-description/download
- Typical consist 6 cars (≈ 128 m) [E].
- Red Line Braintree branch raised to **50 mph on 14 Mar 2025**, the first time in 20+ years that any MBTA subway line ran above 40 mph. [P-2] https://www.wbur.org/news/2025/03/14/mbta-red-line-50-mph-braintree-phil-eng

### 1c. BART "Fleet of the Future" (Bombardier/Alstom D and E cars)

- Car ≈ **70 ft (21.3 m)** long, 10 ft 6 in high, **≈ 65,000 lb (29.5 t)** per car (load not stated). [P-2] NBC Bay Area, https://www.nbcbayarea.com/news/local/fleet-of-the-future-bart-unveils-new-train-car/74286
  - The D car is 65,500–67,500 lb empty. [F] BARTCHIVES, https://bartcars.weebly.com/d-cars.html
  - Cars came in 0.5–1 ton heavier than the contract. [P-2] https://www.nbcbayarea.com/news/local/new-cars-in-barts-fleet-of-future-found-to-be-overweight/42214/
- **Max speed 80 mph** (BART FAQ). [P] https://bart.gov/node/12394
- **3 doors per side**. [P-2]
- D car: 4 motors × 148 hp (110 kW), so ≈ 440 kW per car. Dynamic/regenerative braking to 3 mph, plus friction brakes. [F] BARTCHIVES
- Braking: BART says 80 mph to 0 takes "about 20 to 25 s" depending on brake system. That implies **3.2–4.0 mphps (1.4–1.8 m/s²)**. [P] https://www.bart.gov/news/articles/2019/news20190408; rate [E]
- Acceleration: legacy BART spec 3.0 mphps (1.34 m/s²). No published Fleet of the Future number was found. [P-2] legacy
- Train length up to 10 cars (≈ 213 m) [P-2].

### 1d. NYC R211 (Kawasaki), B Division

- Length **60.21 ft (18.35 m)**; **82,000 lb (37.2 t)** per car. [P-2] Wikipedia infobox via search, https://en.wikipedia.org/wiki/R211_(New_York_City_Subway_car)
- Acceleration **2.5 mphps (1.12 m/s²)**. Braking **3.0 mphps (1.34 m/s²) full service**, **3.2 mphps (1.43 m/s²) emergency**. [P-2]
- Max speed **55 mph in service**, 66 mph design. [P-2]
- **8 doors per car (4 per side), 58 in (1.47 m) wide**, which Kawasaki says is 8 in wider than older cars. [P] https://global.kawasaki.com/en/corp/newsroom/news/detail/?f=20230306_7827
- Motors: 2 or 4 × Alstom 4 ECA 1625 A AC induction per car. Power not found; R160 analogue is 110–120 kW per motor. [P-2]
- Typical consist **10 cars (≈ 184 m)**, or 8 cars on some lines. [E]

### 1e. WMATA 7000 series (Kawasaki)

All from the Kawasaki Technical Review spec table [P], https://global.kawasaki.com/en/corp/rd/magazine/177/pdf/n177en03.pdf, unless noted:

- Dimensions **23 m × 3.1 m × 3.3 m**, 75 ft. Formed as married pairs; 4–8 cars on the main line.
- Max speed **120 km/h (75 mph)**.
- Acceleration **4.5 (+0.3/−0) km/h/s = 1.25 m/s² (2.8 mphps)**.
- Normal deceleration **4.8 ±0.3 km/h/s = 1.33 m/s²**; emergency **5.1 km/h/s = 1.42 m/s²**.
- Motors: Toshiba SEA-430, 140 kW AC induction × 4 per car, so **1,120 kW per pair (560 kW per car)**. [P-2] Wikipedia
- Mass ≈ 84,289 lb (38.2 t) per car, load unspecified. [F] metro-trains-database.fandom.com
- Typical consist 6 or 8 cars (137 m / 183 m). Systemwide 6-car 7000-series trains since March 2024. [P-2]

### 1f. RATP MP14 (Alstom). Note: rubber-tyred, not steel-wheel

- Car **15.04 m**, width 2.45 m. Trains of 5, 6 or 8 cars = 75 / 90 / 120 m.
- **3 double doors per side per car.**
- Max acceleration **4.86 km/h/s = 1.35 m/s²**.
- Design speed 100 km/h, commercial 80 km/h.
- Capacity 562 passengers (5 cars) / 932 (8 cars).
- Power figures conflict: 2,900 kW or 3,200 kW per 8-car train.
- Mass not found.
- Source for all of the above: [P-2] fr.wikipedia and metropolitor.fr via search, https://fr.wikipedia.org/wiki/MP_NG and https://metropolitor.fr/materiel/MP+14+CA

Rubber tyres give higher adhesion (about 7% grades are possible), so **do not use the MP14's acceleration and grade ability for a steel-wheel model.**

### 1g. Generic modern steel-wheel metro references

**Siemens Inspiro, Warsaw, 6-car** [P] Siemens datasheet, https://assets.new.siemens.com/siemens/assets/api/uuid:68efc7133287d03bf86a2acc6a3637d9b540ffad/metro-warsaw-en.pdf

- Formation Mc-T-M-M-T-Mc, so 2/3 of axles are motored.
- Length ≈ **117.8 m** (end cars 20.1 m, intermediate cars 19.4 m); width 2.74 m.
- **Tare ≈ 163 t; ≈ 265 t at 7 passengers/m²**; max axle load 12.6 t.
- Max speed 90 km/h. 750 V DC. Capacity 1,502.
- Electrodynamic braking to standstill.
- Acceleration not found. The Škoda Varsovia on the same metro gives **1.2 m/s² acceleration, 1.3 m/s² service and 1.4 m/s² emergency braking**, 160.4 t, 119 m. [P] https://www.skodagroup.com/reference/metro-varsovia

**Sydney Metro (Alstom Metropolis)** [P-2] EPD via search, https://api.environdec.com/api/v1/EPDLibrary/Files/32a46be5-fc8c-47cc-1b8a-08da2ccce1bd/Data

- **1.2 m/s² acceleration (0–40 km/h), 1.1 m/s² service, 1.4 m/s² emergency.**

**Siemens, Bangkok MRT Blue Line, 3-car** [P] https://assets.new.siemens.com/siemens/assets/api/uuid:2ccdeacd-74e2-4c26-8d83-c702ec7b23aa/Data_Sheet_Metro_MRTA.pdf

- 65.1 m; **tare 107 t / 175 t at 8 passengers/m²**.
- **Starting acceleration 1.3 m/s²**; mean service braking 0.9 m/s².
- 80 km/h. 750 V third rail.

### Summary table for simulator defaults (steel wheel, 6 cars, ~120–140 m)

| Parameter | Recommended default | Range seen |
|---|---|---|
| Starting acceleration (AW0–AW2) | 1.23 m/s² (2.75 mphps, MBTA spec) | 1.1–1.35 |
| Knee speed | 7.3 m/s (16.3 mph, MBTA spec minimum); 30–40 km/h for European stock | 7–11 m/s |
| Above knee | Constant power, P = m·a0·v_knee | — |
| Service braking (planning rate) | 1.34 m/s² max (spec). Use **1.0–1.1 m/s²** as the typical driver/ATO planning rate. | 0.9–1.34 |
| Emergency braking | 1.4 m/s² | 1.33–1.43 |
| Jerk | 0.7–1.0 m/s³ (see section 5) | 0.5–1.5 |
| Mass | 36 t/car AW0, +8 t/car at AW2 | — |
| Rotating-mass factor | 1.08–1.10 [E] (standard EMU practice) | — |

---

## 2. Davis running resistance (R = A + B·v + C·v², N with v in m/s)

**What was found:**

- **Rochard & Schmid (2000)**, "A review of methods to measure and calculate train resistances", Proc IMechE F 214:185–199. https://journals.sagepub.com/doi/10.1243/0954409001531306
  - Secondary extracts quote a suburban-EMU form **F = 1.839·√M + 0.0036·M·v + 4.329·v²**. Units were not shown; most likely kN-free N with M in t and v in m/s.
  - With M = 240 t: A ≈ 28 N (implausibly small, so the units are suspect), B·v at 20 m/s ≈ 17 N, C ≈ 4.3 N/(m/s)². [P-2]; **unverified units, use with care.**
  - The paper says curve resistance can be neglected for radius > 250 m. [P-2]
- **Armstrong & Swift (British Rail EMUs)**: A = 6.4·m_trailer + 8.0·m_motor. Units are N with m in t, so roughly 6–8 N/t. B and C expressions were not retrieved. Rochard & Schmid say these expressions are not valid when powered axles predominate. [P-2] https://www.imeko.org/publications/wc-2012/IMEKO-WC-2012-TC3-P20.pdf
- **Chinese urban-rail basic resistance**: w = 2.755 + 0.014·v + 0.00075·v² N/kN (v in km/h) is often quoted. **I could not confirm it with a search.** It is treated as [E/unverified] and is high: about 10 N/kN at 90 km/h, which likely includes tunnel effects.

**Recommended per-train formula [E]**

Derived from the original Davis (1926) EMU formula: 1.3 + 29/w + 0.03·V + 0.0024·A·V² for the lead car, with 0.00034 for trailing cars. Assumptions: 6 cars, 4 axles each, frontal area 10 m².

| Load | A (N) | B (N per m/s) | C (N per (m/s)²) | R at 40 mph | R at 55 mph |
|---|---|---|---|---|---|
| 36 t/car (216 t) | 4,470 (20.7 N/t) | 71 | 9.9 | 8.9 kN | 12.2 kN |
| 40 t/car (240 t) | 4,630 (19.3 N/t) | 79 | 9.9 | 9.2 kN | 12.5 kN |
| 44 t/car (264 t) | 4,780 | 87 | 9.9 | 9.5 kN | 12.9 kN |

- **Use A = 19 N/t × M, B = 0.33 N/(m/s) per tonne × M, C = 9–10 N/(m/s)² open air.**
- Modern roller-bearing stock is often 20–40% lower in A. A reasonable band is **A = 12–20 N/t**.
- Sanity check: 9–12 kN on 240 t is ≈ 0.4–0.5% equivalent grade, which is consistent with typical metro coast-down data.

**Tunnel factor (multiplier on the aerodynamic C term)**

- EN 14067-3 defines the tunnel factor as tunnel drag divided by open-air drag (≥ 1). It depends mainly on blockage ratio B. [P] https://iteh.es/catalog/standards/sist/3b5db9af-1223-49f5-9901-445496516671/sist-en-14067-3-2004
- Gaillard's correlation for friction drag is 1 + 2.21·B. At B = 0.5 it gives **≈ 2.1**. [P-2] https://journals.sagepub.com/doi/pdf/10.1243/PIME_PROC_1996_210_325_02
- A metro CFD thesis found ≈ 3.65× open-air drag at high blockage. [P-2] https://etd.aau.edu.et/items/a2173866-c143-4ed6-bf91-ebbb4e7b2cd3
- Norwegian tunnel measurements: an added v² coefficient of 2.4–16 kg/m (that is, N per (m/s)²) for cross-sections of 87–27 m². [P-2] https://www.sciencedirect.com/science/article/pii/S2210970616300415
- **Recommendation [E]:**

| Tunnel type | Multiply C by |
|---|---|
| Single-track metro tunnel, B ≈ 0.4–0.5 (e.g., Boston Washington St tunnel) | ≈ 2.0 (range 1.5–2.5) |
| Twin-track box | 1.3–1.5 |
| Open / elevated | 1.0 |

At 40 mph this adds only ≈ 3 kN, so its effect on run time is small (a few seconds per station pair).

---

## 3. Door cycle and dwell modelling

**TCQSM structure (2nd and 3rd editions)**

Dwell = door opening + passenger flow time + door-open time after flow ends + door closing + "waiting to depart" after doors close.

- Flow time is 38–64% of observed dwell. [P] TCQSM 2nd ed., TCRP Report 100 Part 5, https://onlinepubs.trb.org/onlinepubs/tcrp/docs/tcrp100/Part5.pdf
- 3rd ed. (TCRP Report 165) per-passenger, per-door service times for HRT/LRT/BRT with a level interface [P-2] ITDP BRT guide citing TCQSM 3rd ed. p. 8-25, https://brtguide.itdp.org/branch/master/guide/why-brt/performance:
  - **Alighting 1.39–2.0 s**
  - **Boarding 1.11–2.61 s**
  - With steps: 3.4–4.2 s.
- Door open + close term: **2–5 s** [P-2]. TCRP Report 13: "a typical rail rapid transit car door will cycle in 5 s." [P] https://onlinepubs.trb.org/onlinepubs/tcrp/tcrp_rpt_13-c.pdf
- TCQSM headway worked examples: **45 s critical-station dwell + 20 s operating margin**. [P]

**MBTA-specific model**

Puong (2000), MIT memo, "Dwell Time Model and Analysis for the MBTA Red Line" [P-2], quoted in https://engineering.purdue.edu/~ce560/HW/Bus_Dwell_Time_jdf.pdf:

**D = 12.22 + 2.27·B_d + 1.82·A_d + 6.2×10⁻⁴·TS_d³·B_d** (seconds)

- B_d and A_d are boardings and alightings per door.
- TS_d is through-standees per door.
- The 12.22 s intercept is effectively the door cycle plus fixed overhead.

**Door timings**

- London Underground door chime: **1.75 ±0.25 s**. [P] https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/739939/supporting-evidence-1_victoria-line-door-trial-report.pdf
- A typical full door cycle is about 5 s.
- **Recommended [E]:**
  - Opening 2.5 s (after a 1–2 s release delay at stop).
  - Closing including warning 3.5–5 s.
  - Departure delay after doors are proven closed (interlock, brake release, cab-signal pickup, operator reaction): **2–4 s with ATO, 3–6 s manual**.

**Observed dwells**

| System | Observation | Source |
|---|---|---|
| MBTA North Station (Orange) | **63 s before platform markings, 42 s after** | [P-2] Boston Globe 2017, https://www.bostonglobe.com/metro/2017/06/26/simple-way-make-boston-subway-bit-less-chaotic/YIhFwsWmyVRhQggegacZ4I/story.html |
| NYCT | Design target ≈ 30 s; MTA aims for under 45 s; over 60 s at busy stations | [P-2] https://www.6sqft.com/the-subway-system-cant-handle-nycs-growing-popularity/ |
| SF Muni Metro subway | ≈ 20 s ±5 s | [P] https://www.sfmta.com/en/node/26262 |
| London Victoria Line | 24 s best in the central section, 30–40 s typical | [F] |

**Platform screen doors**

- **+4 to 15 s per stop** across 33 CoMET/Nova metros; the main cause is the departure check after both door sets close. [P] https://www.worldtransitresearch.info/research/7234
- Stockholm City Line simulation: ≈ +12 s per stop. [P-2]

**Recommended dwell defaults [E]**

| Station type | Dwell (doors-open to departure) |
|---|---|
| Minor | 20–25 s |
| Average | 30 s |
| Busy CBD / transfer (Downtown Crossing, State, North Station) | 40–60 s |
| Terminal | Layover; not modelled as dwell |

---

## 4. MBTA Orange Line calibration data (from MBTA GTFS, Summer 2026 v.D)

### Stations, southbound order

Coordinates are GTFS parent stations (place-*). Distances are along the GTFS shape (903_0026), using southbound platform stop points projected onto it.

| # | Station | lat | lon | Distance to next (m) | Chainage (m) |
|---|---|---|---|---|---|
| 1 | Oak Grove | 42.43668 | -71.071097 | 1183* | 0 |
| 2 | Malden Center | 42.426632 | -71.07411 | 2824 | 1183 |
| 3 | Wellington | 42.40237 | -71.077082 | 1020 | 4007 |
| 4 | Assembly | 42.392811 | -71.077257 | 930 | 5027 |
| 5 | Sullivan Square | 42.383975 | -71.076994 | 1397 | 5957 |
| 6 | Community College | 42.373622 | -71.069533 | 1216 | 7354 |
| 7 | North Station | 42.365577 | -71.06129 | 301 | 8570 |
| 8 | Haymarket | 42.363021 | -71.05829 | 462 | 8871 |
| 9 | State | 42.358978 | -71.057598 | 453 | 9333 |
| 10 | Downtown Crossing | 42.355518 | -71.060225 | 396 | 9786 |
| 11 | Chinatown | 42.352547 | -71.062752 | 348 | 10182 |
| 12 | Tufts Medical Center | 42.349662 | -71.063917 | 1079 | 10530 |
| 13 | Back Bay | 42.34735 | -71.075727 | 1002 | 11609 |
| 14 | Massachusetts Avenue | 42.341512 | -71.083423 | 669 | 12611 |
| 15 | Ruggles | 42.336377 | -71.088961 | 835 | 13280 |
| 16 | Roxbury Crossing | 42.331397 | -71.095451 | 886 | 14115 |
| 17 | Jackson Square | 42.323132 | -71.099592 | 776 | 15001 |
| 18 | Stony Brook | 42.317062 | -71.104248 | 866 | 15777 |
| 19 | Green Street | 42.310525 | -71.107414 | 1110 | 16643 |
| 20 | Forest Hills | 42.300713 | -71.113943 | — | 17753 |

- Line length along the shape: **17.75 km (11.0 mi)** [P-derived].
- *The Oak Grove platform stop (42.437735, -71.070875) lies about 80 m beyond the shape start. The straight-line Oak Grove–Malden Center distance is 1,263 m, so treat the first segment as 1,183–1,263 m.
- Northbound distances match to ±2 m.

### Scheduled times

- GTFS subway times are **whole minutes**, so single-segment values are quantized. Use sums or means.
- Arrival equals departure in the feed, so each segment time already includes dwell.

**End-to-end scheduled time** (2,146 trips per direction in the feed):

| Direction | Mean | Range | By time of day |
|---|---|---|---|
| Southbound, Oak Grove → Forest Hills | **32.6 min** | 32–33 min | AM peak 32.5, midday 33.0, PM peak 32.9, evening 32.1 |
| Northbound, Forest Hills → Oak Grove | **33.5 min** | 32–35 min | AM 33.1, midday 33.8, PM peak 34.3, evening 33.2 |

**Mean scheduled segment times (s), all-day:**

- Southbound, in station order from Oak Grove: 60, 180, 120, 120, 120, 120, 60, 120, 60, 60, 60, 120, 120, 60, 120, 115, 120, 98, 120.
- Northbound, in station order from Forest Hills: 60, 120, 120, 120, 82, 77, 120, 120, 60, 60, 109, 60, 64, 120, 120, 120, 120, 180, 180.

Oak Grove → Wellington southbound is 4.0 min for 4.0 km. Northbound, Wellington → Oak Grove is 6 min, which includes the terminal approach.

**Flat-track minimum run time [E]** (`scratchpad/scripts/flat_run.py`)

Assumptions: MBTA spec physics (2.75 mphps to 16.3 mph, then constant power; 3.0 mphps braking; Davis 240 t), no grades or curves, zero dwell, 55 mph Oak Grove–Assembly and 40 mph elsewhere.

- Result: **20.6 min** southbound (21.4 min at 40 mph everywhere).
- The schedule (32.6 min) is therefore about 12 min above pure flat running across 18 intermediate stops. Roughly:
  - 18 × 30 s = 9 min of dwell;
  - ≈ 3 min of curves, grades, sub-maximum braking, signal code steps and padding.
- **A realistic model should land at 31–33 min.**
- Per-segment flat minimums (s), southbound: 72, 139, 65, 67, 94, 83, 32, 41, 41, 38, 35, 76, 71, 53, 62, 65, 59, 64, 77.

### Speeds and civil limits

**Line maximum speed**

- **40 mph systemwide** for about 20 years until 2025. [P-2] https://www.wbur.org/news/2025/01/23/mbta-speed-increase
- **55 mph Oak Grove–Assembly since 24 Aug 2025**, up from 40. That segment was designed for 55 mph. [P] MBTA release via https://www.masstransitmag.com/rail/vehicles/press-release/55312934/massachusetts-bay-transportation-authority-mbta-mbtas-orange-line-trains-reach-55-mph and https://mass.streetsblog.org/2025/08/25/t-begins-running-faster-orange-line-service-in-medford-and-malden
- Oak Grove → Assembly takes ≈ **6 min** including stops (TransitMatters data). [P-2] Boston Globe, 25 Aug 2025
- The August 2026 shutdown (20–30 Aug) work is intended to allow **55 mph Assembly–Community College**. As of these sources it is not confirmed in service. [P-2] https://boston.com/news/transportation/2026/08/16/the-orange-line-is-about-to-shut-down-for-11-days-heres-what-to-know

**Tufts curve (Tufts Medical Center–Back Bay area)**

- 10 mph in 2019, then 18 mph from 2022, then full design speed after repairs in July 2023.
- Poftak's 2022 letter: "a majority of this section has a line speed of 18 mph due to a downslope." Model about **18–25 mph in the Chinatown–Tufts–Back Bay curve and downgrade**. [P] https://www.markey.senate.gov/download/mbta-general-manager-poftak_-letter-to-senator-markey?download=1 and https://mass.streetsblog.org/2023/07/18/t-declares-victory-over-notorious-tufts-curve-slow-zone-on-the-orange-line

**Slow zones**

- All Orange Line slow zones cleared in Nov 2024, the first time in 15 years. [P-2] https://www.boston.com/news/transportation/2024/11/04/mbta-orange-line-without-slow-zones-first-time-15-years

**Signalling**

- Fixed-block ATC with cab signals (audio-frequency coded track circuits).
- Being replaced with Alstom digital audio-frequency track circuits, which allow more intermediate speed commands. The $295 M Red/Orange program is still ongoing in 2025. [P-2] https://www.wbur.org/news/2025/10/03/mbta-signal-system-red-orange-line-updates-boston
- Speed codes are not officially published. A hobbyist teardown of an MBTA cab-signal display (Red Line) shows LEDs at **0, 10, 18, 20, 25, 40, 50, 55, 60 mph**. [F] https://tris.fyi/blog/mbta-cab-signaling-indicator.html
- **Use code speeds 0 / 10 / 18 / 25 / 40 / 50 / 55 mph** [E].
- The Orange Line is driven manually under cab-signal ATP. Red Line cars have ATO. [P-2] MBTA system description

**Observed end-to-end times**

| Period | Time |
|---|---|
| April 2023 median Forest Hills → Oak Grove | **51 min** (13 mph) |
| Late 2023 | 43–45 min |
| Post-slow-zone expectation | "under 40 min" (Streetsblog); TransitMatters' 2022 estimate ≈ 38 min |
| Schedule (2026) | 32.6–33.5 min |

Sources: [P-2] https://www.wgbh.org/news/local/2024-11-08/transit-advocates-state-officials-celebrate-orange-line-getting-back-to-full-speed and https://mass.streetsblog.org/2024/11/02/the-orange-line-is-running-at-full-speed-for-the-first-time-in-15-years

Expect real 2025–26 medians around 33–37 min; this is not verified. The TransitMatters dashboard is the place to check, but it was unreachable here.

---

## 5. Operating practice

**Schedule recovery and padding** (TCRP RRD 122, 2026, "Operating Margin and Recovery Factor Practices") [P] https://www.nationalacademies.org/read/29463

| Practice | Allowance |
|---|---|
| Hansen & Pachl, European railways | 3–7% of pure running time |
| Hansen & Pachl, North American passenger trains | 6–8% |
| SEPTA | ≈ 10% added to trip times |
| NYCT | Schedules to the 50th-percentile observed running time, rounded to 30 s |
| LA Metro | 1–2 min recovery at the end of line |
| WMATA | 3 min typical layover |

- **Recommendation [E]:** add 5–8% to simulated pure run plus dwell, or calibrate directly to GTFS.
- The MBTA Orange Line schedule appears to carry roughly 1–2 min of slack (estimated from section 4).

**ATO vs manual [E]** (from general practice; no primary source retrieved)

- ATO tracks the speed profile closely, usually 1–3 mph under the code, brakes on a fixed planning rate (often 0.9–1.1 m/s², below full service) and gives consistent stops.
- Manual drivers are more variable: they may run closer to the limit, but they brake earlier with a final low-rate "creep-in" and take longer to react on departure.
- ATO coasting is a timetable-slack energy-saving tool. In-service effect is a few percent more run time.
- **Model ATO** as v_target = v_code − 2 mph, braking at 1.0 m/s² with a 2 s jerk-limited onset.
- **Model manual operation** as v_target = v_code − 0 to 3 mph, braking at 0.9–1.2 m/s², plus about a 10 s final approach at 3–5 mph at stops.

**Jerk**

- EN 13452-1 (local transit): **service-brake jerk ≤ 1.5 m/s³**. [P-2] cited in a US patent, https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9580052
- TSI maximum brake jerk is < 4 m/s³. Typical service levels: acceleration 0.3–1.3 m/s², service braking 0.7–1.5 m/s². [P-2] https://konferencje-k53.pwr.edu.pl/event/1/papers/17/files/30-PS_2023_MO_eng1.docx
- **Recommendation [E]:** comfort jerk **0.7–1.0 m/s³**, with 0.5 m/s³ for premium comfort and ≤ 1.5 m/s³ as the hard limit.

---

## 6. Steep-grade and historic-car analogues (for the fictional Cincinnati Metro fleet)

### 6a. MBTA Blue Line Siemens "No. 5" / 0700 series (2007–09)

- **≈ 48 ft (14.6 m)** long, **9 ft 3 in (2.82 m)** wide.
- **2 doors per side** (4 per car).
- Max speed **55 mph**. [F/P-2] https://metro-trains-database.fandom.com/wiki/700_Series_(Boston_T)
- Siemens SITRAC IGBT-VVVF with 3-phase AC induction motors.
- Dual 600 V supply: third rail west of Airport, overhead east of it. [P-2]
- 94 cars in 47 pairs. Siemens contract value $172 M. [P] https://www.railwaygazette.com/news/mbta-fleet-renewal/31039.article
- Typical consist 6 cars ≈ 88 m [E].
- Mass, acceleration and braking were **not found**. Estimates [E]:
  - AW0 **≈ 27–30 t** (scaled from 36 t for a 65 ft car).
  - Acceleration 2.5–3.0 mphps; service 3.0 mphps; emergency 3.2 mphps.
  - All axles motored.
- The Blue Line has grades **above 4%** (Wikipedia list of steepest adhesion gradients, via search). [P-2] https://en.wikipedia.org/wiki/List_of_steepest_gradients_on_adhesion_railways

### 6b. NYC IRT Lo-V / Hi-V and the Steinway cars

| Car | Length | Motor-car mass | Motors | Max speed | Source |
|---|---|---|---|---|---|
| Standard Lo-V (1916–25) | 51 ft 6 in (15.7 m), 8 ft 10 in wide | **77,700 lb (35.2 t)**; trailer 56,000 lb | WH 577 at 200 hp or GE 260 at 195 hp (≈ 2 per motor car) | **60 mph** | [P-2] https://en.wikipedia.org/wiki/Standard_Lo-V_(New_York_City_Subway_car) |
| Gibbs Hi-V (1904–05) | 51 ft 1.5 in | 89,450 lb | GE 69 / WH 86 at 200 hp | 55 mph | [P-2] |
| Deck Roof Hi-V (1907–08) | — | 83,780 lb | GE 212 at 200 hp | 55 mph | [P-2] |
| Steinway Lo-V (1915–25, plus conversions) | Lo-V body | **≈ 74,000 lb (33.6 t)**, lighter than a standard Lo-V | See below | — | [P] NY Transit Museum, https://www.nytransitmuseum.org/meet-the-lovs/ |

Steinway Lo-V details:

- 138 cars, **all motor cars**, run as all-motor trains with no trailers.
- Built with "trucks having a special lower gear ratio to overcome the steep grade in the Steinway Tunnels" (**4.5%**). [P-2] https://www.nycsubway.org/wiki/The_Interborough_Fleet,_1900-1939_(Composites,_Hi-V,_Low-V)
- Conventional IRT motor+trailer trains could not climb the grade. In 1929 the IRT converted 8 Flivver and 22 Standard Lo-V trailers to Steinway motors. [P-2]
- The Wikipedia infobox lists WH 302 / GE 240C motors at 105–120 hp per motor. This conflicts with the 200 hp standard-car motors; unresolved.
- The actual gear-tooth ratio and balancing speed were **not found**. The museum's "higher gear ratio" wording conflicts with nycsubway.org's "lower gear ratio". Both mean more motor revolutions per wheel revolution, i.e. a numerically higher reduction.

**Physics of the gearing trade [E]**

- Tractive effort at the wheel scales with the gear reduction ratio. Top speed (motor rpm limit) and balancing speed scale inversely.
- A 15% higher reduction gives about 15% more starting tractive effort, about 13% lower top speed, and lower motor current on the grade.
- All-motor trains roughly double motored axles compared with an M-T consist, so adhesion-limited tractive effort rises about 2× on top of the gearing gain.
- Example balancing speed on 4.5%: an all-motor 33.6 t car needs F ≈ m·g·0.045 + R ≈ 14.8 kN + 0.6 kN ≈ 15.4 kN per car. If the motors give 2 × 120 hp = 179 kW continuous at the wheel, v_bal ≈ 179/15.4 ≈ 11.6 m/s ≈ **26 mph**. With 2 × 200 hp it is about 43 mph if gearing allows. The ~26 mph figure illustrates the order of magnitude; it is not a documented value.

### 6c. NYC 75 ft vs 60 ft B-Division cars, and Eastern Division curves

**R46** [P-2] https://en.wikipedia.org/wiki/R46_(New_York_City_Subway_car)

- **74 ft 8.5 in (22.77 m)**; it is a 75 ft car, not 60 ft.
- A car 91,000 lb, B car 86,670 lb.
- Acceleration 2.5 mphps; service 3.0 mphps; emergency 3.2 mphps.
- 55 mph. 8 doors per car (4 per side), 50 in wide.
- Trains of 8 cars = 600 ft.

**R160** [P-2] https://en.wikipedia.org/wiki/R160_(New_York_City_Subway_car)

- **60 ft 2.5 in (18.35 m)**; 85,200 lb (38.6 t).
- 4 × AC motors per car: Alstom 110 kW or Siemens 120 kW, so **440–480 kW per car, all axles motored**.
- Acceleration 2.5 mphps; service 3.0 mphps (one mirror says 2.5); emergency 3.2 mphps.
- 55 mph. 625 V DC third rail.

**R211**: see section 1d.

**Eastern Division (J/Z/L/M) ban on 75 ft cars** (R44, R46, R68, R68A)

- The ban is due to tight curves and clearance. Problem spots: Williamsburg Bridge approach, Myrtle–Broadway, Crescent St. [P-2] https://forgotten-ny.com/2018/01/r-46-subway-cars/ and https://en.wikipedia.org/wiki/BMT_Jamaica_Line
- Curve radii (2008 NYC DCP Broadway Junction study, cited via Wikipedia):
  - **175 ft (53 m)**: Broadway Jct–Alabama Ave.
  - **175/190 ft**: west of Marcy Ave.
  - **175/180 ft**: east of Crescent St.
  - **210/200 ft**: west of Cypress Hills.
- B Division system minimum radius is **147.5 ft (45 m)**. [P-2]
- No official "minimum radius for 75 ft cars" was found.
- [E] Geometry for 75 ft cars (truck centres about 54 ft): mid-car swing-in on a 175 ft radius is ≈ 2.1 ft (L²/8R), versus about 1.2 ft for 60 ft cars (truck centres about 41 ft). End throw-out is similar, so the binding constraint is clearance on curved platforms and structures.
- **Model: ban 75 ft cars below about 200 ft (61 m) radius; allow 60 ft cars to about 147 ft (45 m).**

### 6d. Magnetic track brakes (Magnetschienenbremse) and steep-grade braking

- Track brakes act independently of wheel-rail adhesion and are always applied unmodulated at full force, so they are used only for emergency or safety braking. [P-2] https://en.wikipedia.org/wiki/Track_brake
- **EN 16207** (secondary summary): minimum magnetic attraction typically **40–80 kN per brake unit**, magnet-rail dynamic friction coefficient ≥ 0.25. Friction falls with speed, so it is higher near a stop. [P-2/F] https://railwaynews.net/en-16207-railway-applications-braking-functional-and-performance-criteria-of-magnetic-track-brake-systems-for-use-in-railway-rolling-stock-standard.html
- **Contribution [E]:** each magnet gives F = μ·N ≈ 0.1–0.25 × 40–80 kN = 4–20 kN.
  - For a 40 t vehicle with 4 magnets, that is **+0.4 to 2.0 m/s²**.
  - Typical design gives about +0.5–1.0 m/s² on top of the about 1.3–1.5 m/s² adhesion-based emergency rate.
- **BOStrab §36(6) / Anlage 2 Table 2** (German street-running trams and Stadtbahn): emergency braking must reach mean deceleration of **2.73 m/s² at 70 km/h** (braking distance ≈ 69 m), for an empty vehicle on level, dry track. One brake must be adhesion-independent. [P-2] https://lxgesetze.de/bostrab/36
- Vehicle examples:
  - Stuttgart Stadtbahnwagen B emergency ≈ **2.7 m/s²** [P-2].
  - Hannover TW 6000 emergency **3.0 m/s²** with track magnets on all 4 bogies [F] https://stadtbahn.fandom.com/de/wiki/Stadtbahnwagen_TW_6000
  - These compare with about 1.4 m/s² for heavy metro without track brakes. Heavy metros (MBTA, NYCT, WMATA) do not normally fit track brakes.
- **Grade effect:** a grade of G adds or subtracts g·G of deceleration. At 5% that is ±0.49 m/s²; at 8.5% it is ±0.83 m/s².
  - Example: on a 5% downgrade, a 1.4 m/s² emergency rate shrinks to an effective 0.9 m/s², and the stopping distance from 50 mph grows from 179 m to ≈ 278 m.
  - Track brakes (+0.7 m/s²) roughly restore the level-track figure. [E]

### 6e. Maximum grades of steel-wheel urban rail

| System | Max grade | Status / source |
|---|---|---|
| Lisbon tram 28 | 13.5–13.8% (Guinness: 1 in 7.2) | [P] |
| Pittsburgh LRT, Brown Line / Beechview | ≈ 10% (another list: 9.1% Allentown) | [P-2] https://en.wikipedia.org/wiki/Brown_Line_(Pittsburgh) |
| SF Muni J-Church, Dolores Park ROW | **9%** | [P-2] https://en.wikipedia.org/wiki/J_Church |
| Portland Streetcar, SW Harrison | 8.75% | [P-2] |
| Stuttgart Stadtbahn (SSB) | up to **8.6%** | [P-2] http://www.tautonline.com/safety-in-stuttgart/ |
| London DLR (light metro) | 6% | [P-2] |
| Heavy metro: Boston and Philadelphia | up to 5% between stations; Boston Blue Line > 4% | [P-2] |
| Heavy metro: WMATA tunnels | 4% | [P-2] |
| Heavy metro: Singapore, Kolkata | 3% | [P-2] |
| Steinway Tunnel (NYC 7) | 4.5% | [P] |
| Typical design criteria | 3.5% normal, 4% limiting; 0.2% max at platforms | [P] JICA, https://openjicareport.jica.go.jp/pdf/11781036_02.pdf |
| Heavy-rail passenger "consolidated" limit | 5% (with MU control and slip control) | [P-2] |

Rubber-tyred metros (Paris, Montréal, Lausanne M2) reach about 7–12% and are excluded.

### 6f. Traction design for sustained 5% [E]

- **Adhesion needed:** μ_req = (a/g + G + r) / f_motored, where f_motored is the fraction of weight on driven axles and r ≈ 0.004.
  - Holding speed on 5% with all axles driven: μ ≈ 0.054.
  - Accelerating at 1.0 m/s² on 5%, all axles driven: μ ≈ 0.16. That is fine on dry rail (0.25–0.35) and marginal on wet or leafy rail (0.08–0.15).
  - With 2/3 of axles motored (Inspiro-style): μ ≈ 0.24, which is not feasible on wet rail.
  - **So all-axle drive is needed for 5%** (consistent with "the only constraint is that all wheels have to be motored", https://www.railforthevalley.com/latest-news/zweisystem/can-trams-climb-steep-grades/).
- **Braking downhill on 5% (adhesion):** 1.34 m/s² needs μ ≈ 0.19 on all axles. This is why steep LRT and Stadtbahn systems fit magnetic track brakes and sanders.
- **Power:** P_wheel = m·g·(G + r)·v.
  - A 6-car, 240 t train on 5% at 40 mph (17.9 m/s) needs **≈ 2.3 MW at the wheel (≈ 390 kW per car)**.
  - That is about the full continuous rating of R160/7000-class equipment (440–560 kW per car). Balancing speed at the continuous rating is therefore about 40–50 mph, and short-time ratings allow acceleration.
- **Recommendations:**
  - Size continuous power at ≥ 9–10 kW/t for 5% lines; typical flat-line metros are 6–8 kW/t.
  - Use all-axle drive.
  - Cap acceleration on the grade with an adhesion limit of μ ≈ 0.15 (wet design case).
  - Reduce planning brake rate downhill by g·G unless track brakes are fitted.
