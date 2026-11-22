"""``crhub imports``: run the importers (section 10, WP5), and the runner the server, setup and rebuild share.

    crhub imports list                                 the importers, their layers and sources
    crhub imports status [--db PATH]                   which importers' sources changed since their last applied run
    crhub imports run [NAME ...] [--dry-run] [--db PATH] [--hub-db PATH] [--working-tree] [--json]
    crhub imports apply RUN [--db PATH]                apply a dry run (refused when its sources changed since)
    crhub imports show RUN [--db PATH]                 one run's stored report

With no NAME, every importer runs, in the order ``ORDER`` gives (``registry``, ``profile_lines``, ``old_hub``): the
old hub's profiles sit on the sections and platforms ``profile_lines`` makes. While a hub serves from ``var``,
``run`` and ``apply`` go through its HTTP API (``POST /imports``, ``POST /imports/{run}/apply``; decision 9.28);
otherwise they hold ``var``'s single-instance lock while they work.

**Changed sources** (9.26). ``check_sources`` hashes each importer's sources and compares them with its last
applied run; for an importer whose sources changed it makes a dry run, so the change is reported before it is
applied. ``crhub serve`` runs it at start and prints the reports; ``crhub setup`` applies the imports only into
layers that hold nothing yet (the first setup), and makes dry runs otherwise.

**The runner** (``run_import``), for one importer:

1. resolves each source the importer names (``sources(paths)``); a source in the importer's ``from_git`` whose folder
   is in the repo is read from git's ``HEAD`` (decision 9.27: the line files on Ben's machine are Deck-tie output and
   can differ from git), materialised under ``var/imports/git/<commit>/``; ``--working-tree`` reads the files as they
   are instead. ``--hub-db PATH`` gives ``old_hub`` a backup-API snapshot of the old hub's database in place of its
   seed folder;
2. records every file's sha256 in the run's ``sources`` (``<name>/<relpath>`` entries beside the source's own);
3. builds one ``IdLookupImpl`` per run (``store.id_lookup``), with a second one for each namespace the importer
   ``borrows`` (the old hub's profiles take the ids of the profiles namespace), and calls ``records(src, ids)``;
4. calls ``store.apply_import(run, records, dry_run=..., ids=...)``.

``setup_imports(db)`` is what ``crhub setup`` runs: every importer, applied on the first setup and a dry run after
that, with a short table.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from region.core import fsio, paths
from region.core.errors import Invalid, NotFound

ORDER = ("registry", "profile_lines", "old_hub")
"""The run order: an importer whose records sit on another's comes after it."""


# ------------------------------------------------------------------------------------------------------ importers


def importers() -> dict[str, Any]:
    """Every feature's importers by name, in run order (``ORDER`` first, then any others by name)."""
    from region.core import features

    found: dict[str, Any] = {}
    for f in features.discover():
        for imp in f.importers():
            if imp.name in found:
                raise Invalid(f"two importers are named {imp.name!r}")
            found[imp.name] = imp
    rank = {n: i for i, n in enumerate(ORDER)}
    return {n: found[n] for n in sorted(found, key=lambda n: (rank.get(n, len(rank)), n))}


def importer(name: str) -> Any:
    found = importers().get(name)
    if found is None:
        raise NotFound(f"no importer {name!r} (crhub imports list shows them)")
    return found


# ------------------------------------------------------------------------------------------------------------ git


def _git() -> str | None:
    return shutil.which("git")


def _git_out(repo: Path, args: list[str], data: bytes | None = None) -> bytes:
    exe = _git()
    if exe is None:
        raise NotFound("git is not on PATH")
    run = subprocess.run([exe, "-C", str(repo), *args], input=data, capture_output=True, check=False)
    if run.returncode != 0:
        raise NotFound(f"git {' '.join(args[:2])} failed: {run.stderr.decode('utf-8', 'replace').strip()}")
    return run.stdout


def git_head(repo: Path | None = None) -> str | None:
    """The commit ``HEAD`` names, or ``None`` when this is not a git checkout (or git is absent)."""
    repo = repo or paths.repo_root()
    try:
        return _git_out(repo, ["rev-parse", "HEAD"]).decode("ascii").strip()
    except NotFound:
        return None


