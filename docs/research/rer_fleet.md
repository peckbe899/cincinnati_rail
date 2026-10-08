# Cincinnati RER fleet: research on the real rolling stock behind it

Purpose: set the parameters for a physics-based running-time simulator.
Research date: 2026-10-08.

## Method and limits (read first)

- **WebFetch did not work in this session.** Every domain failed DNS resolution, and direct curl was blocked by the egress proxy. All data came from **WebSearch result summaries** of the pages cited. The numbers are attributed to those URLs, but nobody read them on the page itself. For any value the simulator depends on, check the page before relying on it.
- **The WebSearch budget ran out** (shared limit of 200 per turn) before the dwell-time, door-cycle and jerk research was finished. Section 11 therefore relies partly on engineering background knowledge. That material is marked **[BK]**: estimated, with no URL verified in this session.
- Tags:
  - **[P]**: published, meaning it appears in the cited source.
  - **[E]**: my estimate or calculation, with the method given.
  - **[BK]**: background engineering knowledge, not verified this session.
- Default loaded-mass method [E]: empty mass + (seats + standees) × 75 kg.
  - Standees are taken at about 4 per m² unless the source gives a figure.
  - Rotating-mass allowance is +6–10% for EMUs.
- Default tractive-effort estimate [E]: F ≈ m_loaded × a_start × 1.08, plus resistance.

---

## 1. Budd/CB&Q "Pioneer Zephyr" (1934): stainless, articulated, diesel-electric

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 3 cars, articulated on Jacobs-type shared trucks (4 trucks). Cars: power/RPO, baggage/buffet/coach, coach/observation | P | https://en.wikipedia.org/wiki/Pioneer_Zephyr |
| Length | 197 ft 2 in = 60.10 m (power car about 74 ft, rear car about 63.5 ft) | P | https://en.wikipedia.org/wiki/Pioneer_Zephyr ; https://www.american-rails.com/9900.html |
| Empty mass | 208,061 lb = 94.4 t | P | https://en.wikipedia.org/wiki/Pioneer_Zephyr |
| Capacity | 72 seats, plus 25 long tons of baggage/mail | P | same |
| Loaded mass | about 100 t with passengers only; up to about 125 t with the full 25.4 t of mail and baggage | E | 94.4 + 72×0.08; mail figure from Wikipedia |
| Prime mover | Winton 8-201-A two-stroke diesel, 600 hp (ASME), later quoted as 660 hp (490 kW). Drives a 600 V DC generator | P | https://www.asme.org/about-asme/engineering-history/landmarks/58-pioneer-zephyr ; https://www.inventionandtech.com/landmark_landing/80342 |
| Traction | 2 traction motors on 1 motor truck (front); 36 in (910 mm) drive wheels | P | https://en.wikipedia.org/wiki/Pioneer_Zephyr |
| Power at wheel | about 330–390 kW | E | 448–490 kW engine × about 0.75–0.8 (generator, motors, auxiliaries) |
| Max tractive effort | about 60–80 kN, adhesion-limited | E | Only 2 driven axles carrying about 30–35 t; μ ≈ 0.22–0.25 |
| Starting acceleration | about 0.5–0.7 m/s² at very low speed; about 0.3 m/s² at 50 km/h | E | From the TE and power figures above at about 100 t |
| Max speed | 112.5 mph (181 km/h) reached on the 1934 "Dawn-to-Dusk" run; average 77.6 mph over 1,015 mi | P | https://en.wikipedia.org/wiki/Pioneer_Zephyr ; rarenewspapers archive cited by the search |
| Brakes | air brakes (period equipment); rate not found | – | – |
| Doors | none found | – | – |
| Gearing | not found | – | – |

**Simulator note: electric articulated equivalent [E]**

- Treat it as a 3-section articulated EMU about 60 m long, about 95 t empty, about 105 t loaded.
- Power-to-mass is only about 4 kW/t. That is very low against modern EMUs at 15–25 kW/t.
- For a fictional electric version with "Zephyr styling", a modern-equivalent rating of 1,000–1,500 kW (about 12 kW/t) with 4 motored axles is more realistic. That would give about 0.8 m/s².
- Keep the 94 t and 60 m as the body and mass basis.

---

## 2. Budd Silverliner I/II and GE Silverliner IV (PRR/Reading/SEPTA single-deck EMU cars)

