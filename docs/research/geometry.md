# Track geometry & alignment design values for a travel-time simulator (Cincinnati metro + commuter/RER)

Research date 2026-10-08. **Method caveat:** WebFetch failed with DNS errors on every host (nap.edu, trb.org, metro.net, wikipedia, …) this session, and so did curl (blocked by the proxy). I could only check values against the excerpts that WebSearch returned. Each value has one of these tags:

- **[PUB]**: published value, seen in a search-retrieved excerpt from the cited URL this session.
- **[PUB-recall]**: published value that I know from the standard but could not re-check this session. Verify it before quoting it as authoritative.
- **[DER]**: derived or converted by me from a published formula. The arithmetic is shown.
- **[EST]**: engineering estimate or heuristic for simulation use.

Units: Ea = actual superelevation (cant), Eu = unbalanced superelevation (cant deficiency). V is in mph (US formulas) or km/h (metric). R is in ft or m. D is degree of curve (chord or arc per 100 ft; D = 5729.58/R_ft).

---

## 1. Horizontal curves

### 1.1 Curve-speed equation and which "G" to use

- US/AREMA/FRA: **Ea + Eu = 0.0007·D·V²** (in, deg, mph), i.e. **V_max = sqrt((Ea+Eu)/(0.0007·D))**. This is the 49 CFR 213.57 formula. [PUB] https://www.law.cornell.edu/cfr/text/49/213.57
  - The same equation in radius form is **Ea+Eu = 4.0·V²/R_ft**, because 0.0007 × 5729.58 = 4.01. [DER] An LA Metro turnout formula uses Et = 4.011 V²/R. [PUB] https://archive.wheel-rail-seminars.com/archives/2022/rt-papers/presentations/RT08%202022%20Wyman%20Jones%20Final%20WRI%20Presentation%20-%20Formatted%20by%20Josh%20Jun%2021.pdf
- Metric: **E_total(mm) = 11.8·V²/R** (V km/h, R m). Ottawa LRT uses **E = 11.83 V²/R**. [PUB] https://documents.ottawa.ca/sites/default/files/OLRT%20-%20Scope%205%20-%20Schedule%2015-2%20Part%202.pdf
  - Rearranged: **V_max(km/h) = sqrt(R·(Ea+Eu)/11.8)**. [DER]
- **Which G is correct:** E = G·v²/(g·R), where G is the distance between the rail-head contact points (rail centre-lines), **not** the 1435 mm gauge.
  - Back-solving the published constants: 11.83 × 9.81 × 3.6² = **1504 mm**. US 4.0 → G = 4.0/(1.4667²/32.17) = **59.8 in ≈ 1520 mm**. [DER]
  - EN 13803 uses 1500 mm for standard gauge. [PUB-recall]
  - **Use G = 1500 mm.** Using 1435 mm overstates the speed by sqrt(1500/1435) − 1 ≈ 2.2%, which is small but systematic. [DER]
  - Equivalent lateral acceleration: a_q = g·Eu/G, so Eu = 75 mm → 0.49 m/s², 100 mm → 0.65 m/s², 115 mm → 0.75 m/s², 150 mm → 0.98 m/s². [DER]

### 1.2 Metro / light-rail / heavy-rail transit criteria

| Parameter | Value | Source |
|---|---|---|
| Max Ea, LRT handbook | 150 mm (6 in) | [PUB-recall] TCRP Rpt 155 ch.3 https://nap.nationalacademies.org/read/22800/chapter/4 |
| Max Eu, LRT standard | **76 mm (3 in)**; "75 to 115 mm (3 to 4.5 in)" acceptable from experience | [PUB] TCRP Rpt 57 https://onlinepubs.trb.org/onlinepubs/tcrp/tcrp_rpt_57-a.pdf |
| Max Eu, Ottawa LRT | 115 mm | [PUB] Ottawa OLRT Schedule 15-2 (URL above) |
| UTA (Salt Lake) LRT | Ea max **5 in**; Eu max **4 in**, 3 in desirable | [PUB] https://www.rideuta.com/-/media/Files/Doing-Business/Design-Info/UTA_Design_Criteria_Manual_R1_2024_10_01.pdf |
| LA Metro (1968 prelim. heavy rail) | Ea ≤ 5 in in tunnel, 6 in on structure; Eu max 5 in, "optimum" 3 in (historical) | [PUB] https://libraryarchives.metro.net/DPGTL/scrtd/1968-metro-rail-preliminary-design-criteria-and-outline-specifications.pdf |
| LA Metro MRDC (current), turnouts | 3 in unbalance | [PUB] WRI 2022 presentation (URL above) |
| MARTA design crosslevel | 0 on tangents and turnouts, up to 6 in in curves | [PUB] https://itsmarta.com/wayside-docs/Books%20For%20QR%20codes%20PDFs/Track%20Inspection%20Modules/Section%2010-Surface.pdf |
| WMATA vehicle min radius | **225 ft (68.6 m)**; max grade 5% (railcar spec) | [PUB] https://www.wmata.com/business/procurement/solicitations/documents/General%20Design%20Criteria%20-%208K%202017%2001%2024.pdf |
| Honolulu (elevated metro) guideway | min radius **1100 ft (335 m)** precast, **800 ft (244 m)** cast-in-place; max grade **5.5%** | [PUB] https://www.aspirebridge.com/magazine/2015Summer/Project-HonoluluRailTransitProject.pdf |
| Typical heavy-rail mainline min radius | desired ≥ 300 m (1000 ft); absolute ~150 m; yard 70–100 m (230–330 ft) | [EST] from the agency values above and general practice |
| Spirals required | Ottawa: none if Ea = 0 and Eu < 50 mm; spiral ≥ 10 m otherwise | [PUB] Ottawa (URL above) |