def git_files(rel: str, repo: Path | None = None, commit: str = "HEAD") -> dict[str, bytes]:
    """The files git holds under ``rel`` (a repo-relative POSIX path, a file or a folder) at ``commit``, as
    ``{path relative to rel: bytes}`` (``{"": bytes}`` for a file). Empty when git tracks nothing there."""
    repo = repo or paths.repo_root()
    rel = rel.strip("/")
    listing = _git_out(repo, ["ls-tree", "-r", "-z", commit, "--", rel or "."])
    entries: list[tuple[str, str]] = []
    for item in listing.split(b"\0"):
        if not item:
            continue
        meta, _, path = item.partition(b"\t")
        mode, kind, sha = meta.decode("ascii").split()
        if kind == "blob":
            entries.append((path.decode("utf-8"), sha))
    if not entries:
        return {}
    blobs = _git_out(repo, ["cat-file", "--batch"], data="".join(sha + "\n" for _, sha in entries).encode("ascii"))
    out: dict[str, bytes] = {}
    at = 0
    for path, sha in entries:
        nl = blobs.index(b"\n", at)
        head = blobs[at:nl].decode("ascii").split()
        if head[0] != sha or head[1] != "blob":
            raise Invalid(f"git cat-file gave {head} for {path}")
        size = int(head[2])
        if path == rel:
            sub = ""
        elif rel:
            sub = path[len(rel) + 1 :]
        else:
            sub = path
        out[sub] = blobs[nl + 1 : nl + 1 + size]
        at = nl + 1 + size + 1
    return out


def materialise(rel: str, dest: Path, repo: Path | None = None, commit: str = "HEAD") -> Path | None:
    """Write git's files under ``rel`` into ``dest`` (only those whose bytes differ) and return the local path
    (``dest`` for a folder, the file for a file); ``None`` when git tracks nothing at ``rel``."""
    files = git_files(rel, repo, commit)
    if not files:
        return None
    if list(files) == [""]:
        target = dest / Path(rel).name
        if not target.is_file() or target.read_bytes() != files[""]:
            fsio.write_atomic(target, files[""])
        return target
    for sub, data in files.items():
        target = dest / sub
        if not target.is_file() or target.read_bytes() != data:
            fsio.write_atomic(target, data)
    return dest


# -------------------------------------------------------------------------------------------------------- sources


def _repo_rel(path: Path, repo: Path) -> str | None:
    try:
        return Path(path).resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return None


def _join(uri: str, rel: str) -> str:
    return uri if not rel else uri.rstrip("/") + "/" + rel


def _files_of(local: Path) -> dict[str, Path]:
    if local.is_file():
        return {"": local}
    return {p.relative_to(local).as_posix(): p for p in sorted(local.rglob("*")) if p.is_file()}


def source_entries(name: str, uri: str, local: Path) -> dict[str, dict[str, str]]:
    """The ``ImportRun.sources`` entries of one source: its own (a file's sha256, or a folder's listing of
    ``<relpath> <sha256>`` lines hashed) and one per file of a folder."""
    files = _files_of(local)
    shas = {rel: fsio.sha256_file(p) for rel, p in files.items()}
    if list(shas) == [""]:
        return {name: {"uri": uri, "sha256": shas[""]}}
    out = {name: {"uri": uri, "sha256": fsio.sha256_hex("".join(f"{r} {s}\n" for r, s in sorted(shas.items())))}}
    for rel, sha in sorted(shas.items()):
        out[f"{name}/{rel}"] = {"uri": _join(uri, rel), "sha256": sha}
    return out


def _lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


