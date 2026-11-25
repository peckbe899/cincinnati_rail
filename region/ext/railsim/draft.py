"""The draft run: railsim on the line sheet's unsaved edit, in a worker of its own (plan sections 1.5 and 1.7).

``draft_input`` makes the draft's RouteInput: the sheet's SectionInput solved with ``vertical.rail@1`` (on the hub's
engine, so the rail is the hub's rule), the draft's structure types (or the saved ones), and its live stations, laid
on the parts of the warm ``route.assemble`` result and the warm ``route.horizontal`` fit (``assemble.route_input``,
the same function the saved run takes). A platform the draft leaves out is removed; a removed terminal stays a stop.

``DraftRunner`` runs it (``adapter.run_route``, as ``railsim.run`` does) in one spawn worker of its own
(``region.jobs.hosts.ProcessHost(1)``), started on the first draft and warm after, so a draft never takes the
scheduler's process slots and the worker sits idle at no CPU between drafts. Answers are kept by key (an LRU of 32):
the same draft twice is one run. Per client and section at most one draft runs and one waits: a newer one drops the
one waiting (409 ``superseded``). Nothing is written.
"""

from __future__ import annotations

import atexit
import threading
import time
from collections import OrderedDict
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np

from region.core.errors import Conflict, HubError, Invalid
from region.core.protocols import Output

LRU = 32
TIMEOUT_S = 30.0
MAX_TASKS_PER_CHILD = 200
ARRAYS = ("limit_ms", "v_fwd_ms", "v_rev_ms", "t_fwd_s", "t_rev_s")
"""The run's arrays a draft answers with (on the section grid of ``grid``); the traces are left out."""


class DraftRun:
    """What the draft worker runs: ``adapter.run_route`` on ``{meta, arrays, settings}``. Found by the worker by
    module and name (``registry.find``); not a scheduled job type (it is in no ``JOB_TYPES``)."""

    name = "railsim.draft"

    def run(self, inputs: Mapping[str, Any], rt: Any) -> Output:
        if inputs.get("probe"):
            import os

            return Output(meta={"pid": os.getpid()})
        from .adapter import run_route

        meta, arrays = run_route(inputs["meta"], inputs["arrays"], inputs["settings"])
        return Output(meta=meta, arrays={k: arrays[k] for k in ARRAYS if k in arrays})


DRAFT_RUN = DraftRun()


