"""The profiles feature's API (``/api/v1/x/profiles``): the section input and the old alignment doc rebuilt from
records (section 5; section 10, WP5)."""

from __future__ import annotations

import json

import pytest

fastapi = pytest.importorskip("fastapi")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from region.core.errors import HubError  # noqa: E402
from region.ext.profiles.doc import without_derived  # noqa: E402
from region.ext.profiles.inputs import StoreReads, section_input  # noqa: E402
from region.ext.profiles.router import router  # noqa: E402
from tests.importers.helpers import ALIGNMENTS, DOCLESS, DOCS, MAIN, read_only, section_of  # noqa: E402

BASE = "/api/v1/x/profiles"


@pytest.fixture(scope="module")
def client():
    """The router mounted as the server mounts a feature's (section 1), over the imported database read-only."""
    app = FastAPI()

    @app.exception_handler(HubError)
    def problem(request: Request, e: HubError) -> JSONResponse:
        return JSONResponse(e.to_problem(), status_code=e.status, media_type="application/problem+json")

    app.include_router(router, prefix=BASE)
    with read_only() as store:
        app.state.store = store
        with TestClient(app) as c:
            yield c, store


def test_doc_export_equals_seed_doc(client):
    c, store = client
    for route in DOCS:
        rid = section_of(store, route)["data"]["route"]
        r = c.get(f"{BASE}/routes/{rid}/doc")
        assert r.status_code == 200, r.text
        want = without_derived(json.loads((ALIGNMENTS / f"{route}.json").read_text(encoding="utf-8")))
        assert r.json() == want, route
    # a route no doc was saved for gives the doc's header and nothing else
    rid = section_of(store, DOCLESS[0])["data"]["route"]
    doc = c.get(f"{BASE}/routes/{rid}/doc").json()
    assert doc == {
        "v": 1,
        "system": "Cincinnati Metro",
        "line": "Line 10",
        "length_m": section_of(store, "Line_10")["data"]["length_m"],
        "platform_m": 121.92,
    }
    missing = c.get(f"{BASE}/routes/01DXF6DT00000000000000000Z/doc")
    assert missing.status_code == 404 and missing.headers["content-type"].startswith("application/problem+json")


def test_section_input_route_is_the_contract_with_ground(client):
    from region.contract.gen import SectionInput

    c, store = client
    sec = section_of(store, "Line_6")
    r = c.get(f"{BASE}/sections/{sec['id']}/input", params={"layer": "main"})
    assert r.status_code == 200, r.text
    body = r.json()
    SectionInput.model_validate(body)  # the engine contract's generated model (zod's schema)
    assert body == section_input(StoreReads(store, MAIN), sec["id"])
    (ground,) = [g for g in store.list("ground_profile", MAIN, parent=sec["id"])[0]]
    assert body["ground"]["step_m"] == 2.0 and len(body["ground"]["z_m"]) == len(ground["data"]["z_dm"])
    assert body["ground"]["z_m"][0] == ground["data"]["z_dm"][0] / 10
    assert c.get(f"{BASE}/sections/{sec['id']}/input", params={"year": "x"}).status_code == 422


def test_station_input_route_is_the_contract(client):
    """``GET /sections/{id}/stations``: the StationInput of station.facts@1, validated by the engine contract's
    generated model, and what ``inputs.station_input`` builds in the same view."""
    from region.contract.gen import StationInput
    from region.ext.profiles.inputs import station_input

    c, store = client
    sec = section_of(store, "Line_3")
    r = c.get(f"{BASE}/sections/{sec['id']}/stations", params={"layer": "main"})
    assert r.status_code == 200, r.text
    body = r.json()
    StationInput.model_validate(body)
    assert body == station_input(StoreReads(store, MAIN), sec["id"])
    assert body["section"] == section_input(StoreReads(store, MAIN), sec["id"])
    assert c.get(f"{BASE}/sections/01DXF6DT000000000000000000/stations").status_code == 404


def test_doc_export_carries_the_members_the_old_page_derived_on_save(pool):
    """R6: with the hub's engine, the doc export carries ``stations`` and ``summary`` as the old page's serialize()
    wrote them on save, from the line's solve as the records stand (equal to the page's own functions on Line 6:
    engine/test/port/derived.test.ts), and ``updated``; the rest of the doc is the seed doc's as before. They are
    derived, never stored in Ben's profile."""
    import gzip

    from region.core import paths

    app = FastAPI()
    app.include_router(router, prefix=BASE)
    with read_only() as store:
        app.state.store = store
        app.state.engine = pool
        with TestClient(app) as c:
            sec = section_of(store, "Line_6")
            doc = c.get(f"{BASE}/routes/{sec['data']['route']}/doc").json()
            want = without_derived(json.loads((ALIGNMENTS / "Line_6.json").read_text(encoding="utf-8")))
            assert without_derived(doc) == want
            dump = json.loads(gzip.decompress((paths.repo_root() / "engine/test/golden/old_page/Line_6.json.gz")
                                              .read_bytes()))  # fmt: skip
            assert [s["name"] for s in doc["stations"]] == [s["name"] for s in dump["stations"]]
            assert [s["rail"] for s in doc["stations"]] == [s["rail"] for s in dump["stations"]]
            assert [s["type"] for s in doc["stations"]] == [s["type"] for s in dump["stations"]]
            assert doc["summary"]["max_grade_permille"] == round(dump["summary"]["maxG"] * 10) / 10
            assert doc["updated"]
            prof = store.list("profile", MAIN, parent=sec["id"])[0][0]
            assert "stations" not in prof["data"] and "summary" not in prof["data"]
