"""The legacy feature (WP5): the old hub's records in ``legacy:old_hub`` (decision 9.23).

- ``kinds/``: ``roadmap_item``, ``camera``, ``view``.
- ``importers.py``: ``old_hub@1``, from ``hub/seed`` or a backup-API snapshot of ``hub\\hub.db`` (``oldhub.py``).
- ``authority.py``: the authority defaults, so legacy owns the kinds the old hub still edits.
"""
