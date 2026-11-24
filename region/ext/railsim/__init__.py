"""The railsim feature: run times from the hub's records (I2.1, "Close the loop"; plan in claude/hub_maps/i21_plan.md).

railsim (``railsim/``) is read and imported, never changed. Its own route builder (``line.build_route``: the KMZ,
the track network, the ground fetch and the Metro profile port) is replaced by four job types over the records:

- ``route.horizontal@1`` (scope a section; process host): railsim's ``fit_horizontal`` on the section's drawn path
  (``horizontal.py``), the curves and the map from section chainage ``c`` to run chainage ``s`` along the fit;
- ``route.assemble@1`` (scope a route; thread host): the RouteInput (``assemble.py``, contract ``route_input/0``):
  the solved rail (``profiles.solve_section``), the tunnel flags (``profiles.solve_structure``), the fit and the
  stops from the records, on the 2 m run grid;
- ``railsim.run@1`` (scope a route; process host; axis year): both directions through railsim's own ``Simulator``
  (``adapter.py``, contract ``run_result/0``), with the era, train, dwell and padding of the year;
- ``railsim.attribution@1`` (scope a route; process host; axis year): where the time goes (``attribution.py``): the
  seconds each speed restriction, the grades and the tunnel drag cost, by re-running without each.

What the records do not hold yet (station dwell classes, PSD, the era file, the rolling stock, the line config's
padding and turnback) is read from railsim's own files through ``ctx.file`` (``legacy.py``), so every file read is
in the key. No job reads a KMZ, a DEM or the network, and none writes: ``run`` returns outputs only.

``draft.py`` runs an unsaved edit of the line sheet in a worker of its own (``POST /x/railsim/sections/{id}/draft``,
``router.py``), so a draft never takes the scheduler's process slots; ``GET /x/railsim/routes/{id}/input`` reads the
warm RouteInput. ``contract.py`` holds the pydantic models of ``route_input/0``, ``run_result/0`` and the draft
route (the router's response models, so ``openapi.json`` and the app's generated types carry them); ``sources.py``
lists the declared fallback files for doctor.

Parity with ``tests/baseline/runtimes.json`` is in ``tests/railsim``: ``test_adapter.py`` (railsim's own route
through the adapter gives the baseline exactly), ``test_parity.py`` (Line 6 within 1 % from the records, and every
Metro line's difference classed) and ``parity.py`` (the decomposition).
"""
