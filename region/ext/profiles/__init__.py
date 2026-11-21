"""The profiles feature (WP5): the ``profile`` record, its inputs to the engine, its jobs and its API.

- ``kinds/profile.yaml``: one record per section, merged whole (section 4).
- ``doc.py``: the old alignment doc and the profile record, each made from the other value for value.
- ``inputs.py``: ``section_input(ctx, section_id)``, SectionInput v0 from records (section 7).
- ``jobs.py``: ``profiles.solve_section@1`` and ``profiles.golden_diff@1`` (``golden.py``, ``golden.yaml``).
- ``router.py``: ``GET /x/profiles/sections/{id}/input`` and ``GET /x/profiles/routes/{id}/doc``.
- ``validators.py``: a profile's platform keys belong to its section.
"""