@dataclass
class Sources:
    """What a run reads: ``local`` paths by source name, the ``entries`` recorded in ``import_run``, and notes."""

    local: dict[str, Path] = field(default_factory=dict)
    entries: dict[str, dict[str, str]] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def resolve_sources(
    imp: Any,
    *,
    overrides: Mapping[str, Path] | None = None,
    hub_db: Path | None = None,
    work: Path | None = None,
    use_git: bool = True,
) -> Sources:
    """Where each of ``imp``'s sources is read from this run (see the module doc)."""
    from region.ext.legacy.oldhub import snapshot

    overrides = dict(overrides or {})
    work = Path(work) if work is not None else paths.var_path("imports")
    repo = paths.repo_root()
    out = Sources()
    uris = dict(imp.sources(paths))
    if hub_db is not None:
        if "seed" not in uris:
            raise Invalid(f"importer {imp.name} reads no old hub seed, so --hub-db means nothing to it")
        del uris["seed"]
        snap = snapshot(Path(hub_db), work / "hub_snapshot.db")
        out.local["hub_db"] = snap
        out.entries.update(source_entries("hub_db", _uri_of(Path(hub_db)), snap))
        out.notes.append(f"read the old hub's database through a snapshot ({snap.name}), never the live file")
    head = git_head(repo) if use_git and getattr(imp, "from_git", ()) else None
    for name, uri in uris.items():
        if name in overrides:
            local = Path(overrides[name])
            out.local[name] = local
            out.entries.update(source_entries(name, uri, local))
            continue
        local = paths.resolve(uri)
        rel = _repo_rel(local, repo)
        if name in getattr(imp, "from_git", ()) and use_git:
            if head is None or rel is None:
                why = "git is not available here" if head is None else f"{local} is outside the repo"
                out.notes.append(f"{name}: read from the working tree ({why})")
            else:
                got = materialise(rel, work / "git" / head[:12] / rel, repo)
                _prune_git(work / "git", keep=head[:12])
                if got is None:
                    out.notes.append(f"{name}: git tracks nothing at {rel}; read from the working tree")
                else:
                    differ = _differs(got, local)
                    if differ:
                        out.notes.append(
                            f"{name}: read {rel} from git {head[:12]}; {len(differ)} file(s) differ in the working "
                            f"tree ({', '.join(differ[:4])}{', ...' if len(differ) > 4 else ''})"
                        )
                    local = got
        out.local[name] = local
        out.entries.update(source_entries(name, uri, local))
    return out


def _prune_git(folder: Path, *, keep: str) -> None:
    """Delete the copies of earlier commits under ``var/imports/git`` (one per commit an import ran at), so ``var``
    does not grow by a copy of the line files at every commit. A copy still open elsewhere (Windows) is left."""
    if not folder.is_dir():
        return
    for old in folder.iterdir():
        if old.name == keep or not old.is_dir():
            continue
        try:
            fsio.check_write(old)
            shutil.rmtree(old)
        except OSError:
            continue


def _differs(git_copy: Path, working: Path) -> list[str]:
    a, b = _files_of(git_copy), _files_of(working) if working.exists() else {}
    out = []
    for rel in sorted(set(a) | set(b)):
        if rel not in a or rel not in b or _lf(a[rel].read_bytes()) != _lf(b[rel].read_bytes()):
            out.append(rel or working.name)
    return out


def _uri_of(path: Path) -> str:
    try:
        return paths.to_uri(path)
    except Invalid:
        return Path(path).resolve().as_posix()


# ----------------------------------------------------------------------------------------------------------- ids


class RoutedIds:
    """One run's ``IdLookup``: the importer's own namespace, plus a lookup per namespace it borrows for some legacy
    kinds. ``apply_import`` flushes all of them in the import's transaction (``flush_into``, ``write_ledger``)."""

    def __init__(self, own: Any, borrowed: Mapping[str, Any] | None = None) -> None:
        self.own = own
        self.by_lkind = dict(borrowed or {})
        seen: list[Any] = [own]
        for lk in self.by_lkind.values():
            if all(lk is not s for s in seen):
                seen.append(lk)
        self.lookups = seen

    def id_for(self, lkind: str, key: str, *, kind: str, match: Callable | None = None) -> str:
        return self.by_lkind.get(lkind, self.own).id_for(lkind, key, kind=kind, match=match)

    @property
    def pending(self) -> dict[tuple[str, str], str]:
        out: dict[tuple[str, str], str] = {}
        for lk in self.lookups:
            out.update(lk.pending)
        return out

    def flush_into(self, con: Any) -> list[tuple[Any, Any]]:
        return [(lk, lk.flush_into(con)) for lk in self.lookups]

    def write_ledger(self, written: Iterable[tuple[Any, Any]]) -> None:
        for lk, w in written or []:
            lk.write_ledger(w)

    def flush(self) -> None:
        for lk in self.lookups:
            lk.flush()


