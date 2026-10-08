# Research notes: signalling/operations eras + 400 km/h-class HSR (for running-time simulator)

Tags: **[P]** published by operator/manufacturer/standard/official report. **[S]** secondary (Wikipedia, trade press, fan sites, papers quoting others). **[E]** estimate or derivation (mine), or background knowledge I could not verify this session (marked "unverified").
Method: ~43 WebSearch queries. WebFetch and curl to Wikipedia were blocked, so all figures come from search-result extracts. Treat [S] values as "probably right, check before citing".

---

## 1. Metro operations by era

### 1a. 1904-1930s: block signals, trip stops, gate cars, early doors

| Item | Value | Tag | Source |
|---|---|---|---|
| IRT opened with automatic block signals + automatic train stops (trip stops) | 1904 | [S] | https://en.wikipedia.org/wiki/Signaling_of_the_New_York_City_Subway ; https://www.chicago-l.org/infrastructure/signals/tracktrips1.html |
| Trip stop action | Raised stop arm engages trip cock on the truck: cuts power + full emergency brake. Every car has trip cocks | [S] | https://nycsubway.org/wiki/Subway_Signals:_Train_Stops |
| Original block length rule | Stopping distance + 50% margin. Next train held out of the station until the platform cleared, which badly delayed rush-hour service | [S] | https://en.wikipedia.org/wiki/Signaling_of_the_New_York_City_Subway |
| First **station time signals** (let a train close in on an occupied station at a controlled speed) | 96th St, 23 Apr 1909; on all express tracks 96th St to Brooklyn Bridge by 28 Nov 1909 | [S] | same |
| Capacity gain from station time signals | +2 to 3 trains/h per track | [S] | same |
| **Grade time signals** (timers enforcing speed at curves, grades, junctions) | Documented on IND 1939 World's Fair line ("two-shot grade time", S aspect). Rapid growth after 1990s crashes, to ~2,000 timers systemwide | [S] | https://www.nycsubway.org/lines/worldsfair.html ; https://www.old.railwayage.com/?p=33764 ; https://scienceline.org/2021/10/a-century-of-amber-lights-the-story-of-new-yorks-subway-signals/ |
| IRT original car doors | Hand-operated by levers. Only door type on the IRT until 1915. Two hand doors per side, and one man opened both doors at each opening (one guard between each pair of cars) | [S] | https://erausa.org/pdf/bulletin/2000s/2009/2009-08-bulletin.pdf (ERA Bulletin, via search extract) |
| Elevated **gate cars** | One trainman per car platform (gate). "High crew costs needing so many trainmen to operate the doors". Rough rule: 1 guard per 2 cars at the shared platform, plus a conductor | [S]/[E] | ERA bulletin above; https://nycsubway.org/wiki/Chapter_1,_The_Elevated_Lines |
| 1909 side-door experiment (8 Hi-V cars, incl. 3421) | Pneumatic doors worked by the guard with a lever. IRT said "practically no time was saved" | [S] (NYT 1909 reprint) | https://nycsubway.org/wiki/Subway_Side_Doors_A_Partial_Success_(1909) |
| Pneumatic center doors | 1910-11 Standard Hi-V: manual end doors + pneumatic center door worked by the conductor. Older Composite/Gibbs/Deck-roof cars retrofitted 1910-12 | [S] | https://nycsubway.org/wiki/The_Interborough_Fleet,_1900-1939_(Composites,_Hi-V,_Low-V) ; https://en.wikipedia.org/wiki/Hedley_Hi-V_(New_York_City_Subway_car) |
| Multiple-unit door control (MUDC) | ~1920-21. IRT spent ~$2M. Each guard then controlled 2 cars (company wanted 4+, but the Commission resisted). Later the elevated MUDC conversion of 464 ex-gate cars cut the crew to motorman + conductor | [S] | https://erausa.org/pdf/bulletin/2000s/2009/2009-08-bulletin.pdf ; https://en.wikipedia.org/wiki/MUDC_(New_York_City_Subway_car) |
| 1904 express station stop (narrative) | Train "moving swiftly again about thirty seconds after stopping" | [S] (1904 press) | https://nycsubway.org/wiki/New_York's_Subway_In_Operation_(1904) |
| 1904 express running time Brooklyn Bridge to 96th St | 14.5 min "regular express time". Later ~15 min (96th to Bklyn Bridge). Ceremonial City Hall to 96th: 19 min | [S] (NYT 1904) | https://nycsubway.org/wiki/McClellan_Motorman_of_First_Subway_Train_(1904) |
| Planned average speeds incl. stops | 1904 book: local (5 cars) 16 mph, express (8 cars) 25-30 mph. 1901 plan (optimistic): express 38 mph, local 18 mph | [S] | https://archive.org/download/newyorkssubwayra00king/newyorkssubwayra00king.pdf ; https://nycsubway.org/wiki/Progress_of_the_New_York_Rapid_Transit_Tunnel_(1901) |
| 1904 headways | Locals every 3 min. Expresses every 4 min in the peaks | [S] | https://nycsubway.org/wiki/Schedule_of_Trains_for_the_Subway_Out_(1904) |
| Implied express average speed | Brooklyn Bridge to 96th is ~6.6 mi, so 14.5 min ≈ 27 mph incl. 3 intermediate stops | [E] | derived |