### Silverliner II (Budd, 1963)

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | Single cars, double-ended, MU-capable. Not articulated | P | https://en.wikipedia.org/wiki/Budd_Silverliner |
| Length | 85 ft = 25.91 m | P | same |
| Empty mass | about 101,400 lb = 46.0 t | P | same ; https://www.flickr.com/photos/widecab/albums/72157632407881200/ |
| Capacity | 124 seats (with lavatory) or 127 (without), 3+2 seating. Flickr album gives 127/129 | P | same |
| Loaded mass | about 56 t (127 seated plus about 50 standees) | E | |
| Power | 550 hp = 410 kW (4 × 137.5 hp motors) | P | Wikipedia / Flickr (as above) |
| Max TE | about 60–70 kN | E | 56 t × 0.76 × 1.08 + margin |
| Acceleration | 1.7 mph/s = 0.76 m/s² (family figure) | P | https://en.wikipedia.org/wiki/Silverliner |
| Max speed | 100 mph design; 85 mph (137 km/h) in service | P | Budd Silverliner (Wikipedia) |
| Service brake | about 2.0–2.5 mph/s = 0.9–1.1 m/s². Dynamic brake plus air | E | US practice for 1960s MU cars |
| Doors | 2 single-leaf end doors per side, with traps (low/high platforms). Width about 0.9 m | E | Same layout as the IV (below) |
| Supply | 11–13.5 kV 25 Hz AC | P | Silverliner IV page (same network) |

### Silverliner IV (GE/AVCO, 1973–76) for comparison

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | Single cars and married pairs | P | https://en.wikipedia.org/wiki/Silverliner_IV |
| Length | 85 ft (25.9 m) | P | same |
| Empty mass | 120,600 lb = 54.7 t | P | same |
| Capacity | 155 total (about 125 seated) | P (total) / E (seats) | same |
| Loaded mass | about 66 t | E | 54.7 + 155×0.075 |
| Power | 550 hp (410 kW) per Wikipedia. A forum claims 4 × 160 hp GE 1259A = 640 hp (477 kW) | P / forum | same ; https://railroad.net/silverliner-iv-horsepower-t82386.html |
| Acceleration | about 0.7–0.9 m/s² (no IV-specific figure found) | E | |
| Max speed | 100 mph (160 km/h) | P | same |
| Brakes | pneumatic plus dynamic; rate not found. Est. 1.0 m/s² service | P / E | same |
| Doors | 2 single-leaf pocket end doors per side, with traps | P | same |
| Supply | 11–13.5 kV 25 Hz AC | P | same |

**Context [P]**

- The Silverliner V reaches 3 mph/s (1.34 m/s²) up to 30 mph, and 110 mph maximum. https://en.wikipedia.org/wiki/Silverliner_V
- SEPTA's RFP for the Silverliner IV replacement specifies 3 mph/s and 100 mph. https://philadelphiatransitvehicles.info/?p=5982

---

## 3. SNCF Z 5100 (Paris-suburban stainless EMU, built by the Budd licensee Carel-Fouché)

Correction to the brief: the Z 5100 is a **1953–58** design, not 1960s. The 1960s stainless suburban EMU is the **Z 5300** (1965–75), given below.

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | M + ZS (2 cars), later M + ZR + ZS (3) or M + 2R + ZS (4). One motor car only. Not articulated | P | https://fr.wikipedia.org/wiki/Z_5100 ; https://docrail.fr/les-automotrices-inox-de-la-sncf/ |
| Length | 2 cars 45.70 m; 3 cars 68.50 m; 4 cars 91.3 m | P | same ; http://www.trains-europe.fr/sncf/automoteurs/z5100.htm |
| Empty mass | 2 cars 93.8–94.8 t; 3 cars 128 t (motor car 57 t, ZR 30 t); 4 cars 158–162 t. Techno-science gives 130 t (3 cars) and 183 t (4 cars) | P (sources conflict) | as above ; https://www.techno-science.net/fr/definitions/z-5100 |
| Capacity | 3 cars: 408 places (Docrail) | P | Docrail |
| Loaded mass | about 160 t (3 cars) | E | 128 + 408×0.078 |
| Power | 880–890 kW (4 × SW 8304 motors, Bo'Bo' on the motor car) | P | fr.wikipedia ; techno-science |
| Max TE | about 100–110 kN, adhesion-limited (57 t over 4 axles, μ ≈ 0.2) | E | |
| Acceleration | "high accelerations" as M+R; worse once trailers were added. About 0.6 m/s² (2 cars), about 0.45 m/s² (3 cars) | P (qualitative) / E | techno-science ; Docrail |
| Max speed | 120 km/h | P | same |
| Brakes | **no electric brake**; air only. Est. 0.8–0.9 m/s² service | P / E | techno-science |
| Doors | not found. Est. 2 double sliding doors per side per car, about 1.3 m | E | |
| Supply | 1.5 kV DC | P | same |

