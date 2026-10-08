# HSR station throat / approach speeds — research notes for the running-time simulator

Date: 2026-10-08. Tags: **[P]** = published by operator / infrastructure manager / national standard;
**[S]** = secondary (Wikipedia, trade press, manufacturer, forum); **[E]** = my estimate.

**How this was gathered:** WebFetch and direct HTTP were blocked by the sandbox proxy for every host I tried
(de.wikipedia.org, hanser.de, stpancras-highspeed.com, railforums.co.uk). So everything below comes from
WebSearch result extracts. Where an extract quotes a primary document (GB 50091, Amtrak Spec 63, CAHSR TMs),
I tag it [P], but I only saw the quoted passage, not the whole document. Approach speeds at specific hubs
are seldom published. Infrastructure managers keep them in sectional appendices or line books (HS1 Sectional
Appendix Table A, SNCF RFN line sheets, DB "La"/Streckenbuch, JR internal ATC tables), so many hub numbers
below are [S]-from-forum or [E].

---

## 1. Turnout geometry vs diverging speed

Rule of thumb from the data below: published diverging speeds correspond to an uncompensated lateral
acceleration of about 0.5–0.65 m/s² on the turnout radius. So **V ≈ 2.9·√R (km/h, R in m)** for small
turnouts and about 2.6·√R for large clothoid turnouts. [E, checked against the rows below]

### Germany (DB) — EW 60 family
| Turnout | Ratio | Diverging speed | Tag | Source |
|---|---|---|---|---|
| EW 60-300-1:9 | 1:9 | 40 (50 curved-frog variants) km/h | [S] | dewiki table (general knowledge, consistent with table) |
| EW 60-500-1:12 | 1:12 | 60 km/h | [S] | https://dewiki.de/Lexikon/Weiche_(Bahn) ; https://drahtkupplung.de/gtbhb2413.html |
| EW 60-760-1:14 | 1:14 | 80 km/h | [S] | dewiki; https://www.oberbau-modellbau.de/weichenhistorie |
| EW 60-760-1:18.5 (Betuwe) | 1:18.5 | 80 km/h | [S] | https://railwaygazette.com/news/pre-assembled-turnouts-cut-installation-times/25309.article ; Hanser textbook table https://files.hanser.de/Files/Article/ARTK_ZCO_9783446448940_0001.pdf |
| EW 60-1200-1:18.5 | 1:18.5 | **100 km/h** | [S] | Hanser table; dewiki; https://forum.stellsi.de/viewtopic.php?t=547 (one modelling site says 70, an outlier) |
| EW 60-2500-1:26.5 fb | 1:26.5 | **130 km/h** (through route 280) | [S] | dewiki Weiche table; Hanser; Polish HS-turnout paper https://pub.pg.edu.pl/pl/download/118555-rozjazdy-do-duzych-predkosci-o-zmiennej-krzywiznie-toru-zwrotnego |
| EW 60-3000/1500 fb (clothoid) | ~1:24 | 100 km/h | [S] | Limburg Süd platform-loop turnouts, dewiki "Bahnhof Limburg Süd" (search extract) |
| EW 60-4800/2450-1:24.26 | 1:24.26 | 130 km/h | [S] | https://als.wikipedia.org/wiki/Weiche_(Bahn) |
| EW 60-6000/3700-1:32.5 fb | 1:32.5 | **160 km/h** | [S] | dewiki Weiche table (another source says 6000/3600-1:36) |
| EW 60-7000/6000-1:42 fb | 1:42 | **200 km/h** (Saalbach junction, 1988) | [S] | dewiki; https://de-academic.com/dic.nsf/dewiki/779495 |
| EW 60-16000/6100-1:40.154 fb | 1:40.15 | 220 km/h design, 200 operational | [S] | https://de-academic.com/dic.nsf/dewiki/381138 |

Note on the question's premise: "1:26.5 at 100 km/h, 1:42 at 160 km/h" is **not** the German pairing.
In German practice 1:18.5/R1200 gives 100 km/h, 1:26.5/R2500 gives 130 km/h, 1:32.5 gives 160 km/h and
1:42 gives 200 km/h.