**Simulator suggestions, 1905-1930s (my estimates):**
- Gate-car era (to ~1910): dwell 25-35 s express, 15-25 s local off-peak, 40-60 s+ in the peak.
- Hand-operated end doors plus pneumatic center door (1910-20): about 20-30 s.
- MUDC with one conductor per 2 cars (1920s): about 20-25 s.
- Block overlap = braking distance × 1.5.
- Station time signals allow close-in at ~10-15 mph.
- Grade timers enforce curve limits by tripping the train, so model them as hard caps with a 2-5 mph undershoot margin.

### 1b. 1950s-1980s: one-person door control and cab signalling/ATO

| Item | Value | Tag | Source |
|---|---|---|---|
| PATCO opening | 4 Jan 1969 (Camden to Lindenwold), full service 15 Feb 1969. "One of the first" regular-service ATO systems | [P] | https://nj.gov/transportation/capital/guideway/pdf/H_PATCO.pdf |
| PATCO cab signals | US&S pulse-code, 100 Hz carrier, "one of five speeds". Speeds 20/30/40/65 mph + stop. Car max 75 mph | [P]/[S] | NJDOT above; https://trid.trb.org/View/486790 ; https://www.dvrpc.org/committees/rtc/presentations/2019-02.pdf ; https://forums.dovetailgames.com/posts/134610/ |
| BART | ATC revenue service 1972 (Fremont to MacArthur first). Operator on board can override | [P] (CPUC) | https://files.cpuc.ca.gov/LegacyCPUCDecisionsAndResolutions/Decisions/Decisions_D73751_to_D86500/D81248_19730410_C9445.pdf |
| BART service brake design | 2.7-3.3 mph/s (1.2-1.5 m/s²) | [P] (CPUC) | same |
| BART station-stop accuracy (design) | ±1 ft | [S] | https://scitepress.org/Documents/2020/94180/ |
| WMATA 1976 | Opened with ATO **and automatic door opening**. Original max 75 mph, cut to 59 mph about a decade later | [P]/[S] | https://www.wmata.com/initiatives/plans/Automatic-Train-Operation-ATO ; https://wusa9.com/article/traffic/mission-metro/metro-trains-maximum-allowable-speed/65-488c0322-b12b-49a9-a2b0-2210271ef996 |
| WMATA ATC block design deceleration | Min braking 1.65 mph/s (0.74 m/s²) | [S] | https://en.wikipedia.org/wiki/Washington_Metro_signaling_and_operation (search extract) |
| WMATA speed-command codes | Display "00" = stop. Commonly cited set: 0, 15, 22, 28, 35, 40, 45/47, 50, 55, 59, 65, 70, 75 mph | [E] unverified | Wikipedia page above (list not retrieved) |
| WMATA ATO suspended / restored | Suspended after the 2009 Fort Totten crash. Operator-assisted ATO restored on the whole 208 km network in 2024-25. Not used in bad weather, single-tracking, or with workers on track | [P]/[S] | https://www.railjournal.com/infrastructure/washington-restores-ato-on-metro-network/ |
| MBTA Red/Orange | Analog cab signals + ATO (Red) from the 1970s. Operator works the doors | [P] | https://www.mass.gov/doc/appendix-b-mbta-system-description/download ; https://www.dotnews.com/?p=50845 |
| CTA cab signals | e.g. "270 rate" = green 55 mph (max) | [S] | https://chicagorailfan.com/signals.html |
| Times Sq-Grand Central shuttle | Early automatic-operation experiments (1960s) | [S] | https://www.railwayage.com/?p=35275 |

