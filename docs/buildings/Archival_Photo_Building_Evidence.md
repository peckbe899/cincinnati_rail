# Pinned archival photos as building evidence: recommendation

Status: research only. Nothing was built or measured. Every accuracy and hours figure below is an estimate unless a URL sits beside it. The error budgets are review arithmetic from stated assumptions, not published tests. "Search text" means the page itself was blocked and only search-result text was read. "Recalled, unverified" means it comes from memory and was not checked this session.

## 1. The short answer

- Do it, but as measurement, not reconstruction. Pin each photo thenthere-style, link it to its lot, read a checklist, and measure on the wall plane by ratio.
- What a photo fixes best is what the eye catches in a city model. In order: storey count, roof form, roofline steps between neighbours, ground floor kind, facade grammar, floor split ratios. Absolute height comes last.
- Absolute height from a photo is only as good as its scale. On a one-building frontal photo expect 0.6 to 1.2 m on a 12 m wall. That may be no better than Sanborn storeys times era floor heights, which is estimated at 1.0 to 1.5 m and has not been measured. Measure that baseline first. It needs no photos.
- A full camera solve is the exception. Use it only when a surviving building or other control with vertical extent is in frame, or for points off the wall plane.
- Check lost-building heights against independent sources: stereo aerials from before 1960 if a pair covers the West End, and shadows on a single frame if not.
- Do not plan on multi-view or feed-forward 3D (VGGT, MASt3R and the like) for ordinary buildings. Most have one photo. Keep it for landmarks with 10 or more photos, if any exist. Nobody has checked whether any do.
- Do not let a vision model write values yet. Use it later as a proposer, scored against your own labels first.
- Photos do not give depth, rear ells or roofs hidden behind parapets.
- The largest cost is not in this plan: traced Sanborn footprints with house numbers. Every route needs them and none exist in the repo. An outside layer may exist (section 3).
- New this round: the Library of Congress has public-domain scans of Cincinnati Sanborn volumes corrected to 1949-50. That is very likely the right base for 1959 photos.

## 2. What thenthere.io is, and what to copy

It is a 2D map pinboard for old home videos and photos. It is video-first. It does no 3D and solves no camera. A photo's "pose" is a point, a whole-degree bearing and a cone width of 15 to 120 degrees, default 60 (verified in the bundle, https://thenthere.io/assets/index-DHcnfjSf.js). It runs on Mapbox GL with Mapbox satellite, not Google (https://thenthere.io/assets/MapboxCanvas-DK20cJ-O.js). It is tiny: 21 videos and 5 photos on 25 Nov 2026 (https://thenthere.io/api/memories?mediaType=photo&limit=500). Nobody had changed the default cone. Its terms forbid reusing other people's media, so copy the idea and none of the content.

Copy:
- Pin, draggable bearing handle, cone. Seconds per photo.
- Date precision (day, month, year, decade). Add an earliest and latest date.
- "Suggested" versus "confirmed" on every machine-filled value.
- "Stand here": fly the 3D camera to the photo station.
- Normalised image coordinates for points clicked on the photo.

Do not copy: the cone as if it were a field of view, the `filmedAt` field (a noon placeholder), the checkbox-only rights model, or the user crop without a stored crop box.

Add what it lacks: holder and call number, separate "may store" and "may display" flags, scan size and crop box, the uncropped scan with film edges where one exists, the view type (frontal, oblique, shifted lens), the scale source used, the buildings shown, the values each photo set, and a solved camera where one was made.

The pin map needs a basemap. Use the hub's own map with the georeferenced Sanborn on top and, if obtained, a 1949 orthophoto. No Mapbox satellite, Google or Apple imagery is needed.

Treat the cone as a search prior only: it lists which footprints a photo can see.

One idea thenthere suggests that the draft missed: motion film. See section 4.

## 3. The images that exist

