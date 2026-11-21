"""``python -m region``: the hub's command line (what ``crhub`` runs). The commands are ``region/cli/*.py``."""

from region.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