**Simulator suggestion:** in the cab-signal era, speed follows discrete code steps. The driver (or ATO) brakes on a code drop at about 0.75-1.0 m/s² (WMATA design 0.74). Typical code ladders: transit 15/25/35/45/55(/70) mph; PATCO 20/30/40/65 mph.

### 1c. Grades of Automation (IEC 62290-1) and the station stop

| GoA | Name | Who does what at a station | Tag | Source |
|---|---|---|---|---|
| GoA0 | On-sight | No ATP | [S] | https://www.apta.com/wp-content/uploads/RC17-Keevill_Dave.pdf |
| GoA1 | Non-automated (manual with ATP) | Driver: start, stop, doors, emergencies. ATP supervises speed | [S] | https://en.wikipedia.org/wiki/Automatic_train_operation |
| GoA2 | **STO** semi-automated | ATO starts and stops. **Driver closes doors and presses "start"**. Opening may be automatic (WMATA: auto open, manual close) | [S]/[P] | same; https://www.wmata.com/news/auto-doors-now-operating-on-all-metrorail-lines.html |
| GoA3 | **DTO** driverless, attendant on board | Attendant (not in a cab) handles doors and evacuation and can drive manually. DLR: the Passenger Service Agent opens/closes doors, the train departs automatically after the close-other-doors button | [P]/[S] | https://foi.tfl.gov.uk/FOI-0897-2223/LI%200737%20Incorrect%20Door%20Procedure%20(Train%20moved%20without%20PSA%20on%20board)%20RW%20Comment_Redacted.pdf ; https://www.theregister.co.uk/2007/11/01/dlr_train_leaves_staff_on_platform/ |
| GoA4 | **UTO** unattended | System opens/closes doors. ATS sets the dwell. No staff on board | [S] | https://en.wikipedia.org/wiki/Automatic_train_operation |

Platform protection examples:
- **DLR (GoA3):** no platform screen doors (PSDs), no intrusion detection, CCTV only (APTA 2017) [P]: https://www.apta.com/wp-content/uploads/RC17-Hulse_Jon.pdf
- **DLR door warning:** no warning before doors begin closing. The operator said a 3 s pre-close warning "would be virtually impossible to introduce without hurting service levels" [P]: https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/779835/door-closure-warning-sounds-on-dlr-report-2018.pdf
- **Nuremberg U2/U3 (GoA4, U3 from June 2008):** no PSDs. Track-intrusion detection interlocked with ATC. First mixed manual + automatic running on the same tracks [S]: https://en.wikipedia.org/wiki/U3_(Nuremberg_U-Bahn) ; https://railwaynews.net/nuremberg-rubin-u-bahn-automation-project-germany.html
- **Paris Line 14 (1998) and Line 1 (converted 2011-12):** GoA4 with PSDs [E] background knowledge, unverified. Line 1 headway 105 s → 85 s [S]: https://www.railjournal.com/passenger/metros/paris-line-1-automation-project-completed/ ; https://www.clearsy.com/wp-content/uploads/2020/07/UITP-2010-full-autmation-of-line-1.pdf
- **Vancouver SkyTrain (GoA4):** no PSDs, track intrusion detection. **Singapore NEL (2003):** GoA4 with full-height PSDs [E] background knowledge, unverified.
- **General pattern:** GoA3 normally has no PSDs (an attendant watches the platform). GoA4 has either PSDs or intrusion detection [E].

Dwell and door-time data:

