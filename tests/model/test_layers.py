"""Layers: copy-on-write in scenarios, import namespaces, the 10k list, promote, tags and authority."""

from __future__ import annotations

import time

import pytest

from region.core import ids
from region.core.errors import Conflict, Invalid, NotFound
from region.core.protocols import Op
from region.core.view import View
from tests.model.helpers import feature, note, raw, run, tag, tid


def test_scenario_shadows_main_and_copies_up(store, main):
    store.create_layer("try", by="ben")
    tried = View(layer="try")
    r = note(store, "main text")
    seen = store.get("note", r["id"], tried)
    assert seen == r and seen["layer"] == "main"
    up = store.patch(
        "note",
        r["id"],
        [{"op": "replace", "path": "/data/text", "value": "try text"}],
        tried,
        if_match=tag(seen),
        by="ben",
    )
    assert up["layer"] == "try" and up["version"] == 1 and tag(up) == '"try:1"'
    con = raw(store)
    base = con.execute(
        "SELECT base_hash FROM rec r JOIN layer l ON l.id = r.layer WHERE l.slug = 'try' AND r.id = ?", (r["id"],)
    ).fetchone()[0]
    con.close()
    assert base == r["hash"]
    assert store.get("note", r["id"], main) == r
    assert store.get("note", r["id"], tried)["data"]["text"] == "try text"
    assert [x["layer"] for x in store.list("note", tried)[0]] == ["try"]
    assert [x["layer"] for x in store.list("note", main)[0]] == ["main"]
    # a record made in the scenario stays there; a delete there hides the main record there only
    own = note(store, "only in try", view=tried)
    assert own["layer"] == "try"
    with pytest.raises(NotFound):
        store.get("note", own["id"], main)
    store.delete("note", r["id"], tried, if_match=tag(up), by="ben")
    with pytest.raises(NotFound):
        store.get("note", r["id"], tried)
    assert store.get("note", r["id"], main) == r
    assert store.chain(tried)[:2] == ["try", "main"]
    # a scenario under a scenario sees both
    store.create_layer("try-deeper", parent="try", by="ben")
    assert store.chain(View(layer="try-deeper"))[:3] == ["try-deeper", "try", "main"]
    assert store.get("note", own["id"], View(layer="try-deeper"))["layer"] == "try"


def test_import_namespaces_disjoint(store, main, monkeypatch):
    real = ids.namespaces()
    extra = ids.Namespace("test_b", real["test"].epoch_ms - 86_400_000, "import:test_b", "second test", True)
    monkeypatch.setattr(ids, "namespaces", lambda: {**real, "test_b": extra})
    store.create_layer("import:test", namespace="test", by="t")
    store.create_layer("import:test_b", namespace="test_b", by="t")
    with pytest.raises(Conflict) as e:
        store.create_layer("import:test_c", tier="import", namespace="test", by="t")
    assert e.value.reason == "namespace"
    a = View(layer="import:test")
    body = {"data": {"name": "x", "class": "road"}, "geom": None}
    store.write([Op("create", "feature", tid("x"), None, body=body)], a, by="t", message="")
    other = ids.stable("test_b", "y")
    with pytest.raises(Conflict) as e:
        store.write([Op("create", "feature", other, None, body=body)], a, by="t", message="")
    assert e.value.reason == "namespace" and e.value.conflicts[0]["namespace"] == "test_b"
    with pytest.raises(Conflict) as e:
        store.write([Op("create", "feature", ids.new(), None, body=body)], a, by="t", message="")
    assert e.value.reason == "namespace"
    with pytest.raises(Invalid):
        store.write([Op("create", "feature", None, None, body=body)], a, by="t", message="")
    store.write([Op("create", "feature", other, None, body=body)], View(layer="import:test_b"), by="t", message="")
    # both import layers sit under main, side by side
    assert {r["layer"] for r in store.list("feature", main)[0]} == {"import:test", "import:test_b"}
    assert [r["id"] for r in store.list("feature", a)[0]] == sorted([tid("x"), other])
    assert store.chain(a) == ["import:test", "import:profiles", "import:registry", "import:test_b"]