def id_lookup(store: Any, imp: Any, *, ledger_dir: Path | None = None) -> RoutedIds:
    """The ``IdLookup`` for one run of ``imp`` over ``store``."""
    from region.core import ids as core_ids

    own = store.id_lookup(layer=imp.layer, namespace=imp.namespace, ledger_dir=ledger_dir)
    borrowed: dict[str, Any] = {}
    for ns, lkinds in (getattr(imp, "borrows", None) or {}).items():
        spec = core_ids.namespaces().get(ns)
        if spec is None:
            raise Invalid(f"importer {imp.name} borrows unknown namespace {ns!r}")
        lk = store.id_lookup(layer=spec.layer, namespace=ns, ledger_dir=ledger_dir)
        for lkind in lkinds:
            borrowed[lkind] = lk
    return RoutedIds(own, borrowed)


# ------------------------------------------------------------------------------------------------------- running


@dataclass
class Run:
    """One importer run: the store's report, what was read, and notes for the person running it."""

    report: Any
    sources: Sources

    def summary(self) -> dict[str, Any]:
        r = self.report
        return {
            "importer": r.importer,
            "layer": r.layer,
            "run": r.run,
            "dry_run": r.dry_run,
            "counts": r.counts,
            "by_kind": r.by_kind,
            "changeset": r.changeset,
            "conflicts": len(r.conflicts),
            "errors": r.errors[:20],
            "notes": self.sources.notes,
        }


def run_one(
    store: Any,
    imp: Any,
    *,
    dry_run: bool = False,
    overrides: Mapping[str, Path] | None = None,
    hub_db: Path | None = None,
    ledger_dir: Path | None = None,
    work: Path | None = None,
    use_git: bool = True,
) -> Run:
    """Run one importer (an importer object or its name) over ``store``; see the module doc."""
    from region.core.protocols import ImportRun

    imp = importer(imp) if isinstance(imp, str) else imp
    src = resolve_sources(imp, overrides=overrides, hub_db=hub_db, work=work, use_git=use_git)
    ids = id_lookup(store, imp, ledger_dir=ledger_dir)
    records = list(imp.records(src.local, ids))
    run = ImportRun(
        importer=imp.name, version=imp.version, layer=imp.layer, namespace=imp.namespace, sources=src.entries
    )
    report = store.apply_import(run, records, dry_run=dry_run, ids=ids)
    return Run(report, src)


def run_import(store: Any, imp: Any, *, dry_run: bool = False, **kw: Any) -> Any:
    """``run_one(...).report``: the ``ImportReport`` (for the server's ``POST /imports``)."""
    return run_one(store, imp, dry_run=dry_run, **kw).report


def run_all(store: Any, names: Iterable[str] | None = None, **kw: Any) -> list[Run]:
    """Run the named importers (default: every one) in run order. ``hub_db`` goes to the importers that read the old
    hub's seed (``old_hub``) and no other."""
    known = importers()
    wanted = list(known) if not names else list(names)
    for n in wanted:
        if n not in known:
            raise NotFound(f"no importer {n!r} (crhub imports list shows them)")
    order = [n for n in known if n in wanted]
    hub_db = kw.pop("hub_db", None)
    runs = []
    for n in order:
        reads_seed = "seed" in known[n].sources(paths)
        runs.append(run_one(store, known[n], hub_db=hub_db if reads_seed else None, **kw))
    return runs


# ------------------------------------------------------------------------------------------------ changed sources


def _tops(entries: Mapping[str, Any] | None) -> dict[str, Any]:
    """The per-source entries of a run's ``sources`` (not the per-file ``<name>/<relpath>`` ones)."""
    return {k: v for k, v in (entries or {}).items() if "/" not in k}