Superelevation practice: transit typically applies less than equilibrium cant. A common rule is Ea ≈ 0.66·E_eq − 0.5 in (TCRP), rounded to 1/4 in, with Ea = 0 when E_eq < ~1 in. [PUB-recall] TCRP 155. In a simulator only the sum Ea+Eu at the speed limit matters. Ea matters separately only for spiral length (§2).

### 1.3 Commuter rail (FRA / AREMA / agency)

- **49 CFR 213.57**: max elevation of the outside rail is **8 in on Classes 1–2 and 7 in on Classes 3–5**. All vehicles are considered qualified for **Eu ≤ 3 in**. Higher Eu needs vehicle qualification, and more than 5 in needs FRA approval or documentation. [PUB] https://www.law.cornell.edu/cfr/text/49/213.57
- FRA Class speed caps for passenger trains: Class 1 = 15, 2 = 30, 3 = 60, 4 = 80, 5 = 90, 6 = 110, 7 = 125 mph (49 CFR 213.9/213.307). [PUB-recall]
- Typical passenger-rail design Eu is 3 in. FRA notes that every operator except MBTA calculates passenger superelevation with at least 3 in of cant deficiency. [PUB] https://railroads.dot.gov/sites/fra.dot.gov/files/fra_net/19085/Superelevation.pdf
- **MBTA commuter rail**: Eu 1.5 in preferred, **2.75 in max**; Ea ≤ 6 in. [PUB] FRA report (above) and MBTA 1996 manual https://archive.org/details/mbta-commuter-rail-design-standards-manual-4-19-1996
- **Amtrak Spec 63**: Ea ≤ **5.5 in**. Ea + Eu must be at least 1 in below (Ea_max + Eu_max). [PUB] https://www.amtrak.com/content/dam/projects/dotcom/english/public/documents/corporate/engineering-practices/engineering-specs/amtrak-track-design-specification-63.pdf
- Shared freight track limits Ea through the cant-excess concern: practical Ea is about 4–5 in on mixed lines. [PUB] context: https://railroads.dot.gov/sites/fra.dot.gov/files/2020-02/Cant%20Excess_Freight_Shared%20Track.pdf. The numeric range is [EST].
- Metric EN 13803 equivalents for non-tilting trains: cant D normal ≤ 160 mm (ballasted), exceptional 180 mm; cant deficiency I normal ~130 mm for V ≤ 160 km/h, exceptional ~150 mm. [PUB-recall] A secondary source gives 130 mm for conventional trains and 160 mm max cant (UIC). [PUB, secondary] https://railwaynews.net/wiki/the-art-of-banking-cant-superelevation-explained

### 1.4 Speed-vs-radius table [DER from V = sqrt(R(Ea+Eu)/11.8)]

| R (m) | Metro Ea150+Eu100 (km/h) | Metro Ea150+Eu75 | Commuter Ea150+Eu76 (FRA 3 in) | Commuter Ea125+Eu76 |
|---|---|---|---|---|
| 100 | 46 | 44 | 44 | 41 |
| 200 | 65 | 62 | 62 | 58 |
| 300 | 80 | 76 | 76 | 71 |
| 400 | 92 | 87 | 88 | 83 |
| 500 | 103 | 98 | 98 | 92 |
| 800 | 130 | 124 | 124 | 117 |
| 1000 | 146 | 138 | 138 | 131 |
| 1500 | 178 | 169 | 169 | 160 |
| 2000 | 206 | 195 | 196 | 185 |

---

## 2. Spirals (transition curves)

### 2.1 Published length formulas (US: L ft, E in, V mph)

| Formula | Basis (implied rate) | Source |
|---|---|---|
| **L = 1.63·Eu·V** | rate of change of Eu = 1.4667/1.63 = **0.90 in/s ≈ 22.9 mm/s** [DER] | AREMA Ch.5 EQ1 [PUB] https://railtec.illinois.edu/wp/wp-content/uploads/AREMA-Chapter-5-2007.pdf ; Amtrak Spec 63 [PUB] |
| **L = 62·Ea** | twist ≤ 1 in per 62 ft = 1:744 | AREMA Ch.5 EQ2 [PUB] (same) |
| **L = 1.22·Eu·V** | 1.20 in/s ≈ 30.5 mm/s [DER]; AREMA EQ3 for realignment of existing track | AREMA 2014 [PUB] https://www.railroadfasteners.com/download/AREMA-Stand-for-Track.pdf |
| UTA LRT: **Ls = 1.63 Eu V desirable, 1.22 Eu V minimum** | as above | [PUB] UTA DCM 2024 (URL §1.2) |
| TCRP 155 LRT: Ls desired min = **62 Ea**; absolute min = **41.7 Ea** (low-floor-only fleets) | twist | [PUB] https://www.scribd.com/document/202327821/Track-Design-Handbook-Tcrp-rpt-155-2nd-Ed-2012-Part19 |
| AREMA-derived "Ls = 1.09 V·Eu" (ordinary alignment work) | ~1.35 in/s | [PUB] cited in an LRT handbook (MBTA search excerpt, same TCRP source) |
| LA Metro 1986 civil-speed study: **L = 1.17 Ea V**, **L = 0.99 Eu V** | 1.25 in/s and 1.48 in/s [DER] | [PUB] https://libraryarchives.metro.net/DPGTL/scrtd/1986-civil-speed-limits-on-horizontal-and-vertical-curves.pdf |
| Ottawa LRT (metric): **L(m) = max(Ea·V/108, Eu·V/180)**, ≥ 10 m (Ea, Eu mm; V km/h) | **30 mm/s** cant rate, **50 mm/s** cant-deficiency rate [DER] | [PUB] Ottawa (URL §1.1) |