def test_list_10k_resolves_under_200ms(store, imp_layer):
    n = 10_000
    recs = [
        feature(f"f{i:05d}", f"Feature {i}", x=700000 + (i % 100) * 10, y=4330000 + (i // 100) * 10) for i in range(n)
    ]
    rep = store.apply_import(run(), recs, dry_run=False)
    assert rep.counts["created"] == n
    main, tried = View(), View(layer="try")
    store.create_layer("try", by="ben")
    page, _ = store.list("feature", main, limit=1000)
    ops = [
        Op("patch", "feature", r["id"], tag(r), patch=[{"op": "replace", "path": "/data/name", "value": "main"}])
        for r in page
    ]
    store.write(ops, main, by="ben", message="1000 in main")
    page, _ = store.list("feature", tried, limit=100)
    ops = [
        Op("patch", "feature", r["id"], tag(r), patch=[{"op": "replace", "path": "/data/name", "value": "try"}])
        for r in page
    ]
    store.write(ops, tried, by="ben", message="100 in try")
    store.list("feature", tried, limit=n)  # warm the statement cache
    t0 = time.perf_counter()
    rows, cursor = store.list("feature", tried, limit=n)
    took = time.perf_counter() - t0
    assert len(rows) == n and cursor is None
    layers = [r["layer"] for r in rows]
    assert layers.count("try") == 100 and layers.count("main") == 900 and layers.count("import:test") == 9000
    assert rows == sorted(rows, key=lambda r: r["id"])
    assert took < 0.2, f"listing {n} records took {took * 1000:.0f} ms"
    # paging walks the same records
    seen, after = [], None
    while True:
        page, after = store.list("feature", tried, limit=3000, after=after)
        seen.extend(r["id"] for r in page)
        if after is None:
            break
    assert seen == [r["id"] for r in rows]
    # the bbox filter is exact on the winning revision
    box = store.list("feature", tried, bbox=(700000, 4330000, 700010, 4330010), limit=n)[0]
    assert len(box) == 4


def test_promote_one_changeset_with_if_match(store, main):
    a, b, c = note(store, "a"), note(store, "b"), note(store, "c")
    store.create_layer("try", by="ben")
    tried = View(layer="try")
    store.patch(
        "note", a["id"], [{"op": "replace", "path": "/data/text", "value": "a2"}], tried, if_match=tag(a), by="ben"
    )
    store.delete("note", b["id"], tried, if_match=tag(b), by="ben")
    made = note(store, "new", view=tried)
    seq = store.last_seq()
    res = store.promote("try", by="ben", message="take try")
    assert res.changeset is not None
    cs = store.changeset(res.changeset)
    assert cs["kind"] == "promote" and cs["layer"] == "main" and cs["count"] == 3
    assert {r["id"] for r in cs["records"]} == {a["id"], b["id"], made["id"]}
    assert [e["type"] for e in store.events_since(seq)].count("changeset") == 1
    assert store.get("note", a["id"], main)["data"]["text"] == "a2"
    with pytest.raises(NotFound):
        store.get("note", b["id"], main)
    assert store.get("note", made["id"], main)["layer"] == "main"
    assert store.get("note", c["id"], main) == c
    assert store.layer("try")["state"] == "promoted"
    with pytest.raises(Conflict):
        note(store, "late", view=tried)
    # If-Match against the parent: main changed under a copy-up, so promote refuses and writes nothing
    store.create_layer("try2", by="ben")
    t2 = View(layer="try2")
    cur = store.get("note", c["id"], main)
    store.patch(
        "note", c["id"], [{"op": "replace", "path": "/data/text", "value": "c-try"}], t2, if_match=tag(cur), by="ben"
    )
    store.patch(
        "note",
        c["id"],
        [{"op": "replace", "path": "/data/text", "value": "c-main"}],
        main,
        if_match=tag(cur),
        by="anna",
    )
    other = store.get("note", a["id"], main)
    store.patch(
        "note", a["id"], [{"op": "replace", "path": "/data/text", "value": "a-try2"}], t2, if_match=tag(other), by="ben"
    )
    seq = store.last_seq()
    with pytest.raises(Conflict) as e:
        store.promote("try2", by="ben")
    assert e.value.reason == "rebase" and [x["id"] for x in e.value.conflicts] == [c["id"]]
    assert store.last_seq() == seq and store.layer("try2")["state"] == "open"
    assert store.get("note", a["id"], main) == other


def test_tag_reads_as_of(store, main):
    a = note(store, "a1")
    b = note(store, "b1")
    t = store.tag("main", "v1", by="ben", note="before the edits")
    assert t["seq"] == store.last_seq()
    a2 = store.patch(
        "note", a["id"], [{"op": "replace", "path": "/data/text", "value": "a2"}], main, if_match=tag(a), by="ben"
    )
    store.delete("note", b["id"], main, if_match=tag(b), by="ben")
    c = note(store, "c1")
    assert store.get("note", a["id"], main, tag="v1") == a
    assert store.get("note", b["id"], main, tag="v1") == b
    with pytest.raises(NotFound):
        store.get("note", c["id"], main, tag="v1")
    rows, _ = store.list("note", main, tag="v1")
    assert rows == sorted([a, b], key=lambda r: r["id"])
    assert {r["id"] for r in store.list("note", main)[0]} == {a["id"], c["id"]}
    assert store.get("note", a["id"], main) == a2
    assert [x["name"] for x in store.tags("main")] == ["v1"]
    with pytest.raises(Conflict):
        store.tag("main", "v1", by="ben")
    with pytest.raises(NotFound):
        store.list("note", main, tag="v9")


def test_authority_legacy_refuses_main_allows_scenario(store, main):
    legacy = "legacy:old_hub"
    auth = {
        "kind": "authority",
        "id": ids.stable("old_hub", "authority:feature"),
        "data": {"kind": "feature", "owner": "legacy", "ruling": None, "note": None},
        "geom": None,
    }
    old = {"kind": "feature", "id": ids.stable("old_hub", "f1"), "data": {"name": "old", "class": "road"}, "geom": None}
    rep = store.apply_import(run(legacy, "old_hub", "old_hub"), [auth, old], dry_run=False)
    assert rep.counts["created"] == 2
    body = {"data": {"name": "new", "class": "road"}, "geom": None}
    with pytest.raises(Conflict) as e:
        store.write([Op("create", "feature", None, None, body=body)], main, by="ben", message="")
    assert e.value.reason == "authority" and e.value.status == 409
    r = store.get("feature", old["id"], main)
    with pytest.raises(Conflict):
        store.patch(
            "feature",
            old["id"],
            [{"op": "replace", "path": "/data/name", "value": "x"}],
            main,
            if_match=tag(r),
            by="ben",
        )
    with pytest.raises(Conflict):
        store.write([Op("create", "feature", None, None, body=body)], View(layer=legacy), by="ben", message="")
    note(store, "other kinds stay writable")
    store.create_layer("try", by="ben")
    tried = View(layer="try")
    store.patch(
        "feature",
        old["id"],
        [{"op": "replace", "path": "/data/name", "value": "tried"}],
        tried,
        if_match=tag(r),
        by="ben",
    )
    with pytest.raises(Conflict) as e:
        store.promote("try", by="ben")
    assert e.value.reason == "authority"
    # the legacy importer may still write its layer
    old2 = {**old, "data": {"name": "old, renamed", "class": "road"}}
    rep = store.apply_import(run(legacy, "old_hub", "old_hub"), [auth, old2], dry_run=False)
    assert rep.counts["updated"] == 1
    # flipping to model squashes the legacy revisions into main in one changeset; main is writable again
    res = store.flip_authority("feature", by="ben", ruling="2026-11-21")
    cs = store.changeset(res.changeset)
    assert cs["kind"] == "legacy" and {x["kind"] for x in cs["records"]} == {"authority", "feature"}
    assert store.get("feature", old["id"], main)["layer"] == "main"
    store.write([Op("create", "feature", None, None, body=body)], main, by="ben", message="")