def last_applied(store: Any, name: str) -> dict[str, Any] | None:
    """``{"run", "sources", "finished"}`` of the newest import run of ``name`` that was applied (or found nothing to
    change), or ``None`` when it never ran here."""
    row = (
        store._reader()
        .execute(
            "SELECT id, sources, finished FROM import_run WHERE importer = ? AND dry_run = 0 "
            "AND state IN ('applied', 'unchanged') ORDER BY id DESC LIMIT 1",
            (name,),
        )
        .fetchone()
    )
    if row is None:
        return None
    return {"run": row[0], "sources": json.loads(row[1]) if row[1] else {}, "finished": row[2]}


def stale_sources(store: Any, names: Iterable[str] | None = None, **kw: Any) -> list[dict[str, Any]]:
    """The importers whose sources differ from their last applied run: ``[{"importer", "last_run", "changed"}]``
    (``changed`` names the sources, or is ``["never imported"]``)."""
    out = []
    for name, imp in importers().items():
        if names is not None and name not in names:
            continue
        last = last_applied(store, name)
        now = _tops(resolve_sources(imp, **kw).entries)
        if last is None:
            out.append({"importer": name, "last_run": None, "changed": ["never imported"]})
            continue
        before = _tops(last["sources"])
        changed = sorted(k for k in set(now) | set(before) if now.get(k) != before.get(k))
        if changed:
            out.append({"importer": name, "last_run": last["run"], "changed": changed})
    return out


def check_sources(store: Any, *, ledger_dir: Path | None = None) -> list[dict[str, Any]]:
    """``stale_sources`` with a dry run of each stale importer: each entry gains ``"dry_run"`` (the run id),
    ``"counts"`` and ``"errors"`` (9.26: a changed source is reported; applying it is a separate step)."""
    stale = stale_sources(store)
    for st in stale:
        done = run_one(store, importers()[st["importer"]], dry_run=True, ledger_dir=ledger_dir)
        st["dry_run"] = done.report.run
        st["counts"] = dict(done.report.counts)
        st["errors"] = list(done.report.errors[:5])
    return stale


def describe_stale(st: Mapping[str, Any]) -> str:
    """One line for a stale importer (``check_sources``' entry)."""
    c = st.get("counts") or {}
    counts = ", ".join(f"{k} {c.get(k, 0)}" for k in ("created", "updated", "deleted", "conflicts"))
    since = f"since run {st['last_run']}" if st.get("last_run") else "(never applied here)"
    line = f"{st['importer']}: {', '.join(st['changed'][:4])} changed {since}"
    if st.get("dry_run") is not None:
        line += f"; dry run {st['dry_run']}: {counts}. Apply: crhub imports apply {st['dry_run']}"
    if st.get("errors"):
        line += f" (it has {len(st['errors'])} error(s): {st['errors'][0].get('message', '')})"
    return line


# ----------------------------------------------------------------------------------------------------- reporting


def _table(runs: list[Run]) -> str:
    cols = ("created", "updated", "unchanged", "deleted", "conflicts")
    lines = [f"  {'importer':<14} {'layer':<17} " + " ".join(f"{c:>9}" for c in cols)]
    for r in runs:
        c = r.report.counts
        flag = " (dry run)" if r.report.dry_run else ""
        lines.append(
            f"  {r.report.importer:<14} {r.report.layer:<17} " + " ".join(f"{c.get(k, 0):>9}" for k in cols) + flag
        )
        for note in r.sources.notes:
            lines.append(f"    {note}")
        for e in r.report.errors[:5]:
            lines.append(f"    error: {e.get('path', '')} {e.get('message', '')}")
    return "\n".join(lines)


def _layer_empty(store: Any, slug: str) -> bool:
    con = store._reader()
    row = con.execute("SELECT 1 FROM rec r JOIN layer l ON l.id = r.layer WHERE l.slug = ? LIMIT 1", (slug,)).fetchone()
    return row is None


