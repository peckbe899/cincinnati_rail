"""``crhub setup``: install what the hub needs, build the app, create or migrate the database, then run doctor.

    crhub setup               every step below, in order, stopping at the first that fails
    crhub setup --dry-run     print the steps and their commands, run nothing
    crhub setup --skip-npm    (and --skip-python, --skip-build, --skip-migrate, --skip-imports, --no-doctor)

setup refuses to start while a hub is serving on the configured port: ``npm ci`` replaces the files its engine runs
from, and the database must not change under it. The steps (9.22, section 9):

1. **python**: with uv on PATH, ``uv sync --locked --inexact`` (``--inexact`` keeps packages Ben installed by hand);
   without it, ``.venv`` is created with this Python if it does not exist, then
   ``.venv`` Python ``-m pip install -r requirements.lock -e .``.
2. **npm**: ``npm ci`` (the root ``package-lock.json`` with the workspaces ``engine`` and ``app``).
3. **build**: ``npm run build -w app``, skipped with a message while ``app/src`` does not exist.
4. **migrate**: ``var/region.db`` is created, or migrated after a checked backup into ``var/backups``
   (``region.model.migrate.migrate`` with ``backup_dir``).
   Skipped with a message while ``region.model`` is not in the checkout; a store that is here but fails to import
   stops setup.
5. **imports**: the first imports, through ``region.cli.imports.setup_imports(db)`` when the imports command
   provides it; skipped with a message until then.
6. **doctor**: the doctor's table; setup's exit code is the doctor's.

Steps 4 to 6 must run in the environment step 1 installed. When setup was started by another Python (say
``py -3.12 -m region setup`` before ``.venv`` existed), it runs them again in ``.venv``'s Python.

Every command is an argument list (never a shell string) run in the repo root, with ``PYTHONUTF8=1``. setup never
touches git, and writes only through npm, uv or pip, the app build and the database.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PYTHON_MIN = (3, 12)

# A command runner: argv, cwd, env -> exit code. Output goes straight to the console. Tests pass a fake.
CommandRunner = Callable[[Sequence[str], Path, Mapping[str, str]], int]


@dataclass
class Step:
    """One step of setup: a command to run, or a Python action, or a skip with its reason."""

    name: str
    about: str
    argv: list[str] | None = None
    action: Callable[[], int] | None = None
    skip: str | None = None
    hint: str = ""

    def describe(self) -> str:
        if self.skip:
            return f"skipped: {self.skip}"
        if self.argv:
            return " ".join(_show(a) for a in self.argv)
        return self.about


@dataclass
class Plan:
    """The steps for this machine, and where steps 4 to 6 must run."""

    repo: Path
    steps: list[Step] = field(default_factory=list)
    env_dir: Path | None = None  # the environment step 1 installs into
    reexec: list[str] | None = None  # the command that runs steps 4 to 6 there, when this process is elsewhere


def _show(arg: str) -> str:
    return f'"{arg}"' if (" " in arg or not arg) else arg


def venv_python(venv: Path) -> Path:
    """The Python of a virtual environment: ``Scripts\\python.exe`` on Windows, ``bin/python`` elsewhere."""
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def uv_env_dir(repo: Path, environ: Mapping[str, str]) -> Path:
    """The environment ``uv sync`` installs into: ``UV_PROJECT_ENVIRONMENT`` (relative to the repo) or ``.venv``."""
    custom = environ.get("UV_PROJECT_ENVIRONMENT")
    if custom:
        p = Path(os.path.expandvars(os.path.expanduser(custom)))
        return p if p.is_absolute() else repo / p
    return repo / ".venv"


def same_env(a: Path, b: Path) -> bool:
    return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))


def run_command(argv: Sequence[str], cwd: Path, env: Mapping[str, str]) -> int:
    """Run one command with its output on the console; its exit code (127 when the program is not found)."""
    try:
        return subprocess.run(list(argv), cwd=cwd, env=dict(env), check=False).returncode
    except FileNotFoundError:
        print(f"crhub setup: {argv[0]} was not found", file=sys.stderr)
        return 127
    except OSError as e:
        print(f"crhub setup: {argv[0]} could not start: {e}", file=sys.stderr)
        return 126


def child_env(environ: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if environ is None else environ)
    env["PYTHONUTF8"] = "1"
    return env


# ----------------------------------------------------------------------------------------------------- the steps


def python_steps(repo: Path, environ: Mapping[str, str], which: Callable[[str], str | None]) -> tuple[list[Step], Path]:
    """Step 1: uv, or the venv and pip path; and the environment it installs into."""
    uv = which("uv")
    if uv:
        env_dir = uv_env_dir(repo, environ)
        return [
            Step(
                "python",
                f"uv sync into {env_dir}",
                argv=[uv, "sync", "--locked", "--inexact"],
                hint="If it says the lock is out of date, git pull again; uv.lock is the lead's to change.",
            )
        ], env_dir
    venv = repo / ".venv"
    py = venv_python(venv)
    steps: list[Step] = []
    if not py.is_file():
        if sys.version_info[:2] < PYTHON_MIN:  # a py launcher default can be older than the hub needs
            steps.append(
                Step(
                    "python",
                    "create .venv",
                    action=lambda: _too_old(),
                    hint="Run setup with Python 3.12: py -3.12 -m region setup",
                )
            )
            return steps, venv
        steps.append(Step("python", "create .venv", argv=[sys.executable, "-m", "venv", str(venv)]))
    elif not has_pip(venv):  # a .venv made by uv has no pip
        steps.append(Step("python", "add pip to .venv", argv=[str(py), "-m", "ensurepip", "--default-pip"]))
    steps.append(
        Step(
            "python",
            "pip install into .venv",
            argv=[str(py), "-m", "pip", "install", "-r", "requirements.lock", "-e", "."],
            hint="Without uv, pip needs the network to fetch the wheels requirements.lock pins.",
        )
    )
    return steps, venv


def has_pip(venv: Path) -> bool:
    """Whether a virtual environment has pip installed (``python -m venv`` adds it; ``uv venv`` does not)."""
    if (venv / "Lib" / "site-packages" / "pip").is_dir():  # Windows
        return True
    return any(venv.glob("lib/python3*/site-packages/pip"))


def _too_old() -> int:
    v = ".".join(str(x) for x in sys.version_info[:3])
    print(f"crhub setup: Python {v} is too old to create .venv; the hub needs 3.12 or later", file=sys.stderr)
    return 1


def npm_steps(repo: Path, which: Callable[[str], str | None], *, skip_npm: bool, skip_build: bool) -> list[Step]:
    """Steps 2 and 3: ``npm ci`` and the app build."""
    npm = which("npm")
    steps: list[Step] = []
    hint_npm = "Install Node 24 LTS (or 22.18 or later) from nodejs.org; npm comes with it."
    if skip_npm:
        steps.append(Step("npm", "npm ci", skip="--skip-npm"))
    elif not npm:
        steps.append(Step("npm", "npm ci", action=lambda: _missing("npm"), hint=hint_npm))
    else:
        steps.append(
            Step(
                "npm",
                "npm ci",
                argv=[npm, "ci"],
                hint="On Windows, close anything running from node_modules (the old hub's browser test, vite, "
                "a running crhub) and run setup again.",
            )
        )
    if skip_build:
        steps.append(Step("build", "npm run build -w app", skip="--skip-build"))
    elif not (repo / "app" / "src").is_dir():
        steps.append(Step("build", "npm run build -w app", skip="app/src does not exist yet, so there is no app"))
    elif not npm:
        steps.append(Step("build", "npm run build -w app", action=lambda: _missing("npm"), hint=hint_npm))
    else:
        steps.append(Step("build", "npm run build -w app", argv=[npm, "run", "build", "-w", "app"]))
    return steps


def _missing(program: str) -> int:
    print(f"crhub setup: {program} is not on PATH", file=sys.stderr)
    return 127


def hub_serving(cfg: Mapping[str, Any] | None = None) -> str | None:
    """The address of a hub serving on the configured port, or None."""
    from region.core import paths

    from .doctor import identify, listening

    cfg = cfg if cfg is not None else paths.config()
    host = str(cfg.get("host") or "127.0.0.1")
    port = int(cfg.get("port") or 8766)
    if listening(host, port) and identify(host, port) == "hub":
        return f"http://{host}:{port}"
    return None


def migrate_db(cfg: Mapping[str, Any] | None = None) -> int:
    """Step 4: create ``var/region.db`` or migrate it, backing it up first. 0 when done or skipped."""
    from region.core import fsio, paths

    from .doctor import module_absent

    cfg = cfg if cfg is not None else paths.config()
    try:
        from region.model.db import connect
        from region.model.migrate import current_version, migrate
    except ImportError as e:
        if not module_absent("region.model.migrate"):
            raise  # the store is here but broken (a missing package, a bug): setup stops and says so
        print(f"      skipped: region.model is not in this checkout yet ({type(e).__name__}: {e})")
        print("      run crhub setup again (or crhub model migrate) once the store has landed")
        return 0
    serving = hub_serving(cfg)
    if serving:
        print(f"crhub setup: a hub is serving at {serving}; stop it before migrating", file=sys.stderr)
        return 1
    db = paths.var_path("region.db", cfg=cfg)
    backups = paths.var_path("backups", cfg=cfg)
    fsio.check_write(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    new = not db.exists()
    con = connect(db)
    try:
        before = current_version(con)
        done = migrate(con, backup_dir=backups)
        after = current_version(con)
    finally:
        con.close()
    if new:
        print(f"      created {db} at schema {after}")
    elif done:
        print(f"      migrated {db} from schema {before} to {after} (backup in {backups})")
    else:
        print(f"      {db} is up to date at schema {after}")
    return 0


def first_imports(cfg: Mapping[str, Any] | None = None) -> int:
    """Step 5: the first imports, when ``region.cli.imports`` provides ``setup_imports(db) -> int``."""
    from region.core import paths

    from .doctor import module_absent

    cfg = cfg if cfg is not None else paths.config()
    try:
        import region.cli.imports as imports_cmd
    except ImportError as e:
        if not module_absent("region.cli.imports"):
            raise  # the command is here but broken: setup stops and says so
        print(f"      skipped: the imports command is not here yet ({type(e).__name__}: {e})")
        return 0
    hook = getattr(imports_cmd, "setup_imports", None)
    if hook is None:
        print("      skipped: region/cli/imports.py has no setup_imports(db); run crhub imports by hand")
        return 0
    db = paths.var_path("region.db", cfg=cfg)
    if not db.is_file():
        print(f"      skipped: no database at {db} (the migrate step creates it)")
        return 0
    return int(hook(db) or 0)


def run_doctor() -> int:
    """Step 6: the doctor's table; its exit code."""
    from region.core import paths

    from . import doctor

    paths.reload()
    checks = doctor.run_checks()
    print(doctor.render(checks))
    return doctor.exit_code(checks)


