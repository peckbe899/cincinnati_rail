"""The rules feature (WP5): ``rule``, ``ruling``, ``param`` and ``era`` records, the ``registry`` importer, and param
resolution (decision 9.25).

- ``importers.py``: ``registry@1``, ``rules/registry.yaml`` into ``import:registry``.
- ``params.py``: ``resolve(store, view, path, scope)``: section, then route, then system, then years; a
  ``region.jobs.plan.ParamResolver`` for ``Scheduler(params=...)``.
"""
