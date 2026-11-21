"""The server's single-instance lock (``lock.acquire(var, port) -> Lock``, section 10 WP2). The lock itself lives in
``region.core.lock`` (``var/hub.lock``, an operating-system lock the OS drops when the process ends), so the CLI
commands that must not run beside a server (``crhub jobs run``, ``crhub restore``, ``crhub setup``) share it; this
module names the same functions for the server's side. ``region.api.serve`` takes the lock before anything else."""

from __future__ import annotations

from region.core.lock import Holder, Lock, LockHeld, acquire, path_of, reader, refuse_if_held

__all__ = ["Holder", "Lock", "LockHeld", "acquire", "path_of", "reader", "refuse_if_held"]