def plan(
    args: argparse.Namespace,
    *,
    repo: Path | None = None,
    environ: Mapping[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
    prefix: str | None = None,
) -> Plan:
    """The steps for this machine. ``environ``, ``which`` and ``prefix`` (``sys.prefix``) are for tests."""
    from region.core import paths

    repo = repo or paths.repo_root()
    environ = os.environ if environ is None else environ
    out = Plan(repo=repo)
    if args.skip_python:
        out.steps.append(Step("python", "install the Python packages", skip="--skip-python"))
    else:
        steps, env_dir = python_steps(repo, environ, which)
        out.steps.extend(steps)
        out.env_dir = env_dir
    out.steps.extend(npm_steps(repo, which, skip_npm=args.skip_npm, skip_build=args.skip_build))
    here = Path(prefix if prefix is not None else sys.prefix)
    target = venv_python(out.env_dir) if out.env_dir is not None else None
    if out.env_dir is not None and not args.in_env and not same_env(here, out.env_dir):
        rest = [str(target), "-m", "region", "setup", "--in-env", "--skip-python", "--skip-npm", "--skip-build"]
        rest += [
            f
            for f, on in (
                ("--skip-migrate", args.skip_migrate),
                ("--skip-imports", args.skip_imports),
                ("--no-doctor", args.no_doctor),
            )
            if on
        ]
        out.reexec = rest
        out.steps.append(
            Step(
                "env",
                f"run the remaining steps in {out.env_dir}",
                argv=rest,
                hint=f"Steps 4 to 6 run in the environment step 1 installed ({out.env_dir}).",
            )
        )
        return out
    if args.skip_migrate:
        out.steps.append(Step("migrate", "create or migrate var/region.db", skip="--skip-migrate"))
    else:
        out.steps.append(
            Step(
                "migrate",
                "create or migrate var/region.db (a checked backup first)",
                action=migrate_db,
                hint="The database is unchanged when a migration fails; backups are in var/backups.",
            )
        )
    if args.skip_imports:
        out.steps.append(Step("imports", "the first imports", skip="--skip-imports"))
    else:
        out.steps.append(Step("imports", "the first imports", action=first_imports))
    if args.no_doctor:
        out.steps.append(Step("doctor", "crhub doctor", skip="--no-doctor"))
    else:
        out.steps.append(Step("doctor", "crhub doctor", action=run_doctor))
    return out


def execute(p: Plan, *, runner: CommandRunner = run_command, environ: Mapping[str, str] | None = None) -> int:
    """Run the plan's steps in order and stop at the first failure; the exit code."""
    env = child_env(environ)
    n = len(p.steps)
    for i, step in enumerate(p.steps, 1):
        print(f"[{i}/{n}] {step.name:8} {step.describe()}", flush=True)
        if step.skip:
            continue
        if step.argv:
            code = runner(step.argv, p.repo, env)
        elif step.action:
            try:
                code = int(step.action() or 0)
            except Exception as e:  # say which step broke and how, then stop like a failed command
                print(f"crhub setup: {step.name} failed: {type(e).__name__}: {e}", file=sys.stderr)
                code = 1
        else:
            code = 0
        if code != 0:
            if step.name in ("doctor", "env"):
                return code  # the doctor's table, or setup run again in the environment, already says why
            print(f"crhub setup stopped at step {i} ({step.name}): exit code {code}", file=sys.stderr)
            if step.hint:
                print(f"  -> {step.hint}", file=sys.stderr)
            return code
    return 0


# ------------------------------------------------------------------------------------------------------------ cli


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser(
        "setup", help="install the dependencies, build the app, create or migrate the database, run doctor"
    )
    p.add_argument("--dry-run", action="store_true", help="print the steps and their commands, run nothing")
    p.add_argument("--skip-python", action="store_true", help="do not run uv sync or pip")
    p.add_argument("--skip-npm", action="store_true", help="do not run npm ci")
    p.add_argument("--skip-build", action="store_true", help="do not build the app")
    p.add_argument("--skip-migrate", action="store_true", help="do not create or migrate the database")
    p.add_argument("--skip-imports", action="store_true", help="do not run the first imports")
    p.add_argument("--no-doctor", action="store_true", help="do not run doctor at the end")
    p.add_argument("--in-env", action="store_true", help=argparse.SUPPRESS)  # set when setup re-runs itself
    p.set_defaults(func=run)


def run(args: argparse.Namespace) -> int:
    p = plan(args)
    if args.in_env:  # setup run again in the environment: the parent already ran or skipped steps 1 to 3
        p.steps = [s for s in p.steps if s.name not in ("python", "npm", "build")]
    else:
        print(f"crhub setup: {p.repo}")
    if args.dry_run:
        for i, step in enumerate(p.steps, 1):
            print(f"[{i}/{len(p.steps)}] {step.name:8} {step.describe()}")
        print("dry run: nothing was run")
        return 0
    from region.core.errors import HubError

    try:
        serving = hub_serving()
    except (HubError, OSError, ValueError) as e:  # configs/local.json is not JSON, or not a JSON object
        print(f"crhub setup: the config cannot be read: {e}", file=sys.stderr)
        print("  -> Fix configs/local.json (see configs/local.example.json), then run setup again.", file=sys.stderr)
        return 1
    if serving and not args.in_env:
        print(f"crhub setup: a hub is serving at {serving}; stop it first (Ctrl+C in its window)", file=sys.stderr)
        print(
            "  -> npm ci replaces the files its engine runs from, and the database must not change under it.",
            file=sys.stderr,
        )
        return 1
    code = execute(p)
    if code == 0 and not args.in_env:
        print("crhub setup: done. Start the hub with crhub (or crhub serve).")
    return code


__all__ = [
    "CommandRunner",
    "Plan",
    "Step",
    "child_env",
    "execute",
    "first_imports",
    "has_pip",
    "hub_serving",
    "migrate_db",
    "npm_steps",
    "plan",
    "python_steps",
    "register",
    "run",
    "run_command",
    "run_doctor",
    "same_env",
    "uv_env_dir",
    "venv_python",
]