| Item | Value | Tag | Source |
|---|---|---|---|
| WMATA manual door opening | Operator checks side and presses button: "up to 15 s" | [P] | https://www.washingtonian.com/2023/10/20/doors-on-metros-red-line-will-finally-operate-faster |
| WMATA auto-door opening | Within ~5 s of stopping (3-5 s). Saves "10-15 s" per stop (2023) or "up to 10 s" (2024). Close stays manual | [P] | same; https://www.wmata.com/news/auto-doors-now-operating-on-all-metrorail-lines.html |
| Door open or close cycle | 2.5-4.5 s per door leaf movement | [S] (weak) | https://railwaynews.net/wiki/the-seconds-that-matter-optimizing-dwell-time-in-rail-ops |
| NYC scheduled dwell | 30 s typical. MTA target <45 s, actual >60 s at busy stations | [S] | https://wnyc.org/story/mta-deploys-subway-platform-conductors-combat-subway-delays ; https://viewing.nyc/mtas-new-platform-controller-program-aims-to-reduce-dwell-time/ |
| NYC observed door-open time | Mean 16.6 s (184 stops, 2006 student study) | [S] | https://hypertextbook.com/facts/2006/subwaydoors.shtml |
| TTC guard allowance | ~15 s per station | [S] | https://stevemunro.ca/2008/01/22/mind-the-doors/ |
| UITP on automation | Consistent dwell + optimised profiles give "up to 10%" higher commercial speed. 60-90 s headways achievable | [P] | https://cms.uitp.org/wp/wp-content/uploads/2021/04/Knowledge-Brief-InfrastructureV7_web.pdf |
| Paris L1 forecast | +4% commercial speed, -20% minimum headway | [S] | https://www.clearsy.com/wp-content/uploads/2020/07/UITP-2010-full-autmation-of-line-1.pdf |

**Simulator suggestion (my estimates), fixed time per stop excluding passenger exchange:**
- **GoA1 manual:** open 5-8 s after stop + close sequence 6-10 s (warning, close, interlock proven, driver reacts and powers).
- **GoA2:** open 3-5 s (auto) or 5-8 s (manual) + driver close/start 5-7 s.
- **GoA3 (DLR-type):** similar to GoA2. The attendant closes doors and the train departs in ~2-3 s.
- **GoA4 with PSDs:** about +2-4 s for PSD and train-door synchronisation and proving. Departure 1-2 s after "all closed and locked".
- **GoA4 without PSDs:** about 1-2 s.
- **Net:** GoA4 vs GoA1 saves about 5-10 s per stop. Dwell variance falls sharply.

### 1d. CBTC/ATO driving behaviour, and does CBTC change running time?

| Item | Value | Tag | Source |
|---|---|---|---|
| ATO profile parameters | Hold (cruise) speed, coast trigger, re-motor threshold, braking rate. Fixed-block systems store ~4 profiles per interstation ("performance levels"). CBTC allows near-continuous values | [S] (Madrid Metro papers) | https://repositorio.comillas.edu/jspui/bitstream/11531/107893/1/IIT-25-385R.pdf ; https://iit.comillas.edu/documentacion/congreso/IIT-08-123C/ |
| Fixed-block ATO braking rates (Madrid) | 0.60-0.75 m/s² in 0.05 steps | [S] | same |
| ATP warning and EB limits | Warning curve set below the EB curve. The margins reduce capacity | [S] | https://patents.google.com/patent/KR20150056242A/ko |
| ATO cruise margin below ATP | Typically 2-5 km/h below the permitted speed. ATO service brake 0.8-1.0 m/s² vs ATP-guaranteed 1.0-1.2 | [E] unverified | — |
| Canarsie (L) CBTC | 15 tph (2007) → up to 26 tph. MTA: fixed block max 26, CBTC 30 tph, but power-limited (20 tph in FTA document) | [S]/[P] | https://en.wikipedia.org/wiki/L_(New_York_City_Subway_service) ; https://www.transit.dot.gov/sites/fta.dot.gov/files/docs/NY_Canarsie_Line_Power_Improvements_FY_2017_0.pdf ; https://pcac.org/?p=2141 |
| Canarsie headways | AM peak 3.5 → 3 min, midday 7.5 → 6 min (2012) | [S] | https://secondavenuesagas.com/2012/06/12/searching-for-the-l-trains-silver-bullet |
| Jubilee line (TBTC, 2011) | Promised -22% journey time. Measured end-to-end 64 → 60 min (-6.25%) | [P]/[S] | https://tfl.gov.uk/info-for/media/press-releases/2011/february/mayor-announces-major-progress-with-jubilee-line-upgrade ; https://archive.londonreconnections.com/?p=813 |
| Northern line (2013-14) | Promised -18% journey time, +20% capacity | [P] | https://www.tfl.gov.uk/info-for/media/press-releases/2013/february/northern-line-upgrade-one-step-closer |
| Victoria line | 36 tph (100 s) from May 2016 | [P]/[S] | https://www.modernrailways.com/article/victoria-line-moves-36tph |