def setup_imports(db: Path, *, ledger_dir: Path | None = None, apply: bool = False) -> int:
    """``crhub setup``'s imports step, under ``var``'s lock. An importer whose layer holds nothing yet (the first
    setup) is applied; any other runs as a dry run whose report is printed with the command that applies it (9.26:
    a changed source is reported, and applying it is an explicit step). ``apply=True`` applies every one. Returns
    0, or 1 when an import failed (its reason printed). ``ledger_dir`` defaults to ``region/ids``."""
    from region.core import lock
    from region.core.errors import HubError
    from region.model import open_store

    with lock.acquire(paths.var_root(), 0, command="crhub setup (imports)"):
        with open_store(Path(db), create=False) as store:
            runs: list[Run] = []
            try:
                for imp in importers().values():
                    first = apply or _layer_empty(store, imp.layer)
                    runs.append(run_one(store, imp, dry_run=not first, ledger_dir=ledger_dir))
            except HubError as e:
                print(f"      imports failed: {e}", file=sys.stderr)
                for err in (getattr(e, "errors", None) or [])[:5]:
                    print(f"        {err.get('path', '')} {err.get('message', '')}", file=sys.stderr)
                return 1
    print(_table(runs))
    planned = [r for r in runs if r.report.dry_run and _changes(r.report.counts)]
    if planned:
        print("      these imports were not applied (their layers already hold records); review, then apply:")
        for r in planned:
            print(f"        crhub imports apply {r.report.run}    ({r.report.importer})")
    return 0


def _changes(counts: Mapping[str, Any]) -> int:
    return sum(int(counts.get(k, 0) or 0) for k in ("created", "updated", "deleted"))


# ----------------------------------------------------------------------------------------------------------- CLI


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("imports", help="run the importers (line files, registry, old hub)")
    sub = p.add_subparsers(dest="imports_command", metavar="<action>")
    sub.add_parser("list", help="the importers, their layers and sources")
    run = sub.add_parser("run", help="run importers (default: every one, in order)")
    run.add_argument("names", nargs="*", metavar="NAME", help="importers to run (default: all)")
    run.add_argument("--dry-run", action="store_true", help="report what would change; write nothing")
    run.add_argument("--db", type=Path, default=None, help="region.db (default var/region.db)")
    run.add_argument(
        "--hub-db", type=Path, default=None, help="read the old hub from a snapshot of this hub.db instead of hub/seed"
    )
    run.add_argument(
        "--working-tree", action="store_true", help="read the line files as they are, not from git (9.27 reads git)"
    )
    run.add_argument("--json", action="store_true", help="print the reports as JSON")
    run.add_argument("--ledger-dir", type=Path, default=None, help="the id ledgers to use (default region/ids)")
    show = sub.add_parser("show", help="one run's stored report")
    show.add_argument("run_id", type=int, metavar="RUN")
    show.add_argument("--db", type=Path, default=None, help="region.db (default var/region.db)")
    apply = sub.add_parser("apply", help="apply a dry run (refused when its sources changed since)")
    apply.add_argument("run_id", type=int, metavar="RUN")
    apply.add_argument("--db", type=Path, default=None, help="region.db (default var/region.db)")
    status = sub.add_parser("status", help="which importers' sources changed since their last applied run")
    status.add_argument("--db", type=Path, default=None, help="region.db (default var/region.db)")
    p.set_defaults(func=_main)


def _db(args: argparse.Namespace) -> Path:
    db = Path(args.db) if getattr(args, "db", None) is not None else paths.var_path("region.db")
    if not db.is_file():
        raise NotFound(f"no database at {db}; run crhub setup first")
    return db