### Z 5300 ("petit gris", 1965–75), the true 1960s equivalent

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 4 cars, 1 motor car (some cut to 3 cars) | P | https://www.techno-science.net/fr/definitions/z-5300 |
| Length / mass | 103.55 m / 153.5 t (4 cars); 78.45 m / 123.5 t (3 cars) | P | same |
| Capacity | 880 places, 388 seated | P | same |
| Loaded mass | about 220 t (4 cars) | E | |
| Power / TE | 1,180 kW one-hour rating; 147 kN | P | same |
| Acceleration | about 0.6 m/s² empty, about 0.55 m/s² loaded (TE-limited) | E | 147/(220×1.08) |
| Max speed | 120 km/h | P | same |
| Doors | 3 per side per car, double-leaf sliding | P | same |
| Supply | 1.5 kV DC | P | same |

---

## 4. DB Class 420 (S-Bahn EMU, 1969)

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 3 cars, all motored (12 motored axles, 12 × 200 kW). Not articulated | P | https://www.igsbahn-muenchen.de/et420.shtml ; https://de.wikipedia.org/wiki/DB-Baureihe_420 |
| Length | 67.40 m over couplers; width 3,080 mm | P | de.wikipedia |
| Empty mass | 129 t (de.wikipedia current). An older mirror and IGS give about 139–139.8 t (steel end cars 49 t, light-alloy middle car 41 t) | P (sources conflict) | de.wikipedia ; https://dewiki.de/Lexikon/DB-Baureihe_420 ; IGS |
| Service mass | 144 t (de.wikipedia); 129–135 t (Bahn-Galerie); 138 t (db-loks) | P | https://www.bahn-galerie.de/Elektro_TW/94-80-0420/Baureihe_420.htm ; http://www.db-loks.de/tfz/420.html |
| Capacity | 192 seats + 266 standing (de.wikipedia). IGS gives 194 seats; 254 standing at 4/m², 381 at 6/m² | P | as above |
| Loaded mass | about 165 t at 4/m²; about 175 t at 6/m² | E | 130 + (194+254)×0.075 |
| Power | 2,400 kW (12 × 200 kW). db-loks gives this as continuous at 72 km/h; Wikipedia calls it the one-hour rating | P | db-loks ; IGS |
| Max TE | about 180–190 kN | E | 165 t × 1.0 × 1.08 + resistance. As a check, 2,400 kW at 72 km/h corresponds to about 120 kN |
| Starting acceleration | **1.0 m/s², 0–60 km/h** (IGS, db-loks); 0.96 m/s² (de.wikipedia). Measured in Frankfurt: mean 0.96, range 0.6–1.3 m/s² | P | IGS ; https://tuprints.ulb.tu-darmstadt.de/175/3/Kap_3_Randbed.PDF |
| Max speed | 120 km/h | P | same |
| Service brake | 0.9 m/s² from 120 km/h with electric brake (IGS); 0.7 m/s² pneumatic only, 0.95 m/s² electric + pneumatic (de.wikipedia). Rheostatic brake; air brake blends in below about 55 km/h | P | IGS ; de.wikipedia |
| Emergency brake | about 1.1–1.2 m/s² | E | |
| Magnetic track brake | not found in the sources searched; treat as **none** | – | |
| Doors | **4 double doors per side per car** (24 per side per unit); width 1,300 mm. Early cars have sliding doors, later cars (420 400 on) plug-sliding | P | de.wikipedia ; https://www.oepnv-info.de/reisen/bahnreisen/informationen-zur-barrierefreiheit-und-ausstattung-von-zuegen/fahrzeuginformationen-nahverkehr/et-420-s-bahn-muenchen ; https://www.deutschebahn.com/resource/blob/12718434/1d8209a8f9988aabb1906506f81ab536/DB-420_421____03-2011-data.pdf |
| Floor height | 1,030 mm above rail (high floor; level with 96 cm S-Bahn platforms) | P | oepnv-info |
| Wheels | 850 mm new / 780 mm worn | P | db-loks |
| Supply | 15 kV 16.7 Hz AC | P | de.wikipedia (standard DB) |

---

## 5. NSW/Sydney "V set" (Comeng intercity double-deck, 1970–89; retired January 2026)