**Takeaway [E]:** CBTC mostly raises capacity and cuts run-time *variability*. On free-running timetables it cuts end-to-end run time by only about 5-10%. Claims of ~20% include new trains with higher speed and acceleration. Simulator effect:
- Fixed block or cab signals: the train runs to code-step ceilings and brakes at the step.
- CBTC: brakes on a continuous curve to the target.
- CBTC gains ~5-15 s per interstation, from later braking and no undershoot below code steps. Coasting choices can give some of it back.

---

## 2. Commuter/RER signalling by era

| Item | Value | Tag | Source |
|---|---|---|---|
| PRR coded track circuit cab signals (first divisions 1927) | Codes in pulses per minute: 180 = Clear, 120 = Approach Medium/Restricting, 75 (1928 article says 80) = Approach. No code = Restricting (~20 mph) | [P] (Railway Signaling 1928/1935) | https://jonroma.net/media/signaling/railway-signaling/1928/Pennsylvania%20Installs%20Code%20System%20of%20Train%20Stop%20with%20Signaling.pdf ; https://www.jonroma.net/media/signaling/railway-signaling/1935/Coded%20Track%20Circuit%20Signaling%20on%20the%20Pennsylvania.pdf |
| Later code set | 50, 75, 120, 180, 270, 420 ppm. 270 = "Cab Speed 60" (forum) | [P] patent / [S] forum | https://patents.google.com/patent/US8998147 ; https://mail.railroadfan.com/phpbb/viewtopic.php?p=507072 |
| Typical NEC aspect speeds | Restricting 20, Approach 30, Approach Medium 45, Cab Speed 60/80, Clear = track max | [E] unverified | — |
| SACEM (RER A) | In service Sept 1989. Continuous speed and spacing supervision with cab display. Under 90 s train spacing at stations, under 2 min in tunnels. Peak core ~30 tph (2 min) in the busy direction | [S]/[P] | https://en.wikipedia.org/wiki/SACEM_(railway_system) ; https://en.wikipedia.org/wiki/RER_A |
| SACEM + ATO | Alstom ATO overlay entered service 2017 | [P] | https://www.alstom.com/press-releases-news/2017/5/alstom-developed-automatic-train-operation-system-successfully-enters-service-on-the-rer-a |
| NExTEO (RER E core, Rosa Parks to Nanterre-La Folie, ~20 km) | CBTC up to 120 km/h. 16 → 22 tph (180 → 108 s). Capacity 28 tph. **GoA2**: automatic start/stop, driver works the doors | [S] | https://www.railwaygazette.com/siemens-cbtc-for-paris-rer-line-e/42056.article ; https://www.railjournal.com/signalling/siemens-chosen-for-paris-rer-line-e-cbtc-deployment/ |
| RER B/D shared tunnel (Châtelet to Gare du Nord) | 2 km tunnel, 32 trains/h at peak (cut to 28 in 2008). NExTEO planned 2027-31, reported suspended | [P] (IDFM, Assemblée) | https://www.iledefrance-mobilites.fr/en/actualites/nexteo-amelioration-ponctualite-rer-e-et-d ; https://questions.assemblee-nationale.fr/dyn/16/questions/QANR5L16QE1670.pdf |
| Elizabeth line | Siemens CBTC core (Westbourne Park to Pudding Mill Lane, plus Whitechapel to Abbey Wood), run in ATO. ETCS L2 on the Heathrow spur. TPWS/AWS on GWML/GEML. Automatic transition: driver accepts CBTC and drives in ATO (Stratford auto-transition from 11 Apr 2023). 22 → 24 tph from 21 May 2023 | [P]/[S] | https://www.railengineer.co.uk/controlling-the-elizabeth-line/ ; https://board.tfl.gov.uk/documents/s19943/elc-20230518-pt1-operational-and-programme-completion-update.pdf ; https://en.wikipedia.org/wiki/Elizabeth_line |

