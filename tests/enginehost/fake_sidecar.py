"""A stand-in sidecar for the engine host's tests: it speaks the NDJSON protocol with a hello of our choosing.

    python tests/enginehost/fake_sidecar.py [--major N] [--build HEX] [--no-hello] [--threads]

It writes a hello whose ``section_input`` major is N (0 by default) and whose engine_build is HEX (64 zeros by
default), then echoes every request's params back as its result, and exits on stdin EOF, as a real sidecar does.
With ``--threads`` each request is answered from its own thread, and two methods misbehave: ``test.hang`` never
answers, and ``test.sleep`` answers after ``params["s"]`` seconds (for a call that shares a sidecar with a hung one).
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--major", type=int, default=0)
    ap.add_argument("--build", default="0" * 64)
    ap.add_argument("--no-hello", action="store_true")
    ap.add_argument("--threads", action="store_true")
    a = ap.parse_args()
    lock = threading.Lock()
    out = sys.stdout
    if not a.no_hello:
        hello = {
            "hello": {
                "engine_version": "9.9.9",
                "engine_build": a.build,
                "contracts": {"section_input": a.major, "vertical_rail": 0},
                "methods": ["engine.echo@1"],
            }
        }
        out.write(json.dumps(hello) + "\n")
        out.flush()
    def answer(req: dict) -> None:
        if req.get("method") == "test.hang":
            return
        if req.get("method") == "test.sleep":
            time.sleep(float((req.get("params") or {}).get("s", 0)))
        with lock:
            out.write(json.dumps({"id": req["id"], "ok": True, "result": req.get("params")}) + "\n")
            out.flush()

    for line in sys.stdin:
        req = json.loads(line)
        if a.threads:
            threading.Thread(target=answer, args=(req,), daemon=True).start()
        else:
            answer(req)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