Correction to the brief: the V-set bodies are **stainless steel**, not aluminium (Transport for NSW, Wikipedia).

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 4-car set: DM + T + T + DM (2 sets coupled to make 8). Not articulated | P | https://en.wikipedia.org/wiki/New_South_Wales_V_set |
| Car length | 23,968 mm (driving motor), 23,965 mm (trailer). Set length about 95.9 m | P | https://transportnsw.info/travel-info/ways-to-get-around/train/fleet-facilities/v-set-trains |
| Width / height | 2,928 mm / 4,382 mm | P | same |
| Car mass | driving motor 59–61 t; trailer 40 t | P | same |
| Set empty mass | about 200 t (4 cars) | E | 2×60 + 2×40 |
| Capacity | 96 seats (driving cars), 112 (trailers), reversible seats; about 416 seats per 4 cars | P | Wikipedia mirror https://wiki.krisyotam.com/content/wikipedia_en_all_nopic_2026-03/V_Set ; transportnsw |
| Loaded mass | about 240 t (416 seated + about 100 standing) | E | |
| Power | per motor car 4 × 134 kW = 536 kW (DCF); 4 × 150 kW = 600 kW (DCM/DIM); 4 × 170 kW = 680 kW (DJM/DKM chopper). About 1,200 kW per 4-car set | P | https://www.mitsubishielectric.com.au/product/australian-rolling-stock-v-set/ ; Wikipedia |
| Max TE | about 120–140 kN (8 motored axles about 60 t each pair) | E | |
| Starting acceleration | about 0.5 m/s² (about 5 kW/t loaded) | E | |
| Max speed | 115 km/h in service; 130 km/h design and trial (from 1987) | P | https://www.loco-info.com/view.aspx?id=12624 ; Wikipedia |
| Service brake | about 0.8 m/s² | E | |
| Doors | end-vestibule layout, about 2 doors per side per car. Interior stairs up and down from the vestibule | E | layout from photos and general knowledge; count not found |
| Control | camshaft resistance control (1977–85); GTO chopper (1986–89) | P | Mitsubishi |
| Supply | 1,500 V DC | P | Mitsubishi |

---

## 6. RATP/SNCF MI 84 (Z 8400; RER A at first, then RER B), single-deck

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 4 cars: M + R(AB) + R(B) + M. Units run in pairs (8 cars) | P | https://www.trains-europe.fr/divers/ratp/z8400.htm |
| Length | 104.16 m per 4-car unit; width 2.80 m; height 4.18 m | P | same |
| Empty mass | 208 t (other values given: 205 t, 200 t). An MI 79/84 data sheet lists 205.6 t and 283.1 t without labels; **283.1 t is very likely the loaded mass** | P (conflict) / E | trains-europe ; https://fr-academic.com/dic.nsf/frwiki/1094821 ; http://fbrisou.free.fr/RAIL21/FicheZ8100.pdf |
| Capacity | MI 79: 312 seats + 112 folding seats, about 843 total. MI 84 has about 15% fewer seats and more standing | P | https://en.wikipedia.org/wiki/MI_79 ; https://en.wikipedia.org/wiki/MI_84 |
| Loaded mass | about 270–283 t | E | |
| Power | 2,480 kW (1.5 kV DC); 2,820 kW (25 kV AC); chopper control | P | trains-europe ; en.wikipedia MI 84 |
| Max TE | about 300 kN | E | 280 t × 1.0 × 1.08 |
| Starting acceleration | **1.0 m/s² from 0 to 40 km/h** (specified load) | P | https://en.wikipedia.org/wiki/MI_84 ; fr-academic |
| Max speed | 120 km/h (the MI 79 is 140 km/h) | P | fr-academic / wikiland |
| Service brake | 1.10 m/s² full service | P | en.wikipedia MI 84 |
| Emergency brake | 1.20 m/s². The MI 84 dropped the rheostatic brake for regenerative braking by motor self-excitation | P | same ; https://docplayer.fr/90331469-Z-8100-mi79-z-8400-mi84.html |
| Doors | 4 double sliding doors per side per car (wide doors, about 1.3 m) | P (count) / E (width) | trains-europe ; fbrisou |
| Floor | high floor, level with RER platforms (about 1.1 m). Not found | E | |
| Supply | 1.5 kV DC + 25 kV 50 Hz AC | P | |

**SACEM context [P]**

- SACEM (in-cab speed control with moving-block-like spacing) entered service on RER A in **September 1989**.
- It allows about 30 trains/h (2-minute headway) in the peak direction on the central trunk, and 24 trains/h in the other direction. Spacing is under 90 s in stations and under 2 min in tunnels.
- In practice, central-section dwells of up to 50 s limited throughput.
- Theoretical RER dwell is about 30 s; peak dwells at Châtelet-Les Halles are 50–60 s.
- The MI 79 and MI 84 were bought in the same era, partly to relieve wear on the MS 61.
- Sources: https://en.wikipedia.org/wiki/SACEM_(railway_system) ; https://en.wikipedia.com/wiki/RER_A ; https://pedestrianobservations.com/2024/08/24/more-on-american-incuriosity-new-york-regional-rail-edition-part-2-station-dwell-times/

---

