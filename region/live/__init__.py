"""The live hub (checklist I2.0): the server watches every source it reads from outside its database and takes a
change in as soon as it settles, without a command.

- ``watch.py``: the poller (``os.scandir`` and ``stat``, ``PRAGMA data_version`` for the old hub's database), the
  settle period, pause;
- ``sources.py``: what is watched (each importer's sources, each data tier, Ben's live ``hub/hub.db``);
- ``service.py``: ``Live``: the worker that imports a settled change from the working tree (one revertible
  changeset, never over Ben's edits), checks the file dependencies of a changed tier, keeps a background goal for
  every section, sends ``source``, ``live`` and ``pending`` events, and offers Pause live and Undo this import;
- ``words.py``: what a change did, in Ben's words.
"""

from .service import Live
from .watch import Source, Watch, Watcher

__all__ = ["Live", "Source", "Watch", "Watcher"]
