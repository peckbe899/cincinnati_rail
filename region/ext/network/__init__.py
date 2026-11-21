"""The network feature (WP5): routes, sections, nodes, tracks and ground profiles, and the ``profile_lines`` importer.

- ``kinds/``: ``route``, ``section`` (chainage basis ``grid:26916`` and a scale per section, 9.14), ``node``,
  ``track``, ``ground_profile``.
- ``lines.py``: reading the Metro line files (``data/profile/lines``), their station keys, legacy keys, geometry.
- ``importers.py``: ``profile_lines@1`` into ``import:profiles`` (with the stations feature's kinds and the empty
  profiles).
- ``validators.py``: a section's path runs forward to its length; a ground profile covers its section.
- ``sources.py``: the files doctor lists.
"""
