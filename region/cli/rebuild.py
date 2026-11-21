"""``crhub rebuild``: build a fresh database from git plus the imports, and compare its seed with git's (9.29).

    crhub rebuild [--out DIR] [--compare] [--working-tree] [--json]

The rebuild never touches the live database and never writes into the repo; an ``--out`` that holds ``var`` itself
is refused, since step 1 would delete the live database and its backups. Into ``var/rebuild/`` (``--out``), it:

1. clears its own files from the last rebuild (``region.db``, ``seed/``, ``ids/``, ``src/``, ``work/``);
2. takes from git's ``HEAD`` (``--working-tree``: from the files as they are) the seed (``region/seed``), the id
   ledgers (``region/ids/*.tsv``) and every importer's sources (the registry, the line files, the old hub's seed),
   into ``src/`` and ``ids/``;
3. creates ``region.db``, runs every importer in order (``region.cli.imports``), with the ledger copy in ``ids/``,
   then imports the seed, the order a fresh clone takes (``crhub setup``, then ``crhub serve``), since a seeded
   record may refer to an imported one;
4. exports the seeded layers into ``seed/`` and compares them, file by file, with git's ``region/seed``; compares
   ``ids/`` with git's ledgers (a line the rebuild added is a key git has not recorded yet);
5. writes ``report.json``: the commit, every source's sha256, the import counts, a digest of each layer's records
   and the comparisons. It holds no time or run id, so two rebuilds of one commit write the same bytes.

With ``--compare`` it also opens the live database read-only and lists, layer by layer, the records whose content
differs from the rebuild's (a live import layer that has drifted from its sources, or legacy revisions newer than
git's old hub seed).

Exit 0 when the rebuilt seed equals git's and the ledgers gained nothing (and, with ``--compare``, the live database
matches); otherwise 1.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from region.core import fsio, paths

SOURCES = {
    "registry": {"registry": "rules/registry.yaml"},
    "profile_lines": {"lines": "data/profile/lines"},
    "old_hub": {"lines": "data/profile/lines", "seed": "hub/seed"},
}
"""Each importer's sources as repo paths, for taking them from git (the tiers' default roots)."""
CLEARED = ("region.db", "region.db-wal", "region.db-shm", "seed", "ids", "src", "work", "backups", "report.json")


def _check_out(out: Path) -> None:
    """Refuse a rebuild folder that holds ``var`` itself (the live database, its backups): clearing it would delete
    them. ``var/rebuild`` and any folder beside or below it are fine."""
    from region.core.errors import Invalid

    here = out.resolve()
    var = paths.var_root().resolve()
    if var == here or var.is_relative_to(here):
        raise Invalid(f"crhub rebuild will not build in {out}: it holds the live var folder ({var}); use var/rebuild")


def _clear(out: Path) -> None:
    for name in CLEARED:
        p = out / name
        if not p.exists():
            continue
        fsio.check_write(p)
        if p.is_dir():
            shutil.rmtree(p)
        else:
            p.unlink()


def _take(rel: str, dest: Path, head: str | None) -> Path | None:
    """Repo path ``rel`` into ``dest`` (from git when ``head``, else from the working tree); ``None`` if absent."""
    from region.cli.imports import materialise

    if head is not None:
        return materialise(rel, dest, paths.repo_root(), head)
    src = paths.repo_root() / rel
    if not src.exists():
        return None
    files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file())
    for f in files:
        target = dest / Path(rel).name if src.is_file() else dest / f.relative_to(src)
        fsio.write_atomic(target, f.read_bytes())
    return dest / Path(rel).name if src.is_file() else dest


def _files(root: Path | None) -> dict[str, bytes]:
    if root is None or not root.is_dir():
        return {}
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def compare_trees(ours: Path | None, theirs: Path | None) -> dict[str, Any]:
    """``{same, added, removed, changed}`` of two folders, by relative path and bytes."""
    a, b = _files(ours), _files(theirs)
    added = sorted(set(a) - set(b))
    removed = sorted(set(b) - set(a))
    changed = sorted(k for k in set(a) & set(b) if a[k] != b[k])
    return {
        "same": not (added or removed or changed),
        "files": len(a),
        "added": added,
        "removed": removed,
        "changed": changed,
    }


def _ledger_lines(folder: Path | None) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    if folder is None or not folder.is_dir():
        return out
    for f in sorted(folder.glob("*.tsv")):
        out[f.name] = {ln for ln in f.read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")}
    return out


def layer_digests(store: Any) -> dict[str, dict[str, Any]]:
    """Per layer: the number of live records and a digest of their ``(id, hash)`` pairs."""
    con = store._reader()
    out: dict[str, dict[str, Any]] = {}
    rows = con.execute(
        "SELECT l.slug, r.id, r.hash, r.deleted FROM rec r JOIN layer l ON l.id = r.layer ORDER BY l.slug, r.id"
    ).fetchall()
    by: dict[str, list[str]] = {}
    for slug, rid, h, deleted in rows:
        by.setdefault(slug, []).append(f"{rid} {h}{' deleted' if deleted else ''}")
    for slug, lines in sorted(by.items()):
        out[slug] = {
            "records": sum(1 for x in lines if not x.endswith(" deleted")),
            "digest": fsio.sha256_hex("\n".join(lines)),
        }
    return out


def _layer_hashes(store: Any) -> dict[str, dict[str, str]]:
    con = store._reader()
    out: dict[str, dict[str, str]] = {}
    for slug, rid, h, deleted in con.execute(
        "SELECT l.slug, r.id, r.hash, r.deleted FROM rec r JOIN layer l ON l.id = r.layer"
    ).fetchall():
        if not deleted:
            out.setdefault(slug, {})[rid] = h
    return out


def compare_live(rebuilt: Any, live: Any) -> dict[str, Any]:
    """Layer by layer, the records whose content differs between the rebuilt and the live database."""
    a, b = _layer_hashes(rebuilt), _layer_hashes(live)
    out: dict[str, Any] = {}
    for slug in sorted(set(a) | set(b)):
        x, y = a.get(slug, {}), b.get(slug, {})
        diff = {
            "only_rebuilt": sorted(set(x) - set(y)),
            "only_live": sorted(set(y) - set(x)),
            "changed": sorted(k for k in set(x) & set(y) if x[k] != y[k]),
        }
        if any(diff.values()):
            out[slug] = {k: v[:50] for k, v in diff.items()} | {k + "_count": len(v) for k, v in diff.items()}
    return {"same": not out, "layers": out}


def rebuild(out: Path | None = None, *, compare: bool = False, working_tree: bool = False) -> dict[str, Any]:
    """Run the rebuild (see the module doc) and return its report (also written to ``<out>/report.json``)."""
    from region.cli import imports as I
    from region.model import open_store
    from region.model import seed as S

    out = Path(out) if out is not None else paths.var_path("rebuild")
    _check_out(out)
    fsio.check_write(out / "report.json")
    out.mkdir(parents=True, exist_ok=True)
    _clear(out)
    head = None if working_tree else I.git_head()
    src = out / "src"
    seed_src = _take("region/seed", src / "region" / "seed", head)
    ids_src = _take("region/ids", out / "ids", head)
    for extra in (out / "ids").glob("*.yaml") if ids_src else []:
        extra.unlink()
    report: dict[str, Any] = {
        "commit": head,
        "from": "git" if head else "working tree",
        "imports": {},
        "notes": [],
    }
    with open_store(out / "region.db", backup_dir=out / "backups") as store:
        for name, imp in I.importers().items():
            overrides: dict[str, Path] = {}
            for sname, rel in (SOURCES.get(name) or {}).items():
                got = _take(rel, src / rel, head)
                if got is None:
                    report["notes"].append(f"{name}: {rel} is not in {'git' if head else 'the working tree'}")
                else:
                    overrides[sname] = got
            run = I.run_one(store, imp, overrides=overrides, ledger_dir=out / "ids", work=out / "work", use_git=False)
            r = run.report
            report["imports"][name] = {
                "layer": r.layer,
                "counts": r.counts,
                "by_kind": r.by_kind,
                "conflicts": len(r.conflicts),
                "errors": r.errors[:20],
                "sources": {k: v["sha256"] for k, v in sorted(run.sources.entries.items())},
                "notes": run.sources.notes,
            }
        # the seed after the importers, as on a fresh clone (crhub setup imports, then crhub serve takes in the
        # seed): a seeded record may refer to an imported one, such as a proposal's profile to its section
        if seed_src is not None:
            imported = S.import_seed(store, seed_src)
            report["seed_import"] = {
                slug: {k: v for k, v in st.items() if k not in ("changeset", "run")}
                for slug, st in imported["layers"].items()
            }
        S.export(store, out / "seed")
        report["layers"] = layer_digests(store)
        report["seed"] = compare_trees(out / "seed", seed_src)
        git_ledgers = _ledger_lines(_ledger_root(head, out))
        ours = _ledger_lines(out / "ids")
        report["ledgers"] = {
            name: {
                "lines": len(lines),
                "added": sorted(lines - git_ledgers.get(name, set()))[:50],
                "added_count": len(lines - git_ledgers.get(name, set())),
            }
            for name, lines in sorted(ours.items())
        }
        if compare:
            live_db = paths.var_path("region.db")
            if live_db.is_file():
                with open_store(live_db, readonly=True) as live:
                    report["live"] = compare_live(store, live)
            else:
                report["live"] = {"same": False, "missing": str(live_db)}
    ok = report["seed"]["same"] and not any(v["added_count"] for v in report["ledgers"].values())
    if compare:
        ok = ok and bool(report["live"].get("same"))
    report["ok"] = ok
    fsio.write_text(out / "report.json", json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    return report


def _ledger_root(head: str | None, out: Path) -> Path | None:
    """git's ledgers as committed (``HEAD``), or the working tree's, for the comparison."""
    from region.cli.imports import materialise

    if head is None:
        return paths.repo_root() / "region" / "ids"
    return materialise("region/ids", out / "src" / "region" / "ids", paths.repo_root(), head)


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("rebuild", help="build a fresh database from git plus imports and compare seeds")
    p.add_argument("--out", type=Path, default=None, help="where to build (default var/rebuild)")
    p.add_argument("--compare", action="store_true", help="also compare with the live database (read-only)")
    p.add_argument("--working-tree", action="store_true", help="build from the files as they are, not git's HEAD")
    p.add_argument("--json", action="store_true", help="print the report as JSON")
    p.set_defaults(func=_main)


def _main(args: argparse.Namespace) -> int:
    report = rebuild(args.out, compare=args.compare, working_tree=args.working_tree)
    if args.json:
        print(json.dumps(report, indent=1, sort_keys=True, ensure_ascii=False))
        return 0 if report["ok"] else 1
    seed = report["seed"]
    print(f"rebuilt from {report['from']}" + (f" {report['commit'][:12]}" if report["commit"] else ""))
    for name, r in report["imports"].items():
        c = r["counts"]
        print(f"  {name:<14} {r['layer']:<17} created {c.get('created', 0)}, conflicts {r['conflicts']}")
    print(f"  seed: {'same as git' if seed['same'] else 'differs from git'} ({seed['files']} files)")
    for k in ("added", "removed", "changed"):
        for f in seed[k][:10]:
            print(f"    {k}: {f}")
    for name, lg in report["ledgers"].items():
        if lg["added_count"]:
            print(f"  ledger {name}: {lg['added_count']} line(s) git does not have (run crhub imports and commit)")
    if "live" in report:
        print(f"  live database: {'same' if report['live'].get('same') else 'differs'}")
        for slug, d in (report["live"].get("layers") or {}).items():
            print(
                f"    {slug}: {d['changed_count']} changed, {d['only_live_count']} only live, "
                f"{d['only_rebuilt_count']} only rebuilt"
            )
    for note in report["notes"]:
        print(f"  note: {note}")
    print(f"  report: {(Path(args.out) if args.out else paths.var_path('rebuild')) / 'report.json'}")
    if not report["ok"]:
        print("rebuild differs (see above)", file=sys.stderr)
    return 0 if report["ok"] else 1


__all__ = ["compare_live", "compare_trees", "layer_digests", "rebuild", "register"]
