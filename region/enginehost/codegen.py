"""Generate ``region/contract/gen`` from ``engine/schema/v0`` with datamodel-code-generator (decision 9.12).

    python -m region.enginehost.codegen            # rewrite region/contract/gen
    python -m region.enginehost.codegen --check    # exit 1 when the committed files are stale

The engine contract is owned by zod in ``engine/src/contract``; ``engine/scripts/gen_schema.ts`` exports it to JSON
Schema, and this turns each schema file named in ``engine/schema/v0/contracts.json`` into one pydantic v2 module. The
output is committed; ``tests/enginehost/test_contract_gen.py`` regenerates it and fails on any difference.

The run is deterministic: no timestamp, the generator's built-in formatter (no black or isort version enters the
bytes), Python 3.12 as the target, and docstring lines wrapped at 120 columns (the repo's ruff line length) by this
module, since descriptions written in zod can be longer than a line.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

from region.core import fsio, paths

SCHEMA_DIR: Path = paths.REPO / "engine" / "schema" / "v0"
OUT_DIR: Path = paths.REPO / "region" / "contract" / "gen"
LINE = 120

# Every option that shapes the output. A change here is a change of the committed files.
OPTIONS = [
    "--input-file-type",
    "jsonschema",
    "--output-model-type",
    "pydantic_v2.BaseModel",
    "--target-python-version",
    "3.12",
    "--disable-timestamp",
    "--formatters",
    "builtin",
    "--use-standard-collections",
    "--use-union-operator",
    "--field-constraints",
    "--use-schema-description",
    "--use-field-description",
    "--use-double-quotes",
]

# The model each module's schema describes, re-exported by the package.
ROOTS = {
    "section_input": "SectionInput",
    "vertical_rail": "VerticalRail",
    "station_input": "StationInput",
    "station_facts": "StationFacts",
    "section_solve_input": "SectionSolveInput",
    "solved_section": "SolvedSection",
    "section_propose_input": "SectionProposeInput",
    "section_proposal": "SectionProposal",
    "flag": "Flag",
    "hello": "Hello",
    "request": "Request",
    "response": "Response",
}


def _wrap_long_lines(text: str) -> str:
    """Wrap any line longer than LINE at word boundaries, keeping its indentation (only docstring text is that
    long; code lines from the generator are short)."""
    out: list[str] = []
    for line in text.split("\n"):
        if len(line) <= LINE:
            out.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        out.extend(
            textwrap.wrap(
                line.strip(),
                width=LINE,
                initial_indent=indent,
                subsequent_indent=indent,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return "\n".join(out)


def _standard_dict(text: str) -> str:
    """The generator writes ``typing.Dict`` for an open object's ``__pydantic_extra__`` even with
    --use-standard-collections: the builtin ``dict`` instead (ruff UP006, UP035)."""
    import re

    if "Dict[" not in text:
        return text
    text = text.replace("Dict[", "dict[")

    def drop(m: re.Match[str]) -> str:
        names = [n.strip() for n in m.group(1).split(",") if n.strip() and n.strip() != "Dict"]
        return f"from typing import {', '.join(names)}" if names else ""

    return re.sub(r"^from typing import (.+)$", drop, text, count=1, flags=re.M)


def _init_text(contracts: dict[str, int], modules: list[str]) -> str:
    lines = [
        '"""Pydantic models of engine contract v0, generated from engine/schema/v0 by datamodel-code-generator.',
        "",
        "Do not edit: run ``python -m region.enginehost.codegen``. tests/enginehost/test_contract_gen.py regenerates",
        "these files and fails on any difference. ``CONTRACTS`` are the contract majors these models describe: the",
        "engine host refuses an engine whose hello names another major.",
        '"""',
        "",
    ]
    for mod in sorted(modules):
        lines.append(f"from .{mod} import {ROOTS[mod]}")
    names = ["CONTRACTS", "SCHEMA_VERSION", *sorted(ROOTS[m] for m in modules)]
    lines += [
        "",
        'SCHEMA_VERSION = "v0"',
    ]
    one_c = "CONTRACTS: dict[str, int] = {" + ", ".join(f'"{k}": {v}' for k, v in sorted(contracts.items())) + "}"
    if len(one_c) <= LINE:
        lines.append(one_c)
    else:
        lines += ["CONTRACTS: dict[str, int] = {", *(f'    "{k}": {v},' for k, v in sorted(contracts.items())), "}"]
    lines += [
        "",
    ]
    one = "__all__ = [" + ", ".join(f'"{n}"' for n in names) + "]"
    lines += [one] if len(one) <= LINE else ["__all__ = [", *(f'    "{n}",' for n in names), "]"]
    return "\n".join(lines) + "\n"


def generate(schema_dir: Path = SCHEMA_DIR) -> dict[str, str]:
    """Every file of ``region/contract/gen`` as it should be: file name to text."""
    index = fsio.read_json(schema_dir / "contracts.json")
    modules = [name.removesuffix(".json") for name in index["schemas"]]
    unknown = [m for m in modules if m not in ROOTS]
    if unknown:
        raise RuntimeError(f"no root model named for schema(s) {unknown}: add them to ROOTS")
    files: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="cr-codegen-") as tmp:
        for mod in modules:
            out = Path(tmp) / f"{mod}.py"
            cmd = [sys.executable, "-m", "datamodel_code_generator", "--input", str(schema_dir / f"{mod}.json")]
            cmd += ["--output", str(out), *OPTIONS]
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=str(schema_dir))
            if r.returncode != 0:
                raise RuntimeError(f"datamodel-codegen failed on {mod}.json:\n{r.stderr or r.stdout}")
            text = fsio.read_text(out)
            files[f"{mod}.py"] = _wrap_long_lines(_standard_dict(text)).rstrip("\n") + "\n"
    files["__init__.py"] = _init_text(index["contracts"], modules)
    return files


def stale(out_dir: Path = OUT_DIR, schema_dir: Path = SCHEMA_DIR) -> list[str]:
    """The files of ``out_dir`` that differ from a fresh generation (missing, changed or extra)."""
    want = generate(schema_dir)
    have = {p.name for p in out_dir.glob("*.py")} if out_dir.is_dir() else set()
    bad = sorted(n for n in have - set(want))
    for name, text in want.items():
        path = out_dir / name
        if not path.is_file() or path.read_bytes() != text.encode("utf-8"):
            bad.append(name)
    return sorted(set(bad))


def write(out_dir: Path = OUT_DIR, schema_dir: Path = SCHEMA_DIR) -> list[str]:
    """Rewrite ``out_dir`` and delete any stale module. Returns the names written."""
    files = generate(schema_dir)
    with fsio.allow_writes(out_dir):
        for name, text in files.items():
            fsio.write_atomic(out_dir / name, text)
        for old in out_dir.glob("*.py"):
            if old.name not in files:
                old.unlink()
    return sorted(files)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m region.enginehost.codegen", description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="report stale files and exit 1, writing nothing")
    a = ap.parse_args(argv)
    if a.check:
        bad = stale()
        for name in bad:
            print(f"stale: region/contract/gen/{name}")
        return 1 if bad else 0
    for name in write():
        print(f"wrote region/contract/gen/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
