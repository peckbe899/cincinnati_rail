"""The hub's command line: ``python -m region <command>``, which the launchers ``crhub.cmd`` and ``crhub`` run.

Each command is a module ``region/cli/<name>.py`` that defines

    def register(subparsers) -> None

which adds a subparser named exactly ``<name>`` (aliases are allowed) and sets ``func``, a callable taking the parsed
``argparse.Namespace`` and returning an exit code (``None`` means 0):

    def register(subparsers):
        p = subparsers.add_parser("doctor", help="check this machine and the data")
        p.add_argument("--data", action="store_true")
        p.set_defaults(func=run)

Modules are found by listing the package folder, so adding a file adds a command (``test_cli_lists_every_command``).
A module that fails to import still shows in the help, marked unavailable, and running it prints the error, so one
broken command never takes the others down. With no command, ``serve`` runs (9.22), once it exists.
"""

from __future__ import annotations

import argparse
import importlib
import pkgutil
import sys
import traceback
from collections.abc import Sequence
from pathlib import Path

DEFAULT_COMMAND = "serve"
PROG = "crhub"


def commands() -> list[str]:
    """The command module names in ``region/cli``, sorted (private modules starting with ``_`` excluded)."""
    folder = Path(__file__).resolve().parent
    return sorted(m.name for m in pkgutil.iter_modules([str(folder)]) if not m.name.startswith("_"))


class _Broken:
    def __init__(self, name: str, error: str) -> None:
        self.name = name
        self.error = error

    def __call__(self, args: argparse.Namespace) -> int:
        print(f"{PROG} {self.name}: this command failed to load:\n{self.error}", file=sys.stderr)
        return 2


def build_parser() -> tuple[argparse.ArgumentParser, dict[str, str]]:
    """The full parser, and the commands that failed to load (name -> traceback text)."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="The Cincinnati Rail hub. With no command, serve runs.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_version()}")
    sub = parser.add_subparsers(dest="command", metavar="<command>")
    broken: dict[str, str] = {}
    for name in commands():
        try:
            module = importlib.import_module(f"{__name__}.{name}")
            register = module.register
            register(sub)
            if name not in sub.choices:
                raise RuntimeError(f"region/cli/{name}.py registered no subparser named {name!r}")
        except Exception:
            broken[name] = traceback.format_exc()
            if name not in sub.choices:
                p = sub.add_parser(name, help="(unavailable: failed to load; run it to see why)")
            else:
                p = sub.choices[name]
            p.set_defaults(func=_Broken(name, broken[name]))
    return parser, broken


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("railsim")
    except Exception:
        return "unknown"


def main(argv: Sequence[str] | None = None) -> int:
    """Parse ``argv`` (default ``sys.argv[1:]``), run the command, return its exit code."""
    args_list = list(sys.argv[1:] if argv is None else argv)
    parser, _broken = build_parser()
    if not args_list:
        sub = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
        if DEFAULT_COMMAND in sub.choices:
            args_list = [DEFAULT_COMMAND]
        else:
            parser.print_help()
            return 0
    args = parser.parse_args(args_list)
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 2
    try:
        code = func(args)
    except KeyboardInterrupt:
        return 130
    except Exception as e:
        from region.core.errors import HubError

        if isinstance(e, HubError):
            print(f"{PROG} {args.command}: {e}", file=sys.stderr)
            return e.exit_code
        raise
    return 0 if code is None else int(code)


__all__ = ["DEFAULT_COMMAND", "PROG", "build_parser", "commands", "main"]