**Concept for the fictional Cincinnati RER [E]:**
- **Core tunnel:** CBTC with GoA2 ATO, a 100-120 km/h ceiling, 24-30 tph capacity, and dynamic transition at the portals.
- **Branches:** stay on lineside or cab signals (later ETCS L2), manual driving.
- **Historical sequence:** PRR-style 4-aspect pulse code (1930s-1990s) → SACEM-like continuous supervision (1990s) → CBTC + ATO core (2020s).

---

## 3. Very-high-speed trains (for "Gen 6" 400 km/h)

| Train | Cars / length | Mass | Power | TE / acceleration | Vmax service (design) | Braking | Tag / source |
|---|---|---|---|---|---|---|---|
| **CR450AF / CR450BF** (2024 prototypes, service ~2026) | 8 (4M4T); 211 m / 211.4 m; width 3.36 m; 14.5 t axle load; 552 seats | ~10% (≈50 t) lighter than CR400. Full-load mass "over 500 t → over 460 t" | 9,600 → **11,000 kW** traction (unofficial). Permanent-magnet water-cooled motors, +3% efficiency | 0-350 km/h in **4 min 40 s** (avg 0.35 m/s²) | **400** (450 design; record 453 km/h) | Emergency stop **<6,500 m from 400 km/h** (avg ≈0.95 m/s²) | [S] https://en.wikipedia.org/wiki/China_Railway_CR450AF ; [P] https://www.crrcgc.cc/en/2025-02/13/article_2025021317203082305.html ; [S] https://www.railwaypro.com/wp/the-worlds-fastest-conventional-train-is-nearing-launch-in-china/ ; [S] https://www.ithome.com/0/910/205.htm (power/mass); [P] https://cn.chinadaily.com.cn/a/202507/21/WS68a2d812a3104ba1353fd663.html (energy) |
| CR450 energy and drag | — | — | **22-23 kWh/km at 400 km/h** (≈ 8.8-9.2 MW average draw) | Running resistance -22% vs CR400. Roof 20 cm lower | — | — | [P]/[S] as above; https://www.alcircle.com/news/chinas-cr450-train-uses-aluminium-and-carbon-fibre-to-hit-record-speed-115998 |
| **CR400AF / BF** (2017) | 8 (4M4T); 209 m; 576 seats | CR400AF-Z 8-car: **449.3 t** (EPD); axle load <17 t | ~10,000 kW at the wheel rim (BF 10,140 kW). AF-G: 12,320 kW installed / 12,012 kW at the rim | 16-car sets 1.76-1.91 km/h/s (0.49-0.53 m/s²) | 350 (400 design; 420 record) | — | [P] https://api.environdec.com/api/v1/EPDLibrary/Files/cd619c0a-9b0a-42f1-efb1-08db61df2909/Data ; [S] https://journal.hep.com.cn/fem/EN/1160058711936917538 ; [S] https://china-emu.cn/EN/Trains/Model/para-12001-101-43.html |
| **Alstom AGV ETR575** (Italo) | 11 articulated; 200 m; 462 seats | 7-car version 272 t → 11-car ≈ 400-410 t [E] | **7,500 kW** (Italo sets) | — | 300 in Italy (360 design) | — | [S] https://ledicoferroviaire.mediarail.be/agv-en/ ; https://railpictures.net/photo/426994 ; https://railway-news.com/100-million-km-avelia-agv-fleet |
| **Frecciarossa 1000 / Zefiro V300 (ETR400)** | 8, non-articulated; 202 m | ~500 t (446-460 t elsewhere) | **9,800 kW** max | **370 kN**; 0.7 m/s² at start; **0-300 km/h in 4 min** | 300 (360 commercial design, 400 design) | — | [P] https://www.hitachirail.com/products-and-solutions/rolling-stock/high-speed-trains/etr1000-frecciarossa/ ; [P] https://www.fsitaliane.it/en/innovation/transport-technology/frecciarossa-1000.html ; [S] https://en.wikipedia.org/wiki/Frecciarossa_1000 |
| **Siemens Velaro Novo** | 7 cars; 202 m (14-car 404 m) | 412-485 t (by speed version). About 15% / >70 t lighter than earlier Velaro | 4,700-8,000 kW | — | 360 concept | — | [P] https://assets.new.siemens.com/siemens/assets/api/uuid:fe879294-8094-4f10-a45a-1d51509e5800/backgrounder-velaronovo-e.pdf ; https://www.railway-technology.com/?p=45845 |
| Velaro Novo aerodynamics | Drag **>30%** lower. Energy **-30% at 300 km/h** (bogie fairings ~15%, nose/gangways ~10%) | | | | | | [P] Siemens brochure https://assets.new.siemens.com/siemens/assets/api/uuid:2e0b0ecf-774d-475a-b957-998feb4e3e63/siemens-mobility-velaro-novo-brochure.pdf ; [S] https://www.railjournal.com/in_depth/velaro-evolution/ |
| **E5 Shinkansen** | 10; 253 m | **453.5 t** | **9,600 kW** (32 × 300 kW) | **1.71 km/h/s** (0.48 m/s²) | 320 (from Mar 2013) | Electro-pneumatic + regenerative. Knorr discs for earthquake stops | [S] https://en.wikipedia.org/wiki/E5_and_H5_Series_Shinkansen ; [S] https://www.railjournal.com/news/knorr-bremse-clinches-shinkansen-braking-deal/ |
| **E10 Shinkansen** (tests 2027, service FY2030) | 10 | — | — | — | 320 | Stopping distance **-15%** (baseline unclear). Anti-derailment L-guides | [S] https://en.wikipedia.org/wiki/E10_Series_Shinkansen ; https://www.railvolution.net/news/class-e10-shinkansen-announced |
| JR East braking (FASTECH/ALFA-X) | — | — | — | — | — | E2 at 275 km/h: EB just under **4,000 m**. At 360 km/h with the same brakes ≈7,000 m. Target **≈4,000 m at 360 km/h** (avg ≈1.25 m/s²) using adhesion control + aero drag plates + linear eddy-current brakes | [P] https://www.jreast.co.jp/e/development/tech/pdf%5F12/Tec-12-12-15eng.pdf |
| **N700 / N700S** | 16; ~404.7 m (2 × 27.35 + 14 × 25 m) | N700 715 t | — | **2.6 km/h/s** (0.72 m/s²) | 285 Tokaido, 300 Sanyo | N700S from 285 km/h: EB ≈3,800 m (weak source) | [S] https://en.wikipedia.org/wiki/N700S_Series_Shinkansen ; https://en.wikipedia.org/wiki/N700_Series_Shinkansen ; https://railwaynews.net/wiki/train-braking-distance-how-long-does-a-train-take-to-stop |
| **Talgo Avril S-106** | 12 passenger cars + 2 power cars; 201.8-201.9 m | **325 t** | **8,800 kW** | — | 300 service (330 certified, 380 design; tested 360) | — | [S] https://en.wikipedia.org/wiki/Talgo_AVRIL |

