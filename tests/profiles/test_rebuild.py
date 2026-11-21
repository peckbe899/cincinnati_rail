"""``crhub rebuild``: a fresh database from git plus the imports, compared with git's seed (9.29; section 10, WP5)."""

from __future__ import annotations

import shutil
import subprocess

import pytest

from region.core import fsio, paths

REPO = paths.repo_root()
WRITABLE = ["region/seed", "region/ids"]
"""The only repo paths the write guard lets anything write (app/dist is not in git): where git could go dirty."""
SOURCES = ["data/profile/lines", "hub/seed", "rules/registry.yaml", "region/ids"]


def _status() -> str:
    run = subprocess.run(
        ["git", "-C", str(REPO), "status", "--porcelain", "--untracked-files=all", "--", *WRITABLE],
        capture_output=True,
        text=True,
        check=True,
    )
    return run.stdout


def _digest(rel: str) -> str:
    p = REPO / rel
    files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file())
    return fsio.sha256_hex("".join(f"{f.relative_to(REPO).as_posix()} {fsio.sha256_file(f)}\n" for f in files))


def _tree(root) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def _ledger_lines(folder) -> set[str]:
    out = set()
    for f in folder.glob("*.tsv"):
        out |= {f"{f.name} {ln}" for ln in f.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")}
    return out


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_rebuild_leaves_git_clean_and_byte_identical(hub_var):
    from region.cli import main
    from region.cli.rebuild import rebuild

    status, digests = _status(), {rel: _digest(rel) for rel in SOURCES}
    out = hub_var / "rebuild"
    first = rebuild()
    report1, seed1, ids1 = (out / "report.json").read_bytes(), _tree(out / "seed"), _tree(out / "ids")
    code = main(["rebuild"])  # the command, as Ben runs it
    assert code == (0 if first["ok"] else 1)
    assert (out / "report.json").read_bytes() == report1  # byte-identical across runs
    assert _tree(out / "seed") == seed1 and _tree(out / "ids") == ids1
    assert _status() == status and {rel: _digest(rel) for rel in SOURCES} == digests  # git stays clean
    assert first["from"] == "git" and first["commit"] is not None
    assert first["seed"]["same"]  # git's region/seed rebuilds byte for byte
    for name, r in first["imports"].items():
        assert r["errors"] == [] and r["conflicts"] == 0, name
    assert first["imports"]["profile_lines"]["counts"]["created"] == 1405
    assert first["imports"]["registry"]["counts"]["created"] == 300
    assert first["layers"]["legacy:old_hub"]["records"] == 13 + 24 + 1 + 11
    # a key the rebuild minted that git's ledger lacks is one the working tree's ledger already holds
    added = {f"{n} {ln}" for n, lg in first["ledgers"].items() for ln in lg["added"]}
    assert added <= _ledger_lines(REPO / "region" / "ids")
    # from the working tree, the rebuild matches it whole: the ledgers there are the ones a fresh import writes
    here = rebuild(working_tree=True)
    assert here["ok"] and here["from"] == "working tree"
    assert here["layers"] == first["layers"]
    assert _status() == status


def test_rebuild_refuses_to_build_over_var(hub_var):
    """Clearing the rebuild folder must never reach the live database or its backups: a --out naming var (or a
    folder holding it) is refused before anything is touched."""
    from region.cli.rebuild import rebuild
    from region.core.errors import Invalid

    live = hub_var / "region.db"
    live.write_bytes(b"the live database")
    (hub_var / "backups").mkdir()
    for out in (hub_var, hub_var.parent):
        with pytest.raises(Invalid):
            rebuild(out)
    assert live.read_bytes() == b"the live database" and (hub_var / "backups").is_dir()


def test_a_seed_that_refers_to_imported_records_rebuilds(hub_var, monkeypatch):
    """A seeded record may refer to an imported one: a proposal's profile names its section, which only the importers
    make. The rebuild imports the seed after them, as a fresh clone does (setup's imports, then serve's seeds); with
    the seed first it stopped on the reference."""
    from region.cli import rebuild as R
    from region.core.view import View
    from region.model import open_store
    from region.model import seed as S

    first = R.rebuild(hub_var / "r1", working_tree=True)
    assert first["imports"]["profile_lines"]["counts"]["created"] == 1405
    seed = hub_var / "seed"
    with open_store(hub_var / "r1" / "region.db") as store:
        section = store.legacy("section", "Line_6")
        assert section is not None
        store.create_layer("proposal:gate", tier="proposal", title="gate", by="ben")
        gate = View(layer="proposal:gate")
        prof = store.list("profile", gate, parent=section)[0][0]
        level = prof["data"]["pvi"][0][1]
        store.patch("profile", prof["id"], [{"op": "replace", "path": "/data/pvi/0/1", "value": level + 1.0}], gate,
                    if_match=f'"{prof["layer"]}:{prof["version"]}"', by="ben")  # fmt: skip
        S.export(store, seed)
    assert (seed / "proposals" / "gate" / "profile" / f"{prof['id']}.json").is_file()

    take = R._take
    monkeypatch.setattr(R, "_take", lambda rel, dest, head: seed if rel == "region/seed" else take(rel, dest, head))
    again = R.rebuild(hub_var / "r2", working_tree=True)
    assert again["seed"]["same"], again["seed"]  # the proposal rebuilds byte for byte
    assert again["seed_import"]["proposal:gate"]["added"] == 1
    assert again["layers"]["proposal:gate"]["records"] == 1