### France (SNCF / LGV)
| Turnout tangent | Diverging speed | Tag | Source |
|---|---|---|---|
| tg 1/46 (~0.0217) | 160 km/h | [S-forum] | https://www.cheminots.net/topic/19684-vitesse-de-franchissement-d-appareil-de-voie/ |
| tg 1/65 (~0.0154), >230 m long | 220 km/h (230 newest) | [S] | same forum; RailJournal (BPL order, 1/65 >230 m) https://www.railjournal.com/track/turnouts-ordered-for-tgv-bretagne-pays-de-la-loire/ ; Vossloh V-Speed "up to 230 km/h diverging" https://www.vossloh.com/01_product_finder/VCO/VSpeed/FTC23_vspeed_EN_V2_060317.pdf |
| LGV Sud-Est crossovers (148 m switches) | 160 km/h, 78 of them, about one per 20 km | [S] | techno-science / fr.wikipedia LGV Sud-Est extract |
| LGV Sud-Est junctions (Pasilly, Mâcon) | 220 km/h | [S] | same |
| "Entering a station" with 170 km/h diverging costs 2 trains/h of capacity (i.e. high-speed station turnouts are a capacity trade-off) | — | [S] | La Jaune et la Rouge https://www.lajauneetlarouge.com/lappareil-de-voie-element-cle-du-transport-a-grande-vitesse/ |

### Spain (ADIF)
| Turnout | Diverging speed | Tag | Source |
|---|---|---|---|
| DSIH-AV-E-60-3000/1500-1:22 (siding/apartado to main) | 100 km/h | [P] (Ministry study) | https://cdn.transportes.gob.es/portal-web-transportes/ferroviario/estudios_planificacion/madrid-oropesa-tamos-i-ii/documento-n1-memoria-y-anejos/13_instalaciones-ferroviarias_vf.pdf |
| DSIH-G-UIC60-1500-0.042 (~1:24) | 100 km/h | [P] | same |
| SEIH-AV-60-10000/4000-0.0267 (~1:37) | 160 km/h (one passage of the same document says 220) | [P] | same + LAV Madrid–Sevilla renewal tender |
| DSIH-60-17000/7300-1:50 | 220 km/h | [P] | same |

### China (CR "客专" series)
| Turnout | Diverging speed | Tag | Source |
|---|---|---|---|
| No.12 | 45 (50) km/h | [P] | GB 50091-2006 §13.5 http://www.jianbiaoku.com/webarbs/book/430/4837693.shtml |
| **No.18** | **80 km/h** (TB/T 2477 once said 75; reverted to 80) | [P] | GB 50091-2006: "侧向速度 >50 且 ≤80 km/h 的单开道岔应采用18号" ; CRCHI product page https://www.crchi.com/col2464/art/2018/art_2464_124.html ; exam bank https://www.eepw.com/shiti/djd3stiygt0a.html |
| No.42 | 160 km/h | [P/S] | same |
| No.62 (ballastless only) | 220 km/h | [P/S] | same |
| Station practice | **High-speed main to arrival/departure (到发线) uses No.18 at 80 km/h.** No.42/62 are only for junctions and flyovers | [S] (manufacturer citing design rule) | http://www.zhuoligk.com/daocha/tieludaocha.html |

### Japan (Shinkansen) and Korea (KTX)
| Turnout | Diverging speed | Tag | Source |
|---|---|---|---|
| Shinkansen main-to-loop #16/#18 single | ~70 km/h | [S-blog] | https://ameblo.jp/tomo-chacharinmaru/entry-11892729173.html |
| Shinkansen #38 (Takasaki, Joetsu/Hokuriku split) | 160 km/h | [S-blog] | same |
| Conventional JR #16 / #20 | 60 / 70 km/h | [S] | https://x.com/_Railway_Mania/status/1441680061719924736 ; https://jtqsw192.nobody.jp/FIG/300/point123.htm |
| Observed: trains leaving loops at Maibara/Gifu-Hashima stop accelerating at ~70 km/h until clear | — | [S] | same blog |
| Korea F18.5 (R1200) / F26 (R2500) / F46 (R3500) | 90 / 130 / 170 km/h | [S] | https://thewiki.kr/w/건넘선 ; F46/F26 used for loops at Osong, Gimcheon-Gumi and Ulsan: https://koreascience.or.kr/article/CFKO201035738819275.page |