## 7. Alstom Coradia Duplex: SNCF TER 2N NG (Z 24500 / Z 26500)

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | Z 24500: 2–3 cars; Z 26500: 4–5 cars. Double-deck cars on conventional bogies (not articulated). Each car has 1 motor bogie (2 × FXA 2851 asynchronous motors) | P | https://en.wikipedia.org/wiki/SNCF_Class_Z_26500 ; https://www.techno-science.net/definition/15493.html |
| Length | 107.5 m (4 cars); 133.9 m (5 cars). Width 2.806 m; height 4.30 m | P | techno-science ; https://www.trains-europe.fr/sncf/automoteurs/z24265.htm |
| Empty mass | 4 cars 250–260 t; 5 cars 310 t; 3 cars 193 t | P | techno-science ; https://simutrans.fr/doku.php?id=en%3Ater2nng ; en.wikipedia |
| Capacity | about 450 seats (4 cars); about 570 (5 cars) | P | en.wikipedia |
| Loaded mass | about 300 t (4 cars, 450 seated + about 150 standing) | E | |
| Power | 3,200 kW (4 cars) or 4,000 kW (5 cars) at 800 kW per car (techno-science, trains-europe). Wikipedia gives 3,400 / 4,250 kW (850 kW per car) | P (conflict) | as above |
| Max TE | about 310 kN (4 cars) | E | 300 t × 0.95 × 1.08 |
| Starting acceleration | **0.95 m/s²** | P | https://nl.wikipedia.org/wiki/SNCF_TER_2N_NG ; https://hu.wikipedia.org/wiki/Alstom_Coradia_Duplex |
| Max speed | 160 km/h | P | |
| Emergency brake | 1.15 m/s² | P | nl.wikipedia |
| Service brake | about 0.9–1.0 m/s² | E | |
| Doors | 2 per side per car; 1,300 mm wide | P | techno-science ; nl.wikipedia ; https://fr.wikipedia.org/wiki/Z_24500 |
| Floor height | 600 mm boarding level (a 1,050 mm variant exists for CFL) | P | nl.wikipedia ; hu.wikipedia |
| Supply | 1.5 kV DC + 25 kV 50 Hz | P | |

### Regio 2N (Bombardier, now Alstom; Z 55500) for comparison

This is the articulated design, alternating double-deck and single-deck cars.

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 6 / 7 / 8 / 10 cars, articulated | P | https://en.wikipedia.org/wiki/Regio_2N ; https://fr.wikipedia.org/wiki/Bombardier_R%C3%A9gio2N |
| Length | 80.9–135.4 m (8 cars about 110 m) | P | same ; https://www.trains-europe.fr/sncf/automoteurs/porteur_hyper_dense.htm |
| Mass | 6 cars 240 t, 7 cars 269 t, 8 cars 329 t, 10 cars 387 t (simulator site, not authoritative) | P (weak) | https://simutrans.fr/doku.php?id=en%3Aregio2n |
| Power | 2,400 kW (6–7 cars); 3,200 kW (8 cars) | P | as above |
| Acceleration 0–50 km/h | 0.78 / 0.67 / 0.59 (or 0.79) / 0.48 (or 0.58) m/s², by length (Bombardier datasheet) | P | http://www.horizonemployeur.fr/wordpress/wp-content/uploads/2018/06/bombardier-transportation-Regio-2N-datasheet-fr.pdf |
| Max speed | 160 km/h (200 km/h for the V200 variant) | P | |
| Doors | single-deck intermediate cars: 2 pairs per side; end cars: 1 pair. About 1.6 m wide (fr infobox lists "Portes 1,60") | P / E | en.wikipedia ; fr.wikipedia |
| Seats | 350–770 (8 cars, e.g. 515) | P | |

---

## 8. DB Class 423 (S-Bahn EMU, 1998+)

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 4 cars, **articulated**: Bo'(Bo')(2')(Bo')Bo'. Jacobs bogies at the 3 inner joints; 2.7 m bogie wheelbase | P | https://en.wikipedia.org/wiki/DBAG_Class_423 ; https://de.wikipedia.org/wiki/DB-Baureihe_423 |
| Length | 67.40 m | P | same |
| Empty mass | 105.0 t; service mass 119.4 t; 18 t axle load. Schaeffler gives 109 t | P | de.wikipedia (citing Lurz) ; https://www.schaeffler.com/remotemedien/media/_shared_media/08_media_library/01_publications/schaeffler_2/datasheet_1/downloads_4/ds_wl_07506_de_de.pdf |
| Capacity | 192 seats + 352 standing | P | Schaeffler ; Wikipedia |
| Loaded mass | about 146 t | E | 105 + 544×0.075 |
| Power | 2,350 kW (8 water-cooled asynchronous motors); regenerative | P | de.wikipedia |
| Max TE | about 160–170 kN | E | 146 × 1.0 × 1.08 |
| Starting acceleration | **1.0 m/s²** | P | de.wikipedia |
| Max speed | 140 km/h. The EBA once cut the permitted speed over braking performance (Bundestag answer, 2011) | P | de.wikipedia ; https://dserver.bundestag.de/btd/17/066/1706681.pdf |
| Service brake | 0.9 m/s² | P | de.wikipedia |
| Emergency brake | about 1.1–1.2 m/s² | E | |
| Magnetic track brake | not confirmed in the sources searched. [BK]: probably fitted on the unpowered Jacobs bogie (unverified) | – | |
| Doors | **3 double plug-sliding doors per side per car** (12 per side per unit); 1,300 mm wide | P | Wikipedia ; https://www.bahn-galerie.de/Elektro_TW/94-80-0423/Baureihe-423.htm |
| Floor / boarding height | 995 mm entry; high floor, near-level with 96 cm platforms | P | bahn-galerie |
| Supply | 15 kV 16.7 Hz AC | P | |