def draft_input(
    assemble: Mapping[str, Any],
    fit: Mapping[str, Any],
    rail: Mapping[str, Any],
    types: Sequence[Sequence[Any]],
    stations: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    """The draft's RouteInput ``(meta, arrays)``.

    ``assemble``: the warm ``route.assemble`` meta (its ``parts``); ``fit``: the warm ``route.horizontal`` output as
    ``{meta, arrays}``; ``rail``: ``{c0, step_m, rail_m}`` of the draft; ``types``: ``type_runs``; ``stations``: the
    draft's live stations (``platform_id``, ``c_m``)."""
    from .assemble import route_input

    parts = dict(assemble.get("parts") or {})
    if not parts:
        raise Invalid("the route's assemble result carries no parts; it predates the draft run")
    live = {str(s["platform_id"]): float(s["c_m"]) for s in stations}
    parts["stations"] = [
        {**s, "c_m": live.get(s["platform_id"], s["c_m"]), "removed": s["platform_id"] not in live}
        for s in parts.get("stations") or []
    ]
    return route_input(parts, rail, types, fit)


def _plain(v: np.ndarray) -> list[float | None]:
    a = np.asarray(v, dtype=float)
    return [None if not np.isfinite(x) else float(x) for x in a.tolist()]


def plain_arrays(arrays: Mapping[str, Any]) -> dict[str, list[float | None]]:
    """The run's arrays as JSON lists (NaN, where the train never is, as null)."""
    return {k: _plain(v) for k, v in arrays.items()}


class DraftRunner:
    """One warm worker and the draft answers by key (see the module doc). ``execute`` replaces the worker (tests):
    a function of the payload giving ``(meta, arrays)``."""

    def __init__(
        self,
        *,
        execute: Callable[[dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]] | None = None,
        lru: int = LRU,
        timeout_s: float = TIMEOUT_S,
    ) -> None:
        self._execute = execute or self._in_worker
        self._lru = int(lru)
        self._timeout_s = float(timeout_s)
        self._cond = threading.Condition()
        self._busy = False
        self._gen: dict[tuple[str, str], int] = {}
        self._cache: OrderedDict[str, tuple[dict[str, Any], dict[str, Any]]] = OrderedDict()
        self._host: Any = None
        self._closed = False
        self.runs = 0
        atexit.register(self.close)

    # --------------------------------------------------------------------------------------------- the worker

    def _in_worker(self, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        from region.core import ids
        from region.jobs.hosts import ProcessHost, Task
        from region.jobs.registry import module_of

        if self._host is None:
            self._host = ProcessHost(1, max_tasks_per_child=MAX_TASKS_PER_CHILD)
        done = threading.Event()
        end: dict[str, Any] = {}

        def on_end(outcome: str, value: Any) -> None:
            end["outcome"], end["value"] = outcome, value
            done.set()

        task = Task(
            job_id=ids.new(),
            type_name=DRAFT_RUN.name,
            job_type=DRAFT_RUN,
            module=module_of(DRAFT_RUN),
            inputs=payload,
            upstream={},
            timeout_s=self._timeout_s,
            on_end=on_end,
        )
        self._host.start(task)
        done.wait(self._timeout_s + 10.0)
        outcome, value = end.get("outcome", "timeout"), end.get("value", "no answer from the draft worker")
        if outcome != "ok":
            text = str(value).strip().splitlines()[-1] if str(value).strip() else outcome
            raise HubError(f"the draft run failed ({outcome}): {text}", code="draft_failed")
        return dict(value.meta), dict(value.arrays)

    # ----------------------------------------------------------------------------------------------- the API

    def run(
        self, client: str, section_id: str, key: str, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any], bool, float]:
        """``(meta, arrays, cached, ms)`` of the draft ``key``. Raises ``Conflict`` (``superseded``) when a newer
        draft of the same client and section arrives while this one waits."""
        t0 = time.perf_counter()
        slot = (str(client), str(section_id))
        with self._cond:
            hit = self._hit(key)
            if hit is not None:
                return hit[0], hit[1], True, (time.perf_counter() - t0) * 1000
            mine = self._gen.get(slot, 0) + 1
            self._gen[slot] = mine
            self._cond.notify_all()
            while self._busy:
                self._cond.wait(0.05)
                if self._gen.get(slot) != mine:
                    raise Conflict(
                        "a newer draft of this section from the same client arrived",
                        reason="superseded",
                        code="superseded",
                    )
            hit = self._hit(key)
            if hit is not None:
                return hit[0], hit[1], True, (time.perf_counter() - t0) * 1000
            if self._closed:
                raise HubError("the draft runner is closed", code="draft_failed")
            self._busy = True
        try:
            meta, arrays = self._execute(payload)
            self.runs += 1
        finally:
            with self._cond:
                self._busy = False
                self._cond.notify_all()
        with self._cond:
            self._cache[key] = (meta, arrays)
            self._cache.move_to_end(key)
            while len(self._cache) > self._lru:
                self._cache.popitem(last=False)
        return meta, arrays, False, (time.perf_counter() - t0) * 1000

    def _hit(self, key: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
        hit = self._cache.get(key)
        if hit is not None:
            self._cache.move_to_end(key)
        return hit

    def close(self) -> None:
        """Retire the worker (the hub's end, or the process's)."""
        self._closed = True
        host, self._host = self._host, None
        if host is not None:
            try:
                host.close()
            except Exception:  # noqa: BLE001, S110 - closing at exit: nothing to report to
                pass


__all__ = ["ARRAYS", "DRAFT_RUN", "DraftRun", "DraftRunner", "draft_input", "plain_arrays"]
