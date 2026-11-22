"""The terrain feature: the ground layers the hub can sample, as records that follow lane B's tier handshakes.

- ``kinds/ground_layer.yaml``: one record per ground surface (9.15: its vertical datum, units and how it came in),
  with whether it can be used now (``available``) and the stage its handshake reports.
- ``importers.py``: ``ground_layers@1`` into ``import:ground``, from each ground tier's handshake (``STATUS.json``):
  when lane B's handshake for the 1912 ground says done, the ``real_1912`` record turns available, and every result
  that reads it is planned again (the live hub runs this importer when the handshake changes).
- ``sources.py``: the files doctor lists.
"""