---

## 9. Stadler KISS

### Caltrain KISS (7-car, revenue service 2024)

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 7 double-deck cars (contracted as 6 + option). Not articulated: each car on its own bogies | P | https://www.railjournal.com/fleet/first-caltrain-kiss-double-deck-emu-completed/ ; https://www.railwayage.com/passenger/intercity/for-caltrain-16-kisses-from-stadler-but-no-flirts/ |
| Length | 157.1 m (6 cars, 2016 figure); 7 cars about 183 m | P / E | Railway Age ; https://caltrain-hsr.blogspot.com/2016/09/emu-brochure.html |
| Mass | 946,000 lb = 429 t (7 cars; unclear whether empty or operating). Blog estimate for 6 cars: about 340 t empty | P (unclear basis) / E | https://en.wikipedia.org/wiki/Caltrain_Modernization_Program ; Caltrain HSR blog |
| Seats | 573 (6 cars, brochure via blog); about 668 for 7 cars | P / E | Caltrain HSR blog |
| Loaded mass | about 520–540 t. The blog infers 540 t from 540 kN at 1 m/s² | E | |
| Power at wheel | **6,000 kW** max (8 traction motors) | P | https://rollingstockworld.com/passenger-cars/caltrain-introduces-the-kiss-double-deck-emus-by-stadler-for-california/ |
| Max TE | **540 kN** starting | P | same |
| Starting acceleration | **1.0 m/s²** | P | same |
| Max speed | 110 mph (177 km/h) design; 115 mph reached in tests at TTC; **79 mph (127 km/h)** in Caltrain service | P | Railway Age ; https://www.railwayage.com/news/caltrain-emu-under-way-to-ttci/ |
| Brakes | not found. Est. 1.0 m/s² service, 1.2–1.3 m/s² emergency. US FRA Tier I alternative-compliance vehicle | E | |
| Doors | low-level doors for 8-inch platforms (with steps up to the lower deck); provision for high doors. A fan source says the high doors became emergency exits. Count not verified; est. 2 per side per car, about 1.3 m | E | https://steamcommunity.com/sharedfiles/filedetails/?id=2974651568 (fan) |
| Floor | generic KISS: entry 570 mm, lower deck 440 mm. Caltrain platforms 8 in, with 25 in planned | P | https://en.wikipedia.org/wiki/Stadler_KISS ; https://www.caltrain.com/media/2783/download |
| Supply | 25 kV 60 Hz AC | P | Railway Age |

### Lighter European KISS: SBB RABe 511 (6 cars, 2010–12)

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 6 cars, Bo'Bo' + 2'2' + 2'2' + 2'2' + 2'2' + Bo'Bo'. Only the 2 end cars are motored | P | https://de.wikipedia.org/wiki/SBB_RABe_511 |
| Length | 150 m; width 2.80 m | P | same |
| Empty mass | 297 t (6 cars); 211.9 t (4 cars) | P | same |
| Capacity | 535 seats (120 1st + 415 2nd) + 838 standing = 1,373 | P | same |
| Loaded mass | about 400 t | E | 297 + 1,373×0.075 |
| Power | 4,000 kW continuous; 6,000 kW short-time | P | same |
| Max TE | 400 kN (up to 54 km/h) | P | same ; https://hellertal.startbilder.de/bild/schweiz~triebzuege~rabe-511-dosto/644686/der-sbb-rabe-511-021-94.html |
| Starting acceleration | 1.1 m/s² (empty or partially loaded; about 0.9 m/s² at full load by 400 kN / 432 t equivalent) | P / E | |
| Max speed | 160 km/h | P | |
| Doors | est. 2 double doors per side per car, about 1.3 m, low-floor entry about 570 mm | E | |
| Supply | 15 kV 16.7 Hz AC | P | |

---

## 10. Stadler FLIRT single-deck suburban

### SBB RABe 523 (4 cars, articulated with Jacobs bogies)

