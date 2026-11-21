"""Every file the hub writes is LF on every platform (9.29): seeds, ledgers, schemas, logs and generated files.

On Windows a file opened in text mode, and ``Path.write_text``, turn each ``\\n`` into ``\\r\\n`` unless ``newline``
is given, so the same code writes different bytes there. The hub writes through ``fsio`` (bytes) instead. This scan
keeps it so: in lane A's ``region/`` code, no ``write_text`` other than ``fsio.write_text`` and no ``open`` for
writing in text mode may appear without ``newline=``.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# lane A's packages; region/ground and region/rules.py predate the hub and are not ours to change
LANE_A = ("core", "cli", "model", "api", "jobs", "enginehost", "contract", "tiers", "analysis", "ext", "kinds", "ids")


def _mode(call: ast.Call, index: int) -> str | None:
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    arg = call.args[index] if len(call.args) > index else None
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return None


def _translating_writes(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if any(kw.arg == "newline" for kw in node.keywords):
            continue
        f = node.func
        where = f"{path.relative_to(REPO).as_posix() if path.is_relative_to(REPO) else path.name}:{node.lineno}"
        if isinstance(f, ast.Attribute) and f.attr == "write_text":
            if not (isinstance(f.value, ast.Name) and f.value.id == "fsio"):
                found.append(f"{where} write_text without newline=")
        elif isinstance(f, ast.Name) and f.id == "open" or isinstance(f, ast.Attribute) and f.attr == "open":
            mode = _mode(node, 1 if isinstance(f, ast.Name) else 0)
            if mode and "b" not in mode and any(c in mode for c in "wax+"):
                found.append(f"{where} open({mode!r}) in text mode without newline=")
    return found


def test_region_writes_no_platform_newlines():
    files = [REPO / "region" / "__init__.py", REPO / "region" / "__main__.py"]
    for pkg in LANE_A:
        files += sorted((REPO / "region" / pkg).rglob("*.py"))
    assert len(files) > 50
    found = [hit for f in files if f.is_file() for hit in _translating_writes(f)]
    assert found == []


def test_the_scan_finds_a_translating_write(tmp_path):
    bad = tmp_path / "probe.py"
    text = 'from pathlib import Path\nPath("x").write_text("a\\n")\nopen("y", "w").write("b")\nopen("z", "wb")\n'
    bad.write_text(text + 'fsio.write_text("v", "c")\nopen("w", "a", newline="\\n")\n', encoding="utf-8", newline="\n")
    hits = _translating_writes(bad)
    assert [h.split(" ", 1)[1] for h in hits] == [
        "write_text without newline=",
        "open('w') in text mode without newline=",
    ]