Metric versions of the US formulas [DER]:

- L(m) = 1.63 Eu V → **L = 0.0121·Eu(mm)·V(km/h)**
- 1.22 Eu V → **L = 0.0091·Eu·V**
- 62 Ea → **L = 0.744·Ea(mm)** (twist 1:744; 150 mm → 112 m)
- 41.7 Ea → **L = 0.50·Ea(mm)**

### 2.2 EN 13803 rate limits (metric)

- Rate of change of cant deficiency dI/dt, non-tilting trains, V < 200 km/h, I < 168 mm: **normal 55 mm/s, exceptional 100 mm/s** (EN 13803-1:2010 Table 3). [PUB] https://cdn.standards.iteh.ai/samples/33335/c7d61477185345ea8bbc7cb20ebecd5b/SIST-EN-13803-1-2010.pdf
- EN 13803:2017 Table 15 (clothoids, V ≤ 220 km/h): I ≤ 160 mm normal 55 / exceptional 100 mm/s; 160 < I ≤ 180 mm normal 55 / exceptional 90 mm/s. [PUB] https://pdfcoffee.com/bs-en-13803-2017-pdf-free.html
- Rate of change of cant dD/dt (linear ramps): **normal 50 mm/s**. Exceptional is ~60 mm/s. [PUB for 50; PUB-recall for 60] (same)
- Cant gradient dD/ds: normal ≤ 2.25 mm/m, exceptional 2.5 mm/m (≈ 1:444 / 1:400). [PUB-recall]
- UK GCRT5021: dI/dt 55 normal / 70 exceptional mm/s. [PUB] https://consultations.rssb.co.uk/_entity/sharepointdocumentlocation/e755957b-950b-ee11-8f6e-000d3aba3cb5/2ab10dab-d681-4911-b881-cc99413f07b6?file=06.+GCRT5021+Issue+6.pdf
- Jerk: dI/dt = 55 mm/s ≈ 0.36 m/s³ lateral jerk (× g/G). [DER]

### 2.3 How curve speed limits come out when spirals exist (simulator rule)

For each curve with body radius R, applied cant Ea, and spiral length Ls (one spiral each side, equal for simplicity):

1. **Body limit:** V_body = sqrt(R(Ea+Eu_max)/11.8). [DER]
2. **Spiral limit from the cant-deficiency rate:** I(V) = 11.8V²/R − Ea runs from 0 to I(V) over Ls. This requires (V/3.6)·I(V)/Ls ≤ r_I, with r_I = 23 mm/s (AREMA desirable), 30 mm/s (AREMA min / Ottawa), or 55 mm/s (EN normal). Solve the cubic in V numerically (bisection). [DER]
3. **Spiral limit from the cant rate:** (V/3.6)·Ea/Ls ≤ r_D (≈ 30–50 mm/s) → V ≤ 3.6·r_D·Ls/Ea. [DER]
4. **V_curve = min(V_body, V_2, V_3, line max speed).**

In a design-to-standard alignment, Ls is chosen so that steps 2 and 3 do not bind. For reconstruction (§6), choose Ls from the formulas first, then check steps 2 and 3 only if Ls had to be shortened to fit. The speed restriction applies over the whole curve including both spirals, plus train length on exit (the rear must clear before acceleration). [EST]

---

## 3. Reverse curves and minimum tangent length

- **0.57V is the metric form of a "2-second" rule:** L(m) = 0.57·V(km/h) ⇔ L(ft) = 3·V(mph). Both give ≈ 2.05 s of travel on tangent. [DER] (0.57 × 3.6 = 2.05 s; 3/1.4667 = 2.05 s.) So "0.57 V ft" with V in mph would be wrong by about ×5.
  - Amtrak Spec 63: tangents and constant-radius curve bodies must be at least **max(3·V_mph ft, 100 ft)**. Tangent between reverse curves ≥ **100 ft**. [PUB] Amtrak Spec 63 (URL §1.3)
  - DC2RVA: reverse curves 3V preferred, **200 ft absolute minimum**. L = 3V is "two seconds on tangent". [PUB] https://vapassengerrailauthority.org/wp-content/uploads/2022/09/APPENDIX_B_Basis_of_Design_Report_DC2RVA_DEIS.pdf
