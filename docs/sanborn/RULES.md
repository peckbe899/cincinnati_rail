# Rules that travel with the Sanborn pipeline

Copied as written from `Sanborn_Pipeline_Migration_Plan.md` section 7 (31 October 2026), so Claude Code has them in the repo.

From Ben and `claude/Sanborn_1922_Plate_Process.md`; Claude Code can't read the project, so these go into `docs/sanborn/`.

1. The 1922 plate is the reference. Fit the plate first, then bend the 1904 sheets onto it.

2. Ben's GeoTIFF is a starting position only. The image that is fitted and drawn is his raw PNG.

3. Controls are today's OSM crossings of streets that have not moved or been widened since 1922. Realigned streets are left out by name (Dixmyth, Glenmary, Lafayette on plate 38; Elmore; Colerain north of N 4,336,600). Renamed streets get aliases (Victory Boulevard = Victory Parkway, Clough Avenue = Crane Avenue, Montgomery Pike / Avenue = Montgomery Road, McNeill = McNeil Avenue, Robertson Road = Robertson Avenue, Mt. Hope Road = Mount Hope Avenue, Filson Terrace = Filson Place, Alpine Way = Alpine Place, Quebec Avenue = Quebec Road).

4. Match within 45 m of the seed, refit, match again within 30 m. Drop, one at a time, any control the tps1 spline misses by more than 6 m. Pick the model by leave-one-out: affine, quadratic, affine plus thin-plate spline at smoothing 0.3, 1, 3, 10, 30, 100.

5. 1922 is its own layer, drawn over 1904, never mixed into it. Only 1904 sheets already on the page are bent. The bend is solved for every bent frame together.

6. A plate's streets take its footprint 3 m inside the edge, less earlier plates and kept lines. Ben's edited streets and named keep-lines stay. Widths are printed widths, else 50 ft for streets and alley defaults for alleys. Each plate is its own street set with its own id prefix and removal file.

7. Western Hills and similar areas: OSM primary and secondary streets first (set w1), the plates fill in only ground not drawn, clipped to Ben's line.

8. Pre-war suburban layout ("Park Ridge, not Park Forest"): few cul-de-sacs; where the ground forces otherwise, the plates and the terrain map decide.

9. Street ids stay stable; Ben's names (`n`) and deletions (`del`) are keyed by id. After any rebuild, every id in his live layout must still exist with the same name.

10. Export the hub (`python hub/hub.py export`) before a build, so the build sees Ben's latest edits.

11. The claude.ai artifacts are retired. Repo and hub changes go through Claude Code; chat sessions write prompts and logs.

12. Every 1922 plate is fitted by thin-plate spline on every control available: the complete set of OSM crossings of
    two named, unchanged streets on the plate (rule 3's lists apply), each read by hand off the scan (two independent
    reads, kept when they agree within 60 px). The smoothing is chosen by held-out error. The hand picks are the
    controls, not seeds. An automatic locator was tried and does not read Sanborn plates well enough
    (`docs/sanborn/dense_locator_2026-11-06.md`). (Ben, 6 November 2026.)
    From 13-14 November 2026 (Ben: blind strip reading is not to be used on its own; fixes go into the reader for
    every plate, not into one plate) a plate is read by the guided reader, `tools/sanborn/guided/`: today's crossings
    and points every 60 m along today's streets are projected onto the scan and read twice; street ends are read in
    rounds; a two-reader review of the built lines adds missing streets and cuts wrong ones. Streets are identified by
    today's street id, not a name key. Blind strip picks only seed the first fit. Plate 80: 76 controls, 2.00 m.
