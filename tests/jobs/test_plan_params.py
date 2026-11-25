"""Params resolve from the per-write cache through a plan's read-only store (I2.1 gate, found on a live hub).

``region.ext.rules.params`` keeps each view's param records once per write, keyed by the store's reader connection
and its ``PRAGMA data_version``. A plan sees the store only through ``ReadOnlyStore``, which did not forward the
reader, so every param a plan read listed every param record again: planning one ``profiles.solve_structure``
(some 200 params) took 2.3 s, and on a live hub the sheet's ``/compute`` requests held the interpreter for seconds,
starving the engine jobs' threads until crossing lines' solves timed out. The reader is ``query_only``, so a plan
still cannot write through it."""

from __future__ import annotations

import sqlite3

import pytest

from region.ext.rules.params import resolve
from region.jobs.plan import ReadOnlyStore
from tests.importers.helpers import MAIN, read_only, section_of


def test_a_plans_store_resolves_params_from_the_cache():
    with read_only() as store:
        sid = section_of(store, "Line_6")["id"]
        calls: list[str] = []
        real = store.list

        def spy(kind, view, **kw):
            if kind == "param":
                calls.append(kind)
            return real(kind, view, **kw)

        store.list = spy
        ro = ReadOnlyStore(store)
        first = resolve(ro, MAIN, "settings.platform", sid)
        listed = len(calls)
        assert listed >= 1
        for _ in range(20):
            assert resolve(ro, MAIN, "settings.platform", sid) == first
        assert len(calls) == listed, "the second and later reads come from the cache"


def test_a_plans_store_still_cannot_write_through_the_reader():
    with read_only() as store:
        ro = ReadOnlyStore(store)
        con = ro._reader()
        with pytest.raises(sqlite3.Error):
            con.execute("DELETE FROM rec")