- AREMA: ≥ **100 ft** between curves where practical. Shorter is allowed if the combined effect is no worse than a single minimum-radius curve. [PUB via CHSR TM] https://hsr.ca.gov/wp-content/uploads/docs/programs/eir_memos/Proj_Guidelines_TM1_1_6R0.pdf
- Miami-Dade rapid transit: absolute minimum **100 ft** between reverse curves outside special trackwork. [PUB] https://www.miamidade.gov/transit/library/reports/compendium-design-criteria/volume7-chapter5-passenger-vehicle.pdf
- Ottawa LRT: **25 m** minimum between reversing curves. [PUB] Ottawa (URL §1.1)
- RTD Denver LRT: at least both trucks of the longest vehicle on tangent. [PUB] https://nacto.org/wp-content/uploads/rtd_light_rail_design_criteria_regional_trans_district.pdf
- CHSR: 100 ft desirable / 75 ft minimum between reverse curves. [PUB] CHSR TM (above)
- Minimum circular-curve body length: the same 3V ft / 0.57V m rule applies (Amtrak). [PUB]
- **Simulator rule:** T_min = max(30 m, 0.57·V_kmh m) between spiral ends of reverse curves. Allow 0 for compound same-direction curves (spiral-to-spiral). [EST]

---

## 4. Vertical alignment

### 4.1 Grades

| Mode | Max sustained | Short/absolute | Source |
|---|---|---|---|
| Heavy rail rapid transit (general) | 3–4% | — | [PUB] https://www.accessengineeringlibrary.com/content/book/9780071800129/back-matter/appendix9 |
| WMATA | — | 5% (railcar design spec) | [PUB] WMATA 8K criteria (URL §1.2) |
| Honolulu elevated metro | — | 5.5% | [PUB] Aspire (URL §1.2) |
| LRT | 4% typical; up to ~6% short grades entered at speed; up to 10% possible | — | [PUB] TCRP 57 (via RTD search excerpt); 6–9% LRT max [PUB] accessengineering (above) |
| Commuter/passenger RR | **2.0%** (Caltrain, UPRR, AREMA abs. max); CHSRA 2.5% | — | [PUB] https://www.caltrain.com/media/1261/download (Caltrain delivery guide table) |
| Mixed freight corridors | ~1% (Caltrain: 1% for freight on structures) | — | [PUB] Caltrain (above) |
| Station platforms | level preferred, **≤ 0.5%**; no platform inside a vertical curve | — | [PUB] DC2RVA (URL §3) |

Further rules:

- **Grade compensation for curves:** 0.04% per degree of curve (AREMA). [PUB via Wikipedia summary] https://en.wikipedia.org/wiki/Curve_resistance_(railroad)
- **Metro stations:** use 0–0.5%. Underground stations often require a minimum of ~0.2–0.35% for drainage. [EST]

### 4.2 Vertical curves

- **AREMA (current):** L = 2.15·V²·(A%/100)/a, with V mph, a in ft/s². Use **a = 0.10 ft/s² freight, 0.60 ft/s² passenger**, sag and crest, and **L ≥ 100 ft**. [PUB] CHSR TM2.1.2 https://hsr.ca.gov/wp-content/uploads/docs/programs/eir_memos/Proj_Guidelines_TM2_1_2R00.pdf ; AREMA 2007 Ch.5 (URL §2.1)
  - Equivalent: L(ft) = 0.0215·A·V²/a. [DER]
  - Example: 60 mph, A = 2%: 258 ft passenger, 1548 ft freight. [PUB example arithmetic]