| Collection | Holder | Size | Years | Coverage | Location key | Access | Rights | Confidence |
|---|---|---|---|---|---|---|---|---|
| Kenyon-Barr (SC#115, from news credits) | Cincinnati History Library and Archives (CHLA), Cincinnati Museum Center | 2,700, "over 3,000" or 3,298; sources differ (https://muse.jhu.edu/article/573059/summary, https://www.wcpo.com/news/insider/finding-kenyon-barr-photo-exhibit-brings-razed-west-end-community-back-to-life) | 1959, maybe some 1958 | Every structure and lot in the clearance area (search text) | Signboard with date and plot number (https://aeqai.org/signs-of-erasure-finding-kenyon-barr-at-ucs-meyers-gallery/). Sign in most frames, not confirmed for all. Catalogue citations seen take the form "Kenyon Barr project # 18-1581 (SC#115-604)". Address in press captions. Address in every record: unverified | Partly online; share, resolution, API unverified (https://www.cincymuseum.org/photograph-film/) | City work, not public domain by default. Unverified | Medium. Search text only |
| George Rosenthal | Same | About 3,600 (https://www.citybeat.com/news/echoes-of-a-lost-west-end-12219411/) | 1957 to 1959 | West End | Unverified | Unverified | Undetermined | Low. 35mm, lower resolution |
| City Engineer, subway and street improvements | UC Archives | Over 8,000 (https://libapps.libraries.uc.edu/liblog/2012/10/cincinnati-subway-and-street-images-digitization-project/) | About 1916 to 1957 | Job streets only | Written on the photo: unverified | Scanned, online (search text) | City work, no statement found | Medium |
| HABS/HAER | Library of Congress | 990 catalogue hits; 112 for Dayton Street. These are catalogue records, not photo counts (https://www.loc.gov/pictures/search/?q=cincinnati&co=hh&fo=json) | Mostly 1970s to 1990s (recalled, unverified) | Surviving West End and OTR types | Address in title. Search by street name: "cincinnati west end" returns 14 hits, mostly Union Terminal (https://www.loc.gov/pictures/search/?co=hh&q=cincinnati+west+end&fo=json) | JSON API, TIFFs | No known restrictions on US Government images (https://www.loc.gov/pictures/item/oh0436/?fo=json) | High, verified |
| FSA/OWI | Library of Congress | 595 hits; 122 Mydans | 1935 to 1943 | Slum housing | Weak | JSON API | Federal | High for counts |
| Detroit Publishing | Library of Congress | 169 hits | 1900 to 1920 | Downtown street walls | Street in title | JSON API | Pre-1931 | High for counts |
| Stereographs | Library of Congress | 322 records matching "cincinnati" (https://www.loc.gov/pictures/search/?co=stereo&q=cincinnati&fo=json) | 1866 to 1904 in the first titles | Fountain Square, suspension bridge; some records are not Cincinnati | Title | JSON API | Not checked | Low value for the West End. Short baseline, depth at close range only. Possible for pre-1904 downtown |
| Panoramas | Library of Congress | 13 records (https://www.loc.gov/pictures/search/?q=cincinnati&co=pan&fo=json) | Not checked | Riverfront, business district, a ballpark. None of the West End in the titles seen | Title | JSON API | Not checked | Low |
| Enquirer archive | Public Library | 1 to 2 million, sources differ: "over 1 million" (https://chpl.org/enquirer-archive/); "over 2 million physical images" (https://storymaps.arcgis.com/stories/901372bb6dc2410686448e568964b467, search text) | 1945 to 1995 or 2005 | City-wide | Captions | Online share ("over 10,000") not re-verified | Copyrighted | Low |
| USGS vertical frames | USGS EROS | Rolls 15 to 17 seen for 3 May 1949. A third-party count gives 1,359 USGS frames near the county, 1937 to 1989 (unverified) | 3 May 1949, 1:14,000, 152.3 mm lens (https://earthexplorer.usgs.gov/scene/metadata/full/5e83d8e4870f4473/AR1IP0000170149/) | Basin; West End stereo pair unverified | Frame centre | Free login. Fine scans $30 a frame plus $5, 3 to 4 weeks, and only if the film is still at EROS (https://www.usgs.gov/centers/eros/science/usgs-eros-archive-aerial-photography-aerial-frequently-asked-questions-faqs). Scan micron size unverified | Probably federal, unconfirmed | Medium. Search text only |
| 1956 Hamilton County flight | Agency unknown | Index entry only, in LSU's photomosaic index list (https://www.lsu.edu/cic/collections/aerial/mosiac.php, search text) | 1956 | County | None | Whether stereo film survives is unknown | Unknown | Low. If film survives it is three years before clearance and beats 1949 |
| ODOT aerial archive | Ohio DOT | Over 500,000 images (search text, no URL captured) | 1946 on | State; West End before 1960 unverified | Unknown | Unverified | Unverified | Low |
| UC Urban Database mosaics | UC | 1932, 1956, 1977 (https://www.uc.edu/cdc/urban_database/historical.html) | | Central city | None | PDFs | Unverified | Low. Mosaics, not stereo |
| Highway obliques | Ohio History Connection | Unknown (https://aspace.ohiohistory.org/subjects/8992) | 1949 to 1971 | Includes Cincinnati; West End unverified | Unknown | Digitisation unverified | Unverified | Low |

Known, not used, and why:

| Source | Why not used yet |
|---|---|
| Greater Cincinnati Memory Project, pre-1940, several institutions (https://cc-pl.org/?p=886) | Pointer only. Not opened |
| Felix Koch, over 5,000 prints, Museum Center (unverified) | Coverage and access not checked |
| Ransohoff, 30,000, Museum Center (unverified) | Same |
| County Auditor 1968 downtown set, 544 or 554 photos (unverified) | After clearance. Useful for downtown survivors only |
| 29 April 1949 aerial on Flickr; 1949 aerial at UC Archives | Single images, source and rights not checked |
| Cincinnati in Motion, the Museum Center's scale model | Scale, decade and West End coverage unverified. Bunker Hill used a period model for colour |
| Hillside panoramas from Price Hill, Fairview, Mt. Adams | Nobody searched for them. See section 4 |
| Archival motion film | Nobody searched for it. See section 4 |

Sanborn editions. LOC has online, public-domain scans of Cincinnati Sanborn volumes corrected to 1949-50. This was verified per item. Example: https://www.loc.gov/item/sanborn06645_027/ (Vol. 4, 1904 to Apr 1949, 110 images, JP2 6438 x 7795 px, TIFF master). Each item's rights line reads "The content of the Library of Congress online Sanborn Maps Collection is in the public domain and is free to use and reuse." Online: 1934 Vol. 2; 1937 Vols. 5, 6, 11; 1950 Vols. 3 to 10 where loaded. Not online: Vol. 1 of 1934 and Vol. 1 of 1950, both noted "Map of congested district", so probably the downtown core. Two items failed to load. Vols. 3 and 4 are the 1904 sheets with corrections to 1949-50, on the sheet layout the repo already georeferenced. Which volume covers the West End is unchecked: open the key map. List: https://www.loc.gov/collections/sanborn-maps/?fa=location:cincinnati&fo=json

Traced footprints from outside. Way Back West End links a Lower West End ArcGIS StoryMap with a GIS layer of 1890s buildings drawn from georeferenced Sanborn maps (https://waybackwestend.org/projects/). A CinTIMHA Lower West End reference file also uses georeferenced Sanborns. Neither was read (hosts blocked). Coverage, date and licence are unknown.

Written records that give dimensions with no photo. None was found. All are worth one email to CHLA, UC Archives and the City:
- The City's Kenyon-Barr appraisal and acquisition files. Federal urban renewal projects normally describe each structure (recalled, unverified). They would also hold the project-number-to-parcel key.
- County Auditor property record cards before 1968. The library's house-history guide points to auditor records from 1937.
- A WPA Real Property Survey of the 1930s. The Bunker Hill precedent used one.
- City building permits.

Renumbering. Cincinnati renumbered its streets in 1895-96. The only known index (Graver and Mullen) stops at Freeman Avenue, east of most of Kenyon-Barr. This does not affect 1959 photos on 1904 or later Sanborns. It does affect any pre-1896 photo or caption and the 1887 and 1891 Sanborns.

## 4. The methods considered

| Method | Verdict | Yields | Realistic accuracy |
|---|---|---|---|
| Pinning ladder: block, lot, point and bearing, cone | Use | The right photo on the right building; a coverage map of lost buildings with no photo | Lot linking by caption works elsewhere: OldNYC reports 87% placed and 96% correct, the author's own New York figures (https://danvk.org/2026/03/08/oldnyc-updates.html). For Kenyon-Barr it depends on records carrying an address. If they carry only a project or plot number, it needs a parcel key that was not found |
| Facade reading by eye (checklist) | Use on every photo | Storeys, bays, cornice kind, window kind, visible roof form, style, ground floor kind | Good on a clear photo. Half storeys are a judgement call. Untested with a second reader |
| Wall-plane measurement by ratio | Use. This is the core | First: floor split ratios, parapet and cornice as a fraction of wall height, window proportions, roofline steps between neighbours in one frame. Second: absolute height where the scale is good | Ratios and steps: 2 to 3% or 0.1 to 0.2 m, because scale error is common to both ends. Absolute height: 0.6 to 1.2 m with single-frontage scale, about 0.3 m with block-face scale, on a 12 m wall. No published test. See the error budget in section 5 |
| Brick-course counting | Use where the scan allows | A vertical scale that needs no map, focal length or principal point: height = courses x course height | Needs about 3 px per course, so about 22 mm per px on the wall or better. A 4,000 px scan of a 15 m view gives 3.75 mm per px. A 1,000 px web JPEG gives 15 mm per px, which is marginal. Course height about 67 mm with joint (recalled, unverified; 19th century Cincinnati brick varied). Calibrate on OTR survivors. Spread perhaps 3 to 5%. No published test searched |
| Full single-photo camera solve | Exception only | Off-plane points: ridge behind the eave, setbacks, rear ells. Several buildings in one oblique frame | Ground-only control is weak (section 5). Example: a ridge 5 m behind the wall, with 15% range error at 15 m, adds about 0.45 m |
| Facade parsing and vision-language models | Do not use yet. Later, as a proposer only | Draft values for review | No benchmark on pre-1960 monochrome photos. Modern figures only: Munich storeys 81.2% exact and 97.9% within one floor (https://arxiv.org/abs/2505.18021). Another study reports about 70% average agreement with experts over three attributes on modern Google Street View images; the figure is not in the abstract and is unverified (https://arxiv.org/abs/2607.14756). It is no evidence for archival photos. The CMP training set has no string course, hood or bay class (https://cmp.felk.cvut.cz/~tylecr1/facade/) |
| Row propagation to twins | Use, labelled `inferred` | Values for unphotographed neighbours of the same width, storeys and material | No precedent paper found. Copies errors, so only from values that passed checks |
| Multi-view and feed-forward 3D | Landmarks only | Poses and a coarse cloud for massing and roof form | Untested on historical street photos. On sparse modern photos, pose AUC@5 is 29 to 37 out of the box (https://arxiv.org/html/2604.22714; figures not re-checked). No building is known to have 10 or more photos. Several weights are non-commercial |
| Archival motion film | Not searched. Worth one search | A film from a moving streetcar or car is a dense image sequence from one camera. That is what structure-from-motion needs and what scattered stills are not | Nothing found, nothing ruled out. Candidates: streetcar-fan films (streetcars ran until 1951; recalled, unverified), newsreels, TV station film (WCPO, WLWT, WKRC), city urban renewal films |
| Pre-1960 stereo aerials | Use as an independent check, after a cheap test | A roof height per footprint, rear ells, flat or pitched roof, "standing on the flight date" | By hand, roof minus street: 1.67 x GSD x parallax error x 1.41. Scale 1:14,000 and a 152.3 mm lens give a flying height of 2,132 m. A 9 inch frame at 60% overlap gives a base of about 1,280 m, base to height 0.6. At a 25 micron scan (0.35 m GSD): 0.4 m at half a pixel, 0.8 m at one pixel. At a 63 micron scan (0.89 m GSD): 1.0 to 2.1 m. So 1 m by hand holds only on fine scans. Scan size, 9 inch format and 60% overlap are unverified. Automatic matching is biased low, not just noisy: a 12 m building 100 mm off nadir leans 7.9 m on the ground and hides half of a 15 m street, streets are in shadow, and matchers smooth across the canyon. Expect per-block bias correction from hand points. No published dense-city result on 1940s film; one study found 1940s film gave poorer surfaces (https://www.sciencedirect.com/science/article/abs/pii/S0305440316300528) |
| Shadows | Cross-check. Needs one frame only | Roofline profile of a whole row where its shadow falls into a street or open lot. Depends on street bearing and time of day | On 3 May the noon sun at Cincinnati is about 66.6 degrees high. A 12 m wall throws 5.2 m at noon and 6.9 m at 60 degrees, which fits a 12 to 18 m street. A 1 to 2 pixel edge error at 0.35 m GSD gives 0.6 to 1.2 m of height at 60 degrees and 0.8 to 1.6 m at noon. Call it 1 to 1.5 m absolute. Relative steps along one row: about 0.5 m. Solve sun angle from shadow azimuth and check it on survivors. No test on 1949 film |
| Hillside panoramas | Not searched. Use for roof form if they exist | Roof form and height for many blocks at once, from Price Hill, Fairview or Mt. Adams | None found. The LOC panoramas seen do not show the West End |
| Aerial obliques and bird's-eye views | Use for roof form if they exist | Roof form and ridge direction per block | Existence and digitisation unconfirmed. Lithographed views are "not drawn to scale" (https://www.loc.gov/item/75694914/): presence and landmarks only |

Height means different things in different sources. Pin this before any cross-check.

| Source | Top it measures | Base it measures | Offset to expect |
|---|---|---|---|
| Ground photo | Eave or parapet top on the street wall | Sidewalk at the facade, if visible. Stoops, raised basements and areaways confuse it | Reference |
| Lidar `h_70p` per part (spec 7.4) | Roof surface statistic | Lidar ground | Above the eave on a pitched roof. 0.3 to 1 m below the parapet top on a flat roof |
| Stereo aerial | Roof surface, or the ridge | Street or open lot, picked by hand | Same as lidar roof surface, unless the parapet line is measured by hand |
| Shadow | The edge that casts: parapet, eave or ridge | The ground the shadow lands on | Depends on roof form |
| Storeys x floor height | Top of the top floor | Ground floor level | Misses parapet and raised basement, 0.3 to 1 m |

Spec 7.4 defines `height_m` as wall top above the base but sources it from `h_70p`. That mismatch is about the size of any pass mark.

Tools to read before writing anything:
- Smapshot (MediaComem/smapshot-api, BSD-3 per search text) is a working "thenthere with a solved camera". It has posed 150,000 to 200,000 images, sources differ. moniQue (smfloery/moniQue) solves a camera from clicked points and reports per-point uncertainty. Both target terrain, not wall planes. Their point rules and fit to wall planes were not read (github.com blocked).
- fSpy (open-source vanishing-point camera matcher), GeoCalib and Perspective Fields may already do the calibration seeding. Recalled, unverified.
- Hand stereo candidates: e-foto, QGIS with a stereo plugin, MicMac's manual point tools. Recalled, unverified. None searched.

Precedent: Kartta Labs modelled 333 buildings from photos across 8 Manhattan blocks. It traced over 1,000 footprints across several map years, so that is not 1,000 distinct buildings and the two numbers are not a yield rate. The authors call the result preliminary (https://arxiv.org/pdf/2010.06536; figures not re-checked). Every scaled project found uses map footprint first, rules second, photos third. No 3D model of the West End was found. Single-view metrology (Criminisi, Reid and Zisserman, about 2000) is the standard reference for measuring heights from one image (recalled, unverified).

## 5. The recommended method

One pipeline. Each value carries a source label and never overwrites a Sanborn value silently.

| # | Step | Fills | Source label on the value |
|---|---|---|---|
| 1 | Ingest catalogue rows and scans to a local folder. Record hash, pixel size, crop box, rights flags. Ask for the uncropped negative scan with film edges for any photo that will get a solved camera | Photo record only | Holder and call number |
| 2 | Link to lot: parse the caption address, join to Sanborn house numbers, one click to confirm. Fallback: if records carry only a project or plot number, the join needs the City's Kenyon-Barr parcel or acquisition map. Not found. Ask CHLA and the City | `evidence[]` on the building | "photo, lot link confirmed" |
| 3 | Rough pin: suggest a station across the street facing the facade. Drag if wrong | Point, bearing, cone | "suggested" until confirmed |
| 4 | Checklist on every linked photo, with a "cannot tell" option | `stories` (as a check), bays, `piers`, `string_courses`, `cornice.kind`, window kind, hood, sill, `facade.ground`, `style`, visible `roof.form` | "photo 1959, read by eye" |
| 5 | Classify the view: frontal, oblique, or shifted lens. Shifted lens means verticals are parallel and the horizon is not at mid-height | View type on the photo | Read by eye |
| 6 | Measure on the wall plane by ratio. No camera solve. Store ratios and roofline steps as their own observations | Floor split, parapet and cornice fractions, window proportions, steps between neighbours | "photo 1959, ratio" |
| 7 | Set scale from the ladder below and convert to metres where the rung is good enough | `height_m`, `floor_h_m`, `roof.parapet_m`, cornice `h_m`, `shopfront_h_m`, window `w_m` and `h_m` | "photo 1959, plane measure, scale rung X, plus or minus sigma" |
| 8 | Full camera solve, only when control with vertical extent is in frame or an off-plane point matters | Photo pose with residuals; ridge and setback heights | Solver, RMSE, control ids |
| 9 | Aerial check. Ground by hand at intersections and open lots, with a ground surface fitted per block. Do not take "roof minus adjoining street" from an automatic surface. Co-register on stable ground only (hillsides, OTR, surviving landmarks), because Queensgate was cleared and regraded and automatic alignment to a modern surface will fail there | Second height, `parts[]` flags, roof flat or pitched, date | "aerial <date>, RMSE from survivors" |
| 10 | Shadow check on rows whose shadow falls into a street or open lot | Roofline steps along the row, rough height | "shadow <date>, sun angle from azimuth" |
| 11 | Level the block: one good absolute height plus relative steps from photos and shadows | `height_m` on neighbours | "levelled from <id>" |
| 12 | Twin propagation | Same fields on matching neighbours | "photo of neighbour <id>", `inferred` |

Scale ladder, best first. Record the rung on every value.

| Rung | Scale source | Needs | Sigma on a 12 m wall |
|---|---|---|---|
| a | A surviving building or other object of known height in frame | A survivor. Rare in the West End | Depends on the object |
| b | Block-face length in an oblique view | Focal length constrained, or a vertical control length | About 0.3 m from scale (60 m with 1.4 m combined end error is 2.3%), plus the focal term below |
| c | Brick-course count | About 22 mm per px or better; course height calibrated on OTR | About 0.4 to 0.6 m (3 to 5%) |
| d | A single frontage | Sanborn frontage width | 0.6 to 1.0 m (5 to 8%) |

Other in-frame scale objects to ask about: the Kenyon-Barr signboard, if its size is standard or one survives at the museum and it stands at the wall; 1950s cars of known wheelbase; door leaves; kerbs. Each is weak alone. A signboard of known size at the wall would give scale in every frame. Not verified.

Why "block face only" was dropped. Kenyon-Barr frames are described as one structure or lot per frame, so most are near-frontal views of one or two frontages. A block-face rule would refuse metres on most of the core collection.

Error budget for a height. Assumptions: 12 m wall, 6 m frontage, 15 m range, camera 1.5 m above ground. Review arithmetic, not a published test.

| Term | Size | Effect on a 12 m wall | Note |
|---|---|---|---|
| Click error | 2 px at 15 mm per px (1,000 px across a 15 m view) | 0.03 m | Negligible |
| Lens distortion, 1950s normal lens | Under about 0.5% (recalled, unverified) | About 0.04 m at the frame edge | Negligible |
| Lens distortion, 35mm wide angle | 1 to 2% (recalled, unverified) | 0.1 to 0.2 m | Small |
| Scale from a single frontage | 0.3 to 0.5 m relative width error on 6 m, so 5 to 8% | 0.6 to 1.0 m | The limit for most frames |
| Scale from a block face | 1.4 m on 60 m, so 2.3% | 0.3 m | Oblique views only |
| Scale from brick courses | 3 to 5% | 0.4 to 0.6 m | Needs a fine scan |
| Oblique view, principal point unknown on a cropped print | Principal point 10 to 20% of frame width off centre; 10 to 30% focal error in weak geometry | 0.6 to 1.2 m at 45 degrees | Fixed by a vertical control length or an uncropped scan |
| Ground-only control in a full solve | 0.15 m error in 1950s grade or kerb height is 10% of camera height | About 1.2 m | Why the full solve is the exception |
| Wall base definition | Stoop, raised basement, areaway | 0.3 to 1 m if mixed up | Store the base with every height |
| Sanborn sheet shift | 1 to 2.5 m, common to the sheet | None | Cancels in heights. Moves the camera station only |
| Baseline: storeys x era floor height | About 0.3 m per floor, correlated, plus parapet and basement | 1.0 to 1.5 m | Estimate. Measure it |

So 0.5 m needs scale good to 4%. A single frontage cannot give that. Pixel size and distortion matter only for whether brick courses can be counted.

Rules by view type:
- Frontal. Skip the camera solve. A frontal view of a wall is a similarity, so height to width ratio holds whatever the focal length. Focal length from vanishing points is ill-conditioned here and is not needed.
- Oblique. Control on the footprint fixes scale along the wall but not the vertical to horizontal ratio. That comes from focal length and principal point. Require at least one vertical control length (a survivor, or brick courses). Otherwise carry a principal point term of 10 to 20% of frame width through the Monte Carlo.
- Shifted lens (view camera with rising front: HABS, and possibly the 1959 survey camera). The vertical vanishing point is at infinity and the principal point is far from centre by design. Never apply a centre prior. Plane measurement only.
- Where a centre prior or vanishing-point seeding is used, it is standard practice, recalled, not sourced this session.
- Radial distortion is ignored unless straight lines visibly bend. Then solve k1 or drop the photo to checklist only.
- Never use a lost building's height as control.
- Refuse metres when the scale rung is poor. Gate a full solve on spread and non-coplanarity of control as well as pixel RMSE, because a wrong focal and range pair can still fit well. In the West End almost no photo will pass that gate, because nothing in frame survives. The photo then gives checklist values and ratios.

Sigma. Run a Monte Carlo over: click error; independent relative corner error on the footprint (guess 0.2 to 0.5 m, to be measured); focal length and principal point; camera height and 1950s grade; and wall base definition. Model Sanborn error as two parts: a common shift and rotation per sheet (1 to 2.5 m, irrelevant to height) and the independent corner error. Add stated allowances for the Sanborn line not being the wall face and for a hidden wall base.

Conflicts with Sanborn:
- Footprint: Sanborn or CAGIS only. A photo raises a Review item.
- Storeys and material: Sanborn stays primary. A disagreement is shown side by side with both dates. It may be an alteration, so Review offers "split at this year" or "Sanborn is wrong".
- Height: a printed Sanborn wall height where one exists, then photo, then style. Whether Cincinnati sheets print wall heights is unverified. Recollection is that Sanborn printed them mainly on larger commercial and industrial buildings, not row dwellings. If so this rule applies to few West End buildings. It is a 10 minute check on any LOC sheet.
- Photo height against aerial height: compare like with like. Either measure the parapet or eave line in stereo by hand, or apply a roof-form offset with its own uncertainty first. Calibrate that offset on OTR survivors, where lidar gives both the wall top and the roof surface. Then flag when they differ by more than the combined sigma.
- Standing buildings: lidar wins.

## 6. How it fits the hub

Spec section 7 already treats photos as evidence and bans them from the look. `evidence[]` already has kinds `photo` and `aerial`. What is missing is a record for the photo itself.

- Photo record: a new `photo` kind with catalogue, scan, rough pin, view type, scale rung, control points, buildings shown, observations, and a solved pose where one exists. Scans sit in a read-only tier on your machine. Git holds small vectors. Large scans need downsampled copies for a click-to-measure pane.
- Observations: ratios and neighbour steps need their own shape, since they are not building fields. A block is levelled from them.
- Value source: two paths. Simplest: an accepted value is saved as your own field on the building, with `evidence[]` pointing at the photo. That changes nothing in 7.4. The other adds a `photo` source to the resolver and a confidence level between `read` and `inferred`. That changes 7.4.
- Height definition: 7.4 should say which top and which base `height_m` means, and stop sourcing a wall-top value from `h_70p` without an offset.
- Jobs: a catalogue fetcher, a plane-measure tool, and one solver. Before writing the solver, read Smapshot and moniQue and check whether fSpy already does the seeding. Build it once, so the batch tool and the app share it.
- UI: a Photos map layer with cones and a year filter, drawn on the hub's own map with the Sanborn overlay; a photo pane with click to measure and, where it applies, "match camera".
- Aerials: frames, surface model and orthophoto need their own tier and record shape. A ground station and cone does not fit them.

Collisions and open questions:
1. Overlaying the model on a photograph inside a pane. I read it as an evidence viewer, like the Sanborn swipe. You have not ruled.
2. Rights, spec question 16. City photos of 1959 are not public domain by default. Measuring is low risk; display needs the museum's terms. Not legal advice.
3. Spec question 1, which Sanborn edition is the base. The 1949-50 corrected state is very likely usable for the West End. Its scans are public domain and Vols. 3 and 4 sit on the 1904 sheet layout, so it may reuse the 1904 georeferencing. The West End volume is not yet identified.
4. Kartta Labs is a Google project. Your ruling covers Google data. Its code is your call. Rulings check: no breach found. The one vision-language study cited was measured on Google Street View images. Citing it is not using Google data, but you should know.
5. The 24 Nov hold. Kind, pane and resolver source all wait.

What can be done now without touching the hub: the checks below, the pilot in section 7, and results written as plain files shaped like the photo record so they import later.

- Open the museum catalogue and look at 30 Kenyon-Barr records from one block. Address, plot number or both? What pixel size? How many frontages does a typical frame show? Is the sign in every frame, and does it stand at the wall?
- Email CHLA and Anne Delano Steinert, who curated Finding Kenyon Barr against the 1934 Sanborn. Ask: exact count; any address index or parcel key; scan size; camera and negative format of the 1959 survey; size of the signboard; research versus display terms; whether appraisal files, auditor cards, a WPA survey or permits survive.
- Log in to EarthExplorer and list every pre-1960 date over the basin, not only 3 May 1949. See whether two frames overlap over the West End. The one frame checked is centred 1.5 to 2 km west. Check the micron size of the $30 scan and whether the film is still at EROS.
- Ask Way Back West End whether their 1890s building layer can be shared, and under what terms.
- Open the LOC Sanborn key map and find the West End volume. On the same visit, check whether sheets print wall heights on dwellings.

## 7. A pilot

Goal: replace the estimates with measured numbers, on rights-clean data, outside the hub.

0. Lot link test. Take the single 1904 Kenyon-Barr Sanborn sheet in batch B4. Pull the photos for those addresses. Count how many link, and how many parameters each fixes. This needs no measuring tool and is the gate for the whole Kenyon-Barr route.
1. Baseline, no photos. Take a few hundred surviving pre-1900 OTR and West End buildings. Compute storeys times spec floor heights (spec 7.4: 4.6 or 3.8 ground, 3.4 upper). Compare with lidar wall-top height. This number is the bar every photo method must clear.
2. Define truth as the feature the photo measures: eave or parapet top above the sidewalk at the facade. Take it from lidar points along the street wall edge, not `h_70p`, and state its sigma (likely 0.2 to 0.3 m). Better: measure 5 to 10 facades on site with a laser distance meter, or use HABS measured drawings where they exist. Whether any Dayton Street building has them was not checked.
3. Pick about 30 surviving buildings, mostly OTR tenements. Dayton Street houses are grand, with tall floors, so era defaults look worse there and flatter the photo method.
4. Trace the 1904 (or 1949-50) Sanborn footprints of the same buildings and use them as control. That is the real West End test. It also measures Sanborn relative corner error against CAGIS, which is unknown today. If tracing is not possible, perturb CAGIS corners with one common shift of 1 to 2.5 m plus an independent 0.2 to 0.5 m per corner. Do not shift corners independently by metres.
5. Photos. Use HABS photos for rights-clean practice, found by street name through the LOC JSON API, and run them as plane measurement only. They are view-camera work with perspective correction (recalled, unverified per frame). For the solver, take your own photos of the same buildings with a known camera and crop them at random to mimic prints. That isolates the principal point effect against known truth.
6. Score three arms on the same buildings:
   - Arm 1: storeys times era floor height.
   - Arm 2: checklist plus ratios. Storeys from the photo, floor split from ratios, style default for absolute scale.
   - Arm 3: plane measurement with the best scale rung available. Report each rung separately, including brick courses.
   Report median and 90th percentile error for each arm. Also score ratios and neighbour steps on their own. Time each building.
7. In parallel, if a stereo pair exists: hand-measure about 30 unaltered OTR roofs in stereo and score against lidar roof surface. Check the shadow method on the same frame against the same buildings.

Success: arm 3 beats arm 1 by a stated margin, say half the error, at under 15 minutes a building. Stated sigmas cover about two thirds of truths, judged on the full 30. For the aerial test: median error at or under 1.5 m by hand.

Failure: arm 3 is no better than arm 1. Then drop absolute photo heights and keep the checklist, ratios and steps. Whether arm 2 beats arm 1 is a result of the pilot, not an assumption. If the aerial test is worse than one storey, use the frames by eye and for shadows only.

Caveat: a pass on modern or HABS photos is necessary, not sufficient. The second test is one West End block on real Kenyon-Barr scans.

Ben-hours, all guesses: 3 to 4 for the checks; 8 to 15 for clicking and scoring, more with 30 buildings; 8 to 16 for hand stereo, plus choosing a stereo tool. Script building is extra. Sanborn tracing is extra and is probably the largest block of your time. No whole-West-End hours figure is given: no throughput has been measured.

## 8. Decisions for you

1. May a photograph sit behind the model inside an evidence pane? Yes or no.
2. Photo values: your own field with evidence (no spec change), or a new `photo` resolver source?
3. Do unaccepted photo values draw with a mark, or stay hidden? I lean hidden.
4. Which Sanborn edition is the West End base? I now lean to the 1949-50 corrected sheets from LOC, once the West End volume is found. The alternatives are 1904 and 1922.
5. Will you ask the museum for bulk research access before or after the pilot?
6. Is private storage of museum scans for measurement acceptable to you before terms are known?
7. Is the aerial track in scope now, as a check, or parked? Shadows need only one frame.
8. May Kartta Labs code be read or used?
9. Does your machine have a GPU, and how much RAM and disk? Nothing in the files says.
10. Machine reading: never, or later as a scored proposer run locally?
11. Should `height_m` in spec 7.4 be pinned to "wall top above sidewalk at the facade"?
12. Is a search for motion film and hillside panoramas worth an hour?

## 9. What could not be verified

- Kenyon-Barr: the count, the online share, scan resolution, whether each record carries an address or only a project or plot number, whether an index or parcel map exists, what the sign shows and whether it is in every frame, its size and position, the camera and negative format, and rights. Scan resolution is the most decisive unknown, because it decides whether brick courses can be counted.
- That the clearance area and the 286-block Sanborn box are the same ground, or that about 3,000 photos cover it.
- Which LOC Sanborn volume covers the West End. Two items did not load. Vol. 1 of 1934 and of 1950 are not online.
- Printed wall heights on Cincinnati Sanborn sheets.
- Sanborn relative accuracy at building-corner level. The 2.3 to 2.7 m figure is a 1912 street-layer residual; no 1904 building corners are traced. Every single-frontage sigma is a guess until the pilot.
- A pre-1960 stereo pair over the West End; 9 inch format; 60% overlap; scan micron size (recalled as 25 micron high resolution and 400 dpi medium, unverified); time of exposure; a calibration report or fiducials; the flying agency; whether the film is still at EROS.
- The 1956 county flight beyond an index entry. ODOT and Ohio History Connection coverage of the West End before 1960.
- Every accuracy figure for photo heights, brick-course counting, 1940s urban stereo and shadows. None has a published test that was found. All budgets are arithmetic from stated assumptions.
- The baseline accuracy of storeys times floor height.
- Whether any West End or downtown building has 10 or more photos.
- Whether HABS Dayton Street or OTR records include enough square-on street views, and the HABS date range.
- The Way Back West End 1890s building layer and the CinTIMHA file: coverage, date, licence.
- Appraisal files, auditor cards, a WPA survey, permits: none found.
- Motion film, hillside panoramas, Cincinnati in Motion: not searched.
- The "about 70%" figure in arXiv 2607.14756, the AUC figures in 2604.22714 and the 333 figure in 2010.06536 were not re-checked this round. The four arXiv pages exist with matching titles.
- Smapshot's point rules and submit gate; moniQue's fit to wall planes; fSpy, GeoCalib, Perspective Fields, e-foto; licences for OpenCV, MapLibre, MicMac, ASP, pi3 and the vision-language models.
- thenthere.io was read from code and API, not rendered. Three lazy chunks were not read.
- One review ran with the web search budget used up, so its gaps without URLs rest on recall.

Hosts blocked that mattered most: cincymuseum.org and library.cincymuseum.org, cdm16998.contentdm.oclc.org (the Public Library's digital site redirects there), digital.libraries.uc.edu, earthexplorer.usgs.gov, www.usgs.gov, github.com, isprs-archives.copernicus.org, sciencedirect.com, muse.jhu.edu, aspace.ohiohistory.org, www.uc.edu, waybackwestend.org, storymaps.arcgis.com, www.lsu.edu, danvk.org, huggingface.co, mdpi.com, link.springer.com, tandfonline.com, hamiltoncountyauditor.org, wiki.openstreetmap.org. www.loc.gov and arxiv.org failed in some sessions.

Context files: (session scratch, not kept)/ctx/spec_s7_buildings.md and (session scratch, not kept)/ctx/Hub_3D_View_Spec.md