| Item | Value | Tag | Source |
|---|---|---|---|
| Formation | 4 cars, articulated (5 bogies; the 2 outer bogies are motored) | P | https://de.wikipedia.org/wiki/SBB_RABe_523 ; https://www.trainsimulator.ch/en/sbb-rabe-523-flirt.html |
| Length | 74.07–74.08 m | P | http://www.juergs.ch/eisenbahn/triebzuege/rabe-523/ |
| Empty mass | 120–121 t | P | same |
| Capacity | about 181 seats (20 1st + 161 2nd); standing about 200 at 3–4/m² | P (seats, simulator source) / E | trainsimulator.ch |
| Loaded mass | about 150 t | E | |
| Power at wheel | 2,000 kW continuous; 2,600 kW max | P | SBB GmbH FLIRT datasheet: https://www.sbb-deutschland.de/wp-content/uploads/PDF/downloads/datenblatt_flirt.pdf |
| Max TE | 200 kN up to 47 km/h | P | same |
| Starting acceleration | **1.2 m/s²** (datasheet); 1.0 m/s² in the simulator data | P | same |
| Max speed | 160 km/h | P | |
| Brakes | not found. Est. 1.0–1.1 m/s² service, about 1.3 m/s² emergency. [BK]: magnetic track brakes are usual on FLIRT trailer Jacobs bogies (unverified) | E | |
| Doors | 1,320 mm wide; est. 2 per side on intermediate cars and 1–2 on end cars (about 6–8 per side per unit) | P (width) / E (count) | juergs.ch |
| Floor | 570–580 mm low-floor entry (level with 55 cm platforms); 1,120 mm high floor over the bogies | P | same |
| Supply | 15 kV 16.7 Hz AC | P | |

- FLIRT family range: acceleration 0.8–1.3 m/s². FLIRT 3 TE about 175 kN. https://www.wikipedia.org/wiki/FLIRT

### NSB Type 75 (5 cars) for comparison

| Item | Value | Tag | Source |
|---|---|---|---|
| Length | 112.7 m (Type 74: 105.5 m) | P | https://www.loco-info.com/view.aspx?id=14981 ; https://en.wikipedia.org/wiki/Norwegian_State_Railways_rolling_stock |
| Power | 4,500 kW per the NSB table; loco-info gives 3,000 kW one-hour and 2,000 kW continuous | P (conflict) | as above |
| Mass | about 235 t (Wikipedia table, unlabelled column); Type 74 about 170 t empty (loco-info) | P (weak) | as above |
| Seats | 295 2nd class (2+3 seating) | P | Wikipedia |
| Max speed | 200 km/h | P | |
| Supply | 15 kV 16.7 Hz | P | |

---

## 11. Cross-cutting parameters

### 11.1 Door cycle times [mostly BK / E]

- **Door opening:** about 2.5–3.5 s for plug-sliding doors and 2–3 s for pocket sliding doors [BK].
- **Door closing:** about 3–4 s plus a 2–3 s warning tone. Closing and lock-proving before traction release take another 1–2 s [BK].
- **Typical fixed overhead per stop:** about 8–12 s (open, close, lock-proving, driver reaction).
  - Douglas's Sydney dwell model uses a **fixed 10 s term** plus boarding and alighting terms (power law with exponent 0.7, per door). [P] https://australasiantransportresearchforum.org.au/wp-content/uploads/2022/03/2009_Coxon_Burns_deBono_Napper.pdf
- **Suggested simulator defaults [E]:**

| Class type | Door overhead per stop |
|---|---|
| Modern plug doors (423, FLIRT, KISS, Coradia) | 9 s |
| 1960s–80s sliding doors (420, MI 84, Z 5300) | 7–8 s |
| US trap-door end vestibules (Silverliner), low platforms with traps | 12–15 s |

### 11.2 Boarding and alighting rates: single-deck vs bilevel

- **Literature review [P]:** alighting 0.4–2.6 pax/s and boarding 0.3–2.1 pax/s per door, depending on width, crowding and level access. https://www.tandfonline.com/doi/full/10.1080/01441647.2021.1887960
- **Bilevel penalty [P, second-hand]:** double-deck stock is about **0.3 s per passenger slower** than single-deck (Harris & Anderson 2002, cited in Coxon et al. 2009, ATRF). URL as above.
- **Sydney modelling [P]** (Parsons Brinckerhoff, via ABC fact-check):
  - Double-deck dwell is 35 s at suburban stations and 70 s in the CBD.
  - At Town Hall, single-deck cuts dwell from 70 to 60 s. Part of that comes from fewer passengers per metre of train.
  - https://www.abc.net.au/news/2014-04-11/barry-ofarrell-sydney-trains-claim-doubtful/5371446
  - https://majorprojects.planningportal.nsw.gov.au/prweb/PRRestService/mp/01/getContent?AttachRef=EXH-104%2120190305T115941.868+GMT