### Tilt and cant at high speed

| Item | Value | Tag | Source |
|---|---|---|---|
| N700 body tilt | 1° via air springs on R = 2,500 m curves. 270 km/h (vs 250-255 before) on Tokaido | [S]/[P] | https://www.railway-technology.com/projects/n700-shinkansen/ ; https://railwaygazette.com/news/n700-pushes-the-speed-envelope/29774.article |
| N700A on 3,000 m curves | 285 km/h | [S] | https://en.wikipedia.org/wiki/N700_Series_Shinkansen |
| E5/H5 | Up to **1.5°** tilt + full active suspension. Holds **320 km/h on R = 4,000 m** | [S] | https://en.wikipedia.org/wiki/E5_and_H5_Series_Shinkansen ; https://railwaygazette.com/news/jr-east-unveils-series-e5-trainset/34156.article |
| Tilt above 320 | None in service. The 1-1.5° air-spring tilt is the only HSR tilt above 250 km/h | [E] | — |
| Shinkansen maximum cant | **200 mm** (Tokaido, Tohoku) | [S]/[P] | https://pedestrianobservations.com/2023/10/27/setting-speed-zones/ ; https://openjicareport.jica.go.jp/pdf/11633419_18.PDF |
| Shinkansen design rule | R = 11.8·V²/(Cm + Cd). Cm 200 mm, Cd 110 mm (for 300 km/h curves above 3,500 m) | [S] (JICA/Kerala report) | https://openjicareport.jica.go.jp/pdf/12001715_02.pdf |
| China 350 km/h (TB 10621-2014) | Cant ≤175 mm, deficiency 40 mm normal / 60 mm difficult (secondary). Typical R = 7,000 (difficult) to 8,000 m | [S] | https://repository.upnjatim.ac.id/48069/ ; https://www.chinesestandard.net/Related.aspx/TB10621-2009 |
| China 400 km/h study | Min R generally 8,000 m. 7,000 m difficult, 9,000 m preferred | [P] (CREC journal) | https://tdgcxb.crec.cn/EN/Y2022/V39/I5/20 |
| Cross-checks with the formula | 350 km/h, 175 + 40 → R ≈ 6,720 m (≈7,000). 400 km/h, 175 + 40 → ≈8,780 m. 400 km/h, Shinkansen 200 + 110 → ≈6,090 m. 1° tilt ≈ 26 mm and 1.5° ≈ 39 mm of extra effective cant deficiency (1,500 mm base) | [E] | derived |

