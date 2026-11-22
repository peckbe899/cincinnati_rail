"""A job type for the live tests: ``t.ground`` stands for the ground jobs of increment 2 (``ground.profile``). Its
plan reads the section, every ``ground_layer`` record and the 1912 tier's handshake file, so the handshake turning
done invalidates it through both the record and the file; its run counts the layers that are available."""

from __future__ import annotations

from typing import Any

from region.core.protocols import Output


class GroundDependent:
    name = "t.ground"
    version = "1"
    scope = "section"
    host = "thread"
    priority = 5
    timeout_s = 10.0

    def plan(self, ctx: Any, scope_id: str) -> dict[str, Any]:
        sec = ctx.read("section", scope_id)
        layers = ctx.list("ground_layer")
        ctx.file("tier://ground_1912_real/STATUS.json")
        length = (sec or {}).get("data", {}).get("length_m")
        return {"length": length, "available": [r["data"]["available"] for r in layers]}

    def run(self, inputs: dict[str, Any], rt: Any) -> Output:
        return Output(meta={"available": sum(1 for a in inputs["available"] if a), "length": inputs["length"]})


GROUND = GroundDependent()