def _main(args: argparse.Namespace) -> int:
    action = getattr(args, "imports_command", None) or "list"
    if action == "list":
        for name, imp in importers().items():
            srcs = ", ".join(f"{k}={v}" for k, v in imp.sources(paths).items())
            git = f" (git: {', '.join(imp.from_git)})" if getattr(imp, "from_git", ()) else ""
            print(f"{name}@{imp.version}  {imp.layer}  {srcs}{git}")
        return 0
    if action == "show":
        from region.model import open_store

        with open_store(_db(args), readonly=True) as store:
            print(json.dumps(store.import_run(args.run_id), indent=1, ensure_ascii=False, default=str))
        return 0
    if action == "status":
        from region.model import open_store

        with open_store(_db(args), readonly=True) as store:
            stale = stale_sources(store)
        for st in stale:
            print(describe_stale(st))
        if not stale:
            print("every importer's sources are as last applied")
        return 1 if stale else 0
    hub = _running_hub(args)
    if hub is not None:
        return _through_hub(hub, action, args)
    from region.core import lock
    from region.model import open_store

    db = _db(args)
    with lock.acquire(paths.var_root(), 0, command=f"crhub imports {action}"):
        with open_store(db, create=False) as store:
            if action == "apply":
                runs = [_apply_direct(store, args.run_id)]
            else:
                runs = run_all(
                    store,
                    args.names,
                    dry_run=args.dry_run,
                    hub_db=args.hub_db,
                    use_git=not args.working_tree,
                    ledger_dir=args.ledger_dir,
                )
    if getattr(args, "json", False):
        print(json.dumps([r.summary() for r in runs], indent=1, ensure_ascii=False, default=str))
    else:
        print(_table(runs))
    return 1 if any(r.report.errors for r in runs) else 0


def _running_hub(args: argparse.Namespace) -> Any:
    """The client of the hub serving from ``var`` when no ``--db`` was given (9.28: its database is written only
    through it), else ``None``."""
    if getattr(args, "db", None) is not None:
        return None
    from region.api.client import running_hub

    return running_hub(client="crhub-cli", timeout=900.0)


def _apply_direct(store: Any, run_id: int) -> Run:
    """Apply dry run ``run_id`` on a store opened here: the importer runs again, only when its sources still hash
    as they did (the same rule as ``POST /imports/{run}/apply``)."""
    from region.core.errors import Conflict

    planned = store.import_run(run_id)
    if not planned.get("dry_run"):
        raise Conflict(f"import run {run_id} was not a dry run", reason="layer")
    imp = importer(planned["importer"])
    now = resolve_sources(imp).entries
    before = planned.get("sources") or {}
    if now != before:
        changed = sorted(k for k in set(now) | set(before) if now.get(k) != before.get(k) and "/" not in k)
        raise Conflict(
            f"the sources of import run {run_id} changed since the dry run ({', '.join(changed) or 'files'}); "
            "run a new dry run (crhub imports run --dry-run)",
            reason="rebase",
        )
    return run_one(store, imp, dry_run=False)


def _through_hub(hub: Any, action: str, args: argparse.Namespace) -> int:
    """``run`` and ``apply`` through the serving hub's ``/imports`` routes."""
    if action == "run" and (args.hub_db or args.working_tree or args.ledger_dir):
        print(
            f"crhub imports run: a hub is serving at {hub.base} ({hub.holder.describe() if hub.holder else 'serve'}),"
            " and its imports read the usual sources only. Drop --hub-db, --working-tree and --ledger-dir, or stop "
            "the hub to run with them.",
            file=sys.stderr,
        )
        return 1
    reps = []
    if action == "apply":
        reps.append(hub.json("POST", f"/imports/{args.run_id}/apply"))
    else:
        names = list(args.names) or list(importers())
        for n in names:
            reps.append(hub.json("POST", "/imports", json_body={"importer": n, "dry_run": bool(args.dry_run)}))
    print(f"imports (through the hub serving at {hub.base})")
    if getattr(args, "json", False):
        print(json.dumps(reps, indent=1, ensure_ascii=False, default=str))
    else:
        cols = ("created", "updated", "unchanged", "deleted", "conflicts")
        for r in reps:
            c = r.get("counts") or {}
            flag = " (dry run)" if r.get("dry_run") else ""
            print(
                f"  {r.get('importer', ''):<14} {r.get('layer', ''):<17} "
                + " ".join(f"{k} {c.get(k, 0)}" for k in cols)
                + f"  run {r.get('run')}{flag}"
            )
    return 1 if any(r.get("errors") for r in reps) else 0


__all__ = [
    "ORDER",
    "RoutedIds",
    "check_sources",
    "describe_stale",
    "last_applied",
    "stale_sources",
    "Run",
    "Sources",
    "git_files",
    "git_head",
    "id_lookup",
    "importer",
    "importers",
    "materialise",
    "register",
    "resolve_sources",
    "run_all",
    "run_import",
    "run_one",
    "setup_imports",
    "source_entries",
]