- **Amtrak:** r ≤ **0.10% change of grade per 100 ft**. [PUB] Amtrak Spec 63
- **Old AREA rule** (still in many agency manuals): rate of change per 100-ft station of 0.05% sag / 0.10% crest on mainline. [PUB-recall] MBTA 1996 uses a per-station rate criterion. [PUB] (MBTA URL §1.3)
- **TCRP LRT** (secondary slide summary): desired L = **60·A (m)**; preferred minimum = **30·A (m)**; absolute minimum is speed-based, and sag is more restrictive than crest. [PUB, secondary] https://www.uoanbar.edu.iq/eStoreImages/Bank/19110.pdf ; sag more restrictive [PUB] TCRP 57
- **Metric physics** [DER]: L(m) = A(%)·V(km/h)²/(1296·a_v), and Rv(m) = V²/(12.96·a_v).
  - a_v = 0.3 m/s² (≈ 0.03 g, the highway/AASHTO comfort value [PUB] https://www.webpages.uidaho.edu/niatt_labmanual/Chapters/geometricdesign/professionalpractice/SagVerticalCurves.htm) gives L = A·V²/389.
  - a_v = 0.22 m/s² gives Rv = 0.35 V² (EN 13803 normal-limit form; [PUB-recall], coefficient arithmetic [DER]).
  - EN 13803 minimum Rv ≈ 2000 m normal. [PUB-recall]
- UK NR/L2/TRK/2049 vertical acceleration: 2.25% g normal, 6% g exceptional. [PUB] https://railwaytrackblog.com/2016/04/11/track-design-limits-of-vertical-acceleration/
- **0.05 g** (0.49 m/s², 1.6 ft/s²) is an aggressive transit absolute limit. I found no published transit source for it, so treat it as [EST] absolute. Use 0.03 g (0.3 m/s²) as the design value. [EST]
- Rules: no vertical curve overlapping a station platform or special trackwork. [PUB] DC2RVA. Avoid coinciding a vertical curve with a spiral where possible. [EST]

### 4.3 At-grade crossings

Profile at a road crossing should match the road crown: a short near-level section (≈ ±1% over ~15–30 m) and no superelevation in the crossing ideally. [EST] For a simulator, crossings mainly impose speed limits (signal/gate practice, e.g. LRT street running ≤ 35 mph). Model these as speed restrictions, not geometry. [EST]

### 4.4 Elevated guideway clearances and depth

- **Over roads (Ohio):** ODOT L&D Vol.3 §1400 airway/highway clearance thresholds: 17 ft interstates/freeways/expressways, 15 ft other public roads, 23 ft railroads. [PUB] https://tas.transportation.ohio.gov/CADD/VOL3/VOL3_SECT1400_2021_01.pdf
  - ODOT prefers 16 ft 6 in (5.03 m) under interstate bridges; the national minimum is 16 ft. [PUB, press] https://amerisurv.com/2015/06/16/odot-hires-woolpert-to-renovate-elevate-complex-highway-bridge/
  - Other states: 16.5 ft over primary and 15.0 ft over non-primary (Iowa, Colorado). [PUB] https://iowadot.gov/media/4609/download
- **Over railroads:** AREMA **23 ft 0 in** above top of rail, adopted by most Class 1 railroads. [PUB] https://www.dot.ny.gov/divisions/engineering/design/dqab/hdm/hdm-repository/chapt_23.pdf. UPRR 23 ft 4 in; BNSF 23 ft 6 in. [PUB] https://www.oregon.gov/ODOT/Engineering/Details/DET1200.pdf
- HART (Honolulu) overhead clearance: 17 ft 6 in desired, 14 ft 6 in reduced. [PUB] http://hartdocs.honolulu.gov/docushare/dsweb/Get/Rendition-11928/unknown
- **Structure depth:** metro U-girder 30 m span ≈ **2.1–2.15 m deep** (span/depth ≈ 14). [PUB] https://www.pedelta.com/preliminary-design-of-viaduct-for-the-mumbai-metro-p-87-en
  - Spans are typically 25–33 m. [PUB] https://themetrorailguy.com/2024/01/12/lt-launches-chennai-metro-line-3s-1st-u-girder-on-omr/
  - Add ~0.4–0.6 m for plinth, rail and fasteners. [EST]
- **Top of rail above the road surface:** ≥ 5.0 m + ~2.6 m ≈ **7.5–8 m** over roads, and ≈ **7.0 + 2.6 ≈ 9.6–10 m** over freight railroads. [DER/EST]
- Ramp from grade to elevated (8 m) at 4% ≈ 200 m plus vertical curves. At 2% (commuter) ≈ 400 m. [DER]

---

## 5. Resistances

| Term | Formula | Source |
|---|---|---|
| Grade | **20 lb/ton per 1% grade** (US); metric **10·i N/kN** with i in % (= g·sinθ ≈ 9.81 N/kN per %) | [PUB] https://www.republiclocomotive.com/locomotive-power-calculations/ ; metric [DER] |
| Curve, AREMA | **0.8 lb/ton per degree** (range 0.3–1.0, often 0.5 assumed); = 0.04% grade per degree | [PUB] https://rosap.ntl.bts.gov/view/dot/79037/dot_79037_DS1.pdf ; https://www.ideals.illinois.edu/items/4799/bitstreams/18774/data.pdf ; Wikipedia (URL §4.1) |
| Curve, metric from AREMA | 0.8 lb/ton/deg = 0.4 N/kN/deg → **w_c ≈ 0.4·1746/R(m) ≈ 700/R N/kN** | [DER] (D = 1746/R_m) |
| Curve, Röckl (standard gauge) | **w_c = 650/(R−55) N/kN for R ≥ 300 m; 500/(R−30) for R < 300 m**. Variant: 650/(R−55) above 350 m, 530/(R−35) for 250–350 m, 500/(R−30) below 250 m | [PUB] https://en.wikipedia.org/wiki/Curve_resistance_(railroad) ; https://yadda.icm.edu.pl/baztech/element/bwmeta1.element.baztech-5fba30a7-429b-411d-a153-b36e9e174499/c/BilinskiTTS10-1.pdf |
| Curve, metre gauge (Röckl) | 400/(R−20) N/kN (0.75 m gauge: 350/(R−10)) | [PUB] Bilinski (above) |
| Curve, AREMA caveat | approximations can be several times too high at balancing speed | [PUB] Wikipedia (above) |
| Starting resistance | roller bearings: barely a factor; 2–5 lb/ton base on level track (≈ 1–2.5 N/kN). Use ~**2.5–5 N/kN breakaway** for the first ~1–2 km/h | [PUB] republiclocomotive (above); breakaway value [EST] |
| Running (Davis) | R = 0.6 + 20/w + 0.01V + K V²/(w n) lb/ton (modified Davis); CN: 1.5 + 18N/W + 0.03V + CaV²/10000W | [PUB] https://www.slideserve.com/adele/module-5-tractive-effort |

Röckl and AREMA agree within ~10% for R = 300–1000 m (e.g. R = 400 m: Röckl 1.88 N/kN, AREMA-metric 1.75 N/kN). [DER] Curve resistance is small compared with grade (2% = 20 N/kN), so either formula is fine for travel time. Grade matters much more for energy.

---

## 6. Inferring realistic curves from coarse hand-drawn polylines

### 6.1 Clothoid / spiral geometry (implementation formulas)

For a clothoid of length Ls into a circle of radius R (spiral angle θs = Ls/(2R) rad), standard result [PUB-recall; textbook, e.g. AREMA/Hickerson]:

- Spiral end coordinates: Xs = Ls(1 − θs²/10 + θs⁴/216 − …); Ys = Ls(θs/3 − θs³/42 + θs⁵/1320 − …)
- Shift: **p = Ys − R(1 − cos θs) ≈ Ls²/(24R) − Ls⁴/(2688R³)**
- Tangent-offset abscissa: **k = Xs − R sin θs ≈ Ls/2 − Ls³/(240R²)**
- Total tangent length (PI to TS): **Ts = (R + p)·tan(Δ/2) + k**
- External: Es = (R + p)·sec(Δ/2) − R
- Circular-arc length: Lc = R(Δ − 2θs). This requires **Δ ≥ Ls/R**. If not, shorten Ls to R·Δ (spiral-spiral curve) or reduce R.
- Total curve length: Lc + 2Ls. The arc is shorter than the two-tangent path by (2Ts − Lc − 2Ls); this changes simulated distance.
- Fresnel-integral evaluation for exact clothoids: https://arxiv.org/pdf/1209.0910 [PUB]

### 6.2 Recommended algorithm (max-radius fit at each vertex) [EST, built from the formulas above]

**Inputs:** polyline vertices P_i, segment lengths l_i = |P_i P_{i+1}|, deflection Δ_i at each interior vertex. Design params: line max speed V_line, Ea_max, Eu_max, R_min, spiral rule, T_min (§3).

1. **Denoise.**
   - Treat |Δ_i| below a threshold as digitizing noise. Use Δ_noise ≈ 2·e/l, with e ≈ 3–5 m drawing tolerance; e.g. l = 150 m → ~3°.
   - Also drop it if the resulting R exceeds the radius needed for V_line: R_free = 11.8·V_line²/(Ea_max+Eu_max), e.g. 120 km/h, 250 mm → 680 m.
2. **Merge curve runs.** Consecutive same-sign deflections separated by short segments (< ~2× the expected Ts) are usually one curve drawn as a chord polygon. Hand-drawn polylines usually put vertices **on** the curve, not at PIs.
   - Replace the run with one PI: the intersection of the incoming and outgoing tangents, with Δ = ΣΔ_i.
   - Or estimate R directly by least-squares circle fit through the run's vertices.
   - For an inscribed polygon with equal chords c: **R ≈ c/Δ_i**, or exactly c/(2 sin(Δ_i/2)).
   - Three-point circumradius: R_i = (a·b·c)/(4·Area).
3. **Tangent budget.** For each PI j, the available length on each side is the distance to the neighbouring PI minus that neighbour's tangent and T_min. Split shared segments in proportion to the neighbours' Δ (or tan(Δ/2)), or solve jointly (below).
4. **Choose R by bisection.**
   - Find the largest R ∈ [R_min, R_cap] such that Ts(R) ≤ available tangent, with:
     - V(R) = min(V_line, sqrt(R(Ea_max+Eu_max)/11.8))
     - Ea(R) = min(Ea_max, max(0, 11.8V²/R − Eu_design))
     - Ls(R) = max(0.0121·Eu·V, 0.744·Ea [or 0.50·Ea for LRT], L_min = 10–20 m), metric per §2.1
   - Ts(R) is monotone increasing in R, so bisection works.
   - If even R_min doesn't fit, the drawing is inconsistent: accept R_min, shorten spirals, and flag it.
5. **Joint solve (better).** Maximize Σ log R_j subject to Ts_j^out + T_min + Ts_{j+1}^in ≤ d(PI_j, PI_{j+1}) for all j. This is a small nonlinear program (scipy SLSQP), or iterate step 4 with Gauss–Seidel passes.
6. **Speed profile input.** For each curve, output [start of spiral, end of spiral] with V_curve from §2.3, which keeps the train-length rule. Optionally output the curvature κ(s) for resistance.
7. **Sanity check.** The deviation of the fitted curve from the drawn vertices is roughly Es for PI-type input, or the sagitta for chord-type input. Flag if it exceeds ~10–20 m.

### 6.3 Literature

- Automatic recreation of railway horizontal alignments (tangents + circles + symmetric clothoids): curve locations from local extrema of the curvature diagram, then constrained least-squares; mean y-offset 4 mm on test data. Limitations: backtracking and compound curves. [PUB] https://link.springer.com/article/10.1007/s40534-024-00348-2 (open copy https://d-nb.info/1353005062/34)
- McCrae & Singh 2008, "Sketching piecewise clothoid curves": discrete curvature of a polyline vs arc length → piecewise-linear fit of the curvature diagram → G2 clothoid segments. Directly applicable to hand-drawn input. [PUB] https://www.dgp.toronto.edu/~mccrae/projects/clothoid/sbim2008mccrae.pdf
- Easa & Wang: recovering radius and clothoid length from scattered points. [PUB, cited in Springer paper]
- Discrete-curvature approach for coarse polylines: κ_i ≈ Δ_i / ((l_{i−1}+l_i)/2). Smooth this, then segment into κ ≈ 0 (tangent), κ ≈ const (arc) and linear (spiral) pieces. With 50–300 m vertex spacing, curvature resolution is poor, so prefer the max-radius tangent fit (§6.2) and use κ only to detect runs. [EST]

---

## 7. Elevation data and deriving a design profile

### 7.1 Datasets

| Dataset | Surface | Vertical datum | Accuracy | Source |
|---|---|---|---|---|
| USGS 3DEP lidar QL2 → 1 m DEM | **bare earth (DTM)** | **NAVD88 (GEOID18)** | RMSEz **10 cm**; NVA **19.6 cm @95%**; VVA **30 cm @95th pct**; ≥ 2 pts/m² | [PUB] https://www.usgs.gov/3d-elevation-program/topographic-data-quality-levels-qls ; https://rockyweb.usgs.gov/vdelivery/Datasets/Staged/Elevation/metadata/CO_SanLuisJuanMiguel_2020_D20/CO_SanLuisJuanMiguel_2_2020/reports/140G0220F0113_CO_SanLuisJuanMiguel_2020_D20_WU_ID213146_Lidar_Mapping_Report.pdf |
| 3DEP 1/3 arc-second (~10 m) seamless | bare earth | NAVD88 | degrades to source quality; in Ohio built from lidar | [PUB-recall] |
| Copernicus GLO-30 | **DSM** (X-band TanDEM-X; includes buildings and part of the canopy) | **EGM2008** | spec abs. < 4 m LE90 [PUB-recall]; vs lidar in floodplains NMAD **1.27 m**, median +0.21 m | [PUB] https://www.tandfonline.com/doi/full/10.1080/17538947.2024.2308734 |
| SRTM / NASADEM | DSM (C-band, 2000) | **EGM96** | NMAD **3.65 m** in the same study | [PUB] (same) |

- **Vegetation:** the bias scales linearly with canopy height and tracks lidar RH50.
  - GLO-30 forest bias was within ~1 m in tropical/boreal tests, with mean bias 5–15 cm and RMSE 55–92 cm. [PUB] https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2023JG007672
  - GLO-30 elevations cluster near the middle of the canopy. [PUB] https://onlinelibrary.wiley.com/doi/abs/10.1111/tgis.12825
  - X-band penetrates less than C-band, so GLO-30 shows large positive errors in dense vegetation. [PUB] tandfonline 2024 (above)
  - In Ohio's deciduous riparian corridors and wooded hillsides, expect **+2 to +15 m** apparent ground in DSMs under 20–30 m canopies. [EST from the RH50 relationship]
- **Buildings and urban areas:** GLO-30 urban RMSE ≈ **1.5–1.9 m** vs lidar. [PUB] https://arxiv.org/pdf/2308.06545. Errors are low on roads and gaps between buildings. [PUB] https://www.sciencedirect.com/science/article/pii/S2666544125000371. A 30 m cell on a building edge can read +5–20 m. [EST]
- **Datum:** NAVD88 vs EGM2008 heights differ by a roughly constant few tenths of a metre over a city-sized area (~0.3–0.6 m in Ohio). This is irrelevant to grades but matters when mixing datasets. [EST]
- **Bridges:** 3DEP bare earth removes bridges, so the DEM shows the creek or road bottom under existing structures. DSMs include bridge decks. [PUB-recall]
- **Effect on grade estimates** [DER]: the standard error of a grade over baseline L is σ_g ≈ √2·σ_z/L.
  - 3DEP (σ_z ≈ 0.1 m): 100 m → 0.14%; 300 m → 0.05%.
  - GLO-30 (σ_z ≈ 1.3–1.9 m, spatially correlated): 300 m → ~0.6–0.9%; 1 km → ~0.2–0.3%.
  - SRTM (σ_z ≈ 3.7 m): 1 km → ~0.5%.
  - A single tree line or building in a DSM can create a spurious 5–10% "grade" over 100 m. **Use 3DEP 1 m bare earth for Cincinnati** (Ohio has statewide QL2 lidar; [PUB-recall]). Sample at 5–10 m and take the median of a 3–5 m swath across the track axis.

### 7.2 Ground profile → designed track profile [EST, method]

1. Sample z_g(s) every 10 m along the fitted horizontal alignment from the 3DEP DTM. Apply a median filter of ~30–50 m.
2. **Target profile by structure type:**
   - At-grade/surface: z_t = z_g + ~0.6 m (ballast and subballast; [EST]).
   - Elevated: z_t ≥ z_g + clearance + depth, ≈ 7.5–8 m over roads and ≈ 10 m over railroads (§4.4), with a soft target of minimum height between obstacles.
   - Fixed points: stations (level ±0.5%), road and rail crossings (at-grade: z_t = road z; grade separated: clearance), river bridges (navigation clearance), tie-ins to existing track.
3. **Optimization:** discretize z_t at Δs = 10 m and solve a QP (cvxpy/OSQP):
   - **minimize** Σ w_i(z_i − target_i)² + λ·Σ|z_{i+1} − 2z_i + z_{i−1}|
   - The L1 term on the second difference is "ℓ1 trend filtering". It yields piecewise-linear grades with few breaks, i.e. VPIs.
   - **Subject to:**
     - |z_{i+1} − z_i| ≤ g_max·Δs
     - |z_{i+1} − 2z_i + z_{i−1}| ≤ Δs²/Rv_min, where Rv_min = V²/(12.96·a_v), e.g. a_v = 0.3 m/s² → Rv = 0.257·V² m; 100 km/h → 2570 m. This encodes the vertical curves directly.
     - Equality or bound constraints at stations and crossings.
     - Station segments: |grade| ≤ 0.5% over platform length + ~20 m each side, and zero curvature there.
     - Clearance lower bounds on elevated sections; bounds on at-grade sections.
   - Weights w_i are high where the line must follow the ground (at-grade in street) and low where structure type is free.
4. **Post-process:** extract VPIs where the second difference is non-zero. Replace each with a parabola L = max(A·V²/(1296·a_v), 30·A m, 30 m). Re-check grade length between VCs (≥ ~0.57V m or ≥ train length). Hand the grade g(s) to the simulator.
5. **Cut/fill/structure heuristics, h = z_t − z_g** [EST, typical US practice]:
   - |h| ≤ 1 m: at-grade.
   - 1 < h ≤ 6–8 m: embankment (in urban ROW, use a retained fill/wall above ~3 m).
   - h > 6–8 m, or wherever a road, rail or waterway must be crossed: viaduct (elevated cost breakeven vs high fill ≈ 8–10 m).
   - 1 < −h ≤ 6–10 m: open cut (retained cut in urban ROW).
   - −h > ~10–12 m, or long cuts in dense urban areas: tunnel (cut-and-cover to ~15–20 m depth, bored beyond).
   - Avoid alternating structure types over < ~300–500 m. Merge short segments into the dominant type.
6. **Cincinnati-specific:** the Ohio River and Mill Creek valleys sit 150–200 m below the surrounding hilltops (river ~140 m NAVD88, uplands ~240–280 m) [EST]. Expect profiles governed by g_max on climbs out of the basin. Check 3–4% (metro) vs 2% (commuter) feasibility, which drives where tunnels or viaducts are needed.

---

## Recommended simulator defaults (summary)

**(a) Metro (heavy-rail or high-floor light metro, at-grade/elevated):**

- Geometry and speed:
  - G = 1500 mm; Ea_max = 150 mm (6 in); Eu = 75 mm design, 100–115 mm max (3 in / 4–4.5 in)
  - V = sqrt(R·(Ea+Eu)/11.8)
  - R_min mainline 300 m desired / 150 m absolute; yard 70–100 m
- Spirals and tangents:
  - Ls = max(0.0121·Eu·V, 0.744·Ea, 20 m), or 0.50·Ea for LRT twist
  - dI/dt ≤ 30 mm/s design, 55 mm/s check
  - Tangent between reverse curves ≥ max(0.57·V_kmh m, 30 m)
- Vertical:
  - Grades 3% sustained, 4% short, 5–5.5% absolute on elevated structures; stations 0–0.5%
  - Vertical curves: a_v = 0.3 m/s² (L = A·V²/389 m), L ≥ 30·A m
- Curve resistance: Röckl 650/(R−55) N/kN

**(b) Commuter / RER (FRA-compliant):**

- Geometry and speed:
  - Ea_max = 125–150 mm (5–6 in; FRA cap 7 in for Class 3–5); Eu = 76 mm (3 in, FRA default)
  - Shared-freight lines: Ea ≤ 100–125 mm, MBTA-like Eu 70 mm (2.75 in)
  - R desired ≥ 600–1000 m for 110–140 km/h
  - FRA class speed caps apply
- Spirals and tangents:
  - Ls = max(0.0121·Eu·V, 0.744·Ea) (AREMA 1.63 Eu V / 62 Ea)
  - Tangent ≥ max(3·V_mph ft, 100 ft) ≈ max(0.57·V_kmh m, 30 m)
- Vertical:
  - Grades ≤ 2% (1% with freight); stations ≤ 0.5% / level
  - Vertical curves per AREMA: L(ft) = 2.15·V²·A%/(100·0.60), ≥ 100 ft; with freight, a = 0.10
- Curve resistance: 0.8 lb/ton/deg (≈ 700/R N/kN) or Röckl

## APEx curve model (canon, Sept 2026)

Settled in the "Tilting train speeds on curves" discussion and implemented in `speed.py`:

- **Equation:** C = 30.56 V²/R (C in mm, V in mph, R in m). This is the same as V = √(g·R·(Ea+Eu)/G) with G = 1500 mm.
- **Applied cant:** D ≤ 180 mm, the FRA Class 3-5 ceiling and LGV practice. Restricting curves get the full 180 mm. On larger radii the cant is sized for line speed.
- **Cant deficiency, banded by speed** (`speed.cant_deficiency_bands`): 130 mm up to 186 mph (300 km/h), 100 mm above (EN 13803 high-speed band). A more conservative option keeps 80 mm above 250 mph.
- **Tilt (Gen 6T only):** 8° tilt bolster with ~66% compensation of 1500·tan 8°, adding ~140 mm, for 270 mm in total (the Pendolino practical ceiling). Tilt locks above 186 mph (canon, 6 May 2026), so tilt only helps below about 2,350 m radius. Canon minimum radius for tilting sections: 2,500 m.
- **Resulting speeds:**

| Radius | Untilted | Tilting |
|---|---|---|
| 1,000 m | 101 mph | 121 mph |
| 2,500 m | 159 mph | 186 mph (lock) |
| 6,000 m | 234 mph | n/a |
| 7,000 m | 253 mph | n/a |
| 8,000 m | 271 mph | n/a |
| 10,000 m | 303 mph | n/a |

- **Radius needed:** 6,821 m for 250 mph cruise and 8,557 m for 280 mph recovery. The canon recovery rule (straight track or ≥ 10 km radius) has margin over that.
- **Checked by tests:** `tests/test_core.py::test_apex_canon_curve_speeds`.
- **Not modelled:**
  - The crosswind cascade, which lowers tilt-active and cruise speeds in wind.
  - The 280 mph recovery running.
  - Small-angle active suspension (1.5-2°), which was proposed but not adopted.