- **Paris RER A [P]:**
  - The MI 2N holds up to 2,600 per train, against 1,887 for the MS 61.
  - The MI 09 has 3 wide level doors per side per car but still does not match single-deck egress times.
  - Peak dwells at Les Halles are 50–60 s.
  - https://en.wikipedia.org/wiki/MI_2N ; https://en.wikipedia.org/wiki/MI_09 ; https://pedestrianobservations.com/2018/01/04/dont-run-bilevels/
- **Caltrain:** no measured KISS dwell data found. The current KISS boards from 8-inch platforms up steps, so expect boarding times like the gallery/bilevel cars, not level boarding.
- **Suggested per-passenger service times, per door [E]:**

| Door type | Time per passenger |
|---|---|
| Single-deck, 1.3 m double door, level boarding (423, FLIRT, MI 84) | 0.6–0.8 s |
| Bilevel with internal stairs, 1.3 m door, level or near-level (Coradia Duplex, Regio 2N, MI 2N-like) | 0.9–1.1 s (the +0.3 s penalty) |
| Bilevel with end vestibule (V set) or steps from low platforms (Caltrain KISS on 8-inch platforms) | 1.2–1.6 s |
| US single-leaf trap doors (Silverliner) | 1.5–2.0 s |

### 11.3 Jerk limits [BK]

- Typical EMU service jerk limit is **0.5–1.0 m/s³**.
  - Common design value: 0.7–0.8 m/s³ for traction and service-brake changes.
  - Metros sometimes allow up to 1.0–1.3 m/s³.
  - Emergency braking is not jerk-limited beyond brake build-up time. Pneumatic build-up is about 1.5–3 s; magnetic track brakes act almost immediately.
- **Suggested simulator default:** 0.75 m/s³. Not verified in this session; check against EN 13452 / EN 14531 or operator specifications.

---

## 12. Summary table (key numbers)

Empty / loaded mass is per train as listed. Loaded mass is [E] unless marked.

| Train | Formation | Empty / loaded mass (t) | Power (kW) | Start accel (m/s²) | Vmax (km/h) | Service brake (m/s²) |
|---|---|---|---|---|---|---|
| Pioneer Zephyr | 3-car articulated | 94.4 P / about 100 E | about 450–490 engine P; about 360 at wheel E | about 0.5 E | 181 record P | about 0.8 E |
| Silverliner II | 1 car | 46.0 P / about 56 | 410 P | 0.76 P (family) | 137 svc / 161 design P | about 1.0 E |
| Silverliner IV | 1 car | 54.7 P / about 66 | 410 P (477 forum) | about 0.8 E | 161 P | about 1.0 E |
| Z 5100 | 3 cars (1 motor car) | 128 P / about 160 | 880 P | about 0.45 E | 120 P | about 0.85 E (no electric brake P) |
| Z 5300 | 4 cars (1 motor car) | 153.5 P / about 220 | 1,180 P (147 kN P) | about 0.55 E | 120 P | about 0.85 E |
| DB 420 | 3 cars, all motored | 129–139 P / about 165 | 2,400 P | 1.0 (0–60) P | 120 P | 0.9 P |
| V set | 4 cars (2M2T) | about 200 P (per car P) / about 240 | about 1,200 P | about 0.5 E | 115 svc / 130 design P | about 0.8 E |
| MI 84 | 4 cars (2M2R) | 208 P / about 283 P? | 2,480 (1.5 kV) / 2,820 (25 kV) P | 1.0 (0–40) P | 120 P | 1.10 P (emergency 1.20 P) |
| Z 26500 Coradia Duplex | 4 cars | 250–260 P / about 300 | 3,200–3,400 P | 0.95 P | 160 P | about 0.95 E (emergency 1.15 P) |
| Regio 2N | 8 cars, articulated | about 329 P (weak) / about 380 | 3,200 P | 0.59 (0–50) P | 160 P | about 0.9 E |
| DB 423 | 4 cars, articulated | 105 P / about 146 | 2,350 P | 1.0 P | 140 P | 0.9 P |
| Caltrain KISS | 7 cars | 429 P? (basis unclear) / about 530 | 6,000 P (540 kN P) | 1.0 P | 127 svc / 177 design P | about 1.0 E |
| SBB RABe 511 KISS | 6 cars | 297 P / about 400 | 4,000 cont / 6,000 P (400 kN P) | 1.1 P | 160 P | about 1.0 E |
| SBB RABe 523 FLIRT | 4 cars, articulated | 121 P / about 150 | 2,000 cont / 2,600 P (200 kN P) | 1.2 P | 160 P | about 1.0 E |
| NSB Type 75 FLIRT | 5 cars, articulated | about 235 P (weak) | 3,000–4,500 P (conflict) | about 1.0 E | 200 P | about 1.0 E |