### USA
| Turnout | Diverging speed | Tag | Source |
|---|---|---|---|
| #10 / #15 | 15 / 25–30 mph (24 / 40–48 km/h) | [S] | historical; Amtrak Spec 63 frog list |
| **#20** | **45 mph (72 km/h)** Amtrak; 50 mph (80 km/h) CAHSR "desirable" / AREMA | [P] | Amtrak Spec 63 https://www.amtrak.com/content/dam/projects/dotcom/english/public/documents/corporate/engineering-practices/engineering-specs/amtrak-track-design-specification-63.pdf ; CAHSR TM 2.1.8 https://hsr.ca.gov/wp-content/uploads/docs/programs/eir_memos/Proj_Guidelines_TM2_1_8R0.pdf |
| #24 | ~50 mph (80 km/h) | [S-forum] | https://www.trainorders.com/discussion/read.php?1,743680 |
| #26.5 | 60 mph (97 km/h) | [S] (Wikipedia "Railroad switch", citing FRA) | https://en.wikipedia.org/wiki/Railroad_switch |
| **#32.75** | **80 mph (129 km/h)** | [P] | Amtrak Spec 63 |
| (#45 / #65 equivalents) | ~110 / ~140 mph by the √R rule | [E] | CAHSR TM 1.1.0 asked for ≥110 mph diverging on main-line junctions: http://www.tillier.net/stuff/hsr/TM-1.1.0-Design-Criteria-Initial-Release-R0-070319.pdf |

**CAHSR station rule [P]:** "turnouts connecting the platform track with the main track shall permit speeds
not less than the train would be running if decelerating to or accelerating from the station stop", and the
turnout must be at least 75 ft (23 m) beyond the platform end. (CAHSR Design Criteria ch.4, Rev 0.1 2012,
search extract; see TM 2.1.3 https://hsr.ca.gov/wp-content/uploads/docs/programs/eir_memos/Proj_Guidelines_TM2_1_3R00.pdf)

---

## 2. Intermediate stations: platform loops (stopping trains diverted, through tracks for non-stoppers)

| Station / system | Loop turnout speed | Through track | Tag | Source |
|---|---|---|---|---|
| **Montabaur** (SFS Köln–Rhein/Main) | **100 km/h** diverging at both ends; plus a 130 km/h crossover on each side of the station | 300 km/h | [S] | dewiki Bahnhof Montabaur; https://ice-treff.de/index.php?id=53618&mode=thread |
| **Limburg Süd** | **100 km/h** (60-3000/1500 fb); 1:26.5 crossover (130) to the north | 300 km/h | [S] | dewiki Bahnhof Limburg Süd |
| Same line, operations | In winter ICEs routed via the platform track brake 300 to 100 just before the station | — | [S-forum] | https://ice-treff.de/index.php?id=217793&mode=thread |
| LGV stations (Haute-Picardie, Mâcon-Loché, Lorraine TGV, Meuse TGV, Valence TGV…) | Standard layout is 2 central 300 km/h through tracks and 2 outer loop tracks with side platforms. Loop turnout speed not found; 160 km/h (tg 1/46) assumed | 300–320 | [S] layout / [E] speed | https://en.wikipedia.org/wiki/TGV_Haute-Picardie_station ; https://fr.wikipedia.org/wiki/Gare_de_M%C3%A2con-Loch%C3%A9-TGV |
| China HSR intermediate stations | **80 km/h** (No.18) | 300–350 | [P] | GB 50091; manufacturer design rule above |
| Shinkansen intermediate stations | **~70 km/h** (#16/#18) | 260–320 (Tokaido intermediate stations e.g. Odawara ~ observed 80 entering) | [S] | blog above; railpictures caption "Kodama entering platform track ~80 km/h at Odawara" |
| KTX (Osong, Gimcheon-Gumi, Ulsan) | F46 turnouts (170 km/h class) on the main line at loop connections | 300 | [S] | koreascience paper above |
| Spain apartados / PAETs | 100 km/h (3000/1500-1:22). Junctions 160–220 | 300 | [P] | Ministry study |

**Distance from turnout to platform.** No hard published number was found except CAHSR's minimum of 75 ft past
the platform end [P]. Physical reasoning [E]:
- A 100 km/h turnout needs ~770 m of braking to a stop at 0.5 m/s² (551 m at 0.7). With a 400 m platform
  and the stop mark near the far end, the turnout sits **~300–500 m before the platform start**. That matches
  Montabaur/Limburg-type layouts, where loops are ~1.0–1.3 km between the outer switches. [E]
- An 80 km/h turnout (China/Japan) gives ~500 m braking, so the turnout is ~100–300 m before the platform. [E]
- A 160 km/h turnout gives ~2 km braking, so the turnout is ~1.5 km out. That is only worth it if the loop is
  long and capacity matters (cf. the La Jaune et la Rouge remark on the cost of 170 km/h station entry). [E]
- The restriction must hold until the **tail** of the train clears the turnout (add train length, 200–400 m)
  when departing. On arrival it rarely binds, because the train is braking anyway. [E]

---

## 3. Hubs and approaches

| Hub | Value | Tag | Source / note |
|---|---|---|---|
| **Paris-Nord** | 60 km/h on all surface tracks; the approach area (avant-gare) is >4 km long with many flyovers; LGV Nord starts at Arnouville/Gonesse, 16.6 km out | [S] | https://areq.net/lang/fr/Gare_de_Paris-Nord.html ; LGV Nord wiki |
| **Paris-Est** | TGVs use 22.5 km of classic line to Vaires; observed entry to the 26-platform station at ~30 km/h | [S] (driver's-eye video blurb) | https://www.videoscene.co.uk/strasbourg-to-paris-drivers-eye-view ; https://www.railway-technology.com/projects/lgv_est/ |
| **Paris-Montparnasse / LGV Atlantique** | Vanves–Massy 200 km/h, Massy–Villejust 220, then 300 after the Villejust tunnel | [S] | techno-science LGV Atlantique https://www.techno-science.net/definition/14898.html |
| **Paris-Gare de Lyon** | LGV SE first segment pK −0.168 to 1.784 at 160 km/h, then 270/300; Paris–Lieusaint on the classic line (≤160) | [S-fan wiki] | https://routes.fandom.com/wiki/LGV_Paris-Sud-Est |
| Lyon Part-Dieu, Lille Europe | Lille Europe has 2 through tracks (non-stop, gated) plus 4 platform tracks; Eurostar through the Lille tunnel at 200 km/h. Throat speeds not found | [S] | https://en.wikipedia.org/wiki/Lille-Europe_station |
| **Frankfurt Hbf** (terminus) | Entry up to 60 km/h depending on route (since the 2005 ESTW); 30 km/h only near the platform end / buffer | [S-forum] | https://ice-treff.de/index.php?id=145678&mode=thread |
| **Köln Hbf** | Hohenzollern bridge partly 30 km/h only (the SFS link avoids it); a 20 km/h Zs3 for occupied-track entry | [S] | dewiki SFS Köln–Rhein/Main; https://wiki.railsignalling.org/ (Köln Hbf local knowledge) |
| German large-station throats generally | 60 / 40 / 30 km/h | [S-forum] | stummiforum thread (search extract) |
| **Berlin Hbf (tief)** | North–South mainline incl. Tiergarten tunnel max 120 km/h; platform throat not found | [S] | https://en.wikipedia.org/wiki/Berlin_North%E2%80%93South_mainline |
| **Stub-track rule (DB Ril 408)** | Entry into a stub track without overlap ≤ **30 km/h** (20 on very short stubs; 40 in ex-DR areas e.g. Leipzig Hbf) | [S] (driver training site) | https://www.tf-ausbildung.de/BahnInfo/gleisabschluesse.htm ; https://forum.zusi.de/viewtopic.php?t=12399 |
| **Brussels-Midi** | "All tracks are 40; Thalys drivers usually ≤30 over 40 km/h switches" | [S-OSM comment, weak] | https://www.openstreetmap.org/user/Eimai/changeset_comments/ |
| **Amsterdam Centraal** | 40 km/h tagged on station tracks; NL ATB yellow aspect = 40 | [S-OSM] | https://www.openstreetmap.org/way/513172775 |
| **London St Pancras (HS1)** | Domestic 225 / international 230 km/h Ebbsfleet–St Pancras; tunnels 230 for aerodynamics; forum: **60 km/h out of St Pancras, 200 just inside the tunnel mouth, 230 from KP6**. Official values are in Sectional Appendix Table A p.A7 (could not read) | [P] line speed / [S-forum] throat | HS1 Network Statement https://stpancras-highspeed.com/wp-content/uploads/2025/10/HS1-Network-Statement-2027-October-2025-Update.pdf ; Sectional Appendix https://stpancras-highspeed.com/wp-content/uploads/2025/01/sectional-appendix-to-the-hs1-rule-book-ref-c-02-os-05-2002.pdf ; https://www.railforums.co.uk/threads/hs1-maximum-permitted-speeds-between-st-pancras-and-stratford.75923/ |
| UK terminal practice | ~30–35 mph throat, 15 mph into terminal platforms (generic drivers' rule of thumb) | [S-forum] | https://www.railforums.co.uk/threads/approach-speeds-and-speed-limits-at-stations-and-platforms.215193 |
| **Madrid Atocha** | 15 stub tracks; RCF generic 30 km/h rules; no published throat speed found | [S] | es.wikipedia Puerta de Atocha; BOE-A-2018-285 |
| Madrid Chamartín | Rebuilt to 12 through HSR tracks (2026); speeds not found | [S] | El Español 2026-06-02 |
| **Tokyo (Tohoku side)** | Tokyo–Ueno 110 km/h; Tokyo–Ōmiya 110 (Ueno–Ōmiya 130 nominal) | [S] | https://en.wikipedia.org/wiki/T%C5%8Dhoku_Shinkansen |
| **Tokaido Shinkansen stations** | Full-length trains reach the **platform end at ~70 km/h** (Nikkei, on JR raising station-entry speed to cut stopping time); Tokyo–Shin-Yokohama urban section ~100–170 limits; Nagoya/Kyoto areas raised from 170 to 230 | [S] | https://www.nikkei.com/article/DGXZQOUD2526M0V20C23A2000000/ ; https://railwaygazette.com/high-speed/speed-increase-on-the-tokaido-shinkansen/40661.article ; https://shinkansen.tabiris.com/speed.html |
| Shinkansen ATC steps | Old ATC-1: 210/160/110/70/30/0; later 285/270/230/170/120/70/30/0. **70 = turnout step, 30 = final platform step**. ATC-NS (2006) uses a continuous single-stage curve | [S] | https://en.wikipedia.org/wiki/Automatic_train_control ; https://trafficnews.jp/post/61664/ |
| Shin-Osaka | 8 tracks (3 island + 2 side platforms); speeds not found | [S] | jrailpass blog |
| **Beijing South (Jing-Jin intercity)** | Approach has a 45 / 80 / 120 km/h stepped profile over the first ~5 km; Tianjin throat 45 (No.12) | [S-Zhihu] | https://zhuanlan.zhihu.com/p/52034629 |
| China generic | Side-route through HSR stations ~80 (No.18); older/underground stations with No.12 at 45 | [S] | Zhihu answers (search extract) |
| **Taiwan HSR** | European turnouts throughout; "end-area restrictions in the 60–140 mph range" (97–225 km/h) at the Taipei/Nangang and Zuoying ends; elsewhere 300 with no intermediate restrictions | [S-forum, George Harris] | https://discuss.amtraktrains.com/goto/post?id=979707 |
| Seoul / KTX | Approaches on shared conventional lines (Seoul–Siheung); turnout table above. Throat not found | — | — |

---

## 4. Synthesis

1. **Platform-loop turnouts at intermediate stations** cluster tightly: 70–80 km/h in Japan and China
   (#16/#18), 90 km/h in Korea (F18.5), 100 km/h in Germany and Spain (1:18.5 R1200, 3000/1500), and
   probably ~160 km/h in France (1/46, unconfirmed). In US terms that is a **#24–#26.5 at 50–60 mph**.
   Platform screen doors make high-speed loop entry safer but do not change the turnout limit.
2. **Hubs** step down in stages: an urban approach zone of 110–230 km/h, 5–20 km long (Tokyo–Ueno 110,
   Paris–Massy 200, Paris-Nord avant-gare >4 km, HS1 London tunnels 230), then a throat of 40–60 km/h
   (Paris-Nord 60, Frankfurt 60, Brussels/Amsterdam 40) over the last ~1–2 km, because of crossovers and
   slips (1:9 to 1:12). Shinkansen hubs end with a 70 km/h then 30 km/h ATC staircase, ~70 km/h at the
   platform end.
3. **Stub terminals** add a buffer rule: 30 km/h (DB Ril 408; 40 in ex-DR areas; UK ~15–25 mph) for the
   final approach into the stub platform, applied from roughly the platform start or the last turnout.

Braking reference at 0.5 m/s² service braking [E]: 30 km/h → 69 m; 40 → 123 m; 60 → 278 m; 80 → 494 m;
100 → 772 m; 130 → 1,304 m; 160 → 1,975 m.

---

## 5. Recommendation for the simulator

| Station type | Throat limit | Applies from | Justification |
|---|---|---|---|
| **Hub (through or many-platform)** | Approach zone **160 km/h (100 mph)**, then throat **60 km/h (35–40 mph; use 60 km/h = 37 mph)** | Approach: **8 km** before the platform start. Throat: **1.5 km** before the platform start, held over the whole platform | Paris-Nord 60 on all station tracks [S]; Frankfurt 60 [S]; Tokyo–Ueno 110 / Paris–Massy 200 approach zones [S]; Tokaido ~70 at the platform end [S]. A modern purpose-built hub (Beijing South / Shin-Osaka style) could justify 80 km/h. |
| **Intermediate with platform loops** | **100 km/h (60 mph)** diverging (US #26.5 ≈ 60 mph; DB 1:18.5 R1200) | Turnout **400 m** before the platform start (loop ≈ platform + 2×400 m). On departure, held until the tail clears the far turnout | Montabaur and Limburg Süd 100 [S]; ADIF 100 [P]; KTX 90, China 80 [P], Shinkansen 70 [S]. A 100 km/h turnout ≈ its own braking distance to a stop at the far end of a 400 m platform, so it costs almost nothing. Through tracks stay at line speed. |
| **Stub terminal** | Throat **60 km/h (37 mph)**, then **30 km/h (20 mph)** final approach to the buffer | Throat: **1.5 km** before the platform start. 30 km/h: from the **platform start** (~400 m before the buffer stop, with the stop mark 10–20 m short of the buffer) | DB Ril 408 stub rule 30 km/h [S]; Frankfurt 60 then 30 [S]; St Pancras 60 km/h exit [S-forum]; UK 15–25 mph terminal practice [S]. |

Option flags [E]: allow 130 km/h (80 mph, US #32.75 / DB 1:26.5) loop turnouts placed ~1 km out for
"premium" intermediate stations. Allow an 80 km/h hub throat for greenfield hubs with only #18–#20 turnouts.