### Resistance and power at 400 km/h

| Item | Value | Tag | Source |
|---|---|---|---|
| ICE 3 (406 t version 426 t) Davis | A = 3.12 kN, B = 22.4 N/(km/h), C = 0.521 N/(km/h)² (wind-adjusted, column mapping inferred) | [S] | https://annals.fih.upt.ro/pdf-full/2019/ANNALS-2019-1-07.pdf |
| Rough HSR formula | 8.0 + 0.08V + 0.0008V² kN, 600 t train (stated as not real values) | [S] (weak) | https://discuss.amtraktrains.com/goto/post?id=218540 |
| KTX coasting test | B came out negative (-19.5 N/(km/h), 326 t), so fitted B is unreliable | [S] | https://rosap.ntl.bts.gov/view/dot/79083/dot_79083_DS1.pdf |
| Tunnel effect | The C term is larger in tunnels | [S] | https://en.wikipedia.org/wiki/Rail_vehicle_resistance |
| ICE3 coefficients at 400 km/h | ≈ 95 kN → **10.6 MW at the wheel** | [E] | derived |
| With CR450-style -22% resistance | C ≈ 0.40 → ≈ 75 kN → **≈8.3 MW at the wheel**. Matches the CR450 22-23 kWh/km (≈8.8-9.2 MW from the catenary incl. losses and auxiliaries) | [E] | derived |
| Service braking context | EN 15734-1 sets graduated decelerations by speed band (values paywalled). Comfortable HSR service braking 0.6-0.8 m/s². Chinese EB limit 3,700 m from 300 km/h (CRH3 3,319 m) | [P] (scope) / [S] / [P] (Chinese paper) | https://knowledge.bsigroup.com/products/railway-applications-braking-systems-of-high-speed-trains-requirements-and-definitions-1 ; https://forums.dovetailgames.com/posts/320610/ ; https://transport.chd.edu.cn/en/article/doi/10.19818/j.cnki.1671-1637.2011.03.008 |

### Suggested "Gen 6" US 400 km/h (250 mph) train [E]

| Parameter | Value |
|---|---|
| Consist | 8 cars (16 double), 211 m, ~420 t tare / ~470 t loaded, 6M2T or 4M4T with PMSM motors |
| Power at the wheel | 11-12 MW continuous (CR450 ~11 MW; FR1000 9.8 MW) |
| Max tractive effort | 380-400 kN. Starting acceleration 0.75-0.8 m/s² (FR1000 0.7) |
| Davis (loaded) | A ≈ 3.5 kN, B ≈ 20 N/(km/h), C ≈ 0.40 N/(km/h)² open air, ×1.5-2 in tunnels |
| At 400 km/h | Resistance ≈ 75 kN, residual acceleration ≈ 0.05 m/s². 0-350 km/h in ~4.0-4.5 min; 0-400 km/h in ~7-8 min, ~30-35 km |
| Service brake (planning) | 0.6 m/s² above 300 km/h, 0.8 m/s² below 200 km/h (stop from 400 km/h in ~9-10 km) |
| Emergency brake | ≤6.5 km from 400 km/h (≈0.95 m/s²) |
| Curves | Cant 175-180 mm, deficiency 40-60 mm (Chinese rule), R ≥ 8,000-9,000 m for 400 km/h. Optional 1-1.5° air-spring tilt adds ~25-40 mm effective deficiency |
